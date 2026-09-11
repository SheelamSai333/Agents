"""
Multi-signal search engine and passage ranker for Q3.

Combines BM25 lexical score, phrase matching, heading alignment,
URL slug relevance, and boilerplate suppression with strict support thresholds.
"""

from typing import List, Optional, Tuple
from urllib.parse import urlparse

from site_qa.indexer import BM25Index, tokenize
from site_qa.models import ContentChunk, ScoredPassage
from site_qa.query_processor import ProcessedQuery, stem_word


def check_explanatory_predicate(
    text: str,
    target_subject: str,
    content_terms: List[str],
    headings: List[str],
) -> Tuple[bool, bool]:
    """
    Checks whether a passage contains an explanatory predicate for target_subject,
    or if it is merely an oblique/incidental mention.
    Returns (has_explanatory_predicate, is_oblique_mention).
    """
    if not target_subject:
        return False, False

    import re
    text_lower = text.lower()
    subj_lower = target_subject.lower()

    # Candidate subjects: full subject plus primary sub-phrases
    candidate_subjects = [re.escape(subj_lower)]
    subj_words = subj_lower.split()
    if len(subj_words) > 1:
        candidate_subjects.append(re.escape(" ".join(subj_words[1:])))
        candidate_subjects.append(re.escape(" ".join(subj_words[:2])))

    subj_pattern = "|".join(candidate_subjects)

    # Explanatory predicate patterns:
    # "X is/are/was/were [a/an/the]?", "X helps", "X allows", "X enables", "X provides",
    # "X is used to/for", "X refers to", "X means", "X lets", "X can help", "X serves as",
    # "X: a [definition]"
    explanatory_regexes = [
        rf"\b(?:{subj_pattern})\s+(?:is|are|was|were)\b(?:\s+(?:a|an|the|one|designed|used|built|intended|defined|known|considered|meant|created|developed))?",
        rf"\b(?:{subj_pattern})\s+(?:helps?|allows?|enables?|provides?|offers?|lets?|serves?\s+as|refers?\s+to|means?|works?\s+by)\b",
        rf"\b(?:{subj_pattern})\s+(?:can\s+(?:help|be\s+used|provide|allow|enable))\b",
        rf"\b(?:{subj_pattern})\s*[:-]\s+[a-z0-9]",
    ]

    has_explanation = False
    for regex in explanatory_regexes:
        if re.search(regex, text_lower):
            has_explanation = True
            break

    # Check if an ancestor heading matches the subject and paragraph begins with an explanation
    if not has_explanation:
        for h in headings:
            h_lower = h.lower()
            if any(re.search(rf"\b{s}\b", h_lower) for s in candidate_subjects):
                if re.search(
                    r"^(?:it|this|the\s+(?:tool|platform|service|software|system|utility))\s+(?:is|helps?|allows?|enables?|provides?|can\s+help|serves?)\b",
                    text_lower,
                ):
                    has_explanation = True
                    break

    # Check if mention is strictly oblique / incidental (e.g. "...in Search Console", "...using Search Console")
    is_oblique = False
    if not has_explanation:
        oblique_match = re.search(
            rf"\b(?:in|into|using|with|via|through|inside|within|on|under|across)\s+(?:the\s+)?(?:{subj_pattern})\b",
            text_lower,
        )
        if oblique_match:
            is_oblique = True

    return has_explanation, is_oblique


DISQUALIFIED_LEGAL_PATTERNS = [
    r"\b(?:jurisdiction\s+of\s+(?:the\s+)?(?:competent\s+)?courts?)\b",
    r"\bcourts?\s+located\s+in\b",
    r"\bgoverned\s+by\s+(?:and\s+construed\s+in\s+accordance\s+with\s+)?(?:the\s+)?laws\s+of\b",
    r"\bterms\s+shall\s+be\s+governed\b",
    r"\bvenue\s+for\s+any\s+(?:dispute|action|claims?)\b",
    r"\bdisputes?\s+arising\s+(?:out\s+of|under)\b",
    r"\bsubject\s+to\s+(?:the\s+)?exclusive\s+jurisdiction\b",
]

