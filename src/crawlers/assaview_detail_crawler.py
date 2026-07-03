import re

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from loguru import logger

from src.config.settings import settings
from src.models.campaign import Campaign
from src.repositories.raw_repository import save_html


def parse_assaview_detail(html: str, source_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    result = {}

    apply_area = soup.find("article", class_="apply_area")

    if apply_area:
        dls = apply_area.find_all("dl")
        for dl in dls:
            dds = dl.find_all("dd")

            if len(dds) >= 2:
                label = dds[0].get_text(strip=True)
                value = dds[1].get_text(strip=True)

                if "모집기간" in label and "~" in value:
                    start, end = value.split("~", 1)
                    result["apply_start_date"] = start.strip()
                    result["apply_end_date"] = end.strip()
                elif "선정자 발표" in label:
                    result["announce_date"] = value
                elif "리뷰 제출 기한" in label:
                    result["review_deadline"] = value
                elif "구매 내역 제출 기한" in label:
                    result["purchase_end"] = value

            elif len(dds) == 1:
                dl_text = dl.get_text(separator="|", strip=True)
                if "모집기간" in dl_text and "~" in dl_text:
                    parts = dl_text.split("|")
                    for part in parts:
                        if "~" in part and re.search(r"\d+\.\d+", part):
                            start, end = part.split("~", 1)
                            result["apply_start_date"] = start.strip()
                            result["apply_end_date"] = end.strip()
                            break

        # dl 외부에서 날짜 탐색 (구조가 다른 경우 보완)
        if "apply_start_date" not in result:
            full_text = apply_area.get_text(separator="\n", strip=True)
            m = re.search(
                r"모집기간\s*[\n|]?\s*(\d{2}\.\d{2})\s*~\s*(\d{2}\.\d{2})",
                full_text,
            )
            if m:
                result["apply_start_date"] = m.group(1)
                result["apply_end_date"] = m.group(2)

        recruit_el = apply_area.find("span", class_="accent_color")
        if recruit_el:
            recruit_text = recruit_el.get_text(strip=True)
            m = re.search(r"(\d+)명", recruit_text)
            if m:
                result["recruit_count"] = int(m.group(1))

    # 신청/모집 인원
    for div in soup.find_all("div"):
        text = div.get_text(" ", strip=True)
        m = re.search(r"신청\s*([\d,]+)\s*/\s*([\d,]+)\s*명", text)
        if m:
            result["apply_count"] = int(m.group(1).replace(",", ""))
            if "recruit_count" not in result:
                result["recruit_count"] = int(m.group(2).replace(",", ""))
            break

    # 미션 키워드/가이드 추출
    mission_sections = soup.find_all("div", class_="head_text")

    for section in mission_sections:
        label = section.get_text(strip=True)
        parent = section.parent

        if not parent:
            continue

        full_text = parent.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]

        if "제목 키워드" in label:
            result["title_keywords"] = extract_section_value(
                lines,
                start_keyword="제목 키워드",
                stop_keywords=["본문 키워드", "미션 가이드", "유의사항"],
            )

        elif "본문 키워드" in label:
            result["search_keywords"] = extract_section_value(
                lines,
                start_keyword="본문 키워드",
                stop_keywords=["제목 키워드", "미션 가이드", "유의사항"],
            )

        elif "미션 가이드" in label:
            mission_text = extract_multiline_section(
                lines,
                start_keyword="미션 가이드",
                stop_keywords=["제목 키워드", "본문 키워드", "유의사항", "캠페인 신청하기"],
            )
            # DB 컬럼이 VARCHAR(255)라 초과분은 잘라낸다.
            result["mission"] = mission_text[:255] if mission_text else mission_text

    return result


def extract_section_value(
    lines: list[str],
    start_keyword: str,
    stop_keywords: list[str],
) -> str | None:
    started = False

    for line in lines:
        if start_keyword in line:
            started = True
            continue

        if not started:
            continue

        if any(keyword in line for keyword in stop_keywords):
            break

        if "✓" in line:
            continue

        if line:
            return line.strip()

    return None


def extract_multiline_section(
    lines: list[str],
    start_keyword: str,
    stop_keywords: list[str],
) -> str | None:
    started = False
    collected = []

    for line in lines:
        if start_keyword in line:
            started = True
            continue

        if not started:
            continue

        if any(keyword in line for keyword in stop_keywords):
            break

        if line:
            collected.append(line.strip())

    return "\n".join(collected) if collected else None


class AssaviewDetailCrawler:

    def crawl(self, campaigns: list[Campaign]) -> list[Campaign]:
        logger.info(f"[assaview-detail] 상세 크롤링 시작: {len(campaigns)}개")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)
            page = browser.new_page()

            detail_map: dict[str, dict] = {}

            for idx, campaign in enumerate(campaigns, 1):
                url = campaign.source_url
                logger.info(f"[assaview-detail] ({idx}/{len(campaigns)}) {url}")

                try:
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=settings.timeout_ms,
                    )
                    page.wait_for_timeout(1500)

                    html = page.content()

                    if idx <= 5:
                        cp_id = re.search(r"cp_id=(\d+)", url)
                        if cp_id:
                            save_html(f"assaview_detail_{cp_id.group(1)}", html)

                    detail = parse_assaview_detail(html, url)
                    detail_map[url] = detail

                except Exception as e:
                    logger.warning(f"[assaview-detail] 실패 {url}: {e}")

                page.wait_for_timeout(300)

            browser.close()

        # campaigns에 상세 정보 병합
        enriched = []

        for campaign in campaigns:
            detail = detail_map.get(campaign.source_url, {})

            if not detail:
                enriched.append(campaign)
                continue

            update = {}

            if detail.get("apply_start_date"):
                update["apply_start_date"] = detail["apply_start_date"]

            if detail.get("apply_end_date"):
                update["apply_end_date"] = detail["apply_end_date"]

            if detail.get("announce_date"):
                update["announce_date"] = detail["announce_date"]

            if detail.get("purchase_end"):
                update["purchase_end"] = detail["purchase_end"]

            if detail.get("review_deadline"):
                update["review_deadline"] = detail["review_deadline"]

            if detail.get("recruit_count"):
                update["recruit_count"] = detail["recruit_count"]

            if detail.get("apply_count"):
                update["apply_count"] = detail["apply_count"]

            keywords = []
            if detail.get("title_keywords"):
                keywords.append(detail["title_keywords"])
            if detail.get("search_keywords"):
                keywords.append(detail["search_keywords"])
            if keywords:
                update["search_keywords"] = " / ".join(keywords)

            if detail.get("mission"):
                update["mission"] = detail["mission"]

            enriched.append(
                campaign.model_copy(update=update) if update else campaign
            )

        logger.info(f"[assaview-detail] 완료: {len(enriched)}개")
        return enriched