#!/usr/bin/env python3
"""Static QA checks for tomcedoz.com."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag

ROOT = Path(__file__).resolve().parent
DOMAIN = "https://tomcedoz.com/"

PRIVATE_DIST_PATHS = [
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


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.labels: dict[str, str] = {}
        self._label_for: str | None = None
        self._label_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k: v or "" for k, v in attrs}
        self.tags.append((tag, data))
        if tag == "label":
            self._label_for = data.get("for")
            self._label_text = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {k: v or "" for k, v in attrs}))

    def handle_endtag(self, tag: str) -> None:
        if tag == "label" and self._label_for:
            self.labels[self._label_for] = " ".join("".join(self._label_text).split())
            self._label_for = None
            self._label_text = []

    def handle_data(self, data: str) -> None:
        if self._label_for:
            self._label_text.append(data)


def html_files(base: Path = ROOT) -> list[Path]:
    return sorted(base.glob("*.html")) + sorted((base / "resources").glob("*.html")) + sorted((base / "insights").glob("*.html"))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def has_json_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(has_json_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(has_json_key(child, key) for child in value)
    return False


def check_pages(errors: list[str]) -> None:
    files = html_files()
    known = {p.resolve() for p in files}

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)

        if len(re.findall(r"<title>.*?</title>", text, re.S | re.I)) != 1:
            fail(errors, f"{rel}: expected exactly one title")
        if len(re.findall(r"<h1\b", text, re.I)) != 1:
            fail(errors, f"{rel}: expected exactly one h1")
        if "FAQPage" in text:
            fail(errors, f"{rel}: hidden FAQPage structured data remains")
        if re.search(r'<meta\s+name="keywords"', text, re.I):
            fail(errors, f"{rel}: meta keywords tag remains")
        if "style=" in text:
            fail(errors, f"{rel}: inline style attribute remains")
        if "onclick=" in text or "window.print()" in text:
            fail(errors, f"{rel}: inline print handler remains")
        if "fonts.googleapis" in text or "fonts.gstatic" in text:
            fail(errors, f"{rel}: third-party font request remains")

        for attrs, _body in re.findall(r"<script(?![^>]*src=)([^>]*)>(.*?)</script>", text, re.S | re.I):
            if "application/ld+json" not in attrs:
                fail(errors, f"{rel}: inline executable script remains")

        head = text.split("</head>", 1)[0]
        meta_counts: dict[str, int] = {}
        for match in re.finditer(r"<meta\s+([^>]+)>", head, re.I):
            attrs = match.group(1)
            key = None
            for attr in ("name", "property"):
                found = re.search(attr + r'="([^"]+)"', attrs, re.I)
                if found:
                    key = f"{attr}:{found.group(1)}"
                    break
            if key:
                meta_counts[key] = meta_counts.get(key, 0) + 1
        for key, count in meta_counts.items():
            if count > 1:
                fail(errors, f"{rel}: duplicate meta {key}")

        for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError as exc:
                fail(errors, f"{rel}: invalid JSON-LD: {exc}")
                continue
            if has_json_key(data, "keywords"):
                fail(errors, f"{rel}: JSON-LD keywords remain")

        for tag, attrs in parser.tags:
            if tag == "a":
                href = attrs.get("href", "")
                if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")) or re.match(r"^https?://", href):
                    continue
                target = urldefrag(href)[0]
                if target and not (path.parent / target).resolve().exists():
                    fail(errors, f"{rel}: broken internal link {href}")
            elif tag == "img":
                if not attrs.get("alt"):
                    fail(errors, f"{rel}: image missing alt text")
                if not attrs.get("width") or not attrs.get("height"):
                    fail(errors, f"{rel}: image missing width/height")
            elif tag == "input":
                input_id = attrs.get("id")
                if not input_id or (input_id not in parser.labels and not attrs.get("aria-label") and not attrs.get("aria-labelledby")):
                    fail(errors, f"{rel}: input missing accessible label")

        if "The choice of a lawyer is an important decision and should not be based solely upon advertisements." not in text:
            fail(errors, f"{rel}: required advertising decision language missing")
        if "does not create an attorney-client relationship" not in text:
            fail(errors, f"{rel}: attorney-client disclaimer missing")
        if "class=\"btn-print\"" in text and "class=\"print-legal\"" not in text:
            fail(errors, f"{rel}: printable page missing print legal block")
        if rel == "resources.html":
            for target in ("#g-ai", "#g-employment", "#g-commercial", "#g-cross"):
                if f'href="{target}"' not in text or f'id="{target[1:]}"' not in text:
                    fail(errors, f"{rel}: category jump link target missing {target}")
        if rel.startswith(("resources/", "insights/")) and 'class="crumbs"' not in text:
            fail(errors, f"{rel}: visible breadcrumb missing")

    if not known:
        fail(errors, "no HTML files found")


def check_sitemap(errors: list[str]) -> None:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        fail(errors, "sitemap.xml missing")
        return

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = {node.find("sm:loc", ns).text for node in ET.parse(sitemap).getroot().findall("sm:url", ns)}
    expected = set()
    for path in html_files():
        rel = path.relative_to(ROOT).as_posix()
        expected.add(DOMAIN if rel == "index.html" else DOMAIN + rel)

    missing = sorted(expected - urls)
    extra = sorted(urls - expected)
    for loc in missing:
        fail(errors, f"sitemap missing {loc}")
    for loc in extra:
        fail(errors, f"sitemap has unexpected URL {loc}")


def check_dist(errors: list[str]) -> None:
    dist = ROOT / "dist"
    if not dist.exists():
        return
    for rel in PRIVATE_DIST_PATHS:
        if (dist / rel).exists():
            fail(errors, f"dist contains private path {rel}")
    for rel in ["_headers", "assets/site.js"]:
        if not (dist / rel).exists():
            fail(errors, f"dist missing {rel}")


def check_headers(errors: list[str]) -> None:
    headers = ROOT / "_headers"
    if not headers.exists():
        fail(errors, "_headers missing")
        return
    text = headers.read_text(encoding="utf-8")
    required = [
        "Content-Security-Policy:",
        "script-src 'self'",
        "style-src 'self'",
        "Referrer-Policy: strict-origin-when-cross-origin",
        "X-Content-Type-Options: nosniff",
        "Permissions-Policy:",
    ]
    for value in required:
        if value not in text:
            fail(errors, f"_headers missing {value}")
    if "'unsafe-inline'" in text:
        fail(errors, "_headers still permits unsafe-inline")


def check_dates(errors: list[str]) -> None:
    review_path = ROOT / "content_review.json"
    if not review_path.exists():
        fail(errors, "content_review.json missing")
        return
    items = json.loads(review_path.read_text(encoding="utf-8")).get("items", {})

    for rel, meta in items.items():
        path = ROOT / rel
        if not path.exists():
            fail(errors, f"review metadata references missing page {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        modified = re.search(r'"dateModified":\s*"([^"]+)"', text)
        if not modified:
            fail(errors, f"{rel}: JSON-LD dateModified missing")
        elif modified.group(1) != meta.get("lastReviewed"):
            fail(errors, f"{rel}: dateModified does not match content_review.json")

    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return
    xml = sitemap.read_text(encoding="utf-8")
    for rel, meta in items.items():
        loc = DOMAIN + rel
        pattern = re.escape(f"<loc>{loc}</loc>") + r"\s*<lastmod>([^<]+)</lastmod>"
        found = re.search(pattern, xml)
        if not found:
            fail(errors, f"sitemap missing reviewed URL {loc}")
        elif found.group(1) != meta.get("lastReviewed"):
            fail(errors, f"sitemap lastmod for {rel} does not match content_review.json")


def main() -> int:
    errors: list[str] = []
    check_pages(errors)
    check_sitemap(errors)
    check_dist(errors)
    check_headers(errors)
    check_dates(errors)

    if errors:
        print(f"Static QA failed: {len(errors)} issue(s)")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Static QA passed")
    print(f"Checked {len(html_files())} HTML files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
