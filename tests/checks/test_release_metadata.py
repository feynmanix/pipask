import pytest

from pipask.checks.release_metadata import ReleaseMetadataChecker
from pipask.checks.types import CheckResultType
from pipask.infra.pypi import ProjectInfo, ReleaseResponse, VerifiedPypiReleaseInfo

PACKAGE_NAME = "package"
PACKAGE_VERSION = "1.0.0"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "release_info,expected_type,expected_message",
    [
        (
            VerifiedPypiReleaseInfo(
                ReleaseResponse(
                    info=ProjectInfo(
                        name=PACKAGE_NAME,
                        version=PACKAGE_VERSION,
                        yanked=True,
                        yanked_reason="Security vulnerability",
                    )
                ),
                "file.whl",
            ),
            CheckResultType.FAILURE,
            "The release is yanked (reason: Security vulnerability)",
        ),
        (
            VerifiedPypiReleaseInfo(
                ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION, yanked=True)),
                "file.whl",
            ),
            CheckResultType.FAILURE,
            "The release is yanked",
        ),
    ],
)
async def test_release_info_checks(release_info, expected_type, expected_message):
    checker = ReleaseMetadataChecker()

    result = await checker.check(release_info)

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
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
                yanked=False,
                classifiers=["License :: OSI Approved :: MIT License", classifier],
            )
        ),
        "file.whl",
    )

    result = await checker.check(release_info)

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
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(
            info=ProjectInfo(
                name=PACKAGE_NAME,
                version=PACKAGE_VERSION,
                yanked=False,
                classifiers=[classifier] if classifier else [],
            )
        ),
        "file.whl",
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.SUCCESS
    assert result.message == (
        "Package is classified as " + classifier if classifier else "No development status classifiers"
    )


@pytest.mark.asyncio
async def test_no_classifiers():
    checker = ReleaseMetadataChecker()
    release_info = VerifiedPypiReleaseInfo(
        ReleaseResponse(info=ProjectInfo(name=PACKAGE_NAME, version=PACKAGE_VERSION)),
        "file.whl",
    )

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.NEUTRAL
    assert result.message == "No development status classifiers"
