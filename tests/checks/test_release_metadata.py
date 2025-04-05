import pytest
from unittest.mock import AsyncMock

from pipask.checks.release_metadata import ReleaseMetadataChecker
from pipask.checks.types import CheckResultType
from pipask.infra.pypi import ReleaseResponse, ProjectInfo
from pipask.infra.pip import InstallationReportItem, InstallationReportItemMetadata, InstallationReportItemDownloadInfo

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
@pytest.mark.parametrize(
    "release_info,expected_type,expected_message",
    [
        (None, CheckResultType.FAILURE, "No release information available"),
        (
            ReleaseResponse(
                info=ProjectInfo(
                    name=PACKAGE_NAME,
                    version=PACKAGE_VERSION,
                    yanked=True,
                    yanked_reason="Security vulnerability",
                )
            ),
            CheckResultType.FAILURE,
            "The release is yanked (reason: Security vulnerability)",
        ),
        (
            ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION, yanked=True)),
            CheckResultType.FAILURE,
            "The release is yanked",
        ),
    ],
)
async def test_release_info_checks(release_info, expected_type, expected_message):
    checker = ReleaseMetadataChecker()
    release_info_future = AsyncMock(return_value=release_info)

    result = await checker.check(REPORT_ITEM, release_info_future())

    assert result.result_type == expected_type
    assert result.message == expected_message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "classifier",
    [
        "Development Status :: 1 - Planning",
        "Development Status :: 2 - Pre-Alpha",
        "Development Status :: 3 - Alpha",
        "Development Status :: 4 - Beta",
        "Development Status :: 7 - Inactive",
    ],
)
async def test_warning_classifiers(classifier):
    checker = ReleaseMetadataChecker()
    release_info = AsyncMock(
        return_value=ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
                yanked=False,
                classifiers=["License :: OSI Approved :: MIT License", classifier],
            )
        )
    )

    result = await checker.check(REPORT_ITEM, release_info())

    assert result.result_type == CheckResultType.WARNING
    assert result.message == f"Package is classified as {classifier}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "classifier",
    [
        "Development Status :: 5 - Production/Stable",
        "Development Status :: 6 - Mature",
    ],
)
async def test_success_classifiers(classifier):
    checker = ReleaseMetadataChecker()
    release_info = AsyncMock(
        return_value=ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
                yanked=False,
                classifiers=[classifier] if classifier else [],
            )
        )
    )

    result = await checker.check(REPORT_ITEM, release_info())

    assert result.result_type == CheckResultType.SUCCESS
    assert result.message == (
        "Package is classified as " + classifier if classifier else "No development status classifiers"
    )


@pytest.mark.asyncio
async def test_no_classifiers():
    checker = ReleaseMetadataChecker()
    release_info = AsyncMock(return_value=ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION)))

    result = await checker.check(REPORT_ITEM, release_info())

    assert result.result_type == CheckResultType.NEUTRAL
    assert result.message == "No development status classifiers"
