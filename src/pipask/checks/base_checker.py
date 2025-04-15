import abc
from typing import Awaitable

from pipask.checks.types import CheckResult
from pipask.infra.pip_report import InstallationReportItem
from pipask.infra.pypi import VerifiedPypiReleaseInfo


class Checker(abc.ABC):
    @abc.abstractmethod
    async def check(
        self, package: InstallationReportItem, verified_release_info_future: Awaitable[VerifiedPypiReleaseInfo | None]
    ) -> "CheckResult":
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        pass
