"""
DOM Content Extraction and Semantic Segmentation for Q3.

Extracts content chunks (paragraphs, list items, headings, table cells) while
preserving exact verbatim text, tracking heading breadcrumbs, and classifying
boilerplate vs main content.
"""

import re
from typing import List, Tuple
from bs4 import BeautifulSoup, Comment, Tag

from seo_audit.models import ParsedPage
from site_qa.models import ContentChunk


BOILERPLATE_TAGS = {"header", "footer", "nav", "aside"}
BOILERPLATE_CLASS_ID_KEYWORDS = {
    "cookie", "banner", "copyright", "footer", "navbar", "navigation",
    "site-header", "menu-drawer", "sidebar", "disclaimer", "popup", "modal"
}
DISCARD_TAGS = {"script", "style", "noscript", "svg", "canvas", "template"}
CONTENT_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "dd", "dt", "td", "th", "address", "div"}


class ContentExtractor:
    """Extracts semantic, grounded content chunks from ParsedPage HTML."""

    def __init__(self, min_chunk_words: int = 3, max_chunk_words: int = 250):
        self.min_chunk_words = min_chunk_words
        self.max_chunk_words = max_chunk_words

    def extract_chunks(self, page: ParsedPage) -> List[ContentChunk]:
        """Extract all content chunks from a parsed page's HTML."""
        if not page.response or not page.response.content:
            return []

        try:
            soup = BeautifulSoup(page.response.content, "lxml")
        except Exception:
            soup = BeautifulSoup(page.response.content, "html.parser")

        # Strip scripts, styles, comments
        for tag in soup.find_all(DISCARD_TAGS):
            tag.decompose()

        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()

        body = soup.find("body") or soup
        chunks: List[ContentChunk] = []
        heading_stack: List[Tuple[int, str]] = []  # (level, text)
        chunk_id = 0

        # Traverse body in DOM order
        for element in body.descendants:
            if not isinstance(element, Tag):
                continue

            tag_name = element.name.lower()

            # Track headings
            if re.match(r"^h[1-6]$", tag_name):
                level = int(tag_name[1])
                heading_text = self._clean_text(element.get_text(" ", strip=True))
                if heading_text:
                    while heading_stack and heading_stack[-1][0] >= level:
                        heading_stack.pop()
                    heading_stack.append((level, heading_text))

            # Only process leaf/semi-leaf content tags to avoid duplicate parent/child text
            if tag_name in CONTENT_TAGS:
                # Check if this tag has child content tags of the same or finer grain
                has_nested_content = any(
                    child.name in CONTENT_TAGS
                    for child in element.find_all(CONTENT_TAGS, recursive=True)
                )
                if has_nested_content and tag_name not in {"p", "blockquote", "td", "th", "address"}:
                    continue

                text = self._clean_text(element.get_text(" ", strip=True))
                word_count = len(text.split())

                is_heading = bool(re.match(r"^h[1-6]$", tag_name))
                min_words = 1 if is_heading else self.min_chunk_words
                if word_count < min_words:
                    continue

                is_boilerplate = self._is_boilerplate_node(element)
                current_headings = [h[1] for h in heading_stack]
                page_depth = getattr(page.response, "depth", 0) if page.response else 0

                chunks.append(
                    ContentChunk(
                        page_url=page.url,
                        text=text,
                        tag=tag_name,
                        heading_hierarchy=list(current_headings),
                        is_boilerplate=is_boilerplate,
                        chunk_id=chunk_id,
                        word_count=word_count,
                        crawl_depth=page_depth,
                    )
                )
                chunk_id += 1

        return chunks

    def extract_full_visible_text(self, page: ParsedPage) -> str:
        """
        Deterministic extraction of full page visible text.
        Used by GroundingVerifier to ensure excerpts are verified against
        the actual visible text of the page.
        """
        if not page.response or not page.response.content:
            return ""

        try:
            soup = BeautifulSoup(page.response.content, "lxml")
        except Exception:
            soup = BeautifulSoup(page.response.content, "html.parser")

        for tag in soup.find_all(DISCARD_TAGS):
            tag.decompose()

        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()

        body = soup.find("body") or soup
        return self._clean_text(body.get_text(" ", strip=True))

    @staticmethod
    def _clean_text(text: str) -> str:
        """Collapse multiple spaces while preserving character casing & punctuation."""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _is_boilerplate_node(node: Tag) -> bool:
        """Check if node is located within header/footer/nav/aside or boilerplate class/id."""
        curr = node
        while curr and curr.name and curr.name != "[document]":
            name = curr.name.lower()
            if name in BOILERPLATE_TAGS:
                return True

            classes = curr.get("class", [])
            if isinstance(classes, list):
                class_str = " ".join(classes).lower()
            else:
                class_str = str(classes).lower()

            elem_id = str(curr.get("id", "")).lower()

            for kw in BOILERPLATE_CLASS_ID_KEYWORDS:
                if kw in class_str or kw in elem_id:
                    return True

            curr = curr.parent

        return False
