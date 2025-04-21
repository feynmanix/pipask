from contextlib import aclosing

from pipask.infra.pypistats import PypiStatsClient
import pytest


@pytest.mark.integration
async def test_pypi_stats_download_stats():
    async with aclosing(PypiStatsClient()) as pypi_stats_client:
        pypi_stats = await pypi_stats_client.get_download_stats("fastapi")
        assert pypi_stats is not None
        assert pypi_stats.last_month > 1


@pytest.mark.integration
@pytest.mark.parametrize("package_name", ["Flask", "discord.py"]) # Actual package names
async def test_pypi_stats_downloads_stats_for_repo_with_non_normalized_name(package_name:str):
    async with aclosing(PypiStatsClient()) as pypi_stats_client:
        pypi_stats = await pypi_stats_client.get_download_stats(package_name)
        assert pypi_stats is not None
        assert pypi_stats.last_month > 1
