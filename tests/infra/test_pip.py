import os
from optparse import Values
from pathlib import Path
import subprocess
import tempfile
import shutil

import pytest

from pipask.cli_args import InstallArgs
from pipask.exception import HandoverToPipException
from pipask.infra.pip import (
    InstallationReportItem,
    get_pip_install_report_unsafe,
    parse_pip_arguments,
    parse_pip_install_arguments,
    get_pip_install_report_from_pypi,
    PipInstallReport,
)
from tests.conftest import with_venv_python

temp_venv_python = pytest.fixture(scope="module")(with_venv_python)


@pytest.fixture
def data_dir():
    """Return the path to the test data directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return Path(current_dir) / "data"


@pytest.mark.integration
async def test_pip_resolves_package_to_install():
    args = ["install", "pyfluent-iterables>1.1.0,<1.3.0"]
    report = get_pip_install_report_unsafe(
        InstallArgs(raw_args=args, raw_options=Values(), install_args=["pyfluent-iterables>1.1.0,<1.3.0"]),
    )
    assert report is not None
    assert len(report.install) == 1
    assert report.install[0].pinned_requirement == "pyfluent-iterables==1.2.0"


def test_parse_pip_arguments_normal_command():
    args = ["install", "requests", "--upgrade"]
    result = parse_pip_arguments(args)

    assert result.command_name == "install"
    assert result.command_args == ["requests", "--upgrade"]
    assert result.raw_args == args


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["help"],
        ["nonexistent"],
        ["--version"],
        ["--version", "install"],
    ],
)
def test_parse_pip_arguments_handover_to_pip(args: list[str]):
    with pytest.raises(HandoverToPipException) as exc_info:
        parse_pip_arguments(args)
    assert str(exc_info.value)


def test_parse_pip_arguments_complex_command():
    args = ["--isolated", "install", "requests", "flask", "--upgrade", "--no-deps"]
    result = parse_pip_arguments(args)

    assert result.command_name == "install"
    assert result.command_args == ["--isolated", "requests", "flask", "--upgrade", "--no-deps"]
    assert result.raw_args == args


def test_parse_pip_install_arguments_basic():
    args = ["--timeout", "9", "install", "flask", "--upgrade"]
    parsed_args = parse_pip_arguments(args)

    result = parse_pip_install_arguments(parsed_args)

    assert result.raw_args == args
    assert result.install_args == ["flask"]
    assert result.options.upgrade  # type: ignore
    assert not result.options.isolated_mode  # type: ignore
    assert result.options.timeout == 9  # type: ignore
    assert not result.help
    assert not result.version
    assert not result.dry_run
    assert result.json_report_file is None


def test_parse_pip_install_arguments_with_options():
    args = ["--help", "install", "--isolated", "flask", "pydantic>2.0.0", "--version", "--dry-run", "--report", "-"]
    parsed_args = parse_pip_arguments(args)

    result = parse_pip_install_arguments(parsed_args)

    assert result.raw_args == args
    assert result.install_args == ["flask", "pydantic>2.0.0"]
    assert result.options.isolated_mode  # type: ignore
    assert result.help
    assert result.version
    assert result.dry_run
    assert result.json_report_file == "-"


# @pytest.mark.integration
def test_install_report_simple_pypi_package(temp_venv_python):
    """Test installing a simple package from PyPI."""
    assert temp_venv_python
    args = _to_parsed_args(["install", "--isolated", "pyfluent-iterables==2.0.1"])

    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) == 1
    _assert_metadata(report.install[0], "pyfluent-iterables", "2.0.1")
    _assert_download_info(report.install[0], "https://files.pythonhosted.org", "pyfluent_iterables-2.0.1-py3-none-any.whl")
    expected = get_pip_install_report_unsafe(args)
    assert report == expected


# @pytest.mark.integration
def test_install_report_source_only_pypi_package(temp_venv_python):
    """Test installing a source only package."""
    assert temp_venv_python
    args = _to_parsed_args(["install", "--isolated", "fire==0.7.0"])

    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) >= 1
    install_item = [i for i in report.install if i.requested][0]
    _assert_metadata(install_item, "fire", "0.7.0")
    _assert_download_info(install_item, "https://files.pythonhosted.org", "fire-0.7.0.tar.gz")
    expected = get_pip_install_report_unsafe(args)
    for i in report.install:
        i.metadata.classifier = []
    for i in expected.install:
        i.metadata.classifier = []
    assert report == expected


def _to_parsed_args(args: list[str]) -> InstallArgs:
    parsed_args = parse_pip_arguments(args)
    assert parsed_args.command_name == "install"
    return parse_pip_install_arguments(parsed_args)


def _assert_metadata(install_item: InstallationReportItem, expected_name: str, expected_version: str):
    assert install_item.metadata.name == expected_name
    assert install_item.metadata.version == expected_version


def _assert_download_info(
    install_item: InstallationReportItem, expected_url_prefix: str, expected_url_suffix: str | None = None
):
    assert install_item.download_info is not None
    assert install_item.download_info.url.startswith(expected_url_prefix)
    if expected_url_suffix is None:
        expected_url_suffix = expected_url_prefix
    assert install_item.download_info.url.endswith(expected_url_suffix)
