import logging
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import httpx
from httpx import AsyncBaseTransport
from pydantic import BaseModel, Field

from pipask._vendor.pip._internal.models.index import PyPI  # type: ignore
from pipask._vendor.pip._internal.network.session import PipSession  # type: ignore
from pipask.infra.pip_types import InstallationReportItem
from pipask.infra.repo_client import REPO_URL_REGEX
from pipask.utils import simple_get_request, simple_get_request_sync

logger = logging.getLogger(__name__)


def _get_maybe_repo_url(url: str) -> str | None:
    match = REPO_URL_REGEX.match(url)
    if match:
        return match.group(0)
    return None


class ProjectUrls(BaseModel):
    # See also https://docs.pypi.org/project_metadata/#icons
    bug_reports_lowercase: Optional[str] = Field(None, alias="bug reports")
    homepage_lowercase: Optional[str] = Field(None, alias="homepage")
    source_lowercase: Optional[str] = Field(None, alias="source")
    documentation_lowercase: Optional[str] = Field(None, alias="documentation")
    repository_lowercase: Optional[str] = Field(None, alias="repository")
    issues_lowercase: Optional[str] = Field(None, alias="issues")
    download_lowercase: Optional[str] = Field(None, alias="download")

    bug_reports_capitalized: Optional[str] = Field(None, alias="Bug Reports")
    homepage_capitalized: Optional[str] = Field(None, alias="Homepage")
    source_capitalized: Optional[str] = Field(None, alias="Source")
    documentation_capitalized: Optional[str] = Field(None, alias="Documentation")
    repository_capitalized: Optional[str] = Field(None, alias="Repository")
    issues_capitalized: Optional[str] = Field(None, alias="Issues")
    download_capitalized: Optional[str] = Field(None, alias="Download")

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

    @property
    def download(self) -> str | None:
        return self.download_capitalized or self.download_lowercase

    def recognized_repo_url(self) -> str | None:
        for url in [self.repository, self.source, self.homepage, self.documentation, self.issues, self.download]:
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
    project_urls: Optional[ProjectUrls] = None
    version: str
    yanked: bool = False
    yanked_reason: Optional[str] = None
    summary: Optional[str] = None
    author_email: Optional[str] = None
    author: Optional[str] = None
    download_url: Optional[str] = None
    requires_python: Optional[str] = None
    requires_dist: Optional[List[str]] = None
    provides_extra: Optional[List[str]] = None


class VulnerabilityPypi(BaseModel):
    aliases: List[str]
    details: Optional[str] = None
    summary: Optional[str] = None
    fixed_in: Optional[List[str]] = None
    id: Optional[str] = None
    link: Optional[str] = None
    source: Optional[str] = None
    withdrawn: Optional[datetime] = None


class ProjectReleaseFile(BaseModel):
    filename: str
    upload_time: datetime = Field(..., alias="upload_time_iso_8601")
    yanked: bool = False
    digests: dict[str, str] = Field(default_factory=dict)


class ProjectResponse(BaseModel):
    info: ProjectInfo
    releases: dict[str, list[ProjectReleaseFile]] = Field(default_factory=dict)


class ReleaseResponse(BaseModel):
    info: ProjectInfo
    urls: list[ProjectReleaseFile] = Field(default_factory=list)
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


class AttestationPublisher(BaseModel):
    # claims: Optional[dict] = None
    kind: str
    repository: str
    workflow: Optional[str] = None
    environment: Optional[str] = None


class AttestationBundle(BaseModel):
    publisher: AttestationPublisher


class AttestationResponse(BaseModel):
    attestation_bundles: List[AttestationBundle]
    version: int


_pypi_root_url = PyPI.url
_pypi_url = PyPI.pypi_url
_pypi_simple_url = PyPI.simple_url
_pypi_file_storage_url = f"https://{PyPI.file_storage_domain}/packages/"


def _release_info_url(project_name: str, version: str) -> str:
    # See https://docs.pypi.org/api/json/#get-a-release for API documentation
    return f"{_pypi_url}/{project_name}/{version}/json"


def _project_info_url(project_name: str) -> str:
    # See https://docs.pypi.org/api/json/#project-metadata for API documentation
    return f"{_pypi_url}/{project_name}/json"


def _integrity_url(project_name: str, version: str, filename: str) -> str:
    integrity_url = urllib.parse.urljoin(_pypi_root_url, "integrity")
    return f"{integrity_url}/{project_name}/{version}/{filename}/provenance"


