"""Offline public-key client; credentials read from stdin, result on stdout."""
import argparse
import json
import sys

from biscuit_auth import PublicKey

from actions import action_input, digest, integer
from capabilities import attenuate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-key", required=True)
    parser.add_argument("--max-amount", required=True, type=int)
    args = parser.parse_args()
    payload = json.load(sys.stdin)
    integer(args.max_amount)
    action_digest = digest(action_input(payload["action"])) if "action" in payload else None
    print(attenuate(payload["capability"], PublicKey(args.public_key), maximum=args.max_amount,
                    action_digest=action_digest))


if __name__ == "__main__":
    main()
