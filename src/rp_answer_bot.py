#!/usr/bin/env python3
"""
Reading Plus AI Answer Bot
Uses Mistral API to answer Reading Plus questions from the browser.
Integrates with chrome-devtools MCP for real-time Q&A capture and submission.
"""

import json
import os
import sys
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

import requests

# API Configuration
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = "mistral-small-2506"  # User's model

# Token limits (1M tokens/month)
MAX_TOKENS_PER_QUESTION = 100  # Keep responses short
SYSTEM_PROMPT_TOKENS = 200  # Minimal system prompt


@dataclass
class Question:
    """Represents a Reading Plus question."""

    question_id: int
    story_id: int
    story_title: str
    excerpt: str  # The reading passage shown
    choices: List[str]  # Answer options
    index: int  # Question number in sequence
    question_progress: List[Dict]  # Previous answers


@dataclass
class AnswerResult:
    """Result from answering a question."""

    choice_index: int
    confidence: float
    reasoning: str


class MistralAnswerBot:
    """
    Token-efficient Reading Plus answer bot using Mistral API.

    Design principles:
    - Minimal system prompt (stored in file to avoid repetition)
    - Concise question formatting
    - Fast response (mistral-small is optimized for speed)
    - Caching to avoid re-answering
    """

    SYSTEM_PROMPT = """You are a reading comprehension expert. Answer multiple-choice questions based ONLY on the provided excerpt.

INSTRUCTIONS:
1. Read the excerpt carefully
2. Analyze the question
3. Select the BEST answer from the lettered choices
4. Output ONLY the letter of your answer

RULES:
- Base your answer ONLY on the excerpt provided
- If uncertain, make your best inference
- Choose the most complete and accurate answer
- Do not overthink - answer efficiently

OUTPUT FORMAT:
Return ONLY a single letter with no explanation:
A
OR
B
OR
C
etc.
"""

    def __init__(self, api_key: str, cache_dir: str = "~/.cache/rp-answers"):
        self.api_key = api_key
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.question_cache = {}  # Cache to avoid re-answering

    def _format_question(self, question: Question) -> str:
        """Format question efficiently for the model."""
        # Truncate excerpt if too long (keep first 500 chars for context)
        excerpt = (
            question.excerpt[:500] if len(question.excerpt) > 500 else question.excerpt
        )

        formatted = f"""EXCERPT:
{excerpt}

QUESTION:
Choose the best answer:

"""
        for i, choice in enumerate(question.choices):
            letter = chr(ord("A") + i)
            formatted += f"{letter}. {choice}\n"

        return formatted

    def _parse_letter_response(self, content: str, num_choices: int) -> int:
        """Parse letter response, return -1 if can't parse."""
        content = content.strip().upper()

        # Extract first letter A-Z
        for char in content:
            if "A" <= char <= "Z":
                answer = ord(char) - ord("A")
                # Cap at last choice
                if answer >= num_choices:
                    answer = num_choices - 1
                return answer

        # Try to extract number as fallback
        for char in content:
            if char.isdigit():
                answer = int(char)
                if answer >= num_choices:
                    answer = num_choices - 1
                return answer

        return -1  # Could not parse

    def _call_mistral(self, prompt: str) -> AnswerResult:
        """Call Mistral API and parse response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 10,  # Very limited - just need answer letter
            "temperature": 0.1,  # Low temperature for consistency
        }

        try:
            response = requests.post(
                MISTRAL_API_URL, headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            num_choices = len(self._get_choices_from_prompt(prompt))
            if num_choices == 0:
                return AnswerResult(
                    choice_index=0, confidence=0.0, reasoning="No choices found"
                )

            answer = self._parse_letter_response(content, num_choices)

            if answer == -1:
                # Could not parse, default to first choice
                return AnswerResult(
                    choice_index=0,
                    confidence=0.1,
                    reasoning=f"Unparseable: {content[:20]}",
                )

            return AnswerResult(
                choice_index=answer,
                confidence=0.8,
                reasoning="",
            )

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] API call failed: {e}", file=sys.stderr)
            return AnswerResult(
                choice_index=0, confidence=0.0, reasoning=f"API error: {e}"
            )
        except (KeyError, IndexError) as e:
            return AnswerResult(
                choice_index=0, confidence=0.0, reasoning=f"Parse error: {e}"
            )

        formatted = f"""EXCERPT:
{excerpt}

