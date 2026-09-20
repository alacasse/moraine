from pathlib import Path
import threading
import time

import pytest

from moraine_email.adapters.simulated import SimulatedProvider
from tests.fixtures.provider_server import ProviderServer


@pytest.fixture
def grant_body():
    return {
        "agent": "agent:pilot", "account_id": "pilot@example.test", "expires_at": time.time() + 600,
        "recipient": "correspondent@example.test", "reply_to_ref": "message-1",
        "resources": [{"resource_ref": "message-1", "provider_message_id": "upstream-1", "kind": "message",
                       "version": 1, "title": "Question du pilote", "text": "Peux-tu confirmer mardi ?",
                       "from_address": "correspondent@example.test", "reply_address": "correspondent@example.test",
                       "message_id": "<original@example.test>", "thread_id": "thread-1"}],
    }


@pytest.fixture
def oracle(tmp_path):
    server = ProviderServer(tmp_path / "oracle")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


@pytest.fixture
def provider(oracle):
    adapter = SimulatedProvider(oracle.url, oracle.token)
    yield adapter
    adapter.close()


@pytest.fixture
def opa():
    from moraine_email.policy import OPA
    policy = OPA(Path(__file__).resolve().parents[1] / ".tools/opa")
    yield policy
    policy.close()


@pytest.fixture
def broker(tmp_path, opa, provider):
    from moraine_email.broker import Broker
    instance = Broker(tmp_path / "broker", opa, provider)
    yield instance
    instance.close()
