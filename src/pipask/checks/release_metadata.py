from pipask.checks.types import CheckResult, CheckResultType
from pipask.checks.base_checker import Checker
from pipask.infra.pip_report import InstallationReportItem
from pipask.infra.pypi import ReleaseResponse
from typing import Awaitable


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
    priority = 50

    @property
    def description(self) -> str:
        return "Checking release metadata"

    async def check(
        self, package: InstallationReportItem, release_info_future: Awaitable[ReleaseResponse | None]
    ) -> CheckResult:
        pkg = package.pinned_requirement
        resolved_release_info = await release_info_future
        if resolved_release_info is None:
            return CheckResult(
                pkg,
                result_type=CheckResultType.FAILURE,
                message="No release information available",
                priority=self.priority,
            )
        if resolved_release_info.info.yanked:
            reason = (
                f" (reason: {resolved_release_info.info.yanked_reason})"
                if resolved_release_info.info.yanked_reason
                else ""
            )
            return CheckResult(
                pkg,
                result_type=CheckResultType.FAILURE,
                message=f"The release is yanked{reason}",
                priority=self.priority,
            )
        if classifier := _first_matching_classifier(resolved_release_info, _WARNING_CLASSIFIERS):
            return CheckResult(
                pkg,
                result_type=CheckResultType.WARNING,
                message=f"Package is classified as {classifier}",
                priority=self.priority,
            )
        if classifier := _first_matching_classifier(resolved_release_info, _SUCCESS_CLASSIFIERS):
            return CheckResult(
                pkg,
                result_type=CheckResultType.SUCCESS,
                message=f"Package is classified as {classifier}",
                priority=self.priority,
            )
        return CheckResult(
            pkg,
            result_type=CheckResultType.NEUTRAL,
            message="No development status classifiers",
            priority=self.priority,
        )


def _first_matching_classifier(release_info: ReleaseResponse, classifiers: list[str]) -> str | None:
    for classifier in classifiers:
        if classifier in release_info.info.classifiers:
            return classifier
    return None
