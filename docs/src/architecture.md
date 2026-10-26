# Architecture

## Overview

HOPE Documents is split into two Django apps:

- **`hope_ocr`** — OCR engine, document catalog (archive), and admin UI. Self-contained; can be used independently of the REST API.
- **`hope_documents`** — REST API, async analysis pipeline, and the `AnalysisJob` model. Depends on `hope_ocr`.

### Key components

| Component | Location | Purpose |
|---|---|---|
| OCR engine | `hope_ocr/ocr/engine.py` | Tesseract + OpenCV image processing |
| Document catalog | `hope_ocr/archive/models.py` | Config layer: countries, document types, attributes, regions |
| Extraction protocol | `hope_documents/extractors.py` | `AttributeExtractor` Protocol + `OCRAttributeExtractor` |
| Analysis task | `hope_documents/tasks.py` | Celery task that runs extraction and persists results |
| REST API | `hope_documents/api/` | DRF views + serializers for `POST /api/analyze/` |
| Admin | `hope_ocr/archive/admin.py` | Catalog management + Define Regions canvas UI |

---

## Domain model

### Configuration layer (`hope_ocr.archive`)

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

### Processing layer (`hope_documents`)

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
                         resolve Document version
                         (score candidate versions against extracted values)
                                   │
                                   ▼
                         OCRAttributeExtractor.extract()
                           for each DocumentAttribute:
                             ├─ region defined → crop image → OCR crop
                             └─ no region → OCR full image
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

## Extraction abstraction

`AttributeExtractor` is a `Protocol` in `hope_documents/extractors.py`:

```python
class AttributeExtractor(Protocol):
    def extract_attribute(
        self,
        image: Image.Image,
        attribute_name: str,
        region: BoundingBox | None,
    ) -> str: ...
```

`OCRAttributeExtractor` is the current implementation — it uses `hope_ocr` directly. A future `LLMAttributeExtractor` is planned for low-confidence fallback (see todo list).

---

## Technologies

| Layer | Technology |
|---|---|
| Web framework | Django + Django REST Framework |
| OCR | Tesseract (via pytesseract), OpenCV |
| Async tasks | Celery |
| Admin UI | Unfold + django-admin-extra-buttons |
| API schema | drf-spectacular (Swagger / ReDoc) |
| CLI | Click (via mkdocs-click autogen) |
