"""python -m lab serve --state-dir /tmp/moraine-lab-unique"""
import argparse
from pathlib import Path
import signal
import sys

from .runtime import Laboratory
from .server import Console
from .scenarios import SCENARIOS, run_suite


def main():
    parser = argparse.ArgumentParser(description="Moraine local-only end-to-end laboratory")
    parser.add_argument("command", choices=["serve", "run"])
    parser.add_argument("--state-dir", type=Path, required=True, help="New private directory outside the repository; must not already exist")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--scenario", choices=SCENARIOS, action="append", help="Repeat to select scenarios; default: all")
    args = parser.parse_args()
    lab = Laboratory(args.state_dir)
    server = None

    def terminate(*_):
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, terminate)
    try:
        if args.command == "run":
            report = run_suite(lab, args.scenario or SCENARIOS)
            print(f"Campaign {report['status']}: {lab.directory / 'campaign.json'}", flush=True)
            return 0 if report["status"] == "passed" else 1
        lab.new()
        server = Console(lab, args.port)
        print(f"Moraine local console: {server.origin}", flush=True)
        print(f"Private connection details: {lab.directory / 'connection.json'}", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        if server:
            server.close()
        else:
            lab.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
