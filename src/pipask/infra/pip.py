import json
import logging
import os
import subprocess
import sys
import time

from pydantic import BaseModel, Field

from pipask._vendor.pip._internal.cli.main_parser import create_main_parser  # pyright: ignore
from pipask._vendor.pip._internal.commands import commands_dict  # pyright: ignore
from pipask._vendor.pip._internal.commands.install import InstallCommand  # pyright: ignore
from pipask.cli_args import InstallArgs, PipCommandArgs
from pipask.exception import HandoverToPipException, PipaskException, PipAskResolutionException

logger = logging.getLogger(__name__)


def _get_pip_command() -> list[str]:
    # Use the currently activated python so that the installation is executed into the activated environment
    venv_path = os.getenv("VIRTUAL_ENV")
    if venv_path:
        python_path = os.path.join(venv_path, "bin", "python")
        return [python_path, "-m", "pip"]
    else:
        return ["pip"]


def pip_pass_through(args: list[str]) -> None:
    pip_args = _get_pip_command() + args
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


def get_pip_install_report_from_pypi(args: InstallArgs) -> "PipInstallReport":
    """
    Get install report by getting all the metadata possible from PyPI or from safe sources such as built wheels.

    :raises PipAskResolutionException: if resolution of versions to install is not possible from safe sources
    """
    raise PipAskResolutionException("TODO")  # TODO


def get_pip_install_report_unsafe(parsed_args: InstallArgs) -> "PipInstallReport":
    """
    Get pip install report by directly invoking pip.
    This is unsafe because it may execute 3rd party code (setup.py or PEP 517 hooks) for source distributions.
    """
    pip_args = (
        _get_pip_command() + parsed_args.raw_args + ["--dry-run", "--quiet", "--report", "-"]
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
    download_info: InstallationReportItemDownloadInfo
    requested: bool
    is_yanked: bool
    is_direct: bool

    @property
    def pinned_requirement(self) -> str:
        return f"{self.metadata.name}=={self.metadata.version}"


class PipInstallReport(BaseModel):
    version: str
    install: list[InstallationReportItem]
