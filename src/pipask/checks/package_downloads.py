from pipask.checks.base_checker import Checker
from pipask.checks.types import CheckResult, CheckResultType
from pipask.infra.pypi import VerifiedPypiReleaseInfo
from pipask.infra.pypistats import PypiStatsClient

_WARNING_THRESHOLD = 5000
_FAILURE_THRESHOLD = 100


class PackageDownloadsChecker(Checker):
    def __init__(self, pypi_stats_client: PypiStatsClient):
        self._pypi_stats_client = pypi_stats_client

    @property
    def description(self) -> str:
        return "Checking package download stats"

    async def check(self, verified_release_info: VerifiedPypiReleaseInfo) -> CheckResult:
        pypi_stats = await self._pypi_stats_client.get_download_stats(verified_release_info.name)
        if pypi_stats is None:
            return CheckResult(
                result_type=CheckResultType.FAILURE,
                message="No download statistics available",
            )
        formatted_downloads = f"{pypi_stats.last_month:,}"
        if pypi_stats.last_month < _FAILURE_THRESHOLD:
            return CheckResult(
                result_type=CheckResultType.FAILURE,
                message=f"Only {formatted_downloads} downloads from PyPI in the last month",
            )
        if pypi_stats.last_month < _WARNING_THRESHOLD:
            return CheckResult(
                result_type=CheckResultType.WARNING,
                message=f"Only {formatted_downloads} downloads from PyPI in the last month",
            )
        return CheckResult(
            result_type=CheckResultType.SUCCESS,
            message=f"{formatted_downloads} downloads from PyPI in the last month",
        )
