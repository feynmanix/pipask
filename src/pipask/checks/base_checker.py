import abc

from pipask.checks.types import CheckResult
from pipask.infra.pypi import VerifiedPypiReleaseInfo


class Checker(abc.ABC):
    @abc.abstractmethod
    async def check(self, verified_release_info: VerifiedPypiReleaseInfo) -> CheckResult:
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        pass
