#!/usr/bin/env python3
"""Scrape Reading Plus answers from answerkeyfinder.com."""

import json
import re
import time
from bs4 import BeautifulSoup
import requests

LEVEL_URLS = {
    "A": "https://answerkeyfinder.com/reading-plus-level-a-answers/",
    "B": "https://answerkeyfinder.com/reading-plus-level-b-answers/",
    "C": "https://answerkeyfinder.com/reading-plus-level-c-answers/",
    "D": "https://answerkeyfinder.com/reading-plus-level-d-answers/",
    "E": "https://answerkeyfinder.com/reading-plus-level-e-answers/",
    "F": "https://answerkeyfinder.com/reading-plus-level-f-answers/",
    "G": "https://answerkeyfinder.com/reading-plus-level-g-answers/",
    "H": "https://answerkeyfinder.com/reading-plus-level-h-answers/",
    "I": "https://answerkeyfinder.com/reading-plus-level-i-answers/",
    "J": "https://answerkeyfinder.com/reading-plus-level-j-answers/",
    "K": "https://answerkeyfinder.com/reading-plus-level-k-answers/",
    "L": "https://answerkeyfinder.com/reading-plus-level-l-answers/",
    "M": "https://answerkeyfinder.com/reading-plus-level-m-answers/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def fetch_page(url: str) -> str:
    print(f"Fetching: {url[:70]}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        return ""


def extract_qa_from_html(html: str, level: str) -> list:
    qa_pairs = []
    if not html:
        return qa_pairs

    soup = BeautifulSoup(html, "html.parser")

    for elem in soup.find_all(["script", "style", "nav", "header", "footer", "form"]):
        elem.decompose()

    text = soup.get_text()
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Find story sections
    story_pattern = r"([A-Z][A-Za-z\s&\-\']+)\s*\n\n"
    stories = re.split(story_pattern, text)

    current_story = f"Level {level}"

    i = 0
    while i < len(stories):
        potential_story = stories[i].strip()
        if len(potential_story) < 60 and not potential_story.startswith("Q."):
            if potential_story and not any(
                x in potential_story.lower()
                for x in [
                    "reading plus",
                    "answer",
                    "table of contents",
                    "note:",
                    "if you",
                ]
            ):
                current_story = potential_story
                i += 1

        if i < len(stories):
            content = stories[i]

            # Extract Q&A
            q_pattern = r"Q\.\s*([^\n]+?)\s*\n*Ans:\s*([^\n]+)"
            matches = re.findall(q_pattern, content)

            for q, a in matches:
                q = q.strip()
                a = a.strip()
                if q and a and len(q) > 10:
                    qa_pairs.append(
                        {
                            "question": q,
                            "answer": a,
                            "story": current_story,
                            "level": level,
                        }
                    )

            i += 1

    return qa_pairs


def main():
    print("Scraping answerkeyfinder.com...\n")
    all_qa = []
    levels_scraped = 0

    for level, url in LEVEL_URLS.items():
        print(f"\n{'=' * 60}")
        print(f"Level {level}")
        print(f"{'=' * 60}")

        html = fetch_page(url)

        if html and len(html) > 1000:
            qa_pairs = extract_qa_from_html(html, level)
            print(f"Found {len(qa_pairs)} Q&A pairs")

            for qa in qa_pairs[:3]:
                print(f"  Q: {qa['question'][:50]}...")
                print(f"  A: {qa['answer'][:40]}...")

            all_qa.extend(qa_pairs)
            levels_scraped += 1
        else:
            print("Failed or empty")

        time.sleep(1)

    data = {
        "source": "answerkeyfinder.com",
        "levels_scraped": levels_scraped,
        "total_questions": len(all_qa),
        "questions": all_qa,
    }

    print(f"\n{'=' * 60}")
    print(f"Total: {len(all_qa)} questions from {levels_scraped} levels")

    with open("data/answerkeyfinder_qa.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved to data/answerkeyfinder_qa.json")


if __name__ == "__main__":
    main()
