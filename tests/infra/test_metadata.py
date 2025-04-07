import os
from unittest.mock import patch

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

from pipask._vendor.pip._internal.index.collector import LinkCollector
from pipask._vendor.pip._internal.index.package_finder import PackageFinder
from pipask._vendor.pip._internal.models.link import Link
from pipask._vendor.pip._internal.models.search_scope import SearchScope
from pipask._vendor.pip._internal.models.target_python import TargetPython
from pipask._vendor.pip._internal.network.session import PipSession
from pipask._vendor.pip._internal.req import InstallRequirement
from pipask._vendor.pip._internal.utils.temp_dir import global_tempdir_manager
from pipask.infra.metadata import (
    fetch_metadata_from_pypi,
    get_pypi_metadata_distribution,
    synthesize_release_metadata_file,
)
from pipask.infra.pypi import ReleaseResponse


@pytest.fixture
def pip_session():
    with PipSession() as session:
        yield session


def test_pypi_synthesizes_release_metadata_file():
    release_info_raw = """
{
  "info": {
    "author": "PyTorch Team",
    "author_email": "packages@pytorch.org",
    "bugtrack_url": null,
    "classifiers": [
      "Development Status :: 5 - Production/Stable"
    ],
    "description": "...",
    "description_content_type": "text/markdown",
    "docs_url": null,
    "download_url": "https://github.com/pytorch/pytorch/tags",
    "dynamic": null,
    "home_page": "https://pytorch.org/",
    "keywords": "pytorch, machine learning",
    "license": "BSD-3-Clause",
    "license_expression": null,
    "license_files": null,
    "maintainer": null,
    "maintainer_email": null,
    "name": "torch",
    "package_url": "https://pypi.org/project/torch/",
    "platform": null,
    "project_url": "https://pypi.org/project/torch/",
    "project_urls": {
      "Download": "https://github.com/pytorch/pytorch/tags",
      "Homepage": "https://pytorch.org/"
    },
    "provides_extra": null,
    "release_url": "https://pypi.org/project/torch/2.6.0/",
    "requires_dist": [
      "filelock",
      "typing-extensions\u003e=4.10.0",
      "networkx",
      "jinja2",
      "fsspec",
      "nvidia-cuda-nvrtc-cu12==12.4.127; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-cuda-runtime-cu12==12.4.127; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-cuda-cupti-cu12==12.4.127; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-cudnn-cu12==9.1.0.70; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-cublas-cu12==12.4.5.8; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-cufft-cu12==11.2.1.3; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-curand-cu12==10.3.5.147; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-cusolver-cu12==11.6.1.9; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-cusparse-cu12==12.3.1.170; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-cusparselt-cu12==0.6.2; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-nccl-cu12==2.21.5; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-nvtx-cu12==12.4.127; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "nvidia-nvjitlink-cu12==12.4.127; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "triton==3.2.0; platform_system == \\"Linux\\" and platform_machine == \\"x86_64\\"",
      "setuptools; python_version \u003e= \\"3.12\\"",
      "sympy==1.13.1; python_version \u003e= \\"3.9\\"",
      "opt-einsum\u003e=3.3; extra == \\"opt-einsum\\"",
      "optree\u003e=0.13.0; extra == \\"optree\\""
    ],
    "requires_python": "\u003e=3.9.0",
    "summary": "Tensors and Dynamic neural networks in Python with strong GPU acceleration",
    "version": "2.6.0",
    "yanked": false,
    "yanked_reason": null
  }
}
"""
    expected_metadata_file = """
Metadata-Version: 2.1
Name: torch
Version: 2.6.0
Summary: Tensors and Dynamic neural networks in Python with strong GPU acceleration
Home-page: https://pytorch.org/
Download-URL: https://github.com/pytorch/pytorch/tags
Author: PyTorch Team
Author-email: packages@pytorch.org
License: BSD-3-Clause
Classifier: Development Status :: 5 - Production/Stable
Requires-Python: >=3.9.0
Requires-Dist: filelock
Requires-Dist: typing-extensions>=4.10.0
Requires-Dist: networkx
Requires-Dist: jinja2
Requires-Dist: fsspec
Requires-Dist: nvidia-cuda-nvrtc-cu12==12.4.127; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-cuda-runtime-cu12==12.4.127; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-cuda-cupti-cu12==12.4.127; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-cudnn-cu12==9.1.0.70; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-cublas-cu12==12.4.5.8; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-cufft-cu12==11.2.1.3; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-curand-cu12==10.3.5.147; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-cusolver-cu12==11.6.1.9; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-cusparse-cu12==12.3.1.170; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-cusparselt-cu12==0.6.2; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-nccl-cu12==2.21.5; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-nvtx-cu12==12.4.127; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: nvidia-nvjitlink-cu12==12.4.127; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: triton==3.2.0; platform_system == "Linux" and platform_machine == "x86_64"
Requires-Dist: setuptools; python_version >= "3.12"
Requires-Dist: sympy==1.13.1; python_version >= "3.9"
Requires-Dist: opt-einsum>=3.3; extra == "opt-einsum"
Requires-Dist: optree>=0.13.0; extra == "optree"
""".strip()
    # Provides-Extra: opt-einsum
    # Provides-Extra: optree

    release_info = ReleaseResponse.model_validate_json(release_info_raw)

    result = synthesize_release_metadata_file(release_info)

    assert result == expected_metadata_file


