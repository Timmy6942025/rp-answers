#!/usr/bin/env python3
"""Test the answer bot with a sample question."""

from src.rp_answer_bot import MistralAnswerBot, Question

# Test question from the Disney story we saw earlier
test_question = Question(
    question_id=10283825,
    story_id=10023369,
    story_title="Disney's Early Years",
    excerpt="""The early Disney films were created during a time when technology was limited. Animators had to draw each frame by hand, and sound technology was still developing. Walt Disney experimented with new techniques, but the technology of the time constrained what was possible.

What was a major limitation of Disney's early films?""",
    choices=[
        "short cartoons shown at cinemas.",
        "toy versions of cartoon characters.",
        "colorfully illustrated comic books.",
        "advertisements for popular products.",
    ],
    index=8,
    question_progress=[],
)

# Initialize bot and answer
bot = MistralAnswerBot(api_key="OE0D4Cq1SdNn7v80Cggz2tRTXMjk5Nzz")

print("=" * 60)
print("TESTING READING PLUS AI ANSWER BOT")
print("=" * 60)
print(f"\nStory: {test_question.story_title}")
print(f"Question: {test_question.excerpt.split('?')[0]}?")
print(f"\nChoices:")
for i, choice in enumerate(test_question.choices):
    print(f"  {i}. {choice}")
print()

result = bot.answer_question(test_question)

print(f"\n>>> ANSWER: {result.choice_index}")
print(f">>> SELECTED: {test_question.choices[result.choice_index]}")
print(f">>> CONFIDENCE: {result.confidence}")

usage = bot.get_token_usage()
print("\n" + "=" * 60)
print("TOKEN USAGE")
print("=" * 60)
for key, value in usage.items():
    print(f"  {key}: {value}")
