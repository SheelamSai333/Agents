"""Extract NAP information from visible HTML content."""

import re
from typing import List

from bs4 import BeautifulSoup

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

    def _extract_phones(
        self,
        soup: BeautifulSoup,
        page: ParsedPage,
    ) -> List[NAPOccurrence]:
        occurrences = []
        seen = set()

        # Highest-quality HTML phone evidence: tel: links.
        for link in soup.find_all("a", href=True):
            href = str(link.get("href", ""))
            if not href.lower().startswith("tel:"):
                continue

            raw = href[4:].strip()
            if not raw:
                raw = link.get_text(" ", strip=True)

            if not raw:
                continue

            key = ("phone", raw)
            if key in seen:
                continue

            seen.add(key)

            occurrences.append(
                NAPOccurrence(
                    field="phone",
                    raw_value=raw,
                    normalized_value=normalize_phone(raw),
                    source_url=page.url,
                    source_type="html_tel_link",
                    source_quality=0.85,
                    context_snippet=link.get_text(" ", strip=True)[:300],
                )
            )

        text = soup.get_text(" ", strip=True)

        # Labeled phone numbers.
        for label in self.PHONE_LABELS:
            pattern = rf"{re.escape(label)}\s*[:\-]?\s*(\+?\d[\d\s().-]{{7,}}\d)"
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                raw = match.group(1).strip()
                key = ("phone", raw)

                if key in seen:
                    continue

                seen.add(key)

                occurrences.append(
                    NAPOccurrence(
                        field="phone",
                        raw_value=raw,
                        normalized_value=normalize_phone(raw),
                        source_url=page.url,
                        source_type="html_labeled_phone",
                        source_quality=0.70,
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
                    key = ("phone", raw)

                    if key in seen:
                        continue

                    seen.add(key)

                    occurrences.append(
                        NAPOccurrence(
                            field="phone",
                            raw_value=raw,
                            normalized_value=normalize_phone(raw),
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

    def _extract_names(
        self,
        soup: BeautifulSoup,
        page: ParsedPage,
    ) -> List[NAPOccurrence]:
        occurrences = []
        seen = set()

        # Prefer explicit branding/company classes.
        selectors = (
            '[class*="brand"]',
            '[class*="company"]',
            '[class*="business"]',
        )

        for selector in selectors:
            for element in soup.select(selector):
                raw = element.get_text(" ", strip=True)

                if not raw or len(raw) > 120:
                    continue

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

        # OpenGraph site name.
        og = soup.find(
            "meta",
            attrs={
                "property": "og:site_name",
            },
        )

        if og and og.get("content"):
            raw = str(og.get("content")).strip()
            normalized = normalize_name(raw)

            if normalized and normalized not in seen:
                seen.add(normalized)

                occurrences.append(
                    NAPOccurrence(
                        field="name",
                        raw_value=raw,
                        normalized_value=normalized,
                        source_url=page.url,
                        source_type="html_og_site_name",
                        source_quality=0.65,
                        context_snippet=raw,
                        entity_name=raw,
                    )
                )

        # Header/logo alt text.
        for element in soup.select("header img[alt], nav img[alt]"):
            raw = str(element.get("alt", "")).strip()

            if not raw or len(raw) > 100:
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
                        context_snippet=raw,
                        entity_name=raw,
                    )
                )

        # Title-derived branding is deliberately low confidence.
        title = (page.title or "").strip()
        raw = extract_title_brand(title)

        if raw:
            normalized = normalize_name(raw)

            if normalized and normalized not in seen:
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
