import requests
import time
import logging
from typing import TypeVar
from pydantic import BaseModel
import httpx
import os
import sys
from optparse import Values
import ssl
import truststore

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


def create_httpx_client(
    options: Values,
    retries: None | int = None,
    timeout: None | int = None,
) -> httpx.AsyncClient:
    # Adapted from SessionCommandMixin._build_session()

    # Handle SSL context
    ssl_context = None
    if hasattr(options, "features_enabled") and "truststore" in options.features_enabled:
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    # Configure timeout
    request_timeout = timeout or getattr(options, "timeout", 30)
    timeout_config = httpx.Timeout(
        timeout=float(request_timeout) if request_timeout else 30.0,
        connect=5.0,
        read=float(request_timeout) if request_timeout else 30.0,
        write=float(request_timeout) if request_timeout else 30.0,
        pool=5.0,
    )

    # Create transport with retry configuration
    max_retries = retries if retries is not None else 0

    # Handle custom CA bundle
    verify_ssl = ssl_context if ssl_context else True
    if options.cert:
        verify_ssl = options.cert

    # Handle client certificate
    client_cert: None | str | tuple[str, str] = None
    if options.client_cert:
        client_cert = options.client_cert

    # Create transport with configuration
    transport = httpx.AsyncHTTPTransport(
        retries=max_retries,
        verify=verify_ssl,
        cert=client_cert,
        http2=True,
    )

    # Create the async client
    client = httpx.AsyncClient(
        transport=transport,
        timeout=timeout_config,
        proxy=options.proxy,
        follow_redirects=True,
    )

    return client


async def simple_get_request(
    url: str,
    client: httpx.AsyncClient,
    response_model: type[ResponseT],
    *,
    headers: dict[str, str] | None = None,
) -> ResponseT | None:
    async with TimeLogger(f"GET {url}", logger):
        response = await client.get(url, headers=headers)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response_model.model_validate(response.json())


def simple_get_request_sync(
    url: str,
    session: requests.Session,
    response_model: type[ResponseT],
    *,
    headers: dict[str, str] | None = None,
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
