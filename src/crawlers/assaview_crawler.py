import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from src.config.settings import settings
from src.crawlers.base_crawler import BaseCrawler
from src.models.campaign import Campaign
from src.repositories.raw_repository import save_html


TYPE_PATTERN = re.compile(r"(배송형|방문형|구매형|기자단)")
DEADLINE_PATTERN = re.compile(r"\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}|\d+일 남음")
APPLY_PATTERN = re.compile(r"신청\s*(\d+)\s*/\s*(\d+)명")
POINT_PATTERN = re.compile(r"(\d[\d,]*)P")
REGION_PATTERN = re.compile(r"\[([^\]]+)\]")


def parse_assaview_card_text(card_text: str) -> dict:
    text = " ".join(card_text.split())

    campaign_type = None
    deadline_text = None
    apply_count_text = None
    recruit_count_text = None
    point_text = None
    region_text = None
    campaign_title = None
    benefit_text = None

    type_match = TYPE_PATTERN.search(text)
    if type_match:
        campaign_type = type_match.group(1)

    deadline_match = DEADLINE_PATTERN.search(text)
    if deadline_match:
        deadline_text = deadline_match.group(0)

    apply_match = APPLY_PATTERN.search(text)
    if apply_match:
        apply_count_text = apply_match.group(1)
        recruit_count_text = apply_match.group(2)

    point_match = POINT_PATTERN.search(text)
    if point_match:
        point_text = point_match.group(1).replace(",", "")

    region_match = REGION_PATTERN.search(text)
    if region_match:
        region_text = region_match.group(1)

    working = text

    if campaign_type:
        working = working.replace(campaign_type, "", 1)
    if deadline_text:
        working = working.replace(deadline_text, "", 1)

    # 신청 이후 텍스트 제거
    apply_match_working = APPLY_PATTERN.search(working)
    if apply_match_working:
        working = working[:apply_match_working.start()].strip()

    # 포인트 제거
    if point_match:
        working = working.replace(point_match.group(0), "").strip()

    # [지역] 뒤 첫 문장을 제목으로 추정
    if region_text and f"[{region_text}]" in working:
        after_region = working.split(f"[{region_text}]", 1)[1].strip()
        parts = after_region.split(" ", 1)
        if parts:
            campaign_title = parts[0].strip()
            if len(parts) > 1:
                benefit_text = parts[1].strip()
    else:
        parts = working.split(" ", 1)
        if parts:
            campaign_title = parts[0].strip()
            if len(parts) > 1:
                benefit_text = parts[1].strip()

    return {
        "campaign_type": campaign_type,
        "deadline_text": deadline_text,
        "apply_count_text": apply_count_text,
        "recruit_count_text": recruit_count_text,
        "point_text": point_text,
        "region_text": region_text,
        "campaign_title": campaign_title or working,
        "benefit_text": benefit_text,
    }


class AssaViewCrawler(BaseCrawler):
    def crawl(self) -> list[Campaign]:
        campaigns: list[Campaign] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)
            page = browser.new_page()
            page.goto(
                settings.assaview_url,
                wait_until="domcontentloaded",
                timeout=settings.timeout_ms,
            )
            page.wait_for_timeout(2500)

            html = page.content()
            raw_path = save_html("assaview", html)

            links = page.locator("a").all()

            for link in links:
                text = link.inner_text().strip()
                href = link.get_attribute("href")

                if not text:
                    continue

                # 캠페인 카드처럼 보이는 텍스트만
                if not any(keyword in text for keyword in ["신청", "배송형", "방문형", "구매형", "기자단"]):
                    continue

                parsed = parse_assaview_card_text(text)
                campaign_url = urljoin(settings.assaview_url, href) if href else None

                if not parsed["campaign_title"]:
                    continue

                campaigns.append(
                    Campaign(
                        source_site="assaview",
                        source_page_url=settings.assaview_url,
                        campaign_title=parsed["campaign_title"],
                        campaign_url=campaign_url,
                        campaign_type=parsed["campaign_type"],
                        region_text=parsed["region_text"],
                        benefit_text=parsed["benefit_text"],
                        deadline_text=parsed["deadline_text"],
                        apply_count_text=parsed["apply_count_text"],
                        recruit_count_text=parsed["recruit_count_text"],
                        point_text=parsed["point_text"],
                        raw_snapshot_path=raw_path,
                    )
                )

            browser.close()

        unique = {}
        for item in campaigns:
            key = (
                item.campaign_title,
                item.campaign_type,
                item.deadline_text,
                item.apply_count_text,
            )
            unique[key] = item

        return list(unique.values())