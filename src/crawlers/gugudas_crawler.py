import re
from playwright.sync_api import sync_playwright

from src.config.settings import settings
from src.crawlers.base_crawler import BaseCrawler
from src.models.campaign import Campaign
from src.repositories.raw_repository import save_html


POINT_PATTERN = re.compile(r"^\d[\d,]*P$")
APPLY_PATTERN = re.compile(r"^신청\s*(\d+)\s*/\s*(\d+)명$")
DEADLINE_PATTERN = re.compile(r"^\d+일 남음$")
PRICE_PATTERN = re.compile(r"^\d[\d,]*원$")


class GugudasCrawler(BaseCrawler):
    def crawl(self) -> list[Campaign]:
        campaigns: list[Campaign] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto(
                settings.gugudas_url,
                wait_until="domcontentloaded",
                timeout=settings.timeout_ms,
            )

            page.wait_for_timeout(3000)
            page.screenshot(path="data/raw/gugudas_debug.png", full_page=True)

            html = page.content()
            raw_path = save_html("gugudas", html)

            body_lines = page.locator("body").inner_text().splitlines()
            lines = [line.strip() for line in body_lines if line.strip()]

            # 디버깅용 출력
            print("\n=== body text sample ===")
            for line in lines[:80]:
                print(line)

            i = 0
            while i < len(lines):
                line = lines[i]

                # 카드 시작점: 13,000P 같은 포인트 문구
                if not POINT_PATTERN.match(line):
                    i += 1
                    continue

                point_text = line
                platform = None
                category_text = None
                campaign_title = None
                apply_count_text = None
                recruit_count_text = None
                benefit_text = None
                deadline_text = None

                # 안전하게 다음 몇 줄만 본다
                window = lines[i:i + 10]

                # 예상 패턴
                # 0: 13,000P
                # 1: 구매평 스마트스토어
                # 2: [구매평] 다사마
                # 3: 텐셀 런 크루
                # 4: 신청 161 / 20명
                # 5: 실구매가
                # 6: 0원
                # 7: 13,000원
                # 8: 2일 남음

                if len(window) > 1:
                    platform = window[1]

                if len(window) > 2 and window[2].startswith("[") and "]" in window[2]:
                    prefix = window[2].split("]")[0].replace("[", "").strip()
                    category_text = prefix

                if len(window) > 3:
                    campaign_title = window[3]

                for w in window:
                    apply_match = APPLY_PATTERN.match(w)
                    if apply_match:
                        apply_count_text = apply_match.group(1)
                        recruit_count_text = apply_match.group(2)

                    if DEADLINE_PATTERN.match(w):
                        deadline_text = w

                # 가격 후보 중 마지막 금액을 benefit_text로 사용
                price_candidates = [w for w in window if PRICE_PATTERN.match(w)]
                if price_candidates:
                    benefit_text = price_candidates[-1]

                if campaign_title:
                    campaigns.append(
                        Campaign(
                            source_site="gugudas",
                            source_page_url=settings.gugudas_url,
                            campaign_title=campaign_title,
                            platform=platform,
                            point_text=point_text.replace("P", "").replace(",", ""),
                            category_text=category_text,
                            apply_count_text=apply_count_text,
                            recruit_count_text=recruit_count_text,
                            benefit_text=benefit_text,
                            deadline_text=deadline_text,
                            raw_snapshot_path=raw_path,
                        )
                    )

                i += 1

            browser.close()

        unique = {}
        for item in campaigns:
            key = (
                item.campaign_title,
                item.platform,
                item.point_text,
                item.deadline_text,
            )
            unique[key] = item

        return list(unique.values())