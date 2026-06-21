from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.api.schemas import (
    BlogLinkCollectRequest,
    BlogLinkCollectResult,
    BlogPostCrawlRequest,
    BlogPostCrawlResult,
    ExtBlogBatchIngestRequest,
    ExtBlogBatchIngestResult,
)
from src.controllers.crawl_controller import CrawlController

router = APIRouter(tags=["blog"])
controller = CrawlController()


@router.post(
    "/crawl/blog-posts",
    response_model=BlogPostCrawlResult,
    summary="블로그 포스트 크롤링 및 Analyzer 전송",
    description="블로그 URL을 받아 포스트를 크롤링하고 Analyzer에 전송합니다.",
)
async def crawl_blog_posts(payload: BlogPostCrawlRequest):
    return await run_in_threadpool(
        controller.run_blog_posts,
        payload.blog_url,
        payload.user_id,
        payload.blog_id,
        payload.correlation_id,
        payload.analysis_mode,
        payload.batch_id,
    )


@router.post(
    "/crawl/blog/detail-links",
    response_model=BlogLinkCollectResult,
    summary="네이버 블로그 상세 글 수집 (선택적 ext_blog 적재)",
    description=(
        "네이버 블로그 목록 페이지 URL을 받아 상세 페이지 링크와 글 내용을 추출합니다. "
        "publish_to_analyzer=true 시 수집 결과를 source_type=ext_blog로 Analyzer에 적재합니다."
    ),
)
async def collect_blog_detail_links(payload: BlogLinkCollectRequest):
    return await run_in_threadpool(
        controller.collect_blog_detail_links,
        payload.url,
        payload.publish_to_analyzer,
        payload.user_id,
        payload.nickname,
        payload.category,
        payload.max_posts,
    )


@router.post(
    "/crawl/blog/ext-posts",
    response_model=ExtBlogBatchIngestResult,
    summary="인플루언서 블로그 배치 적재",
    description=(
        "여러 인플루언서 블로그 URL을 받아 글을 수집하고 "
        "source_type=ext_blog로 Analyzer에 일괄 적재합니다."
    ),
)
async def ingest_influencer_blogs(payload: ExtBlogBatchIngestRequest):
    return await run_in_threadpool(
        controller.ingest_influencer_blogs,
        payload.blogs,
        payload.user_id,
        payload.max_posts_per_blog,
    )
