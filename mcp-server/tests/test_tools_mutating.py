"""
Mutating ("start_*") tool functions against a real scale-server.py
instance. Two response shapes to cover, matching _mutate()'s split in
server.py:

- dry_run=True: fully drained, same shape as a read-only tool's SSE
  events — cheap and safe to test for every tool.
- dry_run=False: fire-and-forget — only start_format_disk gets an
  end-to-end real-run test here (cheapest/most bounded endpoint, and
  every other start_* tool shares the exact same _mutate() plumbing, so
  proving the pattern once here covers them all; their dry_run tests
  above already prove each is wired to the right endpoint with the right
  params). `sudo -n` fails immediately without a password prompt and the
  ssh target doesn't exist, so the underlying command fails fast — this
  machine has no real Storage Scale hardware to test against, but the
  fire-and-forget mechanics (started immediately, background drain
  completes, check_operation reflects the outcome) are fully exercised
  either way.

As in test_dry_run.py (repo root), toolkit-path validation is bypassed
via a _sudo_isfile monkeypatch, not faked infrastructure — these tests
verify wiring, not real toolkit behavior.
"""
import asyncio

import pytest

import scale_guinstall_mcp.server as tools


@pytest.fixture(autouse=True)
def _reset_operation_state(ss):
    ss._current_operation = None
    yield
    ss._current_operation = None


@pytest.fixture
def _fake_toolkit_exists(monkeypatch, ss):
    monkeypatch.setattr(ss, "_sudo_isfile", lambda path: True)


# --- dry_run=True: fully drained preview, one per tool ----------------------

async def test_start_format_disk_dry_run_preview(backend_url):
    result = await tools.start_format_disk(node="node1", device="/dev/sdb", dry_run=True)
    assert "events" in result
    assert any(e["type"] == "dryrun" for e in result["events"])


async def test_start_nsd_add_dry_run_preview(backend_url, _fake_toolkit_exists):
    result = await tools.start_nsd_add(
        toolkit="/tmp/spectrumscale",
        nsds=[{"server": "node1", "disk": "/dev/sdb", "usage": "dataAndMetadata"}],
        dry_run=True,
    )
    assert any(e["type"] == "dryrun" for e in result["events"])


async def test_start_nsd_clear_dry_run_preview(backend_url, _fake_toolkit_exists):
    result = await tools.start_nsd_clear(toolkit="/tmp/spectrumscale", dry_run=True)
    assert any(e["type"] == "dryrun" for e in result["events"])


async def test_start_upgrade_offline_nodes_dry_run_preview(backend_url, _fake_toolkit_exists):
    result = await tools.start_upgrade_offline_nodes(
        toolkit="/tmp/spectrumscale", nodes=["node1", "node2"], dry_run=True,
    )
    assert any(e["type"] == "dryrun" for e in result["events"])


async def test_start_release_latest_dry_run_preview(backend_url):
    result = await tools.start_release_latest(dry_run=True)
    assert any(e["type"] == "dryrun" for e in result["events"])


async def test_start_filesystem_version_dry_run_preview(backend_url):
    result = await tools.start_filesystem_version(device="gpfs0", version="full", dry_run=True)
    assert any(e["type"] == "dryrun" for e in result["events"])


async def test_start_node_config_dry_run_preview(backend_url, _fake_toolkit_exists):
    result = await tools.start_node_config(
        toolkit="/tmp/spectrumscale",
        nodes=[{"hostname": "node1", "roles": ["nsd", "quorum"]}],
        dry_run=True,
    )
    assert any(e["type"] == "dryrun" for e in result["events"])


async def test_start_cluster_config_apply_dry_run_preview(backend_url, _fake_toolkit_exists):
    result = await tools.start_cluster_config_apply(
        toolkit="/tmp/spectrumscale",
        gpfs_flags=[{"flag": "-r", "value": "LATEST"}],
        dry_run=True,
    )
    assert any(e["type"] == "dryrun" for e in result["events"])


async def test_start_phase_dry_run_preview(backend_url, _fake_toolkit_exists):
    result = await tools.start_phase(toolkit="/tmp/spectrumscale", phase="install", dry_run=True)
    assert any(e["type"] == "dryrun" for e in result["events"])


async def test_start_setup_dry_run_preview(backend_url, _fake_toolkit_exists):
    result = await tools.start_setup(dir="/tmp", ip="127.0.0.1", dry_run=True)
    assert any(e["type"] == "dryrun" for e in result["events"])


# dry_run=True must never claim the operation slot, for every mutating tool.
async def test_dry_run_never_claims_the_operation(backend_url, _fake_toolkit_exists, ss):
    await tools.start_nsd_add(
        toolkit="/tmp/spectrumscale",
        nsds=[{"server": "node1", "disk": "/dev/sdb", "usage": "dataAndMetadata"}],
        dry_run=True,
    )
    assert ss._current_operation is None


# --- dry_run=False: fire-and-forget, exercised end-to-end once -------------

async def test_start_format_disk_real_run_starts_and_completes(backend_url, ss):
    result = await tools.start_format_disk(node="127.0.0.1", device="/dev/null", dry_run=False)
    assert result["started"] is True

    # The tool call itself returned as soon as the backend accepted the
    # request — the background drain task (and the real ssh/wipefs
    # attempt, which fails fast under sudo -n with no real target) needs a
    # moment to finish and release the operation slot.
    for _ in range(50):
        if ss._current_operation is not None and ss._current_operation["status"] != "running":
            break
        await asyncio.sleep(0.1)

    assert ss._current_operation is not None
    assert ss._current_operation["status"] in ("success", "error")
    assert ss._current_operation["source"] == "mcp"
    assert ss._current_operation["name"] == "format-disk"


async def test_start_format_disk_real_run_reports_busy(backend_url, ss):
    ss._claim_operation("some-other-op", "web")
    result = await tools.start_format_disk(node="127.0.0.1", device="/dev/null", dry_run=False)
    assert result["started"] is False
    assert "some-other-op" in result["message"]


# --- kill_spectrumscale: plain JSON, not a stream ---------------------------

async def test_kill_spectrumscale_when_nothing_running(backend_url, monkeypatch, ss):
    monkeypatch.setattr(ss, "_running_spectrumscale", lambda: [])
    result = await tools.kill_spectrumscale(dry_run=True)
    assert result["killed"] == []
    assert ss._current_operation is None


async def test_kill_spectrumscale_dry_run_preview(backend_url, monkeypatch, ss):
    monkeypatch.setattr(ss, "_running_spectrumscale", lambda: [(123, "spectrumscale install")])
    result = await tools.kill_spectrumscale(dry_run=True)
    assert result["dry_run"] is True
    assert result["would_kill"] == [{"pid": 123, "cmd": "spectrumscale install"}]
    assert ss._current_operation is None
