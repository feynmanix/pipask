from pipask.infra.pypistats import PypiStatsClient
from pipask.checks.types import CheckResult, CheckResultType
from pipask.infra.pip import InstallationReportItem

_WARNING_THRESHOLD = 5000
_FAILURE_THRESHOLD = 100


async def check_package_downloads(package: InstallationReportItem, pypi_stats_client: PypiStatsClient) -> CheckResult:
    pkg = package.pinned_requirement
    pypi_stats = await pypi_stats_client.get_download_stats(package.metadata.name)
    if pypi_stats is None:
        return CheckResult(pkg, result_type=CheckResultType.FAILURE, message="No download statistics available")
    formatted_downloads = f"{pypi_stats.last_month:,}"
    if pypi_stats.last_month < _FAILURE_THRESHOLD:
        return CheckResult(
            pkg,
            result_type=CheckResultType.FAILURE,
            message=f"Only {formatted_downloads} downloads from PyPI in the last month",
        )
    if pypi_stats.last_month < _WARNING_THRESHOLD:
        return CheckResult(
            pkg,
            result_type=CheckResultType.WARNING,
            message=f"Only {formatted_downloads} downloads from PyPI in the last month",
        )
    return CheckResult(
        pkg,
        result_type=CheckResultType.SUCCESS,
        message=f"{formatted_downloads} downloads from PyPI in the last month",
    )
