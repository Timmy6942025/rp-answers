#!/usr/bin/env python3
"""
Comprehensive scraper for Reading Plus answers from quizzma.com.
Extracts Q&A pairs from HTML pages (works even with login overlays).
"""

import json
import re
import time
from pathlib import Path
from bs4 import BeautifulSoup
import requests

# Level URLs for quizzma.com
LEVEL_URLS = {
    "A": "https://quizzma.com/reading-plus-answers-level-a/",
    "B": "https://quizzma.com/reading-plus-answers-level-b/",
    "C": "https://quizzma.com/reading-plus-answers-level-c/",
    "D": "https://quizzma.com/reading-plus-level-d-answers/",
    "E": "https://quizzma.com/reading-plus-answers-level-e/",
    "F": "https://quizzma.com/reading-plus-answers-level-f/",
    "G": "https://quizzma.com/reading-plus-answers-level-g/",
    "H": "https://quizzma.com/reading-plus-answers-level-h/",
    "I": "https://quizzma.com/reading-plus-level-i-answers/",
    "J": "https://quizzma.com/reading-plus-answers-level-j/",
    "K": "https://quizzma.com/reading-plus-answers-level-k/",
    "L": "https://quizzma.com/reading-plus-level-l-answers/",
    "M": "https://quizzma.com/reading-plus-answers-level-m/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_page(url: str) -> str:
    """Fetch a page and return HTML content."""
    print(f"Fetching: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""


def extract_qa_from_html(html: str, level: str) -> list:
    """Extract Q&A pairs from HTML content."""
    qa_pairs = []

    if not html:
        return qa_pairs

    soup = BeautifulSoup(html, "html.parser")

    # Remove login forms and other non-content elements
    for elem in soup.find_all(["script", "style", "nav", "header", "footer", "form"]):
        elem.decompose()

    # Get page text
    text = soup.get_text()

    # Split by story titles (they're usually headings)
    # Story titles are often followed by "QuestionAnswer" pattern

    # Find all "QuestionAnswer" patterns in the text
    # The content format is: Story Title\n\nQuestionAnswerQ1?A1\nQ2?A2...

    # First, find the main content area
    content = (
        soup.find("div", {"class": "entry-content"})
        or soup.find("main")
        or soup.find("article")
    )

    if content:
        content_html = str(content)
        content_soup = BeautifulSoup(content_html, "html.parser")

        # Get text with line breaks preserved
        lines = []
        for elem in content_soup.find_all(["p", "h1", "h2", "h3", "h4", "br"]):
            if elem.name == "br":
                lines.append("\n")
            else:
                text = elem.get_text().strip()
                if text:
                    lines.append(text)

        full_text = "\n".join(lines)

        # Split by "QuestionAnswer" pattern
        sections = re.split(r"QuestionAnswer", full_text)

        current_story = f"Level {level}"

        for i, section in enumerate(sections):
            if not section.strip():
                continue

            # First section might be introduction, skip it
            if i == 0 and len(section) < 100:
                continue

            # Try to find story title in this section
            section_lines = section.strip().split("\n")

            # Check if first line looks like a story title
            if section_lines:
                potential_title = section_lines[0].strip()
                # Story titles are usually short and don't end with punctuation
                if len(potential_title) < 80 and not potential_title.endswith(
                    ("?", ".", "!")
                ):
                    current_story = potential_title
                    remaining = "\n".join(section_lines[1:])
                else:
                    remaining = section

            # Now extract Q&A from the remaining text
            qa_text = remaining if "remaining" in dir() else section

            # Split by question marks to find questions
            # But we need to be careful not to split on abbreviations

            # Try to find patterns like "Question text?Answer text"
            # Questions end with ? and are followed by answer

            # Use a more robust approach: look for question mark followed by non-newline text
            q_pattern = r"([A-Z][^.!?\n]*\?)"
            q_matches = re.findall(q_pattern, qa_text, re.MULTILINE)

            if q_matches:
                for q in q_matches:
                    q = q.strip()
                    if len(q) < 15:  # Skip too-short "questions"
                        continue

                    # Find where this question starts and ends
                    q_start = qa_text.find(q)
                    if q_start == -1:
                        continue

                    # Find the answer (text after the question mark until next question or end)
                    after_q = qa_text[q_start + len(q) :].strip()

                    # Answer typically doesn't start with lowercase and might be multiple lines
                    # Look for the next question to know where this answer ends
                    next_q_match = re.search(q_pattern, after_q)

                    if next_q_match:
                        answer = after_q[: next_q_match.start()].strip()
                    else:
                        # Last question in section
                        # Take a reasonable amount of text as answer
                        answer = after_q[:500].strip() if after_q else ""

                    # Clean up answer
                    answer = re.sub(r"^[\s:—–-]+", "", answer)
                    answer = answer.split("\n")[0]  # Take first line only

                    if answer and len(answer) > 1:
                        qa_pairs.append(
                            {
                                "question": q,
                                "answer": answer,
                                "story": current_story,
                                "level": level,
                            }
                        )

    # Alternative: If above didn't work, try regex on full text
    if not qa_pairs:
        # Try to find all "Question?Answer" patterns
        text = soup.get_text()

        # Remove extra whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Look for patterns where question mark is followed by answer
        # Questions typically start with capital letter

        # Split by double newlines first (might separate stories)
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            if "QuestionAnswer" in para:
                parts = para.split("QuestionAnswer")
                for part in parts[1:]:  # Skip first (usually intro)
                    if not part.strip():
                        continue

                    # Try to find question and answer
                    lines = part.strip().split("\n")
                    if lines:
                        # First line might be story title or start of Q&A
                        if len(lines) == 1:
                            # Might be "Q?A" format
                            qa_match = re.match(r"([^?]+\?)(.+)", lines[0])
                            if qa_match:
                                qa_pairs.append(
                                    {
                                        "question": qa_match.group(1).strip(),
                                        "answer": qa_match.group(2).strip()[:200],
                                        "story": current_story,
                                        "level": level,
                                    }
                                )
                        else:
                            # Multiple lines - might be Q on one line, A on next
                            # Find questions (lines ending with ?)
                            q_indices = [
                                i
                                for i, l in enumerate(lines)
                                if l.strip().endswith("?")
                            ]

                            for idx, q_idx in enumerate(q_indices):
                                q_line = lines[q_idx].strip()
                                if len(q_line) < 15:
                                    continue

                                # Answer is on next line(s)
                                if q_idx + 1 < len(lines):
                                    answer_lines = []
                                    for a_idx in range(q_idx + 1, len(lines)):
                                        a_line = lines[a_idx].strip()
                                        # Stop if we hit another question or empty line
                                        if a_line.endswith("?") or not a_line:
                                            break
                                        if a_line:
                                            answer_lines.append(a_line)

                                    answer = " ".join(answer_lines[:3])  # Max 3 lines
                                    if answer and len(answer) > 1:
                                        qa_pairs.append(
                                            {
                                                "question": q_line,
                                                "answer": answer[:200],
                                                "story": current_story,
                                                "level": level,
                                            }
                                        )

    return qa_pairs


def scrape_all_levels() -> dict:
    """Scrape all levels and return combined data."""
    all_qa = []
    levels_scraped = 0

    for level, url in LEVEL_URLS.items():
        print(f"\n{'=' * 60}")
        print(f"Scraping Level {level}")
        print(f"{'=' * 60}")

        html = fetch_page(url)

        if html:
            qa_pairs = extract_qa_from_html(html, level)
            print(f"Found {len(qa_pairs)} Q&A pairs for Level {level}")

            for qa in qa_pairs[:3]:  # Show first 3 as samples
                print(f"  Q: {qa['question'][:60]}...")
                print(f"  A: {qa['answer'][:40]}...")

            all_qa.extend(qa_pairs)
            levels_scraped += 1
        else:
            print(f"Failed to fetch Level {level}")

        # Rate limiting
        time.sleep(1)

    return {
        "source": "quizzma.com",
        "levels_scraped": levels_scraped,
        "total_questions": len(all_qa),
        "questions": all_qa,
    }


def main():
    print("Scraping Reading Plus answers from quizzma.com...")
    print("This may take a few minutes.\n")

    data = scrape_all_levels()

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Levels scraped: {data['levels_scraped']}")
    print(f"Total Q&A pairs: {data['total_questions']}")

    # Save to file
    output_file = "data/quizzma_all_levels.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved to {output_file}")

    # Show some statistics
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
