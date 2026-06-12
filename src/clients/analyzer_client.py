"""Analyzer 서버 HTTP 클라이언트.

블로그 포스트 본문 또는 캠페인 본문을 Analyzer POST /v1/documents/chunks 로 직송합니다.
Analyzer 장애 시 크롤은 계속 진행하는 best-effort 처리입니다.
"""

import os
import time
from typing import Optional

import requests
from loguru import logger

ANALYZER_URL = os.getenv("ANALYZER_URL", "http://localhost:8000")
DEMO_USER_ID = int(os.getenv("ANALYZER_DEMO_USER_ID", "1"))
REQUEST_TIMEOUT = 10


def _post_chunks(payload: dict) -> Optional[dict]:
    url = f"{ANALYZER_URL}/v1/documents/chunks"
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("analyzer_client: POST /v1/documents/chunks 실패 (best-effort) — {}", exc)
        return None


def send_blog_post(
    *,
    url: str,
    title: str,
    content: str,
    user_id: int = DEMO_USER_ID,
) -> Optional[dict]:
    """블로그 포스트 본문을 Analyzer에 전송."""
    payload = {
        "user_id": user_id,
        "source_type": "my_blog",
        "title": title,
        "content": content,
        "url": url,
        "external_id": url,
    }
    result = _post_chunks(payload)
    if result:
        logger.info("analyzer_client: blog chunk 전송 완료 document_id={}", result.get("document_id"))
    return result


def send_campaign(
    *,
    source_url: str,
    title: str,
    content: str,
    user_id: int = DEMO_USER_ID,
) -> Optional[dict]:
    """캠페인 공고 본문을 Analyzer에 전송 (external_id = source_url)."""
    payload = {
        "user_id": user_id,
        "source_type": "job_posting",
        "title": title,
        "content": content,
        "url": source_url,
        "external_id": source_url,
    }
    result = _post_chunks(payload)
    if result:
        logger.info("analyzer_client: campaign chunk 전송 완료 source_url={} document_id={}", source_url, result.get("document_id"))
    return result
