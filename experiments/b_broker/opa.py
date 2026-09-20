"""A supervised real OPA process on a private authenticated Unix socket."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import httpx
from bootstrap import verify, ROOT


class PolicyFailure(Exception):
    def __init__(self, reason="policy_unavailable"):
        self.reason = reason
        super().__init__(reason)


class OPA:
    def __init__(self, policy: Path | None = None):
        self.binary = verify()
        policy = policy or ROOT / "policy/broker.rego"
        auth = ROOT / "policy/system_authz.rego"
        self.revision = hashlib.sha256(policy.read_bytes() + auth.read_bytes()).hexdigest()
        checked = subprocess.run([str(self.binary), "check", "--strict", str(policy), str(auth)],
                                 capture_output=True)
        if checked.returncode:
            raise PolicyFailure("policy_invalid")
        self.directory = tempfile.TemporaryDirectory(prefix="moraine-b-opa-")
        self.socket = str(Path(self.directory.name) / "opa.sock")
        self.token = secrets.token_urlsafe(48)
        auth_data = Path(self.directory.name) / "auth.json"
        auth_data.write_text(json.dumps({"broker_private": {"token": self.token}}))
        auth_data.chmod(0o600)
        self.process = subprocess.Popen([
            str(self.binary), "run", "--server", "--addr", "unix://" + self.socket,
            "--authentication=token", "--authorization=basic", "--disable-telemetry",
            "--log-level=error", str(policy), str(auth), str(auth_data),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.client = httpx.Client(transport=httpx.HTTPTransport(uds=self.socket, retries=0),
                                   base_url="http://opa", trust_env=False, timeout=2,
                                   follow_redirects=False,
                                   headers={"Authorization": "Bearer " + self.token})

    def wait_ready(self):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise PolicyFailure()
            if self.healthy():
                return
            time.sleep(0.05)
        raise PolicyFailure("policy_not_ready")

    def healthy(self):
        try:
            if self.process.poll() is not None or self.client.get("/health").status_code != 200:
                return False
            return self.decide({}) == {"decision": "deny", "reason": "scope_denied"}
        except (PolicyFailure, httpx.HTTPError):
            return False

    def decide(self, facts):
        if self.process.poll() is not None:
            raise PolicyFailure()
        try:
            response = self.client.post("/v1/data/broker/decision?strict-builtin-errors=true",
                                        json={"input": facts})
            if response.status_code != 200:
                raise PolicyFailure()
            result = response.json().get("result")
        except (httpx.HTTPError, ValueError, AttributeError) as error:
            raise PolicyFailure() from error
        allowed = {("deny", "scope_denied"), ("allow", "authorized"),
                   ("allow", "approved"), ("review", "requires_approval")}
        if (not isinstance(result, dict) or set(result) != {"decision", "reason"}
                or not isinstance(result["decision"], str) or not isinstance(result["reason"], str)
                or (result["decision"], result["reason"]) not in allowed):
            raise PolicyFailure("policy_invalid_result")
        return result

    def close(self):
        self.client.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.directory.cleanup()
