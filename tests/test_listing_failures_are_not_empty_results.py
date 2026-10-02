"""
A directory listing that fails (sudo `ls` times out or exits non-zero) used to
come back from _sudo_listdir as [], which callers could not tell apart from an
empty directory — so a timeout surfaced as "No version directories found",
"No .md5 files found", or a browse result with no files. It now raises OSError
and every caller reports the failure. Also: an unparseable lsblk SIZE is warned
about instead of silently becoming 0.
"""
import json
import subprocess

import pytest


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _listing_times_out(ss, monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 1))
    monkeypatch.setattr(ss.subprocess, "run", fake_run)


def _listing_fails(ss, monkeypatch):
    monkeypatch.setattr(ss.subprocess, "run",
                        lambda cmd, **kw: _Result(returncode=2, stderr="ls: cannot open directory"))


def test_sudo_listdir_raises_on_timeout(ss, monkeypatch):
    _listing_times_out(ss, monkeypatch)
    with pytest.raises(OSError, match="timed out"):
        ss._sudo_listdir("/usr/lpp/mmfs")


def test_sudo_listdir_raises_on_nonzero_exit_with_the_reason(ss, monkeypatch):
    _listing_fails(ss, monkeypatch)
    with pytest.raises(OSError, match="cannot open directory"):
        ss._sudo_listdir("/usr/lpp/mmfs")


def test_sudo_listdir_still_returns_entries_on_success(ss, monkeypatch):
    monkeypatch.setattr(ss.subprocess, "run", lambda cmd, **kw: _Result(stdout="6.0.1.1\nsomething\n"))
    assert ss._sudo_listdir("/usr/lpp/mmfs") == ["6.0.1.1", "something"]


def _client_get(ss, path, **query):
    return ss.app.test_client().get(path, headers={"X-Scale-Token": ss._AUTH_TOKEN}, query_string=query)


def test_browse_files_reports_a_failed_listing_instead_of_an_empty_one(ss, monkeypatch):
    monkeypatch.setattr(ss, "_sudo_isdir", lambda p: True)
    monkeypatch.setattr(ss, "_sudo_listdir", lambda p: (_ for _ in ()).throw(OSError("listing /tmp timed out")))
    resp = _client_get(ss, "/api/browse/files", dir="/tmp")
    assert resp.status_code == 500
    assert "timed out" in resp.get_json()["error"]
    assert "files" not in resp.get_json()


def test_probe_mmfs_reports_the_listing_error_as_the_reason(ss, monkeypatch):
    monkeypatch.setattr(ss, "_sudo_isdir", lambda p: True)
    monkeypatch.setattr(ss, "_sudo_listdir", lambda p: (_ for _ in ()).throw(OSError("listing timed out")))
    body = _client_get(ss, "/api/probe/mmfs").get_json()
    assert body["found"] is False
    assert "timed out" in body["reason"]
    assert "No version directories" not in body["reason"]


def test_checksum_reports_a_failed_listing_not_missing_md5_files(ss, monkeypatch):
    monkeypatch.setattr(ss, "_sudo_isdir", lambda p: True)
    monkeypatch.setattr(ss, "_sudo_listdir", lambda p: (_ for _ in ()).throw(OSError("cannot list /tmp: denied")))
    resp = _client_get(ss, "/api/stream/checksum", dir="/tmp")
    body = resp.get_data(as_text=True)
    assert "cannot list /tmp: denied" in body
    assert "No .md5 files found" not in body


def test_list_devices_warns_on_an_unparseable_size(ss, monkeypatch):
    line = 'NAME="vdz" SIZE="not-a-number" TYPE="disk" FSTYPE="" MOUNTPOINT="" MODEL=""'
    monkeypatch.setattr(ss, "_run_cmd", lambda cmd, **kw: (line + "\n", 0))
    body = _client_get(ss, "/api/stream/list-devices", node="scale-server1").get_data(as_text=True)
    assert "Could not read the size of vdz" in body
    devices_events = [json.loads(chunk[len("data:"):]) for chunk in body.split("\n\n")
                      if chunk.startswith("data:") and '"type": "devices"' in chunk]
    devices = json.loads(devices_events[0]["line"])
    assert devices == [{"name": "vdz", "sizeBytes": 0, "type": "disk", "fstype": "",
                        "mountpoint": "", "model": "", "inUse": False}]
