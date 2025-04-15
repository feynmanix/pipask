from unittest.mock import AsyncMock, MagicMock

import pytest

from pipask.checks.package_downloads import PackageDownloadsChecker
from pipask.checks.types import CheckResultType
from pipask.infra.pypi import ProjectInfo, ReleaseResponse, VerifiedPypiReleaseInfo
from pipask.infra.pypistats import DownloadStats, PypiStatsClient

PACKAGE_NAME = "package"
PACKAGE_VERSION = "1.0.0"


@pytest.mark.asyncio
async def test_package_downloads_no_stats():
    pypi_stats_client = MagicMock(spec=PypiStatsClient)
    pypi_stats_client.get_download_stats = AsyncMock(return_value=None)
    checker = PackageDownloadsChecker(pypi_stats_client)
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION))
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.FAILURE
    assert result.message == "No download statistics available"


@pytest.mark.asyncio
async def test_high_download_count():
    pypi_stats_client = MagicMock(spec=PypiStatsClient)
    pypi_stats_client.get_download_stats = AsyncMock(
        return_value=DownloadStats(last_month=15000, last_week=500, last_day=50)
    )
    checker = PackageDownloadsChecker(pypi_stats_client)
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION))
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.SUCCESS
    assert result.message == "15,000 downloads from PyPI in the last month"


@pytest.mark.asyncio
async def test_low_download_count():
    pypi_stats_client = MagicMock(spec=PypiStatsClient)
    pypi_stats_client.get_download_stats = AsyncMock(
        return_value=DownloadStats(last_month=50, last_week=10, last_day=0)
    )
    checker = PackageDownloadsChecker(pypi_stats_client)
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION))
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.FAILURE
    assert result.message == "Only 50 downloads from PyPI in the last month"
