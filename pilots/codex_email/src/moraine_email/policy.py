"""Verified OPA process, privately authenticated and fail closed (extracted from B)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import tempfile
import time

import httpx

OPA_SHA256 = "66fa66f3b730b2fb086003863428b382b2898d343adb4b5dfab5598b4d739eed"


class PolicyFailure(Exception):
    def __init__(self, reason="policy_unavailable"):
        self.reason = reason
        super().__init__(reason)


class OPA:
    def __init__(self, binary: Path, policy_dir: Path | None = None):
        self.binary = Path(binary).resolve(strict=True)
        with self.binary.open("rb") as binary_file:
            if hashlib.file_digest(binary_file, "sha256").hexdigest() != OPA_SHA256:
                raise PolicyFailure("policy_binary_unverified")
        directory = policy_dir or Path(__file__).with_name("policy")
        files = [directory / "broker.rego", directory / "system_authz.rego"]
        self.revision = hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()
        checked = subprocess.run([str(self.binary), "check", "--strict", *map(str, files)],
                                 capture_output=True, timeout=10, check=False)
        if checked.returncode:
            raise PolicyFailure("policy_invalid")
        self.directory = tempfile.TemporaryDirectory(prefix="moraine-pilot-opa-")
        self.socket = str(Path(self.directory.name) / "opa.sock")
        self.token = secrets.token_urlsafe(48)
        auth = Path(self.directory.name) / "auth.json"
        auth.write_text(json.dumps({"broker_private": {"token": self.token}}))
        auth.chmod(0o600)
        self.process = subprocess.Popen([
            str(self.binary), "run", "--server", "--addr", "unix://" + self.socket,
            "--authentication=token", "--authorization=basic", "--disable-telemetry",
            "--log-level=error", *map(str, files), str(auth),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.client = httpx.Client(transport=httpx.HTTPTransport(uds=self.socket, retries=0),
                                  base_url="http://opa", timeout=2, trust_env=False,
                                  follow_redirects=False,
                                  headers={"Authorization": "Bearer " + self.token})
        try:
            self.wait_ready()
        except BaseException:
            self.close()
            raise

    def wait_ready(self):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise PolicyFailure()
            try:
                if (self.client.get("/health").status_code == 200
                        and self.decide({}) == {"decision": "deny", "reason": "scope_denied"}):
                    return
            except (PolicyFailure, httpx.HTTPError):
                pass
            time.sleep(0.05)
        raise PolicyFailure("policy_not_ready")

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
                or not isinstance(result["decision"], str)
                or not isinstance(result["reason"], str)
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
