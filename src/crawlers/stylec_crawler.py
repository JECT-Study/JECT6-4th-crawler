import re
from urllib.parse import urlencode, urljoin

from playwright.sync_api import sync_playwright

from src.config.settings import settings
from src.crawlers.base_crawler import BaseCrawler
from src.models.campaign import Campaign
from src.repositories.raw_repository import save_html


DEADLINE_PATTERN = re.compile(r"(오늘마감|\d+일 남음)")
APPLY_PATTERN = re.compile(r"신청\s*([\d,]+)명?\s*/\s*([\d,]+)명")
PRICE_PATTERN = re.compile(r"실구매가\s*([\d,]+원)")
REGION_PREFIX_PATTERN = re.compile(r"^(배달|방문)\s*·\s*([^\s]+)")
BRACKET_PATTERN = re.compile(r"\[([^\]]+)\]")


REMOVE_WORDS = [
    "구매평",
    "기자단",
    "제공형",
    "페이백",
    "배송형",
    "방문형",
    "오늘마감",
    "네이버블로그",
]

INVALID_TITLES = {
    "",
    "신청",
    "실구매가",
    "제공형",
    "기자단",
    "구매평",
    "오늘마감",
    "남음",
}


def normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def build_stylec_url(page_number: int) -> str:
    query = {
        "sortOption": "wr_last",
        "pageNumber": page_number,
        "count": settings.stylec_count,
        "campaignType": "",
        "category": "",
        "region": "",
        "sns": settings.stylec_sns,
        "include_finish": "false",
    }
    return f"{settings.stylec_base_url}?{urlencode(query)}"


def is_card_like_text(text: str) -> bool:
    text = normalize_text(text)
    signals = ["신청", "오늘마감", "일 남음", "실구매가", "제공내역"]
    return any(signal in text for signal in signals)


def extract_region(text: str) -> tuple[str | None, str]:
    text = normalize_text(text)
    match = REGION_PREFIX_PATTERN.search(text)
    if not match:
        return None, text

    region_text = match.group(2).strip()
    text = text.replace(match.group(0), "", 1).strip()
    return region_text, normalize_text(text)


def extract_apply_counts(text: str) -> tuple[str | None, str | None, str]:
    text = normalize_text(text)
    match = APPLY_PATTERN.search(text)
    if not match:
        return None, None, text

    apply_count = match.group(1).replace(",", "")
    recruit_count = match.group(2).replace(",", "")
    text = text.replace(match.group(0), "", 1).strip()
    return apply_count, recruit_count, normalize_text(text)


def extract_deadline(text: str) -> tuple[str | None, str]:
    text = normalize_text(text)
    match = DEADLINE_PATTERN.search(text)
    if not match:
        return None, text

    deadline_text = match.group(1)
    text = text.replace(match.group(0), "", 1).strip()
    return deadline_text, normalize_text(text)


def extract_benefit(text: str) -> tuple[str | None, str]:
    text = normalize_text(text)
    match = PRICE_PATTERN.search(text)
    if not match:
        return None, text

    benefit_text = match.group(1)
    text = text.replace(match.group(0), "", 1).strip()
    return benefit_text, normalize_text(text)


def strip_brackets(text: str) -> tuple[list[str], str]:
    text = normalize_text(text)
    tags = BRACKET_PATTERN.findall(text)
    stripped = BRACKET_PATTERN.sub("", text)
    return [tag.strip() for tag in tags if tag.strip()], normalize_text(stripped)


def remove_noise_words(text: str) -> str:
    text = normalize_text(text)

    changed = True
    while changed:
        changed = False
        for word in REMOVE_WORDS:
            if text.startswith(word):
                text = text[len(word):].strip(" +·:-")
                text = normalize_text(text)
                changed = True

    return normalize_text(text)


def clean_title(text: str) -> str | None:
    text = normalize_text(text)
    text = remove_noise_words(text)

    # 중간에 섞인 불필요 문구 제거
    replacements = [
        "체험단 모집",
        "체험단모집",
        "모집합니다!!",
        "모집합니다",
        "모집",
        "리뷰체험단",
    ]
    for item in replacements:
        text = text.replace(item, "")

    # 제목 끝 가격 숫자 제거
    text = re.sub(r"\s*[\d,]{3,}$", "", text).strip()

    # 깨진 '남음' 시작 텍스트 제거
    text = re.sub(r"^남음\s*", "", text).strip()

    text = normalize_text(text)

    if text in INVALID_TITLES:
        return None
    if len(text) < 2:
        return None

    return text


def parse_stylec_card_text(card_text: str) -> dict:
    raw = normalize_text(card_text)

    region_text, working = extract_region(raw)
    apply_count_text, recruit_count_text, working = extract_apply_counts(working)
    deadline_text, working = extract_deadline(working)
    benefit_text, working = extract_benefit(working)
    tags, working = strip_brackets(working)

    # 태그가 제목 앞 메타인 경우 제거
    working = remove_noise_words(working)

    # 제목 후보 정리
    campaign_title = clean_title(working)

    # region이 비어 있는데 태그 안에 지역성 텍스트가 있는 경우 보정
    if not region_text:
        for tag in tags:
            if any(loc in tag for loc in [
                "서울", "경기", "인천", "부산", "대구", "대전", "광주", "울산",
                "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남",
                "제주", "부천", "의정부", "강남", "명동", "이태원", "용산",
            ]):
                region_text = tag
                break

    return {
        "campaign_title": campaign_title,
        "campaign_type": "블로그",
        "region_text": region_text,
        "benefit_text": benefit_text,
        "deadline_text": deadline_text,
        "apply_count_text": apply_count_text,
        "recruit_count_text": recruit_count_text,
    }


class StyleCCrawler(BaseCrawler):
    def crawl(self) -> list[Campaign]:
        campaigns: list[Campaign] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)

            for page_number in range(1, settings.stylec_pages + 1):
                page_url = build_stylec_url(page_number)

                page = browser.new_page()
                page.goto(
                    page_url,
                    wait_until="domcontentloaded",
                    timeout=settings.timeout_ms,
                )
                page.wait_for_timeout(2500)

                html = page.content()
                raw_path = save_html(f"stylec_p{page_number}", html)

                links = page.locator("a").all()

                for link in links:
                    text = link.inner_text().strip()
                    href = link.get_attribute("href")

                    if not text:
                        continue

                    if not is_card_like_text(text):
                        continue

                    parsed = parse_stylec_card_text(text)
                    if not parsed["campaign_title"]:
                        continue

                    campaign_url = urljoin(page_url, href) if href else None

                    campaigns.append(
                        Campaign(
                            source_site="stylec",
                            source_page_url=page_url,
                            campaign_title=parsed["campaign_title"],
                            campaign_url=campaign_url,
                            campaign_type=parsed["campaign_type"],
                            region_text=parsed["region_text"],
                            benefit_text=parsed["benefit_text"],
                            deadline_text=parsed["deadline_text"],
                            apply_count_text=parsed["apply_count_text"],
                            recruit_count_text=parsed["recruit_count_text"],
                            raw_snapshot_path=raw_path,
                        )
                    )

                page.close()

            browser.close()

        # 중복 제거 강화
        unique = {}
        for item in campaigns:
            key = (
                item.campaign_title,
                item.deadline_text,
                item.apply_count_text,
                item.recruit_count_text,
                item.region_text,
            )
            unique[key] = item

        return list(unique.values())