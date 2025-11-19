"""
Week 1-2 Validation Work

Runs the foundation validation to ensure taxonomy is grounded before scaling.

Tasks:
1. Load current data and check status
2. Run basic error classification
3. Apply LLM-assisted classification to sample
4. Run validation metrics
5. Generate comprehensive report
6. Identify next steps based on results
"""

import json
from pathlib import Path
from typing import Dict, List
import numpy as np

from error_taxonomy import ErrorAnalyzer, ErrorDetector
from llm_assisted_classifier import LLMAssistedClassifier, MockLLMClassifier
from validation_metrics import TaxonomyValidator
try:
    from benchmark_vector_db import BenchmarkVectorDB
except ImportError:
    BenchmarkVectorDB = None


def check_data_status(data_path: str = "data/benchmark_results/raw_benchmark_results.json"):
    """
    Check current data status and identify gaps.
    """
    print("="*80)
    print("STEP 1: Data Status Check")
    print("="*80)

    try:
        with open(data_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Data file not found: {data_path}")
        print("   Action: Run fetch_real_benchmark_data.py first")
        return None

    metadata = data.get('metadata', {})
    questions = data.get('questions', {})

    print(f"\n📊 Dataset Overview:")
    print(f"  Total questions: {len(questions)}")
    print(f"  Models tracked: {len(metadata.get('top_models', []))}")

    # Check for actual model answers
    has_actual_answers = False
    sample_question = list(questions.values())[0] if questions else None

    if sample_question:
        model_results = sample_question.get('model_results', {})
        print(f"\n  Model results populated: {'❌ NO' if not model_results else '✅ YES'}")

        if model_results:
            # Check if we have actual answers or just binary results
            first_result = list(model_results.values())[0]
            if isinstance(first_result, dict) and 'answer' in first_result:
                has_actual_answers = True
                print(f"  Actual answers available: ✅ YES")
            else:
                print(f"  Actual answers available: ❌ NO (only correct/incorrect)")
        else:
            print(f"  ⚠️  WARNING: model_results field is empty!")
            print(f"     Action: Need to populate model results")

    return {
        'total_questions': len(questions),
        'has_model_results': bool(model_results) if sample_question else False,
        'has_actual_answers': has_actual_answers,
        'data_loaded': True
    }


def run_basic_classification(analyzer: ErrorAnalyzer):
    """
    Run rule-based error classification.
    """
    print("\n" + "="*80)
    print("STEP 2: Rule-Based Classification")
    print("="*80)

    print("\nLoading errors from benchmark data...")
    num_errors = analyzer.load_errors_from_benchmark_data(
        "data/benchmark_results/raw_benchmark_results.json"
    )

    if num_errors == 0:
        print("❌ No errors loaded - model_results field may be empty")
        print("   Generating synthetic errors for demonstration...")
        # For demo, we can't load real errors, so we'd need to handle this
        return False

    print(f"✅ Loaded {num_errors} errors")

    print("\nApplying rule-based classification...")
    analyzer.classify_errors()

    # Get statistics
    stats = analyzer.get_error_summary_stats()

    print(f"\n📊 Classification Results:")
    print(f"  Total errors: {stats['total_errors']}")
    print(f"  Unique questions: {stats['unique_questions']}")
    print(f"  Unique models: {stats['unique_models']}")
    print(f"  Classification coverage: {stats['classification_coverage']*100:.1f}%")

    print(f"\n  Errors by Category:")
    for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            pct = count / stats['total_errors'] * 100
            print(f"    {category}: {count} ({pct:.1f}%)")

    return True


def run_llm_classification(
    analyzer: ErrorAnalyzer,
    sample_size: int = 10,
    use_mock: bool = True
):
    """
    Run LLM-assisted classification on sample.

    Args:
        use_mock: If True, use mock classifier (no API needed)
    """
    print("\n" + "="*80)
    print("STEP 3: LLM-Assisted Classification (Sample)")
    print("="*80)

    if len(analyzer.errors) == 0:
        print("⚠️  No errors to classify")
        return

    # Initialize classifier
    if use_mock:
        print("\nUsing MockLLMClassifier (no API needed)")
        classifier = MockLLMClassifier()
    else:
        print("\nUsing real Claude API...")
        try:
            classifier = LLMAssistedClassifier()
        except Exception as e:
            print(f"❌ Failed to initialize LLM classifier: {e}")
            print("   Falling back to mock classifier")
            classifier = MockLLMClassifier()

    # Sample errors
    sample_errors = analyzer.errors[:sample_size]
    print(f"\nAnalyzing {len(sample_errors)} sample errors...")

    # Classify
    enhanced_analyses = classifier.classify_batch(sample_errors)

    print(f"✅ Completed LLM classification")

    # Compare with rule-based
    comparison = classifier.compare_with_rule_based(enhanced_analyses)

    print(f"\n📊 LLM vs Rule-Based Comparison:")
    print(f"  Agreement rate: {comparison['agreement_rate']*100:.1f}%")
    print(f"  Total analyzed: {comparison['total_analyzed']}")
    print(f"  Agreements: {comparison['agreements']}")
    print(f"  Disagreements: {comparison['disagreements_count']}")
    print(f"  Assessment: {comparison['interpretation'].upper()}")

    if comparison['disagreements_count'] > 0:
        print(f"\n  Sample Disagreements:")
        for i, dis in enumerate(comparison['interesting_disagreements'][:3], 1):
            print(f"    {i}. {dis['question_id']}")
            print(f"       Rule-based: {dis['rule_based']}")
            print(f"       LLM: {dis['llm_classification']} (conf: {dis['llm_confidence']:.2f})")

    # Export enhanced analyses
    output_dir = Path("data/error_analysis_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    classifier.export_enhanced_analyses(
        enhanced_analyses,
        str(output_dir / "llm_enhanced_analyses.json")
    )

    print(f"\n✅ Enhanced analyses exported to {output_dir}/llm_enhanced_analyses.json")

    return enhanced_analyses


def run_validation_suite(analyzer: ErrorAnalyzer):
    """
    Run comprehensive validation metrics.
    """
    print("\n" + "="*80)
    print("STEP 4: Validation Metrics")
    print("="*80)

    validator = TaxonomyValidator(analyzer.errors)

    print("\nRunning validation suite...")
    print("  (Note: Some validations require human input and will be skipped)\n")

    # Run validations
    report = validator.run_all_validations()

    # Print results
    print(report.summary)

    # Export report
    output_dir = Path("data/error_analysis_results")
    validator.export_validation_report(report, str(output_dir))

    print(f"\n✅ Validation report exported to {output_dir}/")

    return report


def generate_next_steps_report(
    data_status: Dict,
    validation_report,
    output_path: str = "data/error_analysis_results/next_steps.md"
):
    """
    Generate actionable next steps based on validation results.
    """
    print("\n" + "="*80)
    print("STEP 5: Next Steps Analysis")
    print("="*80)

    next_steps = []

    # Check data status
    if not data_status.get('has_model_results'):
        next_steps.append({
            'priority': 'CRITICAL',
            'task': 'Populate model results',
            'action': 'Run fetch_real_benchmark_data.py or populate model_results manually',
            'why': 'Cannot analyze errors without model performance data'
        })

    if not data_status.get('has_actual_answers'):
        next_steps.append({
            'priority': 'HIGH',
            'task': 'Get actual model answers',
            'action': 'Fetch or generate actual answers (not just correct/incorrect)',
            'why': 'Needed for distractor analysis and answer pattern detection'
        })

    # Check validation results
    for result in validation_report.results:
        if not result.passed:
            if result.action_needed:
                priority = 'HIGH' if 'insufficient' in result.action_needed.lower() else 'MEDIUM'
                next_steps.append({
                    'priority': priority,
                    'task': result.metric_name,
                    'action': result.action_needed,
                    'why': f'Current score: {result.score:.2f}, need: {result.threshold}'
                })

    # Add scaling recommendations
    if validation_report.passed_validations >= 3:
        next_steps.append({
            'priority': 'MEDIUM',
            'task': 'Scale to full dataset',
            'action': 'Expand from 500 to 12,000 MMLU-Pro questions',
            'why': f'Validation passing ({validation_report.passed_validations}/{validation_report.total_validations}), ready to scale'
        })

    # Generate markdown report
    report = "# Next Steps Report\n\n"
    report += f"Generated from Week 1-2 validation\n\n"

    report += "## Summary\n\n"
    report += f"- Validations passed: {validation_report.passed_validations}/{validation_report.total_validations}\n"
    report += f"- Overall score: {validation_report.overall_score*100:.0f}%\n"
    report += f"- Ready for publication: {'✅ YES' if validation_report.ready_for_publication else '❌ NOT YET'}\n\n"

    # Group by priority
    for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        priority_steps = [s for s in next_steps if s['priority'] == priority]

        if priority_steps:
            report += f"## {priority} Priority\n\n"

            for i, step in enumerate(priority_steps, 1):
                report += f"### {i}. {step['task']}\n\n"
                report += f"**Action**: {step['action']}\n\n"
                report += f"**Why**: {step['why']}\n\n"

    report += "\n## Recommended Timeline\n\n"
    report += "### This Week\n"
    critical = [s for s in next_steps if s['priority'] == 'CRITICAL']
    for step in critical:
        report += f"- [ ] {step['task']}\n"

    report += "\n### Next Week\n"
    high = [s for s in next_steps if s['priority'] == 'HIGH']
    for step in high[:3]:  # Top 3
        report += f"- [ ] {step['task']}\n"

    report += "\n### Weeks 3-4\n"
    report += "- [ ] Scale to full dataset (if validations pass)\n"
    report += "- [ ] Add more models (GPT-4, Claude, Gemini)\n"
    report += "- [ ] Implement intervention testing\n"

    # Write report
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report)

    print(f"\n✅ Next steps report generated: {output_path}")
    print("\n📋 Top Priority Actions:")

    for step in next_steps[:3]:
        print(f"  {step['priority']}: {step['task']}")
        print(f"    → {step['action']}")

    return next_steps


