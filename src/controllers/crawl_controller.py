from __future__ import annotations

import os

import requests
from loguru import logger

from src.api.schemas import (
    BlogLinkCollectResult,
    BlogPostCrawlResult,
    CrawlResult,
    ExtBlogBatchIngestItem,
    ExtBlogBatchIngestItemResult,
    ExtBlogBatchIngestResult,
)
from src.clients.stream_client import DEFAULT_USER_ID, publish_blog_post, publish_campaign, publish_ext_blog_post
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

    def run_blog_posts(
        self,
        blog_url: str,
        user_id: int = DEFAULT_USER_ID,
        blog_id: int | None = None,
        correlation_id: str | None = None,
        analysis_mode: str = "FULL_BLOG",
        batch_id: str | None = None,
    ) -> BlogPostCrawlResult:
        logger.info(
            f"[blog-posts] 포스트 크롤링 시작: {blog_url} user_id={user_id} "
            f"mode={analysis_mode} correlation_id={correlation_id} batch_id={batch_id}"
        )
        result = NaverBlogLinkCrawler().crawl(blog_url)
        expected_count = len(result.posts)
        for i, post in enumerate(result.posts):
            publish_blog_post(
                url=post.post_url,
                title=post.title,
                content=post.content,
                user_id=user_id,
                blog_id=blog_id,
                correlation_id=correlation_id,
                analysis_mode=analysis_mode,
                batch_id=batch_id,
                expected_count=expected_count,
                post_index=i,
            )
        logger.info(f"[blog-posts] 완료: {expected_count}개 포스트 mode={analysis_mode}")
        return BlogPostCrawlResult(blog_url=blog_url, count=expected_count)

    def collect_blog_detail_links(
        self,
        url: str,
        publish_to_analyzer: bool = False,
        user_id: int | None = None,
        nickname: str | None = None,
        category: str | None = None,
        max_posts: int | None = None,
    ) -> BlogLinkCollectResult:
        logger.info(f"[blog] 링크 수집: {url} publish={publish_to_analyzer}")
        result = NaverBlogLinkCrawler().crawl(url)

        posts = result.posts
        if max_posts is not None:
            posts = posts[:max_posts]

        published_count = 0
        if publish_to_analyzer:
            effective_user_id = user_id if user_id is not None else DEFAULT_USER_ID
            for post in posts:
                publish_ext_blog_post(
                    url=post.post_url,
                    title=post.title,
                    content=post.content,
                    user_id=effective_user_id,
                    nickname=nickname,
                    category=category,
                    source_blog_url=url,
                )
                published_count += 1
            logger.info(f"[blog] ext_blog publish 완료: {published_count}개 url={url}")

        return BlogLinkCollectResult(
            source_url=result.source_url,
            resolved_list_url=result.resolved_list_url,
            blog_id=result.blog_id,
            blog_owner_name=result.blog_owner_name,
            count=len(posts),
            published_count=published_count,
            detail_urls=result.detail_urls[:len(posts)],
            posts=posts,
        )

    def ingest_influencer_blogs(
        self,
        blogs: list[ExtBlogBatchIngestItem],
        user_id: int | None = None,
        max_posts_per_blog: int = 20,
    ) -> ExtBlogBatchIngestResult:
        """여러 인플루언서 블로그를 순차 수집하여 ext_blog로 Analyzer에 적재한다."""
        effective_user_id = user_id if user_id is not None else DEFAULT_USER_ID
        item_results: list[ExtBlogBatchIngestItemResult] = []
        total_published = 0

        for blog in blogs:
            try:
                result = NaverBlogLinkCrawler().crawl(blog.blog_url)
                posts = result.posts[:max_posts_per_blog]
                published = 0
                for post in posts:
                    publish_ext_blog_post(
                        url=post.post_url,
                        title=post.title,
                        content=post.content,
                        user_id=effective_user_id,
                        nickname=blog.nickname,
                        category=blog.category,
                        source_blog_url=blog.blog_url,
                    )
                    published += 1
                total_published += published
                item_results.append(
                    ExtBlogBatchIngestItemResult(
                        blog_url=blog.blog_url,
                        nickname=blog.nickname,
                        published_count=published,
                    )
                )
                logger.info(f"[ext-posts] 완료: {blog.blog_url} published={published}")
            except Exception as exc:
                logger.warning(f"[ext-posts] 실패: {blog.blog_url} err={exc}")
                item_results.append(
                    ExtBlogBatchIngestItemResult(
                        blog_url=blog.blog_url,
                        nickname=blog.nickname,
                        published_count=0,
                        error=str(exc),
                    )
                )

        return ExtBlogBatchIngestResult(
            total_blogs=len(blogs),
            total_published=total_published,
            results=item_results,
        )
