#!/usr/bin/env python3
"""
Build Complete Task-Oriented Taxonomy from MT-Bench Data

This script systematically parses through MT-Bench human evaluation data
using reasoning agents to build a comprehensive task-oriented error taxonomy.

The taxonomy maps: Human Task → Conceptual Error → Observable Failure

Run in phases to control costs:
  Phase 1: Sample analysis (20-50 cases) - $0.50-$1.50
  Phase 2: Medium coverage (100-200 cases) - $3-$6
  Phase 3: Full coverage (all ~3,000 cases) - $90-$100

Progress is cached, so you can resume anytime!
"""

import argparse
import os
import sys
import json
from pathlib import Path
from collections import Counter

from mt_bench_error_analyzer import MTBenchErrorAnalyzer
from task_oriented_error_analyzer import TaskOrientedErrorAnalyzer


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(text)
    print("="*80 + "\n")


def estimate_cost(num_cases: int) -> tuple:
    """Estimate API cost for analysis"""
    # Claude Sonnet: ~$3 per million input tokens, ~$15 per million output tokens
    # Estimate: ~2000 input tokens + ~1000 output tokens per case
    # = ~$0.006 + ~$0.015 = ~$0.021 per case
    cost_per_case = 0.025  # Rounded up for safety
    total_cost = num_cases * cost_per_case
    return (cost_per_case, total_cost)


