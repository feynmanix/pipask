from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CheckResultType(str, Enum):
    SUCCESS = ("success", "green", "[green]✔[/green]")
    FAILURE = ("failure", "red", "[red]✖[/red]")
    WARNING = ("warning", "yellow", "[yellow bold]![/yellow bold]")
    NEUTRAL = ("neutral", "default", "✔")
    ERROR = ("error", "red", "[red]![/red]")

    rich_color: str
    rich_icon: str

    def __new__(cls, value: str, rich_color: str, rich_icon: str):
        obj = str.__new__(cls, [value])
        obj._value_ = value
        obj.rich_color = rich_color
        obj.rich_icon = rich_icon
        return obj

    @staticmethod
    def get_worst(*results: Optional["CheckResultType"]) -> Optional["CheckResultType"]:
        if any(result is CheckResultType.FAILURE for result in results):
            return CheckResultType.FAILURE
        if any(result is CheckResultType.ERROR for result in results):
            return CheckResultType.ERROR
        if any(result is CheckResultType.WARNING for result in results):
            return CheckResultType.WARNING
        if any(result is CheckResultType.NEUTRAL for result in results):
            return CheckResultType.NEUTRAL
        if any(result is CheckResultType.SUCCESS for result in results):
            return CheckResultType.SUCCESS
        return None


@dataclass
class CheckResult:
    result_type: CheckResultType
    message: str


@dataclass
class PackageCheckResults:
    name: str
    version: str
    results: list[CheckResult]
    is_transitive_dependency: bool
    pypi_url: str | None = None
