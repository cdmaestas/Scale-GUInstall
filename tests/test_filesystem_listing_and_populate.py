"""
`filesystem list` column titles contain spaces, so the old parser matched none
of them and returned made-up values (mount /gpfs/data, replication 2). `nsd
list` likewise invented a failure group and usage. `config populate` reported
success when the toolkit declined to import anything. Sample output is from
toolkit 6.0.1.2.
"""
import pytest

TOOLKIT = "/usr/lpp/mmfs/6.0.1.2/ansible-toolkit/spectrumscale"

FS_LIST = (
    "[ INFO  ] Name    BlockSize   Mountpoint    NSDs Assigned  Default Data Replicas     Max Data Replicas     "
    "Default Metadata Replicas     Max Metadata Replicas    \n"
    "[ INFO  ] zimafs1 4M          /gpfs/zimafs1 6              1                         2                     "
    "2                             2                        \n"
    "[ INFO  ]  \n"
)

NSD_LIST = (
    "[ INFO  ] Name FS      Size(GB) Usage           FG Pool     Device   Servers\n"
    "[ INFO  ] nsd1 zimafs1 931.513  dataAndMetadata 1  system   /dev/sda zima1\n"
    "[ INFO  ] nsd6 zimafs1 931.513  dataOnly        2  data1hdd /dev/sdb zima4\n"
)


def _list(ss, monkeypatch, path, output):
    monkeypatch.setattr(ss, "resolve_path", lambda p: (p, None))
    monkeypatch.setattr(ss, "_sudo_isfile", lambda p: True)
    monkeypatch.setattr(ss, "_run_cmd", lambda cmd, timeout=30: (output, 0))
    return ss.app.test_client().get(path, headers={"X-Scale-Token": ss._AUTH_TOKEN},
                                    query_string={"toolkit": TOOLKIT}).get_json()


def test_filesystem_values_come_from_the_table(ss, monkeypatch):
    body = _list(ss, monkeypatch, "/api/list/filesystem", FS_LIST)
    assert body["ok"] is True
    assert body["filesystems"] == [{"name": "zimafs1", "mount": "/gpfs/zimafs1", "blocksize": "4M",
                                    "replication": "1", "metadataReplication": "2"}]


def test_no_filesystems_is_an_empty_list(ss, monkeypatch):
    body = _list(ss, monkeypatch, "/api/list/filesystem", "[ INFO  ] No file systems are configured.\n")
    assert body["ok"] is True
    assert body["filesystems"] == []


@pytest.mark.parametrize("output", [
    "",
    "[ INFO  ] something else entirely\n",
    FS_LIST.replace("Mountpoint", "Location  "),
    "[ INFO  ] Name    BlockSize   Mountpoint\n[ INFO  ] fs1 4M\n",
])
def test_unreadable_filesystem_output_is_an_error_not_defaults(ss, monkeypatch, output):
    body = _list(ss, monkeypatch, "/api/list/filesystem", output)
    assert body["ok"] is False
    assert body["error"]
    assert "filesystems" not in body


def test_nsd_values_come_from_the_table(ss, monkeypatch):
    body = _list(ss, monkeypatch, "/api/list/nsds", NSD_LIST)
    assert [(n["server"], n["disk"], n["failureGroup"], n["usage"], n["size"]) for n in body["nsds"]] == [
        ("zima1", "/dev/sda", "1", "dataAndMetadata", "931.513"),
        ("zima4", "/dev/sdb", "2", "dataOnly", "931.513"),
    ]


def test_nsd_without_a_failure_group_column_is_an_error(ss, monkeypatch):
    body = _list(ss, monkeypatch, "/api/list/nsds", NSD_LIST.replace(" FG ", " XX "))
    assert body["ok"] is False
    assert "failureGroup" in body["error"]
    assert "nsds" not in body


def _populate(ss, monkeypatch, toolkit_line):
    monkeypatch.setattr(ss, "resolve_path", lambda p: (p, None))
    monkeypatch.setattr(ss, "_sudo_isfile", lambda p: True)

    def fake_stream(cmd, **kwargs):
        yield ss.sse("normal", toolkit_line)
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream)
    resp = ss.app.test_client().post("/api/stream/populate", headers={"X-Scale-Token": ss._AUTH_TOKEN},
                                     json={"toolkit": TOOLKIT, "node": "zima1", "dry_run": False})
    body = resp.get_data(as_text=True)
    op = ss.app.test_client().get("/api/operation/current", headers={"X-Scale-Token": ss._AUTH_TOKEN}).get_json()
    return body, op["status"]


def test_declined_populate_is_an_error(ss, monkeypatch):
    body, status = _populate(ss, monkeypatch, "Do you want to continue  [Y/n]: [ INFO  ] "
                                      "scale_clusterdefinition.json file will not be populated")
    assert "Nothing was imported" in body
    assert "populated successfully" not in body
    assert status == "error"


def test_completed_populate_still_succeeds(ss, monkeypatch):
    body, status = _populate(ss, monkeypatch, "[ INFO  ] Configuration successfully updated.")
    assert status == "success"
    assert "populated successfully" in body
    assert "Nothing was imported" not in body