def analyze_sample(
    base_analyzer: MTBenchErrorAnalyzer,
    task_analyzer: TaskOrientedErrorAnalyzer,
    sample_size: int = 20
):
    """Phase 1: Analyze a representative sample"""
    print_header("PHASE 1: SAMPLE ANALYSIS")

    print(f"Analyzing {sample_size} representative cases to build initial taxonomy...")

    _, est_cost = estimate_cost(sample_size)
    print(f"Estimated cost: ${est_cost:.2f}\n")

    # Get diverse sample across categories
    error_patterns = base_analyzer.error_patterns

    # Sample across categories
    by_category = {}
    for ep in error_patterns:
        if ep.category not in by_category:
            by_category[ep.category] = []
        by_category[ep.category].append(ep)

    # Take proportional sample from each category
    categories = list(by_category.keys())
    sample_per_cat = max(2, sample_size // len(categories))

    print(f"Sampling {sample_per_cat} cases from each of {len(categories)} categories:")
    for cat in categories:
        print(f"  - {cat}: {len(by_category[cat])} total errors")

    # Analyze sample
    task_errors = task_analyzer.batch_analyze(
        base_analyzer,
        limit=sample_size,
        resume=True
    )

    print(f"\n✓ Sample analysis complete: {len(task_errors)} cases analyzed")
    return task_errors


def analyze_medium_coverage(
    base_analyzer: MTBenchErrorAnalyzer,
    task_analyzer: TaskOrientedErrorAnalyzer,
    target_size: int = 100
):
    """Phase 2: Medium coverage for taxonomy validation"""
    print_header("PHASE 2: MEDIUM COVERAGE")

    current_size = len(task_analyzer.task_errors)
    remaining = target_size - current_size

    if remaining <= 0:
        print(f"Already analyzed {current_size} cases (target: {target_size})")
        print("Skipping phase 2...")
        return task_analyzer.task_errors

    print(f"Current: {current_size} cases analyzed")
    print(f"Target: {target_size} cases")
    print(f"Remaining: {remaining} cases\n")

    _, est_cost = estimate_cost(remaining)
    print(f"Estimated additional cost: ${est_cost:.2f}\n")

    response = input("Continue with Phase 2? (y/n): ")
    if response.lower() != 'y':
        print("Skipping Phase 2")
        return task_analyzer.task_errors

    task_errors = task_analyzer.batch_analyze(
        base_analyzer,
        limit=remaining,
        resume=True
    )

    print(f"\n✓ Medium coverage complete: {len(task_errors)} total cases analyzed")
    return task_errors


def analyze_full_coverage(
    base_analyzer: MTBenchErrorAnalyzer,
    task_analyzer: TaskOrientedErrorAnalyzer
):
    """Phase 3: Full coverage (expensive!)"""
    print_header("PHASE 3: FULL COVERAGE")

    current_size = len(task_analyzer.task_errors)
    total_errors = len(base_analyzer.error_patterns)
    remaining = total_errors - current_size

    if remaining <= 0:
        print(f"Already analyzed all {current_size} cases!")
        return task_analyzer.task_errors

    print(f"Current: {current_size} cases analyzed")
    print(f"Total available: {total_errors} cases")
    print(f"Remaining: {remaining} cases\n")

    _, est_cost = estimate_cost(remaining)
    print(f"⚠️  WARNING: This will cost approximately ${est_cost:.2f}")
    print("This is the FULL dataset analysis.\n")

    response = input("Continue with FULL analysis? Type 'yes' to confirm: ")
    if response.lower() != 'yes':
        print("Skipping Phase 3")
        return task_analyzer.task_errors

    print("\nStarting full analysis...")
    print("This will take a while. Progress is saved incrementally.\n")

    task_errors = task_analyzer.batch_analyze(
        base_analyzer,
        limit=None,  # No limit - analyze all
        resume=True
    )

    print(f"\n✓ FULL COVERAGE COMPLETE: {len(task_errors)} cases analyzed!")
    return task_errors


def print_taxonomy_preview(task_analyzer: TaskOrientedErrorAnalyzer):
    """Print a preview of the discovered taxonomy"""
    print_header("TAXONOMY PREVIEW")

    if not task_analyzer.task_errors:
        print("No errors analyzed yet")
        return

    # Build taxonomy
    taxonomy = task_analyzer.build_task_taxonomy()

    print(f"Task Domains Discovered: {len(taxonomy)}\n")

    for domain, tasks in taxonomy.items():
        print(f"📁 {domain}")
        print(f"   Tasks: {len(tasks)}")

        # Show top 2 tasks
        for task_name in list(tasks.keys())[:2]:
            capabilities = tasks[task_name]
            print(f"   └─ {task_name[:60]}...")
            print(f"      Capability gaps found: {len(capabilities)}")

            # Show top capability gap
            if capabilities:
                top_cap = list(capabilities.keys())[0]
                errors = capabilities[top_cap]
                print(f"      └─ {top_cap}: {len(errors)} conceptual errors")

        if len(tasks) > 2:
            print(f"   ... and {len(tasks) - 2} more tasks")
        print()


def export_taxonomy_for_humans(task_analyzer: TaskOrientedErrorAnalyzer, output_file: str):
    """Export taxonomy in human-readable markdown format"""
    if not task_analyzer.task_errors:
        print("No errors to export")
        return

    taxonomy = task_analyzer.build_task_taxonomy()

    md_lines = [
        "# Task-Oriented Error Taxonomy",
        "",
        f"*Generated from {len(task_analyzer.task_errors)} analyzed MT-Bench error cases*",
        "",
        "---",
        ""
    ]

    for domain, tasks in sorted(taxonomy.items()):
        md_lines.append(f"## {domain}")
        md_lines.append("")

        for task_name, capabilities in sorted(tasks.items()):
            md_lines.append(f"### {task_name}")
            md_lines.append("")

            for cap_category, errors in sorted(capabilities.items()):
                md_lines.append(f"#### Required Capability: {cap_category}")
                md_lines.append("")

                for conceptual_error, instances in sorted(errors.items()):
                    md_lines.append(f"**Conceptual Error**: {conceptual_error}")
                    md_lines.append(f"- Occurrences: {len(instances)}")

                    # Get severity distribution
                    severities = Counter(inst['severity'] for inst in instances)
                    md_lines.append(f"- Severity: {dict(severities)}")

                    # Get affected models
                    models = set(inst['losing_model'] for inst in instances)
                    md_lines.append(f"- Affected models: {', '.join(sorted(models))}")

                    # Show one example
                    example = instances[0]
                    md_lines.append(f"- Example: Q{example['question_id']} - {example['observable_failure']}")
                    md_lines.append("")

                md_lines.append("")

        md_lines.append("---")
        md_lines.append("")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write('\n'.join(md_lines))

    print(f"\n✓ Human-readable taxonomy exported to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Build complete task-oriented error taxonomy from MT-Bench",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--phase',
        choices=['sample', 'medium', 'full', 'all'],
        default='sample',
        help='Which phase to run (default: sample for quick start)'
    )

    parser.add_argument(
        '--sample-size',
        type=int,
        default=20,
        help='Number of cases for sample phase (default: 20)'
    )

    parser.add_argument(
        '--medium-size',
        type=int,
        default=100,
        help='Target size for medium phase (default: 100)'
    )

    parser.add_argument(
        '--skip-confirmation',
        action='store_true',
        help='Skip cost confirmation prompts (use with caution!)'
    )

    args = parser.parse_args()

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable required")
        print("\nSet with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    print_header("TASK-ORIENTED TAXONOMY BUILDER")
    print("This system uses reasoning agents to build a taxonomy mapping:")
    print("  Human Task → Conceptual Error → Observable Failure\n")

    # Initialize analyzers
    print("Initializing...")
    print("  [1/3] Loading MT-Bench questions...")
    base_analyzer = MTBenchErrorAnalyzer()
    base_analyzer.load_questions_from_github()

    print("  [2/3] Loading human judgments...")
    try:
        base_analyzer.load_human_judgments_from_huggingface()
    except Exception as e:
        print(f"Error: {e}")
        print("\nInstall datasets: pip install datasets")
        sys.exit(1)

    print("  [3/3] Extracting error patterns...")
    lopsided = base_analyzer.identify_lopsided_preferences(min_preference_strength='strong')
    base_analyzer.extract_error_patterns(lopsided)

    print(f"\n✓ Ready to analyze {len(base_analyzer.error_patterns)} error patterns")

    # Initialize task analyzer
    task_analyzer = TaskOrientedErrorAnalyzer()

    # Run requested phases
    if args.phase == 'sample' or args.phase == 'all':
        analyze_sample(base_analyzer, task_analyzer, args.sample_size)
        print_taxonomy_preview(task_analyzer)

    if args.phase == 'medium' or args.phase == 'all':
        analyze_medium_coverage(base_analyzer, task_analyzer, args.medium_size)
        print_taxonomy_preview(task_analyzer)

    if args.phase == 'full' or args.phase == 'all':
        analyze_full_coverage(base_analyzer, task_analyzer)

    # Generate final reports
    if task_analyzer.task_errors:
        print_header("GENERATING REPORTS")

        print("1. Generating comprehensive JSON report...")
        task_analyzer.generate_insights_report(
            "./data/mt_bench/task_analysis/task_oriented_taxonomy.json"
        )

        print("\n2. Generating human-readable markdown taxonomy...")
        export_taxonomy_for_humans(
            task_analyzer,
            "./data/mt_bench/task_analysis/TAXONOMY.md"
        )

        print("\n✓ All reports generated!")
        print("\nOutput files:")
        print("  - task_oriented_taxonomy.json (machine-readable)")
        print("  - TAXONOMY.md (human-readable)")
        print("  - analysis_cache.jsonl (resumable cache)")

        # Final stats
        print_header("FINAL STATISTICS")
        print(f"Total cases analyzed: {len(task_analyzer.task_errors)}")
        print(f"Task domains discovered: {len(set(e.task_domain for e in task_analyzer.task_errors))}")
        print(f"Capability gaps identified: {len(set(e.capability_category for e in task_analyzer.task_errors))}")
        print(f"Unique conceptual errors: {len(set(e.conceptual_error for e in task_analyzer.task_errors))}")

        understanding = sum(1 for e in task_analyzer.task_errors if e.is_understanding_failure)
        execution = len(task_analyzer.task_errors) - understanding
        print(f"\nUnderstanding failures: {understanding} ({100*understanding/len(task_analyzer.task_errors):.1f}%)")
        print(f"Execution failures: {execution} ({100*execution/len(task_analyzer.task_errors):.1f}%)")

        print("\nNext steps:")
        print("  - Review TAXONOMY.md for human insights")
        print("  - Use task_oriented_taxonomy.json for integration")
        print("  - Run again with --phase=medium to continue analysis")

    else:
        print("\nNo errors analyzed. Run with --phase=sample to start!")


if __name__ == "__main__":
    main()
