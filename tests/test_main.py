import subprocess
from unittest.mock import patch

import pytest

from pipask.main import main


@pytest.mark.integration
def test_installs_package_in_venv(temp_venv_python: str, clear_venv_dependent_caches):
    clear_venv_dependent_caches()
    args = ["install", "--no-input", "pyfluent-iterables"]

    # Act
    with patch("rich.prompt.Confirm.ask", return_value=True):
        main(args)

    # Verify the package is actually installed in the venv
    assert is_installed(temp_venv_python, "pyfluent_iterables")


def is_installed(executable: str, package_name: str) -> bool:
    result = subprocess.run(
        [executable, "-c", f"import {package_name.replace('-', '_')}"], check=False, capture_output=True, text=True
    )
    return result.returncode == 0
