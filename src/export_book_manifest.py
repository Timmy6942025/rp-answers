#!/usr/bin/env python3
"""
Export book manifest from Reading Plus questions database.

Extracts unique story titles with question counts, filtering out noise.
"""

import json
from collections import defaultdict

NOISE_PATTERNS = [
    "quizzma",
    "unknown",
    "other reading plus",
    "conclusion",
    "answer:",
    "question:",
    "primarily",
    "mostly about",
]

LEVEL_PATTERN = r"^level [a-z]$"


def load_json(filepath):
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_noise_title(title):
    """Check if title should be filtered out."""
    if not title:
        return True

    title_lower = title.lower().strip()

    for pattern in NOISE_PATTERNS:
        if pattern in title_lower:
            return True

    if title_lower.startswith("level ") and len(title_lower) <= 8:
        if title_lower[6:7].isalpha():
            return True

    if len(title_lower.split()) <= 2:
        return True

    if any(char in '?!' for char in title_lower):
        return True

    return False


def export_book_manifest(input_path, output_path):
    """Generate book manifest from questions database."""
    data = load_json(input_path)

    story_counts = defaultdict(lambda: {"count": 0, "level": None})
    questions = data.get("questions", [])

    for q in questions:
        story = q.get("story", "").strip()
        level = q.get("level", "").strip()

        if not story or is_noise_title(story):
            continue

        story_counts[story]["count"] += 1
        if story_counts[story]["level"] is None:
            story_counts[story]["level"] = level

    manifest = []
    for title, info in sorted(story_counts.items()):
        manifest.append({
            "title": title,
            "count": info["count"],
            "level": info["level"]
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest


if __name__ == "__main__":
    INPUT_PATH = "data/ULTRACOMPLETE_V4_reading_plus.json"
    OUTPUT_PATH = "data/book_manifest.json"

    manifest = export_book_manifest(INPUT_PATH, OUTPUT_PATH)

    print(f"Exported {len(manifest)} stories to {OUTPUT_PATH}")
    for item in manifest[:10]:
        print(f"  {item['level']}: {item['title']} ({item['count']} questions)")
    if len(manifest) > 10:
        print(f"  ... and {len(manifest) - 10} more")
