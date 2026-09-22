"""
Thin HTTP+SSE client for scale-server.py's backend. Deliberately dumb: it
holds no cluster state of its own, just the connection details and the
per-process auth token — every tool call in server.py is a stateless
passthrough of whatever parameters the corresponding REST endpoint
already requires.

Auth: the backend generates a fresh random token at process start and
embeds it in the HTML page it serves (see scale-server.py's
_serve_sibling_html / _AUTH_TOKEN). There is no separate issuance
endpoint for a non-browser client, so this client bootstraps the same
way a browser effectively does — fetch the page once, pull the token out
of it — and re-bootstraps once on a 401 (the backend restarted and
invalidated the old token; a browser's equivalent recovery is "reload
the page").
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

import httpx

_TOKEN_RE = re.compile(r'<meta name="scale-guinstall-token" content="([^"]+)">')
_TOKEN_HEADER = "X-Scale-Token"
_CLIENT_HEADER = "X-Scale-Client"
_DEFAULT_BASE_URL = "http://127.0.0.1:5001"


class BackendUnreachableError(RuntimeError):
    """The backend couldn't be reached at all (connection refused/timeout)."""


class BackendAuthError(RuntimeError):
    """Authenticated calls to the backend failed even after a token refresh."""


@dataclass
class SSEEvent:
    type: str
    line: str


def parse_sse_events(text: str) -> list[SSEEvent]:
    """Parse a full SSE response body (as produced by scale-server.py's
    sse() helper) into a list of events, in order."""
    events: list[SSEEvent] = []
    for chunk in text.split("\n\n"):
        for raw_line in chunk.splitlines():
            if not raw_line.startswith("data:"):
                continue
            try:
                payload = json.loads(raw_line[len("data:"):].strip())
            except json.JSONDecodeError:
                continue
            events.append(SSEEvent(type=payload.get("type", ""), line=payload.get("line", "")))
    return events


