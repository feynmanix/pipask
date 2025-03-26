from contextlib import aclosing

from pipask.infra.pypistats import PypiStatsClient
import pytest


@pytest.mark.integration
async def test_pypi_stats_download_stats():
    async with aclosing(PypiStatsClient()) as pypi_stats_client:
        pypi_stats = await pypi_stats_client.get_download_stats("fastapi")
        assert pypi_stats is not None
        assert pypi_stats.last_month > 1