@pytest.mark.integration
@pytest.mark.parametrize("use_importlib_metadata", [True, False])
def test_creates_distribution_from_pypi_metadata_importlib(
    use_importlib_metadata: bool, pip_session: PipSession
) -> None:
    # See pip._internal.metadata.__init__._should_use_importlib_metadata()
    with patch.dict(os.environ, {"_PIP_USE_IMPORTLIB_METADATA": "1" if use_importlib_metadata else "0"}):
        with global_tempdir_manager():
            distribution = get_pypi_metadata_distribution("pyfluent-iterables", Version("1.2.0"), pip_session)

            assert distribution.canonical_name == "pyfluent-iterables"
            assert distribution.version == Version("1.2.0")
            assert distribution.requires_python == "<4.0,>=3.7"
            assert list(distribution.iter_dependencies()) == []
            assert "Summary: Fluent API wrapper for Python collections" in str(distribution.metadata)


def test_get_pypi_metadata_distribution_throws_if_tempdir_not_provided(pip_session: PipSession) -> None:
    # See pip._internal.metadata.__init__._should_use_importlib_metadata()
    with patch.dict(os.environ, {"_PIP_USE_IMPORTLIB_METADATA": "1"}):
        with pytest.raises(RuntimeError):
            get_pypi_metadata_distribution("pyfluent-iterables", Version("1.2.0"), pip_session)


@pytest.mark.integration
async def test_fetches_metadata_from_pypi_by_hash(pip_session: PipSession) -> None:
    link_collector = LinkCollector(
        session=PipSession(),
        search_scope=SearchScope([], [], False),
    )
    package_finder = PackageFinder(
        link_collector=link_collector, target_python=TargetPython(py_version_info=(3, 10)), allow_yanked=False
    )
    link_evaluator = package_finder.make_link_evaluator("pyfluent-iterables")
    links = package_finder.process_project_url(Link("https://pypi.org/simple/pyfluent-iterables/"), link_evaluator)
    link_1_2_0 = next(candidate.link for candidate in links if candidate.version == Version("1.2.0"))
    ireq = InstallRequirement(Requirement("pyfluent-iterables==1.2.0"), None, link=link_1_2_0)

    with patch.dict(os.environ, {"_PIP_USE_IMPORTLIB_METADATA": "1"}):
        with global_tempdir_manager():
            metadata = fetch_metadata_from_pypi(ireq, pip_session)

            assert metadata is not None
            assert metadata.canonical_name == "pyfluent-iterables"
            assert metadata.version == Version("1.2.0")
            assert metadata.requires_python == "<4.0,>=3.7"
            assert "Summary: Fluent API wrapper for Python collections" in str(metadata.metadata)
