from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .analysis import rank_stories
from .feeds import FeedError, fetch_feed, load_sources, parse_feed


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
    stories = rank_stories([article for article in articles if article.published_at >= cutoff], now=now)[:args.limit]
    output = args.output or Path("reports") / f"{now.date().isoformat()}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(stories, now, len(articles)), encoding="utf-8")
    print(f"Wrote {len(stories)} stories from {len(articles)} articles to {output}")
    for error in errors:
        print(f"warning: {error}")
    return 1 if errors and not articles else 0
