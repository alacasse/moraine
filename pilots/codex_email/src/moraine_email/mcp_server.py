"""Official MCP SDK Streamable HTTP transport for the four agent operations."""
from __future__ import annotations

from contextlib import asynccontextmanager
from functools import partial
import hmac
import hashlib
import time
import json

import anyio
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.routing import Route

from .human_server import strict_json
from .models import PilotError

MAX_BODY = 128 * 1024
FIELDS = {
    "list_context": {"grant_id": str},
    "read_context": {"grant_id": str, "resource_ref": str, "version": int},
    "propose_reply": {"grant_id": str, "idempotency_key": str, "reply_to_ref": str, "body_text": str},
    "get_request": {"request_id": str},
}


def _schema(fields):
    return {"type": "object", "additionalProperties": False,
            "required": list(fields), "properties": {
                name: ({"type": "integer", "minimum": 1} if kind is int else
                       {"type": "string", "minLength": 1, "maxLength": 16384 if name == "body_text" else 128})
                for name, kind in fields.items()}}


def _error(reason):
    return types.CallToolResult(isError=True, content=[types.TextContent(type="text", text=reason)])


class _Boundary:
    def __init__(self, app, token: str, port: int, auth_lifetime_seconds: float):
        self.app = app
        self.token_hash = hashlib.sha256(token.encode("ascii")).digest()
        self.expires_at = time.monotonic() + auth_lifetime_seconds
        self.hosts = {f"127.0.0.1:{port}".encode(), f"localhost:{port}".encode()}
        self.origins = {b"http://" + host for host in self.hosts}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def refuse(status, reason):
            await send({"type": "http.response.start", "status": status,
                        "headers": [(b"content-type", b"application/json"), (b"cache-control", b"no-store")]})
            await send({"type": "http.response.body", "body": json.dumps({"error": reason}).encode()})

        headers = {}
        for name, value in scope["headers"]:
            name = name.lower()
            if name in headers and name in {b"authorization", b"origin", b"host", b"content-length"}:
                return await refuse(400, "invalid_headers")
            headers[name] = value
        authorization = headers.get(b"authorization", b"")
        candidate = authorization.removeprefix(b"Bearer ")
        if (time.monotonic() >= self.expires_at or not authorization.startswith(b"Bearer ")
                or not hmac.compare_digest(hashlib.sha256(candidate).digest(), self.token_hash)):
            return await refuse(401, "unauthorized")
        if headers.get(b"host") not in self.hosts:
            return await refuse(403, "invalid_host")
        if b"origin" in headers and headers[b"origin"] not in self.origins:
            return await refuse(403, "invalid_origin")
        if scope["path"] != "/mcp":
            return await refuse(404, "not_found")
        body = bytearray()
        try:
            with anyio.fail_after(5):
                while True:
                    event = await receive()
                    if event["type"] == "http.disconnect":
                        return
                    body.extend(event.get("body", b""))
                    if len(body) > MAX_BODY:
                        return await refuse(413, "request_too_large")
                    if not event.get("more_body", False):
                        break
        except TimeoutError:
            return await refuse(408, "request_timeout")
        if body:
            try:
                parsed = strict_json(bytes(body))
                if not isinstance(parsed, dict):
                    return await refuse(400, "invalid_json")
            except (ValueError, UnicodeError, RecursionError):
                return await refuse(400, "invalid_json")
        # Receiving a body can cross the bearer deadline even though ingress
        # authentication succeeded. Do not enqueue an expired request in MCP.
        if time.monotonic() >= self.expires_at:
            return await refuse(401, "unauthorized")
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(broker, *, token: str, agent: str = "agent:pilot", port: int = 8765, auth_lifetime_seconds: float = 86400):
    if not isinstance(token, str) or len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError("agent bearer token must be at least 32 ASCII characters without whitespace")
    if not 0 < auth_lifetime_seconds <= 86400:
        raise ValueError("bearer lifetime must be positive and at most 24 hours")
    sdk = Server("moraine-email-pilot")

    @sdk.list_tools()
    async def list_tools():
        return [types.Tool(name=name, description=f"Scoped email pilot operation: {name}.",
                           inputSchema=_schema(fields)) for name, fields in FIELDS.items()]

    @sdk.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        if time.monotonic() >= boundary.expires_at:
            return _error("unauthorized")
        fields = FIELDS.get(name)
        if fields is None or not isinstance(arguments, dict) or set(arguments) != set(fields):
            return _error("invalid_tool_arguments")
        for field, kind in fields.items():
            value = arguments[field]
            if type(value) is not kind:
                return _error("invalid_tool_arguments")
            if kind is int and value < 1:
                return _error("invalid_tool_arguments")
            if kind is str:
                try:
                    length = len(value.encode("utf-8"))
                except UnicodeError:
                    return _error("invalid_tool_arguments")
                if not length or length > (16384 if field == "body_text" else 128):
                    return _error("invalid_tool_arguments")
        try:
            method = getattr(broker, name)
            action = partial(method, agent, arguments) if name == "propose_reply" else partial(method, agent, **arguments)
            def guarded_action():
                # The pool and broker can each queue work. Check under the
                # broker's reentrant operation lock immediately before dispatch.
                with broker.lock:
                    if time.monotonic() >= boundary.expires_at:
                        raise PilotError("unauthorized", status=401)
                    return action()

            return await anyio.to_thread.run_sync(guarded_action)
        except PilotError as exc:
            return _error(exc.reason)
        except Exception:
            return _error("internal_error")

    manager = StreamableHTTPSessionManager(
        app=sdk, json_response=True, stateless=True, max_request_body_size=MAX_BODY,
        security_settings=TransportSecuritySettings(enable_dns_rebinding_protection=True,
            allowed_hosts=[f"127.0.0.1:{port}", f"localhost:{port}"],
            allowed_origins=[f"http://127.0.0.1:{port}", f"http://localhost:{port}"]))

    @asynccontextmanager
    async def lifespan(app):
        async with manager.run():
            yield

    class Endpoint:
        async def __call__(self, scope, receive, send):
            await manager.handle_request(scope, receive, send)

    app = Starlette(routes=[Route("/mcp", Endpoint(), methods=["GET", "POST", "DELETE"])], lifespan=lifespan)
    boundary = _Boundary(app, token, port, auth_lifetime_seconds)
    return boundary
