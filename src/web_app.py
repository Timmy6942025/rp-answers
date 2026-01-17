#!/usr/bin/env python3
"""Reading Plus Q&A Search - Local Web Application.

A Streamlit web app for fuzzy searching Reading Plus story titles
and displaying all associated questions and answers.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
from rapidfuzz import fuzz, process


# Data path configuration
DATA_PATH = Path(__file__).parent.parent / "data" / "ULTRACOMPLETE_V4_reading_plus.json"


@st.cache_data
def load_and_group_questions() -> Tuple[Dict[str, List[Dict]], List[str]]:
    """
    Load questions from JSON file and group by story title.

    Returns:
        Tuple of (questions_dict, story_list) where:
        - questions_dict: Dictionary mapping story title to list of question dicts
        - story_list: List of unique story titles
    """
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])

    # Group questions by story
    questions_dict: Dict[str, List[Dict]] = {}
    for q in questions:
        story = q.get("story", "")
        if story not in questions_dict:
            questions_dict[story] = []
        questions_dict[story].append(q)

    # Get unique story titles sorted alphabetically
    story_list = sorted(questions_dict.keys())

    return questions_dict, story_list


@st.cache_data
def get_levels() -> List[str]:
    """
    Get all unique Reading Plus levels from the data.

    Returns:
        List of level codes sorted alphabetically (excluding HiE, placed at end)
    """
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    levels = set(q.get("level", "") for q in questions if q.get("level"))

    # Sort levels, but put HiE at the end
    sorted_levels = sorted([l for l in levels if l != "HiE"])
    if "HiE" in levels:
        sorted_levels.append("HiE")

    return sorted_levels


@st.cache_data
def get_stories_by_level(
    questions_dict: Dict[str, List[Dict]], level: str
) -> List[str]:
    """
    Get all story titles that have questions for the given level.

    Args:
        questions_dict: Dictionary mapping story title to list of question dicts
        level: Reading Plus level code (e.g., "A", "B", "HiE")

    Returns:
        List of story titles that have at least one question for the level
    """
    stories = []
    for story, questions in questions_dict.items():
        for q in questions:
            if q.get("level") == level:
                stories.append(story)
                break
    return sorted(stories)


def search_stories(
    query: str, story_list: List[str], limit: int = 5, score_cutoff: float = 60.0
) -> List[Tuple[str, float, int]]:
    """
    Fuzzy search for story titles matching the query.

    Args:
        query: Search query string
        story_list: List of story titles to search
        limit: Maximum number of results to return
        score_cutoff: Minimum similarity score (0-100) to include result

    Returns:
        List of tuples: (story_title, similarity_score, original_index)
    """
    if not query or not story_list:
        return []

    # Create lowercase version of story list for case-insensitive matching
    story_list_lower = [s.lower() for s in story_list]
    query_lower = query.lower()

    # Use RapidFuzz process.extract for fuzzy matching
    results = process.extract(
        query_lower, story_list_lower, scorer=fuzz.WRatio, limit=limit
    )

    # Filter by score cutoff and map back to original story titles
    filtered_results = []
    for match, score, idx in results:
        if score >= score_cutoff:
            filtered_results.append((story_list[idx], score, idx))

    return filtered_results


def main():
    """Main Streamlit application."""
    # Page configuration
    st.set_page_config(
        page_title="Reading Plus Q&A Search",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # App title and description
    st.title("📚 Reading Plus Q&A Search")
    st.markdown("""
    Search for a story title and view all associated questions and answers.
    Use fuzzy search - you can type partial names or with typos!
    """)

    # Initialize session state
    if "selected_story" not in st.session_state:
        st.session_state.selected_story = None
    if "auto_expand" not in st.session_state:
        st.session_state.auto_expand = False
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""
    if "selected_level" not in st.session_state:
        st.session_state.selected_level = None

    # Load data
    questions_dict, story_list = load_and_group_questions()

    # Get available levels
    levels = get_levels()

    # Sidebar for level selection
    st.sidebar.header("📖 Browse by Level")
    st.sidebar.markdown("Select your Reading Plus level to see available stories:")

    # Level selector
    selected_level = st.sidebar.selectbox(
        "Choose Level",
        options=["All Levels"] + levels,
        index=0,
        key="level_selector",
    )

    if selected_level == "All Levels":
        st.session_state.selected_level = None
    else:
        st.session_state.selected_level = selected_level

    # Get stories for selected level
    level_stories = []
    if st.session_state.selected_level:
        level_stories = get_stories_by_level(
            questions_dict, st.session_state.selected_level
        )

    # Auto-expand checkbox
    auto_expand = st.checkbox(
        "Auto-expand best match",
        value=st.session_state.auto_expand,
        key="auto_expand_toggle",
    )
    st.session_state.auto_expand = auto_expand

    # Search input
    query = st.text_input(
        "Search for story...",
        placeholder="e.g., Breaking Barriers, Conclusion",
        key="search_input",
    )

    # Perform search
    if query and query != st.session_state.last_query:
        st.session_state.search_results = search_stories(query, story_list)
        st.session_state.last_query = query

        # Auto-expand if enabled and we have results
        if auto_expand and st.session_state.search_results:
            st.session_state.selected_story = st.session_state.search_results[0][0]

    # Display search results
    if st.session_state.search_results:
        st.subheader("Matching Stories")
        for story, score, idx in st.session_state.search_results:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{story}**")
            with col2:
                st.markdown(f"*Score: {score:.1f}%*")

            if st.button("Show Questions", key=f"btn_{idx}"):
                st.session_state.selected_story = story
                st.rerun()
    elif query and not st.session_state.search_results:
        st.info("No matching stories found. Try a different search term.")

    # Display stories by level (when level selected and no search)
    if (
        st.session_state.selected_level
        and not query
        and not st.session_state.search_results
    ):
        st.divider()
        st.subheader(f"📚 Stories for Level {st.session_state.selected_level}")
        st.markdown(f"**{len(level_stories)} stories available**")

        for story in level_stories:
            question_count = len(questions_dict.get(story, []))
            with st.expander(f"📖 {story} ({question_count} questions)"):
                if st.button(
                    f"View All Q&A",
                    key=f"level_btn_{story.replace(' ', '_').replace(',', '')}",
                ):
                    st.session_state.selected_story = story
                    st.rerun()

    # Display Q&A for selected story
    if st.session_state.selected_story:
        story = st.session_state.selected_story
        st.divider()
        story_level = None
        for q in questions_dict.get(story, []):
            story_level = q.get("level")
            break

        level_info = f" (Level {story_level})" if story_level else ""
        st.subheader(f"Q&A for: {story}{level_info}")

        if st.button("← Back to search"):
            st.session_state.selected_story = None
            st.rerun()

        questions = questions_dict.get(story, [])
        for i, q in enumerate(questions, 1):
            st.write(f"**Q{i}:** {q.get('question', '')}")
            st.info(f"**A:** {q.get('answer', '')}")
    else:
        # Show all stories when no search or selection
        if not query and not st.session_state.selected_level:
            st.info(
                f"Showing all {len(story_list)} stories. Use the search box above or select a level from the sidebar."
            )


if __name__ == "__main__":
    main()
