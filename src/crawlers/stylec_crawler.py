import json
import re
from typing import Optional
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright
from loguru import logger

from src.config.settings import settings
from src.crawlers.base_crawler import BaseCrawler
from src.models.campaign import Campaign
from src.repositories.raw_repository import save_html

BASE_URL = "https://www.stylec.co.kr/"
API_BASE = "https://api2.stylec.co.kr:6439/v1/trial"

TYPE_MAP = {
    "제공형": "DELIVERY",
    "배송형": "DELIVERY",
    "방문형": "VISIT",
    "기자단": "REPORTER",
    "구매평": "REVIEW",
    "페이백": "PAYBACK",
    "페이백 + 구매평": "PAYBACK",
}

CATEGORY_MAP = {
    "식품": "FOOD", "푸드": "FOOD", "음식": "FOOD",
    "뷰티": "BEAUTY", "화장품": "BEAUTY",
    "패션": "FASHION", "의류": "FASHION",
    "생활": "LIFE", "가전": "LIFE", "가구": "LIFE",
    "펫": "PET", "반려": "PET",
    "테크": "TECH", "IT": "TECH",
    "여행": "TRAVEL", "숙박": "TRAVEL",
    "문화": "CULTURE",
}

SKIP_BRAND_WORDS = ["네이버", "쿠팡", "스마트", "배달", "블로그", "리뷰", "체험"]


def infer_category(title: str) -> Optional[str]:
    for keyword, category in CATEGORY_MAP.items():
        if keyword in title:
            return category
    return "ETC"


def safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def extract_brand_name(title: str, b2b_company: str = None) -> Optional[str]:
    # 1. b2b_company 필드
    if b2b_company:
        return b2b_company.strip()

    # 2. 제목 앞 대괄호 [브랜드명]
    m = re.search(r"^\[([^\]]+)\]", title)
    if m:
        return m.group(1).strip()

    # 3. (네이버블로그+쿠팡구매평) 같은 채널 패턴은 제외하고 순수 브랜드 소괄호만
    m = re.search(r"^\(([^+\)]{2,15})\)\s+(.+)", title)
    if m:
        candidate = m.group(1).strip()
        skip = ["네이버", "쿠팡", "블로그", "구매평", "인스타", "유튜브", "배달", "스마트"]
        if not any(kw in candidate for kw in skip):
            return candidate

    return None


def parse_item(item: dict) -> Campaign | None:
    title = item.get("wr_subject", "").strip()
    if not title:
        return None

    link = item.get("link", "")
    source_url = urljoin(BASE_URL, link) if link else ""

    # type 매핑
    wr_type = item.get("wr_type_label") or item.get("wr_type", "")
    campaign_type = TYPE_MAP.get(wr_type, "DELIVERY")

    # 인원
    apply_count = safe_int(item.get("tr_enroll_cnt"))
    recruit_count = safe_int(item.get("tr_recruit_max"))

    # 제공 내용
    price = safe_int(item.get("it_price"))
    cashback = safe_int(item.get("tr_cashback_amt"))
    if price:
        provided_content = f"{price:,}원"
    elif cashback:
        provided_content = f"{cashback:,}C"
    else:
        provided_content = None

    # 썸네일
    thumbnail_url = item.get("img") or None

    # 브랜드명
    brand_name = extract_brand_name(title, item.get("b2b_company"))

    # 100% 당첨
    is_guaranteed = bool(
        recruit_count and apply_count is not None and apply_count < recruit_count
    )

    return Campaign(
        source_platform="STYLEC",
        source_url=source_url,
        brand_name=brand_name,
        title=title,
        thumbnail_url=thumbnail_url,
        category=infer_category(title),
        type=campaign_type,
        channel="BLOG",
        provided_content=provided_content,
        recruit_count=recruit_count,
        apply_count=apply_count,
        is_guaranteed=is_guaranteed,
        status="ACTIVE",
    )


class StyleCCrawler(BaseCrawler):

    def crawl(self) -> list[Campaign]:
        all_items: list[Campaign] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)
            context = browser.new_context()
            page = context.new_page()

            logger.info("[stylec] 세션 초기화")
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=settings.timeout_ms)
            page.wait_for_timeout(2000)

            first_resp = page.evaluate(f"""
                async () => {{
                    const res = await fetch('{API_BASE}?order=wr_last&page=1&count=50&snsType[]=naverblog&include_finish=false');
                    return await res.json();
                }}
            """)

            total = first_resp.get("data", {}).get("Total", 0)
            logger.info(f"[stylec] 총 캠페인 수: {total}")

            total_pages = min(settings.stylec_pages, -(-total // 50))
            if total_pages == 0:
                total_pages = settings.stylec_pages

            logger.info(f"[stylec] 수집 페이지 수: {total_pages}")

            for p_num in range(1, total_pages + 1):
                logger.info(f"[stylec] 페이지 {p_num} 수집 중")

                resp = page.evaluate(f"""
                    async () => {{
                        const res = await fetch('{API_BASE}?order=wr_last&page={p_num}&count=50&snsType[]=naverblog&include_finish=false');
                        return await res.json();
                    }}
                """)

                items = resp.get("data", {}).get("data", [])
                logger.info(f"[stylec] 페이지 {p_num}: {len(items)}개")

                if not items:
                    logger.info(f"[stylec] 페이지 {p_num} 빈 결과 — 종료")
                    break

                save_html(f"stylec_api_p{p_num}", json.dumps(resp, ensure_ascii=False))

                for item in items:
                    campaign = parse_item(item)
                    if campaign:
                        all_items.append(campaign)

                page.wait_for_timeout(500)

            browser.close()

        unique = {c.source_url: c for c in all_items if c.source_url}
        result = list(unique.values())
        logger.info(f"[stylec] 총 {len(result)}개 수집 완료")
        return result