LOCATION_HEADING_PATTERNS = [
    r"\b(?:locations?|training\s+centers?|centers?|centres?|offices?|campuses?|campus|headquarters?|address(?:es)?|where\s+we\s+are|visit\s+us|contact\s+us|branches?|reach\s+us|find\s+us)\b",
]

LOCATION_TEXT_PATTERNS = [
    r"\b(?:located\s+(?:at|in)|headquartered\s+in|based\s+in|headquarters\s+(?:is|are)\s+in|offices?\s+(?:in|located\s+in)|campus\s+in|centers?\s+in|centres?\s+in|branches?\s+in)\b",
    r"\b(?:training\s+centers?\s+across|centers?\s+across|campuses?\s+across)\b",
    r"\b(?:available\s+(?:online|offline)|online\s+or\s+(?:at\s+our\s+)?training\s+centers?|prefer\s+learning\s+from\s+home)\b",
    r"\b(?:survey\s+no|plot\s+no|floor|building|block|street|road|st\.|ave\.|suite|bldg|nagar|circle|colony|sector|cross|main\s+road)\b",
    r"\b(?:we\s+are\s+(?:a\s+)?(?:fully\s+)?remote|100%\s+online|conducted\s+online)\b",
    r"\b(?:roast(?:s|ing)?|brew(?:s|ing)?|operate(?:s|ing)?|manufacture(?:s|ing)?|serve(?:s|ing)?)\s+(?:in|at)\s+[A-Z][a-z]+\b",
]


def check_location_evidence(
    text: str,
    headings: List[str],
    page_url: str,
    query: ProcessedQuery,
) -> Tuple[bool, bool]:
    """
    Checks whether a passage contains genuine location/presence evidence,
    or if it should be disqualified (e.g., legal dispute/court jurisdiction clause).
    Returns (has_location_evidence, is_disqualified).
    """
    import re
    from urllib.parse import urlparse

    text_lower = text.lower()

    # Check disqualification (e.g. legal jurisdiction clauses)
    is_legal_query = any(
        t in query.clean_query
        for t in ("term", "terms", "condition", "court", "law", "jurisdiction", "dispute")
    )
    if not is_legal_query:
        for p in DISQUALIFIED_LEGAL_PATTERNS:
            if re.search(p, text_lower):
                return False, True

        url_path = urlparse(page_url).path.lower()
        if any(k in url_path for k in ("terms", "privacy", "cookie", "disclaimer", "legal", "tos")):
            return False, True

    # Exclude pure opening hours or days of operation chunks from being location evidence
    is_time_hours = bool(
        re.search(r"^(?:(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun|\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*[-–—to\s]+)+", text_lower)
    )
    if is_time_hours:
        return False, False

    has_heading = any(
        re.search(p, h.lower())
        for h in headings
        for p in LOCATION_HEADING_PATTERNS
    )

    has_loc_text = any(re.search(p, text_lower) for p in LOCATION_TEXT_PATTERNS)
    has_postal = bool(re.search(r"\b\d{5,6}\b", text))

    if has_loc_text or has_postal or has_heading:
        return True, False

    return False, False


