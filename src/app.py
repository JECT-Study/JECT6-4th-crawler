from fastapi import FastAPI

from src.api.routers import crawl, blog, system
from src.api.site_registry import OPENAPI_TAGS

app = FastAPI(
    title="Blog Crawler",
    description="체험단 캠페인 크롤러 API",
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS,
)

app.include_router(system.router)
app.include_router(crawl.router)
app.include_router(blog.router)
