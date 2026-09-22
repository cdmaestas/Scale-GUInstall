"""
/api/stream/nsd-clear — `spectrumscale nsd clear -f`, verified against a
real `nsd clear -h` (takes only -f/--force, no other arguments) before
implementing, matching this project's established practice of not
guessing at toolkit flags.
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


def test_nsd_clear_builds_the_verified_command(ss, _fake_toolkit_exists, monkeypatch):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "clearing")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/nsd-clear",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "dry_run": False},
    )
    resp.get_data()  # drain the generator so fake_stream_process actually runs
    assert captured["cmd"] == ["sudo", "-n", "/tmp/spectrumscale", "nsd", "clear", "-f"]


def test_nsd_clear_dry_run_true_does_not_claim_operation(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/nsd-clear",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


def test_nsd_clear_returns_busy_when_operation_already_running(ss, _fake_toolkit_exists):
    ss._claim_operation("some-other-op", "web")
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/nsd-clear",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "dry_run": False},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "busy"' in body
    assert "some-other-op" in body


def test_nsd_clear_invalid_toolkit_reports_error(ss):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/nsd-clear",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/nonexistent/spectrumscale", "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "Toolkit not usable" in body
