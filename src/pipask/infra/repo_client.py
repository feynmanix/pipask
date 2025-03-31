import re
import urllib.parse
import logging
from dataclasses import dataclass

import httpx
from pydantic import BaseModel

from pipask.utils import simple_get_request

logger = logging.getLogger(__name__)


# Same options as in Google's https://docs.deps.dev/api/v3/#getproject, without discontinued bitbucket
REPO_URL_REGEX = re.compile(r"^https://(github|gitlab)[.]com/([^/]+/[^/.]+)")


class _GitHubRepoResponse(BaseModel):
    stargazers_count: int


class _GitLabProjectResponse(BaseModel):
    star_count: int


@dataclass
class RepoInfo:
    star_count: int


class RepoClient:
    def __init__(self):
        self.client = httpx.AsyncClient(follow_redirects=True)

    async def get_repo_info(self, repo_url: str) -> RepoInfo | None:
        match = REPO_URL_REGEX.match(repo_url)
        if not match:
            raise ValueError(f"Invalid repository URL: {repo_url}")
        service_name = match.group(1)
        repo_name = match.group(2)
        if service_name == "github":
            return await self._get_github_repo_info(repo_name)
        elif service_name == "gitlab":
            return await self._get_gitlab_repo_info(repo_name)
        else:
            raise ValueError(f"Unsupported service: {service_name}")

    async def _get_github_repo_info(self, repo_name: str) -> RepoInfo | None:
        url = f"https://api.github.com/repos/{repo_name}"
        parsed_response = await simple_get_request(url, self.client, _GitHubRepoResponse)
        return RepoInfo(star_count=parsed_response.stargazers_count) if parsed_response is not None else None

    async def _get_gitlab_repo_info(self, repo_name: str) -> RepoInfo | None:
        url = f"https://gitlab.com/api/v4/projects/{urllib.parse.quote(repo_name, safe='')}"
        parsed_response = await simple_get_request(url, self.client, _GitLabProjectResponse)
        return RepoInfo(star_count=parsed_response.star_count) if parsed_response is not None else None

    async def aclose(self) -> None:
        await self.client.aclose()
