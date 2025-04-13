from dataclasses import dataclass
from typing import Tuple, cast
import subprocess
import json
from functools import cache

from pipask.infra.executables import get_pip_python_executable


@dataclass
class SysValues:
    exec_prefix: str
    prefix: str
    base_prefix: str
    has_real_prefix: bool
    implementation_name: str
    version_info: Tuple[int, int, int]
    path: str
    executable: str
    abiflags: str | None
    ldversion: str | None
    pip_pkg_dir: str
    site_file: str


@cache  # This is cleared between tests
def get_pip_sys_values() -> SysValues:
    """
    Returns various sys values as they are in the *target* environment.
    This is because pipask is typically installed in a different environment (e.g., pipx)
    than the installation target environment.
    """
    script = """
import sys
import json
import os
from pathlib import Path
import pip
import os.path
import sysconfig
import site

values = {
    "exec_prefix": sys.exec_prefix,
    "prefix": sys.prefix,
    "implementation_name": sys.implementation.name,
    "version_info": list(sys.version_info[:3]),
    "path": sys.path,
    "executable": sys.executable,
    "abiflags": getattr(sys, "abiflags", None),
    "ldversion": sysconfig.get_config_var("LDVERSION"),
    "pip_pkg_dir": os.path.dirname(pip.__file__),
    "base_prefix": getattr(sys, "base_prefix", sys.prefix),
    "has_real_prefix": hasattr(sys, "real_prefix"),
    "site_file": site.__file__,
}
print(json.dumps(values))
"""

    result = subprocess.run([get_pip_python_executable(), "-c", script], capture_output=True, text=True, check=True)

    data = json.loads(result.stdout)
    return SysValues(
        exec_prefix=data["exec_prefix"],
        prefix=data["prefix"],
        implementation_name=data["implementation_name"],
        version_info=cast(Tuple[int, int, int], tuple(data["version_info"])),
        path=data["path"],
        executable=data["executable"],
        abiflags=data["abiflags"],
        ldversion=data["ldversion"],
        pip_pkg_dir=data["pip_pkg_dir"],
        base_prefix=data["base_prefix"],
        has_real_prefix=data["has_real_prefix"],
        site_file=data["site_file"],
    )
