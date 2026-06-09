from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Article


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    published_at TEXT NOT NULL,
    summary TEXT NOT NULL,
    collected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_articles_published_at
ON articles(published_at);

CREATE TABLE IF NOT EXISTS collection_runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    fetched_count INTEGER NOT NULL DEFAULT 0,
    inserted_count INTEGER NOT NULL DEFAULT 0,
    story_count INTEGER NOT NULL DEFAULT 0,
    errors_json TEXT NOT NULL DEFAULT '[]'
);
"""


class NewsStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> NewsStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def start_run(self, started_at: datetime) -> int:
        cursor = self.connection.execute(
            "INSERT INTO collection_runs (started_at) VALUES (?)",
            (_utc_iso(started_at),),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def save_articles(
        self,
        articles: list[Article],
        *,
        collected_at: datetime,
    ) -> int:
        before = self.connection.total_changes
        self.connection.executemany(
            """
            INSERT OR IGNORE INTO articles (
                url, title, source, category, published_at, summary, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    article.url,
                    article.title,
                    article.source,
                    article.category,
                    _utc_iso(article.published_at),
                    article.summary,
                    _utc_iso(collected_at),
                )
                for article in articles
            ],
        )
        self.connection.commit()
        return self.connection.total_changes - before

    def recent_articles(self, since: datetime) -> list[Article]:
        rows = self.connection.execute(
            """
            SELECT title, url, source, category, published_at, summary
            FROM articles
            WHERE published_at >= ?
            ORDER BY published_at DESC
            """,
            (_utc_iso(since),),
        ).fetchall()
        return [
            Article(
                title=row["title"],
                url=row["url"],
                source=row["source"],
                category=row["category"],
                published_at=datetime.fromisoformat(row["published_at"]),
                summary=row["summary"],
            )
            for row in rows
        ]

    def finish_run(
        self,
        run_id: int,
        *,
        completed_at: datetime,
        fetched_count: int,
        inserted_count: int,
        story_count: int,
        errors: list[str],
    ) -> None:
        self.connection.execute(
            """
            UPDATE collection_runs
            SET completed_at = ?,
                fetched_count = ?,
                inserted_count = ?,
                story_count = ?,
                errors_json = ?
            WHERE id = ?
            """,
            (
                _utc_iso(completed_at),
                fetched_count,
                inserted_count,
                story_count,
                json.dumps(errors, ensure_ascii=False),
                run_id,
            ),
        )
        self.connection.commit()


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("stored datetimes must include timezone information")
    return value.astimezone(timezone.utc).isoformat()
