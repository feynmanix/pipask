from pipask.checks.types import CheckResult, CheckResultType
from pipask.checks.base_checker import Checker
from pipask.infra.pip_report import InstallationReportItem
from pipask.infra.pypi import VerifiedPypiReleaseInfo


# See https://pypi.org/classifiers/


class LicenseChecker(Checker):
    priority = 60

    @property
    def description(self) -> str:
        return "Checking package license"

    async def check(
        self, package: InstallationReportItem, verified_release_info: VerifiedPypiReleaseInfo
    ) -> CheckResult:
        pkg = package.pinned_requirement
        info = verified_release_info.release_response.info
        license = next((c for c in info.classifiers if c.startswith("License :: ")), None)
        if license:
            license = license.split(" :: ")[-1]
        if not license:
            license = info.license
        if license:
            return CheckResult(
                pkg,
                result_type=CheckResultType.NEUTRAL,
                message=f"Package is licensed under {license}",
                priority=self.priority,
            )

        return CheckResult(
            pkg,
            result_type=CheckResultType.WARNING,
            message="No license found in PyPI metadata - you may need to check manually",
            priority=self.priority,
        )
