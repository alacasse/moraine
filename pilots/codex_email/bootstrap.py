"""Acquire the pinned OPA artifact into this pilot only; never mutate experiments."""
import hashlib
import json
from pathlib import Path
import platform
import urllib.request

ROOT = Path(__file__).resolve().parent


def main():
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("Pilot requires Linux x86_64 for its pinned OPA artifact")
    pin = json.loads((ROOT / "dependencies.lock.json").read_text())["opa"]
    target = ROOT / ".tools/opa"
    if target.exists():
        content = target.read_bytes()
    else:
        with urllib.request.urlopen(pin["url"], timeout=30) as response:
            content = response.read()
    if hashlib.sha256(content).hexdigest() != pin["sha256"]:
        raise SystemExit("OPA checksum mismatch; refusing installation")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".download")
        temporary.write_bytes(content)
        temporary.chmod(0o700)
        temporary.replace(target)


if __name__ == "__main__":
    main()
