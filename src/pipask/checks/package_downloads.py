from pipask.infra.pypistats import PypiStatsClient
from pipask.checks.types import CheckResult, CheckResultType
from pipask.checks import Checker
from pipask.infra.pip import InstallationReportItem
from pipask.infra.pypi import ReleaseResponse
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
        self, package: InstallationReportItem, release_info_future: Awaitable[ReleaseResponse | None]
    ) -> CheckResult:
        pkg = package.pinned_requirement
        pypi_stats = await self._pypi_stats_client.get_download_stats(package.metadata.name)
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
