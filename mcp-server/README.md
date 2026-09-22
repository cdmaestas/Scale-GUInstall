# scale-guinstall-mcp

An MCP (Model Context Protocol) server that lets an AI agent (Claude Code
or Claude Desktop) drive an IBM Storage Scale cluster install/admin
session by calling tools — a second, parallel interface alongside the
[Scale GUInstall web UI](../README.md), not a replacement for it.

This is a **thin client**, not a reimplementation: every tool call is a
stateless HTTP/SSE request to the same `scale-server.py` backend the web
UI already talks to. It holds no cluster state of its own beyond the
backend's connection details and auth token.

## Prerequisites

1. `scale-server.py` running on the IBM Storage Scale installer node
   (see the [main README](../README.md) for installing/running it).
2. An SSH tunnel from your machine to that backend — **this server does
   not manage the tunnel for you**:
   ```bash
   ssh -L 5001:127.0.0.1:5001 user@installer-node
   ```
3. Python 3.10+ on the machine running this MCP server (your laptop, not
   the installer node).

## Install

```bash
cd mcp-server
pip install -e .
```

## Configure

Set `SCALE_BACKEND_URL` if the backend isn't at the default
`http://127.0.0.1:5001` (e.g. if you tunnel to a different local port).

Register it with Claude Code or Claude Desktop as a local stdio MCP
server, for example in Claude Code's `.mcp.json`:

```json
{
  "mcpServers": {
    "scale-guinstall": {
      "command": "scale-guinstall-mcp",
      "env": { "SCALE_BACKEND_URL": "http://127.0.0.1:5001" }
    }
  }
}
```

## Safety model

- **Read-only tools** (`ping`, `list_nodes`, `check_operation`, etc.) are
  always safe to call — no confirmation needed.
- **Mutating tools** (`start_*`, `kill_spectrumscale`) take a `dry_run`
  parameter that **defaults to `true`**. The backend itself validates
  inputs and reports what it would run without executing anything until
  the caller explicitly passes `dry_run=false`.
- Only one mutating operation can be in flight at a time, shared with the
  web UI — a second attempt gets a clear "busy" response naming what's
  already running and who started it (web UI or MCP), rather than
  silently queuing or colliding.
- Use `check_operation` to see what the current/most recent mutating
  operation did — `start_*` tools return as soon as the backend accepts
  the request, not when the operation finishes.

## v1 tool scope

Every read-only backend endpoint, plus `check_operation`. Mutating tools
cover node config, NSD add, NSD clear (all-or-nothing — no per-NSD delete
tool yet), cluster config apply, install/deploy/upgrade phases, setup,
format-disk, and kill. Endpoints not yet exposed as tools at all (AFM
gateway, node identity/certs, NFS core dump, etc.) are an explicit
backlog, not an oversight.

## Development

```bash
pip install -e ".[dev]"
pytest tests/
```

The test suite starts a real `scale-server.py` instance on a random port
for the session and exercises real HTTP/SSE round trips — no mocking.
