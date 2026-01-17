#!/usr/bin/env python3
"""
Reading Plus Auto-Answer with Mistral AI
Captures questions from browser and answers them using Mistral API.
Designed for token efficiency (1M tokens/month limit).

Usage:
    python3 src/rp_auto_answer.py --api-key YOUR_KEY

The script monitors Reading Plus for new questions and auto-submits answers.
"""

import json
import sys
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

# Import the answer bot
from rp_answer_bot import MistralAnswerBot, AnswerResult, Question

# Browser CDP URL (from your running Chrome)
CDP_URL = "http://127.0.0.1:9222"

READING_PLUS_BASE = "https://student.readingplus.com"


def extract_question_from_page() -> str:
    """
    JavaScript to extract current question from Reading Plus page.
    This script is injected via chrome-devtools evaluate_script.
    """
    return """
    () => {
        // Find question data from the page
        const questionData = {};
        
        // Try to find question ID
        const questionEl = document.querySelector('[data-question-id], .question-container, #question-area');
        if (questionEl) {
            questionData.questionId = questionEl.dataset.questionId || 
                                       questionEl.id?.replace('question-', '');
        }
        
        // Look for question text
        const questionTextEl = document.querySelector('.question-text, .question-title, [class*="question"]');
        if (questionTextEl) {
            questionData.text = questionTextEl.innerText?.trim() || '';
        }
        
        // Find choices
        const choices = [];
        document.querySelectorAll('.choice-item, .choice, [class*="choice"], input[type="radio"]').forEach((el, i) => {
            const text = el.innerText?.trim() || el.textContent?.trim() || 
                        el.querySelector('label')?.innerText?.trim() || '';
            if (text && !choices.includes(text)) {
                choices.push(text);
            }
        });
        questionData.choices = choices.slice(0, 4);  // Max 4 choices
        
        // Find excerpt/passage text
        const excerptEl = document.querySelector('.excerpt, .passage, .reading-text, [class*="excerpt"], [class*="passage"]');
        if (excerptEl) {
            questionData.excerpt = excerptEl.innerText?.trim() || '';
        } else {
            // Fallback: get all text from passage area
            const passageArea = document.querySelector('#passage-area, .passage-area');
            if (passageArea) {
                questionData.excerpt = passageArea.innerText?.trim() || '';
            }
        }
        
        // Get story info
        const storyTitleEl = document.querySelector('.story-title, .title, [class*="story"]');
        if (storyTitleEl) {
            questionData.storyTitle = storyTitleEl.innerText?.trim();
        }
        
        // Get current URL for story ID
        questionData.url = window.location.href;
        
        return JSON.stringify(questionData);
    }
    """


def parse_question_from_json(json_str: str) -> Optional[Question]:
    """Parse the extracted question data into a Question object."""
    try:
        data = json.loads(json_str)

        # Skip if no meaningful data
        if not data.get("text") and not data.get("choices"):
            return None

        # Extract question ID from URL or data
        question_id = 0
        if data.get("questionId"):
            question_id = int(data["questionId"])
        else:
            # Try to extract from URL
            import re

            match = re.search(r"question[_-]?(\\d+)", data.get("url", ""))
            if match:
                question_id = int(match.group(1))

        story_id = 0
        if "storyId" in data:
            story_id = int(data["storyId"])
        else:
            # Extract from URL
            import re

            match = re.search(r"story[_-]?(\\d+)", data.get("url", ""))
            if match:
                story_id = int(match.group(1))

        return Question(
            question_id=question_id,
            story_id=story_id,
            story_title=data.get("storyTitle", "Unknown"),
            excerpt=data.get("excerpt", "") + "\\n\\n" + data.get("text", ""),
            choices=data.get("choices", []),
            index=0,  # Unknown from page
            question_progress=[],  # Unknown from page
        )

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"[ERROR] Failed to parse question: {e}")
        return None


