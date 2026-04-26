import re
import time
from collections import deque
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger

from src.config.settings import settings


class NaverBlogLinkCrawler:
    blog_id_pattern = re.compile(r"var blogId = '([^']+)'")
    log_no_patterns = (
        re.compile(r"logNo=(\d+)"),
        re.compile(r"logNo\s*:\s*'(\d+)'"),
        re.compile(r"PostView\.naver\?blogId=[^\"'&]+&logNo=(\d+)"),
    )

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.default_user_agent})
        self._last_request_at = 0.0

    def collect(self, source_url: str) -> dict:
        logger.info("네이버 블로그 상세 링크 수집 시작: {}", source_url)
        initial_html = self._fetch_text(source_url)
        first_list_url, first_list_html = self._resolve_list_page(source_url, initial_html)
        blog_id = self._extract_blog_id(source_url, first_list_url, first_list_html)
        logger.info("목록 페이지 확인 완료: blogId={}, listUrl={}", blog_id, first_list_url)

        detail_urls = self._collect_all_detail_urls(blog_id, first_list_url, first_list_html)

        logger.info("네이버 블로그 상세 링크 수집 완료: blogId={}, count={}", blog_id, len(detail_urls))
        for index, detail_url in enumerate(detail_urls, start=1):
            logger.info("상세 링크 {}: {}", index, detail_url)

        return {
            "source_url": source_url,
            "resolved_list_url": first_list_url,
            "blog_id": blog_id,
            "count": len(detail_urls),
            "detail_urls": detail_urls,
        }

    def _collect_all_detail_urls(self, blog_id: str, first_list_url: str, first_list_html: str) -> list[str]:
        queue: deque[tuple[str, str | None]] = deque([(first_list_url, first_list_html)])
        visited_pages: set[str] = set()
        seen_log_nos: set[str] = set()
        ordered_log_nos: list[str] = []
        page_index = 0

        while queue:
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

            next_page_urls = self._extract_pagination_links(page_url, html)
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

    def _extract_log_nos_from_html(self, blog_id: str, page_url: str, html: str) -> list[str]:
        ordered_log_nos: list[str] = []
        seen: set[str] = set()

        for pattern in self.log_no_patterns:
            for match in pattern.finditer(html):
                log_no = match.group(1)
                if log_no in seen:
                    continue
                seen.add(log_no)
                ordered_log_nos.append(log_no)

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

        return ordered_log_nos

    def _extract_pagination_links(self, page_url: str, html: str) -> list[str]:
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
            return absolute_url

        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[-1].isdigit():
            return f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={path_parts[-1]}"

        return None

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
            logger.info("목록 요청 시도: attempt={}, url={}", attempt, url)

            try:
                response = self.session.get(url, timeout=settings.timeout_ms / 1000)
                self._last_request_at = time.monotonic()

                if response.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(
                        f"retryable status: {response.status_code}",
                        response=response,
                    )

                response.raise_for_status()
                logger.info("목록 요청 성공: status={}, url={}", response.status_code, url)
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                wait_seconds = settings.request_backoff_seconds * attempt
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                logger.warning(
                    "목록 요청 실패: attempt={}, status={}, waitSeconds={}, url={}, error={}",
                    attempt,
                    status_code,
                    wait_seconds,
                    url,
                    exc,
                )
                if attempt == settings.request_retry_count:
                    break
                time.sleep(wait_seconds)

        raise RuntimeError(f"목록 페이지 요청에 실패했습니다: {url}") from last_error

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_at == 0.0:
            return

        elapsed = time.monotonic() - self._last_request_at
        remaining = settings.request_delay_seconds - elapsed
        if remaining > 0:
            logger.info("레이트 리미트 대기: sleepSeconds={}", round(remaining, 2))
            time.sleep(remaining)
