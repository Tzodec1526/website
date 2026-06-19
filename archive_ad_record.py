#!/usr/bin/env python3
"""Archive the current public deploy output for advertising-record retention."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
OUT = ROOT / "ad-records"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def public_files() -> list[Path]:
    if not DIST.exists():
        raise SystemExit("dist/ does not exist. Run python build_deploy.py first.")
    return sorted(p for p in DIST.rglob("*") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a two-year advertising record for the current dist/ output."
    )
    parser.add_argument(
        "--where",
        default="https://tomcedoz.com/",
        help="Where this advertising communication was or will be disseminated.",
    )
    parser.add_argument(
        "--when",
        default=None,
        help="ISO date/time of dissemination. Defaults to the current local time.",
    )
    args = parser.parse_args()

    created = datetime.fromisoformat(args.when) if args.when else datetime.now().astimezone()
    stamp = created.strftime("%Y%m%d-%H%M%S%z")
    OUT.mkdir(exist_ok=True)

    files = public_files()
    archive_base = OUT / f"{stamp}-tomcedoz-com"
    zip_path = archive_base.with_suffix(".zip")
    manifest_path = archive_base.with_suffix(".json")

    manifest = {
        "schemaVersion": 1,
        "createdAt": created.isoformat(),
        "disseminationLocation": args.where,
        "sourceDirectory": "dist",
        "retentionMinimumYears": 2,
        "retainUntil": (created + timedelta(days=365 * 2)).date().isoformat(),
        "fileCount": len(files),
        "files": [
            {
                "path": path.relative_to(DIST).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(DIST).as_posix())

    print(f"Wrote advertising record manifest: {manifest_path.relative_to(ROOT)}")
    print(f"Wrote deploy snapshot archive: {zip_path.relative_to(ROOT)}")
    print(f"Retain until at least: {manifest['retainUntil']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
