from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from .models import Article, FeedSource


class FeedError(RuntimeError):
    pass


def load_sources(path: Path) -> list[FeedSource]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FeedError(f"cannot read feed configuration: {error}") from error
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise FeedError("configuration must contain a sources list")
    return [FeedSource(**source) for source in sources]


def fetch_feed(source: FeedSource, timeout: float = 10.0) -> bytes:
    request = urllib.request.Request(
        source.url,
        headers={"User-Agent": "daily-news-analyst/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except OSError as error:
        raise FeedError(f"{source.name}: {error}") from error


def _text(element: ET.Element, *names: str) -> str:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] in names and child.text:
            return " ".join(child.text.split())
    return ""


def _link(element: ET.Element) -> str:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == "link":
            return child.attrib.get("href", "") or (child.text or "").strip()
    return ""


def parse_feed(content: bytes, source: FeedSource) -> list[Article]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise FeedError(f"{source.name}: invalid XML: {error}") from error

    articles = []
    for entry in root.iter():
        if entry.tag.rsplit("}", 1)[-1] not in {"item", "entry"}:
            continue
        title = _text(entry, "title")
        url = _link(entry)
        if not title or not url:
            continue
        date_text = _text(entry, "pubDate", "published", "updated")
        try:
            published = parsedate_to_datetime(date_text)
        except (TypeError, ValueError):
            try:
                published = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
            except ValueError:
                published = datetime.now(timezone.utc)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        articles.append(Article(
            title=title,
            url=url,
            source=source.name,
            category=source.category,
            published_at=published,
            summary=_text(entry, "description", "summary"),
        ))
    return articles
