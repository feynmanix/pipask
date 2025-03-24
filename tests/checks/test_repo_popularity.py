import pytest
from unittest.mock import AsyncMock, MagicMock

from pipask.checks.repo_popularity import check_repo_popularity
from pipask.checks.types import CheckResultType
from pipask.infra.pypi import ReleaseResponse, ProjectInfo, ProjectUrls
from pipask.infra.repo_client import RepoClient, RepoInfo
from pipask.infra.pip import InstallationReportItem, InstallationReportItemMetadata, InstallationReportItemDownloadInfo

PACKAGE_NAME = "package"
PACKAGE_VERSION = "1.0.0"
REPORT_ITEM = InstallationReportItem(
    metadata=InstallationReportItemMetadata(name=PACKAGE_NAME, version=PACKAGE_VERSION),
    download_info=InstallationReportItemDownloadInfo(url="https://example.com"),
    requested=True,
    is_yanked=False,
)
RELEASE_RESPONSE_WITH_REPO_URL = ReleaseResponse(
    info=ProjectInfo(
        name=PACKAGE_NAME,
        version=PACKAGE_VERSION,
        project_urls=ProjectUrls(**{"Repository": "https://github.com/user/repo"}),
    )
)


@pytest.mark.asyncio
async def test_repo_popularity_no_release_info():
    repo_client = MagicMock(spec=RepoClient)
    repo_client = MagicMock(spec=RepoClient)
    release_info = AsyncMock(return_value=None)

    result = await check_repo_popularity(REPORT_ITEM, release_info(), repo_client)

    assert result.result_type == CheckResultType.FAILURE
    assert result.message == "No release information available"


@pytest.mark.asyncio
async def test_repo_popularity_no_repo_url():
    repo_client = MagicMock(spec=RepoClient)
    release_info = AsyncMock(
        return_value=ReleaseResponse(
            info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION, project_urls=ProjectUrls(**{}))
        )
    )

    result = await check_repo_popularity(REPORT_ITEM, release_info(), repo_client)

    assert result.result_type == CheckResultType.WARNING
    assert result.message == "No repository URL found"


@pytest.mark.asyncio
async def test_repo_not_found():
    repo_client = MagicMock(spec=RepoClient)
    release_info = AsyncMock(return_value=RELEASE_RESPONSE_WITH_REPO_URL)
    repo_client.get_repo_info.return_value = None

    result = await check_repo_popularity(REPORT_ITEM, release_info(), repo_client)

    assert result.result_type == CheckResultType.FAILURE
    assert result.message == "Declared repository not found: https://github.com/user/repo"


@pytest.mark.asyncio
async def test_high_star_count():
    repo_client = MagicMock(spec=RepoClient)
    release_info = AsyncMock(return_value=RELEASE_RESPONSE_WITH_REPO_URL)
    repo_client.get_repo_info.return_value = RepoInfo(star_count=1500)

    result = await check_repo_popularity(REPORT_ITEM, release_info(), repo_client)

    assert result.result_type == CheckResultType.SUCCESS


@pytest.mark.asyncio
async def test_medium_star_count():
    repo_client = MagicMock(spec=RepoClient)
    release_info = AsyncMock(return_value=RELEASE_RESPONSE_WITH_REPO_URL)
    repo_client.get_repo_info.return_value = RepoInfo(star_count=500)

    result = await check_repo_popularity(REPORT_ITEM, release_info(), repo_client)

    assert result.result_type == CheckResultType.WARNING


@pytest.mark.asyncio
async def test_low_star_count():
    repo_client = MagicMock(spec=RepoClient)
    release_info = AsyncMock(return_value=RELEASE_RESPONSE_WITH_REPO_URL)
    repo_client.get_repo_info.return_value = RepoInfo(star_count=50)

    result = await check_repo_popularity(REPORT_ITEM, release_info(), repo_client)

    assert result.result_type == CheckResultType.WARNING
    assert result.message == "[bold]Repository has less than 100 stars: 50"
