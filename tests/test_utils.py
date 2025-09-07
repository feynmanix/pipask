import asyncio
from contextlib import aclosing
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from optparse import Values

import httpx
import pytest

from pipask.utils import create_httpx_client


class MockProxyHandler(BaseHTTPRequestHandler):
    received_requests: list[dict[str, object]] = []

    @classmethod
    def reset_requests(cls):
        cls.received_requests = []

    def do_CONNECT(self):
        """Handle CONNECT method for HTTPS tunneling."""
        self.__class__.received_requests.append(
            {
                "method": "CONNECT",
                "path": self.path,  # Should be "host:port"
                "headers": dict(self.headers),
            }
        )
        self.send_response(200, "Connection Established")
        self.end_headers()

    def do_GET(self):
        """Handle GET method for HTTP proxying."""
        self.__class__.received_requests.append(
            {
                "method": "GET",
                "path": self.path,  # Should be full URL for proxy
                "headers": dict(self.headers),
            }
        )
        # Send a mock response
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"proxy": "response"}')

    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


def run_mock_proxy(port):
    server = HTTPServer(("localhost", port), MockProxyHandler)
    server.serve_forever()


@pytest.fixture(autouse=True)
def reset_proxy_requests():
    MockProxyHandler.reset_requests()
    yield


@pytest.mark.asyncio
async def test_https_uses_connect_through_proxy():
    proxy_port = 28888
    proxy_thread = threading.Thread(target=run_mock_proxy, args=(proxy_port,), daemon=True)
    proxy_thread.start()

    # Give the server a moment to start
    await asyncio.sleep(0.1)

    # Create options with our mock proxy
    options = Values({"proxy": f"http://localhost:{proxy_port}"})
    async with aclosing(create_httpx_client(options)) as client:
        try:
            await client.get("https://example.com/test", timeout=2.0)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError):
            # Expected - our mock proxy doesn't actually forward requests
            pass

        assert len(MockProxyHandler.received_requests) > 0, "Proxy did not receive any requests!"
        request = MockProxyHandler.received_requests[0]
        assert request["method"] == "CONNECT", f"Expected CONNECT but got {request['method']}"
        # Parse "host:port" from CONNECT path and assert exact match
        host_port = str(request["path"]).split(":")
        assert len(host_port) == 2, f"Expected 'host:port' in path, but got: {request['path']}"
        assert host_port[0] == "example.com", f"Expected host 'example.com', got {host_port[0]}"
        assert host_port[1] == "443", f"Expected port '443', got {host_port[1]}"


@pytest.mark.asyncio
async def test_http_uses_get_through_proxy():
    proxy_port = 28889
    proxy_thread = threading.Thread(target=run_mock_proxy, args=(proxy_port,), daemon=True)
    proxy_thread.start()

    # Give the server a moment to start
    await asyncio.sleep(0.1)

    # Create options with our mock proxy
    options = Values({"proxy": f"http://localhost:{proxy_port}"})
    async with aclosing(create_httpx_client(options)) as client:
        try:
            await client.get("http://example.com/test", timeout=2.0)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError):
            # Expected - our mock proxy doesn't actually forward requests
            pass

        assert len(MockProxyHandler.received_requests) > 0, "Proxy did not receive any requests!"
        request = MockProxyHandler.received_requests[0]
        assert request["method"] == "GET", f"Expected GET but got {request['method']}"
        assert "http://example.com/test" in str(request["path"]), f"Expected full URL in {request['path']}"
