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

    # Typed values from `options`:
    help: bool
    version: bool
    dry_run: bool
    json_report_file: str | None
    quiet: int
    verbose: int
    upgrade: bool
    upgrade_strategy: str
    target_dir: str | None
    isolated: bool

    def __init__(self, raw_args: list[str], raw_options: Values, install_args: list[str]) -> None:
        self.raw_args = raw_args
        self.options = raw_options
        self.install_args = install_args

        self.help = getattr(raw_options, "help", False)
        self.version = getattr(raw_options, "version", False)
        self.dry_run = getattr(raw_options, "dry_run", False)
        self.json_report_file = getattr(raw_options, "json_report_file", None)
        self.quiet = getattr(raw_options, "quiet", 0)
        self.verbose = getattr(raw_options, "verbose", 0)
        self.upgrade = getattr(raw_options, "upgrade", False)
        self.upgrade_strategy = getattr(raw_options, "upgrade_strategy", "only-if-needed")
        self.target_dir = getattr(raw_options, "target_dir", None)
        self.isolated = "--isolated" in raw_args
