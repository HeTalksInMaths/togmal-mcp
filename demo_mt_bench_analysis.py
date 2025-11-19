"""
Demo: MT-Bench Conceptual Error Analysis

This script demonstrates how to use MT-Bench human evaluation data to extract
conceptual errors from weaker models based on lopsided preferences.

Usage:
    # Basic analysis (no API key needed):
    python demo_mt_bench_analysis.py --mode basic

    # Advanced LLM-based analysis (requires ANTHROPIC_API_KEY):
    python demo_mt_bench_analysis.py --mode advanced --limit 10

    # Analyze specific model:
    python demo_mt_bench_analysis.py --mode basic --model "alpaca-13b"

    # Analyze specific category:
    python demo_mt_bench_analysis.py --mode basic --category "reasoning"
"""

import argparse
import sys
from pathlib import Path

from mt_bench_error_analyzer import MTBenchErrorAnalyzer


def run_basic_analysis(args):
    """Run basic heuristic-based error analysis"""
    print("\n" + "="*80)
    print("BASIC MT-BENCH ERROR ANALYSIS")
    print("="*80)

    # Initialize analyzer
    analyzer = MTBenchErrorAnalyzer(data_dir=args.data_dir)

    # Load data
    print("\nStep 1: Loading MT-Bench questions from GitHub...")
    try:
        analyzer.load_questions_from_github()
    except Exception as e:
        print(f"Error loading questions: {e}")
        return

    print("\nStep 2: Loading human judgment data from HuggingFace...")
    try:
        analyzer.load_human_judgments_from_huggingface()
    except Exception as e:
        print(f"Error: {e}")
        print("\nPlease install the 'datasets' library:")
        print("  pip install datasets")
        return

    # Identify lopsided preferences
    print("\nStep 3: Identifying lopsided preferences...")
    lopsided_cases = analyzer.identify_lopsided_preferences(
        min_preference_strength='strong'
    )

    # Extract error patterns
    print("\nStep 4: Extracting conceptual error patterns...")
    error_patterns = analyzer.extract_error_patterns(lopsided_cases)

    # Filter if requested
    if args.model:
        error_patterns = [ep for ep in error_patterns if ep.losing_model == args.model]
        print(f"\nFiltered to {len(error_patterns)} errors from model: {args.model}")

    if args.category:
        error_patterns = [ep for ep in error_patterns if ep.category == args.category]
        print(f"\nFiltered to {len(error_patterns)} errors in category: {args.category}")

    # Update analyzer's error patterns after filtering
    analyzer.error_patterns = error_patterns

    # Analyze distribution
    print("\nStep 5: Analyzing error distribution...")
    analysis = analyzer.analyze_error_distribution()

    # Print summary
    analyzer.print_analysis_summary(analysis)

    # Show detailed examples
    if args.show_examples:
        print("\n" + "="*80)
        print("DETAILED ERROR EXAMPLES")
        print("="*80)

        # Show examples for top 3 error types
        for error_type, count in list(analysis['errors_by_type'].items())[:3]:
            print(f"\n--- Example: {error_type.upper()} ({count} occurrences) ---")
            examples = analyzer.get_examples_for_error_type(error_type, limit=1)

            if examples:
                ex = examples[0]
                question = analyzer.questions[ex.question_id]

                print(f"\nQuestion ID: {ex.question_id}")
                print(f"Category: {ex.category}")
                print(f"Turn {ex.turn}: {question.turns[ex.turn-1]}")

                print(f"\n  Losing Model ({ex.losing_model}):")
                print(f"    {ex.losing_response[:400]}")
                if len(ex.losing_response) > 400:
                    print("    ...")

                print(f"\n  Winning Model ({ex.winning_model}):")
                print(f"    {ex.winning_response[:400]}")
                if len(ex.winning_response) > 400:
                    print("    ...")

                print(f"\n  Analysis: {ex.description}")

    # Export results
    output_file = Path(args.data_dir) / "error_analysis_basic.json"
    print(f"\nStep 6: Exporting results to {output_file}...")
    analyzer.export_analysis(str(output_file))

    print("\n✓ Basic analysis complete!")


