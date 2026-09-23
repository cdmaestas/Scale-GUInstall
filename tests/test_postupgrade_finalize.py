"""
/api/stream/postupgrade/release-latest (`mmchconfig release=LATEST -i`) and
/api/stream/postupgrade/filesystem-version (`mmchfs <device> -V full|compat`)
— the two post-upgrade finalization steps `spectrumscale upgrade run`
deliberately never does itself (it only upgrades packages). Kept as their
own dedicated endpoints rather than folded into the tunables-only
/api/stream/postconfig/mmchconfig, since bumping the cluster's release
level or a filesystem's on-disk format is a much more consequential action
than a runtime performance tunable.
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_operation_state(ss):
    ss._current_operation = None
    yield
    ss._current_operation = None


# ---- release-latest ---------------------------------------------------

def test_release_latest_builds_the_correct_command(ss, monkeypatch):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "updating")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postupgrade/release-latest",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"] == ["sudo", "-n", f"{ss.MMFS_BIN}/mmchconfig", "release=LATEST", "-i"]


def test_release_latest_dry_run_true_does_not_claim_operation(ss):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postupgrade/release-latest",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


def test_release_latest_returns_busy_when_operation_already_running(ss):
    ss._claim_operation("some-other-op", "web")
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postupgrade/release-latest",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"dry_run": False},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "busy"' in body
    assert "some-other-op" in body


# ---- filesystem-version -------------------------------------------------

def test_filesystem_version_builds_the_correct_command(ss, monkeypatch):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "updating")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postupgrade/filesystem-version",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"device": "gpfs0", "version": "full", "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"] == ["sudo", "-n", f"{ss.MMFS_BIN}/mmchfs", "gpfs0", "-V", "full"]


def test_filesystem_version_defaults_to_full(ss, monkeypatch):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "updating")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postupgrade/filesystem-version",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"device": "gpfs0", "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"][-1] == "full"


def test_filesystem_version_accepts_compat(ss, monkeypatch):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "updating")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postupgrade/filesystem-version",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"device": "gpfs0", "version": "compat", "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"][-1] == "compat"


def test_filesystem_version_rejects_invalid_version(ss):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postupgrade/filesystem-version",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"device": "gpfs0", "version": "5.1.9", "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "Invalid version" in body


def test_filesystem_version_rejects_invalid_device_name(ss):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postupgrade/filesystem-version",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"device": "gpfs0; rm -rf /", "version": "full", "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "Invalid filesystem device name" in body


def test_filesystem_version_dry_run_true_does_not_claim_operation(ss):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postupgrade/filesystem-version",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"device": "gpfs0", "version": "full", "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


def test_filesystem_version_returns_busy_when_operation_already_running(ss):
    ss._claim_operation("some-other-op", "web")
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postupgrade/filesystem-version",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"device": "gpfs0", "version": "full", "dry_run": False},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "busy"' in body
    assert "some-other-op" in body
