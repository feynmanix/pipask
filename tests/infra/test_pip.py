import os
import shutil
import signal
import socket
import subprocess
from contextlib import contextmanager

import tarfile
import time
from optparse import Values
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from packaging.version import Version
from resolvelib import ResolutionImpossible

from pipask._vendor.pip._internal.exceptions import DistributionNotFound, InstallationError
from pipask._vendor.pip._internal.utils.urls import path_to_url
from pipask.cli_args import InstallArgs
from pipask.code_execution_guard import PackageCodeExecutionGuard
from pipask.exception import HandoverToPipException
from pipask.infra.executables import get_pip_command
from pipask.infra.pip import (
    get_pip_install_report_from_pypi,
    get_pip_install_report_unsafe,
    parse_pip_arguments,
    parse_pip_install_arguments,
)
from pipask.infra.pip_types import InstallationReportItem, PipInstallReport
from tests.conftest import with_venv_python

temp_venv_python_shared = pytest.fixture(scope="module")(with_venv_python)


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
    assert report.install[0].metadata.name == "pyfluent-iterables"
    assert report.install[0].metadata.version == "1.2.0"


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


@pytest.mark.integration
def test_install_report_simple_pypi_package(temp_venv_python_shared, clear_venv_dependent_caches):
    """Test installing a simple package from PyPI."""
    args = _to_parsed_args(["install", "--isolated", "pyfluent-iterables==2.0.1"])

    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) == 1
    _assert_metadata(report.install[0], "pyfluent-iterables", "2.0.1")
    _assert_download_info(
        report.install[0], "https://files.pythonhosted.org", "pyfluent_iterables-2.0.1-py3-none-any.whl"
    )
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_source_only_pypi_package(temp_venv_python_shared, clear_venv_dependent_caches):
    """Test installing a source only package."""
    args = _to_parsed_args(["install", "--isolated", "fire==0.7.0"])

    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) >= 1
    install_item = [i for i in report.install if i.requested][0]
    _assert_metadata(install_item, "fire", "0.7.0")
    _assert_download_info(install_item, "https://files.pythonhosted.org", "fire-0.7.0.tar.gz")
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_wheel(temp_venv_python_shared, clear_venv_dependent_caches, data_dir):
    """Test installing a wheel package from local file."""
    wheel_path = os.fspath(data_dir / "pyfluent_iterables-2.0.1-py3-none-any.whl")
    args = _to_parsed_args(["install", wheel_path])

    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) == 1
    _assert_metadata(report.install[0], "pyfluent-iterables", "2.0.1")
    _assert_download_info(report.install[0], path_to_url(wheel_path))
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_sdist(temp_venv_python_shared, clear_venv_dependent_caches, data_dir, monkeypatch):
    """Test installing a source distribution package."""
    sdist_path = os.fspath(data_dir / "pyfluent_iterables-2.0.1.tar.gz")
    args = _to_parsed_args(["install", sdist_path])
    mock_guard = MagicMock()
    monkeypatch.setattr(PackageCodeExecutionGuard, "check_execution_allowed", mock_guard)

    report = get_pip_install_report_from_pypi(args)

    mock_guard.assert_any_call(None, path_to_url(sdist_path))
    assert len(report.install) == 1
    _assert_metadata(report.install[0], "pyfluent-iterables", "2.0.1")
    _assert_download_info(report.install[0], path_to_url(sdist_path))
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
@pytest.mark.parametrize("upgrade", [True, False])
def test_install_report_respects_upgrade(temp_venv_python, upgrade, data_dir, clear_venv_dependent_caches):
    assert temp_venv_python
    subprocess.check_call(get_pip_command() + ["install", "pyfluent-iterables==1.2.0"])
    clear_venv_dependent_caches()  # pkg_resources needs to be refreshed to pick up the new dependency
    upgrade_opt = ["--upgrade"] if upgrade else []
    args = _to_parsed_args(["install", "--isolated", *upgrade_opt, "pyfluent-iterables<=2.0.1"])
    report = get_pip_install_report_from_pypi(args)

    if upgrade:
        assert len(report.install) == 1
        assert report.install[0].metadata.name == "pyfluent-iterables"
        version = Version(report.install[0].metadata.version)
        assert version > Version("1.2.0")
        _assert_metadata(report.install[0], "pyfluent-iterables", "2.0.1")
    else:
        assert len(report.install) == 0
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_from_vcs(temp_venv_python_shared, clear_venv_dependent_caches, monkeypatch):
    vcs_url = "git+https://github.com/feynmanix/pyfluent-iterables@1.2.0"
    args = _to_parsed_args(["install", vcs_url])

    mock_guard = MagicMock()
    monkeypatch.setattr(PackageCodeExecutionGuard, "check_execution_allowed", mock_guard)

    report = get_pip_install_report_from_pypi(args)

    mock_guard.assert_any_call(None, vcs_url)
    assert len(report.install) == 1
    _assert_metadata(report.install[0], "pyfluent-iterables", "1.2.0")
    _assert_download_info(report.install[0], "https://github.com/feynmanix/pyfluent-iterables")
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_editable(temp_venv_python_shared, clear_venv_dependent_caches, data_dir, monkeypatch):
    package_dir = os.fspath(data_dir / "test-package")
    args = _to_parsed_args(["install", "-e", package_dir])
    mock_guard = MagicMock()
    monkeypatch.setattr(PackageCodeExecutionGuard, "check_execution_allowed", mock_guard)

    report = get_pip_install_report_from_pypi(args)

    mock_guard.assert_any_call(None, path_to_url(package_dir))
    assert len(report.install) == 2

    test_package = next(i for i in report.install if i.metadata.name == "test-package")
    assert test_package.metadata.version == "0.1.0"
    assert test_package.requested
    _assert_download_info(test_package, path_to_url(package_dir))

    dependency_package = next(i for i in report.install if i.metadata.name == "pyfluent-iterables")
    assert Version(dependency_package.metadata.version) >= Version("2.0.0")
    assert not dependency_package.requested

    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


