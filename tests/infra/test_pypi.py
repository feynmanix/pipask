from pipask.infra.pypi import PypiClient

from datetime import datetime
import pytest


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
async def test_pypi_gets_non_existent_release_info(pypi_client: PypiClient):
    release_info = await pypi_client.get_release_info("fastapi", "10000.9999.0")
    assert release_info is None


@pytest.mark.integration
@pytest.mark.parametrize(
    "project_name,expected_url",
    [
        ("pyfluent-iterables", "https://github.com/mifeet/pyfluent-iterables"),  # Intentionally using an obsolete URL
        ("fastapi", "https://github.com/fastapi/fastapi"),
        ("torch", None),
        ("huggingface-hub", "https://github.com/huggingface/huggingface_hub"),
        ("ase", "https://gitlab.com/ase/ase"),
    ],
)
async def test_pypi_gets_source_repo(pypi_client: PypiClient, project_name: str, expected_url: str | None):
    project_info = await pypi_client.get_project_info(project_name)
    assert project_info is not None
    assert project_info.info.project_urls.recognized_repo_url() == expected_url


@pytest.mark.integration
async def test_pypi_gets_distributions(pypi_client: PypiClient):
    distributions = await pypi_client.get_distributions("pyfluent-iterables")

    assert distributions is not None
    assert len(distributions.files) > 0
    assert distributions.files[0].upload_time
    oldest_file = min(distributions.files, key=lambda x: x.upload_time)
    assert oldest_file.upload_time == datetime.fromisoformat("2022-05-19T22:16:51.061667+00:00")

