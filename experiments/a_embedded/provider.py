"""Private credential holder for the synthetic downstream service."""
from urllib.parse import quote

import httpx


class ProviderRejected(Exception):
    pass


class ProviderUnknown(Exception):
    pass


class ProviderClient:
    def __init__(self, url: str, token: str):
        self.client = httpx.AsyncClient(
            base_url=url.rstrip("/"), headers={"Authorization": "Bearer " + token},
            timeout=httpx.Timeout(3.0), follow_redirects=False, trust_env=False,
        )

    async def ready(self):
        # Verify credential and connectivity without disclosing a document.
        response = await self.client.get("/effects")
        response.raise_for_status()
        if not isinstance(response.json().get("effects"), list):
            raise ValueError("provider readiness response invalid")

    async def document(self, identifier: str) -> dict:
        try:
            response = await self.client.get("/documents/" + quote(identifier, safe=""))
            response.raise_for_status()
            result = response.json()
            if (not isinstance(result, dict) or result.get("id") != identifier
                    or type(result.get("version")) is not int or result["version"] <= 0
                    or not isinstance(result.get("content"), str)
                    or not isinstance(result.get("classification"), str)):
                raise ValueError("invalid document")
            return {key: result[key] for key in ("id", "version", "content", "classification")}
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ProviderRejected("document_unavailable") from exc

    async def execute(self, execution_id: str, action: dict) -> dict:
        try:
            response = await self.client.post("/effects", json={
                "execution_id": execution_id, "action": action,
            })
        except httpx.HTTPError as exc:
            raise ProviderUnknown("provider_outcome_unknown") from exc
        if not 200 <= response.status_code < 300:
            raise ProviderRejected("provider_rejected")
        try:
            result = response.json()
            if (not isinstance(result, dict) or not isinstance(result.get("effect_id"), str)
                    or result.get("execution_id") != execution_id):
                raise ValueError("invalid provider receipt")
            return {key: result[key] for key in ("effect_id", "execution_id")}
        except (ValueError, KeyError) as exc:
            # A malformed success receipt does not establish absence of an effect.
            raise ProviderUnknown("provider_outcome_unknown") from exc

    async def aclose(self):
        await self.client.aclose()