QUESTION:
Choose the best answer:

"""
        for i, choice in enumerate(question.choices):
            letter = chr(ord("A") + i)
            formatted += f"{letter}. {choice}\n"

        return formatted

    def _call_mistral(self, prompt: str) -> AnswerResult:
        """Call Mistral API and parse response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 50,  # Very limited - just need answer number
            "temperature": 0.1,  # Low temperature for consistency
        }

        try:
            response = requests.post(
                MISTRAL_API_URL, headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Parse letter response (A, B, C, D, etc.)
            content = content.strip().upper()

            # Extract first letter A-Z
            answer = None
            for char in content:
                if "A" <= char <= "Z":
                    answer = ord(char) - ord("A")
                    break

            if answer is None:
                # Try to extract number as fallback
                for char in content:
                    if char.isdigit():
                        answer = int(char)
                        break
                else:
                    answer = 0  # Default to first choice

            # Validate against number of choices
            num_choices = len(self._get_choices_from_prompt(prompt))
            if answer >= num_choices:
                answer = num_choices - 1  # Cap at last choice

            # Calculate confidence based on response length and clarity
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            return AnswerResult(
                choice_index=answer % len(self._get_choices_from_prompt(prompt)),
                confidence=0.8,  # Default confidence
                reasoning="",
            )

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] API call failed: {e}", file=sys.stderr)
            return AnswerResult(
                choice_index=0, confidence=0.0, reasoning=f"API error: {e}"
            )

    def _get_choices_from_prompt(self, prompt: str) -> List[str]:
        """Extract choices from prompt (supports A., B., C., etc. and 1., 2., etc.)"""
        lines = prompt.split("\n")
        choices = []
        for line in lines:
            # Match A., B., C., or 1., 2., 3., etc.
            if (
                line.startswith(("A.", "B.", "C.", "D.", "E.", "F.", "G.", "H."))
                or line[0:2].isdigit()
                and line[2] == "."
            ):
                # Extract choice text after the letter/number and period
                if line[0].isdigit():
                    # Numbered: "1. text"
                    choice = line.split(".", 1)[1].strip()
                else:
                    # Lettered: "A. text"
                    choice = line[3:].strip()
                choices.append(choice)
        return choices

    def answer_question(self, question: Question) -> AnswerResult:
        """Answer a single question. Never raises - always returns a result."""
        # Check cache first
        cache_key = f"{question.story_id}_{question.question_id}"
        if cache_key in self.question_cache:
            print(f"[CACHE] Using cached answer for Q{question.index}")
            return self.question_cache[cache_key]

        # Check we have choices
        if not question.choices:
            return AnswerResult(
                choice_index=0, confidence=0.0, reasoning="No choices provided"
            )

        # Format and send to API
        prompt = self._format_question(question)
        print(f"[INFO] Answering Q{question.index}: {question.story_title[:30]}...")

        result = self._call_mistral(prompt)

        # Cache the result
        self.question_cache[cache_key] = result
        print(
            f"[RESULT] Choice: {result.choice_index} (confidence: {result.confidence})"
        )

        return result

    def get_token_usage(self) -> Dict[str, int]:
        """Estimate token usage for budgeting."""
        # Rough estimates based on typical usage
        system_prompt_tokens = 200
        question_tokens = 300  # Average per question
        answer_tokens = 20  # Average response

        total_questions = len(self.question_cache)

        return {
            "system_prompt": system_prompt_tokens,
            "questions_answered": total_questions,
            "estimated_input_tokens": system_prompt_tokens
            + (total_questions * question_tokens),
            "estimated_output_tokens": total_questions * answer_tokens,
            "estimated_total_tokens": system_prompt_tokens
            + (total_questions * (question_tokens + answer_tokens)),
            "questions_remaining": max(
                0, 10000 - total_questions
            ),  # ~1M tokens / 100 tokens per Q
        }


