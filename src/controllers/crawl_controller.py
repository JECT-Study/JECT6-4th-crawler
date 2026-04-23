from src.crawlers.assaview_crawler import AssaViewCrawler
from src.crawlers.stylec_crawler import StyleCCrawler
from src.repositories.campaign_repository import save_campaigns_csv
from src.views.cli_view import print_summary


class CrawlController:
    def run_assaview(self):
        crawler = AssaViewCrawler()
        campaigns = crawler.crawl()
        output = save_campaigns_csv("assaview_campaigns.csv", campaigns)
        print_summary("assaview", len(campaigns), output)

    def run_stylec(self):
        crawler = StyleCCrawler()
        campaigns = crawler.crawl()
        output = save_campaigns_csv("stylec_campaigns.csv", campaigns)
        print_summary("stylec", len(campaigns), output)

    def run_all(self):
        self.run_assaview()
        self.run_stylec()