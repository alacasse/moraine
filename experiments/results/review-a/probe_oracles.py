"""Run the real HTTP campaign against two explicit, review-only A mutants."""
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments"))
from run_campaign import Campaign, require

HERE = Path(__file__).resolve().parent


class MutantCampaign(Campaign):
    def __init__(self, mutation):
        super().__init__("a", HERE / mutation)
        self.mutation = mutation

    def start_app(self):
        folder = ROOT / "experiments/a_embedded"
        command = [str(folder / ".venv/bin/python"), str(HERE / "mutant_host.py"), self.mutation,
                   "--port", str(self.app_port), "--state-dir", str(self.state / "app"),
                   "--provider-url", self.provider_url, "--provider-token", self.tokens["provider"],
                   "--agent-token", self.tokens["agent"], "--other-agent-token", self.tokens["other"],
                   "--human-token", self.tokens["human"]]
        start = time.monotonic()
        self.app_process = self.launch(command, "application", folder)
        self.ready(self.app_url, self.app_process)
        self.startup_seconds += time.monotonic() - start


report = {"purpose": "Controlled mutation testing of campaign oracles; not defects in frozen A", "mutations": {}}
for mutation in ("agent-can-create-grant", "false-executed-on-failure"):
    campaign = MutantCampaign(mutation)
    try:
        campaign.start()
        for name, test in campaign.tests():
            campaign.case(name, test)
        proof = {"cases": campaign.cases, "passed": sum(c["passed"] for c in campaign.cases),
                 "failed": sum(not c["passed"] for c in campaign.cases)}
        if mutation == "agent-can-create-grant":
            spec = {"agent": "agent:alice", "account": "alice", "expires_at": int(time.time()) + 600,
                    "recipients": ["attacker@example.test"], "document_ids": ["tax-return"],
                    "merchants": ["attacker.test"], "currency": "CAD", "auto_limit_minor": 5000,
                    "hard_limit_minor": 5000}
            status, grant = campaign.api("/grants", "POST", spec, "agent")
            require(status == 201 and grant.get("grant_id"), (status, grant))
            before = len(campaign.effects())
            response = campaign.submit(grant, campaign.order(merchant="attacker.test", amount_minor=4999))
            require(response[1].get("state") == "executed", response)
            require(len(campaign.effects()) == before + 1, "mutant did not produce observable unauthorized effect")
            proof["additional_probe"] = {"grant_created_with_agent_credential": [status, grant],
                                         "effect_from_self_issued_authority": campaign.effects()[-1]}
        else:
            before = len(campaign.effects())
            campaign.provider("/control", "POST", {"mode": "reject_before"})
            response = campaign.submit(campaign.grant(), campaign.order())
            require(response[0] == 502 and response[1]["state"] == "executed", response)
            require(len(campaign.effects()) == before, "provider should have rejected")
            proof["additional_probe"] = {"false_success_response": response, "effect_delta": 0}
        report["mutations"][mutation] = proof
    finally:
        campaign.close()

manifest = json.loads((ROOT / "experiments/a_embedded/evidence/source-manifest.json").read_text())
report["frozen_source_mismatches"] = [p for p, digest in manifest.items()
                                       if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
destination = HERE / "oracle-probes.json"
destination.write_text(json.dumps(report, indent=2) + "\n")
print(destination)
