"""Real apparitor orchestration with a stricter Cedar diagnostics contract."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import cedarpy
from apparitor.backends import merge_batch_item
from apparitor.config import ScannerConfig
from apparitor.decision import is_allowed_gateway
from apparitor.engine import AuthorizationEngine
from apparitor.errors import AuthZENConfigError, MalformedPDPResponseError
from apparitor.models import (
    Action, BatchEvaluationRequest, BatchEvaluationResponse, EvaluationRequest,
    EvaluationResponse, Resource, Subject,
)

HERE = Path(__file__).resolve().parent


class StrictCedarBackend:
    """Public DecisionBackend protocol; never subclasses upstream private internals."""

    def __init__(self, policy_path=HERE / "policy.cedar", schema_path=HERE / "schema.json"):
        self.policies = Path(policy_path).read_text()
        self.schema = json.loads(Path(schema_path).read_text())
        try:
            validation = cedarpy.validate_policies(self.policies, self.schema)
            if not validation.validation_passed:
                raise ValueError("policy/schema validation failed")
        except Exception as exc:
            raise AuthZENConfigError("invalid embedded Cedar policy") from exc
        self.policy_hash = hashlib.sha256(
            (self.policies + json.dumps(self.schema, sort_keys=True)).encode()
        ).hexdigest()

    @staticmethod
    def cedar_request(request: EvaluationRequest) -> dict:
        # Structured IDs prevent syntax interpolation. No Resource.properties authority.
        if request.subject.type != "agent" or request.resource.type != "account":
            raise ValueError("unsupported entity kind")
        return {
            "principal": {"type": "Agent", "id": request.subject.id},
            "action": {"type": "Action", "id": request.action.name},
            "resource": {"type": "Account", "id": request.resource.id},
            "context": request.context or {},
        }

    @staticmethod
    def decision(result) -> bool:
        # Cedar can Allow despite an errored policy. This host refuses that result.
        if not isinstance(result, cedarpy.AuthzResult):
            raise ValueError("malformed Cedar result")
        errors = result.diagnostics.errors
        if not isinstance(errors, list) or errors:
            raise ValueError("Cedar diagnostics contain errors")
        if result.decision not in (cedarpy.Decision.Allow, cedarpy.Decision.Deny):
            raise ValueError("Cedar returned no decision")
        return result.decision == cedarpy.Decision.Allow

    def _single(self, request):
        try:
            return self.decision(cedarpy.is_authorized(
                self.cedar_request(request), self.policies, [], self.schema))
        except Exception as exc:
            raise MalformedPDPResponseError("embedded Cedar evaluation error") from exc

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        return EvaluationResponse(decision=await asyncio.to_thread(self._single, request))

    def _batch(self, request):
        try:
            requests = [self.cedar_request(merge_batch_item(item, request))
                        for item in request.evaluations]
            results = cedarpy.is_authorized_batch(requests, self.policies, [], self.schema)
            if len(results) != len(requests):
                raise ValueError("Cedar batch cardinality mismatch")
            return [EvaluationResponse(decision=self.decision(result)) for result in results]
        except Exception as exc:
            raise MalformedPDPResponseError("embedded Cedar batch evaluation error") from exc

    async def evaluate_batch(self, request: BatchEvaluationRequest) -> BatchEvaluationResponse:
        return BatchEvaluationResponse(evaluations=await asyncio.to_thread(self._batch, request))

    async def aclose(self):
        pass


class Policy:
    def __init__(self, policy_path=HERE / "policy.cedar", schema_path=HERE / "schema.json"):
        self.backend = StrictCedarBackend(policy_path, schema_path)
        self.engine = AuthorizationEngine(
            ScannerConfig(backend="cedar", cache_enabled=False, on_error="deny"),
            client=self.backend,
        )

    async def allows(self, actor: str, action: dict, grant: dict, now: int) -> bool:
        # No untrusted dictionary merge: map each field into its own policy slot.
        context = {
            "grant_agent": {"__entity": {"type": "Agent", "id": grant["agent"]}},
            "grant_account": {"__entity": {"type": "Account", "id": grant["account"]}},
            "revoked": grant["revoked"], "expires_at": grant["expires_at"], "now": now,
            "allowed_recipients": grant["recipients"], "allowed_documents": grant["document_ids"],
            "allowed_merchants": grant["merchants"], "allowed_currency": grant["currency"],
            "hard_limit_minor": grant["hard_limit_minor"],
            "recipients": action.get("to", []) + action.get("cc", []) + action.get("bcc", []),
            "attachment_ids": [item["id"] for item in action.get("attachments", [])],
            "merchant": action.get("merchant", ""), "currency": action.get("currency", ""),
            "quantity": action.get("quantity", 0), "amount_minor": action.get("amount_minor", 0),
            "shipping_address_id": action.get("shipping_address_id", ""),
            "recurring": action.get("recurring", False), "document_id": action.get("document_id", ""),
        }
        verdict = await self.engine.evaluate_requests([EvaluationRequest(
            subject=Subject(type="agent", id=actor), action=Action(name=action["type"]),
            resource=Resource(type="account", id=action["account"]), context=context,
        )])
        return is_allowed_gateway(verdict)

    async def aclose(self):
        await self.engine.aclose()
