import re
from datetime import date, timedelta
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup
from loguru import logger

from src.config.settings import settings
from src.crawlers.base_crawler import BaseCrawler
from src.models.campaign import Campaign
from src.repositories.raw_repository import save_html

BASE_URL = "https://assaview.co.kr/"
LIST_URL = "https://assaview.co.kr/campaign_list.php?type=product"

TYPE_MAP = {
    "배송형": "DELIVERY",
    "구매형": "REVIEW",
    "방문형": "VISIT",
    "기자단": "REPORTER",
    "리뷰형": "REVIEW",
}


def _resolve_deadline_date(deadline_text: str | None) -> str | None:
    """목록에 노출되는 상대적 마감 표기("3일 남음" 등)를 실제 날짜(YYYY-MM-DD)로 변환한다.

    상세 페이지의 모집기간 영역이 더 이상 정적 HTML에 존재하지 않아(사이트 구조 변경),
    절대 날짜를 얻을 방법이 이 상대 표기뿐이다.
    """
    if not deadline_text:
        return None
    if deadline_text in ("오늘마감", "마감임박"):
        return date.today().isoformat()
    m = re.match(r"(\d+)일 남음", deadline_text)
    if m:
        return (date.today() + timedelta(days=int(m.group(1)))).isoformat()
    return None

CATEGORY_MAP = {
    "식품": "FOOD", "푸드": "FOOD", "음식": "FOOD", "빵": "FOOD", "쿠키": "FOOD",
    "뷰티": "BEAUTY", "화장품": "BEAUTY", "스킨": "BEAUTY", "크림": "BEAUTY",
    "패션": "FASHION", "의류": "FASHION", "티셔츠": "FASHION", "원피스": "FASHION",
    "생활": "LIVING", "가전": "LIVING", "가구": "LIVING", "소파": "LIVING", "이불": "LIVING",
    "펫": "PET", "반려": "PET", "강아지": "PET", "고양이": "PET",
    "테크": "TECH_IT", "IT": "TECH_IT", "전자": "TECH_IT",
    "여행": "TRAVEL", "숙박": "TRAVEL", "호텔": "TRAVEL",
    "문화": "CULTURE",
}


def infer_category(title: str) -> str:
    for keyword, category in CATEGORY_MAP.items():
        if keyword in title:
            return category
    return "ETC"


def extract_cards_from_page(page: Page) -> list[dict]:
    return page.evaluate("""
        () => {
            const results = [];
            const seen = new Set();
            const links = document.querySelectorAll('a[href*="campaign.php?cp_id="]');

            links.forEach(a => {
                const href = a.getAttribute('href');
                if (!href || seen.has(href)) return;
                seen.add(href);

                // review_type_icon 제외한 첫 번째 img
                let thumbSrc = '';
                const imgs = a.querySelectorAll('img');
                for (const img of imgs) {
                    if (img.classList.contains('review_type_icon')) continue;
                    const src = img.getAttribute('src') || '';
                    if (src) {
                        thumbSrc = src.startsWith('./') ? src.slice(2) : src;
                        break;
                    }
                }

                const text = a.innerText || '';
                results.push({ href, thumbSrc, text });
            });

            return results;
        }
    """)


