import pytest

from pipask.checks.license import LicenseChecker
from pipask.checks.types import CheckResultType
from pipask.infra.pypi import ProjectInfo, ReleaseResponse, VerifiedPypiReleaseInfo

PACKAGE_NAME = "package"
PACKAGE_VERSION = "1.0.0"


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
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
                classifiers=classifiers,
                license=metadata_license,
            )
        ),
        "file.whl",
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.NEUTRAL
    assert result.message == expected_message


@pytest.mark.asyncio
async def test_no_license():
    checker = LicenseChecker()
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
                classifiers=[],
                license=None,
            )
        ),
        "file.whl",
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.WARNING
    assert result.message == "No license found in PyPI metadata - you may need to check manually"
