"""
Crawler component handling URL discovery, politeness, loop prevention, and page fetching.
Supports hybrid crawling: static HTTP first, with Playwright fallback for JavaScript SPAs.
"""

import re
from collections import deque
import logging
import time
from typing import Deque, List, Optional, Set, Tuple
from urllib.parse import urlparse
import httpx

from seo_audit.config import AuditConfig
from seo_audit.browser_renderer import BrowserRenderer
from seo_audit.models import PageResponse, ParsedPage
from seo_audit.parser import HTMLParser
from seo_audit.robots import RobotsPolicy
from seo_audit.url_normalizer import URLNormalizer

logger = logging.getLogger(__name__)

# Patterns that indicate a JavaScript SPA root container
_SPA_ROOT_PATTERNS = re.compile(
    r'<div\s+id\s*=\s*["\'](?:root|app|__next|__nuxt|main-app)["\']',
    re.IGNORECASE,
)


class Crawler:
    """Production-quality polite web crawler for SEO auditing."""

    def __init__(
        self,
        config: AuditConfig,
        normalizer: Optional[URLNormalizer] = None,
        robots_policy: Optional[RobotsPolicy] = None,
        parser: Optional[HTMLParser] = None,
    ):
        self.config = config
        self.normalizer = normalizer or URLNormalizer(tracking_params=config.tracking_params)
        self.robots_policy = robots_policy or RobotsPolicy(
            user_agent=config.user_agent,
            enabled=config.respect_robots_txt,
            timeout=config.timeout,
        )
        self.parser = parser or HTMLParser(normalizer=self.normalizer)
        self.renderer = BrowserRenderer(user_agent=config.user_agent)

        # Crawl state
        self.visited_normalized: Set[str] = set()
        self.enqueued_normalized: Set[str] = set()
        self.crawled_pages: List[ParsedPage] = []

    def crawl(self, start_url: Optional[str] = None) -> List[ParsedPage]:
        """
        Execute the crawl starting from start_url:
        - Validates and normalizes start_url.
        - Respects robots.txt.
        - Traverses internal links via BFS queue.
        - Avoids cycles, path loops, and duplicate URLs.
        - Halts upon reaching max_pages or exhausting internal frontier.
        """
        raw_start = start_url or self.config.start_url
        if not raw_start:
            raise ValueError("Start URL must be provided to crawler.")

        normalized_start = self.normalizer.normalize(raw_start)
        if not normalized_start:
            raise ValueError(f"Invalid starting URL: {raw_start}")

        logger.info(f"Initiating SEO crawl on {normalized_start} (max_pages={self.config.max_pages}, max_depth={self.config.max_depth})")

        # BFS queue: stores (url, current_depth)
        queue: Deque[Tuple[str, int]] = deque([(normalized_start, 0)])
        self.enqueued_normalized.add(normalized_start)

        # HTTP client setup
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
        }

        with httpx.Client(
            headers=headers,
            timeout=self.config.timeout,
            verify=self.config.verify_ssl,
            follow_redirects=True,
        ) as client:
            # Fetch robots.txt first
            if self.config.respect_robots_txt:
                self.robots_policy.fetch_policy(normalized_start, client=client)

            while queue and len(self.crawled_pages) < self.config.max_pages:
                current_url, depth = queue.popleft()
                norm_current = self.normalizer.normalize(current_url)

                if norm_current in self.visited_normalized:
                    continue

                # Check robots.txt permissions
                is_start_target = (norm_current == normalized_start or depth == 0)
                can_fetch = self.robots_policy.can_fetch(current_url, client=client)

                if not can_fetch:
                    if is_start_target:
                        logger.warning(
                            f"Target start URL '{current_url}' is disallowed by robots.txt. "
                            f"Auditing target page markup and reporting robots.txt disallow finding."
                        )
                    else:
                        logger.info(f"Skipping discovered URL {current_url}: Disallowed by robots.txt")
                        self.visited_normalized.add(norm_current)
                        continue

                # Politeness delay between requests
                if self.config.delay > 0 and len(self.visited_normalized) > 0:
                    time.sleep(self.config.delay)

                # Fetch and parse page
                parsed_page = self._fetch_and_parse(client, current_url, depth)
                if not can_fetch:
                    parsed_page.is_disallowed_by_robots_txt = True
                    parsed_page.robots_txt_directive = "Disallow rule in robots.txt"

                self.visited_normalized.add(norm_current)

                # Also mark final URL as visited if redirected
                if parsed_page.response.final_url:
                    norm_final = self.normalizer.normalize(parsed_page.response.final_url)
                    self.visited_normalized.add(norm_final)

                self.crawled_pages.append(parsed_page)

                # If successful HTML page and within depth limits, discover internal links
                internal_links: List[str] = []
                external_links: List[str] = []
                queued_links: List[str] = []
                from collections import defaultdict
                skipped_reasons: dict[str, list[str]] = defaultdict(list)

                if parsed_page.response.is_success and depth < self.config.max_depth:
                    for link in parsed_page.links:
                        if not link.resolved_url:
                            skipped_reasons["Empty or non-HTTP href"].append(link.href or "<empty>")
                            continue

                        if not link.is_internal:
                            external_links.append(link.resolved_url)
                            skipped_reasons["External domain"].append(link.resolved_url)
                            continue

                        internal_links.append(link.resolved_url)

                        # Check if target is likely an HTML document
                        if not self.normalizer.is_html_target(link.resolved_url):
                            skipped_reasons["Non-HTML asset extension"].append(link.resolved_url)
                            continue

                        # Check loop prevention
                        if self.normalizer.detect_path_loop(link.resolved_url):
                            skipped_reasons["Cyclical path loop detected"].append(link.resolved_url)
                            continue

                        norm_link = self.normalizer.normalize(link.resolved_url)
                        if norm_link in self.visited_normalized:
                            skipped_reasons["Already visited"].append(link.resolved_url)
                            continue

                        if norm_link in self.enqueued_normalized:
                            skipped_reasons["Already queued in frontier"].append(link.resolved_url)
                            continue

                        # Check robots.txt permissions for discovered internal links
                        if self.config.respect_robots_txt and not self.robots_policy.can_fetch(link.resolved_url, client=client):
                            skipped_reasons["Disallowed by robots.txt"].append(link.resolved_url)
                            continue

                        self.enqueued_normalized.add(norm_link)
                        queue.append((link.resolved_url, depth + 1))
                        queued_links.append(link.resolved_url)

                # Diagnostic output per crawled page
                total_skipped = sum(len(v) for v in skipped_reasons.values())
                print(f"\n{'='*70}")
                print(f"CRAWL DIAGNOSTICS (Depth {depth}, Queue size: {len(queue)}):")
                print(f"  URL              : {current_url}")
                print(f"  HTTP status      : {parsed_page.response.status_code}")
                print(f"  Links discovered : {len(parsed_page.links)}")
                print(f"  Internal links   : {len(internal_links)}")
                print(f"  External links   : {len(external_links)}")
                print(f"  Queued links     : {len(queued_links)}")
                for q in queued_links[:4]:
                    print(f"    -> [QUEUED] {q}")
                if len(queued_links) > 4:
                    print(f"    ... and {len(queued_links) - 4} more queued")
                if total_skipped > 0:
                    print(f"  Skipped links    : {total_skipped}")
                    for reason, items in skipped_reasons.items():
                        print(f"    x [{reason}]: {len(items)}")
                        for item in items[:2]:
                            print(f"        Sample: {item}")
                elif not parsed_page.response.is_success:
                    print(f"  Link discovery   : Skipped (HTTP status {parsed_page.response.status_code})")
                elif depth >= self.config.max_depth:
                    print(f"  Link discovery   : Skipped (Reached max_depth={self.config.max_depth})")
                print(f"{'='*70}\n")

        # Clean up headless browser if it was used
        self.renderer.close()

        logger.info(f"Crawl completed. Total pages analyzed: {len(self.crawled_pages)}")
        return self.crawled_pages

    @staticmethod
    def _is_spa_shell(html: str) -> bool:
        """
        Detect whether HTML is a thin JavaScript SPA shell that requires
        client-side rendering to produce meaningful content.

        Heuristics:
        1. Body contains an SPA root container (div#root, div#app, div#__next, etc.)
        2. Body has very little visible text (< 50 words excluding scripts/styles)
        3. Body contains fewer than 3 <a> tags with href attributes
        """
        if not html:
            return False

        # Quick check: does the HTML contain a known SPA root element?
        if not _SPA_ROOT_PATTERNS.search(html):
            return False

        # Count <a href="..."> tags (rough count without full parse)
        a_tag_count = len(re.findall(r'<a\s[^>]*href\s*=', html, re.IGNORECASE))
        if a_tag_count >= 5:
            # Enough links exist in static HTML, likely server-rendered
            return False

        # Check visible text volume in the <body> (rough extraction)
        body_match = re.search(r'<body[^>]*>(.*)</body>', html, re.DOTALL | re.IGNORECASE)
        if body_match:
            body_html = body_match.group(1)
            # Remove script and style blocks
            stripped = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', '', body_html, flags=re.DOTALL | re.IGNORECASE)
            # Remove all tags
            text_only = re.sub(r'<[^>]+>', ' ', stripped)
            words = text_only.split()
            if len(words) < 50:
                logger.info(f"SPA shell detected: {a_tag_count} links, {len(words)} words in body")
                return True

        return False

    def _fetch_and_parse(self, client: httpx.Client, url: str, depth: int) -> ParsedPage:
        """
        Fetch URL content over HTTP and parse into ParsedPage structure.
        Uses hybrid strategy: tries static HTTP first, falls back to headless
        browser rendering if the response appears to be a JavaScript SPA shell.
        """
        start_time = time.time()
        redirect_chain: List[str] = []
        final_url = url
        status_code = 0
        headers_dict = {}
        content_text = ""
        error_msg = None
        used_browser_rendering = False

        try:
            resp = client.get(url)
            elapsed = time.time() - start_time
            status_code = resp.status_code
            final_url = str(resp.url)
            headers_dict = {k.lower(): v for k, v in resp.headers.items()}

            # Extract redirect chain from history
            if resp.history:
                redirect_chain = [str(r.url) for r in resp.history]

            # Only read text content for HTML or text responses
            content_type = headers_dict.get("content-type", "").lower()
            if "text/html" in content_type or "application/xhtml" in content_type or not content_type:
                content_text = resp.text
            else:
                content_text = ""

        except httpx.HTTPStatusError as e:
            elapsed = time.time() - start_time
            status_code = e.response.status_code if e.response else 500
            final_url = str(e.request.url) if e.request else url
            error_msg = str(e)
        except httpx.RequestError as e:
            elapsed = time.time() - start_time
            status_code = 0
            error_msg = f"Network/Connection error: {e}"
        except Exception as e:
            elapsed = time.time() - start_time
            status_code = 0
            error_msg = f"Unexpected error: {e}"

        # Hybrid strategy: if static HTML looks like an SPA shell, try browser rendering
        if (
            status_code >= 200
            and status_code < 300
            and content_text
            and self._is_spa_shell(content_text)
        ):
            logger.info(f"Attempting browser rendering for SPA page: {url}")
            rendered_html = self.renderer.render_page(url)
            if rendered_html:
                content_text = rendered_html
                used_browser_rendering = True
                logger.info(f"Browser rendering succeeded for {url} ({len(rendered_html)} bytes)")
            else:
                logger.warning(f"Browser rendering failed for {url}, using static HTML fallback")

        page_resp = PageResponse(
            requested_url=url,
            final_url=final_url,
            status_code=status_code,
            headers=headers_dict,
            content=content_text,
            redirect_chain=redirect_chain,
            depth=depth,
            elapsed_seconds=time.time() - start_time,
            error=error_msg,
        )

        parsed = self.parser.parse(page_resp)

        if used_browser_rendering:
            print(f"  [BROWSER RENDER] Page rendered via headless Chromium ({len(content_text)} bytes, {len(parsed.links)} links extracted)")

        return parsed
