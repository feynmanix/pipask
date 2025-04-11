import os
import venv
from unittest.mock import patch

import pytest
from _pytest.tmpdir import TempPathFactory


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
    path_env_var = str(venv_path / "bin") + os.pathsep + os.environ["PATH"]
    with patch.dict(os.environ, {"PATH": path_env_var, "VIRTUAL_ENV": str(venv_path)}):
        yield venv_python
