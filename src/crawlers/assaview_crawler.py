import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from src.config.settings import settings
from src.crawlers.base_crawler import BaseCrawler
from src.models.campaign import Campaign
from src.repositories.raw_repository import save_html


TYPE_PATTERN = re.compile(r"(배송|방문|구매|기자단)")
DEADLINE_PATTERN = re.compile(r"\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}|\d+일남음")
APPLY_PATTERN = re.compile(r"신청\s*(\d+)\s*/\s*(\d+)명")
POINT_PATTERN = re.compile(r"(\d[\d,]*)P")
BRACKET_PATTERN = re.compile(r"\[([^\]]+)\]")

LOCATION_KEYWORDS = [
    "서울", "경기", "인천", "부산", "대구", "대전", "광주", "울산", "세종",
    "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]

NOISY_TITLE_PREFIXES = [
    "구매평워드",
    "캠페인명",
    "제품명",
    "제품명:",
    "캠페인명 :",
]

GENERIC_TITLE_VALUES = {
    "구매평워드",
    "구매평워드:",
    "캠페인명",
    "캠페인명:",
    "제품명",
    "제품명:",
}


def normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def is_region_text(value: str | None) -> bool:
    if not value:
        return False
    return any(keyword in value for keyword in LOCATION_KEYWORDS)


def clean_leading_labels(text: str) -> str:
    text = normalize_text(text)

    for prefix in NOISY_TITLE_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):].strip(" :")
            text = normalize_text(text)

    for marker in ["제품명:", "제품명", "캠페인명 :", "캠페인명:", "구매평워드:", "구매평워드"]:
        if marker in text:
            parts = text.split(marker, 1)
            if len(parts) == 2 and parts[1].strip():
                text = normalize_text(parts[1])

    return text


def split_title_and_benefit(text: str) -> tuple[str | None, str | None]:
    text = clean_leading_labels(text)
    if not text:
        return None, None

    for sep in [" - ", " / ", " | "]:
        if sep in text:
            left, right = text.split(sep, 1)
            left = clean_leading_labels(left)
            right = clean_leading_labels(right)
            if left and right:
                return left, right

    words = text.split()
    if len(words) >= 4:
        return text, None

    return text, None


def choose_better_title(title: str | None, benefit: str | None) -> tuple[str | None, str | None]:
    title = normalize_text(title or "")
    benefit = normalize_text(benefit or "")

    if not title and benefit:
        return benefit, None
    if title in GENERIC_TITLE_VALUES and benefit:
        return benefit, None
    if title and len(title) <= 4 and benefit and len(benefit) >= 8:
        return benefit, None
    if title.startswith("[") and title.endswith("]") and benefit:
        return benefit, None

    return title or None, benefit or None


def parse_assaview_card_text(card_text: str) -> dict:
    text = normalize_text(card_text)

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

    bracket_match = BRACKET_PATTERN.search(text)
    bracket_value = bracket_match.group(1).strip() if bracket_match else None
    if is_region_text(bracket_value):
        region_text = bracket_value

    working = text
    if campaign_type:
        working = working.replace(campaign_type, "", 1)
    if deadline_text:
        working = working.replace(deadline_text, "", 1)

    apply_match_working = APPLY_PATTERN.search(working)
    if apply_match_working:
        working = working[:apply_match_working.start()].strip()

    if point_match:
        working = working.replace(point_match.group(0), "").strip()

    if region_text and f"[{region_text}]" in working:
        working = working.replace(f"[{region_text}]", "", 1).strip()

    working = clean_leading_labels(working)

    if campaign_type == "방문":
        if working:
            parts = working.split(" ", 1)
            campaign_title = clean_leading_labels(parts[0])
            if len(parts) > 1:
                benefit_text = clean_leading_labels(parts[1])
            campaign_title, benefit_text = choose_better_title(campaign_title, benefit_text)
    else:
        campaign_title, benefit_text = split_title_and_benefit(working)
        campaign_title, benefit_text = choose_better_title(campaign_title, benefit_text)

    if region_text and not is_region_text(region_text):
        region_text = None
    if campaign_title and benefit_text and campaign_title == benefit_text:
        benefit_text = None

    return {
        "campaign_type": campaign_type,
        "deadline_text": deadline_text,
        "apply_count_text": apply_count_text,
        "recruit_count_text": recruit_count_text,
        "point_text": point_text,
        "region_text": region_text,
        "campaign_title": campaign_title,
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
                if not any(keyword in text for keyword in ["신청", "배송", "방문", "구매", "기자단"]):
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

        unique: dict[tuple[str | None, str | None, str | None, str | None], Campaign] = {}
        for item in campaigns:
            key = (
                item.campaign_title,
                item.campaign_type,
                item.deadline_text,
                item.apply_count_text,
            )
            unique[key] = item

        return list(unique.values())
