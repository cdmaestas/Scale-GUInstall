"""
ScaleBackendClient against a real scale-server.py instance (see
conftest.py) — no HTTP mocking, exercising the actual token bootstrap,
401-retry, and SSE parsing against real responses.
"""
import pytest

from scale_guinstall_mcp.client import (
    BackendAuthError,
    BackendUnreachableError,
    ScaleBackendClient,
    parse_sse_events,
)


async def test_bootstraps_token_and_calls_ping(backend_url):
    client = ScaleBackendClient(base_url=backend_url)
    try:
        result = await client.get_json("/api/ping")
        assert result == {"ok": True}
        assert client._token is not None
    finally:
        await client.aclose()


async def test_default_base_url_reads_env_var(backend_url):
    # backend_url fixture already sets SCALE_BACKEND_URL for the session
    client = ScaleBackendClient()
    try:
        assert client.base_url == backend_url.rstrip("/")
        result = await client.get_json("/api/ping")
        assert result == {"ok": True}
    finally:
        await client.aclose()


async def test_stale_token_triggers_one_retry_and_succeeds(backend_url):
    client = ScaleBackendClient(base_url=backend_url)
    try:
        await client.get_json("/api/ping")  # bootstraps a real token
        client._token = "deliberately-wrong-token"
        result = await client.get_json("/api/ping")  # should 401 once, re-bootstrap, retry, succeed
        assert result == {"ok": True}
    finally:
        await client.aclose()


async def test_unreachable_backend_raises_clear_error():
    # Port 1 is a reserved/unused low port — connection should be refused
    # immediately rather than hanging the test.
    client = ScaleBackendClient(base_url="http://127.0.0.1:1")
    try:
        with pytest.raises(BackendUnreachableError, match="SSH tunnel"):
            await client.get_json("/api/ping")
    finally:
        await client.aclose()


async def test_get_json_does_not_raise_on_400_with_error_body(backend_url):
    """list_nodes with an unresolvable toolkit path returns 400 + a
    structured error body — the client must hand that back, not raise."""
    client = ScaleBackendClient(base_url=backend_url)
    try:
        result = await client.get_json("/api/list/nodes", params={"toolkit": "/nonexistent/spectrumscale"})
        assert result["ok"] is False
        assert "error" in result
    finally:
        await client.aclose()


async def test_get_sse_parses_a_real_stream(backend_url):
    client = ScaleBackendClient(base_url=backend_url)
    try:
        events = await client.get_sse("/api/stream/checkpython")
        assert len(events) > 0
        assert events[0].type in ("info", "normal", "error")
        assert events[-1].type == "done"
    finally:
        await client.aclose()


def test_parse_sse_events_handles_multiple_frames():
    text = (
        'data: {"type": "info", "line": "$ some command"}\n\n'
        'data: {"type": "success", "line": "[OK] done"}\n\n'
        'data: {"type": "done", "line": ""}\n\n'
    )
    events = parse_sse_events(text)
    assert [e.type for e in events] == ["info", "success", "done"]
    assert events[0].line == "$ some command"


def test_parse_sse_events_ignores_malformed_lines():
    text = 'not an sse line at all\n\ndata: {"type": "info", "line": "ok"}\n\n'
    events = parse_sse_events(text)
    assert len(events) == 1
    assert events[0].line == "ok"
