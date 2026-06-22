from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from src.api.schemas import CrawlAllResult, CrawlResult, CrawlSite
from src.controllers.crawl_controller import CrawlController

router = APIRouter(tags=["campaign"])
controller = CrawlController()


async def _crawl_site_handler(
    site: CrawlSite,
    save_csv: bool,
    max_campaigns: int | None,
) -> CrawlResult:
    handler = controller.run_assaview if site == CrawlSite.assaview else controller.run_stylec
    return await run_in_threadpool(handler, save_csv, max_campaigns)


async def _crawl_all_handler(save_csv: bool, max_campaigns: int | None) -> CrawlAllResult:
    results = await run_in_threadpool(controller.run_all, save_csv, max_campaigns)
    return {"results": results}


@router.post(
    "/crawl/campain/{site}",
    response_model=CrawlResult,
    summary="단일 사이트 크롤링 (레거시 경로)",
    description="지원 사이트: assaview, stylec. /crawl/campaign/{site} 를 사용하세요.",
    include_in_schema=False,
)
async def crawl_site_legacy(
    site: CrawlSite,
    save_csv: bool = Query(default=True, description="CSV 저장 여부"),
    max_campaigns: int | None = Query(default=None, ge=1, description="테스트용 최대 수집 캠페인 수"),
):
    return await _crawl_site_handler(site, save_csv, max_campaigns)


@router.post(
    "/crawl/campaign/{site}",
    response_model=CrawlResult,
    summary="단일 사이트 크롤링",
    description=(
        "선택한 사이트의 크롤러를 실행하고 필요하면 결과를 CSV로 저장합니다. "
        "지원 사이트는 assaview, stylec 입니다."
    ),
)
async def crawl_site(
    site: CrawlSite,
    save_csv: bool = Query(default=True, description="크롤링 결과를 CSV 파일로 저장할지 여부입니다."),
    max_campaigns: int | None = Query(default=None, ge=1, description="테스트용 최대 수집 캠페인 수입니다."),
):
    return await _crawl_site_handler(site, save_csv, max_campaigns)


@router.post(
    "/crawl/campain",
    response_model=CrawlAllResult,
    summary="전체 사이트 크롤링 (레거시 경로)",
    include_in_schema=False,
)
async def crawl_all_legacy(
    save_csv: bool = Query(default=True, description="CSV 저장 여부"),
    max_campaigns: int | None = Query(default=None, ge=1, description="테스트용 사이트별 최대 수집 캠페인 수"),
):
    return await _crawl_all_handler(save_csv, max_campaigns)


@router.post(
    "/crawl/campaign",
    response_model=CrawlAllResult,
    summary="전체 사이트 크롤링",
    description="설정된 전체 크롤러를 실행하고 수집 결과를 한 번에 반환합니다.",
)
async def crawl_all(
    save_csv: bool = Query(default=True, description="크롤링 결과를 CSV 파일로 저장할지 여부입니다."),
    max_campaigns: int | None = Query(default=None, ge=1, description="테스트용 사이트별 최대 수집 캠페인 수입니다."),
):
    return await _crawl_all_handler(save_csv, max_campaigns)
