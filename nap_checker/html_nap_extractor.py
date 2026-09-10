import re
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from seo_audit.models import ParsedPage
from nap_checker.models import NAPOccurrence
from nap_checker.normalizers import (
    normalize_name,
    normalize_address,
    normalize_phone,
    extract_title_brand,
)


class HTMLNAPExtractor:
    """Extract name, address, and phone from ordinary HTML."""

    PHONE_PATTERNS = (
        r"\+\d[\d\s().-]{7,}\d",
        r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
        r"\b\d{5}[-.\s]\d{5}\b",
        r"\b\d{10}\b",
    )

    PHONE_LABELS = (
        "phone",
        "telephone",
        "tel",
        "call",
        "mobile",
        "whatsapp",
        "contact",
    )

    ADDRESS_LABELS = (
        "address",
        "location",
        "office",
        "branch",
    )

    def extract_from_page(self, page: ParsedPage) -> List[NAPOccurrence]:
        """Extract NAP candidates from visible HTML."""
        occurrences: List[NAPOccurrence] = []

        soup = BeautifulSoup(
            page.response.content or "",
            "html.parser",
        )

        occurrences.extend(self._extract_phones(soup, page))
        occurrences.extend(self._extract_addresses(soup, page))
        occurrences.extend(self._extract_names(soup, page))

        return occurrences

    def _detect_country_hint(self, page: ParsedPage, text: str) -> str:
        """Infer country dialing hint from domain TLD or page content."""
        hostname = urlparse(page.url).hostname or ""
        tld = hostname.split(".")[-1].lower() if "." in hostname else ""

        if tld in ("in",) or hostname.endswith(".co.in"):
            return "IN"
        if tld in ("uk",) or hostname.endswith(".co.uk"):
            return "UK"
        if tld in ("ca",) or hostname.endswith(".gc.ca"):
            return "CA"
        if tld in ("au",) or hostname.endswith(".com.au"):
            return "AU"
        if tld in ("de",):
            return "DE"
        if tld in ("fr",):
            return "FR"
        if tld in ("sg",) or hostname.endswith(".com.sg"):
            return "SG"
        if tld in ("ae",):
            return "AE"

        # Check for explicit international dial code prefixes in text
        if re.search(r"\+91[\s\-]?\d", text):
            return "IN"
        if re.search(r"\+44[\s\-]?\d", text):
            return "UK"
        if re.search(r"\+1[\s\-]?\d", text):
            return "US"

        return ""

    def _extract_phones(
        self,
        soup: BeautifulSoup,
        page: ParsedPage,
    ) -> List[NAPOccurrence]:
        occurrences = []
        seen = set()

        text = soup.get_text(" ", strip=True)
        country_hint = self._detect_country_hint(page, text)

        # Highest-quality HTML phone evidence: tel: links and direct messaging links.
        for link in soup.find_all("a", href=True):
            href = str(link.get("href", "")).strip()
            href_lower = href.lower()
            raw = ""
            if href_lower.startswith("tel:"):
                raw = href[4:].strip()
            elif "wa.me/" in href_lower or "api.whatsapp.com/send" in href_lower:
                m = re.search(r"(?:wa\.me/|phone=)(\+?\d+)", href)
                if m:
                    raw = m.group(1).strip()

            if not raw and (href_lower.startswith("tel:") or "wa.me/" in href_lower):
                raw = link.get_text(" ", strip=True)

            if not raw:
                continue

            normalized = normalize_phone(raw, country_hint=country_hint)
            if not normalized:
                continue

            key = ("phone", normalized)
            if key in seen:
                continue
            seen.add(key)
            seen.add(("phone", raw))

            occurrences.append(
                NAPOccurrence(
                    field="phone",
                    raw_value=raw,
                    normalized_value=normalized,
                    source_url=page.url,
                    source_type="html_tel_link",
                    source_quality=0.85,
                    context_snippet=link.get_text(" ", strip=True)[:300] or href,
                )
            )

        # Labeled phone numbers (explicit business telephone label).
        for label in self.PHONE_LABELS:
            pattern = rf"{re.escape(label)}\s*[:\-]?\s*(\+?\d[\d\s().-]{{7,}}\d)"
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                raw = match.group(1).strip()
                normalized = normalize_phone(raw, country_hint=country_hint)
                if not normalized:
                    continue

                key = ("phone", normalized)
                if key in seen:
                    continue
                seen.add(key)
                seen.add(("phone", raw))

                occurrences.append(
                    NAPOccurrence(
                        field="phone",
                        raw_value=raw,
                        normalized_value=normalized,
                        source_url=page.url,
                        source_type="html_labeled_phone",
                        source_quality=0.80,
                        context_snippet=match.group(0)[:300],
                    )
                )

        # Generic phone detection only on pages likely to contain contact data.
        page_context = (
            (page.title or "").lower()
            + " "
            + " ".join(
                heading.text.lower()
                for heading in page.headings
                if heading.text
            )
            + " "
            + page.url.lower()
        )

        context_terms = (
            "contact",
            "about",
            "location",
            "office",
            "branch",
            "store",
        )

        if any(term in page_context for term in context_terms):
            for pattern in self.PHONE_PATTERNS:
                for match in re.finditer(pattern, text):
                    raw = match.group(0).strip()
                    # Filter out short fragments or coordinate strings (e.g. SVG paths)
                    digits_only = re.sub(r"[^\d]", "", raw)
                    if len(digits_only) < 8 or len(digits_only) > 15:
                        continue

                    normalized = normalize_phone(raw, country_hint=country_hint)
                    if not normalized:
                        continue

                    # If already extracted via tel link or labeled phone, skip redundant noise
                    if ("phone", normalized) in seen or ("phone", raw) in seen:
                        continue

                    seen.add(("phone", normalized))
                    seen.add(("phone", raw))

                    occurrences.append(
                        NAPOccurrence(
                            field="phone",
                            raw_value=raw,
                            normalized_value=normalized,
                            source_url=page.url,
                            source_type="html_phone_pattern",
                            source_quality=0.50,
                            context_snippet=raw,
                        )
                    )

        return occurrences

    def _extract_addresses(
        self,
        soup: BeautifulSoup,
        page: ParsedPage,
    ) -> List[NAPOccurrence]:
        occurrences = []
        seen = set()

        # Semantic <address> element.
        for element in soup.find_all("address"):
            raw = element.get_text(" ", strip=True)

            if not raw:
                continue

            key = raw.lower()
            if key in seen:
                continue

            seen.add(key)

            occurrences.append(
                NAPOccurrence(
                    field="address",
                    raw_value=raw,
                    normalized_value=normalize_address(raw),
                    source_url=page.url,
                    source_type="html_address_tag",
                    source_quality=0.80,
                    context_snippet=raw[:500],
                )
            )

        # Labels such as "Address: ..."
        text = soup.get_text("\n", strip=True)

        for label in self.ADDRESS_LABELS:
            pattern = rf"{re.escape(label)}\s*[:\-]\s*([^\n]{{8,250}})"
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                raw = match.group(1).strip(" ,.-")

                if len(raw) < 8:
                    continue

                key = raw.lower()
                if key in seen:
                    continue

                seen.add(key)

                occurrences.append(
                    NAPOccurrence(
                        field="address",
                        raw_value=raw,
                        normalized_value=normalize_address(raw),
                        source_url=page.url,
                        source_type="html_labeled_address",
                        source_quality=0.70,
                        context_snippet=match.group(0)[:500],
                    )
                )

        return occurrences

    def _is_valid_site_brand_element(self, element, page: ParsedPage) -> bool:
        """Verify an HTML element represents the audited site's brand, not content."""
        raw = element.get_text(" ", strip=True)
        if not raw or len(raw) < 2 or len(raw) > 50:
            return False

        # Must not be a sentence or paragraph
        if len(raw.split()) > 5 or "\n" in raw or ";" in raw:
            return False

        lower = raw.lower()

        # Reject common content/navigation/action noise words
        noise_words = {
            "question", "questions", "interview", "premium", "free", "intern",
            "engineer", "campus", "test", "tests", "available", "rating",
            "reviews", "review", "learn more", "read more", "view all", "explore",
            "sign in", "login", "register", "home", "about us", "contact us",
            "privacy policy", "terms of service", "menu", "search", "navigation",
            "categories", "category", "tags", "tag", "blog", "pricing", "pricing plan",
            "monthly", "yearly", "dashboard", "subscribe", "cart", "checkout",
            "all rights reserved", "all rights", "copyright", "solved", "solutions",
            "contribute", "practice", "company", "companies", "problems", "topics",
            "experience", "experiences", "assessment", "assessments",
        }
        if any(w in lower for w in noise_words):
            return False

        # Reject elements inside content containers (cards, lists, grids, tables, articles)
        prohibited_classes = {
            "card", "item", "list", "grid", "table", "directory", "question",
            "article", "post", "entry", "catalog", "row", "col", "badge",
            "category", "topic", "testimonial", "review", "partner", "sponsor",
            "client", "problem", "snippet", "dropdown", "modal", "tab",
        }

        # Check element classes and ancestor containers
        for parent in [element] + list(element.parents):
            if parent.name in ("body", "html", "[document]"):
                break

            # If inside main content tags (unless explicitly marked site-branding)
            if parent.name in ("article", "section", "table", "tbody", "tr", "td"):
                return False

            classes = parent.get("class", [])
            class_str = " ".join(classes).lower() if isinstance(classes, list) else str(classes).lower()
            parent_id = str(parent.get("id", "")).lower()

            for prohibited in prohibited_classes:
                if prohibited in class_str or prohibited in parent_id:
                    # Allow if it's explicitly navbar-brand or site-branding
                    if "navbar-brand" in class_str or "site-branding" in class_str:
                        continue
                    return False

        return True

    def _extract_names(
        self,
        soup: BeautifulSoup,
        page: ParsedPage,
    ) -> List[NAPOccurrence]:
        occurrences = []
        seen = set()

        # 1. OpenGraph site name: explicit, author-declared canonical site name in <head>.
        og = soup.find("meta", attrs={"property": "og:site_name"})
        if not og:
            og = soup.find("meta", attrs={"name": "og:site_name"})

        if og and og.get("content"):
            raw = str(og.get("content")).strip()
            normalized = normalize_name(raw)

            if normalized and len(raw) <= 80 and normalized not in seen:
                seen.add(normalized)
                occurrences.append(
                    NAPOccurrence(
                        field="name",
                        raw_value=raw,
                        normalized_value=normalized,
                        source_url=page.url,
                        source_type="html_og_site_name",
                        source_quality=0.85,
                        context_snippet=f'<meta property="og:site_name" content="{raw}">',
                        entity_name=raw,
                    )
                )

        # 2. Header/Navbar explicit site branding elements (representing the site itself).
        # We only accept elements in site header/navigation that represent the site's brand,
        # NEVER arbitrary company cards, lists, question titles, or content items.
        brand_selectors = (
            'header .navbar-brand, nav .navbar-brand, .navbar-brand',
            'header [class*="site-title"], [class*="site-title"]',
            'header [class*="site-name"], [class*="site-name"]',
            '.site-branding',
            'header a[href="/"], nav a[href="/"]',
        )

        for selector in brand_selectors:
            matched_elements = soup.select(selector)
            # If a selector matches many different items, it's a list/menu, not a unique site brand
            if len(matched_elements) > 3:
                continue

            for element in matched_elements:
                if not self._is_valid_site_brand_element(element, page):
                    continue

                raw = element.get_text(" ", strip=True)
                normalized = normalize_name(raw)

                if not normalized or normalized in seen:
                    continue

                seen.add(normalized)
                occurrences.append(
                    NAPOccurrence(
                        field="name",
                        raw_value=raw,
                        normalized_value=normalized,
                        source_url=page.url,
                        source_type="html_brand_element",
                        source_quality=0.75,
                        context_snippet=raw[:300],
                        entity_name=raw,
                    )
                )

        # 3. Header/logo alt text.
        for element in soup.select("header img[alt], nav img[alt], .navbar-brand img[alt], .site-logo img[alt]"):
            raw = str(element.get("alt", "")).strip()

            if not raw or len(raw) > 60 or len(raw.split()) > 5:
                continue

            # Skip common generic image alt words
            alt_lower = raw.lower()
            generic_alts = ("logo", "icon", "brand", "image", "search", "menu", "arrow", "close", "banner", "avatar")
            if alt_lower in generic_alts:
                continue

            normalized = normalize_name(raw)

            if normalized and normalized not in seen:
                seen.add(normalized)
                occurrences.append(
                    NAPOccurrence(
                        field="name",
                        raw_value=raw,
                        normalized_value=normalized,
                        source_url=page.url,
                        source_type="html_logo_alt",
                        source_quality=0.40,
                        context_snippet=f'<img alt="{raw}">',
                        entity_name=raw,
                    )
                )

        # 4. Title-derived branding is deliberately low confidence.
        title = (page.title or "").strip()
        raw = extract_title_brand(title)

        if raw:
            normalized = normalize_name(raw)

            if normalized and normalized not in seen:
                seen.add(normalized)
                occurrences.append(
                    NAPOccurrence(
                        field="name",
                        raw_value=raw,
                        normalized_value=normalized,
                        source_url=page.url,
                        source_type="html_title",
                        source_quality=0.30,
                        context_snippet=title[:300],
                        entity_name=raw,
                    )
                )

        return occurrences
