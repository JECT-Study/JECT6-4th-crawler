from pydantic import BaseModel


class CampaignDetail(BaseModel):
    source_site: str
    campaign_url: str
    title: str = ""
    reward_text: str = ""
    region_text: str = ""
    apply_count: str = ""
    recruit_count: str = ""
    apply_start_date: str = ""
    apply_end_date: str = ""
    announce_date: str = ""
    purchase_start_date: str = ""
    purchase_end_date: str = ""
    review_start_date: str = ""
    review_end_date: str = ""
    provided_content: str = ""
    body_keywords: str = ""
    mission_text: str = ""
    review_guidelines: str = ""