"""Redis Stream 기반 ingest 이벤트 publisher.

크롤링 완료된 본문을 crawl:ingest 스트림에 publish합니다.
analyzer_client.py(HTTP 직접 전송)를 대체합니다.
"""

import os

import redis
from loguru import logger

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_NAME = os.getenv("CRAWL_STREAM_NAME", "crawl:ingest")
DEFAULT_USER_ID = int(os.getenv("ANALYZER_DEMO_USER_ID", "1"))

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def publish_blog_post(
    *,
    url: str,
    title: str,
    content: str,
    user_id: int = DEFAULT_USER_ID,
) -> None:
    """블로그 포스트 본문을 ingest 스트림에 publish."""
    try:
        _get_redis().xadd(STREAM_NAME, {
            "user_id": str(user_id),
            "url": url,
            "title": title,
            "content": content,
            "source_type": "my_blog",
            "external_id": url,
            "retry_count": "0",
        })
        logger.info("stream_client: blog post published url={}", url)
    except Exception as exc:
        logger.warning("stream_client: publish 실패 (best-effort) — {}", exc)


def publish_campaign(
    *,
    source_url: str,
    title: str,
    content: str,
    user_id: int = DEFAULT_USER_ID,
) -> None:
    """캠페인 본문을 ingest 스트림에 publish."""
    try:
        _get_redis().xadd(STREAM_NAME, {
            "user_id": str(user_id),
            "url": source_url,
            "title": title,
            "content": content,
            "source_type": "job_posting",
            "external_id": source_url,
            "retry_count": "0",
        })
        logger.info("stream_client: campaign published source_url={}", source_url)
    except Exception as exc:
        logger.warning("stream_client: publish 실패 (best-effort) — {}", exc)