@dataclass
class VerifiedPypiReleaseInfo:
    """
    Pointer to a release on PyPI that has been verified to match a distribution file
    either through download URL or hash.
    This is so that we can enforce checking the identity of the package through static typing.
    """

    release_response: ReleaseResponse

    release_filename: str

    @property
    def name(self) -> str:
        return self.release_response.info.name

    @property
    def version(self) -> str:
        return self.release_response.info.version

    @property
    def pypi_url(self) -> str:
        return f"https://pypi.org/project/{self.name}/{self.version}/"


class PypiClient:
    def __init__(self, transport: AsyncBaseTransport | None = None):
        self.client = httpx.AsyncClient(follow_redirects=True, transport=transport)

    async def get_project_info(self, project_name: str) -> ProjectResponse | None:
        """Get project metadata from PyPI."""
        return await simple_get_request(_project_info_url(project_name), self.client, ProjectResponse)

    async def _get_release_info(self, project_name: str, version: str) -> ReleaseResponse | None:
        """Get metadata for a specific project release from PyPI."""
        # Private to avoid calling this without the checks in get__matching_release_info()
        return await simple_get_request(_release_info_url(project_name, version), self.client, ReleaseResponse)

    async def get_matching_release_info(self, package: InstallationReportItem) -> VerifiedPypiReleaseInfo | None:
        if package.download_info is None:
            # We don't know where the package is from,
            # could be a different thing than a package of the same name in PyPI
            return None

        name = package.metadata.name
        version = package.metadata.version
        pypi_release_info = await self._get_release_info(name, version)
        if pypi_release_info is None:
            # Nothing to report anyway
            return None

        # Note: similar logic is in fetch_metadata_from_pypi_is_available()

        if package.download_info.url.startswith(_pypi_file_storage_url):
            # The package is from PyPI, so we can get the metadata directly
            filename = urllib.parse.urlparse(package.download_info.url).path.split("/")[-1]
            return VerifiedPypiReleaseInfo(pypi_release_info, filename)
        elif package.download_info.archive_info is not None and package.download_info.archive_info.hashes is not None:
            # Not from PyPI, but we can check if the hash matches PyPI (this will match, e.g., for index proxies)
            acceptable_hashes_to_filename: dict[Tuple[str, str], str] = {
                digest: url.filename
                for url in pypi_release_info.urls
                for digest in url.digests.items()
                if digest[0] != "md5"
            }
            package_hashes: list[Tuple[str, str]] = list(package.download_info.archive_info.hashes.items())
            for package_hash in package_hashes:
                if package_hash in acceptable_hashes_to_filename:
                    # We have a match, the metadata can be used
                    logger.debug(f"\n\nHash of package {name} matches a PyPI release hash\n\n")
                    filename = acceptable_hashes_to_filename[package_hash]
                    return VerifiedPypiReleaseInfo(pypi_release_info, filename)
        # No match found, we cannot reliably say the PyPI metadata belong to the package
        logger.debug(f"Hash of package {name} does not match any PyPI release hash")
        return None

    async def get_attestations(self, verified_release_info: VerifiedPypiReleaseInfo) -> AttestationResponse | None:
        url = _integrity_url(
            verified_release_info.name, verified_release_info.version, verified_release_info.release_filename
        )
        headers = {"Accept": "application/vnd.pypi.integrity.v1+json"}
        return await simple_get_request(url, self.client, AttestationResponse, headers=headers)

    async def get_distributions(self, project_name: str) -> DistributionsResponse | None:
        """Get all distribution download URLs for a project's available releases from PyPI."""
        # See https://docs.pypi.org/api/index-api/#get-distributions-for-project
        url = f"{_pypi_simple_url}/{project_name}/"
        headers = {"Accept": "application/vnd.pypi.simple.v1+json"}
        return await simple_get_request(url, self.client, DistributionsResponse, headers=headers)

    async def aclose(self) -> None:
        await self.client.aclose()


def get_pypi_release_info_sync(project_name: str, version: str, request_session: PipSession):
    return simple_get_request_sync(_release_info_url(project_name, version), request_session, ReleaseResponse)


def get_pypi_project_info_sync(project_name: str, request_session: PipSession):
    return simple_get_request_sync(_project_info_url(project_name), request_session, ProjectResponse)
