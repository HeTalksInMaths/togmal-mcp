#!/usr/bin/env python3
"""
Validate Failure Rate Prediction Accuracy
==========================================

Tests whether predicted failure rates match ACTUAL failure rates on held-out questions.

Key Question: Does semantic similarity to benchmark questions actually predict
              the same failure modes on new questions?

Method:
1. Take questions with known model performance
2. For each question:
   - Remove from search corpus (held-out)
   - Predict failure rate using remaining questions
   - Compare predicted vs actual failure rate
3. Measure prediction accuracy (MAE, correlation)
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from local_embedding_scorer import LocalSemanticScorer


def create_train_test_split(performance_db_path: str, test_size: float = 0.3):
    """Split questions with performance data into train/test"""

    with open(performance_db_path, 'r') as f:
        perf_data = json.load(f)

    question_ids = list(perf_data['questions'].keys())

    # Shuffle and split
    np.random.seed(42)
    np.random.shuffle(question_ids)

    split_idx = int(len(question_ids) * (1 - test_size))

    train_ids = question_ids[:split_idx]
    test_ids = question_ids[split_idx:]

    return train_ids, test_ids, perf_data


def compute_actual_failure_rate(question_id: str, perf_data: Dict) -> Tuple[float, Dict]:
    """Compute actual failure rate for a question"""

    question_perf = perf_data['questions'][question_id]

    total = 0
    correct = 0
    by_model = {}

    for model, result in question_perf.items():
        total += 1
        if result.get('is_correct'):
            correct += 1

        by_model[model] = result.get('is_correct', False)

    actual_failure_rate = ((total - correct) / total * 100) if total > 0 else None
    actual_success_rate = (correct / total * 100) if total > 0 else None

    return actual_failure_rate, {
        'success_rate': actual_success_rate,
        'total_models': total,
        'by_model': by_model
    }


def predict_failure_rate_held_out(
    test_question_id: str,
    train_questions: List[Dict],
    test_question_text: str,
    test_question_domain: str,
    performance_data: Dict
) -> Dict:
    """Predict failure rate with test question held out"""

    # Build scorer on training questions only
    scorer = LocalSemanticScorer(
        questions=train_questions,
        embedding_dim=488,
        max_features=5004,
        domain_boost=0.496
    )

    # Find similar questions (all will be from training set)
    similar = scorer.search(
        query=test_question_text,
        top_k=20,
        query_domain=test_question_domain
    )

    # Aggregate performance from similar questions
    model_performance = {}
    questions_with_perf = 0

    for sim_q in similar:
        qid = sim_q['question_id']

        # Try to match with performance data
        perf_id = None
        if str(qid) in performance_data:
            perf_id = str(qid)
        elif qid in performance_data:
            perf_id = qid
        elif qid.startswith('mmlu_pro_'):
            original_id = qid.replace('mmlu_pro_', '')
            if original_id in performance_data:
                perf_id = original_id
            elif int(original_id) in performance_data:
                perf_id = int(original_id)

        if perf_id and perf_id != test_question_id:  # Don't include test question
            perf = performance_data[perf_id]
            questions_with_perf += 1

            for model, result in perf.items():
                if model not in model_performance:
                    model_performance[model] = {'correct': 0, 'total': 0}

                model_performance[model]['total'] += 1
                if result.get('is_correct'):
                    model_performance[model]['correct'] += 1

    # Calculate predicted failure rate
    if model_performance:
        total_correct = sum(d['correct'] for d in model_performance.values())
        total_attempts = sum(d['total'] for d in model_performance.values())

        predicted_success_rate = (total_correct / total_attempts * 100) if total_attempts > 0 else None
        predicted_failure_rate = (100 - predicted_success_rate) if predicted_success_rate is not None else None
    else:
        predicted_failure_rate = None
        predicted_success_rate = None
        total_attempts = 0

    return {
        'predicted_failure_rate': predicted_failure_rate,
        'predicted_success_rate': predicted_success_rate,
        'similar_questions_found': len(similar),
        'questions_with_perf': questions_with_perf,
        'total_evaluations': total_attempts,
        'coverage': questions_with_perf / len(similar) if similar else 0
    }


def validate_failure_prediction():
    """Main validation function"""

    print("="*80)
    print("VALIDATING FAILURE RATE PREDICTION ACCURACY")
    print("="*80)

    # Load databases
    perf_db_path = "./data/model_performance_database.json"
    questions_db_path = "./data/unified_database_with_mmlu_pro.json"

    with open(questions_db_path, 'r') as f:
        questions_data = json.load(f)
    all_questions = questions_data['questions']

    # Create train/test split
    print("\n1. Creating train/test split...")
    train_ids, test_ids, perf_data = create_train_test_split(perf_db_path, test_size=0.3)

    print(f"   Training questions: {len(train_ids)}")
    print(f"   Test questions: {len(test_ids)}")

    # Remove test questions from search corpus
    train_questions = [q for q in all_questions
                      if q.get('original_id') not in test_ids
                      and str(q.get('question_id')).replace('mmlu_pro_', '') not in test_ids]

    print(f"   Search corpus size: {len(train_questions)}")

    # For each test question, predict and compare
    print("\n2. Predicting failure rates for test questions...")

    results = []

    for i, test_id in enumerate(test_ids):
        # Get actual failure rate
        actual_failure, actual_details = compute_actual_failure_rate(test_id, perf_data)

        if actual_failure is None:
            continue

        # Get question text
        test_question = None
        for q in all_questions:
            if str(q.get('original_id')) == str(test_id) or str(q['question_id']).replace('mmlu_pro_', '') == str(test_id):
                test_question = q
                break

        if not test_question:
            continue

        # Predict failure rate
        prediction = predict_failure_rate_held_out(
            test_question_id=str(test_id),
            train_questions=train_questions,
            test_question_text=test_question['question_text'],
            test_question_domain=test_question['domain'],
            performance_data=perf_data['questions']
        )

        predicted_failure = prediction['predicted_failure_rate']

        if predicted_failure is not None:
            error = abs(predicted_failure - actual_failure)

            results.append({
                'test_id': test_id,
                'actual_failure_rate': actual_failure,
                'predicted_failure_rate': predicted_failure,
                'error': error,
                'coverage': prediction['coverage'],
                'domain': test_question['domain']
            })

            if (i + 1) % 10 == 0:
                print(f"   Processed {i + 1}/{len(test_ids)} test questions...")

    # Analyze results
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)

    if not results:
        print("\n❌ No predictions could be made (insufficient coverage)")
        return

    errors = [r['error'] for r in results]
    actual_rates = [r['actual_failure_rate'] for r in results]
    predicted_rates = [r['predicted_failure_rate'] for r in results]

    mae = np.mean(errors)
    median_error = np.median(errors)
    correlation = np.corrcoef(actual_rates, predicted_rates)[0, 1] if len(results) > 1 else 0

    print(f"\n📊 OVERALL METRICS:")
    print(f"   Test questions evaluated: {len(results)}")
    print(f"   Mean Absolute Error (MAE): {mae:.1f}%")
    print(f"   Median Absolute Error: {median_error:.1f}%")
    print(f"   Correlation (actual vs predicted): {correlation:.3f}")

    # Binned analysis
    print(f"\n📈 ERROR DISTRIBUTION:")
    bins = [(0, 10), (10, 20), (20, 30), (30, 100)]
    for low, high in bins:
        count = sum(1 for e in errors if low <= e < high)
        pct = count / len(errors) * 100
        print(f"   {low}-{high}% error: {count} questions ({pct:.1f}%)")

    # Show examples
    print(f"\n🎯 BEST PREDICTIONS (lowest error):")
    best = sorted(results, key=lambda x: x['error'])[:5]
    for r in best:
        print(f"   ID {r['test_id']}: Actual {r['actual_failure_rate']:.1f}%, Predicted {r['predicted_failure_rate']:.1f}%, Error {r['error']:.1f}%")

    print(f"\n❌ WORST PREDICTIONS (highest error):")
    worst = sorted(results, key=lambda x: x['error'], reverse=True)[:5]
    for r in worst:
        print(f"   ID {r['test_id']}: Actual {r['actual_failure_rate']:.1f}%, Predicted {r['predicted_failure_rate']:.1f}%, Error {r['error']:.1f}%")

    # Calibration analysis
    print(f"\n📐 CALIBRATION CHECK:")
    print(f"   (Do predicted failure rates match actual rates?)")

    for threshold in [0, 25, 50, 75]:
        actual_above = sum(1 for r in results if r['actual_failure_rate'] >= threshold)
        predicted_above = sum(1 for r in results if r['predicted_failure_rate'] >= threshold)

        if actual_above > 0:
            precision = sum(1 for r in results if r['predicted_failure_rate'] >= threshold and r['actual_failure_rate'] >= threshold) / predicted_above if predicted_above > 0 else 0
            recall = sum(1 for r in results if r['predicted_failure_rate'] >= threshold and r['actual_failure_rate'] >= threshold) / actual_above

            print(f"   Failure rate ≥{threshold}%:")
            print(f"      Precision: {precision*100:.1f}% | Recall: {recall*100:.1f}%")

    # Save results
    output_path = Path("./validation_results.json")
    with open(output_path, 'w') as f:
        json.dump({
            'summary': {
                'n_predictions': len(results),
                'mae': float(mae),
                'median_error': float(median_error),
                'correlation': float(correlation)
            },
            'predictions': results
        }, f, indent=2)

    print(f"\n✅ Results saved to {output_path}")

    # Interpretation
    print("\n" + "="*80)
    print("INTERPRETATION")
    print("="*80)

    if mae < 15:
        print("\n✅ EXCELLENT: Predictions are highly accurate (MAE < 15%)")
        print("   The semantic similarity approach generalizes well to new questions.")
    elif mae < 25:
        print("\n✓ GOOD: Predictions are reasonably accurate (MAE < 25%)")
        print("   The system provides useful guidance but with some uncertainty.")
    elif mae < 40:
        print("\n⚠️ MODERATE: Predictions have significant error (MAE < 40%)")
        print("   Use predictions as rough guidance only. Consider improving:")
        print("   • Increase coverage (more questions with performance data)")
        print("   • Better relevance scoring (weight by similarity)")
        print("   • Domain-specific calibration")
    else:
        print("\n❌ POOR: Predictions are unreliable (MAE ≥ 40%)")
        print("   Current approach may not generalize. Consider:")
        print("   • Question features beyond semantic similarity")
        print("   • Failure mode classification (why did it fail?)")
        print("   • More sophisticated aggregation methods")

    return results


if __name__ == "__main__":
    results = validate_failure_prediction()
