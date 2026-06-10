from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from src.models.campaign import Campaign


class CrawlSite(str, Enum):
    assaview = "assaview"
    stylec = "stylec"
    all = "all"


class CrawlResult(BaseModel):
    site: str
    count: int
    output_file: Optional[str] = None
    campaigns: list[Campaign]


class CrawlAllResult(BaseModel):
    results: list[CrawlResult]


class SiteInfo(BaseModel):
    name: str
    domain: str
    description: str


class ServiceInfo(BaseModel):
    service: str
    supported_sites: list[SiteInfo]


class BlogLinkCollectRequest(BaseModel):
    url: str = Field(
        description="네이버 블로그 목록 페이지 URL",
        examples=[
            "https://blog.naver.com/PostList.naver?blogId=cha_23&categoryNo=34&parentCategoryNo=34"
        ],
    )


class BlogPostCollectItem(BaseModel):
    url: str
    post_url: str
    title: str
    thumbnail_image_url: Optional[str] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    content: str


class BlogLinkCollectResult(BaseModel):
    source_url: str
    resolved_list_url: str
    blog_id: str
    blog_owner_name: str
    count: int
    detail_urls: list[str]
    posts: list[BlogPostCollectItem]
