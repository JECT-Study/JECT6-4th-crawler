from src.crawlers.assaview_crawler import AssaViewCrawler
from src.crawlers.naver_blog_link_crawler import NaverBlogLinkCrawler
from src.crawlers.stylec_crawler import StyleCCrawler
from src.models.campaign import Campaign
from src.repositories.campaign_repository import save_campaigns_csv
from src.views.cli_view import print_summary


class CrawlController:
    def run_assaview(self, save_csv: bool = True) -> dict:
        crawler = AssaViewCrawler()
        campaigns = crawler.crawl()
        output = self._save_if_needed("assaview_campaigns.csv", campaigns, save_csv)
        if save_csv:
            print_summary("assaview", len(campaigns), output)
        return self._build_result("assaview", campaigns, output)

    def run_stylec(self, save_csv: bool = True) -> dict:
        crawler = StyleCCrawler()
        campaigns = crawler.crawl()
        output = self._save_if_needed("stylec_campaigns.csv", campaigns, save_csv)
        if save_csv:
            print_summary("stylec", len(campaigns), output)
        return self._build_result("stylec", campaigns, output)

    def run_all(self, save_csv: bool = True) -> list[dict]:
        return [
            self.run_assaview(save_csv=save_csv),
            self.run_stylec(save_csv=save_csv),
        ]

    def collect_blog_detail_links(self, url: str) -> dict:
        crawler = NaverBlogLinkCrawler()
        return crawler.collect(url)

    @staticmethod
    def _save_if_needed(filename: str, campaigns: list[Campaign], save_csv: bool) -> str | None:
        if not save_csv:
            return None
        return save_campaigns_csv(filename, campaigns)

    @staticmethod
    def _build_result(site: str, campaigns: list[Campaign], output_file: str | None) -> dict:
        return {
            "site": site,
            "count": len(campaigns),
            "output_file": output_file,
            "campaigns": campaigns,
        }
