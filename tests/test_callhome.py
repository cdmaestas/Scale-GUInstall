"""
/api/stream/callhome (`spectrumscale callhome enable|disable`) — found as a
real gap live: `install --precheck` FATALs when call home is enabled (the
toolkit's default since 5.0.0) but not configured, and there was previously
no way to disable it via this backend — start_cluster_config_apply's
`callhome` flag only ever enables it as part of a broader config-apply, with
no dry-run/operation-buffer support on the underlying GET-based endpoint at
all. Rebuilt as a POST+JSON endpoint matching every other mutating
endpoint's dry_run/operation-buffer convention.
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
        "/api/stream/callhome",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "enable": False, "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"] == ["sudo", "-n", "/tmp/spectrumscale", "callhome", "disable"]


def test_enable_builds_the_correct_command(ss, monkeypatch, _fake_toolkit_exists):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "enabling")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/callhome",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "enable": True, "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"] == ["sudo", "-n", "/tmp/spectrumscale", "callhome", "enable"]


def test_defaults_to_disable(ss, monkeypatch, _fake_toolkit_exists):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "disabling")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/callhome",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"][-1] == "disable"


def test_dry_run_true_does_not_claim_operation(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/callhome",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "enable": False, "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


def test_returns_busy_when_operation_already_running(ss, _fake_toolkit_exists):
    ss._claim_operation("some-other-op", "web")
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/callhome",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "enable": False, "dry_run": False},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "busy"' in body
    assert "some-other-op" in body


def test_nonzero_exit_marks_operation_as_error_not_success(ss, monkeypatch, _fake_toolkit_exists):
    def fake_stream_process(cmd, **kwargs):
        yield ss.sse("normal", "disabling")
        return 1

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/callhome",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "enable": False, "dry_run": False},
    )
    resp.get_data()
    assert ss._current_operation["status"] == "error"
