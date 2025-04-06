from dataclasses import dataclass
from optparse import Values


@dataclass
class PipCommandArgs:
    command_name: str
    command_args: list[str]
    raw_args: list[str]


class InstallArgs:
    raw_args: list[str]
    options: Values
    install_args: list[str]
    help: bool
    version: bool
    dry_run: bool
    json_report_file: str | None

    def __init__(self, raw_args: list[str], raw_options: Values, install_args: list[str]) -> None:
        self.raw_args = raw_args
        self.options = raw_options
        self.install_args = install_args

        self.help = getattr(raw_options, "help", False)
        self.version = getattr(raw_options, "version", False)
        self.dry_run = getattr(raw_options, "dry_run", False)
        self.json_report_file = getattr(raw_options, "json_report_file", None)