class ReadingPlusAutoAnswer:
    """
    Automated answer system for Reading Plus.
    Integrates with chrome-devtools MCP for browser control.
    """

    def __init__(self, api_key: str, cdp_url: str = CDP_URL):
        self.api_key = api_key
        self.cdp_url = cdp_url
        self.answer_bot = MistralAnswerBot(api_key)
        self.last_question_id = None
        self.last_poll_time = 0
        self.poll_interval = 2  # seconds

    def get_current_question(self) -> Optional[Question]:
        """Get current question from browser via CDP."""
        # This would use: chrome-devtools_evaluate_script
        # For demonstration, returns None - actual implementation via MCP tools

        # To use with chrome-devtools MCP:
        # 1. Call chrome-devtools_evaluate_script with extract_question_from_page()
        # 2. Parse the JSON result
        # 3. Return Question object

        print("[INFO] Use chrome-devtools_evaluate_script to get question")
        print("  Script: extract_question_from_page()")
        return None

    def submit_answer_api(
        self, question_id: int, choice_index: int, session_cookie: str, school_code: str
    ) -> bool:
        """
        Submit answer via Reading Plus API.
        Uses the same API you observed in network requests.
        """
        url = f"{READING_PLUS_BASE}/seereader/api/sr/saveQuestion.json"

        payload = {
            "questionId": question_id,
            "clue": False,
            "excerpts": 0,
            "reread": False,
            "secondsTaken": 10,  # Default, can be more accurate
            "choiceList": [choice_index],
        }

        headers = {
            "Authorization": f"Bearer {session_cookie}",  # Actually uses cookie
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": READING_PLUS_BASE,
            "Referer": f"{READING_PLUS_BASE}/seereader/api/sr/start",
        }

        # Use session cookie directly
        cookies = {"SESSION": session_cookie, "school_code_4": school_code}

        try:
            import requests

            response = requests.post(
                url, json=payload, headers=headers, cookies=cookies, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            return data.get("status", {}).get("ok", False)

        except Exception as e:
            print(f"[ERROR] Failed to submit answer: {e}")
            return False

    def auto_answer_loop(self, session_cookie: str, school_code: str):
        """
        Main loop: monitor for questions and answer them.
        Run this while Reading Plus is open in the browser.
        """
        print("\\n" + "=" * 60)
        print("READING PLUS AUTO-ANSWER")
        print("=" * 60)
        print("\\nMonitoring for questions...")
        print("Press Ctrl+C to stop\\n")

        while True:
            try:
                # Get current question
                question = self.get_current_question()

                if question and question.question_id != self.last_question_id:
                    print(f"\\n[NEW QUESTION] ID: {question.question_id}")
                    print(f"  Story: {question.story_title[:40]}...")
                    print(f"  Choices: {len(question.choices)}")

                    # Answer the question
                    result = self.answer_bot.answer_question(question)

                    print(f"  -> Answer: {result.choice_index}")

                    # In real implementation, submit via API:
                    # self.submit_answer_api(question.question_id, result.choice_index,
                    #                        session_cookie, school_code)

                    self.last_question_id = question.question_id

                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                print("\\n\\n[INFO] Stopping auto-answer...")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                time.sleep(self.poll_interval * 2)

        # Show token usage
        usage = self.answer_bot.get_token_usage()
        print("\\n" + "=" * 60)
        print("SESSION STATS")
        print("=" * 60)
        for key, value in usage.items():
            print(f"  {key}: {value}")


def extract_cookies_from_browser() -> Dict[str, str]:
    """
    Extract session cookies from browser via CDP.
    This requires the browser to have remote debugging enabled.
    """
    import requests

    try:
        # Get cookies from browser
        response = requests.get(f"{CDP_URL}/json", timeout=5)
        data = response.json()

        # Get cookies from the first page
        if data and len(data) > 0:
            # CDP v1.3+ uses /json/version for cookies
            version_url = f"{CDP_URL}/json/version"
            response = requests.get(version_url, timeout=5)
            version_data = response.json()

            # Try to get cookies via WebSocket
            ws_url = version_data.get("webSocketDebuggerUrl")
            if ws_url:
                # Would need WebSocket connection here
                # For simplicity, return empty - user must provide cookies
                return {}

        return {}

    except Exception as e:
        print(f"[WARN] Could not extract cookies: {e}")
        return {}


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Reading Plus Auto-Answer with Mistral AI"
    )
    parser.add_argument("--api-key", "-k", help="Mistral API key")
    parser.add_argument("--session", "-s", help="Reading Plus session cookie")
    parser.add_argument("--school", help="School code (e.g., rpsirhenry)")
    parser.add_argument(
        "--cdp-url", default=CDP_URL, help=f"Chrome CDP URL (default: {CDP_URL})"
    )
    parser.add_argument("--test", action="store_true", help="Test API connection only")

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("[ERROR] API key required: --api-key or MISTRAL_API_KEY env var")
        sys.exit(1)

    if args.test:
        from rp_answer_bot import test_api_connection

        test_api_connection(api_key)
        sys.exit(0)

    # Initialize auto-answer
    auto_answer = ReadingPlusAutoAnswer(api_key, args.cdp_url)

    # Get session info
    session_cookie = args.session or os.environ.get("RP_SESSION_COOKIE")
    school_code = args.school or os.environ.get("RP_SCHOOL_CODE", "rpsirhenry")

    if not session_cookie:
        print(
            "[WARN] No session cookie provided. Will not submit answers automatically."
        )
        print("  Use --session or set RP_SESSION_COOKIE env var")
        print("  Answers will be calculated but not submitted.\\n")

    # Start auto-answer loop
    auto_answer.auto_answer_loop(session_cookie, school_code)


if __name__ == "__main__":
    import os

    main()
