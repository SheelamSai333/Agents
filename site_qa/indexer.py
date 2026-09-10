"""
In-memory BM25 index for semantic content chunks.
Deterministic, pure Python, zero external dependencies.
"""

import math
import re
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple

from site_qa.models import ContentChunk
from site_qa.query_processor import stem_word


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric tokens with stems."""
    raw_tokens = [w for w in re.findall(r"\b[a-z0-9]+(?:[-'][a-z0-9]+)*\b", text.lower()) if len(w) > 1]
    expanded: List[str] = []
    for t in raw_tokens:
        expanded.append(t)
        st = stem_word(t)
        if st != t:
            expanded.append(st)
    return expanded


class BM25Index:
    """Okapi BM25 Indexer for ContentChunk passages."""

    def __init__(self, chunks: List[ContentChunk], k1: float = 1.5, b: float = 0.40):
        self.k1 = k1
        self.b = b
        self.chunks = chunks
        self.doc_count = len(chunks)

        # Index structures
        self.doc_lengths: List[int] = []
        self.doc_term_freqs: List[Counter] = []
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.idf: Dict[str, float] = {}

        self._build_index()

    def _build_index(self) -> None:
        """Process all chunks to compute term frequencies and IDF."""
        if self.doc_count == 0:
            self.avg_doc_len = 0.0
            return

        total_length = 0
        for chunk in self.chunks:
            tokens = tokenize(chunk.text)
            length = len(tokens)
            self.doc_lengths.append(length)
            total_length += length

            tf = Counter(tokens)
            self.doc_term_freqs.append(tf)

            for term in tf.keys():
                self.doc_freqs[term] += 1

        self.avg_doc_len = total_length / self.doc_count if self.doc_count > 0 else 0.0

        # Calculate IDF with standard smoothing
        for term, df in self.doc_freqs.items():
            self.idf[term] = math.log(1.0 + (self.doc_count - df + 0.5) / (df + 0.5))

    def score_chunk(self, doc_idx: int, query_terms: List[str]) -> Tuple[float, List[str]]:
        """
        Compute BM25 score of chunk at doc_idx against query terms.
        Returns (bm25_score, list_of_matched_terms).
        """
        if doc_idx < 0 or doc_idx >= self.doc_count:
            return 0.0, []

        doc_len = self.doc_lengths[doc_idx]
        if doc_len == 0 or self.avg_doc_len == 0:
            return 0.0, []

        tf_map = self.doc_term_freqs[doc_idx]
        score = 0.0
        matched_terms: List[str] = []

        len_norm = 1.0 - self.b + self.b * (doc_len / self.avg_doc_len)

        for term in set(query_terms):
            if term in tf_map:
                matched_terms.append(term)
                tf = tf_map[term]
                idf = self.idf.get(term, 0.0)
                term_score = idf * (tf * (self.k1 + 1.0)) / (tf + self.k1 * len_norm)
                score += term_score

        return score, matched_terms

    def get_term_document_frequency(self, term: str) -> int:
        """Return how many documents contain this term."""
        return self.doc_freqs.get(term.lower(), 0)