class PassageSearcher:
    """Ranks passages and applies strict evidence-grounding thresholds."""

    def __init__(
        self,
        index: BM25Index,
        min_score_threshold: float = 0.35,
        min_term_coverage: float = 0.4,
        phrase_boost: float = 1.5,
        heading_boost: float = 1.3,
        url_boost: float = 1.2,
        boilerplate_multiplier: float = 0.25,
    ):
        self.index = index
        self.min_score_threshold = min_score_threshold
        self.min_term_coverage = min_term_coverage
        self.phrase_boost = phrase_boost
        self.heading_boost = heading_boost
        self.url_boost = url_boost
        self.boilerplate_multiplier = boilerplate_multiplier

    def search(
        self,
        query: ProcessedQuery,
        start_url: Optional[str] = None,
    ) -> List[ScoredPassage]:
        """Rank all chunks for the given processed query."""
        if not query.has_substantive_terms or self.index.doc_count == 0:
            return []

        import re
        scored_passages: List[ScoredPassage] = []
        total_query_terms = len(set(query.content_terms))

        for idx, chunk in enumerate(self.index.chunks):
            # Pass both raw and stemmed content terms for matching
            search_terms = list(query.content_terms)
            for qt in query.content_terms:
                st = stem_word(qt)
                if st != qt and st not in search_terms:
                    search_terms.append(st)

            base_score, matched_terms = self.index.score_chunk(idx, search_terms)
            if base_score <= 0.0:
                continue

            chunk_text_lower = chunk.text.lower()
            unique_matches = set()
            for m in matched_terms:
                for qt in query.content_terms:
                    if m == qt or m == stem_word(qt):
                        unique_matches.add(qt)

            # Check heading overlap
            heading_matches = 0
            for h in chunk.heading_hierarchy:
                h_tokens = set(tokenize(h))
                h_stems = {stem_word(t) for t in h_tokens}
                for qt in query.content_terms:
                    st_qt = stem_word(qt)
                    if qt in h_tokens or st_qt in h_tokens or st_qt in h_stems:
                        heading_matches += 1
                        unique_matches.add(qt)

            # Check URL slug overlap
            url_path = urlparse(chunk.page_url).path.lower()
            url_matches = sum(
                1 for qt in query.content_terms
                if qt in url_path or stem_word(qt) in url_path
            )

            # Check contiguous phrase matches
            has_phrase = False
            for phrase in query.phrases:
                if phrase in chunk_text_lower:
                    has_phrase = True
                    break

            # Explanatory predicate vs oblique mention detection for DEFINITION
            has_explanation = False
            is_oblique = False
            if query.intent == "DEFINITION" and query.target_subject:
                has_explanation, is_oblique = check_explanatory_predicate(
                    chunk.text, query.target_subject, query.content_terms, chunk.heading_hierarchy
                )

            # Location evidence verification for LOCATION
            has_location = False
            is_disqualified = False
            if query.intent == "LOCATION":
                has_location, is_disqualified = check_location_evidence(
                    chunk.text, chunk.heading_hierarchy, chunk.page_url, query
                )
                if is_disqualified:
                    # Disqualified passages receive zero score
                    continue

            # Term coverage: fraction of substantive query terms present in chunk or its heading
            coverage = len(unique_matches) / total_query_terms if total_query_terms > 0 else 0.0

            # Composite multiplier
            multiplier = 1.0
            if has_phrase:
                multiplier *= self.phrase_boost
            if heading_matches > 0:
                multiplier *= (self.heading_boost ** min(heading_matches, 2))
            if url_matches > 0:
                multiplier *= self.url_boost
            if chunk.is_boilerplate:
                multiplier *= self.boilerplate_multiplier

            # Intent-specific scoring
            if query.intent == "DEFINITION":
                if has_explanation:
                    multiplier *= 2.0  # Strong boost for genuine definition/explanation
                elif is_oblique:
                    multiplier *= 0.20  # Severe penalty for incidental oblique mentions
            elif query.intent == "LOCATION":
                if has_location:
                    has_direct_address = any(re.search(p, chunk_text_lower) for p in LOCATION_TEXT_PATTERNS) or bool(re.search(r"\b\d{5,6}\b", chunk.text))
                    is_pure_heading = chunk.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
                    if has_direct_address and not is_pure_heading:
                        multiplier *= 4.0  # Highest priority for concrete address/location body content
                    elif has_direct_address:
                        multiplier *= 2.0
                    else:
                        multiplier *= 1.2
                else:
                    multiplier *= 0.20

            # Context-dependent query weighting
            is_start_page = (chunk.crawl_depth == 0) or bool(start_url and chunk.page_url == start_url)
            if query.is_context_dependent:
                if is_start_page:
                    multiplier *= 2.5  # Prioritize supplied page as primary context
                else:
                    # Check semantic relevance of other crawled pages
                    is_semantically_relevant = False
                    if query.intent == "LOCATION":
                        is_semantically_relevant = any(
                            k in url_path
                            for k in ("contact", "about", "location", "center", "centre", "campus", "office", "address", "branch")
                        )
                    elif query.intent == "PRICE_COST":
                        is_semantically_relevant = any(k in url_path for k in ("pricing", "price", "plans", "subscription", "cost"))

                    if is_semantically_relevant:
                        multiplier *= 1.5
                    elif start_url and chunk.page_url.startswith(start_url.rstrip("/")):
                        multiplier *= 1.2
                    else:
                        multiplier *= 0.50
            else:
                # Standard crawl depth proximity weighting
                if chunk.crawl_depth == 0:
                    multiplier *= 1.30
                elif chunk.crawl_depth == 1:
                    multiplier *= 1.05
                elif chunk.crawl_depth >= 2:
                    multiplier *= 0.90

            # Coverage multiplier: penalize passages that only match a tiny fraction of query terms
            if coverage < 1.0:
                multiplier *= (coverage ** 1.5)

            final_score = base_score * multiplier

            scored_passages.append(
                ScoredPassage(
                    chunk=chunk,
                    score=final_score,
                    matched_terms=list(unique_matches),
                    has_phrase_match=has_phrase,
                    heading_match_count=heading_matches,
                    url_match_count=url_matches,
                    has_explanatory_predicate=has_explanation,
                    is_oblique_mention=is_oblique,
                    has_location_evidence=has_location,
                    is_disqualified=is_disqualified,
                )
            )

        # Deterministic sorting:
        # 1. Score (descending)
        # 2. Positive intent evidence first
        # 3. Non-boilerplate first
        # 4. Crawl depth (ascending - prefer start page)
        # 5. URL string (lexicographic)
        # 6. chunk_id (ascending)
        scored_passages.sort(
            key=lambda p: (
                -round(p.score, 4),
                0 if (p.has_explanatory_predicate or p.has_location_evidence) else 1,
                1 if p.chunk.is_boilerplate else 0,
                p.chunk.crawl_depth,
                p.chunk.page_url,
                p.chunk.chunk_id,
            )
        )

        return scored_passages

    def get_best_supported_passage(
        self,
        query: ProcessedQuery,
        start_url: Optional[str] = None,
    ) -> Optional[Tuple[ScoredPassage, float]]:
        """
        Returns the top passage if and only if it strictly satisfies the
        grounding / confidence threshold. Returns None if unsupported.
        """
        candidates = self.search(query, start_url=start_url)
        if not candidates:
            return None

        top = candidates[0]
        total_query_terms = len(set(query.content_terms))
        matched_count = len(set(top.matched_terms))
        coverage = matched_count / total_query_terms if total_query_terms > 0 else 0.0

        # Definitional intent gate:
        if query.intent == "DEFINITION":
            if not top.has_explanatory_predicate:
                return None

        # Location intent gate:
        if query.intent == "LOCATION":
            if top.is_disqualified or not top.has_location_evidence:
                return None

        # Require at least one informative (non-ubiquitous) term to match
        # (prevents matching only the sitewide company name across unrelated pages)
        if self.index.doc_count >= 5:
            informative_query_terms = [
                t for t in query.content_terms
                if (self.index.doc_freqs.get(t.lower(), 0) / self.index.doc_count) < 0.50
                and (self.index.doc_freqs.get(stem_word(t).lower(), 0) / self.index.doc_count) < 0.50
            ]
            if informative_query_terms:
                informative_matched = [
                    t for t in informative_query_terms
                    if t in top.matched_terms or stem_word(t) in top.matched_terms
                ]
                if not informative_matched and not top.has_phrase_match:
                    return None

        # Term coverage requirement:
        # - For 1-term queries: must match that term (coverage == 1.0)
        # - For 2-term queries: must match both terms (coverage == 1.0) unless exact phrase match
        # - For 3+ term queries: must match at least min_term_coverage
        if not top.has_phrase_match:
            if total_query_terms <= 2 and coverage < 1.0:
                return None
            elif total_query_terms >= 3 and coverage < self.min_term_coverage:
                return None

        # Check minimum score threshold
        if top.score < self.min_score_threshold:
            return None

        # If the top candidate is boilerplate and has low score, reject
        if top.chunk.is_boilerplate and top.score < (self.min_score_threshold * 1.5):
            return None

        return top, top.score