def test_install_report_with_hashes(data_dir, temp_venv_python_shared, clear_venv_dependent_caches, tmp_path):
    wheel_path = data_dir / "pyfluent_iterables-2.0.1-py3-none-any.whl"
    import hashlib

    with open(wheel_path, "rb") as f:
        sha256_hash = hashlib.sha256(f.read()).hexdigest()
    requirements_file = tmp_path / "requirements.txt"
    with open(requirements_file, "w") as f:
        f.write(f"{os.fspath(wheel_path)} --hash=sha256:{sha256_hash}\n")

    args = _to_parsed_args(["install", "--require-hashes", "-r", requirements_file.as_posix()])
    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) == 1
    _assert_metadata(report.install[0], "pyfluent-iterables", "2.0.1")
    _assert_download_info(report.install[0], path_to_url(os.fspath(wheel_path)))
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


def test_install_reports_respects_env_vars(
    temp_venv_python_shared, clear_venv_dependent_caches, monkeypatch, tmp_path, data_dir
):
    requirement_file = tmp_path / "requirements.txt"
    requirement_file.write_text((data_dir / "pyfluent_iterables-2.0.1-py3-none-any.whl").as_posix())
    monkeypatch.setenv("PIP_REQUIREMENT", requirement_file.as_posix())
    monkeypatch.setenv("PIP_ISOLATED", "1")

    args = _to_parsed_args(["install"])
    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) == 1
    _assert_metadata(report.install[0], "pyfluent-iterables", "2.0.1")
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


def test_install_report_from_custom_index(temp_venv_python_shared, data_dir, clear_venv_dependent_caches):
    clear_venv_dependent_caches()
    with _start_pypi_server(data_dir) as port:
        args = _to_parsed_args(
            [
                "install",
                "pyfluent-iterables",
                "--isolated",
                "--index-url",
                f"http://127.0.0.1:{port}/simple/",
                "--trusted-host",
                "127.0.0.1",
            ]
        )

        report = get_pip_install_report_from_pypi(args)

        assert len(report.install) >= 1
        install_item = [i for i in report.install if i.requested][0]
        _assert_metadata(install_item, "pyfluent-iterables", "2.0.1")
        _assert_download_info(
            install_item, f"http://127.0.0.1:{port}/packages/pyfluent_iterables-2.0.1-py3-none-any.whl"
        )
        expected = get_pip_install_report_unsafe(args)
        _assert_same_reports(report, expected)


