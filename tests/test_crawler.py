"""
Unit tests for Crawler link queueing, depth management, and loop prevention.
"""

from unittest.mock import MagicMock, patch
import pytest
from seo_audit.config import AuditConfig
from seo_audit.crawler import Crawler
from seo_audit.models import PageResponse


def test_crawler_respects_max_pages():
    config = AuditConfig(start_url="https://example.com/", max_pages=2, delay=0.0)
    crawler = Crawler(config)

    # Mock _fetch_and_parse to return dummy pages with links
    dummy_html = """<html><body>
        <a href="/page1">Page 1</a>
        <a href="/page2">Page 2</a>
        <a href="/page3">Page 3</a>
    </body></html>"""

    def mock_fetch(client, url, depth):
        resp = PageResponse(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers={"content-type": "text/html"},
            content=dummy_html,
            depth=depth,
        )
        return crawler.parser.parse(resp)

    with patch.object(crawler, "_fetch_and_parse", side_effect=mock_fetch), \
         patch.object(crawler.robots_policy, "can_fetch", return_value=True), \
         patch.object(crawler.robots_policy, "fetch_policy", return_value=None):

        pages = crawler.crawl()
        assert len(pages) == 2


def test_crawler_respects_max_depth():
    config = AuditConfig(start_url="https://example.com/", max_pages=10, max_depth=1, delay=0.0)
    crawler = Crawler(config)

    # At depth 0, page links to /child. At depth 1, /child links to /grandchild.
    def mock_fetch(client, url, depth):
        if depth == 0:
            html = '<a href="/child">Child</a>'
        else:
            html = '<a href="/grandchild">Grandchild</a>'
        resp = PageResponse(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers={"content-type": "text/html"},
            content=html,
            depth=depth,
        )
        return crawler.parser.parse(resp)

    with patch.object(crawler, "_fetch_and_parse", side_effect=mock_fetch), \
         patch.object(crawler.robots_policy, "can_fetch", return_value=True), \
         patch.object(crawler.robots_policy, "fetch_policy", return_value=None):

        pages = crawler.crawl()
        # Should have crawled root (depth 0) and /child (depth 1), but NOT /grandchild (depth 2)
        urls = [p.url for p in pages]
        assert "https://example.com/" in urls
        assert "https://example.com/child" in urls
        assert not any("grandchild" in u for u in urls)
