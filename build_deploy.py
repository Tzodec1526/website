#!/usr/bin/env python3
"""Build the public deploy directory from an explicit allowlist.

This repository contains private working files alongside the public static site.
Run this script before uploading to a static host, then deploy only ./dist.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

PUBLIC_ROOT_FILES = [
    "index.html",
    "resources.html",
    "insights.html",
    "how-i-work.html",
    "contact.html",
    "privacy.html",
    "robots.txt",
    "sitemap.xml",
    "llms.txt",
]

PUBLIC_DIR_PATTERNS = {
    "assets": ["*"],
    "resources": ["*.html"],
    "insights": ["*.html"],
}

OPTIONAL_ROOT_FILES = [
    "_headers",
]

PRIVATE_PATHS = [
    "Writing",
    "review",
    "logo",
    ".claude",
    "HH_60799955_Tom_Cedoz.jpg",
    "WEBSITE_BACKLOG.md",
    "LAUNCH_REVIEW_PACKET.md",
    "ad-records",
    "resources/_data",
    "seo",
    "__pycache__",
]


def make_writable(path: Path) -> None:
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    except FileNotFoundError:
        pass


def copy_file(src: Path, dest: Path) -> None:
    if not src.is_file():
        raise FileNotFoundError(f"Missing required public file: {src.relative_to(ROOT)}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        make_writable(dest)
    shutil.copy2(src, dest)


def clean_stale_files(allowed: set[Path]) -> None:
    if not DIST.exists():
        return

    for path in sorted(DIST.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        rel = path.relative_to(DIST)
        if path.is_file() and rel not in allowed:
            make_writable(path)
            path.unlink()
        elif path.is_dir():
            try:
                make_writable(path)
                path.rmdir()
            except OSError:
                pass


def build(clean: bool) -> list[Path]:
    DIST.mkdir(exist_ok=True)

    copied: list[Path] = []
    allowed: set[Path] = set()

    for rel in PUBLIC_ROOT_FILES:
        src = ROOT / rel
        dest = DIST / rel
        copy_file(src, dest)
        copied.append(dest)
        allowed.add(Path(rel))

    for rel in OPTIONAL_ROOT_FILES:
        src = ROOT / rel
        if src.exists():
            dest = DIST / rel
            copy_file(src, dest)
            copied.append(dest)
            allowed.add(Path(rel))

    for directory, patterns in PUBLIC_DIR_PATTERNS.items():
        src_dir = ROOT / directory
        if not src_dir.is_dir():
            raise FileNotFoundError(f"Missing required public directory: {directory}")
        for pattern in patterns:
            for src in sorted(src_dir.glob(pattern)):
                if src.is_file():
                    dest = DIST / src.relative_to(ROOT)
                    copy_file(src, dest)
                    copied.append(dest)
                    allowed.add(dest.relative_to(DIST))

    if clean:
        clean_stale_files(allowed)

    leaked = [rel for rel in PRIVATE_PATHS if (DIST / rel).exists()]
    if leaked:
        joined = ", ".join(leaked)
        raise RuntimeError(f"Private paths were copied into dist: {joined}")

    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the public deploy allowlist into ./dist.")
    parser.add_argument("--no-clean", action="store_true", help="Do not clear dist before copying.")
    args = parser.parse_args()

    copied = build(clean=not args.no_clean)
    print(f"Wrote {len(copied)} public files to {DIST.relative_to(ROOT)}")
    for path in copied:
        print(path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