class BrowserController:
    """Controls Reading Plus browser via chrome-devtools MCP."""

    def __init__(self):
        self.base_url = "https://student.readingplus.com"

    def get_current_question(self) -> Optional[Question]:
        """Extract current question from browser via CDP evaluate script."""
        # This would use chrome-devtools MCP's evaluate_script
        # For now, returns None - actual implementation via MCP tools

        # The actual implementation uses browser.evaluate_script with:
        # document.querySelector to find question elements
        # Extract questionId, choices, excerpt from DOM

        # Expected DOM structure:
        # - [data-question-id] or similar attribute
        # - .choice-list with .choice-item elements
        # - .excerpt or .passage for reading text

        # For integration with chrome-devtools MCP, call:
        # chrome-devtools_evaluate_script with JS to extract question

        print(
            "[INFO] Use chrome-devtools_evaluate_script to extract question from browser"
        )
        return None

    def submit_answer(
        self, question_id: int, choice_index: int, seconds_taken: int = 10
    ) -> bool:
        """Submit answer via API call (not browser automation)."""
        # This uses the Reading Plus API directly
        # POST /seereader/api/sr/saveQuestion.json

        # The browser automation is for extracting questions
        # Answer submission happens via API to avoid timing issues

        print(f"[INFO] Submit answer: question_id={question_id}, choice={choice_index}")
        return True


def test_api_connection(api_key: str) -> bool:
    """Test Mistral API connection."""
    print(f"[TEST] Testing API connection with model: {MODEL}")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": 'Respond with exactly: {"answer": 0}'}
        ],
        "max_tokens": 20,
    }

    try:
        response = requests.post(
            MISTRAL_API_URL, headers=headers, json=payload, timeout=30
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        print(f"[SUCCESS] API connected!")
        print(f"  Response: {content}")
        print(f"  Tokens used: {usage.get('total_tokens', 'N/A')}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API test failed: {e}")
        return False


def run_interactive_mode(api_key: str):
    """Interactive mode: manually input questions and get answers."""
    print("\n" + "=" * 60)
    print("READING PLUS AI ANSWER BOT - Interactive Mode")
    print("=" * 60)
    print("\nEnter question details (Ctrl+C to exit)\n")

    bot = MistralAnswerBot(api_key)

    while True:
        try:
            excerpt = input("Excerpt: ").strip()
            if not excerpt:
                break

            question = input("Question: ").strip()

            choices = []
            print("Enter 4 choices (press Enter after each):")
            for i in range(4):
                choice = input(f"  {i}. ").strip()
                choices.append(choice)

            # Create question object
            q = Question(
                question_id=0,
                story_id=0,
                story_title="",
                excerpt=f"{excerpt}\n\n{question}",
                choices=choices,
                index=0,
                question_progress=[],
            )

            result = bot.answer_question(q)
            print(
                f"\n>>> ANSWER: {result.choice_index} ({bot._get_choices_from_prompt(bot._format_question(q))[result.choice_index]})\n"
            )

        except KeyboardInterrupt:
            print("\n\n[INFO] Exiting...")
            break
        except Exception as e:
            print(f"[ERROR] {e}\n")

    # Show usage stats
    usage = bot.get_token_usage()
    print("\n" + "=" * 60)
    print("TOKEN USAGE STATS")
    print("=" * 60)
    for key, value in usage.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Reading Plus AI Answer Bot")
    parser.add_argument("--api-key", "-k", help="Mistral API key")
    parser.add_argument("--test", action="store_true", help="Test API connection")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive mode"
    )
    parser.add_argument(
        "--model", default=MODEL, help=f"Model to use (default: {MODEL})"
    )

    args = parser.parse_args()

    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("MISTRAL_API_KEY")

    if not api_key:
        print("[ERROR] API key required. Use --api-key or set MISTRAL_API_KEY env var")
        print("  Example: python3 src/rp_answer_bot.py --api-key YOUR_KEY --test")
        sys.exit(1)

    if args.test:
        test_api_connection(api_key)
    elif args.interactive:
        run_interactive_mode(api_key)
    else:
        print("[INFO] Use --interactive for manual mode or --test to verify API")
        print("  For browser automation, integrate with chrome-devtools MCP")
