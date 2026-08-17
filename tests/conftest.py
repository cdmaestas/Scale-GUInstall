"""
scale-server.py has a hyphen in its filename, so it isn't a normal
importable module — load it by path instead. Session-scoped since import
runs Flask app/route setup at module level (no server actually starts;
that's gated behind `if __name__ == "__main__":`).
"""
import importlib.util
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SERVER_PATH = os.path.join(_ROOT, "scale-server.py")


@pytest.fixture(scope="session")
def ss():
    spec = importlib.util.spec_from_file_location("scale_server", _SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
