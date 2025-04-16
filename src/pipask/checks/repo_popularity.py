from pipask.checks.base_checker import Checker
from pipask.checks.types import CheckResult, CheckResultType
from pipask.infra.pypi import VerifiedPypiReleaseInfo
from pipask.infra.repo_client import RepoClient

_WARNING_THRESHOLD = 1000
_BOLD_WARNING_THRESHOLD = 100


class RepoPopularityChecker(Checker):
    def __init__(self, repo_client: RepoClient):
        self._repo_client = repo_client

    @property
    def description(self) -> str:
        return "Checking repository popularity"

    async def check(self, verified_release_info: VerifiedPypiReleaseInfo) -> CheckResult:
        project_urls = verified_release_info.release_response.info.project_urls
        repo_url = project_urls.recognized_repo_url() if project_urls is not None else None
        if repo_url is None:
            return CheckResult(result_type=CheckResultType.WARNING, message="No repository URL found")
        repo_info = await self._repo_client.get_repo_info(repo_url)
        if repo_info is None:
            return CheckResult(
                result_type=CheckResultType.FAILURE,
                message=f"Declared repository not found: {repo_url}",
            )

        formatted_repository = f"[link={repo_url}]Repository[/link]"
        if repo_info.star_count > _WARNING_THRESHOLD:
            return CheckResult(
                result_type=CheckResultType.SUCCESS,
                message=f"{formatted_repository} has {repo_info.star_count} stars",
            )
        elif repo_info.star_count > _BOLD_WARNING_THRESHOLD:
            return CheckResult(
                result_type=CheckResultType.WARNING,
                message=f"{formatted_repository} has less than 1000 stars: {repo_info.star_count}",
            )
        else:
            return CheckResult(
                result_type=CheckResultType.WARNING,
                message=f"[bold]{formatted_repository} has less than 100 stars: {repo_info.star_count}",
            )
