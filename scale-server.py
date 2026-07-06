#!/usr/bin/env python3
"""
IBM Storage Scale Toolkit — local backend server
Provides real command execution for the ibm-scale-toolkit.html frontend.

Usage:
    pip install flask
    python3 scale-server.py

Listens on http://127.0.0.1:5001 (loopback only — not accessible from the network)
"""

import json
import os
import re
import subprocess

from flask import Flask, Response, jsonify, request, stream_with_context

app = Flask(__name__)


def cors(response):
    origin = request.headers.get("Origin", "")
    # Allow file:// (null origin) and localhost only — reject all remote origins
    if origin in ("null",) or origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


app.after_request(cors)


_ALLOWED_ROOTS = ("/tmp", "/opt", "/usr", "/home", "/root", "/var", "/srv", "/mnt", "/data", "/ibm")

_VALID_HOSTNAME_RE = re.compile(r'^[a-zA-Z0-9._-]{1,255}$')

_ALLOWED_GPFS_FLAGS = frozenset({
    "-c", "-p", "-r", "-rc", "-e", "--gplbin_dir", "--list",
    "--ccr-enable", "--ccr-disable",
})

_VALID_MMCHCONFIG_VALUE_RE = re.compile(r'^[A-Za-z0-9.]+$')


def resolve_path(path):
    """
    Resolve a path and verify it starts with a known safe root.
    Returns (resolved_path, None) on success, (None, error_message) on failure.
    """
    if not path:
        return None, "No path provided."
    resolved = os.path.abspath(path)
    if not any(resolved.startswith(root) for root in _ALLOWED_ROOTS):
        return None, f"Path not within an allowed directory: {resolved}"
    return resolved, None


# ---------------------------------------------------------------------------
# Serve the frontend HTML
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve Scale-GUInstall.html from the same directory as this script."""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Scale-GUInstall.html")
    if not os.path.isfile(html_path):
        return "Scale-GUInstall.html not found next to scale-server.py", 404
    with open(html_path, encoding="utf-8") as f:
        content = f.read()
    return content, 200, {"Content-Type": "text/html; charset=utf-8"}


# ---------------------------------------------------------------------------
# Probe installed Scale version under /usr/lpp/mmfs
# ---------------------------------------------------------------------------

@app.route("/api/probe/mmfs")
def probe_mmfs():
    """
    Check /usr/lpp/mmfs for installed IBM Storage Scale versions.
    Returns the latest version found and the path to the spectrumscale binary.
    """
    import re as _re
    base = "/usr/lpp/mmfs"
    ver_re = _re.compile(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)$")

    if not os.path.isdir(base):
        return jsonify({"found": False, "reason": f"{base} does not exist"})

    versions = []
    try:
        for entry in os.listdir(base):
            m = ver_re.match(entry)
            if m:
                versions.append((tuple(int(x) for x in m.groups()), entry))
    except OSError as exc:
        return jsonify({"found": False, "reason": str(exc)})

    if not versions:
        return jsonify({"found": False, "reason": f"No version directories found in {base}"})

    versions.sort(key=lambda x: x[0], reverse=True)
    latest_tuple, latest_str = versions[0]

    # Look for spectrumscale binary under ansible-toolkit/
    toolkit_path = os.path.join(base, latest_str, "ansible-toolkit", "spectrumscale")
    if not os.path.isfile(toolkit_path):
        toolkit_path = None

    # Build per-version toolkit map for all detected versions
    version_map = {}
    for _, vstr in versions:
        tp = os.path.join(base, vstr, "ansible-toolkit", "spectrumscale")
        version_map[vstr] = tp if os.path.isfile(tp) else None

    all_versions = [v for _, v in sorted(versions, key=lambda x: x[0], reverse=True)]

    return jsonify({
        "found": True,
        "version": latest_str,
        "all_versions": all_versions,
        "version_map": version_map,
        "toolkit_path": toolkit_path,
        "base": base,
    })


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/api/ping")
def ping():
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# File existence check
# ---------------------------------------------------------------------------

@app.route("/api/check-file")
def check_file():
    path, err = resolve_path(request.args.get("path", "").strip())
    if err:
        return jsonify({"exists": False, "error": err}), 400
    return jsonify({"exists": os.path.isfile(path), "path": path})


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def sse(type_, line):
    """Format a single Server-Sent Event."""
    return f"data: {json.dumps({'type': type_, 'line': line})}\n\n"


def sse_response(generator):
    """Wrap a generator in a streaming Response with correct SSE headers."""
    return Response(
        stream_with_context(generator),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def stream_process(cmd, cwd=None):
    """
    Run *cmd* as a subprocess and yield SSE lines from stdout/stderr.
    Does NOT yield a done event — the caller is responsible for that.
    Returns the process exit code via StopIteration.value (yield from).
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        bufsize=0,  # unbuffered — don't wait for a full buffer before yielding
    )
    for raw_line in iter(proc.stdout.readline, b""):
        line = raw_line.decode("utf-8", errors="replace").rstrip()
        if line:
            yield sse("normal", line)
    proc.wait()
    return proc.returncode  # available to caller via: rc = yield from stream_process(...)


# ---------------------------------------------------------------------------
# Extract (unzip)
# ---------------------------------------------------------------------------

@app.route("/api/stream/extract")
def stream_extract():
    zip_path, _zip_err = resolve_path(request.args.get("zip", "").strip())
    dest,     _dst_err = resolve_path(request.args.get("dest", "").strip())

    def generate():
        try:
            if _zip_err:
                yield sse("error", f"[ERROR] Invalid zip path: {_zip_err}")
                return
            if _dst_err:
                yield sse("error", f"[ERROR] Invalid destination path: {_dst_err}")
                return

            if not os.path.isfile(zip_path):
                yield sse("error", f"[ERROR] File not found: {zip_path}")
                yield sse("error", f"[ERROR] Server working directory: {os.getcwd()}")
                yield sse("error", "[ERROR] Use an absolute path or verify the filename.")
                return

            if not dest:
                yield sse("error", "[ERROR] No extraction destination provided.")
                return

            try:
                os.makedirs(dest, exist_ok=True)
            except OSError as exc:
                yield sse("error", f"[ERROR] Cannot create destination directory: {exc}")
                return

            yield sse("info", f"$ unzip -o {zip_path} -d {dest}")
            rc = yield from stream_process(["unzip", "-o", zip_path, "-d", dest])

            if rc == 0:
                yield sse("success", "[OK] Extraction complete.")
            else:
                yield sse("error", f"[ERROR] unzip exited with code {rc}.")

            # Find the self-extracting *-install script at the top level of dest
            installer_path = None
            for entry in os.listdir(dest):
                if entry.endswith("-install") and os.path.isfile(os.path.join(dest, entry)):
                    installer_path = os.path.join(dest, entry)
                    break

            if installer_path:
                yield sse("success", f"[OK] Installer script found: {installer_path}")
                yield sse("hint", installer_path)
            else:
                yield sse("warn", f"[WARN] No *-install script found in {dest}.")
                yield sse("warn", "[WARN] Check the extracted directory structure manually.")

        except Exception as exc:
            yield sse("error", f"[ERROR] Unexpected server error: {exc}")
        finally:
            # Always send done so the client knows the stream has ended
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Verify checksum
# ---------------------------------------------------------------------------

