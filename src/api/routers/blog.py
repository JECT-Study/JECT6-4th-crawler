from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.api.schemas import BlogLinkCollectRequest, BlogLinkCollectResult, BlogPostCrawlRequest, BlogPostCrawlResult
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
    return await run_in_threadpool(controller.run_blog_posts, payload.blog_url)


@router.post(
    "/crawl/blog/detail-links",
    response_model=BlogLinkCollectResult,
    summary="네이버 블로그 상세 글 수집",
    description=(
        "네이버 블로그 목록 페이지 URL을 받아 상세 페이지 링크와 글 내용을 추출합니다. "
        "추출된 결과는 파일로 저장하지 않고 응답으로 반환합니다."
    ),
)
async def collect_blog_detail_links(payload: BlogLinkCollectRequest):
    return await run_in_threadpool(controller.collect_blog_detail_links, payload.url)
