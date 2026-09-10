"""
HTML Parser component extracting structured SEO data, DOM elements, and metadata.
"""

import re
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse

from seo_audit.models import HeadingItem, ImageItem, LinkItem, PageResponse, ParsedPage
from seo_audit.url_normalizer import URLNormalizer


class HTMLParser:
    """Parses raw HTML responses into rich ParsedPage structures."""

    def __init__(self, normalizer: Optional[URLNormalizer] = None):
        self.normalizer = normalizer or URLNormalizer()

    def parse(self, response: PageResponse) -> ParsedPage:
        """Parse the page response and extract all relevant SEO elements."""
        parsed_page = ParsedPage(
            url=response.final_url,
            response=response,
        )

        # Non-200 or empty HTML responses return basic page model
        if not response.content or not response.is_success:
            return parsed_page

        # Parse with lxml if available, otherwise html.parser
        try:
            soup = BeautifulSoup(response.content, "lxml")
        except Exception:
            soup = BeautifulSoup(response.content, "html.parser")

        # 1. HTML lang attribute
        html_tag = soup.find("html")
        if html_tag and html_tag.has_attr("lang"):
            parsed_page.html_lang = html_tag.get("lang", "").strip()

        # 2. Title Tag
        title_tag = soup.find("title")
        if title_tag:
            parsed_page.title = title_tag.get_text().strip()
            parsed_page.title_raw_html = str(title_tag).strip()

        # 3. Meta Tags
        head = soup.find("head") or soup
        meta_tags = head.find_all("meta")

        for meta in meta_tags:
            name = meta.get("name", "").strip().lower()
            prop = meta.get("property", "").strip().lower()
            content = meta.get("content", "").strip()

            # Meta Description
            if name == "description" or prop == "og:description":
                if name == "description" and parsed_page.meta_description is None:
                    parsed_page.meta_description = content
                    parsed_page.meta_description_raw_html = str(meta).strip()

            # Viewport
            if name == "viewport":
                parsed_page.viewport = content

            # Robots meta directives
            if name == "robots":
                if content:
                    parsed_page.robots_meta.append(content)

            # Open Graph
            if prop.startswith("og:") and content:
                parsed_page.open_graph[prop] = content

            # Twitter Cards
            if (name.startswith("twitter:") or prop.startswith("twitter:")) and content:
                key = name if name.startswith("twitter:") else prop
                parsed_page.twitter_cards[key] = content

        # Check response header for X-Robots-Tag
        for header_name, header_val in response.headers.items():
            if header_name.lower() == "x-robots-tag":
                parsed_page.x_robots_tag.append(header_val)

        # 4. Canonical Tags
        canonical_links = soup.find_all("link", rel=lambda r: r and "canonical" in [v.lower() for v in (r if isinstance(r, list) else [r])])
        for link in canonical_links:
            href = link.get("href", "").strip()
            if href:
                resolved = self.normalizer.resolve_url(response.final_url, href)
                parsed_page.canonical_urls.append(resolved or href)
                parsed_page.canonical_raw_htmls.append(str(link).strip())

        # 5. Headings (H1 - H6)
        heading_tags = soup.find_all(re.compile(r"^h[1-6]$", re.IGNORECASE))
        for order, h in enumerate(heading_tags):
            level = int(h.name[1])
            text = h.get_text().strip()
            parsed_page.headings.append(
                HeadingItem(
                    level=level,
                    text=text,
                    raw_html=str(h).strip(),
                    order=order,
                )
            )

        # 6. Images
        img_tags = soup.find_all("img")
        for img in img_tags:
            src = img.get("src", "").strip()
            has_alt = img.has_attr("alt")
            alt_val = img.get("alt", "").strip() if has_alt else None
            is_data_uri = src.lower().startswith("data:")
            resolved = None if is_data_uri else self.normalizer.resolve_url(response.final_url, src)

            parsed_page.images.append(
                ImageItem(
                    src=src,
                    resolved_url=resolved or src,
                    alt=alt_val,
                    has_alt=has_alt,
                    raw_html=str(img).strip(),
                    is_data_uri=is_data_uri,
                )
            )

        # 7. Hyperlinks
        a_tags = soup.find_all("a")
        for a in a_tags:
            href = a.get("href", "").strip() if a.has_attr("href") else ""
            rel_attr = a.get("rel", [])
            rel_list = [r.lower() for r in (rel_attr if isinstance(rel_attr, list) else [rel_attr])]
            is_fragment = href.startswith("#")
            resolved = self.normalizer.resolve_url(response.final_url, href) if href else ""
            is_internal = bool(resolved and self.normalizer.is_same_domain(response.final_url, resolved))
            text = a.get_text().strip()

            parsed_page.links.append(
                LinkItem(
                    href=href,
                    resolved_url=resolved,
                    text=text,
                    is_internal=is_internal,
                    is_fragment_only=is_fragment,
                    rel=rel_list,
                    raw_html=str(a).strip(),
                )
            )

        # 8. Insecure Subresources (Mixed content on HTTPS)
        is_https = urlparse(response.final_url).scheme.lower() == "https"
        if is_https:
            subresource_selectors = [
                ("script", "src"),
                ("link", "href"),
                ("img", "src"),
                ("iframe", "src"),
                ("video", "src"),
                ("audio", "src"),
                ("source", "src"),
            ]
            for tag_name, attr in subresource_selectors:
                for el in soup.find_all(tag_name):
                    val = el.get(attr, "").strip()
                    if val.lower().startswith("http://"):
                        parsed_page.insecure_subresources.append(str(el).strip())

        # 9. Visible Text & Word Count
        parsed_page.visible_word_count, parsed_page.visible_text_snippet = self._extract_visible_text(soup)

        return parsed_page

    @staticmethod
    def _extract_visible_text(soup: BeautifulSoup) -> Tuple[int, str]:
        """Extract user-visible text content by removing scripts, styles, and hidden tags."""
        # Work on a copy of the soup or strip unwanted tags
        body = soup.find("body")
        if not body:
            return 0, ""

        body_copy = BeautifulSoup(str(body), "html.parser")

        # Remove invisible or script elements
        for element in body_copy(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
            element.decompose()

        # Remove comments
        for comment in body_copy.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()

        text = body_copy.get_text(separator=" ", strip=True)
        words = [w for w in re.findall(r"\b\w+\b", text) if len(w) > 1]
        snippet = " ".join(words[:40])
        return len(words), snippet
