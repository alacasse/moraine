from __future__ import annotations

import importlib.util
from pathlib import Path
import threading
import time
import uuid

import pytest

from executor import Executor


@pytest.fixture
def grant_data():
    return {"agent": "agent:alice", "account": "alice", "expires_at": int(time.time()) + 600,
            "recipients": ["trusted@example.test"], "document_ids": ["public-note"],
            "merchants": ["shop.test"], "currency": "CAD", "auto_limit_minor": 1000,
            "hard_limit_minor": 5000}


@pytest.fixture
def order():
    return {"type": "order.create", "account": "alice", "merchant": "shop.test", "sku": "paper",
            "quantity": 1, "amount_minor": 500, "currency": "CAD", "shipping_address_id": "home",
            "recurring": False}


@pytest.fixture
def email():
    return {"type": "email.send", "account": "alice", "to": ["trusted@example.test"], "cc": [],
            "bcc": [], "subject": "Review exact bytes", "body": "Original message",
            "attachments": [{"id": "public-note", "version": 1}]}


@pytest.fixture
def provider(tmp_path):
    path = Path(__file__).resolve().parents[2] / "common" / "provider.py"
    spec = importlib.util.spec_from_file_location("capability_test_provider", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = module.Provider(0, tmp_path / "provider", "synthetic-provider")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", "synthetic-provider", server
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.fixture
def executor(tmp_path, provider):
    obj = Executor(tmp_path / "executor", provider[0], provider[1])
    yield obj
    obj.close()


def submission(grant, action, **extra):
    return {**grant, "action": action, "idempotency_key": uuid.uuid4().hex, **extra}
