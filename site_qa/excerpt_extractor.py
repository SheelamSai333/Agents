"""
Exact Verbatim Excerpt Extractor for Q3.

Extracts a clean, tight, cohesive passage from the winning chunk
by identifying the highest-density sentence window while guaranteeing
100% verbatim substring fidelity (no paraphrase, no modification).
"""

import re
from typing import List, Tuple

from site_qa.models import ScoredPassage
from site_qa.query_processor import ProcessedQuery


class ExcerptExtractor:
    """Extracts exact verbatim sentences from a winning passage chunk."""

    def __init__(self, max_excerpt_chars: int = 350):
        self.max_excerpt_chars = max_excerpt_chars

    def extract(self, passage: ScoredPassage, query: ProcessedQuery) -> str:
        """
        Extract the best excerpt from passage.chunk.text.
        Guaranteed to be an exact contiguous substring of chunk.text.
        """
        text = passage.chunk.text.strip()
        if len(text) <= self.max_excerpt_chars:
            return text

        # Find sentence spans inside text
        sentences = self._find_sentence_spans(text)
        if not sentences:
            return text[:self.max_excerpt_chars].rsplit(" ", 1)[0]

        # Score each sentence span
        scored_spans: List[Tuple[float, int, int]] = []
        query_terms = set(query.content_terms)

        for start, end in sentences:
            sentence_text = text[start:end].lower()
            # Count term matches
            term_matches = sum(1 for t in query_terms if t in sentence_text)
            # Bonus for phrase matches
            phrase_bonus = sum(2 for p in query.phrases if p in sentence_text)
            # Bonus for explanatory predicates
            explanation_bonus = 0.0
            if query.intent == "DEFINITION" and query.target_subject:
                from site_qa.searcher import check_explanatory_predicate
                has_expl, is_oblique = check_explanatory_predicate(
                    text[start:end], query.target_subject, query.content_terms, []
                )
                if has_expl:
                    explanation_bonus = 5.0
                elif is_oblique:
                    explanation_bonus = -2.0

            score = term_matches + phrase_bonus + explanation_bonus
            scored_spans.append((score, start, end))

        # Find best starting sentence
        best_idx = 0
        best_score = -1.0
        for idx, (score, _, _) in enumerate(scored_spans):
            if score > best_score:
                best_score = score
                best_idx = idx

        # Try to expand to 1 contiguous neighbor (either next or prev) if within char limit
        start = scored_spans[best_idx][1]
        end = scored_spans[best_idx][2]

        # Try appending next sentence
        if best_idx + 1 < len(scored_spans):
            next_end = scored_spans[best_idx + 1][2]
            if (next_end - start) <= self.max_excerpt_chars:
                end = next_end
        # Otherwise try prepending previous sentence
        elif best_idx - 1 >= 0:
            prev_start = scored_spans[best_idx - 1][1]
            if (end - prev_start) <= self.max_excerpt_chars:
                start = prev_start

        excerpt = text[start:end].strip()
        return excerpt if excerpt else text

    @staticmethod
    def _find_sentence_spans(text: str) -> List[Tuple[int, int]]:
        """
        Identify (start, end) character index spans for sentences
        in text using punctuation boundaries.
        """
        spans: List[Tuple[int, int]] = []
        # Match sentences ending with ., !, ? followed by whitespace or string end
        pattern = re.compile(r"([^.!?]+[.!?]+(?:\s+|$)|[^.!?]+$)")
        for match in pattern.finditer(text):
            s, e = match.span()
            matched_str = text[s:e].strip()
            if matched_str:
                # Find actual strip start and end within match
                actual_start = text.find(matched_str, s)
                actual_end = actual_start + len(matched_str)
                spans.append((actual_start, actual_end))

        return spans
