from urllib.parse import urlparse, parse_qs, urljoin

from playwright.sync_api import sync_playwright
from loguru import logger

from src.api.schemas import BlogLinkCollectResult
from src.config.settings import settings


class NaverBlogLinkCrawler:

    def crawl(self, url: str) -> BlogLinkCollectResult:
        detail_urls = []
        blog_id = self._extract_blog_id(url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=settings.headless)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=settings.timeout_ms)
            page.wait_for_timeout(2000)

            resolved_url = page.url

            # 네이버 블로그는 iframe 구조 — 내부 frame에서 링크 수집
            frames = page.frames
            for frame in frames:
                links = frame.locator("a").all()
                for link in links:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    full_url = urljoin("https://blog.naver.com", href)
                    if "PostView" in full_url and blog_id in full_url:
                        if full_url not in detail_urls:
                            detail_urls.append(full_url)

            browser.close()

        logger.info(f"[blog] {len(detail_urls)}개 링크 수집 완료")
        for u in detail_urls:
            logger.info(f"  {u}")

        return BlogLinkCollectResult(
            source_url=url,
            resolved_list_url=resolved_url,
            blog_id=blog_id,
            count=len(detail_urls),
            detail_urls=detail_urls,
        )

    def _extract_blog_id(self, url: str) -> str:
        qs = parse_qs(urlparse(url).query)
        return qs.get("blogId", ["unknown"])[0]