import sys
from pathlib import Path

import pytest

from pipask.infra.sys_values import get_pip_sys_values
from tests.conftest import with_venv_python

temp_venv_python = pytest.fixture()(with_venv_python)


@pytest.mark.integration
def test_returns_sys_values_respecting_venv(
    temp_venv_python: str,
    monkeypatch: pytest.MonkeyPatch,
    clear_venv_dependent_caches
) -> None:
    clear_venv_dependent_caches()
    assert temp_venv_python

    values = get_pip_sys_values()

    assert values.executable == temp_venv_python
    assert temp_venv_python.startswith(values.exec_prefix)
    assert temp_venv_python.startswith(values.prefix)
    assert values.implementation_name == sys.implementation.name
    assert values.version_info == sys.version_info[:3]
    assert any(p.startswith(Path(temp_venv_python).parent.parent.as_posix()) for p in values.path)
    assert values.site_file
    assert values.base_prefix