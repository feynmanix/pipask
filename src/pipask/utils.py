import requests
import time
import logging
from typing import TypeVar
from pydantic import BaseModel
import httpx

logger = logging.getLogger(__name__)


class TimeLogger:
    def __init__(self, description: str, logger: logging.Logger = logger):
        self.description = description
        self.start_time = time.time()
        self._logger = logger

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logger.debug(f"{self.description} took {time.time() - self.start_time:.2f}s")

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._logger.debug(f"{self.description} took {time.time() - self.start_time:.2f}s")


ResponseT = TypeVar("ResponseT", bound=BaseModel)


async def simple_get_request(
    url: str, client: httpx.AsyncClient, response_model: type[ResponseT], *, headers: dict[str, str] | None = None
) -> ResponseT | None:
    async with TimeLogger(f"GET {url}", logger):
        response = await client.get(url, headers=headers)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response_model.model_validate(response.json())


def simple_get_request_sync(
    url: str, session: requests.Session, response_model: type[ResponseT], *, headers: dict[str, str] | None = None
) -> ResponseT | None:
    with TimeLogger(f"GET {url}", logger):
        response = session.get(url, headers=headers)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response_model.model_validate(response.json())
