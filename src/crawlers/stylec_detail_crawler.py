from datetime import datetime

import pandas as pd

from playwright.sync_api import (
    sync_playwright,
)

from src.parsers.stylec_detail_parser import (
    parse_stylec_detail,
)


class StylecDetailCrawler:

    def __init__(self):

        self.urls = [
            "https://www.stylec.co.kr/trials/107029",
            "https://www.stylec.co.kr/trials/106558",
            "https://www.stylec.co.kr/trials/106546",
        ]

    def crawl(self):

        results = []

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=False,
            )

            page = browser.new_page()

            for idx, url in enumerate(self.urls):

                print(f"\n===== DETAIL {idx+1} =====")
                print(url)

                try:

                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                    )

                    page.wait_for_timeout(3000)

                    body = page.locator(
                        "body"
                    ).inner_text()

                    detail = parse_stylec_detail(
                        body,
                        url,
                    )

                    print("\n=== PARSED RESULT ===")
                    print(
                        detail.model_dump()
                    )

                    result = detail.model_dump()

                    result["collected_at"] = (
                        datetime.now()
                    )

                    results.append(result)

                except Exception as e:

                    print(f"ERROR: {e}")

            browser.close()

        # CSV 저장
        df = pd.DataFrame(results)

        output_path = (
            "data/output/stylec_campaign_details.csv"
        )

        df.to_csv(
            output_path,
            index=False,
            encoding="utf-8-sig",
        )

        print("\n=== SAVE COMPLETE ===")
        print(output_path)