@pytest.mark.integration
@pytest.mark.parametrize("change_hash", [True, False])
def test_install_reports_looks_up_pypi_metadata_only_when_hash_matches(
    tmp_path, monkeypatch, data_dir, change_hash, temp_venv_python_shared, clear_venv_dependent_caches
):
    source_dist = data_dir / "pyfluent_iterables-2.0.1.tar.gz"
    package_dir = tmp_path / "package_dir"
    package_dir.mkdir()

    if change_hash:
        # Extract the source distribution and modify it so that the hash no longer matches pypi metadata
        with tarfile.open(source_dist, "r:gz") as tar:
            tar.extractall(tmp_path)
        extracted_dir = tmp_path / "pyfluent_iterables-2.0.1"
        (extracted_dir / "new_file.txt").write_text("file that changes the package hash")

        # Recompress
        new_tar = package_dir / "pyfluent_iterables-2.0.1.tar.gz"
        with tarfile.open(new_tar, "w:gz") as tar:
            tar.add(extracted_dir, arcname=extracted_dir.name)
    else:
        # Use the original source distribution with the same hash as it has in PyPI
        shutil.copy(source_dist, package_dir / "pyfluent_iterables-2.0.1.tar.gz")

    # Serve the (modified) package
    with _start_pypi_server(package_dir) as port:
        args = _to_parsed_args(
            [
                "install",
                "pyfluent-iterables",
                "--isolated",
                "--index-url",
                f"http://127.0.0.1:{port}/simple/",
                "--trusted-host",
                "127.0.0.1",
            ]
        )

        mock_guard = MagicMock()
        monkeypatch.setattr(PackageCodeExecutionGuard, "check_execution_allowed", mock_guard)

        report = get_pip_install_report_from_pypi(args)

        if change_hash:
            # Expect execution guard call because the match did NOT match,
            # and therefore we need to build the source distribution to get metadata
            mock_guard.assert_any_call(
                "pyfluent-iterables", f"http://127.0.0.1:{port}/packages/pyfluent_iterables-2.0.1.tar.gz"
            )
        else:
            # Not called because we fetched the metadata from PyPI
            mock_guard.assert_not_called()

        assert len(report.install) == 1
        _assert_metadata(report.install[0], "pyfluent-iterables", "2.0.1")
        expected = get_pip_install_report_unsafe(args)
        _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_with_constraints(tmp_path, temp_venv_python_shared, clear_venv_dependent_caches):
    constraints_path = tmp_path / "constraints.txt"
    constraints_path.write_text("pyfluent-iterables==1.2.0\n")

    args = _to_parsed_args(["install", "--isolated", "pyfluent-iterables", "-c", constraints_path.as_posix()])

    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) >= 1
    install_item = [i for i in report.install if i.requested][0]
    _assert_metadata(install_item, "pyfluent-iterables", "1.2.0")
    _assert_download_info(install_item, "https://files.pythonhosted.org", "pyfluent_iterables-1.2.0-py3-none-any.whl")
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_handles_invalid_package():
    args = _to_parsed_args(["install", "--isolated", "this-package-does-not-exist-adfcegzq9"])

    with pytest.raises(InstallationError) as exc_info:
        get_pip_install_report_from_pypi(args)

    assert isinstance(exc_info.value.__cause__, ResolutionImpossible)


def test_install_report_handles_conflicting_requirements():
    args = _to_parsed_args(["install", "--isolated", "pyfluent-iterables>2.0.0", "pyfluent-iterables<2.0.0"])

    with pytest.raises(InstallationError) as exc_info:
        get_pip_install_report_from_pypi(args)

    assert isinstance(exc_info.value.__cause__, ResolutionImpossible)


@pytest.mark.integration
def test_install_report_multiple_packages(temp_venv_python_shared, clear_venv_dependent_caches):
    args = _to_parsed_args(["install", "--isolated", "pyfluent-iterables==2.0.1", "fire==0.7.0"])

    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) == 3
    pyfluent = next(i for i in report.install if i.metadata.name == "pyfluent-iterables")
    fire = next(i for i in report.install if i.metadata.name == "fire")
    termcolor = next(i for i in report.install if i.metadata.name == "termcolor")
    _assert_metadata(pyfluent, "pyfluent-iterables", "2.0.1")
    _assert_metadata(fire, "fire", "0.7.0")
    assert pyfluent.requested
    assert fire.requested
    assert not termcolor.requested
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_with_extras(temp_venv_python_shared, clear_venv_dependent_caches):
    args = _to_parsed_args(["install", "--isolated", "requests[socks]==2.32.3"])

    report = get_pip_install_report_from_pypi(args)

    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)
    assert len(report.install) > 2
    pysocks = next(i for i in report.install if i.metadata.name == "PySocks")
    assert pysocks


