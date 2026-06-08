import json
import re

from playwright.sync_api import sync_playwright
from loguru import logger

from src.config.settings import settings
from src.models.campaign import Campaign
from src.repositories.raw_repository import save_html

BASE_URL = "https://www.stylec.co.kr/"
DETAIL_API = "https://api2.stylec.co.kr:6439/v1/trial/detail"


class StylecDetailCrawler:

    def crawl(self, campaigns: list[Campaign]) -> list[Campaign]:
        # source_url에서 wr_id 추출
        targets = []
        for c in campaigns:
            match = re.search(r"/trials/(\d+)", c.source_url)
            if match:
                targets.append((c, match.group(1)))

        logger.info(f"[stylec-detail] 상세 크롤링 시작: {len(targets)}개")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)
            context = browser.new_context()
            page = context.new_page()

            # 세션 확보
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=settings.timeout_ms)
            page.wait_for_timeout(1500)

            detail_map: dict[str, dict] = {}

            for idx, (campaign, wr_id) in enumerate(targets, 1):
                logger.info(f"[stylec-detail] ({idx}/{len(targets)}) wr_id={wr_id}")
                try:
                    resp = page.evaluate(f"""
                        async () => {{
                            const res = await fetch('{DETAIL_API}?wr_id={wr_id}');
                            return await res.json();
                        }}
                    """)

                    data = resp.get("data", {})
                    if not data:
                        logger.warning(f"[stylec-detail] 빈 응답: wr_id={wr_id}")
                        continue

                    save_html(f"stylec_detail_{wr_id}", json.dumps(resp, ensure_ascii=False))
                    detail_map[campaign.source_url] = data

                except Exception as e:
                    logger.warning(f"[stylec-detail] 실패 wr_id={wr_id}: {e}")

                page.wait_for_timeout(300)

            browser.close()

        # 상세 정보 병합
        enriched = []
        for campaign in campaigns:
            data = detail_map.get(campaign.source_url)
            if not data:
                enriched.append(campaign)
                continue

            enriched.append(campaign.model_copy(update={
                "apply_start_date": data.get("tr_recruit_start"),
                "apply_end_date": data.get("tr_recruit_finish"),
                "announce_date": data.get("tr_winners_announce"),
                "purchase_start": data.get("tr_buy_start"),
                "purchase_end": data.get("tr_buy_finish"),
                "review_deadline": data.get("tr_enroll_finish"),
                "mission": data.get("tr_plus_certify_label"),
                "provided_content": data.get("tr_it_name") or campaign.provided_content,
                "recruit_count": data.get("tr_recruit_max") or campaign.recruit_count,
                "apply_count": data.get("tr_enroll_cnt") or campaign.apply_count,
            }))

        logger.info(f"[stylec-detail] 완료: {len(enriched)}개")
        return enriched