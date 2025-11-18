"""
Demonstration of Hierarchical Error Taxonomy System

This script shows how to use the complete error analysis pipeline to:
1. Validate dataset quality
2. Classify errors hierarchically
3. Discover patterns through clustering
4. Compare to published baselines
5. Generate comprehensive reports
"""

import json
from pathlib import Path
import numpy as np

from error_taxonomy import (
    ErrorRecord, ErrorAnalyzer, ErrorDetector,
    ErrorCategory, ErrorSubtype
)

from advanced_error_analysis import (
    AdvancedErrorAnalyzer,
    DatasetQualityValidator,
    HierarchicalErrorAnalyzer,
    CognitiveComplexityAnalyzer,
    BaselineComparer,
    ErrorLayer
)

from error_clustering import (
    ErrorPatternDiscovery,
    ErrorCooccurrenceAnalyzer,
    DistractorAnalyzer,
    PatternExporter
)


def demo_basic_error_analysis():
    """
    Demo 1: Basic error classification and taxonomy building
    """
    print("=" * 80)
    print("DEMO 1: Basic Error Classification")
    print("=" * 80)

    # Load benchmark data
    data_path = "data/benchmark_results/raw_benchmark_results.json"

    print(f"\nLoading errors from {data_path}...")

    analyzer = ErrorAnalyzer()
    num_errors = analyzer.load_errors_from_benchmark_data(data_path)

    print(f"Loaded {num_errors} errors")

    # Classify errors
    print("\nClassifying errors using rule-based detection...")
    analyzer.classify_errors()

    # Get summary stats
    stats = analyzer.get_error_summary_stats()

    print("\n--- Summary Statistics ---")
    print(f"Total errors: {stats['total_errors']}")
    print(f"Unique questions: {stats['unique_questions']}")
    print(f"Unique models: {stats['unique_models']}")
    print(f"Classification coverage: {stats['classification_coverage']*100:.1f}%")

    print("\n--- Errors by Category ---")
    for category, count in stats['by_category'].items():
        pct = count / stats['total_errors'] * 100 if stats['total_errors'] > 0 else 0
        print(f"{category}: {count} ({pct:.1f}%)")

    print("\n--- Errors by Domain ---")
    for domain, count in sorted(stats['domains'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"{domain}: {count}")

    # Build model profiles
    print("\n--- Model Error Profiles ---")
    for model_name in set(e.model_name for e in analyzer.errors):
        profile = analyzer.build_model_profile(model_name)
        print(f"\n{model_name}:")
        print(f"  Error rate: {profile.error_rate*100:.1f}%")
        print(f"  Total errors: {profile.total_errors}")

        if profile.weakest_categories:
            print(f"  Weakest areas: {', '.join([c.value for c in profile.weakest_categories])}")

    # Generate taxonomy tree
    print("\n\nGenerating hierarchical taxonomy tree...")
    tree = analyzer.generate_taxonomy_tree()

    print(f"\nTaxonomy has {len(tree['children'])} top-level categories")

    # Export results
    output_dir = "data/error_analysis_results"
    analyzer.export_results(output_dir)

    print(f"\nResults exported to {output_dir}/")

    return analyzer


def demo_advanced_analysis(analyzer: ErrorAnalyzer):
    """
    Demo 2: Advanced analysis with dataset quality and hierarchical attribution
    """
    print("\n\n" + "=" * 80)
    print("DEMO 2: Advanced Error Analysis")
    print("=" * 80)

    advanced = AdvancedErrorAnalyzer()

    # Sample a few errors for detailed analysis
    sample_errors = analyzer.errors[:10]

    print(f"\nPerforming comprehensive analysis on {len(sample_errors)} sample errors...\n")

    for i, error in enumerate(sample_errors[:3], 1):
        print(f"\n--- Error {i}: {error.question_id} ---")

        analysis = advanced.analyze_error_comprehensive(error)

        # Dataset quality
        quality = analysis['dataset_quality']
        print(f"\nDataset Quality: {quality.issue_type.value}")
        if quality.evidence:
            print(f"Evidence: {', '.join(quality.evidence)}")

        # Hierarchical analysis
        hierarchical = analysis['hierarchical_analysis']
        print(f"\nError Layer: {hierarchical.primary_layer.value}")

        if hierarchical.knowledge_gaps:
            print(f"Knowledge Gaps: {', '.join(hierarchical.knowledge_gaps)}")

        if hierarchical.reasoning_failures:
            print(f"Reasoning Failures: {', '.join(hierarchical.reasoning_failures)}")

        print(f"\nRecommended Interventions:")
        for intervention in hierarchical.recommended_interventions[:3]:
            print(f"  - {intervention}")

        # Cognitive complexity
        cognitive = analysis['cognitive_complexity']
        print(f"\nCognitive Level: {cognitive.cognitive_level.name}")
        print(f"Indicators: {', '.join(cognitive.indicators)}")

        print("\n" + "-" * 60)

    # Generate research report for each model
    print("\n\n--- Research Reports by Model ---")

    for model_name in set(e.model_name for e in analyzer.errors):
        model_errors = [e for e in analyzer.errors if e.model_name == model_name]

        print(f"\n\n### {model_name} ###")

        report = advanced.generate_research_report(model_errors, model_name)

        print(f"\nTotal errors: {report['total_errors']}")

        # Baseline comparison
        baseline = report['baseline_comparison']
        if baseline:
            print(f"\n--- Comparison to GPT-4o (MMLU-Pro baseline) ---")
            print(f"Knowledge errors: {baseline.knowledge_errors_pct:.1f}% (baseline: 35%)")
            print(f"Reasoning errors: {baseline.reasoning_errors_pct:.1f}% (baseline: 39%)")
            print(f"Execution errors: {baseline.execution_errors_pct:.1f}% (baseline: 12%)")

            if baseline.similar_to_gpt4o:
                print("\n✓ Error profile is similar to GPT-4o")
            else:
                print("\n✗ Error profile differs from GPT-4o:")
                for category, deviation in baseline.deviation_from_baseline.items():
                    if abs(deviation) > 5:
                        direction = "more" if deviation > 0 else "fewer"
                        print(f"  {abs(deviation):.1f}% {direction} {category} errors")

        # Key findings
        print(f"\n--- Key Findings ---")
        for finding in report['key_findings']:
            print(f"  • {finding}")

        # Cognitive complexity distribution
        print(f"\n--- Cognitive Complexity Distribution ---")
        for level, count in report['cognitive_complexity_distribution'].items():
            pct = count / report['total_errors'] * 100
            print(f"  {level}: {count} ({pct:.1f}%)")


def demo_pattern_discovery(analyzer: ErrorAnalyzer):
    """
    Demo 3: Error pattern discovery through clustering
    """
    print("\n\n" + "=" * 80)
    print("DEMO 3: Error Pattern Discovery")
    print("=" * 80)

    discovery = ErrorPatternDiscovery()

    # Cluster errors
    print("\nClustering errors to discover patterns...")

    # Try HDBSCAN first (better for automatic cluster detection)
    try:
        clusters = discovery.cluster_errors_hdbscan(
            analyzer.errors,
            min_cluster_size=5
        )

        print(f"\nDiscovered {len(clusters)} error patterns using HDBSCAN")

    except Exception as e:
        print(f"\nHDBSCAN failed ({e}), falling back to K-Means...")

        clusters = discovery.cluster_errors_kmeans(
            analyzer.errors,
            n_clusters=10
        )

        print(f"\nDiscovered {len(clusters)} error patterns using K-Means")

    # Show top patterns
    print("\n--- Top Error Patterns ---")

    sorted_clusters = sorted(clusters, key=lambda c: c.size, reverse=True)

    for i, cluster in enumerate(sorted_clusters[:5], 1):
        print(f"\n{i}. {cluster.cluster_name}")
        print(f"   {cluster.cluster_description}")
        print(f"   Size: {cluster.size} errors")
        print(f"   Difficulty: {cluster.avg_difficulty:.2f}")

        if cluster.common_keywords:
            keywords = [kw for kw, _ in cluster.common_keywords[:3]]
            print(f"   Keywords: {', '.join(keywords)}")

        if cluster.dominant_error_type:
            print(f"   Error type: {cluster.dominant_error_type.value}")

    # Analyze co-occurrence
    print("\n\n--- Error Co-occurrence Analysis ---")

    cooccurrence = ErrorCooccurrenceAnalyzer()

    # Find correlated questions
    print("\nFinding questions with correlated errors...")

    correlated_questions = cooccurrence.find_correlated_questions(
        analyzer.errors,
        min_correlation=0.5
    )

    if correlated_questions:
        print(f"\nFound {len(correlated_questions)} pairs of correlated questions")
        print("\nTop 3 correlations:")

        for q1, q2, corr in correlated_questions[:3]:
            print(f"  {q1} ↔ {q2}: {corr:.2f}")
    else:
        print("\nNo strongly correlated questions found (need more data)")

    # Find models with similar error patterns
    print("\n\nFinding models with similar error patterns...")

    similar_models = cooccurrence.find_correlated_errors_across_models(
        analyzer.errors,
        min_jaccard=0.3
    )

    if similar_models:
        print(f"\nFound {len(similar_models)} pairs of similar models")
        print("\nTop pairs:")

        for m1, m2, jaccard in similar_models[:3]:
            print(f"  {m1} ↔ {m2}: {jaccard:.2f} Jaccard similarity")
    else:
        print("\nNo strongly similar model pairs found")

    # Distractor analysis
    print("\n\n--- Distractor Analysis ---")
    print("Analyzing why certain wrong answers are attractive...\n")

    distractor_analyzer = DistractorAnalyzer()

    # Analyze top questions by error frequency
    question_error_counts = {}
    for error in analyzer.errors:
        question_error_counts[error.question_id] = question_error_counts.get(error.question_id, 0) + 1

    top_questions = sorted(question_error_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    for qid, count in top_questions:
        # Get question details
        question_errors = [e for e in analyzer.errors if e.question_id == qid]
        if not question_errors:
            continue

        first_error = question_errors[0]

        distractor = distractor_analyzer.analyze_distractors(
            qid,
            first_error.correct_answer,
            analyzer.errors
        )

        if distractor and distractor.strongest_distractor:
            print(f"Question: {qid}")
            print(f"  Models failed: {count}")
            print(f"  Strongest distractor: {distractor.strongest_distractor} ({distractor.distractor_strength*100:.0f}% of errors)")

            if distractor.plausibility_reasons:
                print(f"  Why it's attractive: {', '.join(distractor.plausibility_reasons)}")

            print()

    # Export results
    print("\n\nExporting pattern discovery results...")

    exporter = PatternExporter()

    output_dir = Path("data/error_analysis_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export clusters
    exporter.export_clusters_to_json(
        clusters,
        str(output_dir / "error_clusters.json")
    )

    # Export co-occurrence matrix
    try:
        exporter.export_cooccurrence_matrix(
            analyzer.errors,
            str(output_dir / "error_cooccurrence.csv")
        )
    except:
        print("(Co-occurrence matrix export skipped - need more data)")

    # Generate pattern report
    cooccurrence_results = {
        'question_pairs': correlated_questions,
        'model_pairs': similar_models
    }

    exporter.generate_pattern_report(
        clusters,
        cooccurrence_results,
        str(output_dir / "pattern_discovery_report.md")
    )

    print(f"\nPattern discovery results exported to {output_dir}/")

    return clusters


def demo_research_comparison():
    """
    Demo 4: Compare our findings to published research
    """
    print("\n\n" + "=" * 80)
    print("DEMO 4: Comparison to Published Research")
    print("=" * 80)

    print("\nPublished Baseline (GPT-4o on MMLU-Pro):")
    print("  39% - Reasoning process flaws")
    print("  35% - Domain expertise gaps")
    print("  12% - Computational errors")
    print("  14% - Other")

    print("\n(See RESEARCH_FINDINGS.md for detailed comparison)")
    print("\nKey research insights integrated:")
    print("  ✓ Hierarchical error framework (HEC)")
    print("  ✓ Dataset quality validation ('Are We Done with MMLU?')")
    print("  ✓ Cognitive complexity (Bloom's Taxonomy)")
    print("  ✓ Error layer attribution (Reason's hierarchy)")


def main():
    """
    Run all demonstrations
    """
    print("\n" + "=" * 80)
    print("HIERARCHICAL ERROR TAXONOMY DEMONSTRATION")
    print("=" * 80)

    print("\nThis demonstration shows how to build a hierarchical taxonomy")
    print("of conceptual errors that LLMs make on MMLU-Pro dataset.")
    print("\nBased on research findings from:")
    print("  - MMLU-Pro error analysis (Wang et al., 2024)")
    print("  - 'Are We Done with MMLU?' (Koto et al., 2024)")
    print("  - Hierarchical Error Framework (Li et al., 2024)")
    print("  - Math error dataset (Zhang et al., 2024)")

    # Demo 1: Basic analysis
    analyzer = demo_basic_error_analysis()

    # Demo 2: Advanced analysis
    demo_advanced_analysis(analyzer)

    # Demo 3: Pattern discovery
    clusters = demo_pattern_discovery(analyzer)

    # Demo 4: Research comparison
    demo_research_comparison()

    print("\n\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)

    print("\n✓ Error taxonomy built")
    print("✓ Patterns discovered")
    print("✓ Models profiled")
    print("✓ Results exported to data/error_analysis_results/")

    print("\n\nNext Steps:")
    print("1. Populate actual model answers (not just correct/incorrect)")
    print("2. Expand to full 12K MMLU-Pro dataset")
    print("3. Run LLM-assisted classification for deeper insights")
    print("4. Create interactive visualization dashboard")
    print("5. Compare across model generations (GPT-3.5 → GPT-4 → GPT-4o)")

    print("\n\nFor more details, see:")
    print("  - ERROR_TAXONOMY_DESIGN.md - Complete design document")
    print("  - RESEARCH_FINDINGS.md - Research synthesis")
    print("  - error_taxonomy.py - Core implementation")
    print("  - advanced_error_analysis.py - Research-based enhancements")
    print("  - error_clustering.py - Pattern discovery tools")


if __name__ == "__main__":
    main()
