"""Extract a clean, auditable documentation corpus from saved Xbox Support HTML."""

from __future__ import annotations

import csv
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


SOURCE_DIR = Path("dataset/xbox_support_webpages")
CORPUS_PATH = SOURCE_DIR / "official_docs.jsonl"
LINKS_PATH = SOURCE_DIR / "discovered_help_links.csv"
WHITESPACE = re.compile(r"\s+")


class SupportPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self.canonical_url = ""
        self._in_title = False
        self._current_href: str | None = None
        self._current_link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "title":
            self._in_title = True
        elif tag == "link" and attributes.get("rel", "").casefold() == "canonical":
            self.canonical_url = attributes.get("href", "")
        elif tag == "a" and attributes.get("href"):
            self._current_href = attributes["href"] or ""
            self._current_link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._current_href is not None:
            self.links.append({"url": self._current_href, "anchor_text": clean(" ".join(self._current_link_text))})
            self._current_href = None
            self._current_link_text = []

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        value = clean(data)
        if not value:
            return
        self.text_parts.append(value)
        if self._in_title:
            self.title_parts.append(value)
        if self._current_href is not None:
            self._current_link_text.append(value)


def clean(value: str) -> str:
    return WHITESPACE.sub(" ", html.unescape(value)).strip()


def canonicalize_help_url(url: str) -> str | None:
    if not url.startswith("http"):
        return None
    parsed = urlsplit(url)
    if parsed.netloc.casefold() != "support.xbox.com" or "/help/" not in parsed.path.casefold():
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if parts and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]):
        parts = parts[1:]
    return urlunsplit(("https", "support.xbox.com", "/" + "/".join(parts), "", ""))


def page_kind(url: str, filename: str) -> str:
    if "/browse" in url or "_ XBOX Support.html" in filename:
        return "category_landing_page"
    return "article"


def main() -> None:
    source_files = sorted(SOURCE_DIR.glob("*.html"))
    if not source_files:
        raise FileNotFoundError(f"No saved HTML files found in {SOURCE_DIR}")

    corpus_records: list[dict[str, object]] = []
    discovered_links: dict[str, dict[str, str]] = {}
    for file_path in source_files:
        parser = SupportPageParser()
        parser.feed(file_path.read_text(encoding="utf-8", errors="replace"))
        title = clean(" ".join(parser.title_parts)) or file_path.stem.replace(" _ XBOX Support", "")
        canonical_url = canonicalize_help_url(parser.canonical_url)
        if not canonical_url:
            candidates = [canonicalize_help_url(link["url"]) for link in parser.links]
            canonical_url = next((candidate for candidate in candidates if candidate), "")
        help_links = []
        for link in parser.links:
            url = canonicalize_help_url(link["url"])
            if not url or url == canonical_url:
                continue
            record = {"source_file": file_path.name, "url": url, "anchor_text": link["anchor_text"]}
            help_links.append(record)
            discovered_links.setdefault(url, record)
        corpus_records.append(
            {
                "doc_id": file_path.stem,
                "title": title,
                "url": canonical_url,
                "page_kind": page_kind(canonical_url, file_path.name),
                "source_file": file_path.name,
                "text": " ".join(parser.text_parts),
                "linked_help_articles": len({link["url"] for link in help_links}),
            }
        )

    with CORPUS_PATH.open("w", encoding="utf-8") as file:
        for record in corpus_records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    with LINKS_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["source_file", "url", "anchor_text"])
        writer.writeheader()
        writer.writerows(sorted(discovered_links.values(), key=lambda item: item["url"]))

    category_count = sum(record["page_kind"] == "category_landing_page" for record in corpus_records)
    print(f"Wrote {len(corpus_records):,} cleaned documentation records to {CORPUS_PATH}.")
    print(f"Saved {len(discovered_links):,} unique linked Xbox Help URLs to {LINKS_PATH}.")
    print(f"Saved pages classified as category landing pages: {category_count:,}.")


if __name__ == "__main__":
    main()
