from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    category: str = "general"
    language: str = "en"


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    source: str
    category: str
    published_at: datetime
    summary: str = ""


@dataclass(frozen=True)
class Story:
    title: str
    articles: tuple[Article, ...]
    keywords: tuple[str, ...]
    score: float

    @property
    def sources(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(article.source for article in self.articles))
