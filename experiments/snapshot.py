"""Freeze reviewable source and documentation when no Git baseline is available."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tarfile

from run_campaign import ROOT, source_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("label", help="Unique local evidence directory name")
    args = parser.parse_args()
    if not args.label or Path(args.label).name != args.label or args.label in {".", ".."}:
        parser.error("label must be a single directory name")
    output = ROOT / "experiments/results" / args.label
    output.mkdir(parents=True, exist_ok=False)
    manifest = source_manifest()
    for path in sorted((ROOT / "docs/experiments").rglob("*.md")):
        manifest[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    archive = output / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for relative in sorted(manifest):
            bundle.add(ROOT / relative, arcname=relative, recursive=False)
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Source/docs only; excludes local environments, caches, binaries, state and evidence.",
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": dict(sorted(manifest.items())),
    }
    (output / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Snapshot: {output}")


if __name__ == "__main__":
    main()
