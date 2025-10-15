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

## Installation

To install Hope Documents, you can use pip:

```bash
pip install hope-documents
```

## Usage

Hope Documents provides a command-line interface to extract text from documents.

```bash
extract [OPTIONS] FILEPATHS...
```

### Arguments

-   `FILEPATHS...`: One or more paths to files or directories to process.

### Options

-   `-a`, `--auto`: Automatic mode.
-   `-t`, `--threshold`: CV2 threshold value (0-255). Default is 128.
-   `-p`, `--psm`: Tesseract Page Segmentation Mode (0-13). Default is 11.
-   `-o`, `--oem`: Tesseract OCR Engine Mode (0-3). Default is 3.
-   `-n`, `--number-only`: Only extract numbers from the documents.
-   `--debug`: Enable debug mode.

### Example

```bash
extract tests/images/ita/ci1.png
```

This will output the extracted text from the `ci1.png` image.

## Development

To set up the development environment, you need to have `tox` installed.

### Running Tests

To run the test suite, use the following command:

```bash
tox -e d52-py313
```

### Linting

To check for code style and linting errors, run:

```bash
tox lint
```

### Documentation

To build the documentation, use the following command:

```bash
tox docs
```

The documentation will be generated in the `site` directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
