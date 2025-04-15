import logging
from typing import Tuple

from packaging.utils import (
    InvalidSdistFilename,
    InvalidWheelFilename,
    canonicalize_name,
    parse_sdist_filename,
    parse_wheel_filename,
)
from packaging.version import Version

import pipask._vendor.pip._internal.utils.temp_dir
from pipask._vendor.pip._internal.metadata import BaseDistribution, get_metadata_distribution
from pipask._vendor.pip._internal.models.index import PyPI
from pipask._vendor.pip._internal.models.link import Link
from pipask._vendor.pip._internal.network.session import PipSession
from pipask._vendor.pip._internal.req.req_install import InstallRequirement
from pipask._vendor.pip._internal.utils.hashes import Hashes
from pipask.exception import PipaskException
from pipask.infra.pypi import (
    ProjectReleaseFile,
    ReleaseResponse,
    get_pypi_project_info_sync,
    get_pypi_release_info_sync,
)

logger = logging.getLogger(__name__)


def synthesize_release_metadata_file(release_info: ReleaseResponse) -> str:
    """Synthesize a release metadata file for a project release from PyPI."""
    lines = [
        "Metadata-Version: 2.1",
        f"Name: {release_info.info.name}",
        f"Version: {release_info.info.version}",
    ]
    if release_info.info.summary:
        lines.append(f"Summary: {release_info.info.summary}")
    if release_info.info.home_page:
        lines.append(f"Home-page: {release_info.info.home_page}")
    if release_info.info.download_url:
        lines.append(f"Download-URL: {release_info.info.download_url}")
    if release_info.info.author:
        lines.append(f"Author: {release_info.info.author}")
    if release_info.info.author_email:
        lines.append(f"Author-email: {release_info.info.author_email}")
    if release_info.info.license:
        lines.append(f"License: {release_info.info.license}")
    if release_info.info.classifiers:
        for classifier in release_info.info.classifiers:
            lines.append(f"Classifier: {classifier}")
    if release_info.info.requires_python:
        lines.append(f"Requires-Python: {release_info.info.requires_python}")
    if release_info.info.requires_dist is not None:
        for req in release_info.info.requires_dist:
            lines.append(f"Requires-Dist: {req}")
    if release_info.info.provides_extra:
        for extra in release_info.info.provides_extra:
            lines.append(f"Provides-Extra: {extra}")
    return "\n".join(lines)


# Making this private to avoid inadvertent use without checking that the hash or URL matches PyPI index
def _get_pypi_metadata_distribution(
    canonical_name: str,
    version: Version,
    pip_session: PipSession,
) -> BaseDistribution | None:
    if pipask._vendor.pip._internal.utils.temp_dir._tempdir_manager is None:
        raise RuntimeError(
            # Required inside get_metadata_distribution(), fail fast
            "Tempdir manager is not initialized. This is required by pip._internal.metadata.importlib._dists.Distribution.from_metadata_file_contents"
        )
    release = get_pypi_release_info_sync(canonical_name, str(version), pip_session)
    if release is None:
        return None
    metadata = synthesize_release_metadata_file(release)
    return get_metadata_distribution(metadata.encode(), None, canonical_name)


def _is_from_pypi(link: Link) -> bool:
    if link.comes_from is None:
        return False
    comes_from_url: str = link.comes_from if isinstance(link.comes_from, str) else link.comes_from.url
    return comes_from_url.startswith(PyPI.simple_url)


def _name_and_version_from_link(link: Link) -> Tuple[str, Version]:
    filename = link.filename
    if link.is_wheel:
        try:
            name, version, _build, _tags = parse_wheel_filename(filename)
            return name, version
        except InvalidWheelFilename:
            raise PipaskException("Invalid wheel filename: " + filename)
    else:
        try:
            name, version = parse_sdist_filename(filename)
            return name, version
        except InvalidSdistFilename:
            raise PipaskException("Invalid sdist filename: " + filename)


def _find_release_by_hash(
    releases: dict[str, list[ProjectReleaseFile]], hashes: Hashes
) -> tuple[str, ProjectReleaseFile] | tuple[None, None]:
    for version, files in releases.items():
        for file in files:
            if hashes.has_one_of(file.digests):
                return version, file
    return None, None


def fetch_metadata_from_pypi_is_available(req: InstallRequirement, pip_session: PipSession) -> BaseDistribution | None:
    if req.link is None or req.name is None:
        return None
    if req.link.is_vcs:  # We cannot parse name and version from VCS links
        return None
    req_name = canonicalize_name(req.name)
    parsed_name, parsed_version = _name_and_version_from_link(req.link)
    if canonicalize_name(parsed_name) != req_name:
        logger.warning(
            f"Mismatch of requirement name '{req_name}' and remote file name {req.link.url_without_fragment}"
        )
        return None

    # Note: similar logic is in PypiClient

    if _is_from_pypi(req.link):
        return _get_pypi_metadata_distribution(req_name, parsed_version, pip_session)
    elif req.link.has_hash:
        # If the requirement does not appear to be from PyPI directly
        # it can originate from a proxy that serves files originating from PyPI.
        # In such case, we can fall back on hashes to find the correct release
        # and its metadata in PyPI.
        project_info = get_pypi_project_info_sync(canonicalize_name(req.name), pip_session)
        if project_info is None:
            return None
        version, file = _find_release_by_hash(project_info.releases, req.link.as_hashes())
        if version is not None:
            return _get_pypi_metadata_distribution(canonicalize_name(req.name), Version(version), pip_session)
    else:
        # Not a pypi link, and no hashes to check againsg
        # -> we can't be sure if we would be fetching the correct metadata
        return None


def parse_link_version(link: Link) -> Version:
    return _name_and_version_from_link(link)[1]
