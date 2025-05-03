import requests
import time
import logging
from typing import TypeVar
from pydantic import BaseModel
import httpx
import os
import sys

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


def _terminal_does_not_support_hyperlinks():
    """
    Determine when we can be fairly certain that OSC 8 hyperlinks are NOT supported (can have false negatives).
    """
    # Case 1: Not a terminal at all
    if not sys.stdout.isatty():
        return True

    # Case 2: Known non-supporting terminal types
    term = os.environ.get("TERM", "").lower()
    known_non_supporting_terms = [
        "dumb",  # Dumb terminals don't support any escape sequences
        "vt100",  # Original VT100 predates OSC 8
        "ansi",  # Basic ANSI terminals don't support OSC 8
        "cygwin",  # Traditional Cygwin terminal doesn't support hyperlinks
        "linux",  # The raw Linux console doesn't support hyperlinks
        "screen",  # Default screen without configuration doesn't support hyperlinks
    ]
    if any(term == non_supporting for non_supporting in known_non_supporting_terms):
        return True

    # Case 3: Non-supporting terminal environments
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    non_supporting_programs = [
        "cmd.exe",  # Windows Command Prompt doesn't support hyperlinks
        "apple_terminal",  # Apple's Terminal.app doesn't support hyperlinks
    ]
    if any(program in term_program for program in non_supporting_programs):
        return True

    # Case 4: NO_COLOR environment variable
    # Some terminals respect this for disabling all formatting including hyperlinks
    if os.environ.get("NO_COLOR") is not None or os.environ.get("COLORTERM", "").lower() == "nocolor":
        return True

    # If none of the above cases match, we can't be certain
    # that OSC 8 is not supported, so return False
    return False


_HYPERLINKS_NOT_SUPPORTED = _terminal_does_not_support_hyperlinks()


def format_link(text: str, url: str | None, fallback: bool = False) -> str:
    if not url:
        return text
    if _HYPERLINKS_NOT_SUPPORTED:
        return f"{text} [{url}]" if fallback else text
    return f"[link={url}]{text}[/link]"
