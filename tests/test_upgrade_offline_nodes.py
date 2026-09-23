"""
/api/stream/upgrade/offline-nodes — `spectrumscale upgrade config offline
-N <node1,node2,...>`, confirmed against IBM's documented toolkit behavior
(no corresponding "mark online again" subcommand exists, so this only ever
designates nodes offline).
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_operation_state(ss):
    ss._current_operation = None
    yield
    ss._current_operation = None


@pytest.fixture
def _fake_toolkit_exists(monkeypatch, ss):
    monkeypatch.setattr(ss, "_sudo_isfile", lambda path: True)


def test_offline_nodes_builds_the_comma_joined_command(ss, _fake_toolkit_exists, monkeypatch):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "designating")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/upgrade/offline-nodes",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "nodes": ["zima2", "zima3"], "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"] == [
        "sudo", "-n", "/tmp/spectrumscale", "upgrade", "config", "offline", "-N", "zima2,zima3",
    ]


def test_offline_nodes_dry_run_true_does_not_claim_operation(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/upgrade/offline-nodes",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "nodes": ["zima2"], "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


def test_offline_nodes_rejects_empty_node_list(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/upgrade/offline-nodes",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "nodes": [], "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "At least one node is required" in body


def test_offline_nodes_rejects_invalid_hostname(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/upgrade/offline-nodes",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "nodes": ["zima2; rm -rf /"], "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "Invalid node hostname" in body


def test_offline_nodes_returns_busy_when_operation_already_running(ss, _fake_toolkit_exists):
    ss._claim_operation("some-other-op", "web")
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/upgrade/offline-nodes",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "nodes": ["zima2"], "dry_run": False},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "busy"' in body
    assert "some-other-op" in body


def test_offline_nodes_invalid_toolkit_reports_error(ss):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/upgrade/offline-nodes",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/nonexistent/spectrumscale", "nodes": ["zima2"], "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "Toolkit not usable" in body
