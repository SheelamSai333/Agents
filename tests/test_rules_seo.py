"""
Comprehensive unit tests for all SEO audit rules.
"""

import pytest
from seo_audit.config import AuditConfig
from seo_audit.models import PageResponse
from seo_audit.parser import HTMLParser
from seo_audit.rules.canonical import CanonicalRule
from seo_audit.rules.content import ContentRule
from seo_audit.rules.headings import HeadingsRule
from seo_audit.rules.http_status import HttpStatusRule
from seo_audit.rules.https_security import HttpsSecurityRule
from seo_audit.rules.images import ImagesRule
from seo_audit.rules.language import LanguageRule
from seo_audit.rules.links import LinksRule
from seo_audit.rules.meta_tags import MetaTagsRule
from seo_audit.rules.robots_meta import RobotsMetaRule
from seo_audit.rules.social import SocialMetadataRule
from seo_audit.rules.title import TitleRule


@pytest.fixture
def parser():
    return HTMLParser()


@pytest.fixture
def config():
    cfg = AuditConfig()
    cfg.check_broken_images = False  # Avoid real network requests in unit tests
    return cfg


def make_page(parser, url, html, status_code=200, headers=None, redirect_chain=None):
    resp = PageResponse(
        requested_url=url,
        final_url=url,
        status_code=status_code,
        headers=headers or {"content-type": "text/html"},
        content=html,
        redirect_chain=redirect_chain or [],
    )
    return parser.parse(resp)


# 1. HTTP Status Rule
def test_http_status_errors(parser, config):
    rule = HttpStatusRule()

    # 404
    p_404 = make_page(parser, "https://example.com/not-found", "", status_code=404)
    findings = rule.check_page(p_404, config)
    assert any(f.metric == "http_client_error" and f.severity == "critical" for f in findings)

    # 500
    p_500 = make_page(parser, "https://example.com/error", "", status_code=500)
    findings = rule.check_page(p_500, config)
    assert any(f.metric == "http_server_error" and f.severity == "critical" for f in findings)

    # Excessive redirect chain
    p_redirect = make_page(
        parser,
        "https://example.com/c",
        "",
        status_code=200,
        redirect_chain=["http://example.com/a", "https://example.com/b"],
    )
    findings = rule.check_page(p_redirect, config)
    assert any(f.metric == "redirect_chain_excessive" for f in findings)


# 2. Title Rule
def test_title_rule(parser, config):
    rule = TitleRule()

    # Missing title
    p_missing = make_page(parser, "https://example.com/", "<html><head></head><body><h1>Hi</h1></body></html>")
    f_missing = rule.check_page(p_missing, config)
    assert any(f.metric == "missing_title" and f.severity == "critical" for f in f_missing)

    # Title too short (< 30 chars)
    p_short = make_page(parser, "https://example.com/", "<html><head><title>Short Title</title></head></html>")
    f_short = rule.check_page(p_short, config)
    assert any(f.metric == "title_too_short" for f in f_short)

    # Title too long (> 60 chars)
    long_title = "A" * 75
    p_long = make_page(parser, "https://example.com/", f"<html><head><title>{long_title}</title></head></html>")
    f_long = rule.check_page(p_long, config)
    assert any(f.metric == "title_too_long" for f in f_long)

    # Cross-page duplicate title
    p1 = make_page(parser, "https://example.com/page1", "<html><head><title>Identical Title Across Pages</title></head></html>")
    p2 = make_page(parser, "https://example.com/page2", "<html><head><title>Identical Title Across Pages</title></head></html>")
    f_site = rule.check_site([p1, p2], config)
    assert any(f.metric == "duplicate_title" and f.severity == "high" for f in f_site)


