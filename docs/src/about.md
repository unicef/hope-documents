# About

HOPE Documents is a Django-based application for scanning and processing identity documents to extract structured data using OCR, with optional LLM-assisted fallback extraction.

It provides:

- **REST API** — submit a document image for analysis and retrieve extracted field values as JSON. Supports synchronous (inline) and asynchronous (Celery-backed) processing with an optional callback URL.
- **Admin catalog UI** — configure which document types, countries, attributes, and extraction regions the system recognises. A built-in canvas tool lets operators define per-attribute bounding boxes directly on a reference image.
- **LLM fallback** — when OCR confidence is insufficient, an optional LLM step queries a compatible backend to attempt field extraction from the full document image.
- **CLI** — a `doc` command for development and debugging, with sub-commands for single-image extraction and batch processing.

This documentation covers how to use the REST API, configure the document catalog, and understand the system architecture.