@dataclass
class ScaleBackendClient:
    base_url: str = field(default_factory=lambda: os.environ.get("SCALE_BACKEND_URL", _DEFAULT_BASE_URL))
    _token: str | None = field(default=None, init=False, repr=False)
    _http: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _bootstrap_token(self) -> str:
        try:
            resp = await self._http.get("/")
        except httpx.TransportError as exc:
            raise BackendUnreachableError(
                f"Can't reach the backend at {self.base_url} — is the SSH tunnel up? "
                f"({exc})"
            ) from exc
        match = _TOKEN_RE.search(resp.text)
        if not match:
            raise BackendAuthError(
                f"Backend at {self.base_url} responded, but no auth token was found in the "
                "served page. Is this actually a scale-server.py instance?"
            )
        self._token = match.group(1)
        return self._token

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if self._token is None:
            await self._bootstrap_token()

        headers = kwargs.pop("headers", {}) or {}
        headers[_TOKEN_HEADER] = self._token
        headers[_CLIENT_HEADER] = "mcp"

        try:
            resp = await self._http.request(method, path, headers=headers, **kwargs)
        except httpx.TransportError as exc:
            raise BackendUnreachableError(
                f"Can't reach the backend at {self.base_url} — is the SSH tunnel up? ({exc})"
            ) from exc

        if resp.status_code == 401:
            # The backend restarted since we bootstrapped — its token (and
            # therefore ours) is stale. Re-fetch once and retry once; if
            # that still 401s, something else is wrong and we give up.
            await self._bootstrap_token()
            headers[_TOKEN_HEADER] = self._token
            try:
                resp = await self._http.request(method, path, headers=headers, **kwargs)
            except httpx.TransportError as exc:
                raise BackendUnreachableError(
                    f"Can't reach the backend at {self.base_url} — is the SSH tunnel up? ({exc})"
                ) from exc
            if resp.status_code == 401:
                raise BackendAuthError(
                    f"Still unauthorized after refreshing the token against {self.base_url}."
                )
        return resp

    async def get_json(self, path: str, params: dict | None = None) -> dict:
        # Deliberately no raise_for_status(): several endpoints return 400
        # with a structured {"error": "..."} body on validation failure
        # (e.g. list_nodes with a bad toolkit path) — that body is more
        # useful to the caller than an exception, and matches how the web
        # UI's own JS already treats these responses (check data.error,
        # never response.ok).
        resp = await self._request("GET", path, params=params)
        return resp.json()

    async def post_json(self, path: str, json_body: dict | None = None) -> dict:
        resp = await self._request("POST", path, json=json_body or {})
        return resp.json()

    async def get_sse(self, path: str, params: dict | None = None) -> list[SSEEvent]:
        """GET an SSE endpoint and drain it fully. Only for endpoints known
        to complete quickly (read-only, or a dry_run=true preview) — see
        server.py's start_stream() for the fire-and-forget path used by
        long-running mutating tools."""
        resp = await self._request("GET", path, params=params)
        return parse_sse_events(resp.text)

    async def post_sse(self, path: str, json_body: dict | None = None) -> list[SSEEvent]:
        resp = await self._request("POST", path, json=json_body or {})
        return parse_sse_events(resp.text)

    async def open_stream(
        self, method: str, path: str, params: dict | None = None, json_body: dict | None = None
    ) -> httpx.Response:
        """
        Send a request and return the still-open streaming Response, with
        auth already handled (bootstrap + one 401-retry) but nothing else
        read from the body yet. For long-running mutating endpoints where
        the caller wants to see only the first SSE event (accepted vs.
        busy/rejected) without blocking for the whole operation — see
        read_next_sse_event() and server.py's start_stream() for how the
        rest of the response is drained afterwards without blocking.

        Unlike get_sse/post_sse, the caller owns closing this response
        (directly, or by fully draining it) once done with it.

        Uses no read timeout for this request specifically (connect/write/
        pool stay bounded, so an unreachable backend still fails fast) —
        the shared client's flat 30s timeout applies to every request
        otherwise, including this one's background drain (server.py's
        _drain_stream), and a real toolkit phase can go quiet for minutes
        at a time without anything being wrong. A prior real install run
        confirmed this concretely: retried with no MCP timeout in place,
        the exact same operation ran its full toolkit sequence to
        completion. Under the old flat timeout, that quiet stretch instead
        raised httpx.ReadTimeout here, which — via stream_process()'s
        abandoned-connection safety net on the backend — could kill the
        real child process mid-run. See docs/long-running-operations-plan.md
        for the full fix; this is deliberately just the part that stops
        that from happening, not a replacement for it.
        """
        if self._token is None:
            await self._bootstrap_token()

        stream_timeout = httpx.Timeout(30.0, read=None)

        async def _send() -> httpx.Response:
            headers = {_TOKEN_HEADER: self._token, _CLIENT_HEADER: "mcp"}
            # send() itself has no timeout= parameter — a per-request
            # override has to be baked into the request via build_request()
            # instead, same as request()/get() do internally.
            req = self._http.build_request(
                method, path, params=params, json=json_body, headers=headers, timeout=stream_timeout,
            )
            return await self._http.send(req, stream=True)

        try:
            resp = await _send()
        except httpx.TransportError as exc:
            raise BackendUnreachableError(
                f"Can't reach the backend at {self.base_url} — is the SSH tunnel up? ({exc})"
            ) from exc

        if resp.status_code == 401:
            await resp.aclose()
            await self._bootstrap_token()
            try:
                resp = await _send()
            except httpx.TransportError as exc:
                raise BackendUnreachableError(
                    f"Can't reach the backend at {self.base_url} — is the SSH tunnel up? ({exc})"
                ) from exc
            if resp.status_code == 401:
                await resp.aclose()
                raise BackendAuthError(
                    f"Still unauthorized after refreshing the token against {self.base_url}."
                )
        return resp


async def read_next_sse_event(line_iter) -> SSEEvent | None:
    """
    Consume lines from line_iter (an async iterator over a streaming
    Response's aiter_lines()) until one full SSE frame is available, and
    return it — or None if the stream ended first. Safe to call
    repeatedly against the *same* iterator to read successive events one
    at a time, leaving the rest of the stream unread for a later caller
    (a background drain task) to continue from exactly where this left
    off.
    """
    data_line = None
    async for line in line_iter:
        if line.startswith("data:"):
            data_line = line
        elif line == "" and data_line is not None:
            try:
                payload = json.loads(data_line[len("data:"):].strip())
            except json.JSONDecodeError:
                data_line = None
                continue
            return SSEEvent(type=payload.get("type", ""), line=payload.get("line", ""))
    return None
