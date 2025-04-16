from datetime import datetime

import httpx
import pytest

from pipask.infra.pip_report import (
    InstallationReportArchiveInfo,
    InstallationReportItem,
    InstallationReportItemDownloadInfo,
    InstallationReportItemMetadata,
)
from pipask.infra.pypi import (
    ProjectInfo,
    ProjectReleaseFile,
    PypiClient,
    ReleaseResponse,
)


@pytest.fixture
async def pypi_client():
    client = PypiClient()
    yield client
    await client.aclose()


@pytest.mark.integration
async def test_pypi_gets_non_existent_project_info(pypi_client: PypiClient):
    project_info = await pypi_client.get_project_info("nonexistent-ae392-jdj429jsdklj39j2r")
    assert project_info is None


@pytest.mark.integration
@pytest.mark.parametrize(
    "project_name,expected_url",
    [
        ("pyfluent-iterables", "https://github.com/mifeet/pyfluent-iterables"),  # Intentionally using an obsolete URL
        ("fastapi", "https://github.com/fastapi/fastapi"),
        ("torch", "https://github.com/pytorch/pytorch"),
        ("huggingface-hub", "https://github.com/huggingface/huggingface_hub"),
        ("ase", "https://gitlab.com/ase/ase"),
        ("pip-tools", "https://github.com/jazzband/pip-tools"),
        ("PIPS", None)
    ],
)
async def test_pypi_gets_source_repo(pypi_client: PypiClient, project_name: str, expected_url: str | None):
    project_info = await pypi_client.get_project_info(project_name)
    assert project_info is not None
    if expected_url is None:
        assert project_info.info.project_urls is None or project_info.info.project_urls.recognized_repo_url() is None
    else:
        assert project_info.info.project_urls.recognized_repo_url() == expected_url


@pytest.mark.integration
async def test_pypi_gets_distributions(pypi_client: PypiClient):
    distributions = await pypi_client.get_distributions("pyfluent-iterables")

    assert distributions is not None
    assert len(distributions.files) > 0
    assert distributions.files[0].upload_time
    oldest_file = min(distributions.files, key=lambda x: x.upload_time)
    assert oldest_file.upload_time == datetime.fromisoformat("2022-05-19T22:16:51.061667+00:00")


@pytest.mark.integration
async def test_pypi_matching_release_info_gets_pypi_file_info(pypi_client: PypiClient):
    sha256_hash = "9187d020dc45d1888ea753fb6b5e48687b572ef573543dc65ebc780888b49104"
    package = InstallationReportItem(
        metadata=InstallationReportItemMetadata(name="pyfluent-iterables", version="1.2.0"),
        download_info=InstallationReportItemDownloadInfo(
            url="https://files.pythonhosted.org/packages/df/4d/cc7b682a9762b71280dddac077c300622f277d003db9e145e93ca6b2ad0d/pyfluent_iterables-1.2.0-py3-none-any.whl",
            archive_info=InstallationReportArchiveInfo(hash=f"sha256={sha256_hash}"),
        ),
        requested=True,
        is_direct=True,
    )

    result = await pypi_client.get_matching_release_info(package)
    assert result is not None
    assert result.name == "pyfluent-iterables"
    assert result.version == "1.2.0"
    info = result.release_response

    assert info is not None
    assert info.info.package_url == "https://pypi.org/project/pyfluent-iterables/"
    assert info.info.name == "pyfluent-iterables"
    assert info.info.version == "1.2.0"


@pytest.mark.parametrize("hash_matches", [True, False])
async def test_pypi_matching_release_info_gets_info_only_when_hash_matches(hash_matches):
    source_hash = "aaaaaaaadaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaadaaaaaaaaaaaaaaaaaaaaaa"
    wheel_hash = "bbbbbbbbdbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbdbbbbbbbbbbbbbbbbbbbbbb"
    package_hash = wheel_hash if hash_matches else "ccccccccdcccccccccccccccccccccccccccccccdcccccccccccccccccccccc"
    package = InstallationReportItem(
        metadata=InstallationReportItemMetadata(name="test-package", version="1.0.0"),
        download_info=InstallationReportItemDownloadInfo(
            url="https://example.com/test-package-1.0.0.whl",
            archive_info=InstallationReportArchiveInfo(hash=f"sha256={package_hash}"),
        ),
        requested=True,
        is_direct=True,
    )

    # Mock the PyPI response
    package_url = "https://pypi.org/project/test-package/"
    mock_release_info = ReleaseResponse(
        info=ProjectInfo(
            name="test-package",
            version="1.0.0",
            package_url=package_url,
            yanked=True,
        ),
        urls=[
            ProjectReleaseFile(
                filename="test-package-1.0.0.tar.gz",
                upload_time_iso_8601=datetime.now(),
                digests={"sha256": source_hash},
            ),
            ProjectReleaseFile(
                filename="test-package-1.0.0.whl", upload_time_iso_8601=datetime.now(), digests={"sha256": wheel_hash}
            ),
        ],
    )

    def mock_handler(_req):
        return httpx.Response(200, json=mock_release_info.model_dump(mode="json", by_alias=True))

    pypi_client = PypiClient(transport=(httpx.MockTransport(mock_handler)))

    # Act
    result = await pypi_client.get_matching_release_info(package)
    if hash_matches:
        assert result is not None
        assert result.name == "test-package"
        assert result.version == "1.0.0"
        info = result.release_response
        assert info.info.name == "test-package"
        assert info.info.version == "1.0.0"
        assert info.info.package_url == package_url
        assert info.info.yanked
    else:
        assert result is None


@pytest.mark.integration
@pytest.mark.parametrize(
    "project_name,version", [("fastapi", "10000.9999.8888"), ("this-definitely-does-not-exist-42", "1.0.0")]
)
async def test_pypi_matching_release_info_handles_non_existent_project(
    pypi_client: PypiClient, project_name: str, version: str
):
    package = InstallationReportItem(
        metadata=InstallationReportItemMetadata(name=project_name, version=version),
        download_info=InstallationReportItemDownloadInfo(
            url="https://example.com/test-package-1.0.0.whl",
            archive_info=InstallationReportArchiveInfo(hash="sha256=aaaaa"),
        ),
        requested=True,
        is_direct=True,
    )

    info = await pypi_client.get_matching_release_info(package)

    assert info is None
