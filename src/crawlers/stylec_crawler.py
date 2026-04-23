import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from src.config.settings import settings
from src.crawlers.base_crawler import BaseCrawler
from src.models.campaign import Campaign
from src.repositories.raw_repository import save_html


TYPE_PATTERN = re.compile(r"(구매평|블로그|방문형|배송형|기자단)")
DEADLINE_PATTERN = re.compile(r"\d+일 남음")
APPLY_PATTERN = re.compile(r"신청\s*(\d+)\s*/\s*(\d+)")
PRICE_PATTERN = re.compile(r"(\d[\d,]*)원")


def normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def parse_stylec_card_text(card_text: str) -> dict:
    text = normalize_text(card_text)

    campaign_type = None
    deadline_text = None
    apply_count_text = None
    recruit_count_text = None
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

    working = text

    if campaign_type:
        working = working.replace(campaign_type, "", 1)
    if deadline_text:
        working = working.replace(deadline_text, "", 1)

    apply_match_working = APPLY_PATTERN.search(working)
    if apply_match_working:
        working = working[:apply_match_working.start()].strip()

    working = normalize_text(working)

    # 가격 정보가 있으면 혜택 후보로 사용
    price_match = PRICE_PATTERN.search(working)
    if price_match:
        benefit_text = price_match.group(0)

    # 너무 짧은 값/필터성 문구 제외
    invalid_titles = {
        "구매평", "블로그", "방문형", "배송형", "기자단",
        "필터", "정렬", "최신순", "종료포함", "전체",
    }

    if working and working not in invalid_titles:
        campaign_title = working

    return {
        "campaign_title": campaign_title,
        "campaign_type": campaign_type,
        "deadline_text": deadline_text,
        "apply_count_text": apply_count_text,
        "recruit_count_text": recruit_count_text,
        "benefit_text": benefit_text,
    }


class StyleCCrawler(BaseCrawler):
    def crawl(self) -> list[Campaign]:
        campaigns: list[Campaign] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)
            page = browser.new_page()
            page.goto(
                settings.stylec_url,
                wait_until="domcontentloaded",
                timeout=settings.timeout_ms,
            )
            page.wait_for_timeout(2500)

            html = page.content()
            raw_path = save_html("stylec", html)

            links = page.locator("a").all()

            for link in links:
                text = link.inner_text().strip()
                href = link.get_attribute("href")

                if not text:
                    continue

                # 캠페인 카드처럼 보이는 텍스트만 우선 수집
                if not any(keyword in text for keyword in ["구매평", "블로그", "방문형", "배송형", "기자단"]):
                    continue

                parsed = parse_stylec_card_text(text)
                campaign_url = urljoin(settings.stylec_url, href) if href else None

                if not parsed["campaign_title"]:
                    continue

                campaigns.append(
                    Campaign(
                        source_site="stylec",
                        source_page_url=settings.stylec_url,
                        campaign_title=parsed["campaign_title"],
                        campaign_url=campaign_url,
                        campaign_type=parsed["campaign_type"],
                        benefit_text=parsed["benefit_text"],
                        deadline_text=parsed["deadline_text"],
                        apply_count_text=parsed["apply_count_text"],
                        recruit_count_text=parsed["recruit_count_text"],
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