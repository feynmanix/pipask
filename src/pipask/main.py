import asyncio
import logging
import os
from contextlib import aclosing
from typing import Awaitable

from rich.prompt import Confirm

from pipask.checks.license import LicenseChecker
from pipask.checks.repo_popularity import RepoPopularityChecker
from pipask.checks.package_downloads import PackageDownloadsChecker
from pipask.checks.types import CheckResult
from pipask.cli_helpers import ParsedArgs
from pipask.infra.pip import InstallationReportItem, pip_pass_through, get_pip_report
from pipask.infra.pypi import PypiClient, ReleaseResponse
from pipask.infra.pypistats import PypiStatsClient
from pipask.checks.package_age import PackageAge
from pipask.checks.release_metadata import ReleaseMetadataChecker
from pipask.checks.vulnerabilities import ReleaseVulnerabilityChecker
from pipask.infra.vulnerability_details import OsvVulnerabilityDetailsService
import sys

import click
from rich.console import Console

from pipask.infra.repo_client import RepoClient
from pipask.cli_helpers import SimpleTaskProgress
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
    parsed_args = ParsedArgs.from_click_context(ctx)
    main(parsed_args)


def main(args: ParsedArgs):
    is_install_command = len(args.other_args) > 0 and args.other_args[0] == "install"

    if not is_install_command or args.help:
        # Only run when actually installing something
        pip_pass_through(args.raw_args)
        return

    check_results = None
    with SimpleTaskProgress(console=console) as progress:
        pip_report_task = progress.add_task("Resolving dependencies to install with pip")
        try:
            pip_report = get_pip_report(args)
            pip_report_task.update(True)
        except Exception as e:
            pip_report_task.update(False)
            raise e

        requested_packages = [package for package in pip_report.install if package.requested]
        if len(requested_packages) > 0:
            check_results = asyncio.run(execute_checks(requested_packages, progress))

    if len(requested_packages) == 0:
        console.print("  No new packages to install\n")
        pip_pass_through(args.raw_args)
        return
    elif check_results is None:
        raise Exception("No checks were performed. Aborting.")

    # Intentionally printing report after the progress monitor is closed
    print_report(check_results, console)
    if Confirm.ask("\n[green]?[/green] Would you like to continue installing package(s)?"):
        pip_pass_through(args.raw_args)
    else:
        console.print("[yellow]Aborted!")
        sys.exit(2)


async def execute_checks(
    packages_to_install: list[InstallationReportItem], progress: SimpleTaskProgress
) -> list[CheckResult]:
    async with (
        aclosing(PypiClient()) as pypi_client,
        aclosing(RepoClient()) as repo_client,
        aclosing(PypiStatsClient()) as pypi_stats_client,
        aclosing(OsvVulnerabilityDetailsService()) as vulnerability_details_service,
    ):
        checkers = [
            RepoPopularityChecker(repo_client),
            PackageDownloadsChecker(pypi_stats_client),
            PackageAge(pypi_client),
            ReleaseVulnerabilityChecker(vulnerability_details_service),
            ReleaseMetadataChecker(),
            LicenseChecker(),
        ]

        releases_info_futures: list[Awaitable[ReleaseResponse | None]] = [
            asyncio.create_task(pypi_client.get_release_info(package.metadata.name, package.metadata.version))
            for package in packages_to_install
        ]
        check_result_futures = []
        for checker in checkers:
            progress_task = progress.add_task(checker.description, total=len(packages_to_install))
            for package, releases_info_future in zip(packages_to_install, releases_info_futures):
                check_result_future = asyncio.create_task(checker.check(package, releases_info_future))
                check_result_future.add_done_callback(lambda f, task=progress_task: task.update(f.result().result_type))
                check_result_futures.append(check_result_future)
        return await asyncio.gather(*check_result_futures)


if __name__ == "__main__":
    cli()
