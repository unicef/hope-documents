# Command-Line Interface

Hope Documents provides a `doc` command for development and debugging. It has three sub-commands:

- **`extract`** — extract text from one or more images
- **`report`** — run extraction across a set of images and produce an accuracy report
- **`inspect`** — detailed per-image OCR analysis

::: mkdocs-click
    :module: hope_documents.ocr.__cli__
    :command: extract

::: mkdocs-click
    :module: hope_documents.ocr.__cli__
    :command: report

::: mkdocs-click
    :module: hope_documents.ocr.__cli__
    :command: inspect
