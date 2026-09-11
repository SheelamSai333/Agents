"""
Natural Language Query Processing for Q3.

Strips conversational question wrappers, identifies content terms,
extracts key multi-word phrases, and flags substantive query content.
"""

import re
from dataclasses import dataclass, field
from typing import List, Set


# Common English stopwords and question words
STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "per", "via",
    # Conversational wrappers
    "tell", "know", "find", "give", "show", "please", "can", "may", "much", "many",
    "information", "details", "website", "site", "page",
}

QUESTION_PREFIX_PATTERNS = [
    r"^(can\s+you\s+(please\s+)?tell\s+me(\s+about)?)\b",
    r"^(what\s+(is|are|was|were)\s+(the|a|an)?)\b",
    r"^(where\s+(can\s+i|to|is|are))\b",
    r"^(how\s+(much\s+(is|does|do)|can\s+i|do\s+i|to|many))\b",
    r"^(is\s+there\s+(a|an|any)?)\b",
    r"^(do\s+they\s+(have|offer|provide))\b",
    r"^(does\s+the\s+(company|website|business))\b",
    r"^(who\s+(is|are)\s+(the)?)\b",
    r"^(tell\s+me\s+about)\b",
]


def stem_word(w: str) -> str:
    """Deterministic English suffix stemmer for retrieval matching."""
    w = w.lower()
    if len(w) <= 3:
        return w
    if w.endswith("ions") and len(w) > 5:
        w = w[:-1]
    if w.endswith("ion") and len(w) > 4:
        w = w[:-3]
    for suffix in ("ing", "ly", "ed", "es", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[:-len(suffix)]
    return w


@dataclass
class ProcessedQuery:
    raw_query: str
    clean_query: str
    content_terms: List[str]
    phrases: List[str] = field(default_factory=list)
    has_substantive_terms: bool = True
    intent: str = "GENERAL"  # DEFINITION, PRICE_COST, LOCATION, PROCEDURAL, LEADERSHIP_ABOUT, REQUIREMENTS, GENERAL
    target_subject: str = ""
    is_context_dependent: bool = False
    context_pronouns: List[str] = field(default_factory=list)


class QueryProcessor:
    """Processes user query into structured tokens, phrases, and semantic intent."""

    @classmethod
    def process(cls, query: str) -> ProcessedQuery:
        raw = query.strip()
        cleaned = raw.lower()

        # Strip ending punctuation
        cleaned = re.sub(r"[?!.,;:]+$", "", cleaned).strip()

        # Detect context-dependent pronouns referring to the website / subject entity
        found_pronouns = [
            p for p in ("this", "it", "here", "that", "these")
            if re.search(rf"\b{p}\b", cleaned)
        ]
        is_context_dependent = len(found_pronouns) > 0

        # Classify intent & target subject
        intent = "GENERAL"
        target_subject = ""

        # Check DEFINITION intent: "what is X", "what are X", "who is X", "define X", "explain X"
        def_match = re.match(
            r"^(?:what\s+(?:is|are|was|were)|who\s+(?:is|are|was|were)|define|explain)\s+(?:the\s+|a\s+|an\s+)?(.+)$",
            cleaned,
            flags=re.IGNORECASE,
        )
        if def_match:
            intent = "DEFINITION"
            target_subject = def_match.group(1).strip() if def_match.group(1) else ""
            target_subject = re.sub(r"[?!.,;:]+$", "", target_subject).strip()
            # If target_subject has trailing filler like "used for", "doing", etc.
            target_subject = re.sub(r"\s+(mean|used\s+for|stand\s+for)$", "", target_subject).strip()

        elif re.match(r"^(how\s+much|what\s+(is\s+the\s+)?(price|pricing|cost))\b", cleaned):
            intent = "PRICE_COST"
        elif re.match(r"^(where\s+(is|are|can\s+i\s+find)|what\s+is\s+the\s+(address|location))\b", cleaned) or \
             re.search(r"\b(where\s+(?:is|are|can\s+i\s+find)\b|located|location|address|headquartered|headquarters)\b", cleaned):
            intent = "LOCATION"
        elif re.match(r"^(how\s+(can\s+i|do\s+i|to))\b", cleaned):
            intent = "PROCEDURAL"
        elif re.search(r"\b(who\s+(?:runs?|founded|operates?|owns?|manages?)|founder|leadership|team)\b", cleaned):
            intent = "LEADERSHIP_ABOUT"
        elif re.search(r"\b(requirements?|eligibility|prerequisites?|qualifications?)\b", cleaned):
            intent = "REQUIREMENTS"

        # Strip question prefix patterns for clean_query
        for pattern in QUESTION_PREFIX_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

        # Extract all words
        words = re.findall(r"\b[a-z0-9]+(?:[-'][a-z0-9]+)*\b", cleaned)

        # Content terms (non-stopwords)
        content_terms = [w for w in words if w not in STOPWORDS and len(w) > 1]

        # Extract contiguous 2-word and 3-word candidate phrases
        phrases: List[str] = []
        for i in range(len(content_terms) - 1):
            phrases.append(f"{content_terms[i]} {content_terms[i+1]}")
            if i + 2 < len(content_terms):
                phrases.append(f"{content_terms[i]} {content_terms[i+1]} {content_terms[i+2]}")

        # Add target_subject as an explicit phrase if it has multiple words
        if target_subject and " " in target_subject and target_subject not in phrases:
            phrases.insert(0, target_subject)

        # Also preserve explicit quoted phrases if any exist in raw query
        quoted = re.findall(r'"([^"]+)"', raw.lower())
        for q in quoted:
            q_clean = q.strip()
            if q_clean and q_clean not in phrases:
                phrases.append(q_clean)

        return ProcessedQuery(
            raw_query=raw,
            clean_query=cleaned,
            content_terms=content_terms,
            phrases=phrases,
            has_substantive_terms=len(content_terms) > 0,
            intent=intent,
            target_subject=target_subject,
            is_context_dependent=is_context_dependent,
            context_pronouns=found_pronouns,
        )
