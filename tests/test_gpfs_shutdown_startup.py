"""
/api/stream/gpfs/shutdown (`mmshutdown -N <nodes>`) and
/api/stream/gpfs/startup (`mmstartup -N <nodes>`) — discovered as a real
prerequisite gap while testing the offline-upgrade flow live: `spectrumscale
upgrade config offline -N <node>` refuses a node whose GPFS daemon is still
running ("cannot be designated for offline upgrade until the GPFS daemon
running on the node is stopped"), and `upgrade run` deliberately never
restarts GPFS on an offline-designated node afterward, so both ends of that
lifecycle need their own endpoint.
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_operation_state(ss):
    ss._current_operation = None
    yield
    ss._current_operation = None


@pytest.mark.parametrize(
    "path,mm_binary,verb",
    [
        ("/api/stream/gpfs/shutdown", "mmshutdown", "shut down"),
        ("/api/stream/gpfs/startup", "mmstartup", "started up"),
    ],
)
def test_builds_the_comma_joined_command(ss, monkeypatch, path, mm_binary, verb):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "running")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        path,
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"nodes": ["zima2", "zima3"], "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"] == ["sudo", "-n", f"{ss.MMFS_BIN}/{mm_binary}", "-N", "zima2,zima3"]


@pytest.mark.parametrize("path", ["/api/stream/gpfs/shutdown", "/api/stream/gpfs/startup"])
def test_dry_run_true_does_not_claim_operation(ss, path):
    client = ss.app.test_client()
    resp = client.post(
        path,
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"nodes": ["zima2"], "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


@pytest.mark.parametrize("path", ["/api/stream/gpfs/shutdown", "/api/stream/gpfs/startup"])
def test_rejects_empty_node_list(ss, path):
    client = ss.app.test_client()
    resp = client.post(
        path,
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"nodes": [], "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "At least one node is required" in body


@pytest.mark.parametrize("path", ["/api/stream/gpfs/shutdown", "/api/stream/gpfs/startup"])
def test_rejects_invalid_hostname(ss, path):
    client = ss.app.test_client()
    resp = client.post(
        path,
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"nodes": ["zima2; rm -rf /"], "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "Invalid node hostname" in body


@pytest.mark.parametrize("path", ["/api/stream/gpfs/shutdown", "/api/stream/gpfs/startup"])
def test_returns_busy_when_operation_already_running(ss, path):
    ss._claim_operation("some-other-op", "web")
    client = ss.app.test_client()
    resp = client.post(
        path,
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"nodes": ["zima2"], "dry_run": False},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "busy"' in body
    assert "some-other-op" in body


@pytest.mark.parametrize("action,flag", [("suspend", "--stop"), ("resume", "--start")])
def test_ces_builds_the_documented_command(ss, monkeypatch, action, flag):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "running")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    resp = ss.app.test_client().post(
        f"/api/stream/ces/{action}",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"nodes": ["bg1", "bg2"], "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"] == [
        "sudo", "-n", f"{ss.MMFS_BIN}/mmces", "node", action, "-N", "bg1,bg2", flag,
    ]


@pytest.mark.parametrize("action", ["suspend", "resume"])
def test_ces_defaults_to_dry_run_and_rejects_bad_nodes(ss, action):
    client = ss.app.test_client()
    headers = {"X-Scale-Token": ss._AUTH_TOKEN}
    preview = client.post(f"/api/stream/ces/{action}", headers=headers, json={"nodes": ["bg1"]})
    assert '"type": "dryrun"' in preview.get_data(as_text=True)
    assert ss._current_operation is None
    bad = client.post(f"/api/stream/ces/{action}", headers=headers, json={"nodes": ["bg1; reboot"]})
    assert "Invalid node hostname" in bad.get_data(as_text=True)