def run_advanced_analysis(args):
    """Run advanced LLM-based error analysis"""
    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nError: Advanced analysis requires ANTHROPIC_API_KEY environment variable.")
        print("Set it with: export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\nOr run basic analysis instead: --mode basic")
        sys.exit(1)

    try:
        from mt_bench_llm_error_classifier import LLMErrorClassifier
    except ImportError as e:
        print(f"Error importing LLM classifier: {e}")
        print("\nMake sure you have installed required dependencies:")
        print("  pip install anthropic")
        sys.exit(1)

    print("\n" + "="*80)
    print("ADVANCED LLM-BASED ERROR ANALYSIS")
    print("="*80)

    # First run basic analysis to get error patterns
    analyzer = MTBenchErrorAnalyzer(data_dir=args.data_dir)

    print("\nStep 1-4: Loading data and extracting basic error patterns...")
    analyzer.load_questions_from_github()

    try:
        analyzer.load_human_judgments_from_huggingface()
    except Exception as e:
        print(f"Error: {e}")
        return

    lopsided_cases = analyzer.identify_lopsided_preferences(min_preference_strength='strong')
    analyzer.extract_error_patterns(lopsided_cases)

    # Filter if requested
    error_patterns = analyzer.error_patterns
    if args.model:
        error_patterns = [ep for ep in error_patterns if ep.losing_model == args.model]
        print(f"\nFiltered to {len(error_patterns)} errors from model: {args.model}")

    if args.category:
        error_patterns = [ep for ep in error_patterns if ep.category == args.category]
        print(f"\nFiltered to {len(error_patterns)} errors in category: {args.category}")

    analyzer.error_patterns = error_patterns

    # Initialize LLM classifier
    print("\nStep 5: Initializing LLM classifier (Claude)...")
    classifier = LLMErrorClassifier(model=args.llm_model)

    # Perform LLM analysis
    limit = args.limit if args.limit else len(error_patterns)
    print(f"\nStep 6: Performing deep LLM analysis on {min(limit, len(error_patterns))} errors...")
    print("(This may take a few minutes depending on the number of errors)")

    detailed_analyses = classifier.batch_analyze_errors(
        analyzer,
        limit=limit,
        filter_category=args.category,
        filter_model=args.model
    )

    # Generate insights report
    output_file = Path(args.data_dir) / "error_analysis_advanced.json"
    print(f"\nStep 7: Generating insights report...")
    classifier.generate_insights_report(detailed_analyses, str(output_file))

    # Show detailed example
    if args.show_examples and detailed_analyses:
        print("\n" + "="*80)
        print("DETAILED LLM ANALYSIS EXAMPLE")
        print("="*80)

        da = detailed_analyses[0]
        question = analyzer.questions[da.error_pattern.question_id]

        print(f"\nQuestion ID: {da.error_pattern.question_id}")
        print(f"Category: {da.error_pattern.category}")
        print(f"Turn {da.error_pattern.turn}: {question.turns[da.error_pattern.turn-1]}")

        print(f"\n--- Losing Model Response ({da.error_pattern.losing_model}) ---")
        print(da.error_pattern.losing_response[:500])
        if len(da.error_pattern.losing_response) > 500:
            print("...")

        print(f"\n--- Winning Model Response ({da.error_pattern.winning_model}) ---")
        print(da.error_pattern.winning_response[:500])
        if len(da.error_pattern.winning_response) > 500:
            print("...")

        print(f"\n--- LLM Analysis ---")
        print(f"Error Category: {da.error_category} / {da.error_subcategory}")
        print(f"Severity: {da.severity}")
        print(f"\nSpecific Mistake:")
        print(f"  {da.specific_mistake}")
        print(f"\nWhy Winning Response Better:")
        print(f"  {da.why_winning_response_better}")
        print(f"\nLesson Learned:")
        print(f"  {da.lesson_learned}")
        print(f"\nDetailed Explanation:")
        print(f"  {da.detailed_explanation}")

    print("\n✓ Advanced analysis complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze MT-Bench evaluation data to extract conceptual errors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--mode',
        choices=['basic', 'advanced'],
        default='basic',
        help='Analysis mode: basic (heuristic) or advanced (LLM-based)'
    )

    parser.add_argument(
        '--data-dir',
        default='./data/mt_bench',
        help='Directory to store/load MT-Bench data'
    )

    parser.add_argument(
        '--model',
        help='Filter analysis to specific model (e.g., "alpaca-13b")'
    )

    parser.add_argument(
        '--category',
        help='Filter analysis to specific category (e.g., "reasoning", "coding")'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of errors to analyze (for advanced mode, to save API costs)'
    )

    parser.add_argument(
        '--llm-model',
        default='claude-3-5-sonnet-20241022',
        help='Claude model to use for advanced analysis'
    )

    parser.add_argument(
        '--show-examples',
        action='store_true',
        help='Show detailed examples of errors'
    )

    args = parser.parse_args()

    if args.mode == 'basic':
        run_basic_analysis(args)
    else:
        run_advanced_analysis(args)


if __name__ == "__main__":
    main()
