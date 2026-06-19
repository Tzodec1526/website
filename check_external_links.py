#!/usr/bin/env python3
"""Check external links used by the public static site."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SOFT_STATUS = {401, 403, 405, 429}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        data = dict(attrs)
        url = data.get("href")
        if url and url.startswith(("http://", "https://")):
            self.links.add(url)


def public_files() -> list[Path]:
    return (
        sorted(ROOT.glob("*.html"))
        + sorted((ROOT / "resources").glob("*.html"))
        + sorted((ROOT / "insights").glob("*.html"))
        + [ROOT / "llms.txt"]
    )


def collect_links() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    md_url = re.compile(r"https?://[^\s)<>\"]+")

    for path in public_files():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        links: set[str] = set()
        if path.suffix == ".html":
            parser = LinkParser()
            parser.feed(text)
            links.update(parser.links)
        else:
            links.update(match.group(0).rstrip(".,") for match in md_url.finditer(text))
        links = {url for url in links if urlparse(url).netloc not in {"tomcedoz.com", "www.tomcedoz.com"}}
        if links:
            found[path.relative_to(ROOT).as_posix()] = links
    return found


def request(url: str, timeout: float) -> tuple[str, int | None, str]:
    headers = {"User-Agent": "tomcedoz.com-link-check/1.0"}
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return ("ok", response.status, method)
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in {403, 405}:
                continue
            if exc.code in SOFT_STATUS:
                return ("soft", exc.code, method)
            return ("broken", exc.code, method)
        except urllib.error.URLError as exc:
            return ("error", None, str(exc.reason))
        except TimeoutError:
            return ("error", None, "timeout")
    return ("error", None, "unreachable")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check external links.")
    parser.add_argument("--list-only", action="store_true", help="List links without network requests.")
    parser.add_argument("--timeout", type=float, default=8.0, help="Per-request timeout in seconds.")
    args = parser.parse_args()

    links_by_file = collect_links()
    all_links = sorted({url for links in links_by_file.values() for url in links})

    print(f"External links: {len(all_links)}")
    if args.list_only:
        for url in all_links:
            print(url)
        return 0

    broken: list[str] = []
    errors: list[str] = []
    soft: list[str] = []

    for url in all_links:
        status, code, detail = request(url, args.timeout)
        host = urlparse(url).netloc
        if status == "ok":
            print(f"ok {code} {host} {url}")
        elif status == "soft":
            soft.append(f"soft {code} {host} {url}")
        elif status == "broken":
            broken.append(f"broken {code} {host} {url}")
        else:
            errors.append(f"error {detail} {host} {url}")

    for line in soft:
        print(line)
    for line in broken + errors:
        print(line)

    if broken or errors:
        print(f"External link check failed: {len(broken)} broken, {len(errors)} errors, {len(soft)} soft")
        return 1

    print(f"External link check passed with {len(soft)} soft response(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
