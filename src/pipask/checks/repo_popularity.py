from pipask.checks.base_checker import Checker
from pipask.checks.types import CheckResult, CheckResultType
from pipask.infra.pypi import AttestationPublisher, PypiClient, VerifiedPypiReleaseInfo
from pipask.infra.repo_client import RepoClient
import logging

from pipask.utils import format_link

_WARNING_THRESHOLD = 1000
_BOLD_WARNING_THRESHOLD = 100

logger = logging.getLogger(__name__)


class RepoPopularityChecker(Checker):
    def __init__(self, repo_client: RepoClient, pypi_client: PypiClient):
        self._repo_client = repo_client
        self._pypi_client = pypi_client

    @property
    def description(self) -> str:
        return "Checking repository popularity"

    async def check(self, verified_release_info: VerifiedPypiReleaseInfo) -> CheckResult:
        attestations = await self._pypi_client.get_attestations(verified_release_info)
        project_urls = verified_release_info.release_response.info.project_urls
        if attestations is not None and len(attestations.attestation_bundles):
            # We have VERIFIED info about the source repository
            publisher = attestations.attestation_bundles[0].publisher
            repo_url = _get_repo_url(publisher)
            if repo_url is None:
                return CheckResult(
                    result_type=CheckResultType.WARNING,
                    message=f"Unrecognized repository type in attestation: {publisher.kind}",
                )
            repo_info = await self._repo_client.get_repo_info(repo_url)
            if repo_info is None:
                return CheckResult(
                    result_type=CheckResultType.FAILURE,
                    message=f"Source repository not found: [link={repo_url}]{repo_url}[/link]",
                )
            formatted_repository = format_link("Repository", repo_url, fallback=True)
            if repo_info.star_count > _WARNING_THRESHOLD:
                return CheckResult(
                    result_type=CheckResultType.SUCCESS,
                    message=f"{formatted_repository} has {repo_info.star_count} stars",
                )
            elif repo_info.star_count > _BOLD_WARNING_THRESHOLD:
                return CheckResult(
                    result_type=CheckResultType.WARNING,
                    message=f"{formatted_repository} has less than 1000 stars: {repo_info.star_count} stars",
                )
            else:
                return CheckResult(
                    result_type=CheckResultType.WARNING,
                    message=f"[bold]{formatted_repository} has less than 100 stars: {repo_info.star_count} stars",
                )
        elif project_urls is not None and (repo_url := project_urls.recognized_repo_url()) is not None:
            # We only have an UNVERIFIED link to the repository
            formatted_repository = format_link("repository", repo_url, fallback=True)
            return CheckResult(
                result_type=CheckResultType.WARNING,
                message=f"Unverified link to source {formatted_repository} (true origin may be different)",
            )
        else:
            # No recognized link to the source repository
            return CheckResult(result_type=CheckResultType.WARNING, message="No repository URL found")


def _get_repo_url(publisher: AttestationPublisher) -> str | None:
    match publisher.kind:
        case "GitHub":
            return f"https://github.com/{publisher.repository}"
        case "GitLab":
            return f"https://gitlab.com/{publisher.repository}"
        case _:
            logger.debug("Unsupported publisher: %s", publisher.kind)
            return None
