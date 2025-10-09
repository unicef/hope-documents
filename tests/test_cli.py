from pathlib import Path

import pytest
from click.testing import CliRunner

from hope_documents.ocr.__cli__ import cli

images_dir = Path(__file__).parent / "images"
valid_image = str(images_dir / "arg" / "id1.png")
invalid_image = str(images_dir / "_invalid" / "_empty.png")
test_data = [
    (valid_image, 0),
    (invalid_image, 1),
    (f"{images_dir}/_invalid/", 1),
    (f"{valid_image} --debug", 0),
    (f"{valid_image} --threshold=100", 0),
    (f"{valid_image} --threshold=100 -n", 0),
]


# Define the pytest_generate_tests hook to generate test cases
def pytest_generate_tests(metafunc):
    if "arguments" in metafunc.fixturenames:
        ids = ["-".join(map(str, x)).replace(str(images_dir), "") for x in test_data]
        metafunc.parametrize("arguments,exit_code", test_data, ids=ids)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_extract_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert not result.stderr
    assert result.exit_code == 0


def test_extract_params(runner: CliRunner, arguments, exit_code) -> None:
    result = runner.invoke(cli, arguments)
    assert result.exit_code == exit_code
