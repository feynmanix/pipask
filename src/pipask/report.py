from rich.console import Console

from pipask.checks.types import CheckResultType, PackageCheckResults
from pipask.utils import format_link


def _get_worst_result(package_result: PackageCheckResults) -> CheckResultType:
    return (
        CheckResultType.get_worst(*(result.result_type for result in package_result.results)) or CheckResultType.SUCCESS
    )


def _format_requirement_heading(package_result: PackageCheckResults) -> str:
    worst_result_color = _get_worst_result(package_result).rich_color
    formatted_requirement = (
        f"{package_result.name}=={format_link(package_result.version, package_result.pypi_url)}"
        if package_result.pypi_url
        else f"{package_result.name}=={package_result.version}"
    )
    bold = "" if package_result.is_transitive_dependency else "[bold]"
    return f"  {bold}\\[[{worst_result_color}]{formatted_requirement}[/{worst_result_color}]]"


def _format_check_result(result_type: CheckResultType, message: str) -> str:
    color = "default" if result_type is CheckResultType.SUCCESS else result_type.rich_color
    return f"    {result_type.rich_icon} [{color}]{message}"


def print_report(package_results: list[PackageCheckResults], console: Console) -> None:
    console.print("\nPackage check results:")
    requested_deps = [p for p in package_results if not p.is_transitive_dependency]
    for package_result in requested_deps:
        console.print(_format_requirement_heading(package_result))
        for check_result in package_result.results:
            console.print(_format_check_result(check_result.result_type, check_result.message))

    transitive_deps_with_warning_or_worse = [
        p
        for p in package_results
        if p.is_transitive_dependency
        and len(p.results)
        and _get_worst_result(p) not in {CheckResultType.NEUTRAL, CheckResultType.SUCCESS}
    ]
    if len(transitive_deps_with_warning_or_worse):
        console.print("Vulnerable transitive dependencies:")
    for package_result in transitive_deps_with_warning_or_worse:
        console.print(_format_requirement_heading(package_result))
        for check_result in package_result.results:
            console.print(_format_check_result(check_result.result_type, check_result.message))
