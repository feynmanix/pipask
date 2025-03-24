import asyncio
import logging
import os
from contextlib import aclosing
from typing import Awaitable

from rich.prompt import Confirm
from pipask.checks.repo_popularity import check_repo_popularity
from pipask.checks.types import CheckResult
from pipask.cli_helpers import ParsedArgs, CheckTask
from pipask.infra.pip import pip_pass_through, get_pip_report
from pipask.infra.pypi import PypiClient, ReleaseResponse
import sys

import click
from rich.console import Console

from pipask.infra.repo_client import RepoClient
from pipask.cli_helpers import SimpleTaskProgress
from pipask.infra.pip import PipReport
from rich.logging import RichHandler

from pipask.report import print_report

console = Console()

# Get log level from environment variable, default to INFO if not set
pipask_log_level = os.getenv("PIPASK_LOG_LEVEL", "INFO").upper()
log_format = "%(name)s - %(message)s"
logging.basicConfig(level=logging.WARNING, format=log_format, handlers=[RichHandler(console=console)])
logging.getLogger("pipask").setLevel(getattr(logging, pipask_log_level, logging.INFO))


# (see relevant pip commands at https://pip.pypa.io/en/stable/cli/pip_install/)
@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option("-h", "--help", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--no-deps", is_flag=True)
@click.option("--report", type=str)
@click.pass_context
def cli(ctx: click.Context, help: bool, dry_run: bool, report: str, no_deps: bool) -> None:
    """pipask - safer python package installation with audit and consent."""
    all_args = sys.argv[1:]
    is_install_command = len(ctx.args) > 0 and ctx.args[0] == "install"

    if not is_install_command or help or dry_run:
        # Only run when actually installing something
        pip_pass_through(all_args)
        return

    with SimpleTaskProgress(console=console) as progress:
        pip_report_task = progress.add_task("Resolving dependencies to install with pip")
        try:
            pip_report = get_pip_report(ParsedArgs.from_click_context(ctx))
            pip_report_task.update(True)
        except Exception as e:
            pip_report_task.update(False)
            raise e
        check_results = asyncio.run(execute_checks(pip_report, progress))
    print_report(check_results, console)

    if Confirm.ask("\n[green]?[/green] Would you like to continue installing package(s)?"):
        pip_pass_through(all_args)
    else:
        click.echo("Aborted!")
        sys.exit(2)


async def execute_checks(pip_report: PipReport, progress: SimpleTaskProgress) -> list[CheckResult]:
    packages_to_install = [package for package in pip_report.install if package.requested]
    async with aclosing(PypiClient()) as pypi_client, aclosing(RepoClient()) as repo_client:
        # TODO: create in advance
        repo_popularity_task: CheckTask = progress.add_task(
            "Checking repository popularity", total=len(packages_to_install)
        )
        releases_info_futures: list[Awaitable[ReleaseResponse | None]] = [
            asyncio.create_task(pypi_client.get_release_info(package.metadata.name, package.metadata.version))
            for package in packages_to_install
        ]

        check_result_futures = []
        for package, releases_info_future in zip(packages_to_install, releases_info_futures):
            check_result_future = asyncio.create_task(check_repo_popularity(package, releases_info_future, repo_client))
            check_result_future.add_done_callback(lambda f: repo_popularity_task.update(f.result().result_type))
            check_result_futures.append(check_result_future)

        return await asyncio.gather(*check_result_futures)


if __name__ == "__main__":
    cli()
