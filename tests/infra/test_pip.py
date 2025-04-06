from optparse import Values

import pytest

from pipask.cli_args import InstallArgs
from pipask.exception import HandoverToPipException
from pipask.infra.pip import (
    get_pip_install_report_unsafe,
    parse_pip_arguments,
    parse_pip_install_arguments,
)


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
