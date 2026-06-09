from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .analysis import rank_stories
from .feeds import FeedError, fetch_feed, load_sources, parse_feed
from .storage import NewsStore


def render(stories, generated_at: datetime, article_count: int) -> str:
    lines = [
        f"# Daily News Briefing - {generated_at.date().isoformat()}",
        "",
        f"- 수집 기사: `{article_count}`건",
        f"- 주요 이야기: `{len(stories)}`건",
        "",
    ]
    for index, story in enumerate(stories, 1):
        lines += [
            f"## {index}. {story.title}",
            "",
            f"**중요도:** `{story.score:.2f}`  ",
            f"**키워드:** {', '.join(story.keywords)}  ",
            f"**출처:** {', '.join(story.sources)}",
            "",
        ]
        for article in story.articles:
            lines.append(f"- [{article.source}] [{article.title}]({article.url})")
        lines.append("")
    lines += ["---", "", "자동 생성된 초안입니다. 중요한 내용은 원문을 확인하세요.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a ranked daily RSS news briefing.")
    parser.add_argument("--feeds", type=Path, default=Path("config/feeds.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timezone", default="Asia/Seoul")
    parser.add_argument("--database", type=Path, default=Path("data/news.db"))
    args = parser.parse_args(argv)

    now = datetime.now(ZoneInfo(args.timezone))
    articles, errors = [], []
    try:
        sources = load_sources(args.feeds)
    except FeedError as error:
        parser.error(str(error))
    for source in sources:
        try:
            articles.extend(parse_feed(fetch_feed(source), source))
        except FeedError as error:
            errors.append(str(error))

    cutoff = now - timedelta(hours=args.hours)
    try:
        with NewsStore(args.database) as store:
            run_id = store.start_run(now)
            inserted_count = store.save_articles(articles, collected_at=now)
            recent_articles = store.recent_articles(cutoff)
            stories = rank_stories(recent_articles, now=now)[:args.limit]
            store.finish_run(
                run_id,
                completed_at=datetime.now(ZoneInfo(args.timezone)),
                fetched_count=len(articles),
                inserted_count=inserted_count,
                story_count=len(stories),
                errors=errors,
            )
    except sqlite3.Error as error:
        parser.error(f"database error: {error}")

    output = args.output or Path("reports") / f"{now.date().isoformat()}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(stories, now, len(articles)), encoding="utf-8")
    print(
        f"Wrote {len(stories)} stories from {len(articles)} fetched articles "
        f"({inserted_count} new) to {output}"
    )
    for error in errors:
        print(f"warning: {error}")
    return 1 if errors and not articles else 0
