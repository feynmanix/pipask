from typing import Awaitable

from pipask.infra.pypi import ReleaseResponse
from pipask.infra.repo_client import RepoClient
from pipask.checks.types import CheckResult, CheckResultType
from pipask.infra.pip import InstallationReportItem


async def check_repo_popularity(
    package: InstallationReportItem, release_info: Awaitable[ReleaseResponse | None], repo_client: RepoClient
) -> CheckResult:
    pkg = package.pinned_requirement
    resolved_release_info = await release_info
    if resolved_release_info is None:
        return CheckResult(pkg, result_type=CheckResultType.FAILURE, message="No release information available")
    repo_url = resolved_release_info.info.project_urls.recognized_repo_url()
    if repo_url is None:
        return CheckResult(pkg, result_type=CheckResultType.WARNING, message="No repository URL found")
    repo_info = await repo_client.get_repo_info(repo_url)
    if repo_info is None:
        return CheckResult(
            pkg, result_type=CheckResultType.FAILURE, message=f"Declared repository not found: {repo_url}"
        )

    if repo_info.star_count > 1000:
        return CheckResult(
            pkg, result_type=CheckResultType.SUCCESS, message=f"Repository has {repo_info.star_count} stars"
        )
    elif repo_info.star_count > 100:
        return CheckResult(
            pkg,
            result_type=CheckResultType.WARNING,
            message=f"Repository has less than 1000 stars: {repo_info.star_count}",
        )
    else:
        return CheckResult(
            pkg,
            result_type=CheckResultType.WARNING,
            message=f"[bold]Repository has less than 100 stars: {repo_info.star_count}",
        )
