from typing import Any

from pipc.main import cli, ParsedArgs

import pytest


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
    ctx = cli.make_context("pipc", args)
    parsed_args = ParsedArgs.from_click_context(ctx)
    assert parsed_args.other_args == expected_positional
    assert parsed_args.help == expected_options["help"]
    assert parsed_args.dry_run == expected_options["dry_run"]
    assert parsed_args.report == expected_options["report"]

