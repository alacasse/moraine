"""Observable end-to-end expectations, independent of broker implementation details."""
from __future__ import annotations

import time
import uuid

from .runtime import write_json

SCENARIOS = ("approval", "human_rejection", "revocation", "expiration", "replay",
             "restart", "provider_rejection", "unknown_after_effect", "outside_scope")
REPLY = "Bonjour Camille, je confirme mardi à 10 h pour trois personnes. À mardi !"


def counts(run, attempts, effects):
    actual = (len(run.records("attempts")), len(run.records("effects")))
    run.assert_check("provider_counts", actual == (attempts, effects),
                     expected=[attempts, effects], actual=list(actual))


def state(run, expected, reason):
    result = run.refresh()
    run.assert_check("broker_state", result["state"] == expected and result["reason"] == reason,
                     expected=expected, actual=result)


def mcp_error(run, response, reason):
    run.assert_check("mcp_refusal", response["is_error"] and response["result"] is None
                     and response["content"] == [reason], expected=reason, actual=response)


def unavailable_content(run):
    response = run.agent("read_context", {"grant_id": run.grant["grant_id"],
                                           "resource_ref": "message-1", "version": 1})
    mcp_error(run, response, "scope_denied")
    run.assert_check("terminal_agent_projection_redacted", set(run.refresh()) == {"request_id", "state", "reason"})


def run_scenario(lab, name):
    if name not in SCENARIOS:
        raise ValueError("unknown_scenario")
    mode = {"provider_rejection": "reject_before", "unknown_after_effect": "accept_then_disconnect"}.get(name, "normal")
    run = None
    started = time.monotonic()
    result = {"scenario": name, "passed": False, "actor": "scripted"}
    try:
        run = lab.new(actor="scripted", provider_mode=mode, ttl=3 if name == "expiration" else 600)
        result["run_id"] = run.id
        run.assert_check("positive_context_read", run.read()["text"] == run.message["text"])
        if name == "outside_scope":
            response = run.agent("read_context", {"grant_id": run.grant["grant_id"],
                                                   "resource_ref": "message-private", "version": 1})
            mcp_error(run, response, "scope_denied")
            counts(run, 0, 0)
        else:
            response = run.propose(REPLY)
            run.assert_check("proposal_created", not response["is_error"])
            state(run, "pending", "requires_approval")
            original_id = run.request["request_id"]
            counts(run, 0, 0)
            if name == "restart":
                run.restart()
                run.assert_check("request_survives_restart", run.request["request_id"] == original_id)
                state(run, "pending", "requires_approval")
                counts(run, 0, 0)
            run.review()
            if name == "human_rejection":
                run.decide("reject")
                state(run, "rejected", "human_rejected")
                counts(run, 0, 0)
            elif name in {"revocation", "expiration"}:
                if name == "revocation":
                    run.revoke()
                else:
                    deadline = time.monotonic() + 8
                    while time.time() <= run.grant["expires_at"]:
                        if time.monotonic() > deadline:
                            raise TimeoutError("expiration_clock_did_not_advance")
                        time.sleep(.04)
                    run.refresh()
                run.decide("approve")  # The old nonce cannot resurrect a denied request.
                state(run, "denied", "grant_revoked" if name == "revocation" else "grant_expired")
                unavailable_content(run)
                counts(run, 0, 0)
            else:
                waiting = None
                if name == "unknown_after_effect":
                    second = run.agent("propose_reply", {**run.proposal, "idempotency_key": str(uuid.uuid4())})
                    run.assert_check("second_request_pending_before_unknown", not second["is_error"]
                                     and second["result"]["state"] == "pending")
                    waiting = run.human("review", request_id=second["result"]["request_id"])
                run.decide("approve")
                if name == "provider_rejection":
                    state(run, "failed", "provider_rejected")
                    counts(run, 1, 0)
                elif name == "unknown_after_effect":
                    state(run, "unknown", "provider_outcome_unknown")
                    run.verify_delivery()  # An observed local effect never rewrites broker uncertainty.
                    try:
                        run.human("decide_review", request_id=waiting["request_id"],
                                  action_digest=waiting["action_digest"], nonce=waiting["nonce"], decision="approve")
                    except ValueError as exc:
                        run.assert_check("preexisting_request_blocked", '"source_unresolved"' in str(exc), error=str(exc))
                    else:
                        run.assert_check("preexisting_request_blocked", False)
                    replay = run.propose(REPLY)
                    run.assert_check("unknown_replay_keeps_identity", not replay["is_error"]
                                     and replay["result"]["request_id"] == original_id)
                    run.restart()
                    state(run, "unknown", "provider_outcome_unknown")
                    mcp_error(run, run.agent("propose_reply", {**run.proposal, "idempotency_key": str(uuid.uuid4())}), "source_unresolved")
                    new_grant = run.human("create_grant", body={"agent": "agent:pilot", "account_id": "pilot@example.test",
                        "expires_at": time.time() + 600, "recipient": run.message["reply_address"],
                        "reply_to_ref": "message-1", "resources": [run.message]})
                    mcp_error(run, run.agent("propose_reply", {**run.proposal, "grant_id": new_grant["grant_id"],
                                                              "idempotency_key": str(uuid.uuid4())}), "source_unresolved")
                    counts(run, 1, 1)
                else:
                    state(run, "accepted", "provider_accepted")
                    run.assert_check("delivery_status_not_overclaimed", run.request["result"]["delivery_status"] == "unverified")
                    run.verify_delivery()
                    if name == "replay":
                        replay = run.propose(REPLY)
                        run.assert_check("replay_keeps_identity", not replay["is_error"]
                                         and replay["result"]["request_id"] == original_id)
                        mcp_error(run, run.agent("propose_reply", {**run.proposal, "body_text": "Contenu différent"}), "idempotency_conflict")
                        counts(run, 1, 1)
                        run.revoke()
                        state(run, "accepted", "provider_accepted")
                        unavailable_content(run)
                        counts(run, 1, 1)
        result["passed"] = True
    except Exception as exc:
        result["error"] = str(exc)
        if run:
            run.error = run.clean(str(exc))
            run.event("scenario.failed", {"scenario": name, "error": str(exc)})
    finally:
        if run:
            try:
                run.close()
            except Exception as exc:
                result.update(passed=False, cleanup_error=str(exc))
            try:
                result.update(attempts=len(run.records("attempts")), effects=len(run.records("effects")))
            except Exception as exc:
                result.update(passed=False, attempts=None, effects=None, evidence_error=str(exc))
            result.update(checks=len(run.checks), request=run.request, evidence=str(run.directory / "report.json"))
        result["duration_seconds"] = round(time.monotonic() - started, 3)
    return result


def run_suite(lab, scenarios=SCENARIOS, *, progress=None, cancel=None):
    report = {"actor": "scripted", "status": "running", "results": []}
    for name in scenarios:
        if cancel and cancel.is_set():
            report["status"] = "cancelled"
            break
        report["results"].append(run_scenario(lab, name))
        write_json(lab.directory / "campaign.json", report)
        if progress:
            progress(report)
    else:
        report["status"] = "passed" if all(row["passed"] for row in report["results"]) else "failed"
    write_json(lab.directory / "campaign.json", report)
    if progress:
        progress(report)
    return report
