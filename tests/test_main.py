import os
import subprocess
import venv
from pathlib import Path
from unittest.mock import patch

import pytest

from pipask.main import main


@pytest.mark.integration
def test_installs_package_in_venv(tmp_path: Path):
    # Prepare virtual environment
    venv_path = tmp_path / "venv"
    env_builder = venv.EnvBuilder(with_pip=True, system_site_packages=False)
    venv_ctx = env_builder.ensure_directories(venv_path)
    env_builder.create(venv_path)
    venv_python: str = venv_ctx.env_exe

    # Prepare arguments
    args = ["install", "--no-input", "pyfluent-iterables"]

    # "Activate" the virtual environment
    path_env_var = str(venv_path / "bin") + os.pathsep + os.environ["PATH"]
    with patch.dict(os.environ, {"PATH": path_env_var, "VIRTUAL_ENV": str(venv_path)}):
        # Act
        with patch("rich.prompt.Confirm.ask", return_value=True):
            main(args)

    # Verify the package is actually installed in the venv
    assert is_installed(venv_python, "pyfluent_iterables")


def is_installed(executable: str, package_name: str) -> bool:
    result = subprocess.run(
        [executable, "-c", f"import {package_name.replace('-', '_')}"], check=False, capture_output=True, text=True
    )
    return result.returncode == 0
