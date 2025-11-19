#!/usr/bin/env python3
"""
Quick Start Example: MT-Bench Error Analysis

This script demonstrates a simple workflow for analyzing conceptual errors
from MT-Bench human evaluations.

Run this to see how lopsided preferences reveal model weaknesses!
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mt_bench_error_analyzer import MTBenchErrorAnalyzer


def main():
    print("="*80)
    print("MT-BENCH ERROR ANALYSIS - QUICK START")
    print("="*80)

    print("\nThis example shows how to extract conceptual errors from MT-Bench")
    print("human evaluations by analyzing lopsided preferences.\n")

    # Step 1: Initialize
    print("Step 1: Initializing analyzer...")
    analyzer = MTBenchErrorAnalyzer(data_dir="./data/mt_bench")

    # Step 2: Load questions
    print("\nStep 2: Loading 80 MT-Bench questions from GitHub...")
    try:
        analyzer.load_questions_from_github()
        print(f"✓ Loaded {len(analyzer.questions)} questions")
        print(f"  Categories: {', '.join(set(q.category for q in analyzer.questions.values()))}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return

    # Step 3: Load human judgments
    print("\nStep 3: Loading 3.3K human judgments from HuggingFace...")
    try:
        analyzer.load_human_judgments_from_huggingface()
        print(f"✓ Loaded {len(analyzer.human_judgments)} human judgments")

        # Show model distribution
        from collections import Counter
        models = []
        for j in analyzer.human_judgments:
            models.extend([j['model_a'], j['model_b']])
        model_counts = Counter(models)
        print(f"  Models: {', '.join(model_counts.keys())}")
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\n  To fix this, install the datasets library:")
        print("    pip install datasets")
        print("\n  Or download data manually from:")
        print("    https://huggingface.co/datasets/lmsys/mt_bench_human_judgments")
        return

    # Step 4: Identify lopsided preferences
    print("\nStep 4: Identifying lopsided preferences (strong winners)...")
    lopsided_cases = analyzer.identify_lopsided_preferences(min_preference_strength='strong')
    print(f"✓ Found {len(lopsided_cases)} cases where one model was strongly preferred")

    # Step 5: Extract error patterns
    print("\nStep 5: Extracting conceptual error patterns...")
    error_patterns = analyzer.extract_error_patterns(lopsided_cases)
    print(f"✓ Extracted {len(error_patterns)} error patterns")

    # Step 6: Analyze distribution
    print("\nStep 6: Analyzing error distribution...\n")
    analysis = analyzer.analyze_error_distribution()

    # Print summary
    print("="*80)
    print("RESULTS SUMMARY")
    print("="*80)

    print(f"\nTotal Errors Analyzed: {analysis['total_errors']}")

    print("\n📊 Top 5 Error Types:")
    for i, (error_type, count) in enumerate(
        sorted(analysis['errors_by_type'].items(), key=lambda x: x[1], reverse=True)[:5],
        1
    ):
        percentage = (count / analysis['total_errors']) * 100
        description = analyzer.error_taxonomy.get(error_type, 'Unknown')
        print(f"  {i}. {error_type:20s}: {count:4d} ({percentage:5.1f}%)")
        print(f"     → {description}")

    print("\n🤖 Errors by Model:")
    for model, count in sorted(analysis['errors_by_model'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / analysis['total_errors']) * 100
        print(f"  - {model:20s}: {count:4d} ({percentage:5.1f}%)")

    print("\n📚 Errors by Category:")
    for category, count in sorted(analysis['errors_by_category'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / analysis['total_errors']) * 100
        print(f"  - {category:20s}: {count:4d} ({percentage:5.1f}%)")

    # Show one detailed example
    print("\n" + "="*80)
    print("EXAMPLE ERROR")
    print("="*80)

    # Get an instruction_following error as an example
    example_errors = analyzer.get_examples_for_error_type('instruction_following', limit=1)
    if not example_errors:
        # Fallback to first error type
        first_error_type = list(analysis['errors_by_type'].keys())[0]
        example_errors = analyzer.get_examples_for_error_type(first_error_type, limit=1)

    if example_errors:
        ex = example_errors[0]
        question = analyzer.questions[ex.question_id]

        print(f"\nError Type: {ex.error_type.upper()}")
        print(f"Description: {ex.description}")
        print(f"Category: {ex.category}")
        print(f"Question ID: {ex.question_id}")

        print(f"\nQuestion (Turn {ex.turn}):")
        print(f"  {question.turns[ex.turn-1]}")

        if ex.turn == 2:
            print(f"\nContext (Turn 1):")
            print(f"  {question.turns[0]}")

        print(f"\n❌ Losing Model ({ex.losing_model}):")
        response_preview = ex.losing_response[:300]
        print(f"  {response_preview}")
        if len(ex.losing_response) > 300:
            print("  ...")

        print(f"\n✓ Winning Model ({ex.winning_model}):")
        response_preview = ex.winning_response[:300]
        print(f"  {response_preview}")
        if len(ex.winning_response) > 300:
            print("  ...")

    # Next steps
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\n1. See full analysis summary:")
    print("   python demo_mt_bench_analysis.py --mode basic --show-examples")

    print("\n2. Try advanced LLM-based analysis:")
    print("   export ANTHROPIC_API_KEY='your-key'")
    print("   python demo_mt_bench_analysis.py --mode advanced --limit 10")

    print("\n3. Integrate with ToGMAL infrastructure:")
    print("   python mt_bench_integration.py")

    print("\n4. Read full documentation:")
    print("   cat MT_BENCH_ERROR_ANALYSIS.md")

    print("\n" + "="*80)
    print("✓ Analysis complete! Data saved to ./data/mt_bench/")
    print("="*80)


if __name__ == "__main__":
    main()
