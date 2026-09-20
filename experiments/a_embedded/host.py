"""Benchmark host adapter: fixture authentication, loopback HTTP, one gate loop."""
from __future__ import annotations

import argparse
import asyncio
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys

from pydantic import ValidationError

from gate import ExecutionGate, Refusal, canonical
from models import Approval, Empty, Principal, Submission
from provider import ProviderClient


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate field")
        value[key] = item
    return value


class Host(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, gate, tokens, loop):
        self.gate, self.tokens, self.loop = gate, tokens, loop
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    server: Host

    def log_message(self, *_):
        pass

    def reply(self, status, payload):
        body = canonical(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authenticate(self):
        fields = self.headers.get_all("Authorization", [])
        if len(fields) != 1:
            raise Refusal("invalid_credential", 401)
        supplied = fields[0]
        for token, actor in self.server.tokens.items():
            if hmac.compare_digest(supplied, "Bearer " + token):
                return actor
        raise Refusal("invalid_credential", 401)

    def body(self):
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or self.headers.get("Transfer-Encoding"):
            raise Refusal("invalid_body", 400)
        try:
            size = int(lengths[0])
            if not 0 < size <= 1024 * 1024:
                raise ValueError("invalid body size")
            body = json.loads(self.rfile.read(size), object_pairs_hook=unique_object,
                              parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite")))
            if not isinstance(body, dict):
                raise ValueError("body must be object")
            return body
        except (ValueError, UnicodeError, TypeError):
            raise Refusal("invalid_body", 400) from None

    def dispatch(self, method):
        if method == "GET" and self.path == "/health":
            return 200, {"status": "ok", "approach": "embedded-apparitor-cedar"}
        actor = self.authenticate()
        gate = self.server.gate
        body = self.body() if method == "POST" else None
        if method == "POST" and self.path == "/grants":
            future = gate.create_grant(actor, body)
            status = 201
        elif method == "POST" and self.path == "/requests":
            value = Submission.model_validate(body)
            future = gate.submit(actor, value.grant_id, value.idempotency_key, value.action.model_dump())
            status = 200
        elif match := re.fullmatch(r"/grants/([A-Za-z0-9-]+)/revoke", self.path):
            if method != "POST":
                raise Refusal("not_found", 404)
            Empty.model_validate(body)
            future = gate.revoke(actor, match[1])
            status = 200
        elif match := re.fullmatch(r"/requests/([A-Za-z0-9-]+)/approve", self.path):
            if method != "POST":
                raise Refusal("not_found", 404)
            value = Approval.model_validate(body)
            future = gate.approve(actor, match[1], value.action_digest)
            status = 200
        elif method == "GET" and (match := re.fullmatch(r"/requests/([A-Za-z0-9-]+)", self.path)):
            future = gate.inspect(actor, match[1])
            status = 200
        else:
            raise Refusal("not_found", 404)
        # Never cancel a committed dispatch on client disconnect or thread timeout.
        result = asyncio.run_coroutine_threadsafe(future, self.server.loop).result()
        if result.get("state") == "denied":
            status = 403
        elif result.get("state") == "failed":
            status = 502
        return status, result

    def handle_method(self, method):
        try:
            status, result = self.dispatch(method)
        except Refusal as exc:
            status, result = exc.status, {"error": exc.reason}
        except ValidationError:
            status, result = 400, {"error": "invalid_input"}
        except Exception:
            # An unexpected failure must not disclose credentials or announce success.
            status, result = 500, {"error": "internal_error"}
        try:
            self.reply(status, result)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self.handle_method("GET")

    def do_POST(self):
        self.handle_method("POST")


async def serve(args):
    supplied = [args.agent_token, args.other_agent_token, args.human_token, args.provider_token]
    if any(not token or not token.isascii() or any(c.isspace() for c in token) for token in supplied) or len(set(supplied)) != 4:
        raise ValueError("fixture credentials must be distinct nonempty ASCII tokens")
    tokens = {
        args.agent_token: Principal(kind="agent", id="agent:alice", account="alice"),
        args.other_agent_token: Principal(kind="agent", id="agent:bob", account="bob"),
        args.human_token: Principal(kind="human", id="human:alice", account="alice"),
    }
    provider = ProviderClient(args.provider_url, args.provider_token)
    gate = ExecutionGate(args.state_dir, provider)
    try:
        await provider.ready()
        host = Host(args.port, gate, tokens, asyncio.get_running_loop())
        try:
            await asyncio.to_thread(host.serve_forever)
        finally:
            host.server_close()
    finally:
        await gate.aclose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    for name in ("provider-url", "provider-token", "agent-token", "other-agent-token", "human-token"):
        parser.add_argument("--" + name, required=True)
    # A synthetic opaque token can begin with '-'. Preserve the documented
    # separate-argument interface without argparse interpreting it as an option.
    argv, normalized, index = sys.argv[1:], [], 0
    value_options = {"--provider-token", "--agent-token", "--other-agent-token", "--human-token"}
    while index < len(argv):
        if argv[index] in value_options and index + 1 < len(argv):
            normalized.append(argv[index] + "=" + argv[index + 1])
            index += 2
        else:
            normalized.append(argv[index])
            index += 1
    asyncio.run(serve(parser.parse_args(normalized)))


if __name__ == "__main__":
    main()
