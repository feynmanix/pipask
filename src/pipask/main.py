import asyncio
import logging
import os
import sys
from contextlib import aclosing
from typing import Awaitable

from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Confirm

from pipask.checks.license import LicenseChecker
from pipask.checks.package_age import PackageAge
from pipask.checks.package_downloads import PackageDownloadsChecker
from pipask.checks.release_metadata import ReleaseMetadataChecker
from pipask.checks.repo_popularity import RepoPopularityChecker
from pipask.checks.types import CheckResult
from pipask.checks.vulnerabilities import ReleaseVulnerabilityChecker
from pipask.cli_args import InstallArgs
from pipask.cli_helpers import SimpleTaskProgress
from pipask.exception import PipAskResolutionException, HandoverToPipException
from pipask.infra.pip import (
    InstallationReportItem,
    PipInstallReport,
    get_pip_install_report_from_pypi,
    get_pip_install_report_unsafe,
    parse_pip_arguments,
    parse_pip_install_arguments,
    pip_pass_through,
)
from pipask.infra.pypi import PypiClient, ReleaseResponse
from pipask.infra.pypistats import PypiStatsClient
from pipask.infra.repo_client import RepoClient
from pipask.infra.vulnerability_details import OsvVulnerabilityDetailsService
from pipask.report import print_report

console = Console()

# Get log level from environment variable, default to INFO if not set
pipask_log_level = os.getenv("PIPASK_LOG_LEVEL", "INFO").upper()
log_format = "%(name)s - %(message)s"
logging.basicConfig(level=logging.WARNING, format=log_format, handlers=[RichHandler(console=console)])
logging.getLogger("pipask").setLevel(getattr(logging, pipask_log_level, logging.INFO))


def main(args: list[str] | None = None) -> None:
    if args is None:
        args = sys.argv[1:]

    # Parse arguments
    # And short-circuit to pip if this is not an installation command
    try:
        parsed_args = parse_pip_arguments(args)
    except HandoverToPipException:
        pip_pass_through(args)
        return

    if parsed_args.command_name != "install":
        pip_pass_through(args)
        return

    install_args = parse_pip_install_arguments(parsed_args)
    if install_args.help or install_args.version:
        pip_pass_through(args)
        return

    check_results = None
    with SimpleTaskProgress(console=console) as progress:
        pip_report_task = progress.add_task("Resolving dependencies to install")
        try:
            pip_report = get_pip_install_report_with_consent(install_args)
            pip_report_task.update(True)
        except Exception as e:
            pip_report_task.update(False)
            raise e

        requested_packages = [package for package in pip_report.install if package.requested]
        if len(requested_packages) > 0:
            check_results = asyncio.run(execute_checks(requested_packages, progress))

    if len(requested_packages) == 0:
        console.print("  No new packages to install\n")
        pip_pass_through(parsed_args.raw_args)
        return
    elif check_results is None:
        raise Exception("No checks were performed. Aborting.")

    # Intentionally printing report after the progress monitor is closed
    # to make sure the progress bars are displayed as completed
    print_report(check_results, console)
    if Confirm.ask("\n[green]?[/green] Would you like to continue installing package(s)?"):
        pip_pass_through(parsed_args.raw_args)
    else:
        console.print("[yellow]Aborted!")
        sys.exit(2)


def get_pip_install_report_with_consent(args: InstallArgs) -> PipInstallReport:
    try:
        return get_pip_install_report_from_pypi(args)
    except PipAskResolutionException as e:
        message_formatted = f" ({e.message})" if e.message else ""
        console.print(
            f"[yellow]Unable to resolve dependencies without preparing a source distribution{message_formatted}\n"
            + "Trying to resolve dependencies with pip - note that this may execute 3rd party code before pipask can run checks[/yellow]"
        )
        # TODO: ask for consent if configured to do so
        return get_pip_install_report_unsafe(args)


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
    main()
