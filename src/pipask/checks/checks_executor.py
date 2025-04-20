import asyncio
import logging
from typing import Tuple

from pipask.checks.base_checker import Checker
from pipask.checks.license import LicenseChecker
from pipask.checks.package_age import PackageAge
from pipask.checks.package_downloads import PackageDownloadsChecker
from pipask.checks.release_metadata import ReleaseMetadataChecker
from pipask.checks.repo_popularity import RepoPopularityChecker
from pipask.checks.types import CheckResult, CheckResultType, PackageCheckResults
from pipask.checks.vulnerabilities import ReleaseVulnerabilityChecker
from pipask.cli_helpers import SimpleTaskProgress
from pipask.infra.pip_types import InstallationReportItem
from pipask.infra.pypi import PypiClient, VerifiedPypiReleaseInfo
from pipask.infra.pypistats import PypiStatsClient
from pipask.infra.repo_client import RepoClient
from pipask.infra.vulnerability_details import OsvVulnerabilityDetailsService

logger = logging.getLogger(__name__)


class _CheckProgressTracker:
    def __init__(self, progress: SimpleTaskProgress, checkers_with_counts: list[Tuple[Checker, int]]):
        self._progress = progress
        self._progress_tasks_by_checker = {
            id(checker): progress.add_task(checker.description, total=total_count)
            for checker, total_count in checkers_with_counts
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
        release_vulnerability_checker = ReleaseVulnerabilityChecker(vulnerability_details_service)
        self._requested_package_checkers = [
            RepoPopularityChecker(repo_client, pypi_client),
            PackageDownloadsChecker(pypi_stats_client),
            PackageAge(pypi_client),
            release_vulnerability_checker,
            ReleaseMetadataChecker(),
            LicenseChecker(),
        ]
        self._transitive_dependency_checkers = [release_vulnerability_checker]

    async def execute_checks(
        self, packages_to_install: list[InstallationReportItem], progress: SimpleTaskProgress
    ) -> list[PackageCheckResults]:
        # This is ugly, but it's just some math to figure out the correct number of steps
        # in the progress task to count towards
        requested_deps_count = len([p for p in packages_to_install if p.requested])
        transitive_deps_count = len([p for p in packages_to_install if not p.requested])
        checkers_with_counts_by_id = {
            id(checker): (checker, requested_deps_count) for checker in self._requested_package_checkers
        }
        for checker in self._transitive_dependency_checkers:
            previous_value = checkers_with_counts_by_id.get(id(checker))
            previous_count = previous_value[1] if previous_value else 0
            checkers_with_counts_by_id[id(checker)] = (checker, transitive_deps_count + previous_count)
        check_progress_tracker = _CheckProgressTracker(progress, list(checkers_with_counts_by_id.values()))

        # Run the checks in parallel
        return await asyncio.gather(
            *[self._check_package(package, check_progress_tracker) for package in packages_to_install]
        )

    async def _check_package(
        self,
        unverified_metadata: InstallationReportItem,
        check_progress_tracker: _CheckProgressTracker,
    ) -> PackageCheckResults:
        release_info = await self._pypi_client.get_matching_release_info(unverified_metadata)
        is_transitive_dep = not unverified_metadata.requested

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
                is_transitive_dependency=is_transitive_dep,
            )

        # We do have a trusted release info from PyPI, we can run checks
        checkers_for_package = (
            self._transitive_dependency_checkers if is_transitive_dep else self._requested_package_checkers
        )
        check_results = await asyncio.gather(
            *[_run_one_check(checker, release_info, check_progress_tracker) for checker in checkers_for_package]
        )
        return PackageCheckResults(
            name=release_info.name,
            version=release_info.version,
            results=check_results,
            pypi_url=release_info.pypi_url,
            is_transitive_dependency=is_transitive_dep,
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
