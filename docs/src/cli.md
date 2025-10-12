# Command Line

HOPE Documents provides a command-line interface to extract text from documents.

```bash
extract [OPTIONS] FILEPATHS...
```

## Arguments

-   `FILEPATHS...`: One or more paths to files or directories to process.

## Options

-   `-a`, `--auto`: Automatic mode.
-   `-t`, `--threshold`: CV2 threshold value (0-255). Default is 128.
-   `-p`, `--psm`: Tesseract Page Segmentation Mode (0-13). Default is 11.
-   `-o`, `--oem`: Tesseract OCR Engine Mode (0-3). Default is 3.
-   `-n`, `--number-only`: Only extract numbers from the documents.
-   `--debug`: Enable debug mode.

## Example

```bash
extract tests/images/ita/ci1.png
```

This will output the extracted text from the `ci1.png` image.
