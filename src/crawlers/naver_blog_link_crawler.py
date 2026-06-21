from __future__ import annotations

import re
import time
from collections import deque
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger

from src.api.schemas import BlogLinkCollectResult
from src.config.settings import settings


class NaverBlogLinkCrawler:
    MAX_DETAIL_LINKS = 20

    blog_id_pattern = re.compile(r"var blogId = '([^']+)'")
    log_no_patterns = (
        re.compile(r"logNo=(\d+)"),
        re.compile(r"logNo\s*:\s*'(\d+)'"),
        re.compile(r"PostView\.naver\?blogId=[^\"'&]+&logNo=(\d+)"),
    )
    count_patterns = {
        "like_count": (
            re.compile(r'"sympathyCount"\s*:\s*"?([\d,]+)"?', re.IGNORECASE),
            re.compile(r'"likeCount"\s*:\s*"?([\d,]+)"?', re.IGNORECASE),
            re.compile(r"sympathyCount\s*[:=]\s*'?([\d,]+)'?", re.IGNORECASE),
        ),
        "comment_count": (
            re.compile(r'"commentCount"\s*:\s*"?([\d,]+)"?', re.IGNORECASE),
            re.compile(r"commentCount\s*[:=]\s*'?([\d,]+)'?", re.IGNORECASE),
            re.compile(r"commentCnt\s*[:=]\s*'?([\d,]+)'?", re.IGNORECASE),
        ),
    }

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.default_user_agent})
        self._last_request_at = 0.0

    def crawl(self, source_url: str) -> BlogLinkCollectResult:
        logger.info("네이버 블로그 상세 글 수집 시작: {}", source_url)
        initial_html = self._fetch_text(source_url)
        first_list_url, first_list_html = self._resolve_list_page(source_url, initial_html)
        blog_id = self._extract_blog_id(source_url, first_list_url, first_list_html)
        category_no = self._extract_category_no(source_url, first_list_url)
        blog_owner_name = self._extract_blog_owner_name(first_list_html, blog_id)
        logger.info("목록 페이지 확인 완료: blogId={}, listUrl={}", blog_id, first_list_url)

        detail_urls = self._collect_all_detail_urls(blog_id, category_no, first_list_url, first_list_html)

        logger.info("네이버 블로그 상세 링크 수집 완료: blogId={}, count={}", blog_id, len(detail_urls))
        for index, detail_url in enumerate(detail_urls, start=1):
            logger.info("상세 링크 {}: {}", index, detail_url)

        posts = self._collect_posts(detail_urls)

        return BlogLinkCollectResult(
            source_url=source_url,
            resolved_list_url=first_list_url,
            blog_id=blog_id,
            blog_owner_name=blog_owner_name,
            count=len(posts),
            detail_urls=detail_urls,
            posts=posts,
        )

    def _collect_posts(self, detail_urls: list[str]) -> list[dict]:
        posts: list[dict] = []
        for index, detail_url in enumerate(detail_urls, start=1):
            logger.info("상세 글 요청 시작: index={}, url={}", index, detail_url)
            html = self._fetch_text(detail_url)
            post = self._extract_post(detail_url, html)
            posts.append(post)
            logger.info("상세 글 요청 완료: index={}, title={}", index, post["title"])
        return posts

    def _extract_post(self, detail_url: str, html: str) -> dict:
        soup = BeautifulSoup(html, "lxml")
        content = self._select_post_content(soup)
        title = self._extract_title(soup, content)
        thumbnail_image_url = self._extract_thumbnail_image_url(detail_url, soup, content)
        body = self._extract_text_content(content)
        html_like_count = self._extract_count(soup, html, "like_count")
        api_like_count = self._fetch_like_count(detail_url, soup)
        like_count = api_like_count if api_like_count is not None else html_like_count
        comment_count = self._extract_count(soup, html, "comment_count")

        return {
            "url": detail_url,
            "post_url": detail_url,
            "title": title,
            "thumbnail_image_url": thumbnail_image_url,
            "like_count": like_count,
            "comment_count": comment_count,
            "content": body,
        }

    def _collect_all_detail_urls(
        self,
        blog_id: str,
        category_no: str | None,
        first_list_url: str,
        first_list_html: str,
    ) -> list[str]:
        queue: deque[tuple[str, str | None]] = deque([(first_list_url, first_list_html)])
        visited_pages: set[str] = set()
        seen_log_nos: set[str] = set()
        ordered_log_nos: list[str] = []
        page_index = 0

        while queue and len(ordered_log_nos) < self.MAX_DETAIL_LINKS:
            page_url, cached_html = queue.popleft()
            normalized_page_url = self._normalize_page_url(page_url)
            if normalized_page_url in visited_pages:
                continue

            visited_pages.add(normalized_page_url)
            page_index += 1
            logger.info("목록 페이지 방문 시작: pageIndex={}, queueSize={}, url={}", page_index, len(queue), page_url)

            html = cached_html if cached_html is not None else self._fetch_text(page_url)
            page_log_nos = self._extract_log_nos_from_html(blog_id, page_url, html)

            new_count = 0
            for log_no in page_log_nos:
                if log_no in seen_log_nos:
                    continue
                seen_log_nos.add(log_no)
                ordered_log_nos.append(log_no)
                new_count += 1
                if len(ordered_log_nos) >= self.MAX_DETAIL_LINKS:
                    break

            if len(ordered_log_nos) >= self.MAX_DETAIL_LINKS:
                logger.info("상세 링크 제한 도달: blogId={}, limit={}", blog_id, self.MAX_DETAIL_LINKS)
                break

            next_page_urls = self._extract_pagination_links(blog_id, category_no, page_url, html)
            added_pages = 0
            for next_page_url in next_page_urls:
                normalized_next = self._normalize_page_url(next_page_url)
                if normalized_next in visited_pages:
                    continue
                queue.append((next_page_url, None))
                added_pages += 1

            logger.info(
                "목록 페이지 방문 완료: pageIndex={}, newDetailLinks={}, totalDetailLinks={}, discoveredPages={}, queueSize={}",
                page_index,
                new_count,
                len(ordered_log_nos),
                added_pages,
                len(queue),
            )

        return [
            f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
            for log_no in ordered_log_nos
        ]

    def _resolve_list_page(self, source_url: str, html: str) -> tuple[str, str]:
        soup = BeautifulSoup(html, "lxml")
        frame = soup.select_one("iframe#mainFrame")
        if frame is None or not frame.get("src"):
            return source_url, html

        resolved_url = urljoin(source_url, frame["src"])
        logger.info("프레임 목록 페이지로 이동: {}", resolved_url)
        return resolved_url, self._fetch_text(resolved_url)

    def _extract_blog_owner_name(self, html: str, fallback: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        selectors = (
            ".blog_title",
            ".nick",
            ".nickname",
            "#blogTitleName",
            "#nickNameArea",
            "meta[property='og:title']",
            "title",
        )
        for selector in selectors:
            element = soup.select_one(selector)
            if element is None:
                continue

            value = element.get("content") if element.name == "meta" else element.get_text(" ", strip=True)
            normalized = self._normalize_blog_owner_name(value)
            if normalized:
                return normalized

        match = re.search(r"var\s+nickName\s*=\s*'([^']+)'", html)
        if match:
            normalized = self._normalize_blog_owner_name(match.group(1))
            if normalized:
                return normalized

        return fallback

    @staticmethod
    def _normalize_blog_owner_name(value: str | None) -> str:
        if not value:
            return ""

        normalized = re.sub(r"\s*:\s*네이버\s+블로그\s*$", "", value).strip()
        normalized = re.sub(r"\s*-\s*네이버\s+블로그\s*$", "", normalized).strip()
        normalized = normalized.replace("네이버 블로그", "").strip()
        return normalized

    @staticmethod
    def _select_post_content(soup: BeautifulSoup):
        selectors = (
            "div.se-main-container",
            "div#postViewArea",
            "div.post_ct",
            "div.post-view",
            "body",
        )
        for selector in selectors:
            content = soup.select_one(selector)
            if content is not None:
                return content
        return soup

    @staticmethod
    def _extract_title(soup: BeautifulSoup, content) -> str:
        selectors = (
            "div.se-title-text span",
            "div.se-title-text",
            "h3.se_textarea",
            "h3.title",
            "title",
        )
        for selector in selectors:
            element = soup.select_one(selector)
            if element is None:
                continue
            title = element.get_text(" ", strip=True)
            if title:
                return title

        heading = content.find(["h1", "h2", "h3"])
        if heading is not None:
            title = heading.get_text(" ", strip=True)
            if title:
                return title

        return ""

    def _extract_thumbnail_image_url(self, detail_url: str, soup: BeautifulSoup, content) -> str | None:
        image = content.find("img")
        if image is not None:
            image_url = self._extract_image_url(image)
            if image_url:
                return urljoin(detail_url, image_url)

        meta = soup.select_one("meta[property='og:image'], meta[name='twitter:image']")
        if meta is not None and meta.get("content"):
            return urljoin(detail_url, meta["content"].strip())

        return None

    @staticmethod
    def _extract_image_url(image) -> str | None:
        for attribute in ("data-lazy-src", "data-src", "src"):
            value = image.get(attribute)
            if value:
                return value.strip()

        srcset = image.get("srcset")
        if srcset:
            return srcset.split(",")[0].strip().split(" ")[0]

        return None

    @staticmethod
    def _extract_text_content(content) -> str:
        for tag in content.find_all(["script", "style", "noscript"]):
            tag.decompose()

        text = content.get_text("\n", strip=True)
        text = re.sub(r"\\[rn]+", " ", text)
        text = re.sub(r"https?://\S+|www\.\S+", " ", text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = " ".join(lines)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return cleaned.strip()

    def _extract_count(self, soup: BeautifulSoup, html: str, count_type: str) -> int | None:
        selector_count = self._extract_count_from_selectors(soup, count_type)
        if selector_count is not None:
            return selector_count

        for pattern in self.count_patterns[count_type]:
            match = pattern.search(html)
            if match:
                return self._parse_count(match.group(1))

        return None

    def _extract_count_from_selectors(self, soup: BeautifulSoup, count_type: str) -> int | None:
        selectors = {
            "like_count": (
                ".u_likeit_text._count",
                ".u_likeit_list_btn .u_likeit_list_module",
                ".u_likeit_list_btn .u_likeit_list_count",
                ".u_likeit_list_module .u_likeit_list_count",
                ".u_likeit .u_likeit_text",
                ".u_likeit ._count",
                ".u_likeit .u_cnt",
            ),
            "comment_count": (
                "#commentCount",
                "._commentCount",
                ".btn_comment ._commentCount",
                ".area_comment .num",
                ".btn_comment .num",
                ".commentCount",
                ".comment_count",
                ".u_cbox_count",
            ),
        }[count_type]

        for selector in selectors:
            for element in soup.select(selector):
                data_count = element.get("data-count")
                if data_count:
                    return self._parse_count(data_count)

                count = self._parse_count(element.get_text(" ", strip=True))
                if count is not None:
                    return count

        return None

    @staticmethod
    def _parse_count(value: str) -> int | None:
        match = re.search(r"\d[\d,]*", value)
        if match is None:
            return None
        return int(match.group(0).replace(",", ""))

    def _fetch_like_count(self, detail_url: str, soup: BeautifulSoup) -> int | None:
        content_id = self._extract_like_content_id(soup)
        if content_id is None:
            return None

        url = "https://apis.naver.com/blogserver/like/v1/search/contents"
        params = {
            "suppress_response_codes": "true",
            "q": f"BLOG[{content_id}]",
            "isDuplication": "false",
        }

        try:
            self._wait_for_rate_limit()
            response = self.session.get(
                url,
                params=params,
                headers={"Referer": detail_url},
                timeout=settings.timeout_ms / 1000,
            )
            self._last_request_at = time.monotonic()
            response.raise_for_status()
            return self._extract_like_count_from_payload(response.json())
        except (ValueError, requests.RequestException) as exc:
            logger.warning("좋아요 수 요청 실패: contentId={}, error={}", content_id, exc)
            return None

    @staticmethod
    def _extract_like_content_id(soup: BeautifulSoup) -> str | None:
        element = soup.select_one("[data-likeContentsId], .u_likeit_list_module[data-cid]")
        if element is None:
            return None
        return element.get("data-likeContentsId") or element.get("data-cid")

    def _extract_like_count_from_payload(self, payload) -> int | None:
        candidates: list[int] = []
        self._collect_like_count_candidates(payload, candidates)
        if not candidates:
            return None
        return max(candidates)

    def _collect_like_count_candidates(self, value, candidates: list[int]) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in {"count", "reactioncount", "contentscount", "totalcount"}:
                    count = self._coerce_count(item)
                    if count is not None:
                        candidates.append(count)
                self._collect_like_count_candidates(item, candidates)
            return

        if isinstance(value, list):
            for item in value:
                self._collect_like_count_candidates(item, candidates)

    @staticmethod
    def _coerce_count(value) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return NaverBlogLinkCrawler._parse_count(value)
        return None

    def _extract_blog_id(self, source_url: str, resolved_list_url: str, html: str) -> str:
        for url in (resolved_list_url, source_url):
            query_blog_id = parse_qs(urlparse(url).query).get("blogId", [])
            if query_blog_id:
                return query_blog_id[0]

        match = self.blog_id_pattern.search(html)
        if match:
            return match.group(1)

        path_parts = [part for part in urlparse(source_url).path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[-1].isdigit():
            return path_parts[-2]
        if path_parts and not path_parts[-1].endswith(".naver"):
            return path_parts[-1]

        raise ValueError("blogId를 URL 또는 목록 페이지에서 찾지 못했습니다.")

    @staticmethod
    def _extract_category_no(source_url: str, resolved_list_url: str) -> str | None:
        for url in (source_url, resolved_list_url):
            category_no = parse_qs(urlparse(url).query).get("categoryNo", [])
            if category_no:
                return category_no[0]
        return None

    def _extract_log_nos_from_html(self, blog_id: str, page_url: str, html: str) -> list[str]:
        ordered_log_nos: list[str] = []
        seen: set[str] = set()

        soup = BeautifulSoup(html, "lxml")
        for anchor in soup.find_all("a", href=True):
            detail_url = self._normalize_detail_url(blog_id, page_url, anchor["href"])
            if detail_url is None:
                continue

            log_no = parse_qs(urlparse(detail_url).query).get("logNo", [None])[0]
            if log_no is None or log_no in seen:
                continue
            seen.add(log_no)
            ordered_log_nos.append(log_no)

        if ordered_log_nos:
            return ordered_log_nos

        for pattern in self.log_no_patterns:
            for match in pattern.finditer(html):
                log_no = match.group(1)
                if log_no in seen:
                    continue
                seen.add(log_no)
                ordered_log_nos.append(log_no)

        return ordered_log_nos

    def _extract_pagination_links(
        self,
        blog_id: str,
        category_no: str | None,
        page_url: str,
        html: str,
    ) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        pagination_urls: list[str] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href:
                continue

            absolute_url = urljoin(page_url, href)
            if not self._is_list_page_url(absolute_url):
                continue
            if not self._is_same_blog_category_url(absolute_url, blog_id, category_no):
                continue

            normalized_url = self._normalize_page_url(absolute_url)
            if normalized_url in seen:
                continue

            seen.add(normalized_url)
            pagination_urls.append(absolute_url)

        return pagination_urls

    def _normalize_detail_url(self, blog_id: str, page_url: str, href: str) -> str | None:
        absolute_url = urljoin(page_url, href.strip())
        parsed = urlparse(absolute_url)

        if "PostView.naver" in absolute_url:
            href_blog_id = parse_qs(parsed.query).get("blogId", [None])[0]
            if href_blog_id is not None and href_blog_id != blog_id:
                return None
            return absolute_url

        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[-1].isdigit():
            href_blog_id = path_parts[-2]
            if href_blog_id != blog_id:
                return None
            return f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={path_parts[-1]}"

        return None

    @staticmethod
    def _is_same_blog_category_url(url: str, blog_id: str, category_no: str | None) -> bool:
        query = parse_qs(urlparse(url).query)
        url_blog_id = query.get("blogId", [None])[0]
        if url_blog_id is not None and url_blog_id != blog_id:
            return False

        if category_no is None:
            return True

        return query.get("categoryNo", [None])[0] == category_no

    @staticmethod
    def _is_list_page_url(url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc and "blog.naver.com" not in parsed.netloc:
            return False
        return "PostList.naver" in parsed.path or "PrologueList.naver" in parsed.path

    @staticmethod
    def _normalize_page_url(url: str) -> str:
        parsed = urlparse(url)
        filtered_query = []
        for key, values in parse_qs(parsed.query, keep_blank_values=True).items():
            if key.lower() in {"logno"}:
                continue
            for value in values:
                filtered_query.append((key, value))
        filtered_query.sort()
        query = "&".join(f"{key}={value}" for key, value in filtered_query)
        return parsed._replace(query=query, fragment="").geturl()

    def _fetch_text(self, url: str) -> str:
        last_error: Exception | None = None

        for attempt in range(1, settings.request_retry_count + 1):
            self._wait_for_rate_limit()
            logger.info("페이지 요청 시도: attempt={}, url={}", attempt, url)

            try:
                response = self.session.get(url, timeout=settings.timeout_ms / 1000)
                self._last_request_at = time.monotonic()

                if response.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(
                        f"retryable status: {response.status_code}",
                        response=response,
                    )

                response.raise_for_status()
                logger.info("페이지 요청 성공: status={}, url={}", response.status_code, url)
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                wait_seconds = settings.request_backoff_seconds * attempt
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                logger.warning(
                    "페이지 요청 실패: attempt={}, status={}, waitSeconds={}, url={}, error={}",
                    attempt,
                    status_code,
                    wait_seconds,
                    url,
                    exc,
                )
                if attempt == settings.request_retry_count:
                    break
                time.sleep(wait_seconds)

        raise RuntimeError(f"페이지 요청에 실패했습니다: {url}") from last_error

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_at == 0.0:
            return

        elapsed = time.monotonic() - self._last_request_at
        remaining = settings.request_delay_seconds - elapsed
        if remaining > 0:
            logger.info("레이트 리미트 대기: sleepSeconds={}", round(remaining, 2))
            time.sleep(remaining)
