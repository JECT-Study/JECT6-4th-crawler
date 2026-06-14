import os

import requests
from loguru import logger

from src.api.schemas import BlogLinkCollectResult, BlogPostCrawlResult, CrawlResult
from src.clients.stream_client import publish_blog_post, publish_campaign
from src.crawlers.assaview_crawler import AssaViewCrawler
from src.crawlers.assaview_detail_crawler import AssaviewDetailCrawler
from src.crawlers.stylec_crawler import StyleCCrawler
from src.crawlers.stylec_detail_crawler import StylecDetailCrawler
from src.crawlers.naver_blog_link_crawler import NaverBlogLinkCrawler
from src.models.campaign import Campaign
from src.repositories.campaign_repository import save_campaigns_csv
from src.views.cli_view import print_campaigns

_SPRING_API_URL = os.getenv("SPRING_API_URL", "http://localhost:8080")


def _send_to_spring(campaigns: list[Campaign]) -> None:
    if not campaigns:
        return
    payload = {
        "campaigns": [
            {
                "sourcePlatform": c.source_platform,
                "brandName": c.brand_name,
                "title": c.title,
                "thumbnailUrl": c.thumbnail_url,
                "category": c.category,
                "type": c.type,
                "channel": c.channel,
                "region": c.region_depth1,
                "providedContent": c.provided_content,
                "recruitCount": c.recruit_count,
                "applyStartDate": c.apply_start_date,
                "applyEndDate": c.apply_end_date,
                "mission": c.mission,
                "sourceUrl": c.source_url,
                "isGuaranteed": c.is_guaranteed,
            }
            for c in campaigns
            if c.source_url
        ]
    }
    try:
        url = f"{_SPRING_API_URL}/internal/campaigns/bulk"
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        saved = resp.json().get("data", {}).get("saved", "?")
        logger.info("spring_client: campaign bulk upsert 완료 saved={}", saved)
    except Exception as exc:
        logger.warning("spring_client: /internal/campaigns/bulk 실패 (best-effort) — {}", exc)


def _send_to_analyzer(campaigns: list[Campaign]) -> None:
    for campaign in campaigns:
        if not campaign.source_url:
            continue
        content = " ".join(filter(None, [
            campaign.title,
            campaign.provided_content,
            campaign.mission,
        ]))
        publish_campaign(
            source_url=campaign.source_url,
            title=campaign.title,
            content=content or campaign.title,
        )


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

        _send_to_spring(campaigns)
        _send_to_analyzer(campaigns)

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

        _send_to_spring(campaigns)
        _send_to_analyzer(campaigns)

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

    def run_blog_posts(self, blog_url: str) -> BlogPostCrawlResult:
        logger.info(f"[blog-posts] 포스트 크롤링 시작: {blog_url}")
        result = NaverBlogLinkCrawler().crawl(blog_url)
        for post in result.posts:
            publish_blog_post(url=post.post_url, title=post.title, content=post.content)
        logger.info(f"[blog-posts] 완료: {len(result.posts)}개 포스트")
        return BlogPostCrawlResult(blog_url=blog_url, count=len(result.posts))

    def collect_blog_detail_links(self, url: str) -> BlogLinkCollectResult:
        logger.info(f"[blog] 링크 수집: {url}")
        return NaverBlogLinkCrawler().crawl(url)
