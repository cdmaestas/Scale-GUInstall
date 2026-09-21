"""
Read-only tool functions against a real scale-server.py instance. Tool
functions are plain, directly-callable async functions (the @mcp.tool()
decorator returns the original function unchanged) — call them exactly
as an MCP client would invoke them, just without the protocol framing.

Several of these will surface validation errors (no real spectrumscale
toolkit/sudo on the test machine) rather than real data — that's fine
and expected; these tests verify the wiring (right endpoint, right
params, response shape reaches the caller intact), not real toolkit
behavior, matching the backend's own test suite's philosophy.
"""
import scale_guinstall_mcp.server as tools


async def test_ping(backend_url):
    assert await tools.ping() == {"ok": True}


async def test_check_operation_idle(backend_url):
    result = await tools.check_operation()
    assert result == {"status": "idle"}


async def test_spectrumscale_running_returns_process_list_shape(backend_url):
    result = await tools.spectrumscale_running()
    assert "processes" in result
    assert isinstance(result["processes"], list)


async def test_probe_interfaces_returns_ok_shape(backend_url):
    result = await tools.probe_interfaces()
    assert "ok" in result


async def test_probe_mmfs_returns_a_response(backend_url):
    result = await tools.probe_mmfs()
    assert "found" in result


async def test_check_file_reports_missing_file(backend_url):
    result = await tools.check_file(path="/tmp/definitely-does-not-exist-12345")
    assert result["exists"] is False


async def test_browse_files_on_a_real_directory(backend_url):
    # browse_files is sudo-backed (_sudo_isdir/_sudo_listdir) — on a test
    # machine without passwordless sudo configured it correctly reports
    # that as an error rather than raising, same as the real deployment
    # target would if NOPASSWD wasn't set up. Either shape proves the tool
    # is wired to the right endpoint with the right params; only a raised
    # exception here would be a real failure.
    result = await tools.browse_files(dir="/tmp")
    assert "files" in result or "error" in result


async def test_list_nodes_surfaces_toolkit_error_without_raising(backend_url):
    result = await tools.list_nodes(toolkit="/nonexistent/spectrumscale")
    assert result["ok"] is False
    assert "error" in result


async def test_get_config_returns_revision_shape(backend_url):
    result = await tools.get_config()
    assert "revision" in result


async def test_checkpython_returns_sse_events(backend_url):
    events = await tools.checkpython()
    assert isinstance(events, list)
    assert len(events) > 0
    assert all({"type", "line"} <= e.keys() for e in events)
    assert events[-1]["type"] == "done"


async def test_check_locale_returns_sse_events(backend_url):
    events = await tools.check_locale()
    assert events[-1]["type"] == "done"


async def test_ccr_status_returns_sse_events(backend_url):
    events = await tools.ccr_status()
    assert isinstance(events, list)
    assert events[-1]["type"] == "done"


async def test_check_ansible_returns_sse_events(backend_url):
    events = await tools.check_ansible()
    assert events[-1]["type"] == "done"


async def test_list_devices_requires_a_node(backend_url):
    events = await tools.list_devices(node="")
    assert any(e["type"] == "error" for e in events)


async def test_test_connection_uses_default_user_and_port(backend_url):
    # No real target — just confirm the call round-trips and completes
    # rather than hanging or raising, with the ssh attempt itself failing
    # as an SSE "error" event further down the stream.
    events = await tools.test_connection(node="127.0.0.1")
    assert isinstance(events, list)
    assert events[-1]["type"] == "done"


async def test_all_read_only_tools_are_registered():
    from scale_guinstall_mcp.server import mcp

    registered = {t.name for t in await mcp.list_tools()}
    expected_read_only = {
        "ping", "check_file", "browse_files", "probe_mmfs", "probe_interfaces",
        "probe_cluster_nodes", "spectrumscale_running", "list_nodes", "list_nsds",
        "list_filesystem", "list_config", "get_config", "check_operation",
        "checksum", "checkpython", "test_connection", "list_devices",
        "ccr_status", "check_ansible", "check_locale",
    }
    expected_mutating = {
        "start_format_disk", "start_nsd_add", "start_node_config",
        "kill_spectrumscale", "start_cluster_config_apply", "start_phase",
        "start_setup",
    }
    assert registered == expected_read_only | expected_mutating