# 3. Meta Tags Rule
def test_meta_tags_rule(parser, config):
    rule = MetaTagsRule()

    # Missing meta description & missing viewport
    p_missing = make_page(parser, "https://example.com/", "<html><head><title>Valid Page Title Long Enough Here</title></head></html>")
    findings = rule.check_page(p_missing, config)
    assert any(f.metric == "missing_meta_description" for f in findings)
    assert any(f.metric == "missing_viewport" for f in findings)

    # Short meta description (< 70 chars)
    p_short = make_page(
        parser,
        "https://example.com/",
        '<html><head><meta name="description" content="Too short desc."></head></html>',
    )
    f_short = rule.check_page(p_short, config)
    assert any(f.metric == "meta_description_too_short" for f in f_short)

    # Duplicate meta description
    p1 = make_page(parser, "https://example.com/a", '<html><head><meta name="description" content="A valid length meta description shared across multiple pages for test."></head></html>')
    p2 = make_page(parser, "https://example.com/b", '<html><head><meta name="description" content="A valid length meta description shared across multiple pages for test."></head></html>')
    f_site = rule.check_site([p1, p2], config)
    assert any(f.metric == "duplicate_meta_description" for f in f_site)


# 4. Robots Meta Rule
def test_robots_meta_rule(parser, config):
    rule = RobotsMetaRule()

    # Noindex
    p_noindex = make_page(
        parser,
        "https://example.com/",
        '<html><head><meta name="robots" content="noindex, follow"></head></html>',
    )
    findings = rule.check_page(p_noindex, config)
    assert any(f.metric == "robots_noindex" and f.severity == "critical" for f in findings)

    # Conflicting directives
    p_conflict = make_page(
        parser,
        "https://example.com/",
        '<html><head><meta name="robots" content="index, noindex"></head></html>',
    )
    findings_conflict = rule.check_page(p_conflict, config)
    assert any(f.metric == "robots_conflicting" for f in findings_conflict)

    # robots.txt Disallowed
    p_disallowed = make_page(parser, "https://example.com/blocked", "<html><body>Blocked page</body></html>")
    p_disallowed.is_disallowed_by_robots_txt = True
    p_disallowed.robots_txt_directive = "Disallow: /blocked"
    findings_disallowed = rule.check_page(p_disallowed, config)
    assert any(f.metric == "robots_txt_disallowed" and f.severity == "high" for f in findings_disallowed)


# 5. Headings Rule
def test_headings_rule(parser, config):
    rule = HeadingsRule()

    # Missing H1
    p_no_h1 = make_page(parser, "https://example.com/", "<html><body><h2>Subheading</h2></body></html>")
    findings = rule.check_page(p_no_h1, config)
    assert any(f.metric == "missing_h1" for f in findings)

    # Multiple H1s
    p_multi_h1 = make_page(parser, "https://example.com/", "<html><body><h1>First H1</h1><h1>Second H1</h1></body></html>")
    findings_multi = rule.check_page(p_multi_h1, config)
    assert any(f.metric == "multiple_h1" for f in findings_multi)

    # Empty heading
    p_empty_h = make_page(parser, "https://example.com/", "<html><body><h1>Valid H1</h1><h2>   </h2></body></html>")
    findings_empty = rule.check_page(p_empty_h, config)
    assert any(f.metric == "empty_heading" for f in findings_empty)

    # Heading hierarchy skipped (H1 -> H3)
    p_skip = make_page(parser, "https://example.com/", "<html><body><h1>Title</h1><h3>Skipped level</h3></body></html>")
    findings_skip = rule.check_page(p_skip, config)
    assert any(f.metric == "heading_hierarchy_skipped" for f in findings_skip)


# 6. Images Rule
def test_images_rule(parser, config):
    rule = ImagesRule()

    p_img = make_page(parser, "https://example.com/", '<html><body><img src="/logo.png"><img src="/hero.jpg" alt="Hero"></body></html>')
    findings = rule.check_page(p_img, config)
    assert any(f.metric == "missing_image_alt" for f in findings)
    assert "logo.png" in next(f.evidence for f in findings if f.metric == "missing_image_alt")


