from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.api.schemas import BlogLinkCollectRequest, BlogLinkCollectResult
from src.controllers.crawl_controller import CrawlController

router = APIRouter(tags=["blog"])
controller = CrawlController()


@router.post(
    "/crawl/blog/detail-links",
    response_model=BlogLinkCollectResult,
    summary="네이버 블로그 상세 링크 수집",
    description=(
        "네이버 블로그 목록 페이지 URL을 받아 상세 페이지 링크 목록을 추출합니다. "
        "추출된 링크 목록은 응답으로 반환되고 서버 로그에도 출력됩니다."
    ),
)
async def collect_blog_detail_links(payload: BlogLinkCollectRequest):
    return await run_in_threadpool(controller.collect_blog_detail_links, payload.url)
