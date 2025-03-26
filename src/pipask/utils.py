import time
import logging

logger = logging.getLogger(__name__)


class TimeLogger:
    def __init__(self, description: str, logger: logging.Logger = logger):
        self.description = description
        self.start_time = time.time()
        self._logger = logger

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._logger.debug(f"{self.description} took {time.time() - self.start_time:.2f}s")
