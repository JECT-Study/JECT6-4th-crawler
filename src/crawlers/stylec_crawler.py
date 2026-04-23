from src.crawlers.base_crawler import BaseCrawler
from src.models.campaign import Campaign


class StyleCCrawler(BaseCrawler):
    def crawl(self) -> list[Campaign]:
        return []