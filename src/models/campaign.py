from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Campaign(BaseModel):
    source_site: str
    source_page_url: str
    campaign_title: str
    campaign_url: Optional[str] = None

    campaign_type: Optional[str] = None
    platform: Optional[str] = None
    region_text: Optional[str] = None
    benefit_text: Optional[str] = None
    deadline_text: Optional[str] = None
    apply_count_text: Optional[str] = None
    recruit_count_text: Optional[str] = None
    section_name: Optional[str] = None
    point_text: Optional[str] = None

    category_text: Optional[str] = None
    media_text: Optional[str] = None
    order_text: Optional[str] = None
    content_text: Optional[str] = None

    raw_snapshot_path: Optional[str] = None
    collected_at: datetime = Field(default_factory=datetime.now)