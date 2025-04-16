import asyncio
import logging

from pipask.checks.base_checker import Checker
from pipask.checks.license import LicenseChecker
from pipask.checks.package_age import PackageAge
from pipask.checks.package_downloads import PackageDownloadsChecker
from pipask.checks.release_metadata import ReleaseMetadataChecker
from pipask.checks.repo_popularity import RepoPopularityChecker
from pipask.checks.types import CheckResult, CheckResultType, PackageCheckResults
from pipask.checks.vulnerabilities import ReleaseVulnerabilityChecker
from pipask.cli_helpers import SimpleTaskProgress
from pipask.infra.pip_report import InstallationReportItem
from pipask.infra.pypi import PypiClient, VerifiedPypiReleaseInfo
from pipask.infra.pypistats import PypiStatsClient
from pipask.infra.repo_client import RepoClient
from pipask.infra.vulnerability_details import OsvVulnerabilityDetailsService

logger = logging.getLogger(__name__)


class _CheckProgressTracker:
    def __init__(self, progress: SimpleTaskProgress, checkers: list[Checker], total_count: int):
        self._progress = progress
        self._progress_tasks_by_checker = {
            id(checker): progress.add_task(checker.description, total=total_count) for checker in checkers
        }

    def update_all_checks(self, partial_result: bool | CheckResultType):
        for progress_task in self._progress_tasks_by_checker.values():
            progress_task.update(partial_result)

    def update_check(self, checker: Checker, partial_result: bool | CheckResultType):
        progress_task = self._progress_tasks_by_checker.get(id(checker))
        if progress_task is None:
            logger.warning(f"No progress task found for checker {checker}")
            return
        progress_task.update(partial_result)


class ChecksExecutor:
    def __init__(
        self,
        *,
        pypi_client: PypiClient,
        repo_client: RepoClient,
        pypi_stats_client: PypiStatsClient,
        vulnerability_details_service: OsvVulnerabilityDetailsService,
    ):
        self._pypi_client = pypi_client
        self._checkers = [
            RepoPopularityChecker(repo_client),
            PackageDownloadsChecker(pypi_stats_client),
            PackageAge(pypi_client),
            ReleaseVulnerabilityChecker(vulnerability_details_service),
            ReleaseMetadataChecker(),
            LicenseChecker(),
        ]

    async def execute_checks(
        self, packages_to_install: list[InstallationReportItem], progress: SimpleTaskProgress
    ) -> list[PackageCheckResults]:
        check_progress_tracker = _CheckProgressTracker(progress, self._checkers, len(packages_to_install))
        return await asyncio.gather(
            *[self._check_package(package, check_progress_tracker) for package in packages_to_install]
        )

    async def _check_package(
        self,
        unverified_metadata: InstallationReportItem,
        check_progress_tracker: _CheckProgressTracker,
    ) -> PackageCheckResults:
        release_info = await self._pypi_client.get_matching_release_info(unverified_metadata)

        if release_info is None:
            # We don't have any trusted release information from PyPI available, we can't run any checks
            check_progress_tracker.update_all_checks(CheckResultType.FAILURE)
            return PackageCheckResults(
                name=unverified_metadata.metadata.name,
                version=unverified_metadata.metadata.version,
                results=[
                    CheckResult(
                        result_type=CheckResultType.FAILURE,
                        message="No release information available",
                    )
                ],
            )

        # We do have a trusted release info from PyPI, we can run checks
        check_results = await asyncio.gather(
            *[_run_one_check(checker, release_info, check_progress_tracker) for checker in self._checkers]
        )
        return PackageCheckResults(
            name=release_info.name, version=release_info.version, results=check_results, pypi_url=release_info.pypi_url
        )


async def _run_one_check(
    checker: Checker, release_info: VerifiedPypiReleaseInfo, check_progress_tracker: _CheckProgressTracker
) -> CheckResult:
    try:
        result = await checker.check(release_info)
        check_progress_tracker.update_check(checker, result.result_type)
        return result
    except Exception as e:
        logger.debug(
            f"Error running {checker.__class__.__name__} for {release_info.name}=={release_info.version}",
            exc_info=True,
        )
        check_progress_tracker.update_check(checker, CheckResultType.FAILURE)
        return CheckResult(
            result_type=CheckResultType.FAILURE,
            message=f"Check failed: {str(e)}",
        )
