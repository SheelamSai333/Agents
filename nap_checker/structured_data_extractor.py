"""Extract NAP information from JSON-LD and Microdata."""

import json
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from seo_audit.models import ParsedPage
from nap_checker.models import NAPOccurrence
from nap_checker.normalizers import (
    normalize_name,
    normalize_address,
    normalize_phone,
)


TARGET_TYPES = {
    "LocalBusiness",
    "Organization",
    "Store",
    "Restaurant",
    "Corporation",
    "MedicalBusiness",
    "DentalOffice",
    "LegalService",
    "FinancialService",
    "RealEstateAgent",
    "AutoDealer",
}


class StructuredDataExtractor:
    """Extract NAP occurrences from schema.org structured data."""

    def extract_from_page(self, page: ParsedPage) -> List[NAPOccurrence]:
        occurrences: List[NAPOccurrence] = []

        soup = BeautifulSoup(page.response.content or "", "html.parser")

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw_json = script.string or script.get_text()
            if not raw_json:
                continue

            try:
                data = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                continue

            for entity in self._find_entities(data):
                occurrences.extend(self._extract_entity(entity, page))

        occurrences.extend(self._extract_microdata(soup, page))

        return occurrences

    def _find_entities(self, data: Any) -> List[Dict[str, Any]]:
        """Recursively find schema.org business entities."""
        entities: List[Dict[str, Any]] = []

        if isinstance(data, list):
            for item in data:
                entities.extend(self._find_entities(item))
            return entities

        if not isinstance(data, dict):
            return entities

        entity_type = data.get("@type", "")

        types = entity_type if isinstance(entity_type, list) else [entity_type]

        if any(self._is_target_type(str(t)) for t in types):
            entities.append(data)

        for key, value in data.items():
            if key.startswith("@") and key != "@graph":
                continue

            if isinstance(value, (dict, list)):
                entities.extend(self._find_entities(value))

        return entities

    @staticmethod
    def _is_target_type(entity_type: str) -> bool:
        if entity_type in TARGET_TYPES:
            return True

        if entity_type.endswith("Business"):
            return True

        return False

    def _extract_entity(
        self,
        entity: Dict[str, Any],
        page: ParsedPage,
    ) -> List[NAPOccurrence]:
        occurrences: List[NAPOccurrence] = []

        entity_name = self._string_value(entity.get("name", ""))

        if entity_name:
            occurrences.append(
                NAPOccurrence(
                    field="name",
                    raw_value=entity_name,
                    normalized_value=normalize_name(entity_name),
                    source_url=page.url,
                    source_type="json_ld",
                    source_quality=1.0,
                    context_snippet=json.dumps(entity, ensure_ascii=False)[:500],
                    entity_name=entity_name,
                )
            )

        phone = self._string_value(entity.get("telephone", ""))

        if phone:
            occurrences.append(
                NAPOccurrence(
                    field="phone",
                    raw_value=phone,
                    normalized_value=normalize_phone(phone),
                    source_url=page.url,
                    source_type="json_ld",
                    source_quality=1.0,
                    context_snippet=json.dumps(entity, ensure_ascii=False)[:500],
                    entity_name=entity_name,
                )
            )

        address = entity.get("address")

        if isinstance(address, dict):
            address_text = self._address_to_string(address)
        else:
            address_text = self._string_value(address)

        if address_text:
            occurrences.append(
                NAPOccurrence(
                    field="address",
                    raw_value=address_text,
                    normalized_value=normalize_address(address_text),
                    source_url=page.url,
                    source_type="json_ld",
                    source_quality=1.0,
                    context_snippet=json.dumps(address, ensure_ascii=False)[:500],
                    entity_name=entity_name,
                )
            )

        return occurrences

    @staticmethod
    def _address_to_string(address: Dict[str, Any]) -> str:
        """Convert PostalAddress properties into a readable address."""
        fields = [
            "streetAddress",
            "addressLocality",
            "addressRegion",
            "postalCode",
            "addressCountry",
        ]

        parts = []

        for field in fields:
            value = address.get(field)

            if isinstance(value, dict):
                value = value.get("name") or value.get("@id") or ""

            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)

            if value:
                parts.append(str(value).strip())

        return ", ".join(parts)

    def _extract_microdata(
        self,
        soup: BeautifulSoup,
        page: ParsedPage,
    ) -> List[NAPOccurrence]:
        """Extract NAP from schema.org Microdata."""
        occurrences: List[NAPOccurrence] = []

        for item in soup.find_all(attrs={"itemtype": True}):
            itemtype = str(item.get("itemtype", ""))

            if "schema.org/" not in itemtype:
                continue

            schema_type = itemtype.rsplit("/", 1)[-1]

            if not self._is_target_type(schema_type):
                continue

            entity_name = ""
            properties: Dict[str, str] = {}

            for element in item.find_all(attrs={"itemprop": True}):
                prop = str(element.get("itemprop", "")).split()[0]

                if prop not in {
                    "name",
                    "telephone",
                    "streetAddress",
                    "addressLocality",
                    "addressRegion",
                    "postalCode",
                    "addressCountry",
                }:
                    continue

                value = (
                    element.get("content")
                    or element.get("value")
                    or element.get_text(" ", strip=True)
                )

                if value:
                    properties[prop] = value

            entity_name = properties.get("name", "")

            if entity_name:
                occurrences.append(
                    NAPOccurrence(
                        field="name",
                        raw_value=entity_name,
                        normalized_value=normalize_name(entity_name),
                        source_url=page.url,
                        source_type="microdata",
                        source_quality=0.9,
                        context_snippet=str(item)[:500],
                        entity_name=entity_name,
                    )
                )

            phone = properties.get("telephone", "")

            if phone:
                occurrences.append(
                    NAPOccurrence(
                        field="phone",
                        raw_value=phone,
                        normalized_value=normalize_phone(phone),
                        source_url=page.url,
                        source_type="microdata",
                        source_quality=0.9,
                        context_snippet=str(item)[:500],
                        entity_name=entity_name,
                    )
                )

            address_parts = [
                properties.get("streetAddress", ""),
                properties.get("addressLocality", ""),
                properties.get("addressRegion", ""),
                properties.get("postalCode", ""),
                properties.get("addressCountry", ""),
            ]

            address_text = ", ".join(p for p in address_parts if p)

            if address_text:
                occurrences.append(
                    NAPOccurrence(
                        field="address",
                        raw_value=address_text,
                        normalized_value=normalize_address(address_text),
                        source_url=page.url,
                        source_type="microdata",
                        source_quality=0.9,
                        context_snippet=str(item)[:500],
                        entity_name=entity_name,
                    )
                )

        return occurrences

    @staticmethod
    def _string_value(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, dict):
            return str(value.get("name") or value.get("@id") or "").strip()

        if isinstance(value, list):
            return ", ".join(
                StructuredDataExtractor._string_value(v)
                for v in value
                if StructuredDataExtractor._string_value(v)
            )

        return ""
