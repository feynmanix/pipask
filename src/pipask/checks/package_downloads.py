from pipask.infra.pypistats import PypiStatsClient
from pipask.checks.types import CheckResult, CheckResultType
from pipask.checks.base_checker import Checker
from pipask.infra.pip_report import InstallationReportItem
from pipask.infra.pypi import VerifiedPypiReleaseInfo
from typing import Awaitable

_WARNING_THRESHOLD = 5000
_FAILURE_THRESHOLD = 100


class PackageDownloadsChecker(Checker):
    priority = 20

    def __init__(self, pypi_stats_client: PypiStatsClient):
        self._pypi_stats_client = pypi_stats_client

    @property
    def description(self) -> str:
        return "Checking package download stats"

    async def check(
        self, package: InstallationReportItem, verified_release_info_future: Awaitable[VerifiedPypiReleaseInfo | None]
    ) -> CheckResult:
        pkg = package.pinned_requirement
        verified_release_info = await verified_release_info_future
        if verified_release_info is None:
            return CheckResult(
                pkg,
                result_type=CheckResultType.FAILURE,
                message="No release information available",
                priority=self.priority,
            )
        pypi_stats = await self._pypi_stats_client.get_download_stats(verified_release_info.name)
        if pypi_stats is None:
            return CheckResult(
                pkg,
                result_type=CheckResultType.FAILURE,
                message="No download statistics available",
                priority=self.priority,
            )
        formatted_downloads = f"{pypi_stats.last_month:,}"
        if pypi_stats.last_month < _FAILURE_THRESHOLD:
            return CheckResult(
                pkg,
                result_type=CheckResultType.FAILURE,
                message=f"Only {formatted_downloads} downloads from PyPI in the last month",
                priority=self.priority,
            )
        if pypi_stats.last_month < _WARNING_THRESHOLD:
            return CheckResult(
                pkg,
                result_type=CheckResultType.WARNING,
                message=f"Only {formatted_downloads} downloads from PyPI in the last month",
                priority=self.priority,
            )
        return CheckResult(
            pkg,
            result_type=CheckResultType.SUCCESS,
            message=f"{formatted_downloads} downloads from PyPI in the last month",
            priority=self.priority,
        )
