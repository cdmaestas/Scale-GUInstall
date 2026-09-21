"""
Starts a real scale-server.py Flask app (imported the same way the
repo-root tests/conftest.py's `ss` fixture does — the filename has a
hyphen, so it isn't a normal importable module) on a random free port, in
a background thread, for the whole test session. Tests exercise a real
HTTP+SSE round trip through ScaleBackendClient rather than mocking
anything, matching the backend's own test suite's philosophy of testing
through real interfaces.
"""
import importlib.util
import os
import socket
import threading
import time
import urllib.error
import urllib.request

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SERVER_PATH = os.path.join(_ROOT, "scale-server.py")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def ss():
    spec = importlib.util.spec_from_file_location("scale_server", _SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def backend_url(ss):
    port = _free_port()
    thread = threading.Thread(
        target=lambda: ss.app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()

    url = f"http://127.0.0.1:{port}"
    # Poll a real HTTP request, not just a TCP connect — a bare socket
    # connect can succeed (the OS accepts the connection) before Flask's
    # WSGI app is actually ready to route requests, which showed up as
    # occasional flakiness here (the connect succeeded but the very next
    # real request could still race the app's own startup). "/" is the one
    # endpoint that needs no auth token (see _PUBLIC_PATHS in
    # scale-server.py) and is the same one ScaleBackendClient's own token
    # bootstrap hits first, so this doubles as "the real client's first
    # request would succeed right now."
    for _ in range(100):
        try:
            with urllib.request.urlopen(f"{url}/", timeout=0.5) as resp:
                if resp.status == 200:
                    break
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(0.1)
    else:
        raise RuntimeError(f"scale-server.py did not start responding on {url} in time")

    # Session-wide constant, not per-test state — set directly rather than
    # via the function-scoped monkeypatch fixture (there is only ever one
    # backend for the whole test session).
    os.environ["SCALE_BACKEND_URL"] = url
    return url
