from rich.console import Console

from pipask.checks.types import CheckResultType, PackageCheckResults


def print_report(package_results: list[PackageCheckResults], console: Console) -> None:
    console.print("\nPackage check results:")
    for package_result in package_results:
        worst_result = (
            CheckResultType.get_worst(*(result.result_type for result in package_result.results))
            or CheckResultType.SUCCESS
        )
        worst_result_color = worst_result.rich_color
        formatted_requirement = (
            f"{package_result.name}==[link={package_result.pypi_url}]{package_result.version}[/link]"
            if package_result.pypi_url
            else f"{package_result.name}=={package_result.version}"
        )
        console.print(f"  [bold]\\[[{worst_result_color}]{formatted_requirement}[/{worst_result_color}]]")

        for check_result in package_result.results:
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
