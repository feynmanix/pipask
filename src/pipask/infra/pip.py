import json
import subprocess
from functools import cache

import sys
import time
from typing import Optional, Sequence

from pydantic import BaseModel, Field

import pipask._vendor.pip._internal.utils.logging
from pipask._vendor.pip._internal.cli.main_parser import create_main_parser
from pipask._vendor.pip._internal.commands import commands_dict
from pipask._vendor.pip._internal.commands.install import InstallCommand
from pipask._vendor.pip._internal.models.installation_report import InstallationReport
from pipask._vendor.pip._internal.req.req_install import InstallRequirement
from pipask._vendor.pip._internal.utils.direct_url_helpers import direct_url_for_editable, direct_url_from_link
from pipask._vendor.pip._internal.utils.temp_dir import (
    global_tempdir_manager,
    tempdir_registry,
)
from pipask.cli_args import InstallArgs, PipCommandArgs
from pipask.exception import HandoverToPipException, PipaskException

logger = pipask._vendor.pip._internal.utils.logging.getLogger(__name__)

_fallback_python_command = "python3"


@cache
def get_pip_python_executable() -> str:
    # We can't use sys.executable because it may be a different python than the one we are using
    # pip debug is not guaranteed to be stable, but hopefully this won't change
    pip_debug_output = subprocess.run(["pip", "debug"], check=True, text=True, capture_output=True)
    executable_line = next(line for line in pip_debug_output.stdout.splitlines() if line.startswith("sys.executable:"))
    if not executable_line:
        # Could happen if pip debug output changes?
        logger.warning("Could not reliably determine python executable")
        return _fallback_python_command
    return executable_line[len("sys.executable:"):].strip()


def get_pip_command() -> list[str]:
    python_executable = get_pip_python_executable()
    if python_executable == _fallback_python_command:
        return ["pip"]
    return [python_executable, "-m", "pip"]


def pip_pass_through(args: list[str]) -> None:
    pip_args = get_pip_command() + args
    logger.debug(f"Running subprocess: {' '.join(pip_args)}")
    start_time = time.time()
    try:
        subprocess.run(pip_args, check=True, text=True, stdout=sys.stdout, stderr=sys.stderr)
        logger.debug(f"Subprocess completed in {time.time() - start_time:.2f}s")
    except subprocess.CalledProcessError as e:
        logger.debug(f"Subprocess failed after {time.time() - start_time:.2f}s with exit code {e.returncode}")
        sys.exit(e.returncode)


def parse_pip_arguments(args: list[str]) -> PipCommandArgs:
    """
    :raises HandoverToPipException if processing should not continue - hand over to pip to show the message
    """
    # Modified version of pip.cli.main_parser.parse_command
    parser = create_main_parser()
    general_options, args_else = parser.parse_args(args)
    # --version
    if general_options.version:
        raise HandoverToPipException("--version")

    # pip || pip help -> print_help()
    if not args_else or (args_else[0] == "help" and len(args_else) == 1):
        raise HandoverToPipException("help")

    # the subcommand name
    cmd_name = args_else[0]

    if cmd_name not in commands_dict:
        raise HandoverToPipException("unknown command")

    # all the args without the subcommand
    cmd_args = args[:]
    cmd_args.remove(cmd_name)

    return PipCommandArgs(command_name=cmd_name, command_args=cmd_args, raw_args=args)


def parse_pip_install_arguments(args: PipCommandArgs) -> InstallArgs:
    if args.command_name != "install":
        raise PipaskException("unexpected command " + args.command_name)

    install_command = InstallCommand(name="install", summary="", isolated=("--isolated" in args.command_args))
    install_options, install_args = install_command.parse_args(args.command_args)
    return InstallArgs(raw_args=args.raw_args, raw_options=install_options, install_args=install_args)


