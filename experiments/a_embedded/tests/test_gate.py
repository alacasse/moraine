import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import sqlite3
import threading
import time

import pytest
from pydantic import ValidationError

from gate import ExecutionGate, Refusal
from models import Principal
from policy import Policy
from provider import ProviderClient

ALICE = Principal(kind="agent", id="agent:alice", account="alice")
BOB = Principal(kind="agent", id="agent:bob", account="bob")
HUMAN = Principal(kind="human", id="human:alice", account="alice")


def grant_spec(**changes):
    return {"agent": "agent:alice", "account": "alice", "expires_at": int(time.time()) + 600,
            "recipients": ["trusted@example.test"], "document_ids": ["public-note"],
            "merchants": ["shop.test"], "currency": "CAD", "auto_limit_minor": 1000,
            "hard_limit_minor": 5000, **changes}


def order(**changes):
    return {"type": "order.create", "account": "alice", "merchant": "shop.test", "sku": "paper",
            "quantity": 1, "amount_minor": 500, "currency": "CAD", "shipping_address_id": "home",
            "recurring": False, **changes}


def email(**changes):
    return {"type": "email.send", "account": "alice", "to": ["trusted@example.test"],
            "cc": [], "bcc": [], "subject": "Exact review", "body": "Keep these bytes",
            "attachments": [{"id": "public-note", "version": 1}], **changes}


@asynccontextmanager
async def opened(tmp_path, service, **kwargs):
    gate = ExecutionGate(tmp_path / "gate", ProviderClient(*service), **kwargs)
    try:
        await gate.provider.ready()
        yield gate
    finally:
        await gate.aclose()


async def effects(gate):
    return (await gate.provider.client.get("/effects")).json()["effects"]


@pytest.mark.parametrize("amount,state", [(1, "executed"), (1000, "executed"), (1001, "pending"), (5000, "pending"), (5001, "denied")])
def test_policy_thresholds_reach_actual_provider(tmp_path, provider_service, amount, state):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            grant = await gate.create_grant(HUMAN, grant_spec())
            outcome = await gate.submit(ALICE, grant["grant_id"], "threshold", order(amount_minor=amount))
            assert outcome["state"] == state
            assert len(await effects(gate)) == int(state == "executed")
            assert gate.policy.engine.metrics.latency_count >= 1
    asyncio.run(scenario())


