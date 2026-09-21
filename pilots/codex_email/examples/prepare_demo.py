"""Create fresh SYNTHETIC demo inputs only. Refuse to overwrite any directory."""
import argparse
import json
from pathlib import Path
import secrets
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path)
args = parser.parse_args()
args.directory.mkdir(mode=0o700, parents=False, exist_ok=False)
for name in ("agent-token", "provider-token"):
    path = args.directory / name
    path.write_text(secrets.token_urlsafe(32))
    path.chmod(0o600)
(args.directory / "config.json").write_text(json.dumps({
    "agent": "agent:pilot", "owner": "human:owner", "account": "pilot@example.test"}))
body = {"kind": "reply", "agent": "agent:pilot", "account_id": "pilot@example.test", "expires_at": time.time() + 1800,
        "recipient": "correspondent@example.test", "reply_to_ref": "message-1",
        "resources": [{"resource_ref": "message-1", "provider_message_id": "upstream-1", "kind": "message",
                       "version": 1, "title": "Question du pilote", "text": "Peux-tu confirmer mardi ?",
                       "from_address": "correspondent@example.test", "reply_address": "correspondent@example.test",
                       "message_id": "<original@example.test>", "thread_id": "thread-1"}]}
(args.directory / "grant.json").write_text(json.dumps(body, ensure_ascii=False, indent=2))
print("Synthetic demo prepared; grant input expires in 30 minutes. No service started.")
