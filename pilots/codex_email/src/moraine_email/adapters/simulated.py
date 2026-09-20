"""One-shot HTTP adapter for the independently observed synthetic provider."""
import asyncio
import base64
import hashlib
import json
from urllib.parse import urlsplit

import httpx

from ..models import PilotError


class SimulatedProvider:
    def __init__(self, url, token):
        origin = urlsplit(url)
        if (origin.scheme != "http" or origin.hostname != "127.0.0.1"
                or origin.username or origin.password or origin.path not in ("", "/")
                or origin.query or origin.fragment):
            raise ValueError("The simulated provider must be a loopback HTTP origin")
        if type(token) is not str or not token or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError("Invalid simulated provider token")
        self.url = url.rstrip("/")
        self.headers = {"Authorization": "Bearer " + token}

    def send_prepared(self, prepared, execution_id):
        try:
            raw = base64.b64decode(prepared["mime_b64"], validate=True)
        except (ValueError, KeyError) as error:
            raise PilotError("invalid_prepared_mime") from error
        if hashlib.sha256(raw).hexdigest() != prepared["mime_sha256"]:
            raise PilotError("invalid_prepared_mime")
        return asyncio.run(self._send(prepared, execution_id))

    async def _send(self, prepared, execution_id):
        try:
            # Cancellation encloses connect, write, response headers AND body.
            # A synchronous HTTPX read timeout alone can be prolonged by trickles.
            async with asyncio.timeout(4):
                async with httpx.AsyncClient(base_url=self.url, timeout=1, trust_env=False,
                                             follow_redirects=False, headers=self.headers,
                                             transport=httpx.AsyncHTTPTransport(retries=0)) as client:
                    async with client.stream("POST", "/send", json={"execution_id": execution_id,
                                                                   "mime_b64": prepared["mime_b64"]}) as response:
                        chunks = bytearray()
                        async for chunk in response.aiter_bytes():
                            chunks.extend(chunk)
                            if len(chunks) > 8192:
                                raise ValueError("bounded provider response exceeded")
                        result = json.loads(chunks)
                        status = response.status_code
            if status == 422 and result == {"error": "synthetic_rejected_before_effect"}:
                return {"state": "failed", "reason": "provider_rejected", "result": {}}
            if (status == 200 and type(result) is dict
                    and result.get("execution_id") == execution_id
                    and type(result.get("message_id")) is str and result["message_id"]):
                return {"state": "accepted", "reason": "provider_accepted",
                        "result": {"provider_message_id": result["message_id"], "delivery_status": "unverified"}}
        except (httpx.HTTPError, ValueError, TimeoutError):
            pass
        return {"state": "unknown", "reason": "provider_outcome_unknown", "result": {}}

    def close(self):
        # Each bounded attempt owns and closes its client, including cancellation.
        pass
