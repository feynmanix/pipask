from pipask.checks.base_checker import Checker
from pipask.checks.types import CheckResult, CheckResultType
from pipask.infra.pypi import VerifiedPypiReleaseInfo

# See https://pypi.org/classifiers/


class LicenseChecker(Checker):
    @property
    def description(self) -> str:
        return "Checking package license"

    async def check(self, verified_release_info: VerifiedPypiReleaseInfo) -> CheckResult:
        info = verified_release_info.release_response.info
        license = next((c for c in info.classifiers if c.startswith("License :: ")), None)
        if license:
            license = license.split(" :: ")[-1]
        if not license:
            license = info.license
        if license:
            return CheckResult(
                result_type=CheckResultType.NEUTRAL,
                message=f"Package is licensed under {license}",
            )

        return CheckResult(
            result_type=CheckResultType.WARNING,
            message="No license found in PyPI metadata - you may need to check manually",
        )
