# Hope Documents

[![Test](https://github.com/unicef/hope-documents/actions/workflows/test.yml/badge.svg)](https://github.com/unicef/hope-documents/actions/workflows/test.yml)
[![Lint](https://github.com/unicef/hope-documents/actions/workflows/lint.yml/badge.svg)](https://github.com/unicef/hope-documents/actions/workflows/lint.yml)
[![codecov](https://codecov.io/github/unicef/hope-documents/graph/badge.svg?token=NPQU3MC9PL)](https://codecov.io/github/unicef/hope-documents)
[![Documentation](https://github.com/unicef/hope-documents/actions/workflows/docs.yml/badge.svg)](https://unicef.github.io/hope-documents/)
[![Pypi](https://badge.fury.io/py/hope-documents.svg)](https://badge.fury.io/py/hope-documents)

Hope Documents is a Django-based application for automated document scanning and text analysis.
Its primary purpose is to validate document number consistency, ensuring that identifiers (such as IDs, registration numbers, or codes) detected in document images match the expected reference values.

The system processes uploaded images, extracts textual information using OCR, and searches for the provided number or ID within the document’s contents.
This enables reliable, automated verification of official documents such as ID cards, invoices, and certificates.


## Features

-   **OCR Processing**: Extracts text from various image formats and PDF files.
-   **Command-Line Interface**: Easy-to-use CLI for batch processing of documents.
-   **Configurable OCR Engine**: Options to fine-tune Tesseract and OpenCV parameters for better results.
-   **Django Integration**: Seamlessly integrates with Django projects.

## License

This project is licensed under the MIT License.
