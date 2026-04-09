from src.crawlers.reviewnote_crawler import ReviewNoteCrawler
from src.crawlers.gugudas_crawler import GugudasCrawler
from src.crawlers.blog_post_crawler import BlogPostCrawler
from src.repositories.campaign_repository import save_campaigns_csv
from src.views.cli_view import print_summary


class CrawlController:
    def run_reviewnote(self):
        crawler = ReviewNoteCrawler()
        campaigns = crawler.crawl()
        output = save_campaigns_csv("reviewnote_campaigns.csv", campaigns)
        print_summary("reviewnote", len(campaigns), output)

    def run_gugudas(self):
        crawler = GugudasCrawler()
        campaigns = crawler.crawl()
        output = save_campaigns_csv("gugudas_campaigns.csv", campaigns)
        print_summary("gugudas", len(campaigns), output)

    def run_blog(self, source: str | None = None):
        crawler = BlogPostCrawler(source=source)
        campaigns = crawler.crawl()
        output = save_campaigns_csv("blog_post_campaigns.csv", campaigns)
        print_summary("blog", len(campaigns), output)

    def run_all(self):
        self.run_reviewnote()
        self.run_gugudas()