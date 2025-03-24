from dataclasses import dataclass
import click


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