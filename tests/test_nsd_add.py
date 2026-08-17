def test_build_nsd_add_cmd_minimal(ss):
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {"disk": "/dev/sda", "server": "node1"})
    assert err is None
    assert cmd == ["sudo", "-n", "/tp", "nsd", "add", "-p", "node1",
                    "-u", "dataAndMetadata", "-fg", "1", "/dev/sda"]


def test_build_nsd_add_cmd_full(ss):
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {
        "disk": "/dev/sdb", "server": "node1", "backups": ["node2", "node3"],
        "usage": "dataOnly", "failureGroup": "2", "pool": "fastpool", "filesystem": "gpfs0",
    })
    assert err is None
    assert cmd == ["sudo", "-n", "/tp", "nsd", "add", "-p", "node1",
                    "-s", "node2,node3", "-u", "dataOnly", "-fg", "2",
                    "-po", "fastpool", "-fs", "gpfs0", "/dev/sdb"]


def test_build_nsd_add_cmd_never_emits_ambiguous_flags(ss):
    # Regression guard for the earlier flag-guessing mistake in this
    # project's history: -f is ambiguous with -fs/-fg and is never
    # emitted; -s is always the secondary-server list, never a size.
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {
        "disk": "/dev/sda", "server": "node1", "backups": ["node2"],
    })
    assert err is None
    assert "-f" not in cmd
    assert "-t" not in cmd
    s_idx = cmd.index("-s")
    assert cmd[s_idx + 1] == "node2"  # -s takes the backup list, not a size


def test_build_nsd_add_cmd_system_pool_omits_po_flag(ss):
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {
        "disk": "/dev/sda", "server": "node1", "pool": "system",
    })
    assert err is None
    assert "-po" not in cmd


def test_build_nsd_add_cmd_invalid_usage(ss):
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {"disk": "/dev/sda", "server": "node1", "usage": "bogus"})
    assert cmd is None
    assert "invalid usage" in err


def test_build_nsd_add_cmd_invalid_disk_path(ss):
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {"disk": "/dev/sda; rm -rf /", "server": "node1"})
    assert cmd is None
    assert "invalid disk path" in err


def test_build_nsd_add_cmd_rejects_dot_dot_traversal_in_disk(ss):
    # Uses _VALID_DEVICE_PATH_RE (no '.' in its charset), not the looser
    # _SAFE_PATH_RE — see test_validation_regexes.py for why that
    # distinction matters here.
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {"disk": "/dev/../etc/passwd", "server": "node1"})
    assert cmd is None
    assert "invalid disk path" in err


def test_build_nsd_add_cmd_rejects_disk_path_outside_dev(ss):
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {"disk": "/etc/passwd", "server": "node1"})
    assert cmd is None
    assert "invalid disk path" in err


def test_build_nsd_add_cmd_invalid_server_hostname(ss):
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {"disk": "/dev/sda", "server": "node1; id"})
    assert cmd is None
    assert "invalid server hostname" in err


def test_build_nsd_add_cmd_too_many_backups(ss):
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {
        "disk": "/dev/sda", "server": "node1",
        "backups": [f"node{i}" for i in range(8)],
    })
    assert cmd is None
    assert "maximum 7 backup" in err


def test_build_nsd_add_cmd_non_system_pool_requires_dataonly(ss):
    cmd, err = ss._build_nsd_add_cmd("/tp", 1, {
        "disk": "/dev/sda", "server": "node1", "pool": "fastpool", "usage": "dataAndMetadata",
    })
    assert cmd is None
    assert "dataOnly" in err


def test_nsd_pool_usage_error_none_for_valid_combinations(ss):
    assert ss._nsd_pool_usage_error("dataOnly", "fastpool") is None
    assert ss._nsd_pool_usage_error("dataAndMetadata", "system") is None
    assert ss._nsd_pool_usage_error("dataAndMetadata", "") is None


def test_nsd_pool_usage_error_flags_metadata_on_non_system_pool(ss):
    err = ss._nsd_pool_usage_error("dataAndMetadata", "fastpool")
    assert err is not None
    assert "system pool" in err
