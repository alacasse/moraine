"""Run policy decisions and authentication against the actual pinned engine."""
from pathlib import Path

import httpx
import pytest

from moraine_email.policy import OPA, PolicyFailure


@pytest.fixture
def engine():
    policy = OPA(Path(__file__).parents[1] / ".tools" / "opa")
    yield policy
    policy.close()


def test_empty_or_forged_authority_denied_by_actual_rego(engine):
    assert engine.decide({})["decision"] == "deny"
    facts = {"subject": "agent:other", "trusted": {"agent": "agent:pilot", "owner": "human:owner", "account": "pilot@example.test"},
             "grant": {"agent": "agent:other", "owner": "human:owner", "account_id": "pilot@example.test", "revoked": False,
                       "expires_at": 100, "resource_refs": ["allowed"]}, "now": 1, "operation": "read", "resource_ref": "allowed"}
    assert engine.decide(facts)["decision"] == "deny"
    facts["subject"] = facts["grant"]["agent"] = "agent:pilot"
    assert engine.decide(facts)["decision"] == "allow"
    facts["resource_ref"] = "foreign"
    assert engine.decide(facts)["decision"] == "deny"


def test_private_opa_api_rejects_unauthenticated_and_administration(engine):
    with httpx.Client(transport=httpx.HTTPTransport(uds=engine.socket), base_url="http://opa", trust_env=False) as client:
        assert client.post("/v1/data/broker/decision?strict-builtin-errors=true", json={"input": {}}).status_code in (401, 403)
        assert client.put("/v1/data/untrusted", json={}, headers={"Authorization": "Bearer " + engine.token}).status_code == 401


def test_unverified_binary_is_never_executed(tmp_path):
    fake = tmp_path / "opa"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o700)
    with pytest.raises(PolicyFailure, match="policy_binary_unverified"):
        OPA(fake)
