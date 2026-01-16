#!/usr/bin/env python3
"""
Comprehensive merge script for Reading Plus answers.
Merges data from ALL sources and deduplicates completely.
"""

import json
import re
from pathlib import Path
from collections import defaultdict


def load_json(filepath):
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_question(text):
    """Normalize question text for deduplication."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text


def is_valid_question(q_data):
    """Check if a question entry is valid (not garbage)."""
    q = q_data.get('question', '') or q_data.get('question_text', '')
    a = q_data.get('answer', '') or q_data.get('answer', '')
    
    # Skip if too short
    if len(q) < 10:
        return False
    
    # Skip if answer is empty or too short
    if not a or len(a) < 2:
        return False
    
    # Skip obvious garbage patterns
    garbage_patterns = [
        'sign in', 'forgot password', 'your email', 'create new password',
        'was this helpful', 'please enter', 'lost your password',
        'dont have account', 'report content', 'copyright infringement',
        'mobile menu', 'home quiz answers', 'reading plus answers level',
        'people also viewed', 'let us know', 'your name', 'your email',
    ]
    
    q_lower = q.lower()
    for pattern in garbage_patterns:
        if pattern in q_lower:
            return False
    
    # Question should end with ? (most real questions do)
    # But allow for some edge cases
    if not q.endswith('?') and len(q) > 30:
        pass  # Some questions might be truncated, that's okay
    
    return True


def extract_questions_from_source(data, source_name):
    """Extract all valid questions from a data source."""
    questions = []
    
    # Handle list format (quizzma style)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                questions.append(item)
        return questions
    
    # Handle dict with 'questions' key (flat format)
    if isinstance(data, dict):
        if 'questions' in data:
            q_list = data['questions']
            for q in q_list:
                if isinstance(q, dict):
                    questions.append({
                        'question': q.get('question', q.get('question_text', '')),
                        'answer': q.get('answer', ''),
                        'level': q.get('level', 'Unknown'),
                        'story': q.get('story', q.get('story_title', '')),
                        'source': source_name
                    })
        
        # Handle 'levels' format (merged_reading_plus style)
        if 'levels' in data:
            for level_key, level_data in data['levels'].items():
                if isinstance(level_data, dict):
                    # Extract level name
                    level_name = level_data.get('level_name', level_data.get('level', level_key))
                    
                    # Check if stories are nested
                    stories = level_data.get('stories', [])
                    if isinstance(stories, list):
                        for story in stories:
                            if isinstance(story, dict):
                                story_title = story.get('title', story.get('story', 'Unknown Story'))
                                story_questions = story.get('questions', [])
                                if isinstance(story_questions, list):
                                    for q in story_questions:
                                        if isinstance(q, dict):
                                            questions.append({
                                                'question': q.get('question_text', q.get('question', '')),
                                                'answer': q.get('answer', ''),
                                                'level': level_name,
                                                'story': story_title,
                                                'source': source_name
                                            })
    
    return questions


def merge_all_data():
    """Merge data from all sources and deduplicate."""
    
    all_questions = []
    sources = [
        ('data/merged_reading_plus.json', 'merged (answerkeyfinder + archive)'),
        ('data/answerkeyfinder_qa.json', 'answerkeyfinder.com'),
        ('data/quizzma_archived.json', 'quizzma.com (archive)'),
        ('data/quizzma_all_levels.json', 'quizzma.com'),
        ('data/quizzma_qa.json', 'quizzma.com (qa)'),
    ]
    
    print("=" * 70)
    print("COMPREHENSIVE READING PLUS ANSWER DATABASE MERGE")
    print("=" * 70)
    
    for filepath, source_name in sources:
        path = Path(filepath)
        if not path.exists():
            print(f"\n[SKIP] {filepath} - not found")
            continue
        
        try:
            data = load_json(filepath)
            questions = extract_questions_from_source(data, source_name)
            valid_questions = [q for q in questions if is_valid_question(q)]
            
            print(f"\n[LOADED] {filepath}")
            print(f"  Source: {source_name}")
            print(f"  Total entries: {len(questions)}")
            print(f"  Valid questions: {len(valid_questions)}")
            
            all_questions.extend(valid_questions)
            
        except Exception as e:
            print(f"\n[ERROR] {filepath}: {e}")
    
    print(f"\n{'=' * 70}")
    print(f"TOTAL VALID QUESTIONS FROM ALL SOURCES: {len(all_questions)}")
    print(f"{'=' * 70}")
    
    # Deduplicate by normalized question text
    seen = set()
    unique_questions = []
    duplicates = 0
    
    for q in all_questions:
        q_text = q.get('question', '') or q.get('question_text', '')
        norm_q = normalize_question(q_text)
        
        if norm_q and norm_q not in seen:
            seen.add(norm_q)
            unique_questions.append(q)
        elif norm_q:
            duplicates += 1
    
    print(f"\n[DEDUPLICATION]")
    print(f"  Original valid: {len(all_questions)}")
    print(f"  Duplicates removed: {duplicates}")
    print(f"  Unique questions: {len(unique_questions)}")
    
    # Organize by level
    by_level = defaultdict(list)
    for q in unique_questions:
        level = q.get('level', 'Unknown')
        if not level or level == 'Unknown':
            # Try to extract from question text
            q_text = q.get('question', '')
            # Level might be embedded in story name or elsewhere
            level = 'Unknown'
        
        # Clean up the question and answer
        clean_q = {
            'question': q.get('question', q.get('question_text', '')).strip(),
            'answer': q.get('answer', '').strip(),
            'level': str(level).upper(),
            'story': q.get('story', q.get('story_title', '')).strip(),
            'source': q.get('source', 'unknown')
        }
        
        # Skip if question or answer is still too short
        if len(clean_q['question']) < 10 or len(clean_q['answer']) < 2:
            continue
            
        by_level[clean_q['level']].append(clean_q)
    
    # Count by level
    print(f"\n[QUESTIONS BY LEVEL]")
    for level in sorted(by_level.keys()):
        count = len(by_level[level])
        print(f"  Level {level}: {count} questions")
    
    # Create final database structure
    final_db = {
        'version': '2.0.0',
        'generated_at': str(Path(__file__).stat().st_mtime) if Path(__file__).exists() else 'N/A',
        'source': 'comprehensive merge (multiple sources)',
        'total_questions': len(unique_questions),
        'total_levels': len(by_level),
        'levels': {}
    }
    
    # Sort levels alphabetically and assign sequential IDs
    all_levels = sorted(by_level.keys())
    for level in all_levels:
        questions = by_level[level]
        # Sort questions by story, then by question
        questions.sort(key=lambda x: (x.get('story', ''), x.get('question', '')))
        
        # Group by story
        stories = defaultdict(list)
        for q in questions:
            story = q.get('story', 'Unknown Story')
            stories[story].append(q)
        
        final_db['levels'][level] = {
            'level_name': level,
            'total_stories': len(stories),
            'total_questions': len(questions),
            'stories': []
        }
        
        for story_name, story_questions in sorted(stories.items()):
            # Assign IDs to questions
            q_list = []
            for i, q in enumerate(story_questions):
                q_copy = q.copy()
                q_copy['id'] = f"{level.lower()}-{story_name[:20].replace(' ', '-')}-{i:03d}"
                q_list.append(q_copy)
            
            final_db['levels'][level]['stories'].append({
                'title': story_name,
                'question_count': len(q_list),
                'questions': q_list
            })
    
    # Save comprehensive database
    output_file = 'data/comprehensive_reading_plus_database.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_db, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 70}")
    print(f"[COMPLETE] Comprehensive database saved to: {output_file}")
    print(f"  Total questions: {final_db['total_questions']}")
    print(f"  Total levels: {final_db['total_levels']}")
    print(f"{'=' * 70}")
    
    # Also save flat list for easy searching
    flat_list = []
    for level, level_data in final_db['levels'].items():
        for story in level_data.get('stories', []):
            for q in story.get('questions', []):
                flat_list.append({
                    'question': q['question'],
                    'answer': q['answer'],
                    'level': level,
                    'story': story['title'],
                    'id': q['id'],
                    'source': q.get('source', 'unknown')
                })
    
    flat_file = 'data/comprehensive_flat_questions.json'
    with open(flat_file, 'w', encoding='utf-8') as f:
        json.dump(flat_list, f, indent=2, ensure_ascii=False)
    
    print(f"\n[FLAT LIST] Also saved to: {flat_file}")
    print(f"  Total entries: {len(flat_list)}")
    
    return final_db


if __name__ == '__main__':
    merge_all_data()
