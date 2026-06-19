#!/usr/bin/env python3
"""Report legal-content review status for public resources."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEDULE = ROOT / "content_review.json"


def parse_date(value: str, field: str, page: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{page}: {field} must be YYYY-MM-DD, got {value!r}") from exc


def expected_pages() -> set[str]:
    pages = {p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "resources").glob("*.html"))}
    pages.add("insights/fixing-michigans-fragmented-e-filing.html")
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description="Check content-review schedule freshness.")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="Date for stale checks, YYYY-MM-DD.")
    args = parser.parse_args()

    as_of = parse_date(args.as_of, "--as-of", "command line")
    data = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    items = data.get("items", {})

    expected = expected_pages()
    configured = set(items)
    missing = sorted(expected - configured)
    extra = sorted(configured - expected)

    stale: list[tuple[str, date, str]] = []
    invalid: list[str] = []

    for page, meta in sorted(items.items()):
        try:
            parse_date(meta.get("lastReviewed", ""), "lastReviewed", page)
            due = parse_date(meta.get("nextReviewDue", ""), "nextReviewDue", page)
        except ValueError as exc:
            invalid.append(str(exc))
            continue
        owner = meta.get("owner") or data.get("defaultOwner") or ""
        if not owner:
            invalid.append(f"{page}: owner is required")
        if due < as_of:
            stale.append((page, due, owner))

    print(f"Content review schedule as of {as_of.isoformat()}")
    print(f"Tracked pages: {len(configured)}")
    print(f"Expected pages: {len(expected)}")
    print(f"Missing metadata: {len(missing)}")
    print(f"Extra metadata: {len(extra)}")
    print(f"Stale pages: {len(stale)}")

    if missing:
        print("\nMissing:")
        for page in missing:
            print(f"  - {page}")
    if extra:
        print("\nExtra:")
        for page in extra:
            print(f"  - {page}")
    if invalid:
        print("\nInvalid:")
        for message in invalid:
            print(f"  - {message}")
    if stale:
        print("\nPast due:")
        for page, due, owner in stale:
            print(f"  - {page} due {due.isoformat()} owner {owner}")

    return 1 if missing or extra or invalid or stale else 0


if __name__ == "__main__":
    sys.exit(main())
