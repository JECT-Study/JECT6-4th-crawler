# JECT Crawler (ject_crawl)

체험단 공고 사이트와 네이버 블로그를 수집하는 **FastAPI 크롤링 서버**.
JECT 시스템에서 웹 수집 책임을 전담하며, 수집 결과를 두 경로로 전달합니다.

1. **공고 메타데이터** → Spring 메인 API의 `POST /internal/campaigns/bulk`로 upsert
2. **본문 텍스트**(공고·블로그 포스트) → Redis Stream `crawl:ingest`에 publish
   → Analyzer(`ject`)의 ingest-worker가 청킹·임베딩·저장

크롤러 자신은 임베딩·분석을 하지 않고, DB 벡터 테이블에도 직접 쓰지 않습니다.

---

## 시스템 컨텍스트

```
운영자/내부 호출 ──▶ POST /crawl/campaign[/{site}]
Spring API      ──▶ POST /crawl/blog-posts        (블로그 분석 요청 시 fire-and-forget 트리거)
운영자/배치      ──▶ POST /crawl/blog/ext-posts    (인플루언서 블로그 배치 수집)

ject_crawl
  ├─ 공고 크롤링 (assaview, stylec) ──▶ Spring /internal/campaigns/bulk (upsert)
  └─ 본문 publish ──▶ Redis Stream crawl:ingest
                        · source_type=job_posting  (공고 본문)
                        · source_type=my_blog      (본인 블로그 포스트)
                        · source_type=ext_blog     (인플루언서 블로그 포스트)
```

## 아키텍처

```
src/
├── app.py                  FastAPI 앱 진입점
├── api/
│   ├── routers/            crawl(공고) / blog(블로그) / system(health)
│   ├── schemas.py          요청·응답 Pydantic 모델
│   └── site_registry.py    지원 사이트 레지스트리 (assaview, stylec)
├── controllers/            크롤링 오케스트레이션 (crawl_controller)
├── crawlers/               사이트별 크롤러 — base_crawler를 상속
│   ├── assaview_crawler / assaview_detail_crawler
│   ├── stylec_crawler / stylec_detail_crawler
│   ├── naver_blog_link_crawler    네이버 블로그 글 링크 수집
│   └── blog_post_crawler          블로그 포스트 본문 수집
├── extractors/             본문 텍스트 추출 (blog_post_extractor)
├── clients/
│   └── stream_client.py    Redis Stream crawl:ingest publish (XADD)
├── models/                 campaign, campaign_detail 도메인 모델
├── repositories/           campaign/raw 저장소
├── config/settings.py      설정 (REDIS_URL, SPRING_API_URL, ANALYZER_URL 등)
└── views/cli_view.py       CLI 실행용 뷰 (main.py 진입)
```

---

## API 목록

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | Crawler health check |
| POST | `/crawl/campaign/{site}` | 단일 사이트(assaview \| stylec) 공고 크롤링 |
| POST | `/crawl/campaign` | 전체 사이트 공고 크롤링 |
| POST | `/crawl/blog-posts` | 본인 블로그 포스트 백그라운드 크롤링 → `my_blog` publish |
| POST | `/crawl/blog/detail-links` | 네이버 블로그 상세 글 링크 수집 (옵션으로 `ext_blog` 적재) |
| POST | `/crawl/blog/ext-posts` | 인플루언서 블로그 배치 수집 → `ext_blog` publish |

> **레거시 호환**: 오타 경로 `/crawl/campain`, `/crawl/campain/{site}`는
> `include_in_schema=False`로 유지 중. 정식 경로는 `/crawl/campaign`이다.

---

## 동작 방식

### 1) 공고 수집 (`/crawl/campaign`)

1. 사이트별 크롤러(assaview/stylec)가 목록·상세를 수집
2. 공고 메타데이터를 Spring `POST /internal/campaigns/bulk`로 upsert
3. 공고 본문을 `crawl:ingest`에 `source_type=job_posting`으로 publish
   → Analyzer가 청킹·임베딩하여 추천 검색에 사용할 벡터를 생성

### 2) 본인 블로그 수집 (`/crawl/blog-posts`)

Spring이 블로그 분석 요청(`POST /blog/analyze`) 시 fire-and-forget으로 트리거한다.
요청은 **BackgroundTasks**로 즉시 응답하고, 수집은 백그라운드에서 진행된다
(호출 측이 동기 대기하지 않도록 설계).

네이버 블로그에서 포스트를 수집해 포스트별로 `crawl:ingest`에 publish하며,
FULL_BLOG 분석 진행률 추적을 위해 다음 필드를 함께 싣는다:

| 필드 | 의미 |
|---|---|
| `user_id`, `blog_id` | 요청 사용자·블로그 식별 |
| `correlation_id` | Spring 캐시/락/완료 이벤트와 연결되는 상관관계 ID |
| `analysis_mode` | `FULL_BLOG` 또는 `POST` |
| `batch_id`, `expected_count` | Analyzer가 배치 완료 시점(스냅샷 생성)을 판단하는 기준 |

### 3) 인플루언서 블로그 수집 (`/crawl/blog/ext-posts`)

인플루언서 블로그 URL 목록을 배치로 수집해 `source_type=ext_blog`로 publish한다.
Analyzer ingest-worker가 본문 저장과 함께 `influencer` 테이블 upsert까지 수행하므로,
크롤러는 수집·publish까지만 책임진다. `/crawl/blog/detail-links`는 글 링크 수집이
주 목적이며 옵션에 따라 `ext_blog` 적재를 겸한다.

### Stream publish 규약

- Stream 이름: `crawl:ingest` (`CRAWL_STREAM_NAME`으로 변경 가능)
- 소비자: Analyzer ingest-worker (consumer group `ingest-workers`)
- 처리 실패 격리는 소비 측(`crawl:ingest:dlq`) 책임 — 크롤러는 XADD까지만 보장

---

## 실행

```bash
poetry install

# API 서버
uvicorn src.app:app --port 8000

# CLI 크롤링 (배치 실행)
python main.py
```

설정은 `src/config/settings.py` 참조 — `REDIS_URL`, `SPRING_API_URL`, `ANALYZER_URL`이 핵심.
통합 기동은 `ject_integration_data/docker-compose.yml` 참조.
