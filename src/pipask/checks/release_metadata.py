from pipask.checks.base_checker import Checker
from pipask.checks.types import CheckResult, CheckResultType
from pipask.infra.pypi import ReleaseResponse, VerifiedPypiReleaseInfo

# See https://pypi.org/classifiers/
_WARNING_CLASSIFIERS = [
    "Development Status :: 1 - Planning",
    "Development Status :: 2 - Pre-Alpha",
    "Development Status :: 3 - Alpha",
    "Development Status :: 4 - Beta",
    "Development Status :: 7 - Inactive",
]
_SUCCESS_CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Development Status :: 6 - Mature",
]


class ReleaseMetadataChecker(Checker):
    @property
    def description(self) -> str:
        return "Checking release metadata"

    async def check(self, verified_release_info: VerifiedPypiReleaseInfo) -> CheckResult:
        if verified_release_info.release_response.info.yanked:
            reason = (
                f" (reason: {verified_release_info.release_response.info.yanked_reason})"
                if verified_release_info.release_response.info.yanked_reason
                else ""
            )
            return CheckResult(
                result_type=CheckResultType.FAILURE,
                message=f"The release is yanked{reason}",
            )
        if classifier := _first_matching_classifier(verified_release_info.release_response, _WARNING_CLASSIFIERS):
            return CheckResult(
                result_type=CheckResultType.WARNING,
                message=f"Package is classified as {classifier}",
            )
        if classifier := _first_matching_classifier(verified_release_info.release_response, _SUCCESS_CLASSIFIERS):
            return CheckResult(
                result_type=CheckResultType.SUCCESS,
                message=f"Package is classified as {classifier}",
            )
        return CheckResult(
            result_type=CheckResultType.NEUTRAL,
            message="No development status classifiers",
        )


def _first_matching_classifier(release_info: ReleaseResponse, classifiers: list[str]) -> str | None:
    for classifier in classifiers:
        if classifier in release_info.info.classifiers:
            return classifier
    return None
