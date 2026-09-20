"""Loopback fixture authentication and thin exact-shape HTTP boundary."""
from __future__ import annotations

import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re

from actions import Refusal, canonical
from executor import Executor


def unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def invalid_constant(value: str) -> None:
    raise ValueError("nonfinite JSON")


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, executor: Executor, tokens: dict[str, str]):
        if len(set(tokens.values())) != len(tokens) or any(not token for token in tokens.values()):
            raise ValueError("fixture identities need distinct nonempty bearer tokens")
        self.executor, self.tokens = executor, tokens
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    server: Server

    def log_message(self, *_: object) -> None:
        pass

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)

    def reply(self, status: int, value: dict) -> None:
        data = canonical(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def actor(self) -> str:
        headers = self.headers.get_all("Authorization", [])
        if len(headers) == 1:
            for actor, token in self.server.tokens.items():
                if hmac.compare_digest(headers[0].encode(), ("Bearer " + token).encode()):
                    return actor
        raise Refusal("authentication_required", 401)

    def body(self) -> dict:
        try:
            if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
                raise ValueError("ambiguous framing")
            length = int(self.headers["Content-Length"])
            if not 0 < length <= 1024 * 1024:
                raise ValueError("body size")
            data = self.rfile.read(length)
            if len(data) != length:
                raise ValueError("incomplete body")
            value = json.loads(data, object_pairs_hook=unique_object, parse_constant=invalid_constant)
            if not isinstance(value, dict):
                raise ValueError("non-object")
            return value
        except (ValueError, UnicodeDecodeError, TimeoutError, RecursionError):
            raise Refusal("invalid_json") from None

    def do_GET(self) -> None:
        try:
            if self.path == "/health":
                self.reply(200, {"status": "ok", "approach": "real-biscuit-capability"})
                return
            actor = self.actor()
            match = re.fullmatch(r"/requests/(request-[a-f0-9]{32})", self.path)
            if not match:
                raise Refusal("not_found", 404)
            self.reply(200, self.server.executor.get(actor, match[1]))
        except Refusal as error:
            self.reply(error.status, {"error": error.reason})

    def do_POST(self) -> None:
        try:
            actor = self.actor()
            body = self.body()
            executor = self.server.executor
            if self.path == "/grants":
                self.reply(201, executor.create_grant(actor, body))
            elif self.path == "/requests":
                self.reply(200, executor.submit(actor, body))
            elif match := re.fullmatch(r"/grants/(grant-[a-f0-9]{32})/revoke", self.path):
                self.reply(200, executor.revoke(actor, match[1], body))
            elif match := re.fullmatch(r"/requests/(request-[a-f0-9]{32})/approve", self.path):
                self.reply(200, executor.approve(actor, match[1], body))
            else:
                raise Refusal("not_found", 404)
        except Refusal as error:
            self.reply(error.status, {"error": error.reason})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--state-dir", required=True, type=Path)
    for flag in ("provider-url", "provider-token", "agent-token", "other-agent-token", "human-token"):
        parser.add_argument("--" + flag, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    executor = Executor(args.state_dir, args.provider_url, args.provider_token)
    server = Server(args.port, executor, {"agent:alice": args.agent_token,
                                        "agent:bob": args.other_agent_token, "human:alice": args.human_token})
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        executor.close()


if __name__ == "__main__":
    main()
