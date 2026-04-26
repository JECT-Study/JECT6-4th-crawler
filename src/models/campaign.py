from datetime import datetime

from pydantic import BaseModel, Field


class Campaign(BaseModel):
    source_site: str
    source_page_url: str
    campaign_title: str
    campaign_url: str | None = None
    campaign_type: str | None = None
    platform: str | None = None
    region_text: str | None = None
    benefit_text: str | None = None
    deadline_text: str | None = None
    apply_count_text: str | None = None
    recruit_count_text: str | None = None
    section_name: str | None = None
    point_text: str | None = None
    category_text: str | None = None
    media_text: str | None = None
    order_text: str | None = None
    raw_snapshot_path: str | None = None
    collected_at: datetime = Field(default_factory=datetime.now)
