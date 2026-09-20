import asyncio
import json

import cedarpy
import pytest
from apparitor.config import ScannerConfig
from apparitor.decision import VerdictStatus, is_allowed_gateway
from apparitor.engine import AuthorizationEngine
from apparitor.errors import AuthZENConfigError
from apparitor.models import Action, EvaluationRequest, Resource, Subject

from policy import StrictCedarBackend


def fixture_policy(tmp_path, source):
    applies = {"principalTypes": ["Agent"], "resourceTypes": ["Account"],
               "context": {"type": "Record", "attributes": {"quantity": {"type": "Long"}}}}
    schema = {"": {"entityTypes": {"Agent": {}, "Account": {}},
                   "actions": {"order.create": {"appliesTo": applies}}}}
    policy_path, schema_path = tmp_path / "test.cedar", tmp_path / "schema.json"
    policy_path.write_text(source)
    schema_path.write_text(json.dumps(schema))
    return StrictCedarBackend(policy_path, schema_path)


def request(quantity=1):
    return EvaluationRequest(subject=Subject(type="agent", id="agent:alice"),
                             action=Action(name="order.create"), resource=Resource(type="account", id="alice"),
                             context={"quantity": quantity})


@pytest.mark.parametrize("batch", [False, True])
def test_real_cedar_allow_with_error_is_blocked_by_real_apparitor(tmp_path, batch):
    backend = fixture_policy(tmp_path, '''
        permit(principal, action, resource);
        forbid(principal, action, resource)
        when { context.quantity + 9223372036854775807 > 0 };
    ''')
    raw = cedarpy.is_authorized(backend.cedar_request(request()), backend.policies, [], backend.schema)
    assert raw.decision == cedarpy.Decision.Allow
    assert "integer overflow" in raw.diagnostics.errors[0]

    async def scenario():
        engine = AuthorizationEngine(ScannerConfig(backend="cedar", cache_enabled=False, on_error="deny"), client=backend)
        verdict = await engine.evaluate_requests([request()] * (2 if batch else 1))
        assert verdict.status == VerdictStatus.ERROR
        assert not is_allowed_gateway(verdict)
        assert engine.metrics.decisions == {("block", "error"): 1}
        await engine.aclose()
    asyncio.run(scenario())


def test_real_engine_clean_evaluation_and_empty_evaluation(tmp_path):
    backend = fixture_policy(tmp_path, "permit(principal, action, resource) when { context.quantity > 0 };")

    async def scenario():
        engine = AuthorizationEngine(ScannerConfig(backend="cedar", cache_enabled=False, on_error="deny"), client=backend)
        assert is_allowed_gateway(await engine.evaluate_requests([request(1)]))
        assert not is_allowed_gateway(await engine.evaluate_requests([request(0)]))
        assert not is_allowed_gateway(await engine.evaluate_requests([]))
        # Public upstream metrics demonstrate that real engine execution occurred.
        assert engine.metrics.decisions == {("allow", "success"): 1, ("block", "success"): 1}
        assert engine.metrics.cache_hits == engine.metrics.cache_misses == 0
        await engine.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("source", ["this is not Cedar", "permit(principal, action, resource) when { context.unknown > 0 };"])
def test_invalid_policy_or_schema_cannot_construct_backend(tmp_path, source):
    with pytest.raises(AuthZENConfigError):
        fixture_policy(tmp_path, source)


def test_malformed_cedar_result_is_not_truthy_allow(tmp_path, monkeypatch):
    backend = fixture_policy(tmp_path, "permit(principal, action, resource);")
    monkeypatch.setattr(cedarpy, "is_authorized", lambda *a: {"decision": "Allow"})

    async def scenario():
        engine = AuthorizationEngine(ScannerConfig(backend="cedar", on_error="deny"), client=backend)
        verdict = await engine.evaluate_requests([request()])
        assert verdict.status == VerdictStatus.ERROR and not is_allowed_gateway(verdict)
        await engine.aclose()
    asyncio.run(scenario())
