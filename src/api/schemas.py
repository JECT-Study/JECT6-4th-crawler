from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from src.models.campaign import Campaign


class CrawlSite(str, Enum):
    assaview = "assaview"
    stylec = "stylec"
    all = "all"


class AnalysisMode(str, Enum):
    FULL_BLOG = "FULL_BLOG"
    POST = "POST"


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


class BlogPostCrawlRequest(BaseModel):
    blog_url: str = Field(
        description="크롤링할 네이버 블로그 URL",
        examples=["https://blog.naver.com/example_id"],
    )
    user_id: int = Field(default=1, description="분석 서버에 저장할 사용자 ID")
    blog_id: Optional[int] = Field(default=None, description="Spring UserBlog 엔티티 ID")
    correlation_id: Optional[str] = Field(default=None, description="크롤링→ingest→분석 추적용 UUID")
    analysis_mode: AnalysisMode = Field(default=AnalysisMode.FULL_BLOG, description="분석 모드 (FULL_BLOG | POST)")
    batch_id: Optional[str] = Field(default=None, description="FULL_BLOG 배치 추적용 UUID")


class BlogPostCrawlResult(BaseModel):
    blog_url: str
    count: int


class BlogLinkCollectRequest(BaseModel):
    url: str = Field(
        description="네이버 블로그 목록 페이지 URL",
        examples=[
            "https://blog.naver.com/PostList.naver?blogId=cha_23&categoryNo=34&parentCategoryNo=34"
        ],
    )
    publish_to_analyzer: bool = Field(
        default=False,
        description="수집 결과를 ext_blog source_type으로 Analyzer에 publish할지 여부",
    )
    user_id: Optional[int] = Field(
        default=None,
        description="Analyzer 저장 시 사용할 사용자 ID (미지정 시 시스템 유저 ID 사용)",
    )
    nickname: Optional[str] = Field(default=None, description="인플루언서 닉네임 (메타데이터)")
    category: Optional[str] = Field(default=None, description="블로그 카테고리 (BEAUTY/FOOD/LIVING/FASHION/TECH/TRAVEL)")
    max_posts: Optional[int] = Field(default=None, ge=1, le=20, description="수집할 최대 글 수 (기본: NaverBlogLinkCrawler.MAX_DETAIL_LINKS=20)")


class ExtBlogBatchIngestItem(BaseModel):
    blog_url: str = Field(description="인플루언서 네이버 블로그 URL")
    nickname: Optional[str] = Field(default=None, description="인플루언서 닉네임")
    category: Optional[str] = Field(default=None, description="블로그 카테고리")


class ExtBlogBatchIngestRequest(BaseModel):
    blogs: list[ExtBlogBatchIngestItem] = Field(description="수집·적재할 인플루언서 블로그 목록")
    user_id: Optional[int] = Field(default=None, description="Analyzer 저장 시 사용할 사용자 ID (미지정 시 시스템 유저 ID)")
    max_posts_per_blog: int = Field(default=20, ge=1, le=20, description="블로그당 최대 수집 글 수")


class ExtBlogBatchIngestResult(BaseModel):
    total_blogs: int
    total_published: int
    results: list["ExtBlogBatchIngestItemResult"]


class ExtBlogBatchIngestItemResult(BaseModel):
    blog_url: str
    nickname: Optional[str]
    published_count: int
    error: Optional[str] = None


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
    published_count: int = 0
    detail_urls: list[str]
    posts: list[BlogPostCollectItem]
