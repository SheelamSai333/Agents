"""
Unit tests for URL normalization, scoping, and loop detection.
"""

import pytest
from seo_audit.url_normalizer import URLNormalizer


@pytest.fixture
def normalizer():
    return URLNormalizer()


def test_ensure_scheme(normalizer):
    assert normalizer.ensure_scheme("example.com") == "https://example.com"
    assert normalizer.ensure_scheme("http://example.com") == "http://example.com"
    assert normalizer.ensure_scheme("https://example.com") == "https://example.com"


def test_normalize_strips_fragments(normalizer):
    url = "https://example.com/page#section-one"
    assert normalizer.normalize(url) == "https://example.com/page"


def test_normalize_strips_tracking_params(normalizer):
    url = "https://example.com/page?utm_source=google&utm_medium=cpc&sort=asc&fbclid=1234"
    assert normalizer.normalize(url) == "https://example.com/page?sort=asc"


def test_normalize_sorts_query_params(normalizer):
    url = "https://example.com/shop?z=2&a=1"
    assert normalizer.normalize(url) == "https://example.com/shop?a=1&z=2"


def test_normalize_root_path(normalizer):
    assert normalizer.normalize("https://example.com") == "https://example.com/"
    assert normalizer.normalize("HTTP://EXAMPLE.COM/") == "http://example.com/"


def test_normalize_removes_default_ports(normalizer):
    assert normalizer.normalize("http://example.com:80/about") == "http://example.com/about"
    assert normalizer.normalize("https://example.com:443/about") == "https://example.com/about"


def test_resolve_url(normalizer):
    base = "https://example.com/blog/article"
    assert normalizer.resolve_url(base, "/about") == "https://example.com/about"
    assert normalizer.resolve_url(base, "sub-page") == "https://example.com/blog/sub-page"
    assert normalizer.resolve_url(base, "//cdn.example.com/img.png") == "https://cdn.example.com/img.png"
    assert normalizer.resolve_url(base, "mailto:test@example.com") is None
    assert normalizer.resolve_url(base, "javascript:void(0)") is None
    assert normalizer.resolve_url(base, "#anchor") is None


def test_is_same_domain(normalizer):
    base = "https://example.com/home"
    assert normalizer.is_same_domain(base, "https://example.com/about") is True
    assert normalizer.is_same_domain(base, "https://www.example.com/about") is True
    assert normalizer.is_same_domain(base, "https://other.com/about") is False


def test_is_html_target(normalizer):
    assert normalizer.is_html_target("https://example.com/page") is True
    assert normalizer.is_html_target("https://example.com/page.html") is True
    assert normalizer.is_html_target("https://example.com/doc.pdf") is False
    assert normalizer.is_html_target("https://example.com/image.png") is False


def test_detect_path_loop(normalizer):
    # Normal URLs
    assert normalizer.detect_path_loop("https://example.com/blog/post-1") is False
    # Repetitive segment loop
    assert normalizer.detect_path_loop("https://example.com/dir/dir/dir/dir") is True
    # Alternating cyclical loop
    assert normalizer.detect_path_loop("https://example.com/category/item/category/item") is True
