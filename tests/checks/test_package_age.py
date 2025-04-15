import datetime
from unittest.mock import AsyncMock

import pytest

from pipask.checks.package_age import PackageAge
from pipask.checks.types import CheckResult, CheckResultType
from pipask.infra.pypi import (
    Distribution,
    DistributionsResponse,
    ProjectInfo,
    ProjectReleaseFile,
    ReleaseResponse,
    VerifiedPypiReleaseInfo,
)

PACKAGE_NAME = "package"
PACKAGE_VERSION = "1.0.0"


@pytest.mark.asyncio
async def test_no_distributions():
    pypi_client = AsyncMock()
    pypi_client.get_distributions.return_value = None
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION))
    )
    checker = PackageAge(pypi_client)

    result = await checker.check(release_info)

    assert result == CheckResult(
        result_type=CheckResultType.FAILURE,
        message="No distributions information available",
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
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION))
    )

    result = await checker.check(release_info)

    assert result == CheckResult(
        result_type=CheckResultType.WARNING,
        message="A newly published package: created only 10 days ago",
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
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(
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

    result = await checker.check(release_info)

    assert result == CheckResult(
        result_type=CheckResultType.WARNING,
        message="The release is older than a year: 400 days old",
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
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(
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

    result = await checker.check(release_info)

    assert result == CheckResult(
        result_type=CheckResultType.SUCCESS,
        message="The release is 1 day old",
    )
