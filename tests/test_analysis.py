import unittest
from datetime import datetime, timezone

from daily_news.analysis import rank_stories, similarity
from daily_news.models import Article


class AnalysisTest(unittest.TestCase):
    def test_groups_similar_headlines(self):
        self.assertGreaterEqual(
            similarity(
                "City launches new public transport plan",
                "New public transport plan launched by city",
            ),
            0.82,
        )

    def test_ranks_multi_source_story_first(self):
        now = datetime(2026, 6, 9, tzinfo=timezone.utc)
        articles = [
            Article("City launches new public transport plan", "https://a.test/1", "A", "world", now),
            Article("New public transport plan launched by city", "https://b.test/1", "B", "world", now),
            Article("Separate technology story", "https://a.test/2", "A", "tech", now),
        ]
        stories = rank_stories(articles, now=now)
        self.assertEqual(set(stories[0].sources), {"A", "B"})


if __name__ == "__main__":
    unittest.main()
