#!/usr/bin/env python3
"""
Reading Plus Question Search System

Loads pre-computed embeddings for INSTANT search.
Works without needing book title or story name.
"""

import json
import re
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple


class QuestionSearchEngine:
    def __init__(self, data_file="data/processed/reading_plus_data.json"):
        with open(data_file) as f:
            self.data = json.load(f)

        self.embeddings_file = "data/embeddings/embeddings_db.npz"
        self.question_index = self._build_question_index()

        if Path(self.embeddings_file).exists():
            self._load_embeddings()
        else:
            print("No embeddings found!")
            print("Run: python3 src/simple_embeddings.py")
            self.embeddings = None
            self.ids = []
            self.embedding_dim = 0
            self.model_name = None

    def _load_embeddings(self):
        print(f"Loading embeddings from {self.embeddings_file}...")
        data = np.load(self.embeddings_file, allow_pickle=True)

        self.embeddings = data["embeddings"]
        self.ids = data["ids"]
        self.embedding_dim = int(data["embedding_dim"].item())
        self.model_name = str(data["model_name"].item())
        self.vocabulary = {k: int(v) for k, v in data["vocabulary"].item().items()}
        self.idf = {k: float(v) for k, v in data["idf"].item().items()}

        # Create reverse vocabulary lookup
        self.vocab_list = [None] * len(self.vocabulary)
        for word, idx in self.vocabulary.items():
            if idx < len(self.vocab_list):
                self.vocab_list[idx] = word

        print(
            f"Loaded {len(self.ids)} {self.model_name} embeddings ({self.embedding_dim}D)"
        )

    def _build_question_index(self):
        index = {}
        for level_name, level_data in self.data.get("levels", {}).items():
            for story in level_data.get("stories", []):
                for question in story.get("questions", []):
                    q_id = question["id"]
                    index[q_id] = {
                        "question": question["question_text"],
                        "answer": question["answer"],
                        "level": level_name,
                        "story_title": story["title"],
                        "keywords": question.get("keywords", []),
                    }
        return index

    def extract_keywords(self, query: str) -> List[str]:
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
        }

        words = re.findall(r"\b\w+\b", query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        seen = set()
        unique = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        return unique

    def search_by_embeddings(
        self, query: str, limit: int = 10
    ) -> List[Tuple[Dict, float]]:
        if self.embeddings is None:
            print("No embeddings loaded!")
            return []

        query_keywords = self.extract_keywords(query)

        query_embedding = np.zeros(self.embedding_dim, dtype=np.float32)
        for word in query_keywords:
            if word in self.vocabulary:
                vocab_idx = self.vocabulary[word] % self.embedding_dim
                query_embedding[vocab_idx] = self.idf.get(word, 1.0)

        query_norm = np.linalg.norm(query_embedding)

        if query_norm == 0:
            return []

        results = []
        for i, embedding in enumerate(self.embeddings):
            similarity = np.dot(query_embedding, embedding) / query_norm
            results.append((i, similarity))

        results.sort(key=lambda x: x[1], reverse=True)

        top_results = []
        for idx, score in results[:limit]:
            q_id = self.ids[idx]
            q_data = self.question_index[q_id]
            top_results.append((q_data, score))

        return top_results

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        results = self.search_by_embeddings(query, limit=limit)

        formatted_results = []
        for q_data, score in results:
            formatted_results.append(
                {
                    "question": q_data["question"],
                    "answer": q_data["answer"],
                    "level": q_data["level"],
                    "story_title": q_data["story_title"],
                    "score": score,
                }
            )

        return formatted_results


def main():
    import sys

    engine = QuestionSearchEngine()

    if engine.embeddings is None or len(engine.embeddings) == 0:
        print("\nError: Embeddings not loaded.")
        print("Run: python3 src/simple_embeddings.py")
        sys.exit(1)

    print()
    print("=" * 60)
    print(f"Reading Plus Question Search ({engine.model_name})")
    print("=" * 60)
    print(f"Loaded {len(engine.question_index)} questions")
    print(f"Loaded {len(engine.ids)} embeddings ({engine.embedding_dim}D)")
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
