#!/usr/bin/env python3
"""
Simple MMLU-Pro Data Fetcher
=============================

Downloads MMLU-Pro dataset directly from HuggingFace and creates
a test database with questions and difficulty estimates.
"""

import json
from pathlib import Path
from collections import defaultdict

try:
    from datasets import load_dataset
    DATASETS_AVAILABLE = True
except ImportError:
    print("❌ Error: datasets not installed")
    print("Run: pip install datasets")
    DATASETS_AVAILABLE = False
    exit(1)

def fetch_mmlu_pro(num_questions=1000):
    """
    Fetch MMLU-Pro questions directly from HuggingFace.

    Args:
        num_questions: Number of questions to fetch (default: 1000)
    """
    print("=" * 80)
    print("Fetching MMLU-Pro Data from HuggingFace")
    print("=" * 80)

    try:
        print("\nLoading MMLU-Pro dataset...")
        # Load MMLU-Pro from HuggingFace
        dataset = load_dataset("TIGER-Lab/MMLU-Pro", split="test")

        print(f"✅ Loaded {len(dataset)} questions from MMLU-Pro")

        # Convert to unified format
        questions = []
        difficulty_counts = defaultdict(int)

        for idx, item in enumerate(dataset):
            if idx >= num_questions:
                break

            # Extract fields
            question_text = item.get('question', '')
            options = item.get('options', [])
            answer = item.get('answer', '')
            category = item.get('category', 'unknown')

            # Estimate difficulty based on category (MMLU-Pro categories have known difficulty)
            # Math, Physics, Engineering are typically harder
            hard_categories = ['math', 'physics', 'engineering', 'computer_science', 'chemistry']
            medium_categories = ['biology', 'economics', 'psychology', 'law']

            category_lower = category.lower()
            if any(cat in category_lower for cat in hard_categories):
                estimated_success = 0.35  # Hard
                difficulty_label = "Hard"
            elif any(cat in category_lower for cat in medium_categories):
                estimated_success = 0.55  # Medium
                difficulty_label = "Medium"
            else:
                estimated_success = 0.70  # Easy
                difficulty_label = "Easy"

            difficulty_counts[difficulty_label] += 1

            # Create unified question format
            question = {
                "question_id": f"mmlu_pro_{idx}",
                "question_text": question_text,
                "benchmark": "MMLU-Pro",
                "domain": category,
                "success_rate": estimated_success,
                "difficulty_score": 1.0 - estimated_success,
                "model_scores": {},
                "num_models_tested": 0,
                "error_patterns": [],
                "error_categories": [],
                "conceptual_gaps": [],
                "difficulty_label": difficulty_label,
                "is_universal_failure": estimated_success < 0.2,
                "cot_failure_mode": None,
                "ml_cluster_id": None,
                "category": category,
                "subject": category,
                "answer": answer,
                "options": options
            }

            questions.append(question)

        # Create unified database structure
        unified_db = {
            "metadata": {
                "version": "1.0-mmlu-pro",
                "total_questions": len(questions),
                "source": "TIGER-Lab/MMLU-Pro (HuggingFace)",
                "note": "Using estimated difficulty based on MMLU-Pro category difficulty patterns",
                "difficulty_distribution": dict(difficulty_counts)
            },
            "questions": questions,
            "statistics": {
                "total": len(questions),
                "by_benchmark": {"MMLU-Pro": len(questions)},
                "with_error_patterns": 0,
                "by_difficulty": dict(difficulty_counts)
            }
        }

        # Save
        output_path = Path("./data/unified_database_complete.json")
        print(f"\nSaving to {output_path}...")
        with open(output_path, 'w') as f:
            json.dump(unified_db, f, indent=2)

        print(f"\n✅ Created database with {len(questions)} questions")
        print(f"📁 Saved to: {output_path}")
        print(f"📊 Size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")

        print("\n📊 Difficulty Distribution:")
        for difficulty, count in difficulty_counts.items():
            pct = count / len(questions) * 100
            print(f"   {difficulty}: {count} ({pct:.1f}%)")

        print("\n✅ Ready to test with: python3 test_lightweight_effectiveness.py")

        return unified_db

    except Exception as e:
        print(f"\n❌ Error fetching data: {e}")
        print("\nTroubleshooting:")
        print("  - Check internet connection")
        print("  - Try: pip install --upgrade datasets")
        raise

if __name__ == "__main__":
    import sys

    num_questions = 1000
    if len(sys.argv) > 1:
        num_questions = int(sys.argv[1])

    fetch_mmlu_pro(num_questions=num_questions)
