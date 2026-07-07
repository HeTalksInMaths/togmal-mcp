#!/usr/bin/env python3
"""
Test Lightweight Checker Effectiveness
======================================

Evaluates the lightweight pre-screening tier against actual benchmark data
to measure precision, recall, and false positive/negative rates.

Methodology:
1. Load ground truth from unified database (questions with known difficulty)
2. Run lightweight checker on all question texts
3. Compare predictions vs actual success rates
4. Compute metrics: precision, recall, F1, false positive rate
5. Identify improvement opportunities
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

class LightweightEffectivenessTest:
    """Test lightweight checker against ground truth"""

    def __init__(self, checker=None, data_dir: Path = Path("./data")):
        self.data_dir = data_dir
        if checker is None:
            from lightweight_prompt_checker import LightweightPromptChecker
            checker = LightweightPromptChecker()
        self.checker = checker

    def load_ground_truth(self) -> List[Dict]:
        """Load unified database with actual difficulty data"""
        db_path = self.data_dir / "unified_database_complete.json"

        if not db_path.exists():
            raise FileNotFoundError(
                f"Database not found at {db_path}. "
                "Run: python3 build_complete_unified_db.py"
            )

        with open(db_path, 'r') as f:
            data = json.load(f)

        return data['questions']

    def classify_ground_truth(self, success_rate: float, error_patterns: List) -> str:
        """
        Classify ground truth difficulty

        Rules:
        - CRITICAL: success_rate < 0.2 OR has CRITICAL error patterns
        - HIGH: success_rate < 0.4 OR has HIGH error patterns
        - MEDIUM: success_rate < 0.6 OR has error patterns
        - LOW: success_rate < 0.8
        - NONE: success_rate >= 0.8 and no error patterns
        """
        has_critical = any(p.get('severity') == 'CRITICAL' for p in error_patterns)
        has_high = any(p.get('severity') == 'HIGH' for p in error_patterns)
        has_any_pattern = len(error_patterns) > 0

        if success_rate < 0.2 or has_critical:
            return 'CRITICAL'
        elif success_rate < 0.4 or has_high:
            return 'HIGH'
        elif success_rate < 0.6 or has_any_pattern:
            return 'MEDIUM'
        elif success_rate < 0.8:
            return 'LOW'
        else:
            return 'NONE'

    def run_evaluation(self, sample_size: int = 1000) -> Dict:
        """
        Evaluate lightweight checker on sample of questions

        Args:
            sample_size: Number of questions to test (use smaller for faster testing)

        Returns:
            Evaluation metrics and detailed results
        """
        print("="*80)
        print("Lightweight Checker Effectiveness Test")
        print("="*80)

        # Load ground truth
        print(f"\nLoading ground truth data...")
        questions = self.load_ground_truth()
        print(f"✅ Loaded {len(questions):,} questions")

        # Sample if needed
        if sample_size and sample_size < len(questions):
            import random
            random.seed(42)  # Reproducible sampling
            questions = random.sample(questions, sample_size)
            print(f"📊 Testing on sample of {len(questions):,} questions")

        # Run lightweight checker on all questions
        print(f"\n🔍 Running lightweight checker...")
        results = []

        for i, q in enumerate(questions):
            if (i + 1) % 100 == 0:
                print(f"   Processed {i+1:,} / {len(questions):,} questions...")

            # Ground truth
            gt_risk = self.classify_ground_truth(
                q['success_rate'],
                q.get('error_patterns', [])
            )

            # Lightweight prediction
            prediction = self.checker.quick_check(q['question_text'])
            pred_risk = prediction['risk_level']

            results.append({
                'question_id': q['question_id'],
                'question_text': q['question_text'][:100],
                'benchmark': q['benchmark'],
                'domain': q['domain'],
                'success_rate': q['success_rate'],
                'error_patterns': len(q.get('error_patterns', [])),
                'ground_truth_risk': gt_risk,
                'predicted_risk': pred_risk,
                'should_analyze': prediction['should_analyze'],
                'triggers': prediction['triggers'],
                'risk_score': prediction['risk_score'],
                'confidence': prediction['confidence']
            })

        print(f"✅ Completed {len(results):,} predictions\n")

        # Compute metrics
        return self._compute_metrics(results)

    def _compute_metrics(self, results: List[Dict]) -> Dict:
        """Compute precision, recall, F1, and other metrics"""

        # Ground truth binary: NONE/LOW = safe, MEDIUM/HIGH/CRITICAL = risky.
        # Prediction binary: the checker's actual gating decision (should_analyze),
        # since that is what routes a prompt to Tier 2 deep analysis.
        def is_risky(risk_level: str) -> bool:
            return risk_level in ['MEDIUM', 'HIGH', 'CRITICAL']

        # Confusion matrix
        tp = sum(1 for r in results if is_risky(r['ground_truth_risk']) and r['should_analyze'])
        fp = sum(1 for r in results if not is_risky(r['ground_truth_risk']) and r['should_analyze'])
        tn = sum(1 for r in results if not is_risky(r['ground_truth_risk']) and not r['should_analyze'])
        fn = sum(1 for r in results if is_risky(r['ground_truth_risk']) and not r['should_analyze'])

        total = len(results)

        # Metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / total
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0  # False positive rate

        # Breakdown by benchmark
        by_benchmark = defaultdict(lambda: {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0})
        for r in results:
            bench = r['benchmark']
            if is_risky(r['ground_truth_risk']) and r['should_analyze']:
                by_benchmark[bench]['tp'] += 1
            elif not is_risky(r['ground_truth_risk']) and r['should_analyze']:
                by_benchmark[bench]['fp'] += 1
            elif not is_risky(r['ground_truth_risk']) and not r['should_analyze']:
                by_benchmark[bench]['tn'] += 1
            else:
                by_benchmark[bench]['fn'] += 1

        # Find false positives and false negatives for analysis
        false_positives = [r for r in results if not is_risky(r['ground_truth_risk']) and r['should_analyze']][:10]
        false_negatives = [r for r in results if is_risky(r['ground_truth_risk']) and not r['should_analyze']][:10]

        # Trigger accuracy: a trigger fired correctly when the question it fired on
        # is genuinely risky (it contributed to a TP rather than an FP)
        trigger_analysis = defaultdict(lambda: {'correct': 0, 'incorrect': 0})
        for r in results:
            for trigger in r['triggers']:
                if is_risky(r['ground_truth_risk']):
                    trigger_analysis[trigger]['correct'] += 1
                else:
                    trigger_analysis[trigger]['incorrect'] += 1

        # Print results
        print("="*80)
        print("EVALUATION RESULTS")
        print("="*80)

        print(f"\n📊 Overall Metrics:")
        print(f"   Accuracy:  {accuracy:.1%}")
        print(f"   Precision: {precision:.1%} (of predicted risky, how many are truly risky)")
        print(f"   Recall:    {recall:.1%} (of truly risky, how many were caught)")
        print(f"   F1 Score:  {f1:.1%}")
        print(f"   FPR:       {fpr:.1%} (false positive rate)")

        print(f"\n🎯 Confusion Matrix:")
        print(f"   True Positives:  {tp:,} (correctly identified risky)")
        print(f"   True Negatives:  {tn:,} (correctly identified safe)")
        print(f"   False Positives: {fp:,} (flagged safe as risky)")
        print(f"   False Negatives: {fn:,} (missed risky questions)")

        print(f"\n📚 By Benchmark:")
        for bench, counts in by_benchmark.items():
            bench_precision = counts['tp'] / (counts['tp'] + counts['fp']) if (counts['tp'] + counts['fp']) > 0 else 0
            bench_recall = counts['tp'] / (counts['tp'] + counts['fn']) if (counts['tp'] + counts['fn']) > 0 else 0
            print(f"   {bench}:")
            print(f"      Precision: {bench_precision:.1%}, Recall: {bench_recall:.1%}")

        print(f"\n🔍 Trigger Effectiveness:")
        for trigger, stats in sorted(trigger_analysis.items(), key=lambda x: x[1]['correct'], reverse=True)[:10]:
            total = stats['correct'] + stats['incorrect']
            accuracy_trigger = stats['correct'] / total if total > 0 else 0
            print(f"   {trigger}: {accuracy_trigger:.1%} accurate ({stats['correct']} correct, {stats['incorrect']} incorrect)")

        print(f"\n❌ Sample False Positives (flagged as risky but actually safe):")
        for i, fp_case in enumerate(false_positives[:5], 1):
            print(f"   {i}. {fp_case['question_text']}...")
            print(f"      Ground Truth: {fp_case['ground_truth_risk']} (success={fp_case['success_rate']:.1%})")
            print(f"      Predicted: {fp_case['predicted_risk']}")
            print(f"      Triggers: {', '.join(fp_case['triggers'])}")
            print()

        print(f"\n❌ Sample False Negatives (missed risky questions):")
        for i, fn_case in enumerate(false_negatives[:5], 1):
            print(f"   {i}. {fn_case['question_text']}...")
            print(f"      Ground Truth: {fn_case['ground_truth_risk']} (success={fn_case['success_rate']:.1%})")
            print(f"      Predicted: {fn_case['predicted_risk']}")
            print(f"      Error patterns: {fn_case['error_patterns']}")
            print()

        print("="*80)
        print("RECOMMENDATIONS FOR IMPROVEMENT")
        print("="*80)

        # Generate recommendations based on metrics
        recommendations = []

        if fpr > 0.2:
            recommendations.append(
                f"⚠️  High false positive rate ({fpr:.1%}). Consider:\n"
                f"    - Tightening triggers to reduce false alarms\n"
                f"    - Reviewing which triggers cause most false positives\n"
                f"    - Increasing risk_score thresholds"
            )

        if recall < 0.7:
            recommendations.append(
                f"⚠️  Low recall ({recall:.1%}). Consider:\n"
                f"    - Adding more trigger patterns for missed cases\n"
                f"    - Lowering risk_score thresholds to catch more risky prompts\n"
                f"    - Analyzing false negatives for common patterns"
            )

        if precision < 0.6:
            recommendations.append(
                f"⚠️  Low precision ({precision:.1%}). Consider:\n"
                f"    - Making triggers more specific to reduce false positives\n"
                f"    - Adding context awareness to triggers"
            )

        # Trigger-specific recommendations
        if trigger_analysis:
            worst_triggers = sorted(
                [(t, s['incorrect'] / (s['correct'] + s['incorrect']))
                 for t, s in trigger_analysis.items()],
                key=lambda x: x[1],
                reverse=True
            )[:3]

            if worst_triggers and worst_triggers[0][1] > 0.5:
                recommendations.append(
                    f"⚠️  Problem triggers (high error rate):\n" +
                    "\n".join([f"    - {t}: {err:.1%} error rate" for t, err in worst_triggers])
                )

        if recommendations:
            for rec in recommendations:
                print(f"\n{rec}")
        else:
            print(f"\n✅ Performance looks good! Continue monitoring on larger samples.")

        return {
            'metrics': {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'fpr': fpr
            },
            'confusion_matrix': {
                'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn
            },
            'by_benchmark': dict(by_benchmark),
            'trigger_analysis': dict(trigger_analysis),
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'recommendations': recommendations
        }

def main():
    """Run the effectiveness test

    Usage:
        python3 test_lightweight_effectiveness.py             # original checker, 1K sample
        python3 test_lightweight_effectiveness.py --full      # original checker, all 13K
        python3 test_lightweight_effectiveness.py --improved  # improved checker
        python3 test_lightweight_effectiveness.py --improved --full
    """
    import sys

    use_improved = '--improved' in sys.argv
    sample_size = None if '--full' in sys.argv else 1000

    if use_improved:
        from lightweight_prompt_checker_improved import LightweightPromptChecker
        label = 'improved'
    else:
        from lightweight_prompt_checker import LightweightPromptChecker
        label = 'original'

    print(f"\n🔧 Checker version: {label}\n")

    tester = LightweightEffectivenessTest(checker=LightweightPromptChecker())
    results = tester.run_evaluation(sample_size=sample_size)

    suffix = 'full' if sample_size is None else f'{sample_size}'
    output_path = Path(f"./data/lightweight_effectiveness_{label}_{suffix}.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Results saved to {output_path}")

if __name__ == "__main__":
    main()
