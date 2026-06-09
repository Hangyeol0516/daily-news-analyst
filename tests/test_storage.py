import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from daily_news.models import Article
from daily_news.storage import NewsStore


NOW = datetime(2026, 6, 9, 3, tzinfo=timezone.utc)


def article(url: str, *, published_at: datetime = NOW) -> Article:
    return Article(
        title="Example headline",
        url=url,
        source="Example",
        category="world",
        published_at=published_at,
        summary="Example summary",
    )


class NewsStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "news.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_saves_articles_and_ignores_duplicate_urls(self):
        with NewsStore(self.database) as store:
            first = store.save_articles([article("https://example.com/1")], collected_at=NOW)
            second = store.save_articles([article("https://example.com/1")], collected_at=NOW)

            stored = store.recent_articles(NOW - timedelta(days=1))

        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        self.assertEqual(len(stored), 1)

    def test_returns_only_recent_articles(self):
        with NewsStore(self.database) as store:
            store.save_articles(
                [
                    article("https://example.com/recent"),
                    article(
                        "https://example.com/old",
                        published_at=NOW - timedelta(days=3),
                    ),
                ],
                collected_at=NOW,
            )

            stored = store.recent_articles(NOW - timedelta(days=1))

        self.assertEqual([item.url for item in stored], ["https://example.com/recent"])

    def test_normalizes_timezones_before_filtering(self):
        seoul = timezone(timedelta(hours=9))
        with NewsStore(self.database) as store:
            store.save_articles(
                [article("https://example.com/timezone")],
                collected_at=NOW.astimezone(seoul),
            )

            stored = store.recent_articles(
                (NOW - timedelta(minutes=1)).astimezone(seoul)
            )

        self.assertEqual(len(stored), 1)

    def test_records_collection_run_result(self):
        with NewsStore(self.database) as store:
            run_id = store.start_run(NOW)
            store.finish_run(
                run_id,
                completed_at=NOW + timedelta(seconds=2),
                fetched_count=4,
                inserted_count=3,
                story_count=2,
                errors=["feed unavailable"],
            )
            row = store.connection.execute(
                "SELECT * FROM collection_runs WHERE id = ?",
                (run_id,),
            ).fetchone()

        self.assertEqual(row["fetched_count"], 4)
        self.assertEqual(row["inserted_count"], 3)
        self.assertEqual(json.loads(row["errors_json"]), ["feed unavailable"])

    def test_creates_expected_indexes(self):
        with NewsStore(self.database) as store:
            indexes = {
                row["name"]
                for row in store.connection.execute("PRAGMA index_list(articles)")
            }

        self.assertIn("idx_articles_published_at", indexes)