@app.route("/api/stream/checksum")
def stream_checksum():
    directory, _dir_err = resolve_path(request.args.get("dir", "").strip())

    def generate():
        try:
            if _dir_err:
                yield sse("error", f"[ERROR] Invalid directory: {_dir_err}")
                return

            if not os.path.isdir(directory):
                yield sse("error", f"[ERROR] Directory not found: {directory}")
                return

            md5_files = [f for f in os.listdir(directory) if f.endswith(".md5")]
            if not md5_files:
                yield sse("error", f"[ERROR] No .md5 files found in {directory}")
                yield sse("error", "[ERROR] Make sure Step 1 (extract) completed successfully.")
                return

            yield sse("info", f"$ cd {directory} && md5sum -c *.md5")
            rc = yield from stream_process(["md5sum", "-c"] + md5_files, cwd=directory)

            if rc == 0:
                yield sse("success", "[OK] All checksums verified.")
            else:
                yield sse("error", f"[ERROR] Checksum verification failed (exit code {rc}).")
                yield sse("error", "[ERROR] The package may be corrupt. Re-download and try again.")

        except Exception as exc:
            yield sse("error", f"[ERROR] Unexpected server error: {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Run installer
# ---------------------------------------------------------------------------

@app.route("/api/stream/install")
def stream_install():
    installer,  _inst_err = resolve_path(request.args.get("installer", "").strip())
    target_dir, _dir_err  = resolve_path(request.args.get("dir", "").strip())

    def generate():
        try:
            if _inst_err:
                yield sse("error", f"[ERROR] Invalid installer path: {_inst_err}")
                return
            if _dir_err:
                yield sse("error", f"[ERROR] Invalid target directory: {_dir_err}")
                return

            if not os.path.isfile(installer):
                yield sse("error", f"[ERROR] Installer not found: {installer}")
                yield sse("error", "[ERROR] Run Step 1 first, or check the installer path.")
                return

            if not target_dir:
                yield sse("error", "[ERROR] No --dir target directory provided.")
                return

            cmd = ["sh", installer, "--dir", target_dir, "--silent"]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)

            if rc == 0:
                yield sse("success", "[OK] Installer completed successfully.")
                yield sse("success", f"[OK] Scale files installed to: {target_dir}")
            else:
                yield sse("error", f"[ERROR] Installer exited with code {rc}.")

        except Exception as exc:
            yield sse("error", f"[ERROR] Unexpected server error: {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Check Python version
# ---------------------------------------------------------------------------

def _parse_python_version(binary):
    """Run *binary* --version and return (major, minor, version_str, binary) or None."""
    try:
        result = subprocess.run(
            [binary, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
        parts = result.stdout.strip().split()
        if len(parts) == 2 and parts[0] == "Python":
            major, minor, *_ = parts[1].split(".")
            return int(major), int(minor), parts[1], binary
    except Exception:
        pass
    return None


def find_compliant_python():
    """
    Search for the highest Python >= 3.10 available on this system.

    Strategy (in order):
    1. Probe versioned binaries python3.13 … python3.10 in common bin dirs.
    2. Query the package manager (dnf/rpm or apt/dpkg) for installed packages.
    3. Fall back to the default `python3` symlink.

    Returns (major, minor, version_str, binary_path) or None.
    """
    import glob

    search_dirs = ["/usr/bin", "/usr/local/bin", "/opt/rh/rh-python*/root/usr/bin",
                   "/opt/rh/python*/root/usr/bin"]
    candidates = []

    # 1. Probe versioned binaries from newest to oldest
    for minor in range(13, 9, -1):  # 13 down to 10
        for d in search_dirs:
            for path in glob.glob(os.path.join(d, f"python3.{minor}")):
                info = _parse_python_version(path)
                if info and (info[0], info[1]) >= (3, 10):
                    candidates.append(info)

    if candidates:
        # Return the highest version found
        return max(candidates, key=lambda x: (x[0], x[1]))

    # 2. Ask package manager for installed python3.x packages
    pkg_binaries = []
    # dnf/rpm (RHEL, CentOS, Fedora)
    try:
        r = subprocess.run(
            ["rpm", "-qa", "--queryformat", "%{NAME}\n"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=10,
        )
        for pkg in r.stdout.splitlines():
            if pkg.startswith("python3") and pkg[7:].isdigit():
                minor_str = pkg[7:]
                binary = f"/usr/bin/python3.{minor_str}"
                if os.path.isfile(binary):
                    pkg_binaries.append(binary)
    except Exception:
        pass
    # apt/dpkg (Debian, Ubuntu)
    try:
        r = subprocess.run(
            ["dpkg", "-l", "python3.*"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=10,
        )
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "ii" and parts[1].startswith("python3."):
                suffix = parts[1].split("python3.")[1].split(":")[0]
                if suffix.isdigit():
                    binary = f"/usr/bin/python3.{suffix}"
                    if os.path.isfile(binary):
                        pkg_binaries.append(binary)
    except Exception:
        pass

    for binary in pkg_binaries:
        info = _parse_python_version(binary)
        if info and (info[0], info[1]) >= (3, 10):
            candidates.append(info)

    if candidates:
        return max(candidates, key=lambda x: (x[0], x[1]))

    # 3. Fall back to default python3 symlink
    info = _parse_python_version("python3")
    if info and (info[0], info[1]) >= (3, 10):
        return info

    return None


@app.route("/api/stream/checkpython")
def stream_checkpython():
    def generate():
        try:
            yield sse("info", "$ Searching for Python >= 3.10 on this system...")
            info = find_compliant_python()

            if info is None:
                yield sse("error", "[ERROR] No Python >= 3.10 installation found.")
                yield sse("error", "[ERROR] Install Python 3.10+ via your package manager and try again.")
                return

            _, _, version_str, binary = info
            yield sse("normal", f"Found: {binary} — Python {version_str}")
            yield sse("success", f"[OK] Python {version_str} — meets the requirement (>= 3.10).")

        except Exception as exc:
            yield sse("error", f"[ERROR] Unexpected server error: {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Setup installation service
# ---------------------------------------------------------------------------

@app.route("/api/stream/setup")
def stream_setup():
    directory, _dir_err = resolve_path(request.args.get("dir", "").strip())
    server_ip  = request.args.get("ip", "").strip()

    def generate():
        try:
            if _dir_err:
                yield sse("error", f"[ERROR] Invalid working directory: {_dir_err}")
                return

            if not server_ip:
                yield sse("error", "[ERROR] No server IP address provided.")
                return

            spectrumscale_bin = os.path.join(directory, "ansible-toolkit", "spectrumscale")
            if not os.path.isfile(spectrumscale_bin):
                yield sse("error", f"[ERROR] spectrumscale not found at: {spectrumscale_bin}")
                yield sse("error", "[ERROR] Make sure Step 3 (installer) completed successfully.")
                return

            # Verify system python3 >= 3.10
            py_info = find_compliant_python()
            if py_info is None:
                yield sse("error", "[ERROR] No Python >= 3.10 installation found.")
                yield sse("error", "[ERROR] Use 'Check Python Version' above to confirm, then upgrade Python.")
                return
            _, _, py_ver_str, py_binary = py_info
            yield sse("normal", f"[INFO] Python {py_ver_str} confirmed ({py_binary}).")

            cmd = ["sudo", spectrumscale_bin, "setup", "-s", server_ip]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)

            if rc == 0:
                yield sse("success", "[OK] Installation service setup complete.")
            else:
                yield sse("error", f"[ERROR] Setup exited with code {rc}.")

        except Exception as exc:
            yield sse("error", f"[ERROR] Unexpected server error: {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Apply node configuration (spectrumscale node add)
# ---------------------------------------------------------------------------

@app.route("/api/stream/nodes", methods=["POST", "OPTIONS"])
def stream_nodes():
    if request.method == "OPTIONS":
        return "", 204
    body             = request.get_json(silent=True) or {}
    toolkit, _tk_err = resolve_path(body.get("toolkit", "").strip())
    nodes            = body.get("nodes", [])

    def generate():
        try:
            if _tk_err:
                yield sse("error", f"[ERROR] Invalid toolkit path: {_tk_err}")
                return

            if not os.path.isfile(toolkit):
                yield sse("error", f"[ERROR] spectrumscale binary not found: {toolkit}")
                return

            if not isinstance(nodes, list):
                yield sse("error", "[ERROR] Invalid node data.")
                return

            if not nodes:
                yield sse("error", "[ERROR] No nodes provided.")
                return

            role_flag_map = {
                "nsd": "-n", "manager": "-m", "quorum": "-q", "admin": "-a",
                "protocol": "-p", "gui": "-g", "ems": "-e", "callhome": "-c",
            }
            for node in nodes:
                hostname = node.get("hostname", "")
                roles = node.get("roles", [])
                if not hostname:
                    continue
                if not _VALID_HOSTNAME_RE.fullmatch(hostname):
                    yield sse("error", f"[ERROR] Invalid hostname: {hostname!r}")
                    return

                # Delete first so role changes take effect cleanly
                del_cmd = ["sudo", toolkit, "node", "delete", hostname]
                yield sse("info", f"$ {' '.join(del_cmd)}")
                yield from stream_process(del_cmd)  # ignore rc — node may not exist yet

                role_flags = [role_flag_map[r] for r in roles if r in role_flag_map]
                add_cmd = ["sudo", toolkit, "node", "add", hostname] + role_flags
                yield sse("info", f"$ {' '.join(add_cmd)}")
                rc = yield from stream_process(add_cmd)
                if rc == 0:
                    yield sse("success", f"[OK] Node {hostname} added.")
                else:
                    yield sse("error", f"[ERROR] Failed to add node {hostname} (exit code {rc}).")

            yield sse("success", "[OK] All node add commands completed.")

        except Exception as exc:
            yield sse("error", f"[ERROR] Unexpected server error: {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Apply cluster GPFS configuration (spectrumscale config gpfs)
# ---------------------------------------------------------------------------

@app.route("/api/stream/config-gpfs")
def stream_config_gpfs():
    toolkit, _tk_err = resolve_path(request.args.get("toolkit", "").strip())
    flag    = request.args.get("flag", "").strip()
    value   = request.args.get("value", "").strip()

    def generate():
        try:
            if _tk_err:
                yield sse("error", f"[ERROR] Invalid toolkit path: {_tk_err}")
                return

            if not os.path.isfile(toolkit):
                yield sse("error", f"[ERROR] spectrumscale binary not found: {toolkit}")
                return

            if not flag:
                yield sse("error", "[ERROR] No flag provided.")
                return

            if flag not in _ALLOWED_GPFS_FLAGS:
                yield sse("error", f"[ERROR] Unrecognised flag: {flag}")
                return

            cmd = ["sudo", toolkit, "config", "gpfs", flag]
            if value:
                cmd.append(value)

            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)

            if rc == 0:
                yield sse("success", f"[OK] config gpfs {flag} completed.")
            else:
                yield sse("error", f"[ERROR] config gpfs {flag} exited with code {rc}.")

        except Exception as exc:
            yield sse("error", f"[ERROR] Unexpected server error: {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Generic list helpers
# ---------------------------------------------------------------------------

def _run_cmd(cmd, timeout=30):
    """Run a command, return (stdout, returncode)."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.returncode
    except Exception as exc:
        return str(exc), 1


def _parse_table(output):
    """
    Parse a whitespace-aligned tabular output into a list of dicts.
    Assumes the first non-blank line is the header.
    """
    lines = [l for l in output.splitlines() if l.strip()]
    if not lines:
        return []
    # Find header: first line that looks like column titles (no colons)
    header_line = None
    header_idx = 0
    for i, line in enumerate(lines):
        if ':' not in line:
            header_line = line
            header_idx = i
            break
    if header_line is None:
        return []

    # Determine column start positions from header word positions
    headers = []
    col_starts = []
    pos = 0
    for word in header_line.split():
        idx = header_line.index(word, pos)
        headers.append(word.lower().replace(' ', '_'))
        col_starts.append(idx)
        pos = idx + len(word)

    rows = []
    for line in lines[header_idx + 1:]:
        if not line.strip() or line.startswith('-'):
            continue
        row = {}
        for j, (col, start) in enumerate(zip(headers, col_starts)):
            end = col_starts[j + 1] if j + 1 < len(col_starts) else len(line)
            row[col] = line[start:end].strip() if start < len(line) else ''
        rows.append(row)
    return rows


def _parse_kv(output):
    """
    Parse spectrumscale config output into a dict.

    Handles formats emitted by the installer toolkit:
      [INFO] GPFS cluster name: gpfscluster01          <- colon-separated
      [INFO] GPFS cluster name is zima.                <- "is <value>."
      [INFO] GPFS cluster name set to gpfscluster01    <- "set to" phrase
      [INFO] GPFS cluster name is set to gpfscluster01 <- "is set to" phrase
    Bracket prefixes like [INFO], [WARN] are stripped. Trailing periods removed.
    """
    result = {}
    bracket_prefix = re.compile(r'^\s*\[[\w\s]+\]\s*', re.IGNORECASE)
    # Matches "is set to", "set to", or bare "is" followed by a value
    value_phrase = re.compile(r'\s+(?:(?:is\s+)?set\s+to|is)\s+', re.IGNORECASE)

    for line in output.splitlines():
        line = bracket_prefix.sub('', line).strip()
        if not line:
            continue

        if ':' in line:
            k, _, v = line.partition(':')
            key = k.strip().lower().replace(' ', '_')
            result[key] = v.strip().rstrip('.')
        else:
            m = value_phrase.search(line)
            if m:
                k = line[:m.start()].strip().lower().replace(' ', '_')
                v = line[m.end():].strip().rstrip('.')
                result[k] = v

    return result


# ---------------------------------------------------------------------------
# List: nodes
# ---------------------------------------------------------------------------

@app.route("/api/list/nodes")
def list_nodes():
    toolkit, _tk_err = resolve_path(request.args.get("toolkit", "").strip())
    if _tk_err or not os.path.isfile(toolkit):
        return jsonify({"ok": False, "error": _tk_err or f"Toolkit not found: {toolkit}"}), 400

    raw, rc = _run_cmd(["sudo", toolkit, "node", "list"])
    if rc != 0:
        return jsonify({"ok": False, "error": raw.strip(), "raw": raw})

    _INFO_RE = re.compile(r"^\[\s*\w+\s*\]\s?")

    # Strip [ INFO ] / [ WARN ] prefixes
    stripped = [_INFO_RE.sub("", ln) for ln in raw.splitlines()]

    # Find the first header line: starts with "GPFS" and contains "Admin" or "Quorum"
    header_idx = None
    for i, line in enumerate(stripped):
        if line.strip().upper().startswith("GPFS") and (
            "Admin" in line or "Quorum" in line or "admin" in line.lower()
        ):
            header_idx = i
            break

    nodes = []
    if header_idx is not None:
        header = stripped[header_idx]
        # Build column start positions from first header line words
        col_starts = {}
        pos = 0
        for word in header.split():
            idx = header.index(word, pos)
            col_starts[word.lower()] = idx
            pos = idx + len(word)

        # Map header keywords → role names (hostname is the "gpfs" column)
        role_map = {
            "admin":    "admin",
            "quorum":   "quorum",
            "manager":  "manager",
            "nsd":      "nsd",
            "protocol": "protocol",
            "callhome": "callhome",
            "gui":      "gui",
            "ems":      "ems",
        }
        hostname_col = col_starts.get("gpfs", 0)
        # Next col after gpfs gives the width of the hostname field
        sorted_cols = sorted(col_starts.values())
        hostname_end = sorted_cols[sorted_cols.index(hostname_col) + 1] if hostname_col in sorted_cols and sorted_cols.index(hostname_col) + 1 < len(sorted_cols) else hostname_col + 20

        _truthy = {"x", "yes", "true", "1"}
        # Skip the second header line (e.g. "Node   Node   Node   Server …") and blank lines
        for line in stripped[header_idx + 2:]:
            s = line.strip()
            if not s or s.startswith("[") or s.startswith("-"):
                break  # end of node table
            hostname = line[hostname_col:hostname_end].strip()
            if not hostname:
                continue
            roles = []
            for kw, role in role_map.items():
                col = col_starts.get(kw)
                if col is None:
                    continue
                cell = line[col:col + 6].strip() if col < len(line) else ""
                if cell.lower() in _truthy:
                    roles.append(role)
            nodes.append({"hostname": hostname, "roles": roles})

    return jsonify({"ok": True, "raw": raw, "nodes": nodes})


# ---------------------------------------------------------------------------
# List: NSDs
# ---------------------------------------------------------------------------

@app.route("/api/list/nsds")
def list_nsds():
    toolkit, _tk_err = resolve_path(request.args.get("toolkit", "").strip())
    if _tk_err or not os.path.isfile(toolkit):
        return jsonify({"ok": False, "error": _tk_err or f"Toolkit not found: {toolkit}"}), 400

    raw, rc = _run_cmd(["sudo", toolkit, "nsd", "list"])
    if rc != 0:
        return jsonify({"ok": False, "error": raw.strip(), "raw": raw})

    rows = _parse_table(raw)
    nsds = []
    for row in rows:
        disk = row.get("disk", row.get("device", row.get("path", ""))).strip()
        if not disk:
            continue
        nsds.append({
            "disk":         disk,
            "server":       row.get("server", row.get("servers", row.get("primary_server", ""))).strip(),
            "backup":       row.get("backup", row.get("backup_server", "")).strip(),
            "failureGroup": row.get("fg", row.get("failuregroup", row.get("failure_group", "1"))).strip() or "1",
            "usage":        row.get("usage", "dataAndMetadata").strip() or "dataAndMetadata",
            "size":         row.get("size", "").strip(),
        })

    return jsonify({"ok": True, "raw": raw, "nsds": nsds})


# ---------------------------------------------------------------------------
# List: filesystems
# ---------------------------------------------------------------------------

@app.route("/api/list/filesystem")
def list_filesystem():
    toolkit, _tk_err = resolve_path(request.args.get("toolkit", "").strip())
    if _tk_err or not os.path.isfile(toolkit):
        return jsonify({"ok": False, "error": _tk_err or f"Toolkit not found: {toolkit}"}), 400

    raw, rc = _run_cmd(["sudo", toolkit, "filesystem", "list"])
    if rc != 0:
        return jsonify({"ok": False, "error": raw.strip(), "raw": raw})

    rows = _parse_table(raw)
    filesystems = []
    for row in rows:
        name = row.get("name", row.get("filesystem", row.get("fs", ""))).strip()
        if not name:
            continue
        filesystems.append({
            "name":        name,
            "mount":       row.get("mount", row.get("mount_point", "/gpfs/data")).strip(),
            "blocksize":   row.get("block_size", row.get("blocksize", "256K")).strip(),
            "replication": row.get("replication", row.get("data_rep", "2")).strip(),
        })

    return jsonify({"ok": True, "raw": raw, "filesystems": filesystems})


# ---------------------------------------------------------------------------
# List: cluster config
# ---------------------------------------------------------------------------

@app.route("/api/list/config")
def list_config():
    toolkit, _tk_err = resolve_path(request.args.get("toolkit", "").strip())
    if _tk_err or not os.path.isfile(toolkit):
        return jsonify({"ok": False, "error": _tk_err or f"Toolkit not found: {toolkit}"}), 400

    raw, rc = _run_cmd(["sudo", toolkit, "config", "gpfs", "--list"])
    if rc != 0:
        return jsonify({"ok": False, "error": raw.strip(), "raw": raw})

    kv = _parse_kv(raw)

    def _first(*keys, default=""):
        for k in keys:
            v = kv.get(k, "")
            if v and v.lower() != "none":
                return v
        return default

    config = {
        "cluster_name": _first(
            "gpfs_cluster_name", "cluster_name", "name",
        ),
        "rsh": _first(
            "remote_shell_command", "remote_shell_binary",
            "remote_shell", "remote_shell_path",
            default="/usr/bin/ssh",
        ),
        "rcp": _first(
            "remote_file_copy_command", "remote_file_copy_binary",
            "remote_file_copy", "remote_copy_command",
            default="/usr/bin/scp",
        ),
        "port_range": _first(
            "gpfs_daemon_communication_port_range",
            "ephemeral_port_range", "port_range",
            "tcp_port_range", "communication_port_range",
            default="60000-61000",
        ),
        "profile": _first(
            "gpfs_profile", "profile", "profile_name",
        ),
    }

    # Include the raw parsed keys for diagnostics
    return jsonify({"ok": True, "raw": raw, "config": config, "parsed_keys": list(kv.keys())})


# ---------------------------------------------------------------------------
# Config populate
# ---------------------------------------------------------------------------

@app.route("/api/stream/populate", methods=["POST", "OPTIONS"])
def stream_populate():
    if request.method == "OPTIONS":
        return "", 204
    body     = request.get_json(silent=True) or {}
    toolkit, _tk_err = resolve_path(body.get("toolkit", "").strip())
    node     = body.get("node", "").strip()
    skip_ssh = body.get("skip_ssh", True)
    skip_nsd = body.get("skip_nsd", False)

    def generate():
        try:
            if _tk_err or not os.path.isfile(toolkit):
                yield sse("error", f"[ERROR] Toolkit not found: {_tk_err or toolkit}")
                return
            if not node:
                yield sse("error", "[ERROR] Node is required.")
                return
            cmd = ["sudo", toolkit, "config", "populate", "-N", node]
            if skip_ssh:
                cmd += ["--skip", "ssh"]
            if skip_nsd:
                cmd += ["--skip", "nsd"]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", "[OK] Cluster definition populated successfully.")
            else:
                yield sse("error", f"[ERROR] config populate exited with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Call Home enable / disable
# ---------------------------------------------------------------------------

@app.route("/api/stream/callhome")
def stream_callhome():
    toolkit, _tk_err = resolve_path(request.args.get("toolkit", "").strip())
    enable  = request.args.get("enable", "false").lower() in ("true", "1", "yes")

    def generate():
        try:
            if _tk_err or not os.path.isfile(toolkit):
                yield sse("error", f"[ERROR] Toolkit not found: {_tk_err or toolkit}")
                return
            action = "enable" if enable else "disable"
            cmd = ["sudo", toolkit, "callhome", action]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", f"[OK] Call Home {action}d.")
            else:
                yield sse("error", f"[ERROR] callhome {action} exited with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Performance monitoring enable / disable
# ---------------------------------------------------------------------------

@app.route("/api/stream/perfmon")
def stream_perfmon():
    toolkit, _tk_err = resolve_path(request.args.get("toolkit", "").strip())
    enable    = request.args.get("enable", "false").lower() in ("true", "1", "yes")

    def generate():
        try:
            if _tk_err or not os.path.isfile(toolkit):
                yield sse("error", f"[ERROR] Toolkit not found: {_tk_err or toolkit}")
                return
            cmd = ["sudo", toolkit, "config", "perfmon", "-r", "on" if enable else "off"]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", f"[OK] Performance monitoring {'enabled' if enable else 'disabled'}.")
            else:
                yield sse("error", f"[ERROR] config perfmon exited with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# File audit logging enable / disable
# ---------------------------------------------------------------------------

@app.route("/api/stream/fileaudit")
def stream_fileaudit():
    toolkit, _tk_err = resolve_path(request.args.get("toolkit", "").strip())
    enable  = request.args.get("enable", "false").lower() in ("true", "1", "yes")
    logfs   = request.args.get("logfs", "").strip()

    def generate():
        try:
            if _tk_err or not os.path.isfile(toolkit):
                yield sse("error", f"[ERROR] Toolkit not found: {_tk_err or toolkit}")
                return
            if enable:
                cmd = ["sudo", toolkit, "fileauditlogging", "enable"]
                if logfs:
                    cmd += ["--log-fileset", logfs]
            else:
                cmd = ["sudo", toolkit, "fileauditlogging", "disable"]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", f"[OK] File audit logging {'enabled' if enable else 'disabled'}.")
            else:
                yield sse("error", f"[ERROR] fileauditlogging exited with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Apply all cluster config commands in one stream
# ---------------------------------------------------------------------------

@app.route("/api/stream/apply-cluster-config", methods=["POST", "OPTIONS"])
def stream_apply_cluster_config():
    if request.method == "OPTIONS":
        return "", 204
    body = request.get_json(silent=True) or {}
    toolkit, _tk_err = resolve_path(body.get("toolkit", "").strip())

    gpfs_flags   = body.get("gpfs_flags", [])   # list of {flag, value}
    callhome_on  = body.get("callhome", False)
    perfmon_on   = body.get("perfmon", False)
    perfmon_node = body.get("perfmon_node", "")
    fileaudit_on = body.get("fileaudit", False)
    fileaudit_fs = body.get("fileaudit_fs", "")

    def generate():
        try:
            if _tk_err or not os.path.isfile(toolkit):
                yield sse("error", f"[ERROR] Toolkit not found: {_tk_err or toolkit}")
                return

            # config gpfs flags
            for entry in gpfs_flags:
                flag  = entry.get("flag", "")
                value = entry.get("value", "")
                if not flag:
                    continue
                if flag not in _ALLOWED_GPFS_FLAGS:
                    yield sse("error", f"[ERROR] Unrecognised flag: {flag}")
                    return
                cmd = ["sudo", toolkit, "config", "gpfs", flag]
                if value:
                    cmd.append(value)
                yield sse("info", f"$ {' '.join(cmd)}")
                rc = yield from stream_process(cmd)
                if rc == 0:
                    yield sse("success", f"[OK] config gpfs {flag} completed.")
                else:
                    yield sse("error", f"[ERROR] config gpfs {flag} exited with code {rc}.")

            # callhome
            ch_action = "enable" if callhome_on else "disable"
            cmd = ["sudo", toolkit, "callhome", ch_action]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", f"[OK] Call Home {ch_action}d.")
            else:
                yield sse("error", f"[ERROR] callhome {ch_action} exited with code {rc}.")

            # perfmon
            pm_flag = "on" if perfmon_on else "off"
            cmd = ["sudo", toolkit, "config", "perfmon", "-r", pm_flag]
            if perfmon_node:
                cmd += ["-N", perfmon_node]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", f"[OK] Performance monitoring {pm_flag}.")
            else:
                yield sse("error", f"[ERROR] config perfmon exited with code {rc}.")

            # fileaudit
            if fileaudit_on:
                cmd = ["sudo", toolkit, "fileauditlogging", "enable"]
                if fileaudit_fs:
                    cmd += ["--log-fileset", fileaudit_fs]
            else:
                cmd = ["sudo", toolkit, "fileauditlogging", "disable"]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", f"[OK] File audit logging {'enabled' if fileaudit_on else 'disabled'}.")
            else:
                yield sse("error", f"[ERROR] fileauditlogging exited with code {rc}.")

        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# List partitions on a remote node via SSH
# ---------------------------------------------------------------------------

@app.route("/api/stream/list-partitions")
def stream_list_partitions():
    node = request.args.get("node", "").strip()

    def generate():
        try:
            if not node:
                yield sse("error", "[ERROR] Node is required.")
                return
            if not _VALID_HOSTNAME_RE.fullmatch(node):
                yield sse("error", f"[ERROR] Invalid node hostname: {node!r}")
                return
            cmd = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10", node, "cat", "/proc/partitions"]
            yield sse("info", f"$ ssh {node} cat /proc/partitions")
            rc = yield from stream_process(cmd)
            if rc != 0:
                yield sse("error", f"[ERROR] SSH to {node} failed with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Post-configuration endpoints
# ---------------------------------------------------------------------------

_SAFE_PATH_RE = re.compile(r'^[/a-zA-Z0-9_.:-]+$')


@app.route("/api/stream/postconfig/profiled")
def stream_profiled():
    binpath = request.args.get("binpath", "/usr/lpp/mmfs/bin").strip()

    def generate():
        try:
            if not _SAFE_PATH_RE.fullmatch(binpath):
                yield sse("error", "[ERROR] Invalid binpath — only alphanumeric characters, '/', '.', '_', '-', and ':' are allowed.")
                return

            profile_content = f"export PATH=$PATH:{binpath}\n"
            import tempfile, shutil
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as tf:
                tf.write(profile_content)
                tmp_path = tf.name

            dest = "/etc/profile.d/gpfs.sh"
            cmd = ["sudo", "cp", tmp_path, dest]
            yield sse("info", f"$ sudo cp <tmpfile> {dest}  # content: export PATH=$PATH:{binpath}")
            rc = yield from stream_process(cmd)
            __import__("os").unlink(tmp_path)

            if rc == 0:
                chmod_cmd = ["sudo", "chmod", "644", dest]
                yield from stream_process(chmod_cmd)
            if rc == 0:
                yield sse("success", "[OK] /etc/profile.d/gpfs.sh created. Source it or re-login to apply.")
            else:
                yield sse("error", f"[ERROR] profile.d setup exited with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


@app.route("/api/stream/postconfig/guiuser", methods=["POST", "OPTIONS"])
def stream_guiuser():
    if request.method == "OPTIONS":
        return "", 204
    body     = request.get_json(silent=True) or {}
    username = body.get("username", "").strip()
    role     = body.get("role", "SecurityAdmin").strip()
    password = body.get("password", "").strip()

    def generate():
        try:
            if not username or not password:
                yield sse("error", "[ERROR] Username and password are required.")
                return
            gui_cli = "/usr/lpp/mmfs/gui/cli/mkuser"
            cmd = ["sudo", gui_cli, username, "-g", role, "-p", password]
            yield sse("info", f"$ sudo {gui_cli} {username} -g {role} -p ********")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", f"[OK] GUI user '{username}' created with role {role}.")
            else:
                yield sse("error", f"[ERROR] mkuser exited with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


@app.route("/api/stream/postconfig/mmchconfig")
def stream_mmchconfig():
    allowed = {"maxFilesToCache", "maxStatCache", "pagepool", "maxMBpS"}
    settings = {k: v.strip() for k, v in request.args.items() if k in allowed and v.strip()}

    def generate():
        try:
            if not settings:
                yield sse("error", "[ERROR] No settings provided.")
                return
            for key, val in settings.items():
                if not _VALID_MMCHCONFIG_VALUE_RE.fullmatch(val):
                    yield sse("error", f"[ERROR] Invalid value for {key}: {val!r}")
                    return
                cmd = ["sudo", "mmchconfig", f"{key}={val}", "-i"]
                yield sse("info", f"$ {' '.join(cmd)}")
                rc = yield from stream_process(cmd)
                if rc != 0:
                    yield sse("error", f"[ERROR] mmchconfig {key} exited with code {rc}.")
                    return
            yield sse("success", "[OK] GPFS configuration settings applied.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


@app.route("/api/stream/postconfig/healthinterval")
def stream_healthinterval():
    interval = request.args.get("interval", "DEFAULT").strip().upper()
    nodes    = request.args.get("nodes", "all").strip()
    valid    = {"OFF", "LOW", "MEDIUM", "DEFAULT", "HIGH"}

    def generate():
        try:
            if interval not in valid:
                yield sse("error", f"[ERROR] Invalid interval '{interval}'. Must be one of: {', '.join(sorted(valid))}.")
                return
            cmd = ["sudo", "mmhealth", "config", "interval", interval, "-N", nodes]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", f"[OK] Health monitoring interval set to {interval} on {nodes}.")
            else:
                yield sse("error", f"[ERROR] mmhealth config exited with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


@app.route("/api/stream/postconfig/afmgateway", methods=["POST", "OPTIONS"])
def stream_afmgateway():
    if request.method == "OPTIONS":
        return "", 204
    body    = request.get_json(silent=True) or {}
    proto   = body.get("proto", "nfs").strip()
    fs      = body.get("fs", "").strip()
    fileset = body.get("fileset", "").strip()
    node    = body.get("node", "").strip()
    mode    = body.get("mode", "ro").strip()

    def generate():
        try:
            if not fs or not fileset or not node:
                yield sse("error", "[ERROR] Filesystem, fileset, and gateway node are required.")
                return

            # Step 1: create the fileset
            cmd1 = ["sudo", "mmcrfileset", fs, fileset, "--inode-space", "new"]
            yield sse("info", f"$ {' '.join(cmd1)}")
            rc = yield from stream_process(cmd1)
            if rc != 0:
                yield sse("error", f"[ERROR] mmcrfileset exited with code {rc}.")
                return

            # Step 2: configure AFM target
            if proto == "nfs":
                nfs_target = body.get("nfs_target", "").strip()
                if not nfs_target:
                    yield sse("error", "[ERROR] NFS target is required.")
                    return
                cmd2 = ["sudo", "mmafmconfig", fs, fileset, "-N", node,
                        "--afm-target", f"nfs://{nfs_target}", "--afm-mode", mode]
            else:
                s3_url    = body.get("s3_url", "").strip()
                s3_bucket = body.get("s3_bucket", "").strip()
                s3_key    = body.get("s3_key", "").strip()
                s3_secret = body.get("s3_secret", "").strip()
                if not all([s3_url, s3_bucket, s3_key, s3_secret]):
                    yield sse("error", "[ERROR] All S3 fields are required.")
                    return
                cmd2 = ["sudo", "mmafmconfig", fs, fileset, "-N", node,
                        "--afm-target", f"s3://{s3_url}/{s3_bucket}",
                        "--afm-mode", mode, "-K", s3_key, "-E", s3_secret]
                yield sse("info", f"$ sudo mmafmconfig {fs} {fileset} -N {node} --afm-target s3://{s3_url}/{s3_bucket} --afm-mode {mode} -K {s3_key} -E ********")

            if proto == "nfs":
                yield sse("info", f"$ {' '.join(cmd2)}")
            rc = yield from stream_process(cmd2)
            if rc != 0:
                yield sse("error", f"[ERROR] mmafmconfig exited with code {rc}.")
                return

            # Step 3: link the fileset
            junction = f"/ibm/{fs}/{fileset}"
            cmd3 = ["sudo", "mmlinkfileset", fs, fileset, "-J", junction]
            yield sse("info", f"$ {' '.join(cmd3)}")
            rc = yield from stream_process(cmd3)
            if rc == 0:
                yield sse("success", f"[OK] AFM fileset '{fileset}' configured and linked at {junction}.")
            else:
                yield sse("error", f"[ERROR] mmlinkfileset exited with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# Install / deploy / precheck phases
# ---------------------------------------------------------------------------

PHASE_CMDS = {
    "precheck-install":  ["install", "--precheck"],
    "install":           ["install"],
    "postcheck-install": ["install", "--postcheck"],
    "enable-daemon":     ["scaleadmd", "enable"],
    "nodeid-define":     ["nodeid", "define"],
    "precheck-deploy":   ["deploy", "--precheck"],
    "deploy":            ["deploy"],
    "postcheck-deploy":  ["deploy", "--postcheck"],
}

_SKIP_SSH_PHASES = {"precheck-install", "install", "postcheck-install",
                    "precheck-deploy", "deploy", "postcheck-deploy"}

@app.route("/api/stream/phase")
def stream_phase():
    toolkit,  _tk_err  = resolve_path(request.args.get("toolkit", "").strip())
    phase    = request.args.get("phase", "").strip()
    skip_ssh = request.args.get("skip_ssh", "false").lower() in ("true", "1", "yes")

    def generate():
        try:
            if _tk_err or not os.path.isfile(toolkit):
                yield sse("error", f"[ERROR] Toolkit not found: {_tk_err or toolkit}")
                return
            args = PHASE_CMDS.get(phase)
            if args is None:
                yield sse("error", f"[ERROR] Unknown phase: {phase}")
                return
            cmd = ["sudo", toolkit] + args
            if skip_ssh and phase in _SKIP_SSH_PHASES:
                cmd += ["--skip", "ssh"]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", f"[OK] {phase} completed successfully.")
            else:
                yield sse("error", f"[ERROR] {phase} exited with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------
# CCR status check
# ---------------------------------------------------------------------------

@app.route("/api/stream/ccr-status")
def stream_ccr_status():
    def generate():
        try:
            cmd = ["mmlscluster"]
            yield sse("info", "$ mmlscluster | grep -i Repository")
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0
            )
            found = False
            for raw in iter(proc.stdout.readline, b""):
                line = raw.decode("utf-8", errors="replace").rstrip()
                if "repository" in line.lower():
                    found = True
                    yield sse("normal", line)
            proc.wait()
            if not found:
                yield sse("warn", "[WARN] No 'Repository' line found in mmlscluster output.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")
    return sse_response(generate())


# ---------------------------------------------------------------------------
# Ansible version check
# ---------------------------------------------------------------------------

@app.route("/api/stream/check-ansible")
def stream_check_ansible():
    def generate():
        try:
            result = subprocess.run(
                ["ansible", "--version"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=10,
            )
            first_line = result.stdout.splitlines()[0] if result.stdout.strip() else ""
            yield sse("normal", first_line or "[WARN] No output from ansible --version")

            m = re.search(r"(\d+)\.(\d+)\.(\d+)", first_line)
            if not m:
                yield sse("warn", "[WARN] Could not parse ansible version — check manually.")
            else:
                major, minor = int(m.group(1)), int(m.group(2))
                version_str = m.group(0)
                if major > 2 or (major == 2 and minor >= 24):
                    yield sse("error",
                        f"[ERROR] ansible-core {version_str} is INCOMPATIBLE with the toolkit.")
                    yield sse("error",
                        "[ERROR] Downgrade: pip install 'ansible-core<2.24'")
                    yield sse("ansible-compat", "fail")
                else:
                    yield sse("success", f"[OK] ansible-core {version_str} is compatible (< 2.24).")
                    yield sse("ansible-compat", "ok")
        except FileNotFoundError:
            yield sse("warn", "[WARN] ansible not found — it may not be installed yet.")
            yield sse("ansible-compat", "missing")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")
    return sse_response(generate())


# ---------------------------------------------------------------------------
# Locale check
# ---------------------------------------------------------------------------

@app.route("/api/stream/check-locale")
def stream_check_locale():
    def generate():
        try:
            yield sse("info", "$ locale | grep LC_ALL")
            result = subprocess.run(
                ["locale"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "LC_ALL" in line:
                    yield sse("normal", line)
                    val = line.split("=", 1)[-1].strip().strip('"')
                    if not val or val == "C" or val == "POSIX":
                        yield sse("warn",
                            "[WARN] LC_ALL is not set or is C/POSIX — set it before installing:")
                        yield sse("warn", "       export LC_ALL=en_US.UTF-8")
                    else:
                        yield sse("success", f"[OK] LC_ALL={val}")
                    break
            else:
                yield sse("warn", "[WARN] LC_ALL not found in locale output.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")
    return sse_response(generate())


# ---------------------------------------------------------------------------
# NFS core dump enable / disable
# ---------------------------------------------------------------------------

@app.route("/api/stream/nfs-core-dump", methods=["POST", "OPTIONS"])
def stream_nfs_core_dump():
    if request.method == "OPTIONS":
        return "", 204
    body             = request.get_json(silent=True) or {}
    toolkit, _tk_err = resolve_path(body.get("toolkit", "").strip())
    mode             = body.get("mode", "enable").strip().lower()

    def generate():
        try:
            if mode not in ("enable", "disable"):
                yield sse("error", f"[ERROR] Invalid mode '{mode}'. Use 'enable' or 'disable'.")
                return
            if _tk_err or not os.path.isfile(toolkit):
                yield sse("error", f"[ERROR] Toolkit not found: {_tk_err or toolkit}")
                return
            cmd = ["sudo", toolkit, "nfs_core_dump", mode]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc == 0:
                yield sse("success", f"[OK] NFS core dump {mode}d.")
            else:
                yield sse("error", f"[ERROR] nfs_core_dump {mode} exited with code {rc}.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")
    return sse_response(generate())


# ---------------------------------------------------------------------------

@app.route("/api/stream/node-identity", methods=["POST", "OPTIONS"])
def stream_node_identity():
    if request.method == "OPTIONS":
        return "", 204
    body         = request.get_json(silent=True) or {}
    tls_dir_raw  = body.get("tls_dir", "~/tls").strip()
    org_name     = body.get("org_name", "IBM").strip() or "IBM"
    cluster_name = body.get("cluster_name", "").strip()
    ca_cn        = body.get("ca_cn", "ScaleCA").strip() or "ScaleCA"
    try:
        days = max(1, min(int(body.get("days", 10000)), 36525))
    except (ValueError, TypeError):
        days = 10000
    nodes        = body.get("nodes", [])
    ssh_user     = body.get("ssh_user", "root").strip() or "root"
    import_ssh   = bool(body.get("import_via_ssh", False))
    add_trust    = bool(body.get("add_trust", False))

    def generate():
        try:
            tls_dir = os.path.expanduser(tls_dir_raw)
            resolved = os.path.abspath(tls_dir)
            if not any(resolved.startswith(r) for r in _ALLOWED_ROOTS):
                yield sse("error", f"[ERROR] TLS directory not in an allowed path: {resolved}")
                return
            if not cluster_name:
                yield sse("error", "[ERROR] Cluster name is required for certificate CN.")
                return
            if not nodes:
                yield sse("error", "[ERROR] No nodes configured.")
                return

            # 1. Create TLS directory
            cmd = ["mkdir", "-p", tls_dir]
            yield sse("info", f"$ {' '.join(cmd)}")
            rc = yield from stream_process(cmd)
            if rc != 0:
                yield sse("error", "[ERROR] Could not create TLS directory.")
                return

            ca_key = os.path.join(tls_dir, "ca.key")
            ca_crt = os.path.join(tls_dir, "ca.crt")

            # 2. Generate CA private key (skip if already exists)
            if not os.path.exists(ca_key):
                cmd = ["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", ca_key]
                yield sse("info", f"$ {' '.join(cmd)}")
                rc = yield from stream_process(cmd)
                if rc != 0:
                    yield sse("error", "[ERROR] CA key generation failed.")
                    return
            else:
                yield sse("info", f"# CA key already exists: {ca_key} (reusing)")

            # 3. Generate self-signed CA certificate (skip if already exists)
            if not os.path.exists(ca_crt):
                subj = f"/O={org_name}/CN={ca_cn}"
                cmd = ["openssl", "req", "-new", "-x509", "-sha256",
                       "-key", ca_key, "-out", ca_crt,
                       "-subj", subj, "-days", str(days)]
                yield sse("info", f"$ {' '.join(cmd)}")
                rc = yield from stream_process(cmd)
                if rc != 0:
                    yield sse("error", "[ERROR] CA cert generation failed.")
                    return
            else:
                yield sse("info", f"# CA cert already exists: {ca_crt} (reusing)")

            yield sse("success", "[OK] CA ready.")

            # 4. Per-node certificate generation
            for node_info in nodes:
                hostname = (node_info.get("hostname") or "").strip()
                fqdn     = (node_info.get("fqdn") or "").strip() or hostname
                if not hostname:
                    continue
                if not _VALID_HOSTNAME_RE.fullmatch(hostname):
                    yield sse("error", f"[ERROR] Invalid hostname: {hostname!r}")
                    continue
                if fqdn != hostname and not _VALID_HOSTNAME_RE.fullmatch(fqdn):
                    yield sse("error", f"[ERROR] Invalid FQDN: {fqdn!r}")
                    continue

                short_name = hostname.split(".")[0]
                node_key  = os.path.join(tls_dir, f"{hostname}.key")
                node_csr  = os.path.join(tls_dir, f"{hostname}.csr")
                node_pem  = os.path.join(tls_dir, f"{hostname}.pem")
                san_conf  = os.path.join(tls_dir, f"{hostname}-san.conf")

                yield sse("info", f"# ── Node: {hostname} ──")

                # Generate node private key
                cmd = ["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", node_key]
                yield sse("info", f"$ {' '.join(cmd)}")
                rc = yield from stream_process(cmd)
                if rc != 0:
                    yield sse("error", f"[ERROR] Key generation failed for {hostname}.")
                    continue

                # Generate CSR with cluster name as CN
                subj = f"/O={org_name}/CN={cluster_name}"
                cmd = ["openssl", "req", "-new", "-sha256",
                       "-key", node_key, "-out", node_csr, "-subj", subj]
                yield sse("info", f"$ {' '.join(cmd)}")
                rc = yield from stream_process(cmd)
                if rc != 0:
                    yield sse("error", f"[ERROR] CSR generation failed for {hostname}.")
                    continue

                # Write SAN config file
                san_content = (
                    "[req]\nreq_extensions = v3_req\n"
                    "[v3_req]\nsubjectAltName = @alt_names\n"
                    "[alt_names]\n"
                    f"DNS.1 = {short_name}\n"
                    f"DNS.2 = {fqdn}\n"
                )
                try:
                    with open(san_conf, "w") as f:
                        f.write(san_content)
                    yield sse("info", f"# SAN config written: {san_conf}")
                except OSError as exc:
                    yield sse("error", f"[ERROR] Could not write SAN config: {exc}")
                    continue

                # Sign node certificate with CA
                cmd = ["openssl", "x509", "-req",
                       "-in", node_csr, "-CA", ca_crt, "-CAkey", ca_key,
                       "-CAcreateserial", "-out", node_pem,
                       "-days", str(days), "-sha256",
                       "-extensions", "v3_req", "-extfile", san_conf]
                yield sse("info", f"$ {' '.join(cmd)}")
                rc = yield from stream_process(cmd)
                if rc != 0:
                    yield sse("error", f"[ERROR] Cert signing failed for {hostname}.")
                    continue

                # Verify certificate chain
                cmd = ["openssl", "verify", "-CAfile", ca_crt, node_pem]
                yield sse("info", f"$ {' '.join(cmd)}")
                rc = yield from stream_process(cmd)
                if rc != 0:
                    yield sse("error", f"[ERROR] Cert verification failed for {hostname}.")
                    continue

                yield sse("success", f"[OK] Certificate ready for {hostname}.")

                # Import via SSH (distribute + scalectl)
                if import_ssh:
                    for fname in [f"{hostname}.pem", f"{hostname}.key", "ca.crt"]:
                        src = os.path.join(tls_dir, fname)
                        dst = f"{ssh_user}@{hostname}:{tls_dir}/"
                        cmd = ["scp", src, dst]
                        yield sse("info", f"$ {' '.join(cmd)}")
                        rc = yield from stream_process(cmd)
                        if rc != 0:
                            yield sse("error", f"[ERROR] SCP failed for {fname} to {hostname}.")
                    remote_cmd = (
                        f"mkdir -p {tls_dir} && "
                        f"scalectl node config set "
                        f"--cert {tls_dir}/{hostname}.pem "
                        f"--key {tls_dir}/{hostname}.key "
                        f"--chain {tls_dir}/ca.crt"
                    )
                    cmd = ["ssh", f"{ssh_user}@{hostname}", remote_cmd]
                    yield sse("info", f"$ {' '.join(cmd)}")
                    rc = yield from stream_process(cmd)
                    if rc != 0:
                        yield sse("error", f"[ERROR] scalectl import failed on {hostname}.")
                    else:
                        yield sse("success", f"[OK] Identity imported on {hostname}.")
                else:
                    yield sse("info", f"# Manual import for {hostname}:")
                    yield sse("info", f"#   scp {tls_dir}/{hostname}.pem {tls_dir}/{hostname}.key {tls_dir}/ca.crt {ssh_user}@{hostname}:{tls_dir}/")
                    yield sse("info", f"#   ssh {ssh_user}@{hostname} 'scalectl node config set --cert {tls_dir}/{hostname}.pem --key {tls_dir}/{hostname}.key --chain {tls_dir}/ca.crt'")

            # 5. Add CA cert to local system trust store
            if add_trust:
                trust_path = "/etc/pki/ca-trust/source/anchors/scale-ca.crt"
                cmd = ["cp", ca_crt, trust_path]
                yield sse("info", f"$ {' '.join(cmd)}")
                rc = yield from stream_process(cmd)
                if rc == 0:
                    cmd = ["update-ca-trust"]
                    yield sse("info", f"$ {' '.join(cmd)}")
                    yield from stream_process(cmd)
                    yield sse("success", "[OK] CA added to system trust store.")
                else:
                    yield sse("error", "[ERROR] Could not copy CA to trust store (check permissions).")

            yield sse("success", "[DONE] Node identity setup complete.")
        except Exception as exc:
            yield sse("error", f"[ERROR] {exc}")
        finally:
            yield sse("done", "")

    return sse_response(generate())


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print("IBM Storage Scale Toolkit — backend server")
    print(f"Listening on http://127.0.0.1:{port}  (loopback only)")
    print("Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)
