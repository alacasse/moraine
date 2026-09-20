"""Review-only controlled defects, loaded in memory; frozen A sources are unchanged.

These mutants measure campaign assertion sensitivity. They are NOT findings that
the unchanged A implementation has either defect.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/a_embedded"))
import gate
import host

mutation = sys.argv.pop(1)
if mutation == "agent-can-create-grant":
    original_human = gate.ExecutionGate._human

    def missing_human_kind_check(actor):
        # An ordinary agent Alice can now create its own grant. Bob is still out
        # of account scope, and the Pydantic validation remains unchanged.
        if actor.kind == "agent" and actor.id == "agent:alice" and actor.account == "alice":
            return
        return original_human(actor)

    gate.ExecutionGate._human = staticmethod(missing_human_kind_check)
elif mutation == "false-executed-on-failure":
    original_dispatch = host.Handler.dispatch

    def wrong_outcome(self, method):
        status, result = original_dispatch(self, method)
        if result.get("state") in {"failed", "unknown"}:
            return 502, {**result, "state": "executed", "reason": "completed"}
        return status, result

    host.Handler.dispatch = wrong_outcome
else:
    raise SystemExit("unknown review mutation")

host.main()
