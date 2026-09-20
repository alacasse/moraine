from __future__ import annotations

import json
import time

from biscuit_auth import BlockBuilder
import httpx
import pytest

from actions import Refusal
from capabilities import attenuate, authorize, verify
from conftest import submission
from executor import Executor, REVIEW_MAX_AGE


def effects(provider):
    with provider[2].connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM effects")]


def reads(provider):
    with provider[2].connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM reads")]


def test_revocation_is_online_state_not_offline_crypto(executor, grant_data, order, provider):
    grant = executor.create_grant("human:alice", grant_data)
    child = attenuate(grant["capability"], executor.pair.public_key, maximum=500)
    token = verify(child, executor.pair.public_key)
    executor.revoke("human:alice", grant["grant_id"], {})
    # An offline verifier with unchanged time/public key still accepts cryptographic authority.
    assert authorize(token, grant_id=grant["grant_id"], actor="agent:alice", action=order) == "auto"
    online = executor.submit("agent:alice", submission({**grant, "capability": child}, order))
    assert online["state"] == "denied" and online["reason"] == "grant_revoked"
    assert effects(provider) == []


def test_child_executes_narrow_action_and_parent_still_has_broader_rights(executor, grant_data, order, provider):
    grant = executor.create_grant("human:alice", grant_data)
    child = {**grant, "capability": attenuate(grant["capability"], executor.pair.public_key, maximum=500)}
    allowed = executor.submit("agent:alice", submission(child, order))
    denied = executor.submit("agent:alice", submission(child, {**order, "amount_minor": 501}))
    broader = executor.submit("agent:alice", submission(grant, {**order, "amount_minor": 501}))
    assert [r["state"] for r in (allowed, denied, broader)] == ["executed", "denied", "executed"]
    assert len(effects(provider)) == 2


def test_capability_change_with_same_idempotency_key_conflicts(executor, grant_data, order, provider):
    grant = executor.create_grant("human:alice", grant_data)
    body = submission(grant, order)
    assert executor.submit("agent:alice", body)["state"] == "executed"
    child = attenuate(grant["capability"], executor.pair.public_key, maximum=500)
    with pytest.raises(Refusal, match="idempotency_conflict"):
        executor.submit("agent:alice", {**body, "capability": child})
    assert len(effects(provider)) == 1


def test_foreign_signed_grant_cannot_be_rebound(executor, grant_data, order, provider):
    first = executor.create_grant("human:alice", grant_data)
    second = executor.create_grant("human:alice", grant_data)
    response = executor.submit("agent:alice", submission({**first, "capability": second["capability"]}, order))
    assert response["state"] == "denied" and response["reason"] == "grant_binding"
    assert effects(provider) == []


def test_forged_descendant_document_fact_stops_before_provider(executor, grant_data, provider):
    grant = executor.create_grant("human:alice", grant_data)
    token = verify(grant["capability"], executor.pair.public_key)
    attack = token.append(BlockBuilder('cap:document("tax-return");')).to_base64()
    response = executor.submit("agent:alice", submission({**grant, "capability": attack},
                               {"type": "document.read", "account": "alice", "document_id": "tax-return"}))
    assert response["state"] == "denied"
    assert reads(provider) == []


def test_pending_attenuation_rechecked_at_approval(executor, grant_data, order, provider):
    grant = executor.create_grant("human:alice", {**grant_data, "auto_limit_minor": 0})
    token = verify(grant["capability"], executor.pair.public_key)
    deadline = int(time.time()) + 2
    child = token.append(BlockBuilder("check if req:time($t), $t < {end};", {"end": deadline})).to_base64()
    request = executor.submit("agent:alice", submission({**grant, "capability": child}, order))
    assert request["state"] == "pending"
    time.sleep(max(0, deadline - time.time() + 0.05))
    result = executor.approve("human:alice", request["request_id"], {"action_digest": request["action_digest"]})
    assert result["state"] == "denied" and result["reason"] == "capability_denied"
    assert effects(provider) == []


def test_review_deadline_and_separate_snapshot_digest(executor, grant_data, email, provider):
    grant = executor.create_grant("human:alice", grant_data)
    request = executor.submit("agent:alice", submission(grant, email))
    record = executor.load_request("human:alice", request["request_id"])
    assert record["review_deadline"] - record["submitted_at"] == REVIEW_MAX_AGE == 300
    assert record["input_digest"] != record["action_digest"]
    # Exercise persisted age, without a five-minute sleep or an agent-controlled clock.
    record["review_deadline"] = time.time() - 1
    executor.save(record)
    result = executor.approve("human:alice", request["request_id"], {"action_digest": request["action_digest"]})
    assert result["state"] == "denied" and result["reason"] == "review_expired"
    assert effects(provider) == []


def test_startup_lock_refuses_second_executor(executor, provider):
    with pytest.raises(RuntimeError, match="already has an executor"):
        Executor(executor.database.parent, provider[0], provider[1])


def test_restart_retains_key_pending_snapshot_and_revocation(tmp_path, provider, grant_data, email, order):
    path = tmp_path / "durable"
    first = Executor(path, provider[0], provider[1])
    grant = first.create_grant("human:alice", grant_data)
    revoked = first.create_grant("human:alice", grant_data)
    request = first.submit("agent:alice", submission(grant, email))
    public_key = repr(first.pair.public_key)
    first.revoke("human:alice", revoked["grant_id"], {})
    first.close()
    second = Executor(path, provider[0], provider[1])
    try:
        assert repr(second.pair.public_key) == public_key
        assert (path / "issuer.key").stat().st_mode & 0o077 == 0
        assert second.get("agent:alice", request["request_id"])["snapshot"] == request["snapshot"]
        assert second.approve("human:alice", request["request_id"],
                              {"action_digest": request["action_digest"]})["state"] == "executed"
        assert second.submit("agent:alice", submission(revoked, order))["reason"] == "grant_revoked"
        assert len(effects(provider)) == 1
    finally:
        second.close()


def test_unfinished_dispatch_restarts_unknown_without_retry(tmp_path, provider, grant_data, order):
    path = tmp_path / "interrupted"
    first = Executor(path, provider[0], provider[1])
    grant = first.create_grant("human:alice", {**grant_data, "auto_limit_minor": 0})
    body = submission(grant, order)
    request = first.submit("agent:alice", body)
    record = first.load_request("human:alice", request["request_id"])
    record.update(state="dispatching", reason="dispatch_reserved")
    first.save(record)
    first.close()
    second = Executor(path, provider[0], provider[1])
    try:
        result = second.submit("agent:alice", body)
        assert result["state"] == "unknown" and result["reason"] == "interrupted_dispatch"
        assert second.load_request("human:alice", result["request_id"])["execution_id"] == record["execution_id"]
        with pytest.raises(Refusal, match="not_pending"):
            second.approve("human:alice", request["request_id"], {"action_digest": request["action_digest"]})
        assert effects(provider) == []
    finally:
        second.close()


def test_provider_ambiguous_completion_remains_unknown_on_replay(executor, grant_data, order, provider):
    grant = executor.create_grant("human:alice", grant_data)
    body = submission(grant, order)
    httpx.post(provider[0] + "/control", json={"mode": "accept_then_disconnect"},
               headers={"Authorization": "Bearer " + provider[1]}, trust_env=False)
    first = executor.submit("agent:alice", body)
    second = executor.submit("agent:alice", body)
    assert first == second and first["state"] == "unknown"
    assert len(effects(provider)) == 1
