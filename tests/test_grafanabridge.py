"""
/api/stream/grafanabridge (`spectrumscale grafanabridge enable|disable`) and
/api/list/grafanabridge (`spectrumscale grafanabridge list`) — like
callhome, this only stages the setting in the cluster definition; a
subsequent `deploy` actually installs and activates the bridge.
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


def test_disable_builds_the_correct_command(ss, monkeypatch, _fake_toolkit_exists):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "disabling")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/grafanabridge",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "enable": False, "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"] == ["sudo", "-n", "/tmp/spectrumscale", "grafanabridge", "disable"]


def test_enable_builds_the_correct_command(ss, monkeypatch, _fake_toolkit_exists):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "enabling")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/grafanabridge",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "enable": True, "dry_run": False},
    )
    body = resp.get_data(as_text=True)
    assert captured["cmd"] == ["sudo", "-n", "/tmp/spectrumscale", "grafanabridge", "enable"]
    assert "Run deploy to install and activate it" in body


def test_defaults_to_disable(ss, monkeypatch, _fake_toolkit_exists):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "disabling")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/grafanabridge",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"][-1] == "disable"


def test_dry_run_true_does_not_claim_operation(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/grafanabridge",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "enable": True, "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


def test_returns_busy_when_operation_already_running(ss, _fake_toolkit_exists):
    ss._claim_operation("some-other-op", "web")
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/grafanabridge",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "enable": True, "dry_run": False},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "busy"' in body
    assert "some-other-op" in body


def test_nonzero_exit_marks_operation_as_error_not_success(ss, monkeypatch, _fake_toolkit_exists):
    def fake_stream_process(cmd, **kwargs):
        yield ss.sse("normal", "enabling")
        return 1

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/grafanabridge",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "enable": True, "dry_run": False},
    )
    resp.get_data()
    assert ss._current_operation["status"] == "error"


def test_apply_cluster_config_includes_grafanabridge(ss, monkeypatch, _fake_toolkit_exists):
    """The bundled Cluster Settings apply path also stages grafanabridge,
    mirroring how callhome/perfmon/fileaudit are bundled there."""
    commands = []

    def fake_stream_process(cmd, **kwargs):
        commands.append(cmd)
        yield ss.sse("normal", "running")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/apply-cluster-config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale",
            "gpfs_flags": [],
            "callhome": False,
            "perfmon": True,
            "fileaudit": False,
            "grafana_bridge": True,
            "dry_run": False,
        },
    )
    resp.get_data()
    assert any(cmd[-2:] == ["grafanabridge", "enable"] for cmd in commands)


def test_list_grafanabridge_returns_parsed_properties(ss, monkeypatch, _fake_toolkit_exists):
    monkeypatch.setattr(
        ss, "_run_cmd",
        lambda cmd: ("Enabled: yes\nPort: 4739\n", 0),
    )
    client = ss.app.test_client()
    resp = client.get(
        "/api/list/grafanabridge",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"toolkit": "/tmp/spectrumscale"},
    )
    data = resp.get_json()
    assert data["ok"] is True
    assert data["properties"]


def test_list_grafanabridge_reports_error_on_nonzero_exit(ss, monkeypatch, _fake_toolkit_exists):
    monkeypatch.setattr(ss, "_run_cmd", lambda cmd: ("boom", 1))
    client = ss.app.test_client()
    resp = client.get(
        "/api/list/grafanabridge",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"toolkit": "/tmp/spectrumscale"},
    )
    data = resp.get_json()
    assert data["ok"] is False
