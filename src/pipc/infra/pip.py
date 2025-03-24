import subprocess
import sys
import json
import click
from pydantic import BaseModel

from pipc.cli import ParsedArgs
from pipc.exception import PipcException


def _get_python_executable() -> str:
    python_executable = sys.executable
    if not python_executable:
        click.echo("No Python executable found.")
        sys.exit(1)
    return python_executable


def pip_pass_through(args: list[str]) -> None:
    pip_args = [_get_python_executable(), "-m", "pip"] + args
    try:
        subprocess.run(pip_args, check=True, text=True, stdout=sys.stdout, stderr=sys.stderr)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)  # Preserve the original exit code


def get_pip_report(parsed_args: ParsedArgs) -> "PipReport":
    if "install" not in parsed_args.other_args:
        raise PipcException("unexpected command")
    pip_args = (
        [_get_python_executable(), "-m", "pip"] + parsed_args.other_args + ["--dry-run", "--quiet", "--report", "-"]
    )
    try:
        result = subprocess.run(pip_args, check=True, text=True, capture_output=True)
        report = PipReport.model_validate(json.loads(result.stdout))
    except subprocess.CalledProcessError as e:
        raise PipcException(f"Error while getting pip report: {e}") from e
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


class PipReport(BaseModel):
    version: str
    install: list[InstallationReportItem]
