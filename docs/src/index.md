# Hope Documents

[![Test](https://github.com/unicef/hope-documents/actions/workflows/test.yml/badge.svg)](https://github.com/unicef/hope-documents/actions/workflows/test.yml)
[![Lint](https://github.com/unicef/hope-documents/actions/workflows/lint.yml/badge.svg)](https://github.com/unicef/hope-documents/actions/workflows/lint.yml)
[![codecov](https://codecov.io/github/unicef/hope-documents/graph/badge.svg?token=NPQU3MC9PL)](https://codecov.io/github/unicef/hope-documents)
[![Documentation](https://github.com/unicef/hope-documents/actions/workflows/docs.yml/badge.svg)](https://unicef.github.io/hope-documents/)
[![Pypi](https://badge.fury.io/py/hope-documents.svg)](https://badge.fury.io/py/hope-documents)

Hope Documents is a Django-based application for automated identity document scanning and structured field extraction using OCR.

The system processes uploaded document images, extracts named field values (e.g. `first_name`, `document_number`) using configurable per-field extraction regions, and returns structured JSON — synchronously or via an async Celery pipeline with an optional webhook callback.

## Features

-   **OCR Processing**: Extracts text from document images using Tesseract and OpenCV.
-   **Structured extraction**: Returns per-field values rather than raw text, driven by a configurable document catalog.
-   **Command-Line Interface**: Easy-to-use CLI for development, batch processing, and OCR debugging.
-   **Configurable OCR Engine**: Options to fine-tune Tesseract and OpenCV parameters for better results.
-   **Django Integration**: Seamlessly integrates with Django projects.

## License

This project is licensed under the MIT License.
