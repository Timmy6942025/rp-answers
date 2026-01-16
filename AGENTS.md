# AGENTS.md - Agent Guidelines for Reading Plus Database

## Project Overview

This is a **Reading Plus question database** project that scrapes, parses, and searches comprehension questions from multiple sources (AnswerKeyFinder.com, Quizzma.com, PDF files). Contains 3,359 unique questions across 14 levels (A-M + HiE).

## Build/Lint/Test Commands

### No Test Infrastructure
This project has **no automated tests**, pytest configuration, or CI/CD. All scripts are standalone executables designed for data processing.

### Running Scripts
```bash
# Main search (interactive or query argument)
python3 src/search.py "your question here"
python3 src/search.py  # Interactive mode

# Data generation/processing
python3 src/simple_embeddings.py              # Generate TF-IDF embeddings
python3 src/parse_pdf_qa.py                  # Extract Q&A from PDFs
python3 src/comprehensive_merge.py            # Merge all data sources

# Web scraping
python3 src/scrape_answerkeyfinder.py        # Scrape AnswerKeyFinder.com
python3 src/scrape_quizzma_all.py            # Scrape Quizzma.com (all levels)
python3 src/scrape_archive.py                # Scrape Wayback Machine archives

# Alternative search engines
python3 src/search_bm25.py                   # BM25 ranking search
python3 src/search_enhanced.py               # Multi-strategy search
```

### Dependencies
```bash
pip install -r requirements.txt
# Requires: beautifulsoup4, requests, sentence-transformers, numpy
```

## Code Style Guidelines

### 1. File Structure
- All scripts in `src/` directory
- Executable scripts with shebang: `#!/usr/bin/env python3`
- Entry point pattern: `if __name__ == "__main__":` at bottom
- Data in `data/` directory (JSON, TXT, NPZ files)

### 2. Imports
```python
# Standard library first
import json
import re
import math
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Tuple

# Third-party after
import numpy as np
from bs4 import BeautifulSoup
import requests
```

**Rules:**
- Group: stdlib → third-party (no local modules to import)
- Order alphabetically within groups
- Use `from typing` for type hints
- Prefer `import numpy as np` for NumPy

### 3. Formatting (No Linter Configured)
No `.flake8`, `.pylintrc`, or `black` config. Observed patterns:

**Indentation:** 4 spaces
**Line length:** ~80-100 chars (not strictly enforced)
**Blank lines:** 2 blank lines before top-level functions/classes, 1 blank line between methods

### 4. Naming Conventions
```python
# Functions: snake_case
def parse_pdf_questions(filepath, level):
def extract_qa_from_html(html, level):
def _tokenize(text: str) -> List[str]:

# Variables: snake_case
all_questions = []
question_to_id = {}
document_freq = {}

# Classes: PascalCase
class QuestionSearchEngine:
class BM25SearchEngine:

# Constants: UPPER_CASE
PDF_FILES = {...}
HEADERS = {...}
LEVEL_URLS = {...}

# Private methods: _prefix
def _load_embeddings(self):
def _build_index(self):
def _score(self, query_tokens, doc_idx):
```

### 5. Type Hints (Partial Usage)
```python
# Used for function signatures (not enforced consistently)
def search(self, query: str, limit: int = 10) -> List[Dict]:
def _tokenize(self, text: str) -> List[str]:
def _score(self, query_tokens: List[str], doc_idx: int) -> float:

# Not used everywhere - inconsistent across codebase
# DO NOT enforce type hints when editing existing code
```

### 6. Docstrings
```python
# Triple double quotes at module/function level
"""Parse Reading Plus Q&A from extracted PDF text files."""

def search(self, query: str, limit: int = 10) -> List[Dict]:
    """
    Search for questions matching the query.

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        List of matching questions with scores
    """
```

**Rules:**
- Module-level docstring at top of file (1-2 lines describing purpose)
- Function docstrings for public methods (Args/Returns sections)
- Simple one-liners for private methods acceptable

