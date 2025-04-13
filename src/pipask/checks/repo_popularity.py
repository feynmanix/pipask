from typing import Awaitable

from pipask.infra.pypi import ReleaseResponse
from pipask.infra.repo_client import RepoClient
from pipask.checks.types import CheckResult, CheckResultType
from pipask.checks import Checker
from pipask.infra.pip import InstallationReportItem


_WARNING_THRESHOLD = 1000
_BOLD_WARNING_THRESHOLD = 100


class RepoPopularityChecker(Checker):
    priority = 10

    def __init__(self, repo_client: RepoClient):
        self._repo_client = repo_client

    @property
    def description(self) -> str:
        return "Checking repository popularity"

    async def check(
        self, package: InstallationReportItem, release_info_future: Awaitable[ReleaseResponse | None]
    ) -> CheckResult:
        pkg = package.pinned_requirement
        resolved_release_info = await release_info_future
        if resolved_release_info is None:
            return CheckResult(
                pkg,
                result_type=CheckResultType.FAILURE,
                message="No release information available",
                priority=self.priority,
            )
        repo_url = resolved_release_info.info.project_urls.recognized_repo_url()
        if repo_url is None:
            return CheckResult(
                pkg, result_type=CheckResultType.WARNING, message="No repository URL found", priority=self.priority
            )
        repo_info = await self._repo_client.get_repo_info(repo_url)
        if repo_info is None:
            return CheckResult(
                pkg,
                result_type=CheckResultType.FAILURE,
                message=f"Declared repository not found: {repo_url}",
                priority=self.priority,
            )

        formatted_repository = f"[link={repo_url}]Repository[/link]"
        if repo_info.star_count > _WARNING_THRESHOLD:
            return CheckResult(
                pkg,
                result_type=CheckResultType.SUCCESS,
                message=f"{formatted_repository} has {repo_info.star_count} stars",
                priority=self.priority,
            )
        elif repo_info.star_count > _BOLD_WARNING_THRESHOLD:
            return CheckResult(
                pkg,
                result_type=CheckResultType.WARNING,
                message=f"{formatted_repository} has less than 1000 stars: {repo_info.star_count}",
                priority=self.priority,
            )
        else:
            return CheckResult(
                pkg,
                result_type=CheckResultType.WARNING,
                message=f"[bold]{formatted_repository} has less than 100 stars: {repo_info.star_count}",
                priority=self.priority,
            )
