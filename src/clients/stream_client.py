"""Redis Stream 기반 ingest 이벤트 publisher.

크롤링 완료된 본문을 crawl:ingest 스트림에 publish합니다.
analyzer_client.py(HTTP 직접 전송)를 대체합니다.
"""
from __future__ import annotations

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
    blog_id: int | None = None,
    correlation_id: str | None = None,
    analysis_mode: str = "FULL_BLOG",
    batch_id: str | None = None,
    expected_count: int | None = None,
    post_index: int | None = None,
) -> None:
    """블로그 포스트 본문을 ingest 스트림에 publish."""
    try:
        payload: dict = {
            "user_id": str(user_id),
            "url": url,
            "title": title,
            "content": content,
            "source_type": "my_blog",
            "external_id": url,
            "retry_count": "0",
            "analysis_mode": analysis_mode,
        }
        if blog_id is not None:
            payload["blog_id"] = str(blog_id)
        if correlation_id is not None:
            payload["correlation_id"] = correlation_id
        if batch_id is not None:
            payload["batch_id"] = batch_id
        if expected_count is not None:
            payload["expected_count"] = str(expected_count)
        if post_index is not None:
            payload["post_index"] = str(post_index)
        _get_redis().xadd(STREAM_NAME, payload)
        logger.info(
            "stream_client: blog post published url={} mode={} batch_id={} index={}/{}",
            url, analysis_mode, batch_id, post_index, expected_count,
        )
    except Exception as exc:
        logger.warning("stream_client: publish 실패 (best-effort) — {}", exc)


def publish_ext_blog_post(
    *,
    url: str,
    title: str,
    content: str,
    user_id: int = DEFAULT_USER_ID,
    nickname: str | None = None,
    category: str | None = None,
    source_blog_url: str | None = None,
) -> None:
    """인플루언서 블로그 포스트를 ext_blog source_type으로 ingest 스트림에 publish."""
    try:
        payload: dict = {
            "user_id": str(user_id),
            "url": url,
            "title": title,
            "content": content,
            "source_type": "ext_blog",
            "external_id": url,
            "retry_count": "0",
        }
        if nickname is not None:
            payload["nickname"] = nickname
        if category is not None:
            payload["category"] = category
        if source_blog_url is not None:
            payload["source_blog_url"] = source_blog_url
        _get_redis().xadd(STREAM_NAME, payload)
        logger.info(
            "stream_client: ext_blog post published url={} nickname={} category={}",
            url, nickname, category,
        )
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
