from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from src.api.schemas import CrawlAllResult, CrawlResult, CrawlSite
from src.controllers.crawl_controller import CrawlController

router = APIRouter(tags=["campaign"])
controller = CrawlController()


@router.post(
    "/crawl/campain/{site}",
    response_model=CrawlResult,
    summary="단일 사이트 크롤링",
    description=(
        "선택한 사이트의 크롤러를 실행하고 필요하면 결과를 CSV로 저장합니다. "
        "지원 사이트는 assaview, stylec 입니다."
    ),
)
async def crawl_site(
    site: CrawlSite,
    save_csv: bool = Query(
        default=True,
        description="크롤링 결과를 CSV 파일로 저장할지 여부입니다.",
    ),
):
    # if site == CrawlSite.all:
    #     raise HTTPException(status_code=400, detail="전체 수집은 /crawl/campaign 엔드포인트를 사용하세요.")

    handler = controller.run_assaview if site == CrawlSite.assaview else controller.run_stylec
    return await run_in_threadpool(handler, save_csv)


@router.post(
    "/crawl/campain",
    response_model=CrawlAllResult,
    summary="전체 사이트 크롤링",
    description="설정된 전체 크롤러를 실행하고 수집 결과를 한 번에 반환합니다.",
)
async def crawl_all(
    save_csv: bool = Query(
        default=True,
        description="크롤링 결과를 CSV 파일로 저장할지 여부입니다.",
    ),
):
    results = await run_in_threadpool(controller.run_all, save_csv)
    return {"results": results}
