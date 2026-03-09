import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from src.config.settings import settings
from src.crawlers.base_crawler import BaseCrawler
from src.models.campaign import Campaign
from src.repositories.raw_repository import save_html


TITLE_PATTERN = re.compile(r"^\[(?P<prefix>[^\]]+)\]\s*(?P<title>.+)$")
DEADLINE_PATTERN = re.compile(r"(오늘 선정 마감|\d+\s*일\s*남음)")
APPLY_PATTERN = re.compile(r"신청\s*(\d+)\s*/\s*(\d+)")
POINT_PATTERN = re.compile(r"([\d,]+)\s*P")


def parse_title_parts(raw_title: str) -> tuple[str, str | None, str | None]:
    """
    예:
    [재택] 미닉스 더 플렌더 PRO 음식물 처리기
    -> campaign_title='미닉스 더 플렌더 PRO 음식물 처리기', campaign_type='재택', region_text=None

    [서울/마포구] 루프홍대점
    -> campaign_title='루프홍대점', campaign_type=None, region_text='서울/마포구'
    """
    matched = TITLE_PATTERN.match(raw_title.strip())
    if not matched:
        return raw_title.strip(), None, None

    prefix = matched.group("prefix").strip()
    title = matched.group("title").strip()

    if "/" in prefix:
        return title, None, prefix

    # 필요하면 여기에 규칙 추가 가능
    if prefix in {"재택", "전국"}:
        return title, prefix, None

    # 기본적으로는 유형으로 넣되, 불확실하면 원문 유지
    return title, prefix, None


def extract_card_fields(card_text: str) -> dict:
    lines = [line.strip() for line in card_text.splitlines() if line.strip()]

    deadline_text = None
    apply_count_text = None
    recruit_count_text = None
    campaign_type = None
    benefit_text = None
    point_text = None
    section_name = None

    for line in lines:
        if not deadline_text:
            m = DEADLINE_PATTERN.search(line)
            if m:
                deadline_text = m.group(1)

        if not apply_count_text or not recruit_count_text:
            m = APPLY_PATTERN.search(line)
            if m:
                apply_count_text = m.group(1)
                recruit_count_text = m.group(2)

        if line in {"방문형", "배송형"} and not campaign_type:
            campaign_type = line

        if not point_text:
            m = POINT_PATTERN.search(line)
            if m:
                point_text = m.group(1)

    # 제목 줄과 메타 줄 제외하고 혜택 문구 후보 찾기
    skip_keywords = {
        "방문형", "배송형", "더보기",
        "프리미엄 체험단", "인기 체험단", "마감 임박 체험단", "신규 체험단",
    }

    for line in lines:
        if line in skip_keywords:
            continue
        if DEADLINE_PATTERN.search(line):
            continue
        if APPLY_PATTERN.search(line):
            continue
        if TITLE_PATTERN.match(line):
            continue
        if POINT_PATTERN.fullmatch(line.replace(" ", "")):
            continue

        # 혜택처럼 보이는 첫 번째 문장 사용
        benefit_text = line
        break

    for line in lines:
        if line in {"프리미엄 체험단", "인기 체험단", "마감 임박 체험단", "신규 체험단"}:
            section_name = line
            break

    return {
        "deadline_text": deadline_text,
        "apply_count_text": apply_count_text,
        "recruit_count_text": recruit_count_text,
        "campaign_type_from_card": campaign_type,
        "benefit_text": benefit_text,
        "point_text": point_text,
        "section_name": section_name,
    }


class ReviewNoteCrawler(BaseCrawler):
    def crawl(self) -> list[Campaign]:
        campaigns: list[Campaign] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)
            page = browser.new_page()
            page.goto(
                settings.reviewnote_url,
                wait_until="networkidle",
                timeout=settings.timeout_ms,
            )

            html = page.content()
            raw_path = save_html("reviewnote", html)

            # 제목 링크만 우선
            links = page.locator("a[href*='/campaigns/']").all()

            for link in links:
                raw_title = link.inner_text().strip()
                href = link.get_attribute("href")

                if not raw_title:
                    continue
                if not raw_title.startswith("["):
                    continue

                campaign_url = urljoin(settings.reviewnote_url, href) if href else None

                title, title_type, region_text = parse_title_parts(raw_title)

                # 카드 부모를 위로 조금 올라가며 텍스트 확보
                card = link.locator("xpath=ancestor::*[self::li or self::div][1]")
                card_text = card.inner_text().strip() if card.count() else ""

                fields = extract_card_fields(card_text)

                campaigns.append(
                    Campaign(
                        source_site="reviewnote",
                        source_page_url=settings.reviewnote_url,
                        campaign_title=title,
                        campaign_url=campaign_url,
                        campaign_type=fields["campaign_type_from_card"] or title_type,
                        region_text=region_text,
                        benefit_text=fields["benefit_text"],
                        deadline_text=fields["deadline_text"],
                        apply_count_text=fields["apply_count_text"],
                        recruit_count_text=fields["recruit_count_text"],
                        section_name=fields["section_name"],
                        point_text=fields["point_text"],
                        raw_snapshot_path=raw_path,
                    )
                )

            browser.close()

        unique = {}
        for item in campaigns:
            unique[(item.campaign_title, item.campaign_url)] = item

        return list(unique.values())