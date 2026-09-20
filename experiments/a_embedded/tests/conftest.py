"""Real loopback downstream fixture, isolated state per test."""
import importlib.util
from pathlib import Path
import sys
import threading

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("synthetic_provider", HERE.parent / "common/provider.py")
fixture_provider = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_provider)


@pytest.fixture
def provider_service(tmp_path):
    server = fixture_provider.Provider(0, tmp_path / "downstream", "synthetic-provider-secret")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", server.token
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
