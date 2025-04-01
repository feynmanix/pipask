from pipask.infra.repo_client import REPO_URL_REGEX
from datetime import datetime
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field
import logging

from pipask.utils import simple_get_request

logger = logging.getLogger(__name__)


def _get_maybe_repo_url(url: str) -> str | None:
    match = REPO_URL_REGEX.match(url)
    if match:
        return match.group(0)
    return None


class ProjectUrls(BaseModel):
    bug_reports_lowercase: Optional[str] = Field(None, alias="bug reports")
    homepage_lowercase: Optional[str] = Field(None, alias="homepage")
    source_lowercase: Optional[str] = Field(None, alias="source")
    documentation_lowercase: Optional[str] = Field(None, alias="documentation")
    repository_lowercase: Optional[str] = Field(None, alias="repository")
    issues_lowercase: Optional[str] = Field(None, alias="issues")

    bug_reports_capitalized: Optional[str] = Field(None, alias="Bug Reports")
    homepage_capitalized: Optional[str] = Field(None, alias="Homepage")
    source_capitalized: Optional[str] = Field(None, alias="Source")
    documentation_capitalized: Optional[str] = Field(None, alias="Documentation")
    repository_capitalized: Optional[str] = Field(None, alias="Repository")
    issues_capitalized: Optional[str] = Field(None, alias="Issues")

    @property
    def bug_reports(self) -> str | None:
        return self.bug_reports_capitalized or self.bug_reports_lowercase

    @property
    def homepage(self) -> str | None:
        return self.homepage_capitalized or self.homepage_lowercase

    @property
    def source(self) -> str | None:
        return self.source_capitalized or self.source_lowercase

    @property
    def documentation(self) -> str | None:
        return self.documentation_capitalized or self.documentation_lowercase

    @property
    def repository(self) -> str | None:
        return self.repository_capitalized or self.repository_lowercase

    @property
    def issues(self) -> str | None:
        return self.issues_capitalized or self.issues_lowercase

    def recognized_repo_url(self) -> str | None:
        for url in [self.repository, self.source, self.homepage, self.documentation, self.issues]:
            if url and (repo_url := _get_maybe_repo_url(url)):
                return repo_url
        return None


class ProjectInfo(BaseModel):
    home_page: Optional[str] = None
    classifiers: list[str] = Field(default_factory=list)
    license: Optional[str] = None
    name: str
    package_url: Optional[str] = None
    project_url: Optional[str] = None
    project_urls: ProjectUrls = Field(default_factory=lambda: ProjectUrls(**{}))
    version: str
    yanked: bool = False
    yanked_reason: Optional[str] = None


class VulnerabilityPypi(BaseModel):
    aliases: List[str]
    details: Optional[str] = None
    summary: Optional[str] = None
    fixed_in: Optional[List[str]] = None
    id: Optional[str] = None
    link: Optional[str] = None
    source: Optional[str] = None
    withdrawn: Optional[datetime] = None


class ReleaseUrl(BaseModel):
    filename: str
    upload_time: datetime = Field(..., alias="upload_time_iso_8601")
    yanked: bool = False


class ProjectResponse(BaseModel):
    info: ProjectInfo


class ReleaseResponse(BaseModel):
    info: ProjectInfo
    urls: list[ReleaseUrl] = Field(default_factory=list)
    vulnerabilities: List[VulnerabilityPypi] = Field(default_factory=list)


class Distribution(BaseModel):
    filename: str
    upload_time: datetime = Field(..., alias="upload-time")
    yanked: bool | str = False


class DistributionsResponse(BaseModel):
    files: List[Distribution]
    # meta: dict[str, int | str]
    # name: str
    # versions: List[str]


class PypiClient:
    def __init__(self):
        self.client = httpx.AsyncClient(follow_redirects=True)

    async def get_project_info(self, project_name: str) -> ProjectResponse | None:
        """Get project metadata from PyPI."""
        url = f"https://pypi.org/pypi/{project_name}/json"
        return await simple_get_request(url, self.client, ProjectResponse)

    async def get_release_info(self, project_name: str, version: str) -> ReleaseResponse | None:
        """Get metadata for a specific project release from PyPI."""
        # See https://docs.pypi.org/api/json/#get-a-release for API documentation
        url = f"https://pypi.org/pypi/{project_name}/{version}/json"
        return await simple_get_request(url, self.client, ReleaseResponse)

    async def get_distributions(self, project_name: str) -> DistributionsResponse | None:
        """Get all distribution download URLs for a project's available releases from PyPI."""
        # See https://docs.pypi.org/api/index-api/#get-distributions-for-project
        url = f"https://pypi.org/simple/{project_name}/"
        headers = {"Accept": "application/vnd.pypi.simple.v1+json"}
        return await simple_get_request(url, self.client, DistributionsResponse, headers=headers)

    async def aclose(self) -> None:
        await self.client.aclose()
