#!/usr/bin/env python3
"""
Combined Tier-1 + Tier-2 Evaluation
====================================

Measures the full screening system against ground truth: a prompt is flagged
when the lightweight checker fires (should_analyze) OR the semantic checker
confidently predicts success < 0.6. Ground truth: measured success rate
< 0.6 or known error patterns.

Run as a pipeline stage (togmal_pipeline) or standalone:
    python3 evaluate_combined_tiers.py [sample_size]

Writes data/combined_tier_evaluation.json.
"""

import json
import random
import sys
from pathlib import Path

from lightweight_prompt_checker_improved import LightweightPromptChecker
from semantic_difficulty_checker import SemanticDifficultyChecker


def main():
    sample_size = int(sys.argv[1]) if len(sys.argv) > 1 else 2000

    sem = SemanticDifficultyChecker.load()
    lw = LightweightPromptChecker()
    questions = json.load(open('data/unified_database_complete.json'))['questions']
    sample = random.Random(42).sample(range(len(questions)),
                                      min(sample_size, len(questions)))

    tp = fp = tn = fn = 0
    t1_only = t2_only = 0

    for n, i in enumerate(sample):
        if (n + 1) % 500 == 0:
            print(f"  {n + 1}/{len(sample)}...")
        q = questions[i]
        actual = q['success_rate'] < 0.6 or bool(q.get('error_patterns'))
        t1 = lw.quick_check(q['question_text'])['should_analyze']
        r2 = sem.assess(q['question_text'], exclude_dups_of_query=True)
        t2 = r2['confident'] and r2['predicted_success_rate'] < 0.6
        flagged = t1 or t2
        if actual and flagged:
            tp += 1
            if t1 and not t2:
                t1_only += 1
            if t2 and not t1:
                t2_only += 1
        elif actual:
            fn += 1
        elif flagged:
            fp += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0

    results = {
        'sample_size': len(sample),
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'fpr': round(fpr, 4),
        'tier1_unique_tps': t1_only,
        'tier2_unique_tps': t2_only,
        'confusion': {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn},
    }

    print(f"\nCOMBINED (T1 OR T2): P={precision:.1%} R={recall:.1%} "
          f"F1={f1:.1%} FPR={fpr:.1%}")
    print(f"unique TPs — Tier-1 only: {t1_only}, Tier-2 only: {t2_only}")

    out = Path('data/combined_tier_evaluation.json')
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"saved {out}")


if __name__ == '__main__':
    main()
