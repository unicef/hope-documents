# Configuration

This page explains how to configure the document extraction catalog — the set of models that tell the OCR engine which fields exist for each document type, country, and version.

---

## Objects at a glance

| Object | Purpose |
|---|---|
| **Country** | Identifies the issuing country |
| **DocumentType** | Identifies the kind of document (passport, driving licence, …) |
| **Attribute** | A named extractable field (e.g. `first_name`, `date_of_birth`) |
| **Document** | A specific version of a document type for a country |
| **DocumentAttribute** | Links an Attribute to a Document; stores the extraction region and validation expression |

---

## Countries and Document Types

Countries and Document Types are reference objects — create or import them once and reuse them across Documents.

**Country** carries two sets of codes:

- `code2`, `code3`, `number` — the legacy identifiers already used by Document Rules.
- `full_name`, `iso_code2`, `iso_code3`, `un_code` — supplementary ISO 3166-1 fields, all optional.

**DocumentType** has a short `code` (e.g. `DL`, `PAS`), a human-readable `name`, and an optional `description`.

---

## Attribute catalog

The Attribute catalog lists every field that *can* be extracted from any document in the system.

| Field | Notes |
|---|---|
| `name` | Unique identifier used by the extraction engine to reference the field |
| `description` | Human-readable explanation |
| `system` | If `True`, the attribute is built-in and cannot be renamed or deleted |

Three system attributes are seeded automatically: **`first_name`**, **`last_name`**, **`document_number`**. Their descriptions can be edited but their names are fixed.

Custom attributes can be created, renamed, and deleted freely from the admin.

---

## Documents and versioning

A **Document** captures the combination of a DocumentType, a Country, and a `version` label. The version is free text and groups a full set of DocumentAttributes together — think of it as the "edition" of a document template.

### Choosing a version value

There is no enforced format. Common conventions:

- **Year the form became valid** — e.g. `"2024"` for an Italian passport redesigned in 2024.
- **Iteration label** — e.g. `"v2"` or `"rev3"` for internally-versioned templates.

> **Example:** The Italian passport was redesigned in 2024. You would create:
>
> - Document: type=`PAS`, country=`IT`, version=`"2024"`
> - DocumentAttribute: document=above, attribute=`last_name`
> - DocumentAttribute: document=above, attribute=`first_name`
> - DocumentAttribute: document=above, attribute=`document_number`, with a validation expression `[A-Z]{2}[0-9]{7}`

---

## DocumentAttributes

A **DocumentAttribute** links one Attribute to a Document and carries two optional configuration fields: `region` and `validation_expression`.

### Region (bounding box)

The `region` field defines the pixel crop on the document image from which the attribute value should be extracted. When a region is set the extraction engine crops the image to that area before running OCR, which significantly improves accuracy for known layouts.

The region is stored internally as a four-corner bounding box. When entering coordinates manually in the admin form the expected format is:

```json
{"x": 10, "y": 20, "width": 100, "height": 50}
```

#### Defining regions with the canvas UI

The **Define Regions** button on the Document change page opens an interactive canvas tool:

1. Upload a reference image of the document.
2. Click a row in the attribute table to select it.
3. Drag on the canvas to draw that attribute's bounding box.
4. Repeat for each attribute.
5. Click **Save regions** — coordinates are saved and the canvas remains visible.

The canvas uses display-scaled coordinates that are automatically converted to original image pixel space on save. Leaving all four coordinate fields blank for an attribute clears its region.

> **Note:** The reference image is not persisted server-side between sessions. You will need to re-upload it each time you open Define Regions. Persisting the reference image on the Document model is a planned improvement.

### Validation expression

The `validation_expression` field accepts a regular expression. At analysis time, each extracted value is tested against it. The outcome depends on the `validation_mode` set on the analysis request — see [Validation modes](api.md#validation-modes) in the API docs.

Leave blank to accept any extracted value.

> **Example:** For `document_number` on an Italian passport, a suitable expression is `[A-Z]{2}[0-9]{7}` — two uppercase letters followed by seven digits.

---

## Admin step-by-step

1. **Create a Country** — Admin → ID Documents → Countries → Add.
2. **Create a DocumentType** — Admin → ID Documents → Document Types → Add.
3. **Add any custom Attributes** — Admin → ID Documents → Attributes → Add. (System attributes are already present.)
4. **Create a Document** — Admin → ID Documents → Documents → Add. Select the type and country, enter a version label.
5. **Add DocumentAttributes** inline on the Document form — select an Attribute, optionally enter a `validation_expression`.
6. **Define extraction regions** — on the Document change page click **Define Regions**, upload a reference image, and draw bounding boxes for each attribute.
