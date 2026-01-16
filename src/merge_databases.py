#!/usr/bin/env python3
"""Merge all Reading Plus data sources into a comprehensive database."""

import json
from pathlib import Path


def load_existing_data():
    """Load existing database from answerkeyfinder."""
    with open("data/processed/reading_plus_data.json") as f:
        return json.load(f)


def load_archive_data():
    """Load archived data from quizzma."""
    try:
        with open("data/quizzma_archived.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"questions": []}


def merge_databases():
    """Merge all data sources into one comprehensive database."""

    print("Loading data sources...")

    # Load existing database
    existing = load_existing_data()
    print(f"Existing database: {len(existing.get('levels', {}))} levels")

    # Count questions in existing
    existing_count = 0
    for level_data in existing.get("levels", {}).values():
        for story in level_data.get("stories", []):
            existing_count += len(story.get("questions", []))
    print(f"Existing questions: {existing_count}")

    # Load archive data
    archive = load_archive_data()
    archive_qa = archive.get("questions", [])
    archive_count = len(
        [
            q
            for q in archive_qa
            if len(q.get("question", "")) > 10 and "?" in q.get("question", "")
        ]
    )
    print(f"Archive Q&A pairs: {len(archive_qa)}")

    # Create merged structure
    merged = {
        "source": "combined (answerkeyfinder + quizzma archive)",
        "total_questions": existing_count,
        "levels": existing.get("levels", {}),
        "metadata": {
            "answerkeyfinder": f"{existing_count} questions",
            "quizzma_archive": f"{len(archive_qa)} Q&A pairs (partial)",
            "notes": "Greta Thunberg/climate strike questions not found in available public databases",
        },
    }

    # Check for duplicate stories and add new content
    archive_stories_added = 0

    for qa in archive_qa:
        # Skip login forms and garbage
        q = qa.get("question", "")
        if not q or "sign in" in q.lower() or "password" in q.lower():
            continue
        if "?" not in q:
            continue
        if len(q) < 20:
            continue

        level = qa.get("level", "Unknown")
        story_title = qa.get("story", "Unknown Story")

        # Check if story exists in existing data
        if level in merged["levels"]:
            story_exists = False
            for story in merged["levels"][level].get("stories", []):
                if story.get("title", "").lower() == story_title.lower():
                    story_exists = True
                    # Add question if not duplicate
                    existing_questions = [
                        sq.get("question_text", "") for sq in story.get("questions", [])
                    ]
                    if q not in existing_questions:
                        story["questions"].append(
                            {
                                "id": f"archive-{len(story.get('questions', []))}",
                                "question_text": q,
                                "answer": qa.get("answer", ""),
                                "keywords": [],
                            }
                        )
                        archive_stories_added += 1
                    break

            # Add new story if doesn't exist
            if not story_exists:
                merged["levels"][level]["stories"].append(
                    {
                        "title": story_title,
                        "questions": [
                            {
                                "id": f"archive-{len(merged['levels'][level].get('stories', []))}",
                                "question_text": q,
                                "answer": qa.get("answer", ""),
                                "keywords": [],
                            }
                        ],
                    }
                )
                archive_stories_added += 1

    # Update count
    new_count = 0
    for level_data in merged["levels"].values():
        for story in level_data.get("stories", []):
            new_count += len(story.get("questions", []))

    merged["total_questions"] = new_count

    print(f"\nMerged database:")
    print(f"  Total questions: {new_count}")
    print(f"  New from archive: {archive_stories_added}")

    return merged


def save_merged(merged):
    """Save merged database."""
    output_file = "data/merged_reading_plus.json"

    with open(output_file, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"\nSaved to {output_file}")

    # Also save as the main processed file
    with open("data/processed/reading_plus_data.json", "w") as f:
        json.dump(merged, f, indent=2)

    print(f"Updated data/processed/reading_plus_data.json")


def main():
    print("=" * 60)
    print("Merging Reading Plus Databases")
    print("=" * 60)
    print()

    merged = merge_databases()
    save_merged(merged)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total levels: {len(merged['levels'])}")
    print(f"Total questions: {merged['total_questions']}")
    print("\nData sources:")
    for key, val in merged.get("metadata", {}).items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
