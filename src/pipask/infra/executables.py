import shutil
import subprocess
from functools import cache
import logging

logger = logging.getLogger(__name__)

_fallback_python_command = "python3"


@cache # This is cleared between tests
def get_pip_python_executable() -> str:
    # We can't use sys.executable because it may be a different python than the one we are using
    # pip debug is not guaranteed to be stable, but hopefully this won't change
    pip_debug_output = subprocess.run(["pip", "debug"], check=True, text=True, capture_output=True)
    executable_line = next(line for line in pip_debug_output.stdout.splitlines() if line.startswith("sys.executable:"))
    if not executable_line:
        # Could happen if pip debug output changes?
        logger.warning("Could not reliably determine python executable")
        return _fallback_python_command
    return executable_line[len("sys.executable:") :].strip()


def get_pip_command() -> list[str]:
    python_executable = get_pip_python_executable()
    if python_executable == _fallback_python_command:
        return [shutil.which("pip")]
    return [python_executable, "-m", "pip"]
