from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher

from .models import Article, Story


WORDS = re.compile(r"[0-9A-Za-z가-힣]{2,}")
STOP_WORDS = {"the", "and", "for", "from", "with", "that", "this", "news", "대한", "관련"}


def tokens(title: str) -> set[str]:
    return {word.lower() for word in WORDS.findall(title) if word.lower() not in STOP_WORDS}


def similarity(left: str, right: str) -> float:
    a, b = tokens(left), tokens(right)
    if not a or not b:
        return 0.0
    overlap = len(a & b) / len(a | b)
    sequence = SequenceMatcher(None, " ".join(sorted(a)), " ".join(sorted(b))).ratio()
    return max(overlap, sequence)


def rank_stories(articles: list[Article], now: datetime | None = None) -> list[Story]:
    now = now or datetime.now(timezone.utc)
    groups: list[list[Article]] = []
    for article in sorted(articles, key=lambda item: item.published_at, reverse=True):
        group = next((items for items in groups if similarity(article.title, items[0].title) >= 0.82), None)
        (group.append(article) if group is not None else groups.append([article]))

    stories = []
    for group in groups:
        newest = max(group, key=lambda item: item.published_at)
        source_count = len({item.source for item in group})
        age_hours = max(0.0, (now - newest.published_at).total_seconds() / 3600)
        score = source_count * 5 + max(0.0, 3 - age_hours / 16)
        counts = Counter(word for item in group for word in tokens(item.title))
        stories.append(Story(newest.title, tuple(group), tuple(word for word, _ in counts.most_common(5)), round(score, 2)))
    return sorted(stories, key=lambda story: story.score, reverse=True)
