"""
Evidence formatting and collection utilities.
Ensures every finding includes concrete, verifiable excerpts from the page markup or HTTP headers.
"""

from typing import List, Optional


def truncate_snippet(text: str, max_length: int = 140) -> str:
    """Safely truncate markup or text for concise, readable evidence strings."""
    if not text:
        return ""
    text = " ".join(text.split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_title_evidence(title_text: Optional[str], raw_tag: Optional[str]) -> str:
    """Format evidence for title-related findings."""
    if not title_text and not raw_tag:
        return "No <title> element was found in the HTML <head>."
    char_len = len(title_text) if title_text else 0
    tag_disp = truncate_snippet(raw_tag) if raw_tag else f"<title>{title_text}</title>"
    return f"The <title> tag contains {char_len} characters: '{tag_disp}'."


def format_meta_desc_evidence(desc_text: Optional[str], raw_tag: Optional[str]) -> str:
    """Format evidence for meta description findings."""
    if not desc_text and not raw_tag:
        return "No <meta name=\"description\"> tag was found in the HTML <head>."
    char_len = len(desc_text) if desc_text else 0
    tag_disp = truncate_snippet(raw_tag) if raw_tag else f"<meta name=\"description\" content=\"{desc_text}\">"
    return f"Meta description tag contains {char_len} characters: '{tag_disp}'."


def format_heading_evidence(level: int, count: int, snippets: List[str]) -> str:
    """Format evidence for heading count and tags."""
    tag_name = f"<h{level}>"
    if count == 0:
        return f"Found 0 {tag_name} elements in the document."
    samples = ", ".join(f"'{truncate_snippet(s, 60)}'" for s in snippets[:3])
    return f"Found {count} {tag_name} elements: {samples}."


def format_image_alt_evidence(missing_alts: List[str]) -> str:
    """Format evidence for missing image alt attributes."""
    count = len(missing_alts)
    samples = ", ".join(f"'{truncate_snippet(img, 70)}'" for img in missing_alts[:3])
    suffix = f" (and {count - 3} more)" if count > 3 else ""
    return f"Found {count} <img> element(s) missing an 'alt' attribute: {samples}{suffix}."


def format_canonical_evidence(canonicals: List[str], raw_tags: List[str]) -> str:
    """Format evidence for canonical tag findings."""
    if not canonicals:
        return "No <link rel=\"canonical\"> tag was found in the HTML <head>."
    if len(canonicals) > 1:
        samples = ", ".join(f"'{truncate_snippet(t, 80)}'" for t in raw_tags[:3])
        return f"Found {len(canonicals)} conflicting canonical tags in markup: {samples}."
    return f"Canonical tag found: '{truncate_snippet(raw_tags[0] if raw_tags else canonicals[0], 100)}'."


def format_robots_meta_evidence(directives: List[str], raw_tags: List[str]) -> str:
    """Format evidence for robots meta tags."""
    all_directives = ", ".join(directives)
    tag_samples = ", ".join(f"'{truncate_snippet(t, 80)}'" for t in raw_tags)
    return f"Robots meta directive '{all_directives}' detected in markup: {tag_samples}."


def format_broken_link_evidence(href: str, resolved_url: str, status_code: int, link_html: str) -> str:
    """Format evidence for broken links."""
    snippet = truncate_snippet(link_html, 80)
    return (
        f"Internal link '{snippet}' pointing to '{resolved_url}' (href='{href}') "
        f"returned HTTP status {status_code}."
    )


def format_mixed_content_evidence(insecure_tags: List[str]) -> str:
    """Format evidence for mixed content (HTTP assets on HTTPS page)."""
    count = len(insecure_tags)
    samples = ", ".join(f"'{truncate_snippet(t, 80)}'" for t in insecure_tags[:3])
    suffix = f" (and {count - 3} more)" if count > 3 else ""
    return f"Found {count} insecure HTTP subresource(s) loaded on HTTPS page: {samples}{suffix}."


def format_duplicate_evidence(tag_type: str, value: str, matching_pages: List[str]) -> str:
    """Format evidence for cross-page duplicate titles or descriptions."""
    pages_str = ", ".join(matching_pages[:4])
    suffix = f" (and {len(matching_pages) - 4} more)" if len(matching_pages) > 4 else ""
    return (
        f"Duplicate {tag_type} '{truncate_snippet(value, 80)}' shared across "
        f"{len(matching_pages)} pages: {pages_str}{suffix}."
    )
