#!/usr/bin/env python3
"""Enhanced Reading Plus search with question normalization and paraphrase handling.

This module improves search by:
1. Normalizing common question patterns
2. Expanding queries with paraphrases
3. Using both BM25 keyword matching and semantic similarity
"""

import json
import math
import re
from collections import Counter
from typing import List, Dict, Set, Tuple


def normalize_question(question: str) -> str:
    """Normalize a question to its core meaning."""
    q = question.lower().strip()

    prefixes_to_remove = [
        "according to the selection, ",
        "based on what you have read, ",
        "based on this excerpt, ",
        "based on the selection, ",
        "in this excerpt, ",
        "read this excerpt. ",
        "read these two excerpts. ",
        "read this part of this selection. ",
        "you can infer from this that ",
        "from this excerpt you can conclude that ",
        "think about what you read in this selection. ",
        "the previous question asked about ",
        "based on your answer to the previous question, ",
    ]

    for prefix in prefixes_to_remove:
        if q.startswith(prefix):
            q = q[len(prefix) :]

    q = re.sub(
        r"\s*(can best be described as|can be classified as|is mainly about|is mostly about|tells mostly|is primarily about).*$",
        "",
        q,
    )

    return q.strip()


def extract_core_concepts(question: str) -> Set[str]:
    """Extract core concepts from a question."""
    q = question.lower()

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
        "can",
        "could",
        "would",
        "should",
        "may",
        "might",
        "must",
        "will",
        "shall",
        "ought",
        "need",
        "dare",
        "used",
    }

    words = re.findall(r"\b\w+\b", q)
    core = {w for w in words if w not in stop_words and len(w) > 2}

    return core


def expand_with_paraphrases(question: str) -> List[str]:
    """Expand a question with common paraphrases."""
    q = question.lower().strip()
    queries = [q]

    normalized = normalize_question(q)
    if normalized != q:
        queries.append(normalized)

    core = extract_core_concepts(q)
    if core:
        queries.append(" ".join(sorted(core, key=lambda x: -len(x))))

    return queries


class EnhancedBM25Search:
    """Enhanced BM25 search with question normalization and paraphrase handling."""

    def __init__(
        self, data_file="data/processed/reading_plus_data.json", k1=1.5, b=0.75
    ):
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
        text = text.lower()
        words = re.findall(r"\b\w+\b", text)
        return words

    def _build_index(self):
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

        for level_name, level_data in self.data.get("levels", {}).items():
            for story in level_data.get("stories", []):
                for question in story.get("questions", []):
                    question_text = question.get("question_text", "")
                    answer = question.get("answer", "")

                    if question_text:
                        tokens = self._tokenize(question_text)
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
                                    "normalized": normalize_question(question_text),
                                }
                            )

        self.N = len(self.documents)
        self.avgdl = (
            sum(len(doc) for doc in self.documents) / self.N if self.N > 0 else 0
        )

        self.term_docs = {}
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
        doc = self.documents[doc_idx]
        doc_len = len(doc)

        score = 0.0
        term_freq = Counter(doc)

        for term in query_tokens:
            if term in self.idf:
                tf = term_freq.get(term, 0)
                tf_component = (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
                )
                score += self.idf[term] * tf_component

        return score

    def _normalized_score(self, query: str, doc_idx: int) -> float:
        """Score based on normalized question matching."""
        normalized_query = normalize_question(query)
        normalized_doc = self.doc_metadata[doc_idx].get("normalized", "")

        if not normalized_query or not normalized_doc:
            return 0.0

        query_tokens = set(self._tokenize(normalized_query))
        doc_tokens = set(self._tokenize(normalized_doc))

        overlap = len(query_tokens & doc_tokens)
        total = len(query_tokens | doc_tokens)

        if total == 0:
            return 0.0

        return overlap / total * 10

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search with normalization and paraphrase expansion."""
        expanded_queries = expand_with_paraphrases(query)

        all_scores = Counter()

        for expanded_q in expanded_queries:
            query_tokens = self._tokenize(expanded_q)
            query_tokens = [t for t in query_tokens if t in self.idf]

            if not query_tokens:
                continue

            for i in range(self.N):
                bm25_score = self._score(query_tokens, i)
                norm_score = self._normalized_score(query, i)
                all_scores[i] += bm25_score + norm_score

        top_indices = [idx for idx, _ in all_scores.most_common(limit)]

        results = []
        for idx in top_indices:
            meta = self.doc_metadata[idx]
            results.append(
                {
                    "question": meta["question"],
                    "answer": meta["answer"],
                    "level": meta["level"],
                    "story_title": meta["story_title"],
                    "score": all_scores[idx],
                }
            )

        return results


def main():
    import sys

    engine = EnhancedBM25Search()

    print()
    print("=" * 60)
    print("Reading Plus Enhanced Search (BM25 + Normalization)")
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
