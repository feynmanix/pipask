import datetime
import pytest
from unittest.mock import AsyncMock

from pipask.checks.package_age import PackageAge
from pipask.checks.types import CheckResult, CheckResultType
from pipask.infra.pypi import ReleaseResponse, ProjectInfo, DistributionsResponse, Distribution, ProjectReleaseFile
from pipask.infra.pip_report import InstallationReportItem, InstallationReportItemDownloadInfo, \
    InstallationReportItemMetadata

PACKAGE_NAME = "package"
PACKAGE_VERSION = "1.0.0"
REPORT_ITEM = InstallationReportItem(
    metadata=InstallationReportItemMetadata(name=PACKAGE_NAME, version=PACKAGE_VERSION),
    download_info=InstallationReportItemDownloadInfo(url="https://example.com"),
    requested=True,
    is_yanked=False,
    is_direct=True,
)


@pytest.mark.asyncio
async def test_no_distributions():
    pypi_client = AsyncMock()
    pypi_client.get_distributions.return_value = None
    release_info_future = AsyncMock(return_value=None)
    checker = PackageAge(pypi_client)

    result = await checker.check(REPORT_ITEM, release_info_future())

    assert result == CheckResult(
        pinned_requirement="package==1.0.0",
        result_type=CheckResultType.FAILURE,
        message="No distributions information available",
        priority=PackageAge.priority,
    )


@pytest.mark.asyncio
async def test_too_new_package():
    pypi_client = AsyncMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    pypi_client.get_distributions.return_value = DistributionsResponse(
        files=[
            Distribution(
                filename="package-1.0.0.tar.gz",
                **{"upload-time": now - datetime.timedelta(days=10)},
                yanked=False,
            )
        ],
    )
    checker = PackageAge(pypi_client)
    release_info_future = AsyncMock(return_value=None)

    result = await checker.check(REPORT_ITEM, release_info_future())

    assert result == CheckResult(
        pinned_requirement="package==1.0.0",
        result_type=CheckResultType.WARNING,
        message="A newly published package: created only 10 days ago",
        priority=PackageAge.priority,
    )


@pytest.mark.asyncio
async def test_too_old_release():
    pypi_client = AsyncMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    pypi_client.get_distributions.return_value = DistributionsResponse(
        files=[
            Distribution(
                filename="package-1.0.0.tar.gz",
                **{"upload-time": now - datetime.timedelta(days=400)},
                yanked=False,
            ),
            Distribution(
                filename="package-2.0.0.tar.gz",
                **{"upload-time": now - datetime.timedelta(days=100)},
                yanked=False,
            ),
        ],
    )
    checker = PackageAge(pypi_client)
    release_info_future = AsyncMock(
        return_value=ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
            ),
            urls=[
                ProjectReleaseFile(
                    filename="package-1.0.0.tar.gz",
                    upload_time_iso_8601=now - datetime.timedelta(days=400),
                    yanked=False,
                )
            ],
        )
    )

    result = await checker.check(REPORT_ITEM, release_info_future())

    assert result == CheckResult(
        pinned_requirement="package==1.0.0",
        result_type=CheckResultType.WARNING,
        message="The release is older than a year: 400 days old",
        priority=PackageAge.priority,
    )


@pytest.mark.asyncio
async def test_successful_check():
    pypi_client = AsyncMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    pypi_client.get_distributions.return_value = DistributionsResponse(
        files=[
            # Include both a recent and an old distribution
            Distribution(
                filename="package-1.0.0.tar.gz",
                **{"upload-time": now - datetime.timedelta(days=25)},
                yanked=False,
            ),
            Distribution(
                filename="package-2.0.0.tar.gz",
                **{"upload-time": now - datetime.timedelta(days=1)},
                yanked=False,
            ),
        ],
    )
    checker = PackageAge(pypi_client)
    release_info_future = AsyncMock(
        return_value=ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
            ),
            urls=[
                ProjectReleaseFile(
                    filename="package-2.0.0.tar.gz",
                    upload_time_iso_8601=now - datetime.timedelta(days=1),
                    yanked=False,
                )
            ],
        )
    )

    result = await checker.check(REPORT_ITEM, release_info_future())

    assert result == CheckResult(
        pinned_requirement="package==1.0.0",
        result_type=CheckResultType.SUCCESS,
        message="The release is 1 day old",
        priority=PackageAge.priority,
    )
