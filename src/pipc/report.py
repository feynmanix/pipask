from rich.console import Console

from pipc.checks.types import CheckResult, CheckResultType


def print_report(check_results: list[CheckResult], console: Console) -> None:
    console.print("\nPackage check results:")
    packages = set(result.pinned_requirement for result in check_results)
    for package in packages:
        package_results = [result for result in check_results if result.pinned_requirement == package]
        worst_result = (
            CheckResultType.get_worst(*(result.result_type for result in package_results)) or CheckResultType.SUCCESS
        )
        worst_result_color = worst_result.rich_color
        console.print(f"  [bold]\\[[{worst_result_color}]{package}[/{worst_result_color}]]")

        # TODO: make sure these are sorted
        for check_result in package_results:
            color = (
                "default"
                if check_result.result_type is CheckResultType.SUCCESS
                else check_result.result_type.rich_color
            )
            message_parts = [
                "    ",
                check_result.result_type.rich_icon,
                " ",
                "[" + color + "]",
                check_result.message,
            ]
            console.print("".join(message_parts))