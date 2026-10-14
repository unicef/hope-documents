# Architecture

This section describes the architecture of the HOPE Documents project.

## Overview

HOPE Documents is a Django application designed for document processing and OCR. It is structured into several key components:

-   **`hope_documents.archive`**: A Django app responsible for storing and managing document configuration. It includes Django models, admin configurations, and migrations.

-   **`hope_documents.ocr`**: This is the core component for OCR processing. It contains:
    -   `engine.py`: The main OCR engine, likely using Tesseract and OpenCV.
    -   `__cli__.py`: Implements the command-line interface for batch processing.
    -   `loaders.py`: Likely responsible for loading documents from different sources.
    -   `reader.py`: Reads the content of the documents.

-   **`hope_documents.utils`**: A collection of utility modules for common tasks such as image manipulation, language detection, logging, and performance timing.

## Domain model

The `archive` app contains two independent layers:

**Configuration layer** — defines *which fields exist* for a given document type, country and version:

```
Country ──────────────────┐
                          ▼
DocumentType ────────► Document ──► DocumentAttribute ──► Attribute
                       (version)        (region)
```

- `Country` and `DocumentType` are the base reference objects.
- `Document` groups a `DocumentType`, `Country` and free-text `version` together. The version labels a set of extractable attributes (e.g. all attributes valid for Italian driving licences issued after 2019).
- `Attribute` is a catalog of extractable field names (`first_name`, `last_name`, `number` are built-in system attributes).
- `DocumentAttribute` links one `Attribute` to a `Document` and stores the bounding-box `region` on the document image where the value should be extracted.

**Processing layer** (existing) — validates extracted values at runtime:

- `DocumentRule` links a `Country` and `DocumentType` and holds regex patterns used by the OCR engine to validate number formats. It is independent of the configuration layer above.

## Technologies

-   **Backend Framework**: Django
-   **OCR Engine**: Tesseract, with image processing capabilities provided by OpenCV.
-   **Command-Line Interface**: Click
