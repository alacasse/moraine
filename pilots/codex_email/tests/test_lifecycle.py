"""Behavioral lifecycle tests against real OPA, persistent SQLite and an IO oracle."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import sqlite3
import threading
import time

import pytest

from moraine_email.broker import Broker
from moraine_email.models import PilotError
from moraine_email.policy import OPA


class Oracle:
    """Independent no-deduplication IO oracle: every invocation is an attempt."""
    def __init__(self):
        self.attempts = []
        self.effects = []
        self.mode = "accept"

    def send_prepared(self, prepared, execution_id):
        self.attempts.append((deepcopy(prepared), execution_id))
        if self.mode == "reject":
            return {"state": "failed", "reason": "provider_rejected", "result": {}}
        self.effects.append(deepcopy(prepared))
        if self.mode == "disconnect":
            raise ConnectionError("synthetic accepted then disconnected")
        return {"state": "accepted", "reason": "provider_accepted", "result": {"receipt": len(self.effects)}}


@pytest.fixture
def core(tmp_path):
    policy = OPA(Path(__file__).parents[1] / ".tools" / "opa")
    oracle = Oracle()
    broker = Broker(tmp_path / "state", policy, oracle)
    yield broker, oracle, policy
    broker.close()
    policy.close()


def grant_body():
    return {"agent": "agent:pilot", "account_id": "pilot@example.test",
            "expires_at": time.time() + 1200, "recipient": "friend@example.test",
            "reply_to_ref": "message-1", "resources": [{"resource_ref": "message-1",
            "provider_message_id": "provider-1", "kind": "message", "version": 1,
            "title": "Bonjour", "text": "Protected original", "from_address": "friend@example.test",
            "reply_address": "friend@example.test", "message_id": "<original@example.test>", "thread_id": "thread-1"}]}


def proposal(broker, *, key="one", gid=None):
    gid = gid or broker.create_grant("human:owner", grant_body())["grant_id"]
    body = {"grant_id": gid, "idempotency_key": key, "reply_to_ref": "message-1", "body_text": "Approved body"}
    return broker.propose_reply("agent:pilot", body), body


def approve(broker, request_id, decision="approve"):
    review = broker.review("human:owner", request_id)
    return broker.decide_review("human:owner", request_id, review["action_digest"], review["nonce"], decision)


def test_selection_immutable_and_denied_reads_do_not_touch_text(core):
    broker, oracle, _ = core
    body = grant_body()
    gid = broker.create_grant("human:owner", body)["grant_id"]
    body["resources"][0]["text"] = "Changed outside broker"
    assert broker.read_context("agent:pilot", gid, "message-1", 1)["text"] == "Protected original"
    statements = []
    broker.db.set_trace_callback(statements.append)
    for agent, ref, version in [("agent:foreign", "message-1", 1), ("agent:pilot", "absent", 1),
                                ("agent:pilot", "message-1", 2)]:
        with pytest.raises(PilotError):
            broker.read_context(agent, gid, ref, version)
    assert not any("SELECT text" in sql for sql in statements)
    assert oracle.attempts == []


def test_human_approval_exact_bytes_and_idempotence(core):
    broker, oracle, _ = core
    pending, body = proposal(broker)
    assert pending["state"] == "pending" and oracle.attempts == []
    review = broker.review("human:owner", pending["request_id"])
    accepted = broker.decide_review("human:owner", pending["request_id"], review["action_digest"], review["nonce"], "approve")
    assert accepted["state"] == "accepted"
    assert oracle.effects == [review["snapshot"]["prepared_reply"]]
    assert broker.propose_reply("agent:pilot", body)["state"] == "accepted"
    broker.decide_review("human:owner", pending["request_id"], review["action_digest"], review["nonce"], "approve")
    assert len(oracle.attempts) == 1
    body["body_text"] = "Substituted"
    with pytest.raises(PilotError, match="idempotency_conflict"):
        broker.propose_reply("agent:pilot", body)


def test_refusal_and_foreign_request(core):
    broker, oracle, _ = core
    request, _ = proposal(broker)
    for rid in (request["request_id"], "absent"):
        with pytest.raises(PilotError, match="not_found"):
            broker.get_request("agent:foreign", rid)
    assert approve(broker, request["request_id"], "reject")["state"] == "rejected"
    assert oracle.attempts == []


def test_nonce_digest_and_human_are_required(core):
    broker, oracle, _ = core
    request, _ = proposal(broker)
    first = broker.review("human:owner", request["request_id"])
    second = broker.review("human:owner", request["request_id"])
    for actor, fingerprint, nonce in [("agent:pilot", second["action_digest"], second["nonce"]),
                                       ("human:owner", "wrong", second["nonce"]),
                                       ("human:owner", first["action_digest"], first["nonce"])]:
        with pytest.raises(PilotError):
            broker.decide_review(actor, request["request_id"], fingerprint, nonce, "approve")
    assert oracle.attempts == []
    assert broker.decide_review("human:owner", request["request_id"], second["action_digest"], second["nonce"], "approve")["state"] == "accepted"


def test_revocation_masks_pending_and_terminal_without_protected_read(core):
    broker, oracle, _ = core
    accepted, body = proposal(broker)
    approve(broker, accepted["request_id"])
    pending, _ = proposal(broker, key="two", gid=body["grant_id"])
    broker.revoke_grant("human:owner", body["grant_id"])
    statements = []
    broker.db.set_trace_callback(statements.append)
    for request in (accepted, pending):
        assert set(broker.get_request("agent:pilot", request["request_id"])) == {"request_id", "state", "reason"}
    assert broker.get_request("agent:pilot", accepted["request_id"])["state"] == "accepted"
    assert not any("SELECT snapshot" in sql or "SELECT text" in sql for sql in statements)
    assert len(oracle.attempts) == 1


def test_unknown_blocks_new_grants_and_preexisting_requests_until_human_resolution(core):
    broker, oracle, _ = core
    a, body = proposal(broker)
    b, _ = proposal(broker, key="two", gid=body["grant_id"])
    oracle.mode = "disconnect"
    assert approve(broker, a["request_id"])["state"] == "unknown"
    with pytest.raises(PilotError, match="source_unresolved"):
        approve(broker, b["request_id"])
    with pytest.raises(PilotError, match="source_unresolved"):
        proposal(broker, key="new-grant")
    with pytest.raises(PilotError):
        broker.resolve_unknown("human:owner", a["request_id"], False)
    broker.resolve_unknown("human:owner", a["request_id"], True)
    assert broker.get_request("agent:pilot", a["request_id"])["state"] == "unknown"
    oracle.mode = "accept"
    assert approve(broker, b["request_id"])["state"] == "accepted"
    assert len(oracle.attempts) == 2


def test_restart_preserves_results_and_unknown_barrier(core):
    broker, oracle, policy = core
    a, body = proposal(broker)
    oracle.mode = "disconnect"
    approve(broker, a["request_id"])
    broker.close()
    recovered = Broker(broker.directory, policy, oracle)
    # Keep fixture ownership on the live handles.
    broker.db, broker.filelock = recovered.db, recovered.filelock
    assert broker.propose_reply("agent:pilot", body)["state"] == "unknown"
    with pytest.raises(PilotError, match="source_unresolved"):
        proposal(broker, key="new")
    assert len(oracle.attempts) == 1


def test_unfinished_durable_intent_recovers_unknown_without_retry(core):
    broker, oracle, policy = core
    a, _ = proposal(broker)
    with broker.transaction():
        broker.db.execute("UPDATE requests SET state='processing' WHERE id=?", (a["request_id"],))
        broker.db.execute("INSERT INTO executions(id,request_id,account,source_id,state) VALUES('crash',?,?,?,'intent')",
                          (a["request_id"], broker.account, "provider-1"))
    broker.close()
    recovered = Broker(broker.directory, policy, oracle)
    broker.db, broker.filelock = recovered.db, recovered.filelock
    assert broker.get_request("agent:pilot", a["request_id"])["state"] == "unknown"
    with pytest.raises(PilotError, match="source_unresolved"):
        proposal(broker, key="new")
    assert oracle.attempts == []


def test_double_click_and_concurrent_refusal_are_single_decision(core):
    broker, oracle, _ = core
    a, _ = proposal(broker)
    review = broker.review("human:owner", a["request_id"])
    def decide(decision):
        return broker.decide_review("human:owner", a["request_id"], review["action_digest"], review["nonce"], decision)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(decide, ["approve", "reject", "approve"]))
    assert len({r["state"] for r in results}) == 1
    assert len(oracle.attempts) <= 1


def test_policy_unavailable_fails_closed(core):
    broker, oracle, policy = core
    a, _ = proposal(broker)
    review = broker.review("human:owner", a["request_id"])
    policy.process.terminate()
    policy.process.wait(timeout=3)
    with pytest.raises(PilotError, match="policy_unavailable"):
        broker.decide_review("human:owner", a["request_id"], review["action_digest"], review["nonce"], "approve")
    assert oracle.attempts == []


def test_expiry_while_waiting_for_sqlite_write_prevents_send(core):
    broker, oracle, _ = core
    body = grant_body()
    body["expires_at"] = time.time() + 0.6
    gid = broker.create_grant("human:owner", body)["grant_id"]
    a, _ = proposal(broker, gid=gid)
    review = broker.review("human:owner", a["request_id"])
    other = sqlite3.connect(broker.directory / "broker.sqlite3", isolation_level=None)
    other.execute("BEGIN IMMEDIATE")
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(broker.decide_review, "human:owner", a["request_id"], review["action_digest"], review["nonce"], "approve")
        time.sleep(0.75)
        other.execute("ROLLBACK")
        with pytest.raises(PilotError):
            future.result(timeout=3)
    other.close()
    assert oracle.attempts == []


def test_expiry_during_policy_call_does_not_release_protected_text(core, monkeypatch):
    broker, oracle, policy = core
    body = grant_body()
    body["expires_at"] = time.time() + 0.25
    gid = broker.create_grant("human:owner", body)["grant_id"]
    real_decide = policy.decide
    def delayed(facts):
        result = real_decide(facts)
        time.sleep(0.3)
        return result
    monkeypatch.setattr(policy, "decide", delayed)
    statements = []
    broker.db.set_trace_callback(statements.append)
    with pytest.raises(PilotError):
        broker.read_context("agent:pilot", gid, "message-1", 1)
    assert not any("SELECT text" in sql for sql in statements)
    assert oracle.attempts == []


def test_configured_identity_and_account_replace_experimental_names(tmp_path):
    policy = OPA(Path(__file__).parents[1] / ".tools" / "opa")
    oracle = Oracle()
    broker = Broker(tmp_path, policy, oracle, owner="human:other", agent="agent:other", account="other@example.test")
    try:
        body = grant_body()
        body.update(agent="agent:other", account_id="other@example.test")
        gid = broker.create_grant("human:other", body)["grant_id"]
        assert broker.read_context("agent:other", gid, "message-1", 1)["text"] == "Protected original"
        with pytest.raises(PilotError):
            broker.create_grant("human:owner", body)
    finally:
        broker.close()
        policy.close()


def test_result_commit_failure_preserves_intent_and_returns_unknown(core):
    broker, oracle, policy = core
    a, body = proposal(broker)
    broker.db.execute("""CREATE TRIGGER fail_result BEFORE UPDATE OF result ON requests
        BEGIN SELECT RAISE(ABORT, 'synthetic storage failure'); END""")
    outcome = approve(broker, a["request_id"])
    assert outcome["state"] == "unknown"
    assert broker.get_request("agent:pilot", a["request_id"])["state"] == "unknown"
    assert len(oracle.effects) == 1
    assert broker.db.execute("SELECT state FROM executions").fetchone()[0] == "intent"
    assert broker.suspended
    broker.db.execute("DROP TRIGGER fail_result")
    broker.close()
    recovered = Broker(broker.directory, policy, oracle)
    broker.db, broker.filelock = recovered.db, recovered.filelock
    broker.suspended = False
    assert broker.propose_reply("agent:pilot", body)["state"] == "unknown"
    with pytest.raises(PilotError, match="source_unresolved"):
        proposal(broker, key="new-after-crash")
    assert len(oracle.attempts) == 1


def test_post_intent_policy_delay_rechecks_expiration_before_io(core, monkeypatch):
    broker, oracle, policy = core
    body = grant_body()
    body["expires_at"] = time.time() + 0.4
    gid = broker.create_grant("human:owner", body)["grant_id"]
    a, _ = proposal(broker, gid=gid)
    real_decide = policy.decide
    def delay_only_after_durable_intent(facts):
        result = real_decide(facts)
        if broker.db.execute("SELECT 1 FROM executions").fetchone():
            time.sleep(0.5)
        return result
    monkeypatch.setattr(policy, "decide", delay_only_after_durable_intent)
    assert approve(broker, a["request_id"])["state"] == "denied"
    assert oracle.attempts == []
    assert broker.db.execute("SELECT state FROM executions").fetchone()[0] == "denied"


def test_policy_outage_masks_existing_preview_and_decisions_are_durable(core):
    broker, oracle, policy = core
    a, body = proposal(broker)
    rejected, _ = proposal(broker, key="refusal", gid=body["grant_id"])
    approve(broker, rejected["request_id"], "reject")
    decision = broker.db.execute("SELECT * FROM decisions").fetchone()
    assert decision["human"] == "human:owner" and decision["decision"] == "reject"
    assert decision["action_digest"] == rejected["action_digest"]
    policy.process.terminate()
    policy.process.wait(timeout=3)
    statements = []
    broker.db.set_trace_callback(statements.append)
    assert set(broker.get_request("agent:pilot", a["request_id"])) == {"request_id", "state", "reason"}
    assert set(broker.propose_reply("agent:pilot", body)) == {"request_id", "state", "reason"}
    assert not any("SELECT snapshot" in sql for sql in statements)
    assert oracle.attempts == []


def test_pending_expiry_is_terminal_but_accepted_outcome_is_immutable(core):
    broker, oracle, _ = core
    body = grant_body()
    body["expires_at"] = time.time() + 0.4
    gid = broker.create_grant("human:owner", body)["grant_id"]
    a, _ = proposal(broker, gid=gid)
    b, _ = proposal(broker, key="second", gid=gid)
    approve(broker, a["request_id"])
    time.sleep(0.5)
    assert broker.get_request("agent:pilot", a["request_id"])["state"] == "accepted"
    assert broker.get_request("agent:pilot", b["request_id"])["state"] == "denied"
    assert len(oracle.attempts) == 1


def test_revocation_linearizes_after_in_flight_dispatch_and_blocks_next(core, monkeypatch):
    broker, oracle, _ = core
    a, body = proposal(broker)
    b, _ = proposal(broker, key="next", gid=body["grant_id"])
    in_provider, release_provider, revoke_started = threading.Event(), threading.Event(), threading.Event()
    real_send = oracle.send_prepared
    def blocked_send(prepared, execution_id):
        in_provider.set()
        assert release_provider.wait(3)
        return real_send(prepared, execution_id)
    monkeypatch.setattr(oracle, "send_prepared", blocked_send)
    def revoke():
        revoke_started.set()
        return broker.revoke_grant("human:owner", body["grant_id"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        dispatch = pool.submit(approve, broker, a["request_id"])
        assert in_provider.wait(3)
        revocation = pool.submit(revoke)
        assert revoke_started.wait(3)
        assert not revocation.done()
        release_provider.set()
        assert dispatch.result(timeout=3)["state"] == "accepted"
        assert revocation.result(timeout=3)["state"] == "revoked"
    assert broker.get_request("agent:pilot", b["request_id"])["state"] == "denied"
    assert len(oracle.attempts) == 1


def test_expiry_during_protected_read_hides_result_and_blocks_next_read(core):
    broker, oracle, _ = core
    body = grant_body()
    body["expires_at"] = time.time() + 0.25
    gid = broker.create_grant("human:owner", body)["grant_id"]
    reads = []
    def trace(sql):
        if "SELECT text" in sql:
            reads.append(sql)
            time.sleep(0.3)
    broker.db.set_trace_callback(trace)
    for _ in range(2):
        with pytest.raises(PilotError):
            broker.read_context("agent:pilot", gid, "message-1", 1)
    assert len(reads) == 1
    assert oracle.attempts == []


def test_only_one_broker_can_own_state(core):
    broker, oracle, policy = core
    with pytest.raises(BlockingIOError):
        Broker(broker.directory, policy, oracle)
