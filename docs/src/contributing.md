# Contributing to Hope Documents

We welcome contributions to Hope Documents! This guide will help you get started with setting up your development environment.

## Cloning the Repository

First, clone the repository to your local machine:

```bash
git clone https://github.com/unicef/hope-documents.git
cd hope-documents
```

## Development Environment

We use `uv` to manage the development environment. Install it from [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/), then install all dependencies:

```bash
uv sync
```

### Running Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check src/
uv run ruff format --check src/
```

### Building the Documentation

```bash
uv run --group docs mkdocs build
```

The documentation will be generated in the `~build/docs` directory.
