#!/usr/bin/env python3
"""Scrape Reading Plus answers from Wayback Machine archived quizzma.com pages."""

import json
import re
import time
from pathlib import Path
from bs4 import BeautifulSoup
import requests

# Wayback Machine archived URLs
ARCHIVE_URLS = {
    "A": "https://web.archive.org/web/20241207092342/https://quizzma.com/reading-plus-answers-level-a/",
    "B": "https://web.archive.org/web/2024/https://quizzma.com/reading-plus-answers-level-b/",
    "C": "https://web.archive.org/web/2024/https://quizzma.com/reading-plus-answers-level-c/",
    "D": "https://web.archive.org/web/202412/https://quizzma.com/reading-plus-level-d-answers/",
    "E": "https://web.archive.org/web/2024/https://quizzma.com/reading-plus-answers-level-e/",
    "F": "https://web.archive.org/web/2024/https://quizzma.com/reading-plus-answers-level-f/",
    "G": "https://web.archive.org/web/2024/https://quizzma.com/reading-plus-answers-level-g/",
    "H": "https://web.archive.org/web/2024/https://quizzma.com/reading-plus-answers-level-h/",
    "I": "https://web.archive.org/web/20241207092342/https://quizzma.com/reading-plus-level-i-answers/",
    "J": "https://web.archive.org/web/2024/https://quizzma.com/reading-plus-answers-level-j/",
    "K": "https://web.archive.org/web/2024/https://quizzma.com/reading-plus-answers-level-k/",
    "L": "https://web.archive.org/web/2024/https://quizzma.com/reading-plus-level-l-answers/",
    "M": "https://web.archive.org/web/2024/https://quizzma.com/reading-plus-answers-level-m/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def fetch_page(url: str) -> str:
    """Fetch a page and return HTML content."""
    print(f"Fetching: {url[:80]}...")

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching: {e}")
        return ""


def extract_qa_from_archived_html(html: str, level: str) -> list:
    """Extract Q&A pairs from archived HTML content."""
    qa_pairs = []

    if not html:
        return qa_pairs

    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements
    for elem in soup.find_all(
        ["script", "style", "nav", "header", "footer", "form", "iframe"]
    ):
        elem.decompose()

    # Get text content
    text = soup.get_text()

    # Split by "QuestionAnswer" pattern
    sections = re.split(r"QuestionAnswer", text)

    current_story = f"Level {level}"

    for i, section in enumerate(sections):
        if not section.strip():
            continue

        # Skip first section (usually intro)
        if i == 0 and len(section) < 200:
            continue

        lines = section.strip().split("\n")

        # Find story title (first substantial line that isn't a question)
        for j, line in enumerate(lines):
            line = line.strip()
            if line and len(line) < 80 and not line.endswith("?"):
                if line and not line.startswith("Q") and not line.startswith("A"):
                    # Check if it looks like a title
                    if any(c.isupper() for c in line[:5]):  # Title case
                        current_story = line
                        lines = lines[j + 1 :]
                        break

        # Process Q&A pairs
        # Look for question mark followed by answer
        full_text = " ".join(lines)

        # Find all questions (ending with ?)
        q_pattern = r"([A-Z][^.!?\n]*\?)"
        questions = re.findall(q_pattern, full_text, re.MULTILINE)

        for q in questions:
            q = q.strip()
            if len(q) < 15:
                continue

            # Find position of this question
            q_pos = full_text.find(q)
            if q_pos == -1:
                continue

            # Find next question to determine answer boundary
            after_q = full_text[q_pos + len(q) :]
            next_q_match = re.search(q_pattern, after_q)

            if next_q_match:
                answer = after_q[: next_q_match.start()].strip()
            else:
                answer = after_q.strip()

            # Clean up answer
            answer = re.sub(r"^[\s:—–-]+", "", answer)
            answer = answer.split("\n")[0]
            answer = answer[:300]  # Limit length

            if answer and len(answer) > 1:
                qa_pairs.append(
                    {
                        "question": q,
                        "answer": answer,
                        "story": current_story,
                        "level": level,
                    }
                )

    return qa_pairs


def scrape_all_from_archive():
    """Scrape all levels from Wayback Machine."""
    all_qa = []
    levels_scraped = 0

    for level, url in ARCHIVE_URLS.items():
        print(f"\n{'=' * 60}")
        print(f"Scraping Level {level} from Archive")
        print(f"{'=' * 60}")

        html = fetch_page(url)

        if html and len(html) > 1000:
            qa_pairs = extract_qa_from_archived_html(html, level)
            print(f"Found {len(qa_pairs)} Q&A pairs for Level {level}")

            # Show first 3 as samples
            for qa in qa_pairs[:3]:
                print(f"  Q: {qa['question'][:60]}...")
                print(f"  A: {qa['answer'][:40]}...")

            all_qa.extend(qa_pairs)
            levels_scraped += 1
        else:
            print(f"Failed to fetch Level {level} (empty or too short)")

        time.sleep(1)  # Rate limiting

    return {
        "source": "quizzma.com (Wayback Machine)",
        "levels_scraped": levels_scraped,
        "total_questions": len(all_qa),
        "questions": all_qa,
    }


def main():
    print("Scraping Reading Plus answers from Wayback Machine...")
    print("This may take a few minutes.\n")

    data = scrape_all_from_archive()

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Levels scraped: {data['levels_scraped']}")
    print(f"Total Q&A pairs: {data['total_questions']}")

    # Save to file
    output_file = "data/quizzma_archived.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved to {output_file}")

    # Show statistics
    if data["questions"]:
        levels_count = {}
        for qa in data["questions"]:
            lvl = qa["level"]
            levels_count[lvl] = levels_count.get(lvl, 0) + 1

        print("\nQuestions per level:")
        for lvl in sorted(levels_count.keys()):
            print(f"  Level {lvl}: {levels_count[lvl]}")


if __name__ == "__main__":
    main()
