import re

from src.models.campaign_detail import (
    CampaignDetail,
)


def extract_section(
    body: str,
    start: str,
    end: str,
) -> str:

    if start not in body:
        return ""

    text = body.split(start, 1)[1]

    if end in text:
        text = text.split(end, 1)[0]

    return text.strip()


def extract_period(
    body: str,
    label: str,
):

    pattern = rf"{label}\s*(.*?)\s*~\s*(.*)"

    match = re.search(pattern, body)

    if not match:
        return "", ""

    return (
        match.group(1).strip(),
        match.group(2).strip(),
    )


def parse_stylec_detail(
    body: str,
    url: str,
) -> CampaignDetail:

    lines = body.split("\n")

    title = lines[0].strip()

    # reward
    reward_match = re.search(
        r"([0-9,]+)\s*C",
        body,
    )

    reward_text = ""

    if reward_match:
        reward_text = reward_match.group(1)

    # region
    region_match = re.search(
        r"\n([가-힣/]+)\n지각불허",
        body,
    )

    region_text = ""

    if region_match:
        region_text = region_match.group(1)

    # 신청/모집 인원
    recruit_match = re.search(
        r"신청\s*([0-9]+)\s*명\s*/\s*([0-9]+)\s*명",
        body,
    )

    apply_count = ""
    recruit_count = ""

    if recruit_match:
        apply_count = recruit_match.group(1)
        recruit_count = recruit_match.group(2)

    # sections
    provided_content = extract_section(
        body,
        "제공내역",
        "검색 키워드",
    )

    keywords = extract_section(
        body,
        "검색 키워드",
        "체험단 미션",
    )

    mission_text = extract_section(
        body,
        "체험단 미션",
        "리뷰 작성 유의사항",
    )

    review_guidelines = extract_section(
        body,
        "리뷰 작성 유의사항",
        "체험단 신청하기",
    )

    # 기간
    apply_start, apply_end = extract_period(
        body,
        "신청 기간",
    )

    purchase_start, purchase_end = extract_period(
        body,
        "구매 기간",
    )

    review_start, review_end = extract_period(
        body,
        "등록 기간",
    )

    detail = CampaignDetail(

        source_site="stylec",

        campaign_url=url,

        title=title,

        reward_text=reward_text,

        region_text=region_text,

        apply_count=apply_count,

        recruit_count=recruit_count,

        apply_start_date=apply_start,
        apply_end_date=apply_end,

        purchase_start_date=purchase_start,
        purchase_end_date=purchase_end,

        review_start_date=review_start,
        review_end_date=review_end,

        provided_content=provided_content,

        body_keywords=keywords,

        mission_text=mission_text,

        review_guidelines=review_guidelines,
    )

    return detail