@pytest.mark.integration
@pytest.mark.parametrize("use_importlib", [True, False])
def test_install_report_works_both_with_pkg_resources_and_importlib(
    temp_venv_python_shared, clear_venv_dependent_caches, monkeypatch, use_importlib
):
    args = _to_parsed_args(["install", "--isolated", "requests[socks]==2.32.3"])
    expected = get_pip_install_report_unsafe(args)
    monkeypatch.setenv("_PIP_USE_IMPORTLIB_METADATA", "1" if use_importlib else "0")

    report = get_pip_install_report_from_pypi(args)

    _assert_same_reports(report, expected)
    assert len(report.install) > 2
    pysocks = next(i for i in report.install if i.metadata.name == "PySocks")
    assert pysocks


@pytest.mark.integration
def test_install_report_with_no_deps(temp_venv_python_shared, clear_venv_dependent_caches):
    args = _to_parsed_args(["install", "--isolated", "--no-deps", "black==25.1.0"])

    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) == 1
    _assert_metadata(report.install[0], "black", "25.1.0")
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_complex_requirement(temp_venv_python_shared, clear_venv_dependent_caches):
    args = _to_parsed_args(
        [
            "install",
            "--isolated",
            "torch==2.6.0",
            "matplotlib==3.10.1",
            "h5py==3.13.0",
            "psycopg[binary]==3.2.6",
            "fastapi[all]",
            "pandas[test]",
        ]
    )

    report = get_pip_install_report_from_pypi(args)

    assert len(report.install) > 4
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_with_egg_fragment(temp_venv_python_shared, clear_venv_dependent_caches, monkeypatch):
    egg_url = "git+https://github.com/feynmanix/pyfluent-iterables@1.2.0#egg=pyfluent-iterables"
    args = _to_parsed_args(["install", egg_url])

    mock_guard = MagicMock()
    monkeypatch.setattr(PackageCodeExecutionGuard, "check_execution_allowed", mock_guard)

    report = get_pip_install_report_from_pypi(args)

    mock_guard.assert_any_call("pyfluent-iterables", "git+https://github.com/feynmanix/pyfluent-iterables@1.2.0")
    assert len(report.install) == 1
    _assert_metadata(report.install[0], "pyfluent-iterables", "1.2.0")
    _assert_download_info(report.install[0], "https://github.com/feynmanix/pyfluent-iterables")
    expected = get_pip_install_report_unsafe(args)
    _assert_same_reports(report, expected)


@pytest.mark.integration
def test_install_report_fails_with_invalid_egg_fragment(clear_venv_dependent_caches, monkeypatch):
    egg_url = "git+https://github.com/feynmanix/pyfluent-iterables@1.2.0#egg=non-matching-name"
    args = _to_parsed_args(["install", egg_url])

    mock_guard = MagicMock()
    monkeypatch.setattr(PackageCodeExecutionGuard, "check_execution_allowed", mock_guard)

    with pytest.raises(DistributionNotFound):
        get_pip_install_report_from_pypi(args)


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


def _normalize_report(report: PipInstallReport):
    report.install = sorted(report.install, key=lambda i: i.metadata.name)
    for i in report.install:
        i.metadata.classifier = sorted(i.metadata.classifier)
        i.metadata.license = i.metadata.license.replace("\r\n", "\n") if i.metadata.license else None


def _assert_same_reports(actual_report: PipInstallReport, expected_report: PipInstallReport):
    _normalize_report(actual_report)
    _normalize_report(expected_report)
    assert actual_report == expected_report


def _get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def _start_pypi_server(package_dir: str | Path):
    port = _get_free_port()
    server_process = subprocess.Popen(
        [
            "pypi-server",
            "run",
            "-p",
            str(port),
            "-i",
            "127.0.0.1",
            "--backend=simple-dir",
            str(package_dir),
        ],
        start_new_session=True,
    )
    try:
        # Give the server a moment to start
        time.sleep(1)
        yield port
    finally:
        # Kill all processes in the session group
        os.kill(server_process.pid, signal.SIGTERM)
        server_process.wait()
