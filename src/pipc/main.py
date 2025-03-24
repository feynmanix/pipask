from dataclasses import dataclass
from pipc.installers.pip import pip_pass_through
import sys

import click

# (see relevant pip commands at https://pip.pypa.io/en/stable/cli/pip_install/)

@dataclass
class ParsedArgs:
    other_args: list[str]
    help: bool
    dry_run: bool
    report: str | None

    @staticmethod
    def from_click_context(ctx: click.Context) -> "ParsedArgs":
        return ParsedArgs(
            other_args=ctx.args,
            help=ctx.params["help"],
            dry_run=ctx.params["dry_run"],
            report=ctx.params["report"] or None,
        )

@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option("-h", "--help", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--report", type=str)
@click.pass_context
def cli(ctx: click.Context, help: bool, dry_run: bool, report: str) -> None:
    """pipc - safer python package installation with audit and consent."""
    all_args = sys.argv[1:]
    is_install_command = len(ctx.args) > 0 and ctx.args[0] == "install"
    if not is_install_command or help or dry_run:
        # Only run when actually installing something
        pip_pass_through(all_args)
        return
    parsed_args = ParsedArgs.from_click_context(ctx)
    execute_checks(parsed_args)
    if click.confirm("Do you want to continue?"):
        pip_pass_through(all_args)
    else:
        click.echo("Aborted!")
        sys.exit(2)


def execute_checks(parsed_args: ParsedArgs) -> None:
    click.echo("Checking stuff...")


if __name__ == "__main__":
    cli()
