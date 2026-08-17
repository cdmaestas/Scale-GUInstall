import pytest


@pytest.mark.parametrize("value", [
    "node1", "gpfs-node01", "192.168.1.10", "node.example.com", "a", "A1_2.-3",
])
def test_valid_hostname_accepts(ss, value):
    assert ss._VALID_HOSTNAME_RE.fullmatch(value)


@pytest.mark.parametrize("value", [
    "", "node1; rm -rf /", "node1 && echo pwned", "node$(whoami)",
    "node`id`", "node1\nnode2", "node1|cat", "a" * 256,
])
def test_valid_hostname_rejects(ss, value):
    assert not ss._VALID_HOSTNAME_RE.fullmatch(value)


@pytest.mark.parametrize("value", ["root", "admin_user", "a", "user.name-1"])
def test_valid_ssh_user_accepts(ss, value):
    assert ss._VALID_SSH_USER_RE.fullmatch(value)


@pytest.mark.parametrize("value", ["", "root; id", "a" * 65])
def test_valid_ssh_user_rejects(ss, value):
    assert not ss._VALID_SSH_USER_RE.fullmatch(value)


@pytest.mark.parametrize("value", ["/dev/sda", "/dev/sdb1", "/dev/nvme0n1", "/dev/mapper/vg-lv"])
def test_valid_device_path_accepts(ss, value):
    assert ss._VALID_DEVICE_PATH_RE.fullmatch(value)


@pytest.mark.parametrize("value", ["", "sda", "-a", "/dev/sda; rm -rf /", "/etc/passwd", "/dev/../etc/passwd"])
def test_valid_device_path_rejects(ss, value):
    # Unlike _SAFE_PATH_RE below, this one also rejects '..' traversal —
    # its charset has no '.' at all, only [A-Za-z0-9/_-] after '/dev/'.
    assert not ss._VALID_DEVICE_PATH_RE.fullmatch(value)


@pytest.mark.parametrize("value", ["mycluster", "gpfs_data.pool-1", "a"])
def test_valid_gpfs_name_accepts(ss, value):
    assert ss._VALID_GPFS_NAME_RE.fullmatch(value)


@pytest.mark.parametrize("value", ["", "my cluster", "pool/data", "name;drop"])
def test_valid_gpfs_name_rejects(ss, value):
    assert not ss._VALID_GPFS_NAME_RE.fullmatch(value)


@pytest.mark.parametrize("value", ["1024", "yes", "4G", "2.5"])
def test_valid_mmchconfig_value_accepts(ss, value):
    assert ss._VALID_MMCHCONFIG_VALUE_RE.fullmatch(value)


@pytest.mark.parametrize("value", ["", "1024;rm -rf /", "1024 ", "-1", "a,b"])
def test_valid_mmchconfig_value_rejects(ss, value):
    assert not ss._VALID_MMCHCONFIG_VALUE_RE.fullmatch(value)


@pytest.mark.parametrize("value", ["/dev/sda", "/tmp/gpfs-packages", "/usr/lpp/mmfs/5.x/spectrumscale"])
def test_safe_path_accepts_legitimate_paths(ss, value):
    assert ss._SAFE_PATH_RE.fullmatch(value)


@pytest.mark.parametrize("value", ["", "/dev/sda; rm -rf /", "/dev/sda $(whoami)", "/dev/sda|cat", "/dev/sda`id`"])
def test_safe_path_rejects_shell_metacharacters(ss, value):
    assert not ss._SAFE_PATH_RE.fullmatch(value)


def test_safe_path_does_not_block_dot_dot_traversal(ss):
    # Documents actual behavior, not a security guarantee: the charset
    # includes '.' and '/', so '..' segments pass the regex untouched.
    # Safety here comes from elsewhere (allowlisted roots via
    # resolve_path(), or the value never reaching a shell), not from
    # this pattern — don't assume it blocks traversal.
    assert ss._SAFE_PATH_RE.fullmatch("/dev/../etc/passwd")
