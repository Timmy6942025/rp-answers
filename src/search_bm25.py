#!/usr/bin/env python3
"""BM25-based search engine for Reading Plus questions.

BM25 is a probabilistic ranking function used by search engines.
Better than TF-IDF for question answering because it:
- Normalizes for document length
- Uses saturation functions for term frequency
- Has proven effectiveness in information retrieval
"""

import json
import math
import re
from collections import Counter
from typing import List, Dict, Tuple
import numpy as np


class BM25SearchEngine:
    """BM25 search engine for Reading Plus questions."""

    def __init__(
        self, data_file="data/processed/reading_plus_data.json", k1=1.5, b=0.75
    ):
        """
        Initialize BM25 search engine.

        Args:
            data_file: Path to Reading Plus JSON data
            k1: Term frequency saturation parameter (1.2-2.0 typical)
            b: Length normalization parameter (0-1, higher = more normalization)
        """
        self.k1 = k1
        self.b = b

        print("Loading Reading Plus data...")
        with open(data_file) as f:
            self.data = json.load(f)

        self.documents = []
        self.doc_metadata = []
        self._build_index()

        print(f"Indexed {len(self.documents)} questions")

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        text = text.lower()
        words = re.findall(r"\b\w+\b", text)
        return words

    def _build_index(self):
        """Build BM25 index from questions."""
        stop_words = {
            "what",
            "is",
            "the",
            "a",
            "an",
            "in",
            "on",
            "at",
            "by",
            "for",
            "to",
            "of",
            "with",
            "as",
            "and",
            "or",
            "but",
            "how",
            "why",
            "when",
            "where",
            "which",
            "who",
            "whose",
            "does",
            "do",
            "did",
            "are",
            "were",
            "was",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "it",
            "from",
            "they",
            "their",
            "them",
            "you",
            "your",
            "i",
            "we",
            "our",
            "he",
            "she",
            "his",
            "her",
            "its",
            "all",
            "each",
            "every",
            "both",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "also",
        }

        # Collect all documents
        for level_name, level_data in self.data.get("levels", {}).items():
            for story in level_data.get("stories", []):
                for question in story.get("questions", []):
                    question_text = question.get("question_text", "")
                    answer = question.get("answer", "")

                    if question_text:
                        tokens = self._tokenize(question_text)
                        # Remove stop words
                        tokens = [
                            t for t in tokens if t not in stop_words and len(t) > 1
                        ]

                        if tokens:
                            self.documents.append(tokens)
                            self.doc_metadata.append(
                                {
                                    "question": question_text,
                                    "answer": answer,
                                    "level": level_name,
                                    "story_title": story.get("title", ""),
                                    "id": question.get("id", ""),
                                }
                            )

        # Calculate document statistics
        self.N = len(self.documents)
        self.avgdl = (
            sum(len(doc) for doc in self.documents) / self.N if self.N > 0 else 0
        )

        # Build term-document frequency matrix
        self.doc_freqs = []  # df[term] = number of documents containing term
        self.term_docs = {}  # term -> set of document indices

        for i, doc in enumerate(self.documents):
            doc_terms = set(doc)
            for term in doc_terms:
                if term not in self.term_docs:
                    self.term_docs[term] = set()
                self.term_docs[term].add(i)

        self.idf = {}
        for term, docs in self.term_docs.items():
            self.idf[term] = math.log(
                (self.N - len(docs) + 0.5) / (len(docs) + 0.5) + 1
            )

    def _score(self, query_tokens: List[str], doc_idx: int) -> float:
        """Calculate BM25 score for a query against a document."""
        doc = self.documents[doc_idx]
        doc_len = len(doc)

        score = 0.0
        term_freq = Counter(doc)

        for term in query_tokens:
            if term in self.idf:
                tf = term_freq.get(term, 0)
                # BM25 term frequency component
                tf_component = (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
                )
                score += self.idf[term] * tf_component

        return score

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for questions matching the query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching questions with scores
        """
        query_tokens = self._tokenize(query)
        query_tokens = [t for t in query_tokens if t in self.idf]

        if not query_tokens:
            # Fallback: simple keyword matching
            return self._keyword_search(query, limit)

        # Calculate scores for all documents
        scores = []
        for i in range(self.N):
            score = self._score(query_tokens, i)
            if score > 0:
                scores.append((i, score))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top results
        results = []
        for idx, score in scores[:limit]:
            meta = self.doc_metadata[idx]
            results.append(
                {
                    "question": meta["question"],
                    "answer": meta["answer"],
                    "level": meta["level"],
                    "story_title": meta["story_title"],
                    "score": score,
                }
            )

        return results

    def _keyword_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Fallback keyword search using simple matching."""
        query_tokens = set(self._tokenize(query))

        results = []
        for i, doc in enumerate(self.documents):
            overlap = len(query_tokens & set(doc))
            if overlap > 0:
                meta = self.doc_metadata[i]
                results.append(
                    {
                        "question": meta["question"],
                        "answer": meta["answer"],
                        "level": meta["level"],
                        "story_title": meta["story_title"],
                        "score": overlap,
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


def main():
    import sys

    engine = BM25SearchEngine()

    print()
    print("=" * 60)
    print("Reading Plus BM25 Search")
    print("=" * 60)
    print(f"Indexed {len(engine.documents)} questions")
    print()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        results = engine.search(query)

        print(f"\nSearching for: '{query}'")
        print()

        if not results:
            print("No matching questions found.")
        else:
            print(f"Found {len(results)} result(s):\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. [Level {result['level']}] {result['question'][:70]}")
                print(f"   Story: {result['story_title'][:50]}")
                print(f"   Answer: {result['answer'][:60]}")
                print(f"   Score: {result['score']:.4f}\n")
    else:
        print("Type your question or 'quit' to exit\n")

        while True:
            try:
                query = input("Search: ").strip()

                if query.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break

                if not query:
                    continue

                results = engine.search(query)

                if not results:
                    print("No matching questions found.\n")
                    continue

                print(f"\nFound {len(results)} result(s):\n")
                for i, result in enumerate(results, 1):
                    print(f"{i}. [Level {result['level']}] {result['question'][:70]}")
                    print(f"   Story: {result['story_title'][:50]}")
                    print(f"   Answer: {result['answer'][:60]}")
                    print(f"   Score: {result['score']:.4f}\n")
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break


if __name__ == "__main__":
    main()
