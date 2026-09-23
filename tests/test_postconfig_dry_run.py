"""
dry_run/operation-buffer support added to the six "Post Configuration" page
endpoints (profiled, guiuser, mmchconfig, healthinterval, nfs-core-dump,
afmgateway) — found as a gap while wiring MCP tools for them: the web UI has
had these wired for a while, but none had dry-run support, and none were
ever exposed via MCP at all. dry_run defaults to False on all six (not True
like newer endpoints) specifically because the existing web UI calls never
send this param — defaulting to True would have silently turned every
existing "run for real" button into a no-op.
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


# ---- profiled ---------------------------------------------------------

def test_profiled_omitted_dry_run_still_runs_for_real(ss, monkeypatch):
    # Checks that the operation buffer gets claimed, proving dry_run
    # defaulted to False (a dry run never claims the buffer).
    def fake_stream_process(cmd, **kwargs):
        yield ss.sse("normal", "running")
        return 0
    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/postconfig/profiled",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
    )
    resp.get_data()
    assert ss._current_operation is not None
    assert ss._current_operation["name"] == "postconfig-profiled"


def test_profiled_dry_run_true_does_not_claim_operation(ss):
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/postconfig/profiled",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"dry_run": "true"},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


# ---- guiuser ------------------------------------------------------------

def test_guiuser_omitted_dry_run_still_runs_for_real(ss, monkeypatch):
    def fake_stream_process(cmd, **kwargs):
        yield ss.sse("normal", "running")
        return 0
    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postconfig/guiuser",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"username": "testuser", "password": "testpass123"},
    )
    resp.get_data()
    assert ss._current_operation is not None
    assert ss._current_operation["name"] == "postconfig-guiuser"


def test_guiuser_dry_run_true_does_not_claim_operation(ss):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postconfig/guiuser",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"username": "testuser", "password": "testpass123", "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


# ---- mmchconfig -----------------------------------------------------------

def test_mmchconfig_omitted_dry_run_still_runs_for_real(ss, monkeypatch):
    def fake_stream_process(cmd, **kwargs):
        yield ss.sse("normal", "running")
        return 0
    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/postconfig/mmchconfig",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"pagepool": "4G"},
    )
    resp.get_data()
    assert ss._current_operation is not None
    assert ss._current_operation["name"] == "postconfig-mmchconfig"


def test_mmchconfig_dry_run_true_does_not_claim_operation(ss):
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/postconfig/mmchconfig",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"pagepool": "4G", "dry_run": "true"},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


# ---- healthinterval ---------------------------------------------------

def test_healthinterval_omitted_dry_run_still_runs_for_real(ss, monkeypatch):
    def fake_stream_process(cmd, **kwargs):
        yield ss.sse("normal", "running")
        return 0
    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/postconfig/healthinterval",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"interval": "LOW"},
    )
    resp.get_data()
    assert ss._current_operation is not None
    assert ss._current_operation["name"] == "postconfig-healthinterval"


def test_healthinterval_dry_run_true_does_not_claim_operation(ss):
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/postconfig/healthinterval",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"interval": "LOW", "dry_run": "true"},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


# ---- nfs-core-dump ----------------------------------------------------

def test_nfs_core_dump_omitted_dry_run_still_runs_for_real(ss, monkeypatch, _fake_toolkit_exists):
    def fake_stream_process(cmd, **kwargs):
        yield ss.sse("normal", "running")
        return 0
    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/nfs-core-dump",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "mode": "enable"},
    )
    resp.get_data()
    assert ss._current_operation is not None
    assert ss._current_operation["name"] == "nfs-core-dump"


def test_nfs_core_dump_dry_run_true_does_not_claim_operation(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/nfs-core-dump",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "mode": "enable", "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


# ---- afmgateway -----------------------------------------------------------

def test_afmgateway_omitted_dry_run_still_runs_for_real(ss, monkeypatch):
    def fake_stream_process(cmd, **kwargs):
        yield ss.sse("normal", "running")
        return 0
    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postconfig/afmgateway",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "fs": "gpfs0", "fileset": "afmfs1", "node": "node1",
            "proto": "nfs", "nfs_target": "nfsserver:/export",
        },
    )
    resp.get_data()
    assert ss._current_operation is not None
    assert ss._current_operation["name"] == "postconfig-afmgateway"


def test_afmgateway_dry_run_true_does_not_claim_operation(ss):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postconfig/afmgateway",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "fs": "gpfs0", "fileset": "afmfs1", "node": "node1",
            "proto": "nfs", "nfs_target": "nfsserver:/export", "dry_run": True,
        },
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


def test_afmgateway_validates_nfs_target_before_creating_fileset(ss, monkeypatch):
    """Regression check: the original code created the fileset (mmcrfileset)
    BEFORE validating that nfs_target was present, so a missing target left
    an orphaned fileset behind. Validation now happens before any command
    runs."""
    calls = []

    def fake_stream_process(cmd, **kwargs):
        calls.append(cmd)
        yield ss.sse("normal", "running")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/postconfig/afmgateway",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"fs": "gpfs0", "fileset": "afmfs1", "node": "node1", "proto": "nfs", "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "NFS target is required" in body
    assert calls == []
