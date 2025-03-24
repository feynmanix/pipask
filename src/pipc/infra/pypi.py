import re
from datetime import datetime
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field

# Same options as in Google's https://docs.deps.dev/api/v3/#getproject, without discontinued bitbucket
_REPO_URL_REGEX = re.compile(r"^https://(?:github|gitlab)[.]com/[^/]+/[^/.]+")


def _get_maybe_repo_url(url: str) -> str | None:
    match = _REPO_URL_REGEX.match(url)
    if match:
        return match.group(0)
    return None


class ProjectUrls(BaseModel):
    bug_reports: Optional[str] = Field(None, alias="Bug Reports")
    funding: Optional[str] = Field(None, alias="Funding")
    homepage: Optional[str] = Field(None, alias="Homepage")
    source: Optional[str] = Field(None, alias="Source")
    documentation: Optional[str] = Field(None, alias="Documentation")
    repository: Optional[str] = Field(None, alias="Repository")
    issues: Optional[str] = Field(None, alias="Issues")

    def recognized_repo_url(self) -> str | None:
        for url in [self.repository, self.source, self.homepage, self.documentation, self.issues]:
            if url and (repo_url := _get_maybe_repo_url(url)):
                return repo_url
        return None


class ProjectInfo(BaseModel):
    license: Optional[str] = None
    name: str
    package_url: Optional[str] = None
    project_url: Optional[str] = None
    project_urls: ProjectUrls = Field(default_factory=lambda: ProjectUrls(**{}))
    version: str
    yanked: bool = False
    yanked_reason: Optional[str] = None


class Vulnerability(BaseModel):
    aliases: List[str]
    details: Optional[str] = None
    summary: Optional[str] = None
    fixed_in: List[str]
    id: Optional[str] = None
    link: Optional[str] = None
    source: Optional[str] = None
    withdrawn: Optional[datetime] = None


class ProjectResponse(BaseModel):
    info: ProjectInfo


class ReleaseResponse(BaseModel):
    info: ProjectInfo
    vulnerabilities: List[Vulnerability] = Field(default_factory=list)


# See https://docs.pypi.org/api/json/#get-a-release for API documentation
class PypiClient:
    def __init__(self):
        self.client = httpx.AsyncClient()

    async def get_project_info(self, project_name: str) -> ProjectResponse | None:
        """Get project metadata from PyPI."""
        url = f"https://pypi.org/pypi/{project_name}/json"
        response = await self.client.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return ProjectResponse.model_validate(response.json())

    async def get_release_info(self, project_name: str, version: str) -> ReleaseResponse | None:
        """Get metadata for a specific project release from PyPI."""
        url = f"https://pypi.org/pypi/{project_name}/{version}/json"
        response = await self.client.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return ReleaseResponse.model_validate(response.json())

    async def aclose(self) -> None:
        await self.client.aclose()
