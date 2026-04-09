import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright


WHITESPACE_RE = re.compile(r"\s+")
INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")


def normalize_text(value: str) -> str:
    value = INVISIBLE_RE.sub("", value)
    return WHITESPACE_RE.sub(" ", value).strip()


def normalize_naver_blog_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.netloc.endswith("blog.naver.com"):
        return url

    query = parse_qs(parsed.query)
    blog_id = query.get("blogId", [None])[0]
    log_no = query.get("logNo", [None])[0]
    path_parts = [part for part in parsed.path.split("/") if part]

    if len(path_parts) >= 2 and path_parts[0] != "PostView.naver":
        path_blog_id = path_parts[0]
        path_log_no = path_parts[1]
        if path_log_no.isdigit():
            return (
                "https://blog.naver.com/PostView.naver"
                f"?blogId={path_blog_id}&logNo={path_log_no}"
            )

    if parsed.path.endswith("/PostView.naver") and blog_id and log_no:
        return f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"

    return url


def _extract_from_context(page_or_frame, source: str) -> dict[str, str]:
    title_selectors = [
        ".se-title-text",
        ".se-section-documentTitle .pcol1",
        "meta[property='og:title']",
        "title",
    ]

    title = ""
    for selector in title_selectors:
        locator = page_or_frame.locator(selector).first
        if locator.count() == 0:
            continue

        if selector.startswith("meta"):
            value = locator.get_attribute("content") or ""
        else:
            value = locator.inner_text()

        title = normalize_text(value)
        if title:
            break

    paragraph_locator = page_or_frame.locator(".se-main-container .se-text-paragraph")
    paragraphs: list[str] = []
    for i in range(paragraph_locator.count()):
        text = normalize_text(paragraph_locator.nth(i).inner_text())
        if text:
            paragraphs.append(text)

    return {
        "source": source,
        "title": title,
        "content": "\n".join(paragraphs),
    }


def _has_post_content(page_or_frame) -> bool:
    return page_or_frame.locator(".se-main-container .se-text-paragraph").count() > 0


def _extract_from_page(page, source: str) -> dict[str, str]:
    if _has_post_content(page):
        return _extract_from_context(page, source)

    for frame in page.frames:
        if frame == page.main_frame:
            continue
        if _has_post_content(frame):
            return _extract_from_context(frame, source)

    return _extract_from_context(page, source)


def extract_blog_post_from_file(html_path: Path) -> dict[str, str]:
    html = html_path.read_text(encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        context.route("**/*", lambda route: route.abort())
        page = context.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        extracted = _extract_from_page(page, str(html_path))
        browser.close()

    return extracted


def extract_blog_post_from_url(url: str, timeout_ms: int = 15000) -> dict[str, str]:
    url = normalize_naver_blog_url(url)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        extracted = _extract_from_page(page, url)
        browser.close()

    return extracted


def extract_blog_post(source: str, timeout_ms: int = 15000) -> dict[str, str]:
    if source.startswith(("http://", "https://")):
        return extract_blog_post_from_url(source, timeout_ms=timeout_ms)

    return extract_blog_post_from_file(Path(source).resolve())

