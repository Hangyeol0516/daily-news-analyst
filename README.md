# Daily News Analyst

RSS 피드에서 기사를 수집하고, 비슷한 기사를 하나의 이야기로 묶은 뒤 중요도 순으로 Markdown 브리핑을 생성하는 프로젝트입니다.

현재 버전은 외부 AI API 없이 실행되는 기초 파이프라인입니다. 출처 수, 기사 최신성, 제목 유사도를 이용해 주요 이야기를 선정합니다.

## 현재 기능

- RSS 2.0 및 Atom 피드 수집
- HTML 요약문 정리
- URL 정규화와 유사 기사 중복 제거
- 출처 수와 최신성 기반 중요도 점수
- 출처 링크를 포함한 Markdown 리포트
- 일부 피드 실패 시 나머지 피드 계속 처리
- SQLite 기사 저장 및 URL 기준 중복 수집 방지
- 수집 실행별 신규 기사 수와 오류 이력 기록

## 실행

Python 3.10 이상이 필요합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
daily-news
```

기본 출력은 `reports/YYYY-MM-DD.md`입니다.

```bash
daily-news \
  --feeds config/feeds.json \
  --database data/news.db \
  --hours 24 \
  --limit 10 \
  --timezone Asia/Seoul
```

## 테스트

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 다음 단계

- 한국어 군집 품질 개선
- LLM 기반 출처 인용 요약
- 카테고리별 브리핑
- Telegram, Discord, 이메일 발송
- 매일 자동 실행

자동 생성된 브리핑은 탐색용 초안이며 중요한 내용은 반드시 원문으로 확인해야 합니다.

## License

MIT