def _get_download_info(req: InstallRequirement) -> Optional["InstallationReportItemDownloadInfo"]:
    download_info = None
    if req.download_info is not None:
        download_info = req.download_info
    elif req.editable:
        download_info = direct_url_for_editable(req.unpacked_source_directory)
    elif req.link is not None:
        download_info = direct_url_from_link(req.link)

    if download_info is None:
        return None
    return InstallationReportItemDownloadInfo.model_validate(download_info.to_dict())


def _get_metadata_dict(req: InstallRequirement) -> dict[str, str]:
    if req.metadata_distribution is not None:
        return req.metadata_distribution.metadata_dict
    return req.get_dist().metadata_dict


def get_pip_install_report_from_pypi(args: InstallArgs) -> "PipInstallReport":
    """
    Get install report by getting all the metadata possible from PyPI or from safe sources such as built wheels.

    :raises PipAskResolutionException: if resolution of versions to install is not possible from safe sources
    """

    install_command = InstallCommand(name="install", summary="", isolated=args.isolated)
    with install_command.main_context():
        # Modified version of pip._internal.cli.base_command.Command.main()
        install_command.tempdir_registry = install_command.enter_context(tempdir_registry())
        install_command.enter_context(global_tempdir_manager())
        install_command.verbosity = args.verbose - args.quiet

        install_requirements: int | Sequence[InstallRequirement] = install_command.run(args.options, args.install_args)
        if isinstance(install_requirements, int):
            raise RuntimeError("install command did not return install requirements")

        install_report_items = [
            # Similar to pipask._vendor.pip._internal.models.installation_report.InstallationReport
            InstallationReportItem(
                requested=ireq.user_supplied,
                is_direct=ireq.is_direct,
                is_yanked=ireq.link.is_yanked if ireq.link else False,
                download_info=_get_download_info(ireq),
                metadata=InstallationReportItemMetadata.model_validate(_get_metadata_dict(ireq)),
            )
            for ireq in install_requirements
        ]
    return PipInstallReport(version=InstallationReport([]).to_dict()["version"], install=install_report_items)


def get_pip_install_report_unsafe(parsed_args: InstallArgs) -> "PipInstallReport":
    """
    Get pip install report by directly invoking pip.
    This is unsafe because it may execute 3rd party code (setup.py or PEP 517 hooks) for source distributions.
    """
    pip_args = (
        get_pip_command() + parsed_args.raw_args + ["--dry-run", "--quiet", "--report", "-"]
        # Would be nice to use --no-deps to speed up the resolution, but that may give versions
        # different from will actually be installed
    )
    logger.debug(f"Running pip report subprocess: {' '.join(pip_args)}")
    start_time = time.time()
    try:
        result = subprocess.run(pip_args, check=True, text=True, capture_output=True)
        logger.debug(f"Pip report subprocess completed in {time.time() - start_time:.2f}s")
        report = PipInstallReport.model_validate(json.loads(result.stdout))
    except subprocess.CalledProcessError as e:
        logger.debug(
            f"Pip report subprocess failed after {time.time() - start_time:.2f}s with exit code {e.returncode}"
        )
        raise PipaskException(f"Error while getting pip report: {e}") from e
    return report


# See https://pip.pypa.io/en/stable/reference/installation-report/
class InstallationReportItemMetadata(BaseModel):
    name: str
    version: str
    license: str | None = None
    classifier: list[str] = Field(default_factory=list)


class InstallationReportArchiveInfo(BaseModel):
    hash: str | None = None
    hashes: dict[str, str] | None = None


class InstallationReportItemDownloadInfo(BaseModel):
    url: str
    archive_info: InstallationReportArchiveInfo | None = None


class InstallationReportItem(BaseModel):
    metadata: InstallationReportItemMetadata
    download_info: InstallationReportItemDownloadInfo | None
    requested: bool
    is_yanked: bool
    is_direct: bool

    @property
    def pinned_requirement(self) -> str:
        return f"{self.metadata.name}=={self.metadata.version}"


class PipInstallReport(BaseModel):
    version: str
    install: list[InstallationReportItem]