def parse_card_data(card: dict) -> Campaign | None:
    href = card.get("href", "")
    if not href:
        return None

    source_url = urljoin(BASE_URL, href)
    full_text = card.get("text", "").strip()
    thumb_src = card.get("thumbSrc", "")

    # 썸네일
    thumbnail_url = urljoin(BASE_URL, thumb_src) if thumb_src else None
    # 일부 파일명이 유니코드 바이트 시퀀스로 인코딩되어 DB 컬럼(VARCHAR(255))을 초과하는 경우가 있다.
    # 자르면 깨진 URL이 되므로 초과 시 통째로 비운다.
    if thumbnail_url and len(thumbnail_url) > 255:
        thumbnail_url = None

    # 캠페인 타입
    type_match = re.search(r"(배송형|구매형|방문형|기자단|리뷰형)", full_text)
    raw_type = type_match.group(1) if type_match else None
    campaign_type = TYPE_MAP.get(raw_type, "DELIVERY") if raw_type else "DELIVERY"

    # 마감일
    deadline = None
    d_match = re.search(r"(오늘마감|\d+일 남음|마감임박)", full_text)
    if d_match:
        deadline = d_match.group(1)

    # 신청/모집 인원
    apply_count = recruit_count = None
    a_match = re.search(r"신청\s*([\d,]+)\s*/\s*([\d,]+)\s*명", full_text)
    if a_match:
        apply_count = int(a_match.group(1).replace(",", ""))
        recruit_count = int(a_match.group(2).replace(",", ""))

    # 포인트/제공 내용
    provided_content = None
    p_match = re.search(r"([\d,]+)\s*P(?:\s|$)", full_text)
    if p_match:
        provided_content = f"{p_match.group(1)}P"

    price_match = re.search(r"\[([\d,]+원)\s*상당\]|\[(배송비 포함[\d,]+원)\]", full_text)
    if price_match:
        provided_content = price_match.group(1) or price_match.group(2)

    # 제목 정제
    title_text = full_text
    for pattern in [
        r"(배송형|구매형|방문형|기자단|리뷰형)",
        r"(오늘마감|\d+일 남음|마감임박)",
        r"신청\s*[\d,]+\s*/\s*[\d,]+\s*명",
        r"[\d,]+\s*P(?:\s|$)",
        r"참여 조건.*",
        r"\[배송비 포함[\d,]+원\]",
        r"\[[\d,]+원 상당\]",
        r"아싸뷰 원고료",
    ]:
        title_text = re.sub(pattern, "", title_text)
    title_text = re.sub(r"\s+", " ", title_text).strip()

    if len(title_text) < 4:
        chunks = re.findall(r"[가-힣a-zA-Z0-9 ]{6,}", full_text)
        chunks = [c.strip() for c in chunks if len(c.strip()) >= 6]
        chunks = [c for c in chunks if not re.match(
            r"^(배송형|구매형|방문형|기자단|신청|참여|오늘)", c
        )]
        title_text = max(chunks, key=len) if chunks else full_text[:50]

    if not title_text or len(title_text) < 2:
        return None

    # 브랜드명
    brand_name = None
    b_match = re.search(r"^\[([^\]]+)\]", title_text)
    if b_match:
        brand_name = b_match.group(1).strip()

    # 100% 당첨
    is_guaranteed = bool(
        recruit_count and apply_count is not None and apply_count < recruit_count
    )

    return Campaign(
        source_platform="ASSAVIEW",
        source_url=source_url,
        brand_name=brand_name,
        title=title_text[:200],
        thumbnail_url=thumbnail_url,
        category=infer_category(title_text),
        type=campaign_type,
        channel="BLOG",
        provided_content=provided_content,
        recruit_count=recruit_count,
        apply_count=apply_count,
        apply_end_date=_resolve_deadline_date(deadline),
        is_guaranteed=is_guaranteed,
        status="ACTIVE",
    )


class AssaViewCrawler(BaseCrawler):

    def crawl(self) -> list[Campaign]:
        all_campaigns: list[Campaign] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)
            page = browser.new_page()

            logger.info(f"[assaview] 목록 로드: {LIST_URL}")
            page.goto(LIST_URL, wait_until="domcontentloaded", timeout=settings.timeout_ms)
            page.wait_for_timeout(2500)

            prev_count = 0
            no_change_count = 0
            scroll_count = 0
            max_scrolls = 30

            while scroll_count < max_scrolls:
                cards = extract_cards_from_page(page)
                current_count = len(cards)
                logger.info(f"[assaview] 스크롤 {scroll_count}: {current_count}개")

                if current_count == prev_count:
                    no_change_count += 1
                    if no_change_count >= 3:
                        logger.info("[assaview] 더 이상 새 항목 없음 — 종료")
                        break
                else:
                    no_change_count = 0
                    prev_count = current_count

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1500)
                scroll_count += 1

            # 최종 수집
            final_cards = extract_cards_from_page(page)
            save_html("assaview_final", page.content())

            for card in final_cards:
                campaign = parse_card_data(card)
                if campaign:
                    all_campaigns.append(campaign)

            browser.close()

        unique = {c.source_url: c for c in all_campaigns if c.source_url}
        result = list(unique.values())
        logger.info(f"[assaview] 총 {len(result)}개 수집 완료")
        return result