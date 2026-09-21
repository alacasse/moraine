"""Access decisions against real SQLite, OPA and a separately observed HTTP provider."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from moraine_email.broker import Broker
from moraine_email.models import PilotError
from moraine_email.policy import PolicyFailure

CATALOGUE = {"travaux-demo": ["upstream-1", "upstream-2"], "other-demo": ["upstream-private"]}
AGENT, HUMAN = "agent:pilot", "human:owner"


@pytest.fixture
def access(tmp_path, opa, provider):
    broker = Broker(tmp_path / "access", opa, provider, resource_sets=CATALOGUE)
    yield broker
    broker.close()


def request(broker, key="first", ref="travaux-demo"):
    return broker.request_access(AGENT, ref, key)


def decide(broker, rid, choice="approve"):
    view = broker.review_access(HUMAN, rid)
    return broker.decide_access(HUMAN, rid, view["scope_digest"], view["nonce"], choice)


def assert_empty(broker):
    assert broker.db.execute("SELECT count(*) FROM grants").fetchone()[0] == 0
    assert broker.db.execute("SELECT count(*) FROM resources").fetchone()[0] == 0


def test_pending_idempotence_conflict_and_restart(access, oracle, opa, provider):
    assert access.get_access(AGENT, "travaux-demo")["decision"] == "absent"
    first = request(access)
    assert first["decision"] == "pending"
    assert "grant_id" not in first
    assert request(access) == first
    with pytest.raises(PilotError, match="idempotency_conflict"):
        request(access, ref="other-demo")
    with pytest.raises(PilotError, match="access_already_exists"):
        request(access, key="second")
    assert_empty(access)
    assert oracle.records("reads") == []
    state = access.directory
    access.close()
    # Keep fixture cleanup valid while reopening the same persistent state.
    access.__init__(state, opa, provider, resource_sets=CATALOGUE)
    assert access.get_access(AGENT, "travaux-demo") == first
    assert request(access) == first
    assert decide(access, first["request_id"], "reject")["decision"] == "rejected"
    assert request(access)["decision"] == "rejected"
    # The rejected conflicting key was not accepted/consumed. A new explicit call may now create a request.
    second = request(access, key="second")
    assert second["request_id"] != first["request_id"]
    assert second["decision"] == "pending"
    assert oracle.records("reads") == []


def test_closed_capture_then_read_only_and_revocation(access, oracle):
    pending = request(access)
    view = access.review_access(HUMAN, pending["request_id"])
    access.resource_sets["travaux-demo"] = ["upstream-private"]
    ready = access.decide_access(HUMAN, pending["request_id"], view["scope_digest"], view["nonce"], "approve")
    assert ready["decision"] == "approved" and ready["retrieval"] == "ready"
    assert access.get_access(AGENT, "travaux-demo") == ready
    assert access.decide_access(HUMAN, pending["request_id"], view["scope_digest"], view["nonce"], "approve") == ready
    assert len(oracle.records("reads")) == 1
    observed = oracle.records("reads")[0]
    assert observed["message_ids"] == ["upstream-1", "upstream-2"]
    gid = ready["grant_id"]
    resources = access.list_context(AGENT, gid)["resources"]
    assert {r["provider_message_id"] for r in resources} == set(observed["message_ids"])
    for item in resources:
        assert item["source_digest"] == observed["source_digests"][item["provider_message_id"]]
        read = access.read_context(AGENT, gid, item["resource_ref"], item["version"])
        assert read["text"] == oracle.messages[item["provider_message_id"]]["text"]
        assert read["digest"] == item["digest"]
    for actor, ref, version in [("agent:foreign", resources[0]["resource_ref"], 1),
                                (AGENT, "upstream-private", 1), (AGENT, resources[0]["resource_ref"], 2)]:
        with pytest.raises(PilotError, match="scope_denied"):
            access.read_context(actor, gid, ref, version)
    with pytest.raises(PilotError, match="scope_denied"):
        access.propose_reply(AGENT, {"grant_id": gid, "idempotency_key": "send", "reply_to_ref": resources[0]["resource_ref"],
                                    "body_text": "Do not send"})
    assert access.db.execute("SELECT count(*) FROM requests").fetchone()[0] == 0
    assert oracle.records("attempts") == []
    access.revoke_grant(HUMAN, gid)
    receipt = access.get_access(AGENT, "travaux-demo")
    assert receipt["retrieval"] == "ready" and receipt["access"] == "revoked" and "grant_id" not in receipt
    with pytest.raises(PilotError, match="scope_denied"):
        access.list_context(AGENT, gid)


@pytest.mark.parametrize("mode", ["slow_fetch", "disconnect_fetch", "invalid_fetch", "extra_fetch",
                                  "duplicate_fetch", "missing_fetch", "oversized_fetch"])
def test_failed_capture_never_publishes_or_retries(access, oracle, mode):
    oracle.mode = mode
    pending = request(access)
    result = decide(access, pending["request_id"])
    assert result["decision"] == "approved" and result["retrieval"] == "failed"
    assert result["reason"] == "retrieval_failed"
    assert_empty(access)
    assert access.get_access(AGENT, "travaux-demo") == result
    assert request(access) == result
    assert len(oracle.records("reads")) == 1


def test_bad_actor_digest_nonce_or_old_review_do_not_capture(access, oracle):
    pending = request(access)
    rid = pending["request_id"]
    view = access.review_access(HUMAN, rid)
    for actor, sha, nonce in [(AGENT, view["scope_digest"], view["nonce"]),
                              (HUMAN, "0" * 64, view["nonce"]), (HUMAN, view["scope_digest"], "forged")]:
        with pytest.raises(PilotError):
            access.decide_access(actor, rid, sha, nonce, "approve")
    access.review_access(HUMAN, rid)
    with pytest.raises(PilotError, match="invalid_review"):
        access.decide_access(HUMAN, rid, view["scope_digest"], view["nonce"], "approve")
    with pytest.raises(PilotError):
        access.get_access("agent:foreign", "travaux-demo")
    assert_empty(access)
    assert oracle.records("reads") == []


def test_expiry_before_approval(access, oracle, monkeypatch):
    pending = request(access)
    view = access.review_access(HUMAN, pending["request_id"])
    monkeypatch.setattr(access, "now", lambda: view["scope"]["request_expires_at"] + 1)
    result = access.decide_access(HUMAN, pending["request_id"], view["scope_digest"], view["nonce"], "approve")
    assert result["decision"] == "expired"
    assert_empty(access)
    assert oracle.records("reads") == []


def test_expiry_during_http_capture_keeps_approval_without_publication(access, oracle, monkeypatch):
    pending = request(access)
    view = access.review_access(HUMAN, pending["request_id"])
    original = access.provider.fetch_selected

    def late(ids):
        data = original(ids)
        monkeypatch.setattr(access, "now", lambda: view["review_expires_at"] + 1)
        return data

    monkeypatch.setattr(access.provider, "fetch_selected", late)
    result = access.decide_access(HUMAN, pending["request_id"], view["scope_digest"], view["nonce"], "approve")
    assert (result["decision"], result["retrieval"], result["reason"]) == ("approved", "failed", "activation_expired")
    assert_empty(access)
    assert len(oracle.records("reads")) == 1
    assert access.get_access(AGENT, "travaux-demo") == result


def test_interrupted_capture_recovers_without_retry(access, oracle, opa, provider, monkeypatch):
    pending = request(access)

    def interrupt(ids):
        raise KeyboardInterrupt()

    monkeypatch.setattr(provider, "fetch_selected", interrupt)
    with pytest.raises(KeyboardInterrupt):
        decide(access, pending["request_id"])
    state = access.directory
    access.close()
    access.__init__(state, opa, provider, resource_sets=CATALOGUE)
    receipt = access.get_access(AGENT, "travaux-demo")
    assert (receipt["decision"], receipt["retrieval"], receipt["reason"]) == ("approved", "failed", "retrieval_interrupted")
    assert_empty(access)
    assert oracle.records("reads") == []


def test_old_database_is_rejected_without_migration(tmp_path, opa, provider):
    state = tmp_path / "old"
    state.mkdir()
    with sqlite3.connect(state / "broker.sqlite3") as db:
        db.execute("PRAGMA user_version=1")
    with pytest.raises(PilotError, match="storage_version"):
        Broker(state, opa, provider, resource_sets=CATALOGUE)
    with sqlite3.connect(state / "broker.sqlite3") as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1


def test_publication_failure_rolls_back_all_resources(access, oracle):
    access.db.execute("CREATE TRIGGER fail_publication BEFORE UPDATE OF grant_id ON access_requests "
                      "WHEN NEW.grant_id IS NOT NULL BEGIN SELECT RAISE(ABORT, 'simulated failure'); END")
    result = decide(access, request(access)["request_id"])
    assert result["retrieval"] == "failed"
    assert_empty(access)
    assert len(oracle.records("reads")) == 1


def test_concurrent_retry_records_one_request(access, oracle):
    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(lambda _: request(access), range(4)))
    assert all(r == results[0] for r in results)
    assert access.db.execute("SELECT count(*) FROM access_requests").fetchone()[0] == 1
    assert oracle.records("reads") == []


def test_policy_failure_prevents_capture(access, oracle, monkeypatch):
    pending = request(access)

    def unavailable(_):
        raise PolicyFailure()

    monkeypatch.setattr(access.policy, "decide", unavailable)
    result = decide(access, pending["request_id"])
    assert result["decision"] == "approved" and result["retrieval"] == "failed"
    assert_empty(access)
    assert oracle.records("reads") == []


def test_expired_grant_is_not_reactivated_by_lookup(access, oracle, monkeypatch):
    active = decide(access, request(access)["request_id"])
    resource = access.list_context(AGENT, active["grant_id"])["resources"][0]
    monkeypatch.setattr(access, "now", lambda: active["expires_at"] + 1)
    receipt = access.get_access(AGENT, "travaux-demo")
    assert receipt["access"] == "expired" and "grant_id" not in receipt
    assert receipt["decision"] == "approved" and receipt["retrieval"] == "ready"
    with pytest.raises(PilotError, match="scope_denied"):
        access.read_context(AGENT, active["grant_id"], resource["resource_ref"], 1)
    assert request(access) == receipt
    assert len(oracle.records("reads")) == 1


def test_expiry_while_publishing_rolls_back_capture(access, oracle, monkeypatch):
    pending = request(access)
    view = access.review_access(HUMAN, pending["request_id"])
    original = access._insert_grant

    def delayed(*args, **kwargs):
        gid = original(*args, **kwargs)
        monkeypatch.setattr(access, "now", lambda: view["review_expires_at"] + 1)
        return gid

    monkeypatch.setattr(access, "_insert_grant", delayed)
    result = access.decide_access(HUMAN, pending["request_id"], view["scope_digest"], view["nonce"], "approve")
    assert result["reason"] == "activation_expired" and result["retrieval"] == "failed"
    assert_empty(access)
    assert len(oracle.records("reads")) == 1
