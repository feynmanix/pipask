import logging

import httpx
from pydantic import BaseModel

from pipask.utils import TimeLogger

logger = logging.getLogger(__name__)


class DownloadStats(BaseModel):
    last_day: int
    last_week: int
    last_month: int


class _DownloadStatsResponse(BaseModel):
    data: DownloadStats
    package: str
    type: str


_BASE_URL = "https://pypistats.org/api"


class PypiStatsClient:
    def __init__(self):
        self.client = httpx.AsyncClient()

    async def get_download_stats(self, package_name: str) -> DownloadStats | None:
        url = f"{_BASE_URL}/packages/{package_name}/recent"
        async with TimeLogger(f"GET {url}", logger):
            response = await self.client.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        parsed_response = _DownloadStatsResponse.model_validate(response.json())
        return parsed_response.data

    async def aclose(self) -> None:
        await self.client.aclose()
