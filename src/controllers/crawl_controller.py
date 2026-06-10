from loguru import logger

from src.api.schemas import BlogLinkCollectResult, CrawlResult
from src.crawlers.assaview_crawler import AssaViewCrawler
from src.crawlers.assaview_detail_crawler import AssaviewDetailCrawler
from src.crawlers.stylec_crawler import StyleCCrawler
from src.crawlers.stylec_detail_crawler import StylecDetailCrawler
from src.crawlers.naver_blog_link_crawler import NaverBlogLinkCrawler
from src.repositories.campaign_repository import save_campaigns_csv
from src.views.cli_view import print_campaigns


class CrawlController:

    def run_stylec(self, save_csv: bool = True) -> CrawlResult:
        logger.info("[stylec] 목록 크롤링 시작")
        campaigns = StyleCCrawler().crawl()
        logger.info(f"[stylec] 목록 {len(campaigns)}개 → 상세 크롤링")
        campaigns = StylecDetailCrawler().crawl(campaigns)

        print_campaigns(campaigns)
        output_file = None
        if save_csv:
            output_file = save_campaigns_csv("stylec_campaigns.csv", campaigns)
            logger.info(f"[stylec] 저장: {output_file}")

        return CrawlResult(
            site="stylec",
            count=len(campaigns),
            output_file=output_file,
            campaigns=campaigns,
        )

    def run_assaview(self, save_csv: bool = True) -> CrawlResult:
        logger.info("[assaview] 목록 크롤링 시작")
        campaigns = AssaViewCrawler().crawl()
        logger.info(f"[assaview] 목록 {len(campaigns)}개 → 상세 크롤링")
        campaigns = AssaviewDetailCrawler().crawl(campaigns)

        print_campaigns(campaigns)
        output_file = None
        if save_csv:
            output_file = save_campaigns_csv("assaview_campaigns.csv", campaigns)
            logger.info(f"[assaview] 저장: {output_file}")

        return CrawlResult(
            site="assaview",
            count=len(campaigns),
            output_file=output_file,
            campaigns=campaigns,
        )

    def run_all(self, save_csv: bool = True) -> list[CrawlResult]:
        return [
            self.run_stylec(save_csv),
            self.run_assaview(save_csv),
        ]

    def collect_blog_detail_links(self, url: str) -> BlogLinkCollectResult:
        logger.info(f"[blog] 링크 수집: {url}")
        return NaverBlogLinkCrawler().crawl(url)
