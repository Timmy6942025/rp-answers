#!/usr/bin/env python3
"""Parse Reading Plus Q&A from extracted PDF text files."""

import json
import re
from pathlib import Path

PDF_FILES = {
    'F': '/home/timmy/rp-answers/data/level_f_pdf.txt',
    'G': '/home/timmy/rp-answers/data/level_g_pdf.txt',
    'H': '/home/timmy/rp-answers/data/level_h_pdf.txt',
    'HiE': '/home/timmy/rp-answers/data/level_hie_pdf.txt',
    'I': '/home/timmy/rp-answers/data/level_i_pdf.txt',
    'J': '/home/timmy/rp-answers/data/level_j_pdf.txt',
    'K': '/home/timmy/rp-answers/data/level_k_pdf.txt',
    'L': '/home/timmy/rp-answers/data/level_l_pdf.txt',
    'M': '/home/timmy/rp-answers/data/level_m_pdf.txt',
}


def parse_pdf_questions(filepath, level):
    """Extract Q&A pairs from a PDF text file."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    questions = []
    current_story = None
    
    # Split by story markers (often in ALL CAPS or followed by credits)
    # Stories often have format: "Story Title\n[Credit for answers: ...]"
    story_pattern = r'([A-Z][A-Z\s&\-\']{5,80})\s*\n\[Credit'
    stories = re.split(story_pattern, content)
    
    # If no stories found with that pattern, try alternate
    if len(stories) < 2:
        # Try finding story titles as all-caps lines followed by content
        story_pattern2 = r'^([A-Z][A-Z\s&\-\'\,\.]{10,80})\s*$'
        stories = re.split(story_pattern2, content, flags=re.MULTILINE)
    
    i = 0
    while i < len(stories):
        potential_title = stories[i].strip()
        
        # Check if this looks like a story title
        if len(potential_title) > 5 and len(potential_title) < 100 and not potential_title.startswith('['):
            # This is likely a story title
            current_story = potential_title
            story_content = stories[i + 1] if i + 1 < len(stories) else ''
            
            # Extract Q&A from story content
            # Pattern: Number. Question text Answer: Answer text
            qa_pattern = r'(?:\d+)\.\s*([^_\n]+?)\s*Answer[:\.]?\s*([^\n_]{2,300})'
            matches = re.findall(qa_pattern, story_content)
            
            for q, a in matches:
                q = q.strip()
                a = a.strip()
                # Clean up answer (remove bullet points)
                a = re.sub(r'^[\•\-\*]\s*', '', a)
                a = a.split('Answer:')[0] if 'Answer:' in a else a
                
                if len(q) > 10 and len(a) > 1:
                    questions.append({
                        'question': q,
                        'answer': a,
                        'level': level,
                        'story': current_story,
                        'source': f'PDF - Level {level}'
                    })
        
        i += 2 if i + 1 < len(stories) else 1
    
    # Alternate extraction method - find all numbered questions
    # Pattern: 1. Question text Answer: Answer text OR 1. Question text\nAnswer: Answer text
    simple_pattern = r'(?:\d+)\.\s*([^\n]+?)\s*(?:Answer|ANSWER)[:\.\s]+([^\n]{5,300})'
    simple_matches = re.findall(simple_pattern, content, re.IGNORECASE)
    
    for q, a in simple_matches:
        q = q.strip()
        a = a.strip()
        a = re.sub(r'^[\•\-\*]\s*', '', a)
        
        if len(q) > 10 and len(a) > 1 and q not in [x['question'] for x in questions]:
            questions.append({
                'question': q,
                'answer': a,
                'level': level,
                'story': 'Unknown',
                'source': f'PDF - Level {level}'
            })
    
    return questions


def main():
    print("=== PARSING PDF Q&A FILES ===\n")
    
    all_questions = []
    
    for level, filepath in PDF_FILES.items():
        path = Path(filepath)
        if not path.exists():
            print(f"✗ Level {level}: File not found")
            continue
        
        print(f"Parsing Level {level}...")
        questions = parse_pdf_questions(filepath, level)
        print(f"  → Found {len(questions)} questions")
        all_questions.extend(questions)
    
    print(f"\n=== TOTAL QUESTIONS FROM PDFs: {len(all_questions)} ===")
    
    # Remove exact duplicates
    seen = set()
    unique = []
    for q in all_questions:
        key = (q['question'].lower()[:100], q['level'])
        if key not in seen:
            seen.add(key)
            unique.append(q)
    
    print(f"Unique questions: {len(unique)}")
    
    # Save to JSON
    output = {
        'source': 'PDF files (9 levels)',
        'total': len(unique),
        'questions': unique
    }
    
    with open('/home/timmy/rp-answers/data/pdf_questions_all.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSaved to data/pdf_questions_all.json")
    
    # Show sample
    print("\nSample questions:")
    for q in unique[:5]:
        print(f"  [{q['level']}] {q['story'][:30]}")
        print(f"    Q: {q['question'][:60]}...")
        print(f"    A: {q['answer'][:40]}...")


if __name__ == '__main__':
    main()
