#!/usr/bin/env python3
"""
Build Simple Test Database for Lightweight Checker Testing
===========================================================

Creates a minimal unified_database_complete.json using existing datasets.
This allows testing the lightweight checker without needing full MMLU-Pro/DS-1000 data.
"""

import json
from pathlib import Path

def build_simple_test_db():
    """Build simple test database from existing datasets"""

    print("Building simple test database from existing datasets...")

    data_dir = Path("./data")

    # Load existing datasets
    datasets_dir = data_dir / "datasets"
    combined_path = datasets_dir / "combined_dataset.json"

    if not combined_path.exists():
        print(f"❌ Error: {combined_path} not found")
        return

    print(f"Loading {combined_path}...")
    with open(combined_path, 'r') as f:
        combined_data = json.load(f)

    # Extract all questions from all categories
    all_items = []
    if 'categories' in combined_data:
        for category, items in combined_data['categories'].items():
            all_items.extend(items)
    else:
        all_items = combined_data

    print(f"Found {len(all_items)} total items")

    # Convert to unified format
    questions = []
    for idx, item in enumerate(all_items[:1000]):  # Use first 1000
        # Extract question text (different formats in dataset)
        question_text = item.get('question') or item.get('text') or item.get('prompt', '')

        if not question_text:
            continue

        # Get LLM performance to determine success rate
        llm_performance = item.get('metadata', {}).get('llm_performance', 0.5)

        # Create unified question format
        question = {
            "question_id": item.get('id', f"test_{idx}"),
            "question_text": question_text,
            "benchmark": item.get('source', 'test'),
            "domain": item.get('domain', 'general'),
            "success_rate": llm_performance,
            "difficulty_score": 1.0 - llm_performance,
            "model_scores": {},
            "num_models_tested": 0,
            "error_patterns": [],  # No error patterns for simple test
            "error_categories": [],
            "conceptual_gaps": [],
            "difficulty_label": "Medium" if llm_performance > 0.4 and llm_performance < 0.7 else ("Easy" if llm_performance >= 0.7 else "Hard"),
            "is_universal_failure": False,
            "cot_failure_mode": None,
            "ml_cluster_id": None,
            "category": item.get('cluster_category'),
            "subject": item.get('domain')
        }

        questions.append(question)

    # Create unified database structure
    unified_db = {
        "metadata": {
            "version": "1.0-simple",
            "total_questions": len(questions),
            "source": "existing_datasets",
            "note": "Simplified test database - no real error patterns or success rates"
        },
        "questions": questions,
        "statistics": {
            "total": len(questions),
            "by_benchmark": {"test": len(questions)},
            "with_error_patterns": 0
        }
    }

    # Save
    output_path = data_dir / "unified_database_complete.json"
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(unified_db, f, indent=2)

    print(f"\n✅ Created test database with {len(questions)} questions")
    print(f"📁 Saved to: {output_path}")
    print(f"📊 Size: {output_path.stat().st_size / 1024:.1f} KB")
    print("\n⚠️  Note: This is a simplified database without real success rates or error patterns")
    print("   It's sufficient for basic testing of the lightweight checker's pattern matching")

if __name__ == "__main__":
    build_simple_test_db()
