"""Confidence scoring for NAP findings."""

from typing import Dict, List

from nap_checker.models import NAPOccurrence


class ConfidenceScorer:
    """Calculate confidence using source quality and evidence strength."""

    def compute_confidence(
        self,
        occurrences: List[NAPOccurrence],
        verdict: str,
        page_priorities: Dict[str, float],
    ) -> float:
        if not occurrences:
            return 0.0

        source_quality = sum(
            occurrence.source_quality for occurrence in occurrences
        ) / len(occurrences)

        source_types = {
            occurrence.source_type
            for occurrence in occurrences
        }

        source_diversity = min(len(source_types) / 3.0, 1.0)

        count_score = min(len(occurrences) / 4.0, 1.0)

        priority_values = [
            page_priorities.get(occurrence.source_url, 0.4)
            for occurrence in occurrences
        ]

        page_priority = sum(priority_values) / len(priority_values)

        if any(occurrence.field == "phone" for occurrence in occurrences):
            from nap_checker.comparison_engine import _canonicalize_phone_values
            raw_norm = list(dict.fromkeys(
                occ.normalized_value
                for occ in occurrences
                if occ.normalized_value
            ))
            canon_norm = _canonicalize_phone_values(raw_norm)
            agreement = 1.0 if len(canon_norm) <= 1 else 0.0
        else:
            normalized_values = {
                occurrence.normalized_value
                for occurrence in occurrences
                if occurrence.normalized_value
            }
            agreement = 1.0 if len(normalized_values) <= 1 else 0.0

        score = (
            source_quality * 0.35
            + source_diversity * 0.20
            + count_score * 0.15
            + page_priority * 0.15
            + agreement * 0.15
        )

        # A single high-quality structured-data occurrence can still
        # be strong evidence, but do not allow it to appear fully certain.
        if len(occurrences) == 1:
            if occurrences[0].source_quality >= 0.9:
                score = min(score, 0.85)
            elif occurrences[0].source_quality <= 0.4:
                score = min(score, 0.35)

        # Genuine disagreement should reduce confidence somewhat,
        # because conflicting evidence makes the result less certain.
        if verdict == "genuine_mismatch":
            score *= 0.9

        if verdict == "uncertain":
            score *= 0.75

        return round(max(0.0, min(score, 1.0)), 2)