def test_exact_email_snapshot_persists_across_restart_and_provider_change(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            grant = await gate.create_grant(HUMAN, grant_spec())
            pending = await gate.submit(ALICE, grant["grant_id"], "email", email())
            snapshot = await gate.inspect(HUMAN, pending["request_id"])
            assert snapshot["snapshot"]["action"]["attachments"] == [
                {"id": "public-note", "version": 1, "content": "Public fixture note"}]
            assert snapshot["review_deadline"] <= int(time.time()) + 300
            await gate.provider.client.post("/control", json={"document": {"id": "public-note", "version": 2, "content": "Replacement bytes"}})
        async with opened(tmp_path, provider_service) as gate:
            assert (await gate.approve(HUMAN, pending["request_id"], pending["action_digest"]))["state"] == "executed"
            sent = (await effects(gate))[0]["action"]
            assert sent == snapshot["snapshot"]["action"]
            with pytest.raises(Refusal):
                await gate.approve(HUMAN, pending["request_id"], pending["action_digest"])
            assert (await gate.submit(ALICE, grant["grant_id"], "email", email()))["state"] == "executed"
            assert len(await effects(gate)) == 1
    asyncio.run(scenario())


def test_revocation_is_durable_and_not_cached(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            grant = await gate.create_grant(HUMAN, grant_spec())
            first = await gate.submit(ALICE, grant["grant_id"], "allowed", order())
            assert first["state"] == "executed"
            pending = await gate.submit(ALICE, grant["grant_id"], "pending", email())
            await gate.revoke(HUMAN, grant["grant_id"])
            assert (await gate.submit(ALICE, grant["grant_id"], "after-revoke", order()))["state"] == "denied"
        async with opened(tmp_path, provider_service) as gate:
            assert (await gate.approve(HUMAN, pending["request_id"], pending["action_digest"]))["state"] == "denied"
            assert len(await effects(gate)) == 1
    asyncio.run(scenario())


def test_denied_read_and_bcc_never_reach_provider(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            grant = await gate.create_grant(HUMAN, grant_spec())
            actions = [email(bcc=["attacker@example.test"]), email(attachments=[{"id": "tax-return", "version": 1}]),
                       {"type": "document.read", "account": "alice", "document_id": "tax-return"}]
            for index, action in enumerate(actions):
                assert (await gate.submit(ALICE, grant["grant_id"], str(index), action))["state"] == "denied"
            assert (await gate.provider.client.get("/reads")).json()["reads"] == []
            assert await effects(gate) == []
    asyncio.run(scenario())


@pytest.mark.parametrize("amount", [True, 500.0, "500", -1, 0, 2**63])
def test_strict_numeric_input_before_policy_or_provider(tmp_path, provider_service, amount):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            grant = await gate.create_grant(HUMAN, grant_spec())
            with pytest.raises(ValidationError):
                await gate.submit(ALICE, grant["grant_id"], "bad-number", order(amount_minor=amount))
            assert gate.policy.engine.metrics.latency_count == 0
            assert await effects(gate) == []
    asyncio.run(scenario())


def test_actor_binding_and_idempotency_payload_conflict(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            grant = await gate.create_grant(HUMAN, grant_spec())
            original = await gate.submit(ALICE, grant["grant_id"], "same-key", order())
            assert (await gate.submit(ALICE, grant["grant_id"], "same-key", order())) == original
            with pytest.raises(Refusal, match="idempotency_conflict"):
                await gate.submit(ALICE, grant["grant_id"], "same-key", order(amount_minor=501))
            other = await gate.submit(BOB, grant["grant_id"], "same-key", order())
            assert other["state"] == "denied" and other["request_id"] != original["request_id"]
            with pytest.raises(Refusal, match="not_found"):
                await gate.inspect(BOB, original["request_id"])
            assert len(await effects(gate)) == 1
    asyncio.run(scenario())


def test_expiry_after_attachment_preparation_blocks_review(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            expiry = int(time.time()) + 1
            grant = await gate.create_grant(HUMAN, grant_spec(expires_at=expiry))
            fetch = gate.provider.document
            async def slow_document(identifier):
                result = await fetch(identifier)
                await asyncio.sleep(max(0, expiry - time.time() + 0.03))
                return result
            gate.provider.document = slow_document
            assert (await gate.submit(ALICE, grant["grant_id"], "slow", email()))["state"] == "denied"
            assert await effects(gate) == []
    asyncio.run(scenario())


def test_expiry_between_attachments_prevents_second_provider_read(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            expiry = int(time.time()) + 2
            grant = await gate.create_grant(HUMAN, grant_spec(expires_at=expiry))
            fetch = gate.provider.document
            started = []

            async def delayed_first_document(identifier):
                started.append(time.time())
                result = await fetch(identifier)
                if len(started) == 1:
                    await asyncio.sleep(max(0, expiry - time.time() + 0.05))
                return result

            gate.provider.document = delayed_first_document
            proposal = email(attachments=[{"id": "public-note", "version": 1}] * 2)
            outcome = await gate.submit(ALICE, grant["grant_id"], "two-reads", proposal)
            reads = (await gate.provider.client.get("/reads")).json()["reads"]
            assert (outcome["state"], len(reads), len(started)) == ("denied", 1, 1)
            assert await effects(gate) == []
    asyncio.run(scenario())


@pytest.mark.parametrize("deadline", ["grant", "review"])
def test_expiry_while_sqlite_waits_prevents_dispatch_and_replay(tmp_path, provider_service, deadline):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            if deadline == "review":
                gate.REVIEW_MAX_AGE = 2
            changes = {"expires_at": int(time.time()) + 2} if deadline == "grant" else {}
            grant = await gate.create_grant(HUMAN, grant_spec(**changes))
            proposal = email()
            pending = await gate.submit(ALICE, grant["grant_id"], "storage-wait", proposal)
            snapshot = await gate.inspect(HUMAN, pending["request_id"])
            blocker = sqlite3.connect(tmp_path / "gate/gate.sqlite3", check_same_thread=False)
            blocker.execute("BEGIN IMMEDIATE")

            def release_after_deadline():
                time.sleep(max(0, snapshot["review_deadline"] - time.time() + 0.1))
                blocker.commit()

            release = threading.Thread(target=release_after_deadline)
            release.start()
            try:
                outcome = await gate.approve(HUMAN, pending["request_id"], pending["action_digest"])
            finally:
                release.join(timeout=5)
                blocker.close()
            assert (outcome["state"], await effects(gate)) == ("denied", [])
            assert (await gate.submit(ALICE, grant["grant_id"], "storage-wait", proposal))["state"] == "denied"
        async with opened(tmp_path, provider_service) as gate:
            assert (await gate.submit(ALICE, grant["grant_id"], "storage-wait", proposal))["state"] == "denied"
            assert await effects(gate) == []
    asyncio.run(scenario())


def test_approval_maximum_age_is_enforced(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            gate.REVIEW_MAX_AGE = 0
            grant = await gate.create_grant(HUMAN, grant_spec())
            pending = await gate.submit(ALICE, grant["grant_id"], "expired-review", email())
            result = await gate.approve(HUMAN, pending["request_id"], pending["action_digest"])
            assert result["state"] == "denied" and result["reason"] == "review_expired"
            assert await effects(gate) == []
    asyncio.run(scenario())


def test_concurrent_approvals_dispatch_once(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            grant = await gate.create_grant(HUMAN, grant_spec())
            pending = await gate.submit(ALICE, grant["grant_id"], "concurrent", email())
            outcomes = await asyncio.gather(*[gate.approve(HUMAN, pending["request_id"], pending["action_digest"])
                                              for _ in range(8)], return_exceptions=True)
            assert sum(isinstance(result, dict) and result["state"] == "executed" for result in outcomes) == 1
            assert len(await effects(gate)) == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("mode,state,count", [("reject_before", "failed", 0), ("accept_then_disconnect", "unknown", 1)])
def test_provider_outcomes_are_durable_without_blind_retry(tmp_path, provider_service, mode, state, count):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            grant = await gate.create_grant(HUMAN, grant_spec())
            await gate.provider.client.post("/control", json={"mode": mode})
            result = await gate.submit(ALICE, grant["grant_id"], "outcome", order())
            assert result["state"] == state
        async with opened(tmp_path, provider_service) as gate:
            assert (await gate.submit(ALICE, grant["grant_id"], "outcome", order())) == result
            assert len(await effects(gate)) == count
    asyncio.run(scenario())


def test_interrupted_dispatch_recovers_unknown_and_never_reexecutes(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            grant = await gate.create_grant(HUMAN, grant_spec())
            accepted = asyncio.Event()
            execute = gate.provider.execute
            async def pause_after_accept(*args):
                await execute(*args)
                accepted.set()
                await asyncio.Event().wait()
            gate.provider.execute = pause_after_accept
            task = asyncio.create_task(gate.submit(ALICE, grant["grant_id"], "interrupted", order()))
            await asyncio.wait_for(accepted.wait(), timeout=3)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            # The public API never leaks an internal phase even before restart.
            assert (await gate.submit(ALICE, grant["grant_id"], "interrupted", order()))["state"] == "unknown"
            assert len(await effects(gate)) == 1
        async with opened(tmp_path, provider_service) as gate:
            outcome = await gate.submit(ALICE, grant["grant_id"], "interrupted", order())
            assert outcome["state"] == "unknown" and outcome["reason"] == "interrupted_dispatch"
            assert len(await effects(gate)) == 1
    asyncio.run(scenario())


def test_pending_request_rechecks_new_policy_on_restart(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service) as gate:
            grant = await gate.create_grant(HUMAN, grant_spec())
            pending = await gate.submit(ALICE, grant["grant_id"], "new-policy", email())
        changed = tmp_path / "deny.cedar"
        changed.write_text('forbid(principal, action, resource);')
        async with opened(tmp_path, provider_service, policy=Policy(policy_path=changed)) as gate:
            assert (await gate.approve(HUMAN, pending["request_id"], pending["action_digest"]))["state"] == "denied"
            assert await effects(gate) == []
    asyncio.run(scenario())


def test_second_gate_cannot_share_a_live_state_directory(tmp_path, provider_service):
    async def scenario():
        async with opened(tmp_path, provider_service):
            second_provider = ProviderClient(*provider_service)
            try:
                with pytest.raises(RuntimeError, match="already has a live gate"):
                    ExecutionGate(tmp_path / "gate", second_provider)
            finally:
                await second_provider.aclose()
    asyncio.run(scenario())
