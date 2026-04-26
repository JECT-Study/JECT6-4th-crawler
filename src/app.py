from fastapi import FastAPI

from src.api.routers.blog import router as blog_router
from src.api.routers.crawl import router as crawl_router
from src.api.routers.system import router as system_router
from src.api.site_registry import OPENAPI_TAGS


def create_app() -> FastAPI:
    app = FastAPI(
        title="블로그 체험단 크롤러 API",
        version="0.1.0",
        description=(
            "블로그 체험단 캠페인과 네이버 블로그 상세 링크를 수집하는 API입니다. "
            "현재 지원 도메인은 assaview.co.kr, stylec.co.kr, blog.naver.com 입니다."
        ),
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=OPENAPI_TAGS,
    )
    app.include_router(system_router)
    app.include_router(crawl_router)
    app.include_router(blog_router)
    return app


app = create_app()
