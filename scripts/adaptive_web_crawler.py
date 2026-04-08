#!/usr/bin/env python3
"""
Adaptive web crawler for HTML, JSON, and JavaScript-rendered pages.

Features:
- Async crawling with concurrency control
- Automatic content type detection (JSON/HTML/text)
- Basic HTML content extraction (title, text, links)
- Optional JS rendering via Playwright
- Retry with exponential backoff

Examples:
  python scripts/adaptive_web_crawler.py --url https://example.com
  python scripts/adaptive_web_crawler.py --url https://example.com/api/data --url https://news.ycombinator.com
  python scripts/adaptive_web_crawler.py --from-file urls.txt --render-js --output crawl_results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp


class HTMLTextExtractor(HTMLParser):
    """Extract visible text from HTML using the standard library parser."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Any]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            cleaned = data.strip()
            if cleaned:
                self._parts.append(cleaned)

    def get_text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._parts)).strip()


@dataclass
class CrawlResult:
    url: str
    status: Optional[int]
    content_type: str
    title: Optional[str]
    text_excerpt: Optional[str]
    json_data: Optional[Any]
    links: List[str]
    fetched_at: float
    elapsed_ms: int
    source: str
    error: Optional[str] = None


class AdaptiveWebCrawler:
    def __init__(
        self,
        timeout: int = 15,
        max_concurrency: int = 5,
        max_retries: int = 2,
        render_js: bool = False,
        js_wait_ms: int = 1200,
        user_agent: Optional[str] = None,
    ) -> None:
        self.timeout = timeout
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.render_js = render_js
        self.js_wait_ms = js_wait_ms
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        self._browser = None
        self._playwright = None

    async def _init_browser(self) -> None:
        if not self.render_js or self._browser is not None:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. Install with: pip install playwright"
            ) from exc

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)

    async def _close_browser(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    @staticmethod
    def _extract_title(html: str) -> Optional[str]:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        return re.sub(r"\s+", " ", match.group(1)).strip() or None

    @staticmethod
    def _extract_links(base_url: str, html: str, limit: int = 100) -> List[str]:
        links: List[str] = []
        for m in re.finditer(r"<a[^>]+href=[\"'](.*?)[\"']", html, flags=re.IGNORECASE):
            href = m.group(1).strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            absolute = urljoin(base_url, href)
            links.append(absolute)
            if len(links) >= limit:
                break
        return links

    @staticmethod
    def _maybe_json(content_type: str, body: str) -> bool:
        if "json" in content_type.lower():
            return True
        trimmed = body.lstrip()
        return trimmed.startswith("{") or trimmed.startswith("[")

    @staticmethod
    def _looks_html(content_type: str, body: str) -> bool:
        if "html" in content_type.lower():
            return True
        snippet = body[:500].lower()
        return "<html" in snippet or "<!doctype html" in snippet

    def _parse_html(self, url: str, html: str, status: Optional[int], elapsed_ms: int, source: str) -> CrawlResult:
        title = self._extract_title(html)
        extractor = HTMLTextExtractor()
        extractor.feed(html)
        text = extractor.get_text()
        links = self._extract_links(url, html)
        return CrawlResult(
            url=url,
            status=status,
            content_type="html",
            title=title,
            text_excerpt=text[:1000] if text else None,
            json_data=None,
            links=links,
            fetched_at=time.time(),
            elapsed_ms=elapsed_ms,
            source=source,
        )

    def _parse_json(self, url: str, raw: str, status: Optional[int], elapsed_ms: int, source: str) -> CrawlResult:
        data = json.loads(raw)
        return CrawlResult(
            url=url,
            status=status,
            content_type="json",
            title=None,
            text_excerpt=None,
            json_data=data,
            links=[],
            fetched_at=time.time(),
            elapsed_ms=elapsed_ms,
            source=source,
        )

    def _parse_text(self, url: str, raw: str, status: Optional[int], elapsed_ms: int, source: str) -> CrawlResult:
        return CrawlResult(
            url=url,
            status=status,
            content_type="text",
            title=None,
            text_excerpt=raw[:1000] if raw else None,
            json_data=None,
            links=[],
            fetched_at=time.time(),
            elapsed_ms=elapsed_ms,
            source=source,
        )

    async def _fetch_static(self, session: aiohttp.ClientSession, url: str) -> CrawlResult:
        started = time.perf_counter()
        async with session.get(url, timeout=self.timeout) as response:
            body = await response.text(errors="replace")
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            content_type = response.headers.get("content-type", "")

            if self._maybe_json(content_type, body):
                return self._parse_json(url, body, response.status, elapsed_ms, source="static")

            if self._looks_html(content_type, body):
                return self._parse_html(url, body, response.status, elapsed_ms, source="static")

            return self._parse_text(url, body, response.status, elapsed_ms, source="static")

    async def _fetch_dynamic(self, url: str) -> CrawlResult:
        if self._browser is None:
            await self._init_browser()

        started = time.perf_counter()
        context = await self._browser.new_context(user_agent=self.user_agent)
        page = await context.new_page()
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
            await page.wait_for_timeout(self.js_wait_ms)
            html = await page.content()
            status = response.status if response else None
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return self._parse_html(url, html, status, elapsed_ms, source="dynamic")
        finally:
            await context.close()

    @staticmethod
    def _needs_dynamic_render(result: CrawlResult) -> bool:
        if result.content_type != "html":
            return False
        text_len = len(result.text_excerpt or "")
        if text_len > 120:
            return False
        if result.title and len(result.title) > 3:
            return False
        return True

    async def crawl_one(self, session: aiohttp.ClientSession, url: str) -> CrawlResult:
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                static_result = await self._fetch_static(session, url)
                if self.render_js and self._needs_dynamic_render(static_result):
                    return await self._fetch_dynamic(url)
                return static_result
            except Exception as exc:
                last_error = str(exc)
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5 * (2**attempt))

        return CrawlResult(
            url=url,
            status=None,
            content_type="error",
            title=None,
            text_excerpt=None,
            json_data=None,
            links=[],
            fetched_at=time.time(),
            elapsed_ms=0,
            source="none",
            error=last_error or "Unknown error",
        )

    async def crawl(self, urls: List[str]) -> List[CrawlResult]:
        await self._init_browser()
        sem = asyncio.Semaphore(self.max_concurrency)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json,text/html,application/xhtml+xml,text/plain,*/*",
        }

        timeout = aiohttp.ClientTimeout(total=self.timeout + 3)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async def bounded(url: str) -> CrawlResult:
                async with sem:
                    return await self.crawl_one(session, url)

            tasks = [bounded(url) for url in urls]
            results = await asyncio.gather(*tasks)

        await self._close_browser()
        return results


def read_urls_from_file(path: str) -> List[str]:
    urls: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Adaptive crawler for HTML, JSON, and JS pages")
    parser.add_argument("--url", action="append", help="Target URL (can be used multiple times)")
    parser.add_argument("--from-file", help="File with target URLs (one URL per line)")
    parser.add_argument("--output", default="crawl_results.json", help="Output JSON file path")
    parser.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds")
    parser.add_argument("--max-concurrency", type=int, default=5, help="Max concurrent requests")
    parser.add_argument("--max-retries", type=int, default=2, help="Retry count on failure")
    parser.add_argument("--render-js", action="store_true", help="Use Playwright for JS-heavy pages")
    parser.add_argument("--js-wait-ms", type=int, default=1200, help="Wait time after page load (ms)")
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_result",
        help="Print result summary to console",
    )
    return parser.parse_args()


def dedupe_urls(urls: List[str]) -> List[str]:
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


async def run() -> int:
    args = parse_args()

    urls: List[str] = []
    if args.url:
        urls.extend(args.url)
    if args.from_file:
        urls.extend(read_urls_from_file(args.from_file))

    urls = dedupe_urls(urls)
    if not urls:
        print("No URLs provided. Use --url or --from-file.")
        return 1

    crawler = AdaptiveWebCrawler(
        timeout=args.timeout,
        max_concurrency=args.max_concurrency,
        max_retries=args.max_retries,
        render_js=args.render_js,
        js_wait_ms=args.js_wait_ms,
    )

    results = await crawler.crawl(urls)
    payload: List[Dict[str, Any]] = [asdict(r) for r in results]

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    if args.print_result:
        for item in payload:
            status = item.get("status")
            ctype = item.get("content_type")
            source = item.get("source")
            url = item.get("url")
            error = item.get("error")
            if error:
                print(f"[ERROR] {url} :: {error}")
            else:
                print(f"[{status}] {ctype:<5} ({source}) {url}")

    print(f"Crawled {len(payload)} URL(s). Saved to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
