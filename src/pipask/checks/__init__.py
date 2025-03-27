import abc
from typing import Awaitable

from pipask.checks.types import CheckResult
from pipask.infra.pip import InstallationReportItem
from pipask.infra.pypi import ReleaseResponse


class Checker(abc.ABC):
    @abc.abstractmethod
    async def check(
        self, package: InstallationReportItem, release_info_future: Awaitable[ReleaseResponse | None]
    ) -> CheckResult:
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        pass
