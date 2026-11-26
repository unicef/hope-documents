# Architecture

## Overview

HOPE Documents is a single Django package (`hope_documents`) with four logical layers:

- **Archive** (`hope_documents.archive`) — document catalog, admin UI, and document pre-processing. Defines which fields exist for each document type, country, and version.
- **Processing** (`hope_documents`) — REST API, async analysis pipeline, and the `AnalysisJob` model.
- **OCR** (`hope_documents.ocr`) — Tesseract + OpenCV image processing engine; used by both the archive admin and the processing layer.
- **Stream** (`hope_documents.stream`) — batch OCR pipeline that reads documents from HOPE Azure storage and publishes results via a message broker.

### Key components

| Component | Location | Purpose |
|---|---|---|
| OCR engine | `hope_documents/ocr/engine.py` | Tesseract + OpenCV image processing |
| Document catalog | `hope_documents/archive/models.py` | Config layer: countries, document types, attributes, regions |
| Extraction protocol | `hope_documents/extractors.py` | `AttributeExtractor` Protocol + `OCRAttributeExtractor` + `LLMAttributeExtractor` + `ChainedAttributeExtractor` |
| Document pre-processing | `hope_documents/utils/preprocessing.py` | Detect document boundary, deskew, crop background |
| Analysis task | `hope_documents/tasks.py` | Celery task that runs extraction and persists results |
| REST API | `hope_documents/api/` | DRF views + serializers for `POST /api/analyze/` |
| Admin | `hope_documents/archive/admin.py` | Catalog management + Define Regions canvas UI + Test Regions overlay |
| Grants | `hope_documents/grants.py` | `Grant` enum used by `TokenRequiredView` to gate API endpoints |

---

## Domain model

### Configuration layer (`hope_documents.archive`)

Defines *which fields exist* for each document type, country, and version:

```
Country ──────────────────┐
                          ▼
DocumentType ────────► Document ──► DocumentAttribute ──► Attribute
                       (version)     (region, validation_expression)
```

- `Country` and `DocumentType` are reference objects shared across documents.
- `Document` groups a `DocumentType`, `Country`, and free-text `version`. A version labels one complete layout — e.g. all attributes valid for Italian passports issued from 2024 onwards.
- `Attribute` is a catalog of extractable field names. Three system attributes (`first_name`, `last_name`, `document_number`) are seeded automatically and cannot be renamed.
- `DocumentAttribute` links one `Attribute` to a `Document` and stores:
  - `region` — a `BoundingBox` (pixel coordinates) on the document image used to crop before OCR.
  - `validation_expression` — an optional regex the extracted value must satisfy.

### Processing layer

`AnalysisJob` records every extraction request:

| Field | Notes |
|---|---|
| `id` | UUID primary key |
| `status` | `pending` → `running` → `completed` / `failed` |
| `document_type` / `country` | FK to catalog |
| `image` | Uploaded document image |
| `validation_mode` | Controls how validation_expression failures are handled |
| `callback_url` | Optional POST target on completion |
| `matched_version` / `version_matched` | Which Document version was selected |
| `result` | JSON array of `{attribute_name, extracted_value}` |

`DocumentRule` (existing) stores per-country regex patterns used by the legacy OCR engine. It is independent of the configuration layer above.

---

## Extraction pipeline

```
POST /api/analyze/
       │
       ▼
AnalyzeView
  ├─ validate input (document_type, country, image)
  ├─ create AnalysisJob (status=pending)
  └─ save image to media/analysis_jobs/
       │
       ├─ ?sync=true ──► process_analysis_job() in-process
       └─ default ──────► process_analysis_job.delay() via Celery
                                   │
                                   ▼
                         detect_and_normalise(image)
                           ├─ contour detection → perspective warp to document quad
                           ├─ deskew
                           └─ fallback: return original if no document found
                                   │
                                   ▼
                         resolve Document version
                         (score candidate versions against extracted values)
                                   │
                                   ▼
                         ChainedAttributeExtractor.extract()
                           ├─ OCRAttributeExtractor.extract()
                           │    for each DocumentAttribute:
                           │      ├─ region defined → scale coords by (processed_size / reference_size)
                           │      │                 → crop image → OCR crop (PSM 6)
                           │      └─ no region → fuzzy label search (find_single) on full image
                           │
                           └─ LLMAttributeExtractor.extract() (if configured)
                                sends full image + field names to LLM backend
                                fills in any attributes not extracted by OCR
                                   │
                                   ▼
                         validate against validation_expression
                         apply validation_mode logic
                                   │
                                   ▼
                         persist result on AnalysisJob
                         fire callback_url if set
```

---

## Document pre-processing

`detect_and_normalise` in `hope_documents/utils/preprocessing.py` runs on every submitted image before extraction begins:

1. **Contour detection** — finds the largest quadrilateral contour that covers > 15% of the image (the document boundary).
2. **Perspective warp** — if a quad is found, `cv2.warpPerspective` rectifies it to a straight-on view at the document's natural pixel size, removing background.
3. **Deskew** — corrects slight rotational tilt using the `deskew` package (Hough-line skew estimation + `scipy.ndimage.rotate`). Skews < 0.5° are skipped.
4. **Fallback** — if no clear document quad is detected, only deskew is applied. If deskew finds no rotation, the original image is returned unchanged.

### Coordinate normalisation

Region coordinates are stored in absolute pixels relative to the **reference image** used in Define Regions. The reference image dimensions (`Document.reference_width`, `Document.reference_height`) are stored when the user saves regions. At extraction time, the pre-processed image may have different dimensions, so coordinates are scaled:

```
sx = processed_width  / document.reference_width
sy = processed_height / document.reference_height
region_coords *= (sx, sy)
```

If `reference_width`/`reference_height` are not set (e.g. the document was configured before this feature), scale factors default to 1.0 and coordinates are used as-is.

---

## Extraction abstraction

`AttributeExtractor` is a runtime-checkable `Protocol` in `hope_documents/extractors.py`:

```python
class AttributeExtractor(Protocol):
    def extract_attribute(
        self,
        image: Image.Image,
        attribute_name: str,
        region: BoundingBox | None,
    ) -> str: ...
```

Three concrete implementations ship with the package:

- **`OCRAttributeExtractor`** — crops each field region and runs Tesseract. The default and primary extractor.
- **`LLMAttributeExtractor`** — sends the full document image to an Ollama or OpenAI-compatible backend with a structured prompt listing the fields to extract. Used as a fallback when OCR yields nothing for an attribute.
- **`ChainedAttributeExtractor`** — wraps a list of extractors and tries each in order, stopping as soon as one returns a non-empty value for an attribute. This is what `tasks.py` builds when `EXTRACTOR_CHAIN` contains more than one entry.

The active chain is controlled by the `HOPE_EXTRACTOR_CHAIN` environment variable (see [Configuration — LLM](#llm-extraction-optional)).

---

## Technologies

| Layer | Technology |
|---|---|
| Web framework | Django + Django REST Framework |
| OCR | Tesseract (via pytesseract), OpenCV |
| LLM backends | Ollama (local), any OpenAI-compatible API |
| Async tasks | Celery |
| Admin UI | Unfold + django-admin-extra-buttons |
| API schema | drf-spectacular (Swagger / ReDoc) |
| API auth | hope-api-auth (`TokenRequiredView` + `Grant` enum) |
| CLI | Click (via mkdocs-click autogen) |
