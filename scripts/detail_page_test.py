import pandas as pd

from playwright.sync_api import sync_playwright


CSV_PATH = "data/output/stylec_campaigns.csv"

df = pd.read_csv(CSV_PATH)

df = df[df["campaign_url"].notna()]

urls = df["campaign_url"].head(3).tolist()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    for idx, url in enumerate(urls):

        print(f"\n===== TEST {idx + 1} =====")
        print(url)

        page = browser.new_page()

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(3000)

            page.screenshot(
                path=f"data/raw/detail_{idx}.png",
                full_page=True
            )

            html = page.content()

            with open(
                f"data/raw/detail_{idx}.html",
                "w",
                encoding="utf-8"
            ) as f:
                f.write(html)

            body = page.locator("body").inner_text()

            print("\n=== BODY SAMPLE ===")
            print(body[:3000])

            print("\n=== IMAGE COUNT ===")
            print(page.locator("img").count())

            print("\n=== LINK COUNT ===")
            print(page.locator("a").count())

        except Exception as e:
            print("ERROR:", e)

        finally:
            page.close()

    browser.close()