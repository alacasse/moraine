"""Real process/HTTP tests for B's distinct claims; no substitute evaluator."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments"))
from run_campaign import Campaign
from opa import OPA, PolicyFailure

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def campaign(tmp_path):
    active = Campaign("b", tmp_path / "evidence")
    try:
        active.start()
        yield active
    finally:
        active.close()


def child_pid(process):
    children = Path(f"/proc/{process.pid}/task/{process.pid}/children").read_text().split()
    assert len(children) == 1, children
    return int(children[0])


def test_killed_real_opa_fails_closed(campaign):
    _, pending = campaign.pending()
    grant = campaign.grant()
    os.kill(child_pid(campaign.app_process), signal.SIGKILL)
    status, result = campaign.submit(grant, campaign.order())
    assert status == 200 and result["state"] == "failed"
    assert result["reason"] == "policy_unavailable"
    assert campaign.approve(pending)[1]["state"] == "failed"
    assert campaign.api("/health", actor=None)[0] == 503
    assert campaign.effects() == []
    # Historical reads and revocation remain possible during dependency outage.
    assert campaign.api("/requests/" + pending["request_id"])[0] == 200
    assert campaign.api(f"/grants/{grant['grant_id']}/revoke", "POST", {}, "human")[0] == 200


@pytest.mark.parametrize("policy,reason", [("runtime_error", "policy_unavailable"),
                                          ("conflict", "policy_unavailable"),
                                          ("malformed", "policy_invalid_result")])
def test_real_policy_evaluation_failure(tmp_path, monkeypatch, policy, reason):
    monkeypatch.setenv("B_BROKER_TEST_POLICY", str(FIXTURES / f"{policy}.rego"))
    active = Campaign("b", tmp_path / policy)
    try:
        active.start()
        response = active.submit(active.grant(), active.order())
        assert response[1]["state"] == "failed", response
        assert response[1]["reason"] == reason
        assert active.effects() == []
    finally:
        active.close()


def test_invalid_rego_blocks_startup():
    with pytest.raises(PolicyFailure, match="policy_invalid"):
        OPA(FIXTURES / "invalid.rego")


def test_real_undefined_result_and_startup_gate():
    opa = OPA(FIXTURES / "undefined.rego")
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                raw = opa.client.post("/v1/data/broker/decision?strict-builtin-errors=true", json={"input": {}})
                break
            except httpx.HTTPError:
                time.sleep(.05)
        assert raw.status_code == 200 and "result" not in raw.json()
        with pytest.raises(PolicyFailure, match="policy_invalid_result"):
            opa.decide({})
        assert not opa.healthy()
        with pytest.raises(PolicyFailure, match="policy_not_ready"):
            opa.wait_ready()
    finally:
        opa.close()


def test_private_opa_auth_and_management_routes():
    opa = OPA()
    try:
        opa.wait_ready()
        # OPA's only configured listener is a Unix socket, with a 0700 parent.
        command = Path(f"/proc/{opa.process.pid}/cmdline").read_bytes().split(b"\0")
        addresses = [command[i + 1] for i, item in enumerate(command) if item == b"--addr"]
        assert addresses == [("unix://" + opa.socket).encode()]
        assert Path(opa.socket).parent.stat().st_mode & 0o777 == 0o700
        for token in (None, "agent-fixture", "human-fixture"):
            headers = {"Authorization": "Bearer " + token} if token else {}
            with httpx.Client(transport=httpx.HTTPTransport(uds=opa.socket), base_url="http://opa", headers=headers) as client:
                assert client.get("/health").status_code in (401, 403)
                assert client.post("/v1/data/broker/decision?strict-builtin-errors=true", json={"input": {}}).status_code in (401, 403)
                assert client.get("/v1/data").status_code in (401, 403)
        for method, route in (("GET", "/v1/data"), ("PUT", "/v1/data"),
                              ("GET", "/v1/policies"), ("PUT", "/v1/policies/evil"),
                              ("POST", "/v1/compile")):
            assert opa.client.request(method, route, content=b"{}").status_code in (401, 403)
        assert opa.client.post("/v1/data/broker/decision?strict-builtin-errors=true&explain=full", json={"input": {}}).status_code in (401, 403)
    finally:
        opa.close()


def test_second_broker_refuses_same_state(campaign):
    process = campaign.app_process
    result = subprocess.run(process.args, cwd=ROOT, capture_output=True, timeout=10)
    assert result.returncode != 0
    assert b"BlockingIOError" in result.stderr
    assert campaign.api("/health", actor=None)[0] == 200


def test_strict_protocol_and_no_authority_fields(campaign):
    grant = campaign.grant()
    valid = {"grant_id": grant["grant_id"], "idempotency_key": "protocol", "action": campaign.order()}
    malformed = ['{"grant_id":"one","grant_id":"two"}', '[]', '{"now":NaN}',
                 '{"value":"\\ud800"}', json.dumps({**valid, "now": 0}),
                 json.dumps({**valid, "approved": True}),
                 json.dumps({**valid, "action": {**campaign.order(), "amount_minor": 1.0}})]
    with httpx.Client(base_url=campaign.app_url, headers={"Authorization": "Bearer " + campaign.tokens["agent"]}) as client:
        for body in malformed:
            assert client.post("/requests", content=body).status_code == 400
        assert client.post("/requests", content=b"\xff").status_code == 400
    assert campaign.effects() == []


def test_approval_race_persists_one_intent(campaign):
    _, pending = campaign.pending()
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: campaign.approve(pending), range(8)))
    assert sum(status == 200 for status, _ in responses) == 1
    assert len(campaign.effects()) == 1
    with sqlite3.connect(campaign.state / "app/broker.sqlite3") as db:
        assert db.execute("SELECT count(*) FROM executions").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM approvals").fetchone()[0] == 1


@pytest.mark.parametrize("phase,effect_count", [("after_intent", 0), ("after_effect", 1)])
def test_crash_intent_recovery_without_redispatch(tmp_path, monkeypatch, phase, effect_count):
    monkeypatch.setenv("B_BROKER_TEST_PAUSE", phase)
    active = Campaign("b", tmp_path / phase)
    try:
        active.start()
        grant, key = active.grant(), "interrupted"
        def submit():
            try:
                return active.submit(grant, active.order(), key)
            except OSError:
                return None
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(submit)
            marker = active.state / "app/test-paused"
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            assert marker.read_text() == phase
            assert len(active.effects()) == effect_count
            with sqlite3.connect(active.state / "app/broker.sqlite3") as db:
                original = db.execute("SELECT id FROM executions").fetchone()[0]
            active.stop(active.app_process, hard=True)
            future.result(timeout=5)
        monkeypatch.delenv("B_BROKER_TEST_PAUSE")
        active.start_app()
        result = active.submit(grant, active.order(), key)[1]
        assert result["state"] == "unknown" and result["reason"] == "execution_interrupted"
        assert len(active.effects()) == effect_count
        with sqlite3.connect(active.state / "app/broker.sqlite3") as db:
            assert db.execute("SELECT id,state FROM executions").fetchall() == [(original, "unknown")]
    finally:
        active.close()


def test_policy_revision_change_invalidates_pending(campaign, monkeypatch, tmp_path):
    _, pending = campaign.pending()
    replacement = tmp_path / "new.rego"
    replacement.write_text((ROOT / "experiments/b_broker/policy/broker.rego").read_text() + "\n# New revision\n")
    monkeypatch.setenv("B_BROKER_TEST_POLICY", str(replacement))
    campaign.restart()
    assert campaign.approve(pending)[1]["reason"] == "policy_changed"
    assert campaign.effects() == []


@pytest.mark.parametrize("deadline_kind", ["grant", "review"])
def test_expiry_during_intent_lock_stays_terminal_without_effect(campaign, deadline_kind):
    from broker import canonical, digest

    expiry = int(time.time()) + 3
    grant = campaign.grant(expires_at=expiry if deadline_kind == "grant" else expiry + 600)
    key, action = "expired-intent", campaign.email(attachments=[])
    pending = campaign.submit(grant, action, key)[1]
    assert pending["state"] == "pending"
    if deadline_kind == "review":
        # Build a legitimately aged review snapshot without sleeping five minutes.
        # No clock is replaced. The original grant remains valid beyond this deadline.
        with sqlite3.connect(campaign.state / "app/broker.sqlite3") as db:
            snapshot = json.loads(db.execute("SELECT snapshot FROM requests WHERE id=?",
                                            (pending["request_id"],)).fetchone()[0])
            snapshot.update(prepared_at=expiry - 300, review_expires_at=expiry)
            pending["action_digest"] = digest(snapshot)
            db.execute("UPDATE requests SET snapshot=?,action_digest=?,review_expires_at=? WHERE id=?",
                       (canonical(snapshot), pending["action_digest"], expiry, pending["request_id"]))
    with sqlite3.connect(campaign.state / "app/broker.sqlite3", isolation_level=None) as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(campaign.approve, pending)
            time.sleep(max(0, expiry - time.time() + .1))
            try:
                assert not future.done(), "approval must be waiting for its durable reservation"
                assert campaign.effects() == []
            finally:
                blocker.execute("COMMIT")
            status, result = future.result(timeout=5)
    assert status == 200 and result["state"] == "denied"
    assert result["reason"] == "authorization_expired"
    assert campaign.submit(grant, action, key)[1] == result
    assert campaign.approve(pending)[0] == 409
    campaign.restart()
    assert campaign.submit(grant, action, key)[1] == result
    assert campaign.effects() == [] and campaign.reads() == []
    with sqlite3.connect(campaign.state / "app/broker.sqlite3") as db:
        assert db.execute("SELECT state FROM executions").fetchall() == [("denied",)]


@pytest.mark.parametrize("deadline_kind", ["grant_read", "consent"])
def test_expiry_after_committed_intent_pause_prevents_io(tmp_path, monkeypatch, deadline_kind):
    monkeypatch.setenv("B_BROKER_TEST_PAUSE", "after_intent")
    active = Campaign("b", tmp_path / deadline_kind)
    try:
        active.start()
        expiry = int(time.time()) + 3
        grant = active.grant(expires_at=expiry if deadline_kind == "grant_read" else expiry + 600)
        key = "paused-expiry"
        pending = None
        if deadline_kind == "grant_read":
            action = {"type": "document.read", "account": "alice", "document_id": "public-note"}
            path = "/requests"
            body = {"grant_id": grant["grant_id"], "idempotency_key": key, "action": action}
            token = active.tokens["agent"]
        else:
            action = active.email(attachments=[])
            pending = active.submit(grant, action, key)[1]
            assert pending["state"] == "pending"
            path = f"/requests/{pending['request_id']}/approve"
            body = {"action_digest": pending["action_digest"]}
            token = active.tokens["human"]

        def call():
            # Consent uses its real 60-second lifetime, not an injected clock.
            with httpx.Client(timeout=75, trust_env=False) as client:
                response = client.post(active.app_url + path, json=body,
                                       headers={"Authorization": "Bearer " + token})
                return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(call)
            marker = active.state / "app/test-paused"
            ready_deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < ready_deadline:
                time.sleep(.02)
            try:
                assert marker.read_text() == "after_intent"
                if deadline_kind == "consent":
                    with sqlite3.connect(active.state / "app/broker.sqlite3") as db:
                        accepted, expiry = db.execute("SELECT accepted_at,expires_at FROM approvals").fetchone()
                        assert expiry == accepted + 60
                assert active.effects() == [] and active.reads() == []
                time.sleep(max(0, expiry - time.time() + .1))
            finally:
                os.kill(active.app_process.pid, signal.SIGCONT)
            status, result = future.result(timeout=5)
        assert status == 200 and result["state"] == "denied"
        assert result["reason"] == "authorization_expired"
        assert active.submit(grant, action, key)[1] == result
        if pending:
            assert active.approve(pending)[0] == 409
        active.restart()
        assert active.submit(grant, action, key)[1] == result
        assert active.effects() == [] and active.reads() == []
    finally:
        active.close()
