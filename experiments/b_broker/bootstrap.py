"""Acquire only the pinned official OPA binary; verify even on cached startup."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent
LOCK = json.loads((ROOT / "dependencies.lock.json").read_text())["opa"]
BINARY = ROOT / ".tools" / ("opa-" + LOCK["version"]) / "opa"


def verify() -> Path:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("This experiment pins the Linux x86_64 OPA artifact")
    if not BINARY.exists():
        BINARY.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(LOCK["url"], timeout=60) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != LOCK["sha256"]:
            raise RuntimeError("OPA download checksum mismatch")
        temporary = BINARY.with_suffix(".download")
        temporary.write_bytes(content)
        temporary.chmod(0o700)
        temporary.replace(BINARY)
    if hashlib.sha256(BINARY.read_bytes()).hexdigest() != LOCK["sha256"]:
        raise RuntimeError("OPA binary checksum mismatch")
    BINARY.chmod(0o700)
    version = subprocess.check_output([str(BINARY), "version"], text=True)
    if f"Version: {LOCK['version']}\n" not in version:
        raise RuntimeError("OPA version mismatch")
    return BINARY


if __name__ == "__main__":
    verify()
