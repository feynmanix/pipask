import os
import subprocess
import sys
import json
import time
import logging
from pydantic import BaseModel

from pipask.cli_helpers import ParsedArgs
from pipask.exception import PipaskException

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


def get_pip_report(parsed_args: ParsedArgs) -> "PipReport":
    if "install" not in parsed_args.other_args:
        raise PipaskException("unexpected command")
    pip_args = (
        _get_pip_command()
        + parsed_args.other_args
        + ["--dry-run", "--quiet", "--no-deps", "--report", "-"]  # No-deps to speed up the resolution
    )
    logger.debug(f"Running pip report subprocess: {' '.join(pip_args)}")
    start_time = time.time()
    try:
        result = subprocess.run(pip_args, check=True, text=True, capture_output=True)
        logger.debug(f"Pip report subprocess completed in {time.time() - start_time:.2f}s")
        report = PipReport.model_validate(json.loads(result.stdout))
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


class InstallationReportItemDownloadInfo(BaseModel):
    url: str


class InstallationReportItem(BaseModel):
    metadata: InstallationReportItemMetadata
    download_info: InstallationReportItemDownloadInfo
    requested: bool
    is_yanked: bool

    @property
    def pinned_requirement(self) -> str:
        return f"{self.metadata.name}=={self.metadata.version}"


class PipReport(BaseModel):
    version: str
    install: list[InstallationReportItem]
