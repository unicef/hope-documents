# Contributing to Hope Documents

We welcome contributions to Hope Documents! This guide will help you get started with setting up your development environment.

## Cloning the Repository

First, clone the repository to your local machine:

```bash
git clone https://github.com/unicef/hope-documents.git
cd hope-documents
```

## Development Environment

We use `tox` to manage the development environment and ensure consistency. Make sure you have `tox` installed:

```bash
pip install tox
```

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

### Building the Documentation

To build the documentation locally, use:

```bash
tox docs
```

The documentation will be generated in the `~build/docs` directory.
