from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Campaign(BaseModel):
    # 식별
    source_platform: str                    # STYLEC / ASSAVIEW
    source_url: str                         # 원본 공고 URL

    # 기본 정보
    brand_name: Optional[str] = None
    title: str
    thumbnail_url: Optional[str] = None

    # 분류
    category: Optional[str] = None          # FOOD/BEAUTY/FASHION/LIFE/PET/TECH/TRAVEL/CULTURE/ETC
    type: Optional[str] = None              # VISIT/DELIVERY/REPORTER/REVIEW/PAYBACK
    channel: str = "BLOG"

    # 지역 (방문형만)
    region_depth1: Optional[str] = None
    region_depth2: Optional[str] = None

    # 제공 내용
    provided_content: Optional[str] = None

    # 인원
    recruit_count: Optional[int] = None
    apply_count: Optional[int] = None

    # 일정
    apply_start_date: Optional[str] = None
    apply_end_date: Optional[str] = None
    announce_date: Optional[str] = None
    experience_start: Optional[str] = None
    experience_end: Optional[str] = None
    purchase_start: Optional[str] = None
    purchase_end: Optional[str] = None
    review_deadline: Optional[str] = None

    # 미션
    mission: Optional[str] = None
    search_keywords: Optional[str] = None

    # 방문형 주소
    visit_address: Optional[str] = None

    # 상태
    is_guaranteed: bool = False
    status: str = "ACTIVE"

    # 메타
    crawled_at: datetime = Field(default_factory=datetime.now)