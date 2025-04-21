import logging

import httpx
from packaging.utils import canonicalize_name
from pydantic import BaseModel

from pipask.utils import simple_get_request

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
        url = f"{_BASE_URL}/packages/{canonicalize_name(package_name)}/recent"
        parsed_response = await simple_get_request(url, self.client, _DownloadStatsResponse)
        return parsed_response.data if parsed_response is not None else None

    async def aclose(self) -> None:
        await self.client.aclose()
