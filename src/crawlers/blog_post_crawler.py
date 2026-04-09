from pathlib import Path

from src.config.settings import settings
from src.crawlers.base_crawler import BaseCrawler
from src.extractors.blog_post_extractor import extract_blog_post
from src.models.campaign import Campaign


class BlogPostCrawler(BaseCrawler):
    def __init__(self, source: str | None = None):
        self.source = source or settings.blog_html_path

    def crawl(self) -> list[Campaign]:
        source = self.source
        extracted = extract_blog_post(source, timeout_ms=settings.timeout_ms)

        if source.startswith(("http://", "https://")):
            source_page_url = source
        else:
            html_path = Path(source).resolve()
            source_page_url = html_path.as_uri()

        return [
            Campaign(
                source_site="blog",
                source_page_url=source_page_url,
                campaign_title=extracted["title"],
                content_text=extracted["content"],
            )
        ]
