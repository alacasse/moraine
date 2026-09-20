"""Authenticated operator console on loopback, separate from the agent MCP facade."""
from __future__ import annotations

import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import socket
import threading
import uuid
from urllib.parse import urlsplit

from moraine_email.human_server import strict_json
from .runtime import Laboratory, LabError, write_json
from .scenarios import run_suite

STATIC = Path(__file__).with_name("static")
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8")}


class Console(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, lab, port=0):
        self.lab = lab
        self.token = secrets.token_urlsafe(32)
        self.campaign = None
        self.campaign_thread = None
        self.cancel = threading.Event()
        self.closing = False
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        connection = lab.directory / "connection.json"
        write_json(connection, {"url": self.origin, "operator_token": self.token,
                                 "launch_url": self.origin + "/#" + self.token})
        connection.chmod(0o600)

    def state(self):
        with self.lab.lock:
            return {"run": self.lab.current.snapshot() if self.lab.current else None,
                    "campaign": json.loads(json.dumps(self.campaign))}

    def start_campaign(self):
        if self.campaign_thread and self.campaign_thread.is_alive():
            raise LabError("campaign_already_running")
        directory = self.lab.directory / ("campaign-" + uuid.uuid4().hex[:12])
        self.campaign = {"status": "running", "actor": "scripted", "results": [], "directory": str(directory)}

        def progress(report):
            with self.lab.lock:
                self.campaign = {**json.loads(json.dumps(report)), "directory": str(directory)}

        def execute():
            campaign_lab = None
            try:
                campaign_lab = Laboratory(directory)
                run_suite(campaign_lab, progress=progress, cancel=self.cancel)
            except Exception as exc:
                with self.lab.lock:
                    self.campaign.update(status="failed", error=str(exc))
            finally:
                if campaign_lab:
                    campaign_lab.close()

        self.campaign_thread = threading.Thread(target=execute, name="local-campaign")
        self.campaign_thread.start()

    def close(self):
        with self.lab.lock:
            self.closing = True
            self.cancel.set()
        self.server_close()
        if self.campaign_thread:
            self.campaign_thread.join()  # Current bounded scenario finishes before shutdown.
        self.lab.close()

    def action(self, payload):
        with self.lab.lock:
            if self.closing:
                raise LabError("console_closing")
            if type(payload) is not dict or not {"action", "run_id"} <= payload.keys():
                raise LabError("invalid_action")
            name = payload["action"]
            fields = {"new": {"actor", "provider_mode"}, "propose": {"body"}}
            if not isinstance(name, str) or set(payload) - ({"action", "run_id"} | fields.get(name, set())):
                raise LabError("invalid_action")
            current = self.lab.current
            if payload["run_id"] != (current.id if current else None):
                raise LabError("stale_run")
            if name == "campaign":
                self.start_campaign()
                return self.state()
            if name == "new":
                self.lab.new(actor=payload.get("actor", "operator"), provider_mode=payload.get("provider_mode", "normal"))
                return self.state()
            if current is None or current.closed:
                raise LabError("no_active_run")
            operations = {"read": current.read, "review": current.review,
                          "approve": lambda: current.decide("approve"), "reject": lambda: current.decide("reject"),
                          "revoke": current.revoke, "restart": current.restart,
                          "refresh": current.refresh, "verify": current.verify_delivery,
                          "propose": lambda: current.propose(payload.get("body"))}
            if name not in operations:
                raise LabError("unknown_action")
            try:
                result = operations[name]()
                if isinstance(result, dict) and result.get("is_error"):
                    raise LabError("mcp_refused: " + "; ".join(result["content"]))
                current.error = None
            except Exception as exc:
                current.error = current.clean(str(exc))
                current.event("operator.error", {"action": name, "error": current.error})
                raise
            finally:
                current.save()
            return self.state()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(8)

    def log_message(self, *_):
        pass  # Never log credentials, query strings or request bodies.

    def respond(self, status, value, content_type="application/json; charset=utf-8"):
        raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(raw)

    def boundary(self, *, authenticate):
        for name in ("Host", "Authorization", "Origin", "Content-Length"):
            if len(self.headers.get_all(name, [])) > 1:
                self.respond(400, {"error": "duplicate_headers"})
                return False
        hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in hosts:
            self.respond(403, {"error": "invalid_host"})
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {"http://" + host for host in hosts}:
            self.respond(403, {"error": "invalid_origin"})
            return False
        if authenticate and not hmac.compare_digest(self.headers.get("Authorization", "").encode(), ("Bearer " + self.server.token).encode()):
            self.respond(401, {"error": "operator_authentication_required"})
            return False
        return True

    def do_GET(self):
        path = urlsplit(self.path)
        if not self.boundary(authenticate=path.path not in ASSETS):
            return
        if path.query:
            self.respond(400, {"error": "query_not_supported"})
        elif path.path in ASSETS:
            name, content_type = ASSETS[path.path]
            self.respond(200, (STATIC / name).read_bytes(), content_type)
        elif path.path == "/api/state":
            try:
                self.respond(200, self.server.state())
            except Exception:
                self.respond(500, {"error": "evidence_unreadable; inspect the private run directory"})
        else:
            self.respond(404, {"error": "not_found"})

    def do_POST(self):
        if not self.boundary(authenticate=True):
            return
        if self.path != "/api/action":
            self.respond(404, {"error": "not_found"})
            return
        try:
            if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Type") != "application/json":
                raise ValueError("invalid_body_headers")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 32768:
                raise ValueError("invalid_body_size")
            payload = strict_json(self.rfile.read(size))
            self.respond(200, self.server.action(payload))
        except socket.timeout:
            self.respond(408, {"error": "request_timeout"})
        except (ValueError, UnicodeError, RecursionError) as exc:
            self.respond(400, {"error": str(exc)[:300]})
        except LabError as exc:
            self.respond(409, {"error": str(exc)})
        except Exception:
            self.respond(500, {"error": "action_failed; inspect the run events and process logs"})
