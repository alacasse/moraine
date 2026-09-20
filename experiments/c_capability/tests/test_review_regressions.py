"""Independent-review regressions against real SQLite and the common provider."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import threading
import time

import httpx
import pytest

from actions import Refusal
from conftest import submission
from server import Server


def provider_counts(provider):
    with provider[2].connect() as db:
        return {
            "effects": db.execute("SELECT COUNT(*) FROM effects").fetchone()[0],
            "reads": db.execute("SELECT COUNT(*) FROM reads").fetchone()[0],
        }


@pytest.mark.parametrize("operation", ["approved_order", "automatic_order", "document_read"])
def test_expiry_while_sqlite_reservation_waits_prevents_provider_io(
        executor, provider, grant_data, order, monkeypatch, operation):
    expiry = int(time.time()) + 3
    grant = executor.create_grant("human:alice", {
        **grant_data, "expires_at": expiry,
        "auto_limit_minor": 0 if operation == "approved_order" else 1000,
    })
    action = ({"type": "document.read", "account": "alice", "document_id": "public-note"}
              if operation == "document_read" else order)
    body = submission(grant, action)
    if operation == "approved_order":
        pending = executor.submit("agent:alice", body)
        assert pending["state"] == "pending"
        perform = lambda: executor.approve("human:alice", pending["request_id"],
                                          {"action_digest": pending["action_digest"]})
    else:
        perform = lambda: executor.submit("agent:alice", body)

    # Observe the actual reservation attempt, without replacing its real SQLite IO.
    reservation_started = threading.Event()
    observed_at = []
    original_save = executor.save

    def observe_save(record):
        if record["state"] == "dispatching":
            observed_at.append(time.time())
            reservation_started.set()
        return original_save(record)

    monkeypatch.setattr(executor, "save", observe_save)
    blocker = sqlite3.connect(executor.database, isolation_level=None)
    blocker.execute("BEGIN IMMEDIATE")
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(perform)
        try:
            assert reservation_started.wait(timeout=1.5), "dispatch must reach the real locked write"
            assert observed_at[0] < expiry
            assert not future.done()
            time.sleep(max(0, expiry - time.time() + 0.1))
            assert not future.done(), "SQLite must hold the reservation past expiry"
        finally:
            blocker.execute("COMMIT")
            blocker.close()
        result = future.result(timeout=5)

    assert result["state"] == "denied" and result["reason"] == "capability_denied"
    assert provider_counts(provider) == {"effects": 0, "reads": 0}
    stored = executor.load_request("human:alice", result["request_id"])
    assert stored["state"] == "denied"
    assert executor.submit("agent:alice", body) == result
    with pytest.raises(Refusal, match="not_pending"):
        executor.approve("human:alice", result["request_id"], {"action_digest": result["action_digest"]})
    assert executor.load_request("human:alice", result["request_id"])["execution_id"] == stored["execution_id"]
    assert provider_counts(provider) == {"effects": 0, "reads": 0}


def test_delayed_first_attachment_does_not_start_second_read_after_expiry(
        executor, provider, grant_data, email):
    server = provider[2]
    server.document_started_at = []
    expiry = int(time.time()) + 2

    class DelayFirstDocumentResponse(server.RequestHandlerClass):
        def do_GET(self):
            if self.path.startswith("/documents/"):
                self.server.document_started_at.append(time.time())
            super().do_GET()

        def reply(self, status, payload):
            if self.path.startswith("/documents/") and len(self.server.document_started_at) == 1:
                # The unchanged common provider has already recorded the authorized read.
                time.sleep(max(0, expiry - time.time() + 0.1))
            super().reply(status, payload)

    server.RequestHandlerClass = DelayFirstDocumentResponse
    grant = executor.create_grant("human:alice", {**grant_data, "expires_at": expiry})
    body = submission(grant, {**email, "attachments": email["attachments"] * 2})
    result = executor.submit("agent:alice", body)
    assert result["state"] == "denied" and result["reason"] == "capability_denied"
    assert len(server.document_started_at) == 1
    assert server.document_started_at[0] < expiry
    assert provider_counts(provider) == {"effects": 0, "reads": 1}
    assert executor.submit("agent:alice", body) == result
    assert provider_counts(provider) == {"effects": 0, "reads": 1}


@pytest.mark.parametrize("subject", ["\ud800", "\udfff"])
def test_surrogate_json_subject_returns_400_without_provider_access(
        executor, provider, grant_data, email, subject):
    server = Server(0, executor, {"agent:alice": "alice-token", "agent:bob": "bob-token",
                                 "human:alice": "human-token"})
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        grant = executor.create_grant("human:alice", grant_data)
        body = submission(grant, {**email, "subject": subject})
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False,
                          headers={"Authorization": "Bearer alice-token"}) as client:
            # Escaped surrogate is valid JSON syntax and reaches server-side string validation.
            response = client.post("/requests", content=json.dumps(body).encode("ascii"))
            assert response.status_code == 400
            assert response.json()["error"] == "invalid_string"
            assert client.get("/health").status_code == 200
        assert provider_counts(provider) == {"effects": 0, "reads": 0}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
