import os
import subprocess
import venv
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from pipask.main import ParsedArgs, cli, main


@pytest.mark.parametrize(
    "args,expected_positional,expected_options",
    [
        (
            ["--help"],
            [],  #
            {"help": True, "dry_run": False, "report": None},
        ),
        (
            ["--dry-run", "--report", "output.txt", "--unknown", "unknown"],
            ["--unknown", "unknown"],
            {"help": False, "dry_run": True, "report": "output.txt"},
        ),
        (
            ["--report", "output.txt"],
            [],  #
            {"help": False, "dry_run": False, "report": "output.txt"},
        ),
        (
            ["install", "package"],
            ["install", "package"],  #
            {"help": False, "dry_run": False, "report": None},
        ),
        (
            ["unknown", "command", "--unknown-option"],
            ["unknown", "command", "--unknown-option"],
            {"help": False, "dry_run": False, "report": None},
        ),
        (
            ["install", "--", "--help"],
            ["install", "--help"],  #
            {"help": False, "dry_run": False, "report": None},
        ),
    ],
)
def test_parses_cli_args(args: list[str], expected_positional: list[str], expected_options: dict[str, Any]):
    ctx = cli.make_context("pipask", args)
    parsed_args = ParsedArgs.from_click_context(ctx)
    assert parsed_args.other_args == expected_positional
    assert parsed_args.help == expected_options["help"]
    assert parsed_args.dry_run == expected_options["dry_run"]
    assert parsed_args.report == expected_options["report"]


@pytest.mark.integration
def test_installs_package_in_venv(tmp_path: Path):
    # Prepare virtual environment
    venv_path = tmp_path / "venv"
    env_builder = venv.EnvBuilder(with_pip=True, system_site_packages=False)
    venv_ctx = env_builder.ensure_directories(venv_path)
    env_builder.create(venv_path)
    venv_python: str = venv_ctx.env_exe

    # Prepare arguments
    args = ["install", "--no-input", "pyfluent-iterables"]
    click_ctx = cli.make_context("pipask", list(args))
    parsed_args = ParsedArgs.from_click_context(click_ctx)
    parsed_args.raw_args = list(args)

    # "Activate" the virtual environment
    path_env_var = str(venv_path / "bin") + os.pathsep + os.environ["PATH"]
    with patch.dict(os.environ, {"PATH": path_env_var, "VIRTUAL_ENV": str(venv_path)}):
        # Act
        with patch("rich.prompt.Confirm.ask", return_value=True):
            main(parsed_args)

    # Verify the package is actually installed in the venv
    assert is_installed(venv_python, "pyfluent_iterables")


def is_installed(executable: str, package_name: str) -> bool:
    result = subprocess.run(
        [executable, "-c", f"import {package_name.replace('-', '_')}"], check=False, capture_output=True, text=True
    )
    return result.returncode == 0
