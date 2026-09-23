# scale-guinstall-mcp

An MCP (Model Context Protocol) server that lets an AI agent — Claude
Code, Claude Desktop, Codex CLI, or any other MCP-compliant client —
drive an IBM Storage Scale cluster install/admin session by calling
tools. A second, parallel interface alongside the
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

This is a standard stdio-transport MCP server — `scale-guinstall-mcp` is
just a regular local process any MCP-compliant client can launch, not
something built specifically for one client. Confirmed working with
Claude Code and Codex CLI; any other client with stdio MCP server
support should work the same way — point it at the `scale-guinstall-mcp`
command (or its full path, e.g.
`mcp-server/.venv/bin/scale-guinstall-mcp` if you installed into a venv)
with `SCALE_BACKEND_URL` in its environment.

### Claude Code

Add to `.mcp.json` in your project root:

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

### Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.scale-guinstall]
command = "scale-guinstall-mcp"
env = { SCALE_BACKEND_URL = "http://127.0.0.1:5001" }
```

(Codex's config schema has moved before — check `codex mcp --help` or the
current [Codex docs](https://github.com/openai/codex) if this doesn't
take.)

### Claude Desktop and other clients

Claude Desktop uses the same `command`/`env` shape as Claude Code, in its
own `claude_desktop_config.json` (location varies by OS — see
[Anthropic's MCP quickstart](https://modelcontextprotocol.io/quickstart/user)).
For any other client, consult its docs for where local stdio MCP servers
are configured; the `command` + `env` values above are all it needs.

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
cover: node config; NSD add and clear (all-or-nothing — no per-NSD
delete tool yet); cluster config apply; install/deploy/upgrade phases;
setup; format-disk; kill; config populate; offline-upgrade node
designation; GPFS shutdown/startup; post-upgrade finalization
(`mmchconfig release=LATEST`, filesystem version); call home
enable/disable; CES protocol config and enable (NFS/SMB/S3/HDFS); and
the "Post Configuration" set — environment PATH setup, GUI user
creation, GPFS performance tunables, health monitoring interval, NFS
core dump, and AFM gateway.

Node identity/certificate generation (`node-identity`) is the one
backend endpoint not yet exposed as a tool — an explicit backlog item,
not an oversight.

## Development

```bash
pip install -e ".[dev]"
pytest tests/
```

The test suite starts a real `scale-server.py` instance on a random port
for the session and exercises real HTTP/SSE round trips — no mocking.
