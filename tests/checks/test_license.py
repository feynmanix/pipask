import pytest
from unittest.mock import AsyncMock

from pipask.checks.license import LicenseChecker
from pipask.checks.types import CheckResultType
from pipask.infra.pypi import ReleaseResponse, ProjectInfo
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
async def test_no_release_info():
    checker = LicenseChecker()
    release_info_future = AsyncMock(return_value=None)

    result = await checker.check(REPORT_ITEM, release_info_future())

    assert result.result_type == CheckResultType.FAILURE
    assert result.message == "No release information available"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "classifiers,metadata_license,expected_message",
    [
        (["License :: OSI Approved :: MIT License"], "MIT", "Package is licensed under MIT License"),
        (
            ["License :: OSI Approved :: Apache Software License"],
            "ASL",
            "Package is licensed under Apache Software License",
        ),
        (["License :: OSI Approved :: BSD License"], "BSD", "Package is licensed under BSD License"),
        (["License :: Unexpected"], None, "Package is licensed under Unexpected"),
        (["License :: OSI Approved :: BSD License"], None, "Package is licensed under BSD License"),
        ([], "MIT", "Package is licensed under MIT"),
    ],
)
async def test_license_classifiers(classifiers: list[str], metadata_license: str, expected_message: str):
    checker = LicenseChecker()
    release_info_future = AsyncMock(
        return_value=ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
                classifiers=classifiers,
                license=metadata_license,
            )
        )
    )

    result = await checker.check(REPORT_ITEM, release_info_future())

    assert result.result_type == CheckResultType.NEUTRAL
    assert result.message == expected_message


@pytest.mark.asyncio
async def test_no_license():
    checker = LicenseChecker()
    release_info_future = AsyncMock(
        return_value=ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
                classifiers=[],
                license=None,
            )
        )
    )

    result = await checker.check(REPORT_ITEM, release_info_future())

    assert result.result_type == CheckResultType.WARNING
    assert result.message == "No license found in PyPI metadata - you may need to check manually"
