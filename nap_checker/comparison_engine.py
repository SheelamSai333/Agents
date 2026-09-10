"""Deterministic comparison engine for NAP consistency."""

from difflib import SequenceMatcher
from typing import Dict, List

from nap_checker.models import NAPFieldReport, NAPOccurrence, NAPVerdict, NAPEvidence
from nap_checker.confidence import ConfidenceScorer
from nap_checker.normalizers import normalize_name, normalize_address, parse_address_components


class ComparisonEngine:
    """Compare NAP occurrences using deterministic rules."""

    def __init__(self):
        self.confidence_scorer = ConfidenceScorer()

    def compare_field(
        self,
        occurrences: List[NAPOccurrence],
        field: str,
        page_priorities: Dict[str, float] | None = None,
    ) -> NAPFieldReport:
        field_occurrences = [
            occurrence for occurrence in occurrences
            if occurrence.field == field
        ]

        pages = list(dict.fromkeys(
            occurrence.source_url
            for occurrence in field_occurrences
            if occurrence.raw_value
        ))

        values = list(dict.fromkeys(
            occurrence.raw_value
            for occurrence in field_occurrences
            if occurrence.raw_value
        ))

        normalized_values = list(dict.fromkeys(
            occurrence.normalized_value
            for occurrence in field_occurrences
            if occurrence.normalized_value
        ))

        evidence = [
            NAPEvidence(
                page=occurrence.source_url,
                raw_value=occurrence.raw_value,
                source_type=occurrence.source_type,
                source_quality=occurrence.source_quality,
            )
            for occurrence in field_occurrences
        ]

        if not field_occurrences:
            return NAPFieldReport(
                field=field,
                pages_compared=[],
                values=[],
                normalized_values=[],
                confidence=0.0,
                verdict="not_found",
                evidence=[],
                details=f"No {field} value was found.",
            )

        if field == "address":
            verdict, details = self._compare_addresses(field_occurrences)
        else:
            verdict, details = self._compare_simple_field(
                field_occurrences,
                field,
            )

        confidence = self.confidence_scorer.compute_confidence(
            field_occurrences,
            verdict,
            page_priorities or {},
        )

        return NAPFieldReport(
            field=field,
            pages_compared=pages,
            values=values,
            normalized_values=normalized_values,
            confidence=confidence,
            verdict=verdict,
            evidence=evidence,
            details=details,
        )

    def compare_all(
        self,
        occurrences: List[NAPOccurrence],
        page_priorities: Dict[str, float] | None = None,
    ) -> Dict[str, NAPFieldReport]:
        """Compare name, address, and phone."""
        return {
            field: self.compare_field(occurrences, field, page_priorities)
            for field in ("name", "address", "phone")
        }

    @staticmethod
    def _compare_simple_field(
        occurrences: List[NAPOccurrence],
        field: str,
    ):
        usable = [
            occurrence
            for occurrence in occurrences
            if occurrence.normalized_value
        ]

        if not usable:
            return "not_found", f"No usable normalized {field} value was found."

        # Weak HTML title/logo evidence should not override stronger
        # structured-data or explicitly labelled evidence.
        trusted = [
            occurrence
            for occurrence in usable
            if occurrence.source_quality >= 0.65
        ]

        comparison_occurrences = trusted or usable

        if field == "phone":
            # Build canonical phone values using suffix-matching.
            # A bare local number (e.g. "9876543210") is equivalent to
            # a country-coded number (e.g. "919876543210") if the longer
            # number ends with the shorter one.  This avoids hardcoding
            # any specific country code.
            raw_normalized = list(dict.fromkeys(
                occ.normalized_value
                for occ in comparison_occurrences
            ))

            canonical_values = _canonicalize_phone_values(raw_normalized)

            if len(canonical_values) == 1:
                raw_values = list(dict.fromkeys(
                    occurrence.raw_value
                    for occurrence in comparison_occurrences
                ))

                if len(comparison_occurrences) == 1:
                    quality = comparison_occurrences[0].source_quality

                    if quality >= 0.8:
                        return (
                            "consistent",
                            "One high-quality phone occurrence was found."
                        )

                    return (
                        "uncertain",
                        "Only one lower-confidence phone occurrence was found."
                    )

                if len(raw_values) > 1:
                    return (
                        "minor_formatting_difference",
                        "Phone values use different formatting or country-code "
                        "representations but resolve to the same number."
                    )

                return (
                    "consistent",
                    "All trusted phone occurrences resolve to the same number."
                )

            return (
                "genuine_mismatch",
                f"Different normalized phone values were found: "
                f"{', '.join(canonical_values)}."
            )

        normalized = list(dict.fromkeys(
            occurrence.normalized_value
            for occurrence in comparison_occurrences
        ))

        if len(normalized) == 1:
            raw_values = list(dict.fromkeys(
                occurrence.raw_value
                for occurrence in comparison_occurrences
            ))

            if len(comparison_occurrences) == 1:
                quality = comparison_occurrences[0].source_quality

                if quality >= 0.8:
                    return (
                        "consistent",
                        f"One high-quality {field} occurrence was found."
                    )

                return (
                    "uncertain",
                    f"Only one lower-confidence {field} occurrence was found."
                )

            if len(raw_values) > 1:
                return (
                    "minor_formatting_difference",
                    f"All trusted {field} values normalize to the same value "
                    f"despite different raw formatting."
                )

            return (
                "consistent",
                f"All trusted {field} occurrences normalize to the same value."
            )

        return (
            "genuine_mismatch",
            f"Different trusted normalized {field} values were found: "
            f"{', '.join(normalized)}."
        )

    @staticmethod
    def _compare_addresses(
        occurrences: List[NAPOccurrence],
    ):
        components = [
            parse_address_components(occurrence.raw_value)
            for occurrence in occurrences
        ]

        usable = [component for component in components if component.has_components()]

        if not usable:
            return "uncertain", "Address values could not be parsed reliably."

        # Compare important structured components first.
        component_fields = (
            "postal_code",
            "locality",
            "region",
        )

        for field in component_fields:
            values = {
                getattr(component, field).strip().lower()
                for component in usable
                if getattr(component, field)
            }

            if len(values) > 1:
                return (
                    "genuine_mismatch",
                    f"Address {field.replace('_', ' ')} values differ."
                )

        # Compare street components when enough information is available.
        streets = [
            component.street
            for component in usable
            if component.street
        ]

        if len(streets) >= 2:
            base = streets[0]

            for street in streets[1:]:
                similarity = SequenceMatcher(
                    None,
                    base.lower(),
                    street.lower(),
                ).ratio()

                if similarity < 0.80:
                    return (
                        "genuine_mismatch",
                        "Street address components differ substantially."
                    )

        normalized = list(dict.fromkeys(
            occurrence.normalized_value
            for occurrence in occurrences
            if occurrence.normalized_value
        ))

        raw_values = list(dict.fromkeys(
            occurrence.raw_value
            for occurrence in occurrences
        ))

        if len(normalized) == 1:
            if len(raw_values) > 1:
                return (
                    "minor_formatting_difference",
                    "Address values differ in formatting but normalize "
                    "to the same address."
                )

            return (
                "consistent",
                "All address components and normalized values agree."
            )

        # Sparse addresses: fuzzy similarity is supporting evidence only.
        if len(usable) >= 2:
            similarities = []

            base = usable[0].raw_normalized

            for component in usable[1:]:
                similarities.append(
                    SequenceMatcher(
                        None,
                        base,
                        component.raw_normalized,
                    ).ratio()
                )

            if similarities and min(similarities) >= 0.90:
                return (
                    "uncertain",
                    "Addresses are highly similar, but the available "
                    "components are too sparse to prove consistency."
                )

        return (
            "uncertain",
            "Address values differ, but the available components are "
            "insufficient to determine whether the difference is genuine."
        )


def _canonicalize_phone_values(values: list[str]) -> list[str]:
    """
    Reduce a set of normalized phone digit strings to canonical groups.

    If a shorter number is a strict suffix of a longer number, they are
    treated as the same phone number (the longer, country-coded form is
    kept as the canonical value).  This handles *any* country code
    without hardcoding specific prefixes.

    Example:
        ["919876543210", "9876543210"]  →  ["919876543210"]
        ["12125551234", "2125551234"]   →  ["12125551234"]
        ["919876543210", "919887766554"] → ["919876543210", "919887766554"]
    """
    if len(values) <= 1:
        return values

    # Sort longest first so shorter values can be matched as suffixes.
    sorted_vals = sorted(values, key=len, reverse=True)
    canonical: list[str] = []

    for val in sorted_vals:
        # Check if this value is a suffix of any already-kept canonical value.
        is_suffix = False
        for canon in canonical:
            if canon.endswith(val) and len(canon) > len(val):
                is_suffix = True
                break
        if not is_suffix:
            canonical.append(val)

    return canonical
