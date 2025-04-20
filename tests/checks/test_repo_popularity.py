from unittest.mock import MagicMock, AsyncMock

import pytest

from pipask.checks.repo_popularity import RepoPopularityChecker
from pipask.checks.types import CheckResultType
from pipask.infra.pypi import (
    AttestationBundle,
    AttestationPublisher,
    AttestationResponse,
    ProjectInfo,
    ProjectUrls,
    ReleaseResponse,
    VerifiedPypiReleaseInfo,
)
from pipask.infra.repo_client import RepoClient, RepoInfo
from pipask.infra.pypi import PypiClient

PACKAGE_NAME = "package"
PACKAGE_VERSION = "1.0.0"

GITHUB_ATTESTATION = AttestationResponse(
    attestation_bundles=[
        AttestationBundle(
            publisher=AttestationPublisher(
                kind="GitHub",
                repository="user/repo",
            )
        )
    ],
    version=1,
)

GITLAB_ATTESTATION = AttestationResponse(
    attestation_bundles=[
        AttestationBundle(
            publisher=AttestationPublisher(
                kind="GitLab",
                repository="user/repo",
            )
        )
    ],
    version=1,
)

UNKNOWN_PUBLISHER_ATTESTATION = AttestationResponse(
    attestation_bundles=[
        AttestationBundle(
            publisher=AttestationPublisher(
                kind="Unknown",
                repository="user/repo",
            )
        )
    ],
    version=1,
)


@pytest.mark.asyncio
async def test_repo_popularity_no_repo_url():
    repo_client = MagicMock(spec=RepoClient)
    pypi_client = MagicMock(spec=PypiClient)
    pypi_client.get_attestations = AsyncMock(return_value=None)
    checker = RepoPopularityChecker(repo_client, pypi_client)
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION, project_urls=None)),
        "file.whl",
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.WARNING
    assert result.message == "No repository URL found"


@pytest.mark.asyncio
async def test_unrecognized_publisher_type():
    repo_client = MagicMock(spec=RepoClient)
    pypi_client = MagicMock(spec=PypiClient)
    pypi_client.get_attestations = AsyncMock(return_value=UNKNOWN_PUBLISHER_ATTESTATION)
    checker = RepoPopularityChecker(repo_client, pypi_client)
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION, project_urls=None)),
        "file.whl",
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.WARNING
    assert result.message == "Unrecognized repository type in attestation: Unknown"


@pytest.mark.asyncio
async def test_repo_not_found_with_attestation():
    repo_client = MagicMock(spec=RepoClient)
    repo_client.get_repo_info.return_value = None
    pypi_client = MagicMock(spec=PypiClient)
    pypi_client.get_attestations = AsyncMock(return_value=GITHUB_ATTESTATION)
    checker = RepoPopularityChecker(repo_client, pypi_client)
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION, project_urls=None)),
        "file.whl",
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.FAILURE
    assert (
        result.message
        == "Source repository not found: [link=https://github.com/user/repo]https://github.com/user/repo[/link]"
    )


@pytest.mark.asyncio
async def test_unverified_repo_url():
    repo_client = MagicMock(spec=RepoClient)
    pypi_client = MagicMock(spec=PypiClient)
    pypi_client.get_attestations = AsyncMock(return_value=None)
    checker = RepoPopularityChecker(repo_client, pypi_client)
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
                project_urls=ProjectUrls(**{"Repository": "https://github.com/user/repo"}),
            )
        ),
        "file.whl",
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.WARNING
    assert (
        result.message
        == "Unverified link to source [link=https://github.com/user/repo]repository[/link] (true origin may be different)"
    )


@pytest.mark.asyncio
async def test_high_star_count_with_attestation():
    repo_client = MagicMock(spec=RepoClient)
    pypi_client = MagicMock(spec=PypiClient)
    pypi_client.get_attestations = AsyncMock(return_value=GITHUB_ATTESTATION)
    checker = RepoPopularityChecker(repo_client, pypi_client)
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION, project_urls=None)),
        "file.whl",
    )
    repo_client.get_repo_info.return_value = RepoInfo(star_count=1500)

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.SUCCESS
    assert "[link=https://github.com/user/repo]Repository[/link] has 1500 stars" in result.message
    pypi_client.get_attestations.assert_called_once_with(release_info)


@pytest.mark.asyncio
async def test_medium_star_count_with_attestation():
    repo_client = MagicMock(spec=RepoClient)
    pypi_client = MagicMock(spec=PypiClient)
    pypi_client.get_attestations = AsyncMock(return_value=GITHUB_ATTESTATION)
    checker = RepoPopularityChecker(repo_client, pypi_client)
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION, project_urls=None)),
        "file.whl",
    )
    repo_client.get_repo_info.return_value = RepoInfo(star_count=500)

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.WARNING
    assert "[link=https://github.com/user/repo]Repository[/link] has less than 1000 stars: 500 stars" in result.message


@pytest.mark.asyncio
async def test_low_star_count_with_attestation():
    repo_client = MagicMock(spec=RepoClient)
    pypi_client = MagicMock(spec=PypiClient)
    pypi_client.get_attestations = AsyncMock(return_value=GITHUB_ATTESTATION)
    checker = RepoPopularityChecker(repo_client, pypi_client)
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION, project_urls=None)),
        "file.whl",
    )
    repo_client.get_repo_info.return_value = RepoInfo(star_count=50)

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.WARNING
    assert result.message == "[bold][link=https://github.com/user/repo]Repository[/link] has less than 100 stars: 50 stars"
