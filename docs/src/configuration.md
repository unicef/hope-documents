# Configuration

This page explains how to configure the document extraction catalog — the set of models that tell the OCR engine which fields exist for each document type, country and version.

---

## Objects at a glance

| Object | Purpose |
|---|---|
| **Country** | Identifies the issuing country |
| **DocumentType** | Identifies the kind of document (passport, driving licence, …) |
| **Attribute** | A named extractable field (e.g. `first_name`, `date_of_birth`) |
| **Document** | A specific version of a document type for a country |
| **DocumentAttribute** | Links an Attribute to a Document and stores the extraction region |

---

## Countries and Document Types

Countries and Document Types are reference objects — create or import them once and reuse them across Documents.

**Country** carries two sets of codes:

- `code2`, `code3`, `number` — the legacy identifiers already used by Document Rules.
- `full_name`, `iso_code2`, `iso_code3`, `un_code` — supplementary ISO 3166-1 fields, all optional.

**Document Type** has a short `code` (e.g. `DL`, `PAS`), a human-readable `name`, and an optional `description`.

---

## Attribute catalog

The Attribute catalog lists every field that *can* be extracted from any document in the system.

| Field | Notes |
|---|---|
| `name` | Unique identifier, used by the OCR engine to reference the field |
| `description` | Human-readable explanation |
| `system` | If `True`, the attribute is built-in and cannot be renamed or deleted |

Three system attributes are seeded automatically: **`first_name`**, **`last_name`**, **`number`**. Their descriptions can be edited but their names are fixed.

Custom attributes can be created, renamed and deleted freely from the admin.

---

## Documents and versioning

A **Document** captures the combination of a Document Type, a Country, and a `version` label. The version is free text and groups a full set of DocumentAttributes together — think of it as the "edition" of a document template.

### Choosing a version value

There is no enforced format. Common conventions:

- **Year the form became valid** — e.g. `"2019"` for an Italian driving licence redesigned in 2019. All attributes defined under this version describe the layout of licences issued from that year onwards.
- **Iteration label** — e.g. `"v2"` or `"rev3"` for internally-versioned document templates.

The same version string is shared across all DocumentAttributes that belong to that Document — it is the Document record itself, not each attribute, that carries the version.

> **Example:** The Italian driving licence was redesigned in 2019. You would create:
>
> - Document: type=`DL`, country=`IT`, version=`"2019"`
> - DocumentAttribute: document=above, attribute=`last_name`, region=`{"x": 40, "y": 120, …}`
> - DocumentAttribute: document=above, attribute=`first_name`, region=`{"x": 40, "y": 145, …}`
>
> Pre-2019 licences keep the previous Document version with its own region coordinates.

---

## DocumentAttributes and regions

A **DocumentAttribute** links one Attribute from the catalog to a Document and stores a `region` — the bounding box on the document image from which the value should be extracted.

The region is a JSON object with pixel coordinates:

```json
{"x": 10, "y": 20, "width": 100, "height": 50}
```

> **Note:** A region labelling UI does not yet exist. Regions must currently be entered as raw JSON in the admin form. A future ticket will add an image-annotation interface.

The combination of `(document_type, country, version, attribute)` must be unique — the admin will block and display an error if a duplicate is submitted.

---

## Admin step-by-step

1. **Create a Country** — Admin → ID Documents → Countries → Add.
2. **Create a Document Type** — Admin → ID Documents → Document Types → Add.
3. **Add any custom Attributes** — Admin → ID Documents → Attributes → Add. (System attributes are already present.)
4. **Create a Document** — Admin → ID Documents → Documents → Add. Select the type and country, enter a version label.
5. **Add DocumentAttributes** inline on the Document form — select an Attribute from the dropdown and enter the region JSON.

---

## Developer reference

The OCR engine looks up extraction configuration as follows:

```python
from hope_ocr.archive.models import Document, DocumentAttribute

doc = Document.objects.get(document_type=dt, country=country, version="2019")
attrs = DocumentAttribute.objects.filter(document=doc).select_related("attribute")
# attrs[i].attribute.name  → field name
# attrs[i].region          → bounding box dict
```

The `version` value must be known at processing time — typically determined by a prior document-type identification step or passed explicitly by the caller.
