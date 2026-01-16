#!/usr/bin/env python3
"""Generate TF-IDF embeddings for Reading Plus questions."""

import json
import re
import numpy as np
from pathlib import Path
import math


def main():
    print("=" * 60)
    print("Reading Plus TF-IDF Embeddings Generator")
    print("=" * 60)
    print()

    data_file = "data/ULTRACOMPLETE_V4_reading_plus.json"
    output_file = "data/embeddings/embeddings_db.npz"

    print(f"Loading data from {data_file}...")

    with open(data_file) as f:
        data = json.load(f)

    all_questions = []
    question_to_id = {}

    # Handle flat questions structure (ULTRACOMPLETE_V4)
    if "questions" in data:
        for question in data["questions"]:
            # Check for different question text keys (question_text vs question)
            question_text = question.get("question_text", question.get("question", ""))
            q_id = question.get("id", "")

            if question_text:
                all_questions.append(question_text)
                question_to_id[question_text] = q_id
    # Handle nested levels→stories→questions structure
    elif "levels" in data:
        for level_name, level_data in data.get("levels", {}).items():
            for story in level_data.get("stories", []):
                for question in story.get("questions", []):
                    question_text = question.get("question_text", question.get("question", ""))
                    q_id = question.get("id", "")

                    if question_text:
                        all_questions.append(question_text)
                        question_to_id[question_text] = q_id

    print(f"Total questions: {len(all_questions)}")

    vocabulary = {}
    document_freq = {}

    for question in all_questions:
        words = re.findall(r"\b\w+\b", question.lower())

        for word in words:
            if word not in vocabulary:
                vocabulary[word] = len(vocabulary)
                document_freq[word] = 1
            else:
                document_freq[word] += 1

    print(f"Vocabulary size: {len(vocabulary)} unique words")

    total_docs = len(all_questions)

    idf = {}
    for word in vocabulary:
        idf[word] = math.log(total_docs / (1 + document_freq[word]))

    embedding_dim = 256

    embeddings = np.zeros((len(all_questions), embedding_dim), dtype=np.float32)

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

    print(f"Generating {embedding_dim}D embeddings...")

    for i, question in enumerate(all_questions):
        if i % 200 == 0:
            print(
                f"  Progress: {i}/{len(all_questions)} ({i / len(all_questions) * 100:.1f}%)"
            )

        words = re.findall(r"\b\w+\b", question.lower())

        word_scores = {}
        for word in words:
            if word in vocabulary and word not in stop_words:
                tf = 1.0
                if word not in word_scores:
                    word_scores[word] = tf * idf[word]

        for word, score in word_scores.items():
            vocab_idx = vocabulary[word] % embedding_dim
            embeddings[i, vocab_idx] = score

    print(f"  Progress: {len(all_questions)}/{len(all_questions)} (100.0%)")

    ids = [question_to_id[q] for q in all_questions]

    print(f"Saving embeddings to {output_file}...")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        output_file,
        embeddings=embeddings,
        ids=np.array(ids),
        model_name="TF-IDF",
        embedding_dim=np.array([embedding_dim], dtype=np.int64),
        vocabulary=vocabulary,
        idf=idf,
    )

    file_size = output_path.stat().st_size / 1024 / 1024

    print()
    print("=" * 60)
    print("EMBEDDINGS GENERATED SUCCESSFULLY!")
    print("=" * 60)
    print()
    print(f"Output file: {output_file}")
    print(f"File size: {file_size:.2f} MB")
    print(f"Total embeddings: {len(all_questions)}")
    print(f"Embedding dimension: {embedding_dim}")
    print()
    print("Search usage:")
    print('  python3 src/search.py "your question"')
    print()


if __name__ == "__main__":
    main()