# 7. Canonical Rule
def test_canonical_rule(parser, config):
    rule = CanonicalRule()

    # Missing canonical
    p_missing = make_page(parser, "https://example.com/", "<html><head></head></html>")
    findings_missing = rule.check_page(p_missing, config)
    assert any(f.metric == "missing_canonical" for f in findings_missing)

    # Relative canonical
    p_rel = make_page(parser, "https://example.com/", '<html><head><link rel="canonical" href="/home"></head></html>')
    findings_rel = rule.check_page(p_rel, config)
    assert any(f.metric == "relative_canonical" for f in findings_rel)

    # Multiple canonicals
    p_multi = make_page(
        parser,
        "https://example.com/",
        '<html><head><link rel="canonical" href="https://example.com/a"><link rel="canonical" href="https://example.com/b"></head></html>',
    )
    findings_multi = rule.check_page(p_multi, config)
    assert any(f.metric == "multiple_canonical" for f in findings_multi)


# 8. Links Rule
def test_links_rule(parser, config):
    rule = LinksRule()

    # Missing href & empty anchor text
    html = """<html><body>
        <a>No href</a>
        <a href="/internal"></a>
    </body></html>"""
    p_links = make_page(parser, "https://example.com/", html)
    findings = rule.check_page(p_links, config)
    assert any(f.metric == "missing_href" for f in findings)
    assert any(f.metric == "empty_anchor_text" for f in findings)

    # Broken internal link site check
    p_source = make_page(parser, "https://example.com/home", '<html><body><a href="/missing-page">Broken Link</a></body></html>')
    p_target_404 = make_page(parser, "https://example.com/missing-page", "<html>Not found</html>", status_code=404)
    findings_site = rule.check_site([p_source, p_target_404], config)
    assert any(f.metric == "broken_internal_link" for f in findings_site)


# 9. HTTPS Security Rule
def test_https_security_rule(parser, config):
    rule = HttpsSecurityRule()

    # Insecure HTTP
    p_http = make_page(parser, "http://example.com/", "<html></html>")
    findings_http = rule.check_page(p_http, config)
    assert any(f.metric == "insecure_http" for f in findings_http)

    # Mixed content on HTTPS
    p_mixed = make_page(parser, "https://example.com/", '<html><head><script src="http://cdn.example.com/app.js"></script></head></html>')
    findings_mixed = rule.check_page(p_mixed, config)
    assert any(f.metric == "mixed_content" for f in findings_mixed)


# 10. Social Metadata Rule
def test_social_metadata_rule(parser, config):
    rule = SocialMetadataRule()

    p_no_og = make_page(parser, "https://example.com/", "<html><head><title>Title</title></head></html>")
    findings = rule.check_page(p_no_og, config)
    assert any(f.metric == "missing_open_graph" for f in findings)


# 11. Content Rule
def test_content_rule(parser, config):
    rule = ContentRule()

    # Empty content
    p_empty = make_page(parser, "https://example.com/", "<html><body></body></html>")
    findings_empty = rule.check_page(p_empty, config)
    assert any(f.metric == "empty_content" for f in findings_empty)

    # Thin content (< 200 words)
    p_thin = make_page(parser, "https://example.com/", "<html><body><p>Just a few short words here.</p></body></html>")
    findings_thin = rule.check_page(p_thin, config)
    assert any(f.metric == "thin_content" for f in findings_thin)


# 12. Language Rule
def test_language_rule(parser, config):
    rule = LanguageRule()

    # Missing lang
    p_no_lang = make_page(parser, "https://example.com/", "<html><body>Text</body></html>")
    findings = rule.check_page(p_no_lang, config)
    assert any(f.metric == "missing_html_lang" for f in findings)

    # Empty lang
    p_empty_lang = make_page(parser, "https://example.com/", '<html lang=""><body>Text</body></html>')
    findings_empty = rule.check_page(p_empty_lang, config)
    assert any(f.metric == "invalid_html_lang" for f in findings_empty)
