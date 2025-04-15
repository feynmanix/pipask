import datetime

from pipask.checks.base_checker import Checker
from pipask.checks.types import CheckResult, CheckResultType
from pipask.infra.pypi import PypiClient, VerifiedPypiReleaseInfo

_TOO_NEW_DAYS = 22
_TOO_OLD_DAYS = 365


class PackageAge(Checker):
    def __init__(self, pypi_client: PypiClient):
        self._pypi_client = pypi_client

    @property
    def description(self) -> str:
        return "Checking package age"

    async def check(self, verified_release_info: VerifiedPypiReleaseInfo) -> CheckResult:
        distributions = await self._pypi_client.get_distributions(verified_release_info.name)
        if distributions is None:
            return CheckResult(
                result_type=CheckResultType.FAILURE,
                message="No distributions information available",
            )
        oldest_distribution = min(distributions.files, key=lambda x: x.upload_time)
        max_age_days = (datetime.datetime.now(datetime.timezone.utc) - oldest_distribution.upload_time).days
        if max_age_days < _TOO_NEW_DAYS:
            return CheckResult(
                result_type=CheckResultType.WARNING,
                message=f"A newly published package: created only {max_age_days} days ago",
            )

        newest_release_file = max(verified_release_info.release_response.urls, key=lambda x: x.upload_time)
        release_age_days = (datetime.datetime.now(datetime.timezone.utc) - newest_release_file.upload_time).days
        if release_age_days > _TOO_OLD_DAYS:
            return CheckResult(
                result_type=CheckResultType.WARNING,
                message=f"The release is older than a year: {release_age_days} days old",
            )
        return CheckResult(
            result_type=CheckResultType.SUCCESS,
            message=f"The release is {release_age_days} day{'' if release_age_days == 1 else 's'} old",
        )