### 7. Error Handling
```python
# Try-except for file I/O
try:
    data = load_json(filepath)
except Exception as e:
    print(f"[ERROR] {filepath}: {e}")

# Request handling with timeout
try:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text
except Exception as e:
    print(f"Error fetching {url}: {e}")
    return ""

# User input handling
try:
    query = input("Search: ").strip()
except (EOFError, KeyboardInterrupt):
    print("\nGoodbye!")
    break

# Check paths exist before operations
if not path.exists():
    print(f"✗ Level {level}: File not found")
    continue
```

**Rules:**
- Use try-except for I/O operations (files, network)
- Print informative error messages with `print(f"...")`
- Use `Path().exists()` checks before file operations
- Don't suppress exceptions silently unless expected

### 8. String/Regex Patterns
```python
# String operations
text = text.lower().strip()
text = re.sub(r'\s+', ' ', text)

# Word tokenization
words = re.findall(r"\b\w+\b", query.lower())

# HTML cleaning
for elem in soup.find_all(["script", "style", "nav", "header", "footer", "form"]):
    elem.decompose()

# Stop words as sets (for O(1) lookup)
stop_words = {"what", "is", "the", "a", "an", ...}
```

### 9. Data Structures
```python
# JSON schema
{
    "version": "4.0.0",
    "generated": "2026-01-16",
    "total_unique": 3359,
    "levels": {
        "A": {
            "level_name": "A",
            "stories": [
                {
                    "title": "Story Title",
                    "questions": [
                        {
                            "id": "unique-id",
                            "question_text": "Question text",
                            "answer": "Answer text",
                            "keywords": ["word1", "word2"]
                        }
                    ]
                }
            ]
        }
    }
}

# Flat question format
{
    "question": "Question text",
    "answer": "Answer text",
    "level": "A",
    "story": "Story Title",
    "source": "AnswerKeyFinder.com"
}
```

### 10. Print/Logging
```python
# Section headers
print("=" * 60)
print("READING PLUS TF-IDF EMBEDDINGS GENERATOR")
print("=" * 60)

# Progress updates
if i % 200 == 0:
    print(f"  Progress: {i}/{len(all_questions)} ({i / len(all_questions) * 100:.1f}%)")

# Results formatting
print(f"  Total questions: {len(all_questions)}")
print(f"  File size: {file_size:.2f} MB")

# Error/warning markers
print(f"✗ Level {level}: File not found")
print(f"[ERROR] {filepath}: {e}")
print(f"[LOADED] {filepath}")
```

**Rules:**
- Use `=` characters for section headers
- Use `[PREFIX]` markers for status messages (LOADED, ERROR, COMPLETE)
- Format numbers with `.2f` for precision where appropriate
- No logging module - use print() for all output

### 11. Git Conventions
```bash
# Commit messages (from git log)
feat: Add 2041 Reading Plus questions from answerkeyfinder.com
feat: Comprehensive Reading Plus database - 2,090 questions
docs: Update README with 3,359 question database
feat: Add 9 PDF answer files - 1,635 new questions
```

**Rules:**
- Format: `type: description`
- Types: `feat` (new feature), `docs` (documentation), `fix` (bug fix)
- Imperative mood ("Add" not "Added")
- No trailing period

## Special Notes

### Data Processing Patterns
- **Deduplication:** Use normalized text + sets for O(1) lookup
- **Stop words:** Hardcoded sets in functions (stop_words)
- **Embeddings:** TF-IDF with 256 dimensions, NumPy for storage (NPZ format)
- **Search strategies:** Keyword, TF-IDF, BM25 (can combine)

### Web Scraping
- Use `requests` with User-Agent headers
- Rate limiting with `time.sleep(1)`
- BeautifulSoup for HTML parsing
- Remove script/style/nav/header/footer elements

### File Paths
- Use `pathlib.Path` for path operations
- Hardcoded absolute paths in some files (acceptable, no config system)
- Data files in `data/` directory
- Output to `data/` or `data/embeddings/`

### Important: No Tests
When adding features:
1. Manually test with sample data
2. Verify JSON structure matches schema
3. Check for edge cases (empty files, missing fields)
4. No need to write unit tests (no test infrastructure exists)

### Codebase Maturity
**Disciplined but minimal:**
- Consistent patterns across files
- No linter/formatter configured
- Practical, production-focused code
- Prioritize functionality over strict style enforcement
