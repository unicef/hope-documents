# Contributing

To contribute to HOPE Documents, you can follow these steps:

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/unicef/hope-documents.git
    ```

2.  **Install the dependencies**:

    To set up the development environment, you need to have `tox` installed.

3.  **Run the tests**:

    To run the test suite, use the following command:

    ```bash
    tox -e d52-py313
    ```

4.  **Check for code style and linting errors**:

    ```bash
    tox lint
    ```

5.  **Build the documentation**:

    To build the documentation, use the following command:

    ```bash
    tox docs
    ```

    The documentation will be generated in the `~build/docs` directory.
