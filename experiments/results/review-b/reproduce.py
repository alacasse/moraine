"""Independent review probes; never edits experiment source or frozen tests."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments"))
from run_campaign import Campaign

OUT = Path(__file__).resolve().parent


def expiry_during_intent_lock():
    active = Campaign("b", OUT / "expiry-during-intent-lock")
    try:
        active.start()
        expires = int(time.time()) + 3
        grant = active.grant(expires_at=expires)
        status, request = active.submit(grant, active.email(), "expiry-lock-review")
        assert status == 200 and request["state"] == "pending"
        with sqlite3.connect(active.state / "app/broker.sqlite3") as blocker:
            blocker.execute("BEGIN IMMEDIATE")
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(active.approve, request)
                while time.time() <= expires + .15:
                    time.sleep(.01)
                assert not pending.done(), "approval should be blocked on durable intent"
                effects_before_unlock = active.effects()
                unlocked_at = time.time()
                blocker.commit()
                response = pending.result(timeout=5)
        effects = active.effects()
        assert not effects_before_unlock
        assert unlocked_at > expires
        assert response[1]["state"] == "executed" and len(effects) == 1
        return {"expires_at": expires, "unlocked_at": unlocked_at,
                "effects_before_unlock": effects_before_unlock,
                "response": response, "effects_after_unlock": effects}
    finally:
        active.close()


def expiry_after_intent():
    old = os.environ.get("B_BROKER_TEST_PAUSE")
    os.environ["B_BROKER_TEST_PAUSE"] = "after_intent"
    active = Campaign("b", OUT / "expiry-after-intent")
    try:
        active.start()
        expires = int(time.time()) + 2
        grant = active.grant(expires_at=expires)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(active.submit, grant, active.order(), "expiry-review")
            marker = active.state / "app/test-paused"
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            assert marker.read_text() == "after_intent"
            effects_before_resume = active.effects()
            while time.time() <= expires + .15:
                time.sleep(.01)
            resumed_at = time.time()
            os.kill(active.app_process.pid, signal.SIGCONT)
            response = pending.result(timeout=5)
        effects = active.effects()
        assert not effects_before_resume
        assert resumed_at > expires
        assert response[1]["state"] == "executed" and len(effects) == 1
        return {"expires_at": expires, "resumed_at": resumed_at,
                "effects_before_resume": effects_before_resume,
                "response": response, "effects_after_resume": effects}
    finally:
        active.close()
        if old is None:
            os.environ.pop("B_BROKER_TEST_PAUSE", None)
        else:
            os.environ["B_BROKER_TEST_PAUSE"] = old


def rejected_control_mutates_mode():
    active = Campaign("b", OUT / "rejected-control")
    active.output.mkdir(parents=True, exist_ok=True)
    try:
        active.start_provider()
        rejected = active.provider("/control", "POST", {
            "mode": "reject_before", "document": {"id": "not-public-note", "version": 2, "content": "invalid"}})
        response = active.provider("/effects", "POST", {
            "execution_id": "oracle-rejected-control", "action": {"type": "fixture"}})
        effects = active.effects()
        assert rejected[0] == 400
        assert response[0] == 503 and effects == []
        return {"rejected_control_response": rejected, "next_effect_response": response,
                "effects": effects}
    finally:
        active.close()


if __name__ == "__main__":
    results = {"expiry_during_intent_lock": expiry_during_intent_lock(),
               "expiry_after_intent": expiry_after_intent(),
               "rejected_control_mutates_mode": rejected_control_mutates_mode()}
    (OUT / "reproduction.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
