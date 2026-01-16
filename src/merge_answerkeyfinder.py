#!/usr/bin/env python3
"""Merge answerkeyfinder data into main database."""

import json
from pathlib import Path


def load_answerkeyfinder():
    with open("data/answerkeyfinder_qa.json") as f:
        return json.load(f)


def build_combined_database():
    akf_data = load_answerkeyfinder()

    combined = {
        "source": "combined (answerkeyfinder.com + archive)",
        "total_questions": akf_data["total_questions"],
        "levels": {},
        "metadata": {
            "answerkeyfinder": f"{akf_data['total_questions']} questions",
            "note": "Greta Thunberg climate strike question not found in public databases",
        },
    }

    # Group by level and story
    for qa in akf_data["questions"]:
        level = qa.get("level", "Unknown")
        story = qa.get("story", "Unknown Story")

        if level not in combined["levels"]:
            combined["levels"][level] = {"stories": []}

        # Check if story exists
        story_exists = False
        for s in combined["levels"][level]["stories"]:
            if s.get("title", "").lower() == story.lower():
                story_exists = True
                s["questions"].append(
                    {
                        "id": f"akf-{len(s.get('questions', []))}",
                        "question_text": qa.get("question", ""),
                        "answer": qa.get("answer", ""),
                        "keywords": [],
                    }
                )
                break

        if not story_exists:
            combined["levels"][level]["stories"].append(
                {
                    "title": story,
                    "questions": [
                        {
                            "id": "akf-0",
                            "question_text": qa.get("question", ""),
                            "answer": qa.get("answer", ""),
                            "keywords": [],
                        }
                    ],
                }
            )

    # Count total questions
    total = 0
    for level_data in combined["levels"].values():
        for story in level_data.get("stories", []):
            total += len(story.get("questions", []))

    combined["total_questions"] = total

    return combined


def main():
    print("Building combined database from answerkeyfinder...")

    combined = build_combined_database()

    print(f"\nTotal levels: {len(combined['levels'])}")
    print(f"Total questions: {combined['total_questions']}")

    # Show breakdown
    for level in sorted(combined["levels"].keys()):
        level_data = combined["levels"][level]
        stories = len(level_data.get("stories", []))
        questions = sum(
            len(s.get("questions", [])) for s in level_data.get("stories", [])
        )
        print(f"  Level {level}: {stories} stories, {questions} questions")

    # Save
    with open("data/processed/reading_plus_data.json", "w") as f:
        json.dump(combined, f, indent=2)

    print(f"\nSaved to data/processed/reading_plus_data.json")

    # Also save as merged
    with open("data/merged_reading_plus.json", "w") as f:
        json.dump(combined, f, indent=2)

    print("Updated data/merged_reading_plus.json")


if __name__ == "__main__":
    main()