def main():
    """
    Run complete Week 1-2 validation workflow.
    """
    print("\n" + "="*80)
    print("WEEK 1-2 VALIDATION: Foundation Check")
    print("="*80)
    print("\nThis script validates that the error taxonomy is grounded before scaling.")
    print("It implements the validation framework from VALIDATION_FRAMEWORK.md\n")

    # Step 1: Check data status
    data_status = check_data_status()

    if not data_status or not data_status['data_loaded']:
        print("\n❌ Cannot proceed without data")
        print("   Run: python fetch_real_benchmark_data.py")
        return

    # Initialize analyzer
    analyzer = ErrorAnalyzer()

    # Try to load vector DB for embeddings
    if BenchmarkVectorDB is not None:
        try:
            print("\nLoading vector database for embeddings...")
            vector_db = BenchmarkVectorDB()
            analyzer.vector_db = vector_db
            print("✅ Vector DB loaded")
        except Exception as e:
            print(f"⚠️  Could not load vector DB: {e}")
            print("   (Embeddings won't be available for some validations)")
    else:
        print("\n⚠️  BenchmarkVectorDB not available (dependencies missing)")
        print("   (Embeddings won't be available for some validations)")

    # Step 2: Run basic classification
    success = run_basic_classification(analyzer)

    if not success:
        print("\n⚠️  Classification failed - likely no model results in data")
        print("   Continuing with limited validation...\n")

    # Step 3: Run LLM-assisted classification
    if len(analyzer.errors) > 0:
        enhanced_analyses = run_llm_classification(
            analyzer,
            sample_size=10,
            use_mock=True  # Set to False to use real Claude API
        )

    # Step 4: Run validation suite
    if len(analyzer.errors) > 0:
        validation_report = run_validation_suite(analyzer)
    else:
        print("\n⚠️  Skipping validation - no errors to validate")
        # Create dummy report
        from validation_metrics import ValidationReport
        validation_report = ValidationReport(
            total_validations=0,
            passed_validations=0,
            overall_score=0.0,
            results=[],
            summary="No errors to validate",
            ready_for_publication=False
        )

    # Step 5: Generate next steps
    next_steps = generate_next_steps_report(data_status, validation_report)

    # Final summary
    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)

    if len(analyzer.errors) > 0:
        print(f"\n✅ Processed {len(analyzer.errors)} errors")
        print(f"✅ Validation: {validation_report.passed_validations}/{validation_report.total_validations} metrics passed")

        if validation_report.ready_for_publication:
            print("\n🎉 READY FOR NEXT PHASE: Scaling to full dataset")
        else:
            print(f"\n⚠️  NOT READY YET: {len(next_steps)} action items to address")
    else:
        print("\n⚠️  LIMITED VALIDATION: No error data available")
        print("   Priority: Populate model_results field in raw_benchmark_results.json")

    print("\n📁 Results:")
    print("  - data/error_analysis_results/validation_report.md")
    print("  - data/error_analysis_results/validation_report.json")
    print("  - data/error_analysis_results/llm_enhanced_analyses.json")
    print("  - data/error_analysis_results/next_steps.md")

    print("\n📖 Next: Review next_steps.md for prioritized action items")


if __name__ == "__main__":
    main()
