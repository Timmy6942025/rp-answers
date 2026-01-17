"""Tests for the web_app data loader functions."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_stories():
    """Sample story titles matching real data."""
    return [
        "Conclusion",
        "Breaking Barriers, Breaking Records",
        "Checkmate",
        "Because on a moral basis it is the right thing to do",
        "Fortune and MisfortuneConclusion",
    ]


@pytest.fixture
def sample_questions_data():
    """Sample data structure matching ULTRACOMPLETE_V4_reading_plus.json."""
    return {
        "version": "4.1.0",
        "generated": "2026-01-17",
        "sources": ["Test Source"],
        "total_unique": 3,
        "questions": [
            {
                "question": "What is the main conflict?",
                "answer": "A brave hero",
                "level": "A",
                "story": "Conclusion",
                "id": "a-Conclusion-000",
                "source": "test",
            },
            {
                "question": "What happens at the end?",
                "answer": "Victory",
                "level": "A",
                "story": "Conclusion",
                "id": "a-Conclusion-001",
                "source": "test",
            },
            {
                "question": "Who is the antagonist?",
                "answer": "Dark lord",
                "level": "B",
                "story": "Breaking Barriers, Breaking Records",
                "id": "b-Barriers-000",
                "source": "test",
            },
        ],
    }


class TestLoadAndGroupQuestions:
    """Test suite for load_and_group_questions function."""

    def test_loads_json_successfully(self, sample_questions_data, tmp_path):
        """Test that function can load JSON data from file."""
        # Create a temporary JSON file with sample data
        json_file = tmp_path / "test_data.json"
        import json

        json_file.write_text(json.dumps(sample_questions_data))

        # Import and call the function
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import load_and_group_questions

        # Mock the data path to use our temp file
        import unittest.mock

        with unittest.mock.patch("src.web_app.DATA_PATH", str(json_file)):
            questions_dict, story_list = load_and_group_questions()

        # Verify we got data back
        assert questions_dict is not None
        assert story_list is not None

    def test_groups_questions_by_story(self, sample_questions_data, tmp_path):
        """Test that questions are correctly grouped by story field."""
        json_file = tmp_path / "test_data.json"
        import json

        json_file.write_text(json.dumps(sample_questions_data))

        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import load_and_group_questions

        import unittest.mock

        with unittest.mock.patch("src.web_app.DATA_PATH", str(json_file)):
            questions_dict, story_list = load_and_group_questions()

        # Verify grouping
        assert "Conclusion" in questions_dict
        assert "Breaking Barriers, Breaking Records" in questions_dict
        assert len(questions_dict["Conclusion"]) == 2  # 2 questions about Conclusion
        assert len(questions_dict["Breaking Barriers, Breaking Records"]) == 1

    def test_returns_correct_number_of_unique_stories(
        self, sample_questions_data, tmp_path
    ):
        """Test that function returns correct count of unique stories."""
        json_file = tmp_path / "test_data.json"
        import json

        json_file.write_text(json.dumps(sample_questions_data))

        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import load_and_group_questions

        import unittest.mock

        with unittest.mock.patch("src.web_app.DATA_PATH", str(json_file)):
            questions_dict, story_list = load_and_group_questions()

        # Verify 2 unique stories
        assert len(story_list) == 2
        assert len(questions_dict) == 2

    def test_returns_list_of_story_titles(self, sample_questions_data, tmp_path):
        """Test that story_list is a list of story titles."""
        json_file = tmp_path / "test_data.json"
        import json

        json_file.write_text(json.dumps(sample_questions_data))

        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import load_and_group_questions

        import unittest.mock

        with unittest.mock.patch("src.web_app.DATA_PATH", str(json_file)):
            questions_dict, story_list = load_and_group_questions()

        # Verify it's a list of strings
        assert isinstance(story_list, list)
        assert all(isinstance(s, str) for s in story_list)
        assert "Conclusion" in story_list
        assert "Breaking Barriers, Breaking Records" in story_list

    def test_questions_have_required_fields(self, sample_questions_data, tmp_path):
        """Test that loaded questions have question, answer, story fields."""
        json_file = tmp_path / "test_data.json"
        import json

        json_file.write_text(json.dumps(sample_questions_data))

        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import load_and_group_questions

        import unittest.mock

        with unittest.mock.patch("src.web_app.DATA_PATH", str(json_file)):
            questions_dict, story_list = load_and_group_questions()

        # Check first question in first story has required fields
        first_story = story_list[0]
        first_question = questions_dict[first_story][0]
        assert "question" in first_question
        assert "answer" in first_question
        assert "story" in first_question


class TestSearchStories:
    """Test suite for search_stories fuzzy search function."""

    def test_finds_story_with_typo(self, sample_stories):
        """Test that fuzzy search finds story with typo."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import search_stories

        results = search_stories("breaking bariers", sample_stories, limit=3)

        # Should find at least one result
        assert len(results) > 0
        # First result should be "Breaking Barriers, Breaking Records" with good score
        assert results[0][0] == "Breaking Barriers, Breaking Records"
        assert results[0][1] >= 70  # Good fuzzy match

    def test_empty_query_returns_empty_list(self, sample_stories):
        """Test that empty query returns empty list."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import search_stories

        results = search_stories("", sample_stories)
        assert results == []

        results = search_stories(None, sample_stories)
        assert results == []

    def test_no_matches_returns_empty_list(self, sample_stories):
        """Test that nonexistent story returns empty list."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import search_stories

        results = search_stories("xyz nonexistent story xyz", sample_stories)
        assert results == []

    def test_case_insensitive_search(self, sample_stories):
        """Test that search is case-insensitive."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import search_stories

        # Uppercase query should find lowercase story
        results = search_stories("CONCLUSION", sample_stories, limit=3)

        assert len(results) > 0
        assert "Conclusion" in [r[0] for r in results]

    def test_returns_limited_results(self, sample_stories):
        """Test that results are limited to specified number."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import search_stories

        results = search_stories("the", sample_stories, limit=2)

        assert len(results) <= 2

    def test_results_are_tuples_with_three_elements(self, sample_stories):
        """Test that results are tuples with story, score, index."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import search_stories

        results = search_stories("breaking", sample_stories)

        if results:
            result = results[0]
            assert isinstance(result, tuple)
            assert len(result) == 3
            assert isinstance(result[0], str)  # story
            assert isinstance(result[1], float)  # score
            assert isinstance(result[2], int)  # index

    def test_high_score_for_exact_match(self, sample_stories):
        """Test that exact match gets high score."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.web_app import search_stories

        results = search_stories("Conclusion", sample_stories)

        # Exact match should have score close to 100
        exact_match = [r for r in results if r[0] == "Conclusion"]
        assert len(exact_match) > 0
        assert exact_match[0][1] >= 90
