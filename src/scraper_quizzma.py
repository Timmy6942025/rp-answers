#!/usr/bin/env python3
"""Parse Reading Plus Q&A from quizzma.com HTML content."""

import json
import re
from pathlib import Path

HTML_CACHE = {
    "level_i": """She Sells Sea Shells

QuestionAnswerWhat is the main idea of this selection?A young woman follows her passion while making important scientific discoveries.What does the word "dissenters" mean in this excerpt?People who questioned the accepted views of the timeWhat destructive force in nature was responsible for Lyme Regis being…erosionWhat effect did Mary's near-death experience from lightning strike have on her?She expanded her interests and intellectual pursuits.""",
    "level_j": """A Century of Slavery and Strikes

QuestionAnswerWhat is the main idea?to chronicle the protestsThe First Amendment to the U.S. Constitutionthe right to bear armsRead this excerpt: Why did the…News of the bloody…What was the outcome…They did not change

The Future Of News

QuestionAnswerWhich sentence from the selection captures the central idea?The evolution of news reporting in the face of changing technology and changing reading habits raises a number of questions.Compared with newspapers, news outlets like CNNare able to continually update the newsIn this excerpt, the "great engine" of newsgathering isnews reporters.

Campus Confrontation

QuestionAnswerThe central idea of this selection is that the violent outcome of what began as a peaceful anti-war protestIncreased tensions on U.S college campuses and raised important questions about the right to protest.Kent State geology teacher, Glenn Frank is best described as?Peace Keeper

Stand Against Bullying

QuestionAnswerThis selection is mainly aboutImpact of cyberbullyingBullying is an intentional, repetitiveChoose victims with lessBased on this text, which two of the following• Modern technology means• Bullies can remain invisible""",
}


def extract_qa_pairs(html_content, story_title, level):
    """Extract question-answer pairs from HTML content."""
    qa_pairs = []

    sections = re.split(r"\n{2,}", html_content)
    current_story = story_title

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n")
        potential_story = lines[0].strip()
        if len(potential_story) < 100 and not potential_story.startswith("Question"):
            current_story = potential_story
            section = "\n".join(lines[1:])

        if "QuestionAnswer" in section:
            parts = section.split("QuestionAnswer")

            for part in parts[1:]:
                if not part.strip():
                    continue

                q_text = part.strip()
                q_lines = q_text.split("\n")

                if len(q_lines) >= 2:
                    full_text = " ".join(q_lines)
                    qa_pattern = r"([A-Z][^.!?]*[?])"
                    questions = re.split(qa_pattern, full_text)

                    i = 0
                    while i < len(questions) - 1:
                        if "?" in questions[i]:
                            q = questions[i].strip()
                            q = re.sub(r"^\d+\.\s*", "", q)
                            q = q.strip()
                            if q and len(q) > 5:
                                if i + 1 < len(questions):
                                    answer = questions[i + 1].strip()
                                    answer = re.sub(r"^[A-Z]\.\s*", "", answer)
                                    answer = answer.strip()
                                    if answer and len(answer) > 1:
                                        qa_pairs.append(
                                            {
                                                "question": q,
                                                "answer": answer,
                                                "story": current_story,
                                                "level": level,
                                            }
                                        )
                        i += 2
                else:
                    q_text = q_text.strip()
                    if len(q_text) > 10:
                        qa_pairs.append(
                            {
                                "question": q_text[:500],
                                "answer": "",
                                "story": current_story,
                                "level": level,
                            }
                        )

    return qa_pairs


def parse_all_content():
    """Parse all cached HTML content."""
    all_qa = []

    for level_key, html in HTML_CACHE.items():
        level = level_key.replace("level_", "").upper()
        qa = extract_qa_pairs(html, f"Level {level}", level)
        all_qa.extend(qa)

    return all_qa


def main():
    print("Parsing Reading Plus Q&A from cached HTML...")

    qa_pairs = parse_all_content()
    print(f"Extracted {len(qa_pairs)} Q&A pairs")

    output = {
        "source": "quizzma.com",
        "total_questions": len(qa_pairs),
        "questions": qa_pairs,
    }

    with open("data/quizzma_qa.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved to data/quizzma_qa.json")


if __name__ == "__main__":
    main()
