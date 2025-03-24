import asyncio
import logging
import os
from contextlib import aclosing

from pipc.cli import ParsedArgs
from pipc.infra.pip import pip_pass_through, get_pip_report
from pipc.infra.pypi import PypiClient, ReleaseResponse
import sys

import click

from pipc.infra.repo_client import RepoClient

# Get log level from environment variable, default to INFO if not set
log_level = os.getenv("PIPC_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("pipc").setLevel(getattr(logging, log_level, logging.INFO))


# (see relevant pip commands at https://pip.pypa.io/en/stable/cli/pip_install/)
@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option("-h", "--help", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--report", type=str)
@click.pass_context
def cli(ctx: click.Context, help: bool, dry_run: bool, report: str) -> None:
    """pipc - safer python package installation with audit and consent."""
    all_args = sys.argv[1:]
    is_install_command = len(ctx.args) > 0 and ctx.args[0] == "install"
    if not is_install_command or help or dry_run:
        # Only run when actually installing something
        pip_pass_through(all_args)
        return
    parsed_args = ParsedArgs.from_click_context(ctx)
    asyncio.run(execute_checks(parsed_args))
    if click.confirm("Do you want to continue?"):
        pip_pass_through(all_args)
    else:
        click.echo("Aborted!")
        sys.exit(2)


async def execute_checks(parsed_args: ParsedArgs) -> None:
    click.echo("Checking stuff...")
    report = get_pip_report(parsed_args)
    packages_to_install = [package for package in report.install if package.requested]
    async with aclosing(PypiClient()) as pypi_client, aclosing(RepoClient()) as repo_client:
        releases_info_futures = [
            pypi_client.get_release_info(package.metadata.name, package.metadata.version)
            for package in packages_to_install
        ]
        releases_info: list[ReleaseResponse | None] = await asyncio.gather(*releases_info_futures)
        for release_info in releases_info:
            if release_info is None:
                continue
            repo_url = release_info.info.project_urls.recognized_repo_url()
            if repo_url is None:
                continue  # TODO
            repo_info = await repo_client.get_repo_info(repo_url)
            if repo_info is None:
                continue  # TODO
            print(release_info.info.name, "number of stars:", repo_info.star_count)


if __name__ == "__main__":
    cli()
