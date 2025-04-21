import importlib
import os
import subprocess
import venv
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from _pytest.tmpdir import TempPathFactory

from pipask._vendor.pip._internal.locations import get_bin_prefix
from pipask.infra.executables import get_pip_python_executable
from pipask.infra.sys_values import get_pip_sys_values


def _clear_venv_dependent_caches():
    get_pip_python_executable.cache_clear()
    get_pip_sys_values.cache_clear()
    from pipask._vendor.pip._vendor import pkg_resources

    importlib.reload(pkg_resources)


@pytest.fixture()
def clear_venv_dependent_caches():
    _clear_venv_dependent_caches()
    return _clear_venv_dependent_caches  # Return in case the test needs to call it again


def pytest_collection_modifyitems(config, items):
    run_integration = config.getoption("--integration") or config.getoption("-m") == "integration"
    if not run_integration:
        skip_integration_marker = pytest.mark.skip(reason="Need --integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration_marker)


def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true", default=False, help="run integration tests")


def with_venv_python(tmp_path_factory: TempPathFactory):
    # Create virtual environment
    venv_path = tmp_path_factory.mktemp("venv")
    env_builder = venv.EnvBuilder(with_pip=True, system_site_packages=False)
    venv_ctx = env_builder.ensure_directories(venv_path)
    env_builder.create(venv_path)
    venv_python: str = venv_ctx.env_exe

    # "Activate" the virtual environment
    platform_scripts_dir = Path(get_bin_prefix()).name
    path_env_var = str(venv_path / platform_scripts_dir) + os.pathsep + os.environ["PATH"]
    with patch.dict(os.environ, {"PATH": path_env_var, "VIRTUAL_ENV": str(venv_path)}):
        os.environ.pop("PYTHONHOME", None)
        pip_version_override = os.environ.get("PIPASK_TEST_PIP_VERSION", None)
        if pip_version_override:
            print(subprocess.check_output([venv_python, "-m", "pip", "install", f"pip~={pip_version_override}"]))
        yield venv_python


@pytest.fixture
def temp_venv_python(tmp_path_factory):
    with contextmanager(with_venv_python)(tmp_path_factory) as venv_python:
        _clear_venv_dependent_caches()
        yield venv_python
