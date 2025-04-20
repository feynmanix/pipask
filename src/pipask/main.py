import asyncio
import logging
import os
import sys
from contextlib import aclosing

from httpx import HTTPError
from rich import traceback as rich_traceback
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Confirm

import pipask._vendor.pip._internal.exceptions
import pipask._vendor.pip._internal.utils.logging
from pipask.checks.checks_executor import ChecksExecutor
from pipask.checks.types import PackageCheckResults
from pipask.cli_args import InstallArgs
from pipask.cli_helpers import CheckTask, SimpleTaskProgress
from pipask.code_execution_guard import PackageCodeExecutionGuard
from pipask.exception import HandoverToPipException, PipAskCodeExecutionDeniedException
from pipask.infra.pip import (
    get_pip_install_report_from_pypi,
    parse_pip_arguments,
    parse_pip_install_arguments,
    pip_pass_through,
)
from pipask.infra.pip_types import InstallationReportItem, PipInstallReport
from pipask.infra.pypi import PypiClient
from pipask.infra.pypistats import PypiStatsClient
from pipask.infra.repo_client import RepoClient
from pipask.infra.vulnerability_details import OsvVulnerabilityDetailsService
from pipask.report import print_report

console = Console()

# Get log level from environment variable, default to INFO if not set
pipask_log_level = getattr(logging, os.getenv("PIPASK_LOG_LEVEL", "INFO").upper(), logging.INFO)
debug_logging = pipask_log_level < logging.INFO
log_format = "%(name)s - %(message)s"
logging.basicConfig(level=logging.WARNING, format=log_format, handlers=[RichHandler(console=console, show_time=False)])
logging.getLogger("pipask").setLevel(pipask_log_level)
logger = logging.getLogger(__name__)


def main(args: list[str] | None = None) -> None:
    if args is None:
        args = sys.argv[1:]

    try:
        # 1. Parse arguments
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

        # 2. Resolve dependencies
        if debug_logging:
            rich_traceback.install(show_locals=True)
        check_results: list[PackageCheckResults] | None = None
        with SimpleTaskProgress(console=console) as progress:
            pip_report_task = progress.add_task("Resolving dependencies to install")
            try:
                pip_report = get_pip_install_report_with_consent(install_args, pip_report_task)
                pip_report_task.update(True)
            except Exception as e:
                pip_report_task.update(False)
                raise e

            packages_to_install = pip_report.install

            # 3. Run checks on the dependencies to install
            if len(packages_to_install) > 0:
                check_results = asyncio.run(execute_checks(packages_to_install, progress))

        # 4. Either delegate actual installation to pip or abort (based on the checks and user consent)
        if len(packages_to_install) == 0:
            console.print("  No new packages to install\n")
            pip_pass_through(parsed_args.raw_args)
            return
        elif check_results is None:
            console.print("  No checks were performed. Aborting.")
            sys.exit(1)

        # Intentionally printing report after the progress monitor is closed
        # to make sure the progress bars are displayed as completed
        print_report(check_results, console)
        if Confirm.ask("\n[green]?[/green] Would you like to continue installing package(s)?"):
            pip_pass_through(parsed_args.raw_args)
        else:
            console.print("[yellow]Aborted by user.")
            sys.exit(2)
    except (KeyboardInterrupt, PipAskCodeExecutionDeniedException):
        console.print("\n[yellow]Aborted by user.")
    except HTTPError as exc:
        logger.error(f"\nNetwork error when making request to {exc.request.url}")
        logger.debug("Exception information:", exc_info=True)
        sys.exit(1)
    except (
        pipask._vendor.pip._internal.exceptions.InstallationError,
        pipask._vendor.pip._internal.exceptions.UninstallationError,
        pipask._vendor.pip._internal.exceptions.BadCommand,
        pipask._vendor.pip._internal.exceptions.NetworkConnectionError,
    ) as exc:
        logger.error(f"Error: {exc}")
        logger.debug("Exception information:", exc_info=True)
        sys.exit(1)
    except Exception:
        logger.error("Unexpected error", exc_info=True)
        logger.debug("Exception information:", exc_info=True)
        sys.exit(1)


def get_pip_install_report_with_consent(args: InstallArgs, progress_task: CheckTask) -> PipInstallReport:
    pipask._vendor.pip._internal.utils.logging.setup_logging(
        verbosity=1 if debug_logging else -1, no_color=False, user_log_file=None
    )
    # PackageCodeExecutionGuard is the part responsible for asking for user consent;
    # its check_execution_allowed() method should be called on all code paths inside
    # get_pip_install_report_from_pypi() that may execute 3rd party code.
    PackageCodeExecutionGuard.reset_confirmation_state(progress_task)
    return get_pip_install_report_from_pypi(args)


async def execute_checks(
    packages_to_install: list[InstallationReportItem], progress: SimpleTaskProgress
) -> list[PackageCheckResults]:
    async with (
        aclosing(PypiClient()) as pypi_client,
        aclosing(RepoClient()) as repo_client,
        aclosing(PypiStatsClient()) as pypi_stats_client,
        aclosing(OsvVulnerabilityDetailsService()) as vulnerability_details_service,
    ):
        checks_executor = ChecksExecutor(
            pypi_client=pypi_client,
            repo_client=repo_client,
            pypi_stats_client=pypi_stats_client,
            vulnerability_details_service=vulnerability_details_service,
        )
        return await checks_executor.execute_checks(packages_to_install, progress)


if __name__ == "__main__":
    main()
