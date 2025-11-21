#!/usr/bin/env python3
"""
Train Predictor Using FULL 12,252 Questions with Model Test Results
====================================================================

CORRECTION: We actually have 12,252 questions with known model performance:
- 12,000 questions (q_0 to q_11999): Tested with Claude, Gemini, Llama-3.1, etc.
- 170 MMLU-Pro questions: Tested with Llama-2 models
- 82 MLE-bench: Measured failure rates

All should be used as "known" rates, not just 252!
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def main():
    print("="*80)
    print("TRAINING WITH FULL 12,252 QUESTIONS")
    print("="*80)

    # Load data
    with open('data/unified_database_with_real_mle.json') as f:
        unified_db = json.load(f)

    with open('data/model_performance_database.json') as f:
        perf_db = json.load(f)

    all_questions = unified_db['questions']
    print(f"\nTotal questions in taxonomy: {len(all_questions):,}")

    # Extract ALL failure rates (not just 252!)
    failure_rates = {}

    # 1. From q_* questions (the 12k)
    for q in all_questions:
        qid = str(q['question_id'])

        if 'success_rate' in q and q['success_rate'] is not None:
            failure_rate = 1.0 - q['success_rate']
            failure_rates[qid] = failure_rate

    # 2. Override with performance DB if available (252 questions)
    for qid, data in perf_db['questions'].items():
        if 'failure_rate' in data:
            # MLE-bench format
            failure_rates[str(qid)] = data['failure_rate']
        else:
            # MMLU-Pro format - compute from models
            correct_count = sum(1 for m, r in data.items()
                              if isinstance(r, dict) and r.get('is_correct', False))
            total_count = sum(1 for m, r in data.items()
                            if isinstance(r, dict) and 'is_correct' in r)
            if total_count > 0:
                failure_rates[str(qid)] = 1.0 - (correct_count / total_count)

    print(f"Questions with known failure rates: {len(failure_rates):,}")

    # Get questions with failure rates
    known_questions = [q for q in all_questions
                      if str(q['question_id']) in failure_rates]

    print(f"Matched questions: {len(known_questions):,}")

    # Split data
    np.random.seed(42)
    indices = np.random.permutation(len(known_questions))
    n_test = int(len(known_questions) * 0.2)
    n_val = int(len(known_questions) * 0.1)

    test_indices = indices[:n_test]
    val_indices = indices[n_test:n_test + n_val]
    train_indices = indices[n_test + n_val:]

    train_questions = [known_questions[i] for i in train_indices]
    val_questions = [known_questions[i] for i in val_indices]
    test_questions = [known_questions[i] for i in test_indices]

    print(f"\nSplit:")
    print(f"  Train: {len(train_questions):,}")
    print(f"  Val:   {len(val_questions):,}")
    print(f"  Test:  {len(test_questions):,}")

    # Train TF-IDF
    print(f"\nTraining TF-IDF predictor...")
    vectorizer = TfidfVectorizer(
        max_features=2000,
        ngram_range=(1, 2),
        min_df=1,
        stop_words='english'
    )

    train_texts = [q.get('question_text', '') for q in train_questions]
    train_vectors = vectorizer.fit_transform(train_texts)

    print(f"  ✅ Fitted on {len(train_questions):,} questions")
    print(f"  ✅ TF-IDF features: {train_vectors.shape[1]:,}")

    # Create failure rate lookup
    train_failure_rates = {
        str(q['question_id']): failure_rates[str(q['question_id'])]
        for q in train_questions
    }

    # Evaluate on test set
    print(f"\nEvaluating on test set...")

    predictions = []
    actuals = []
    confidences = []

    for q in test_questions:
        qid = str(q['question_id'])
        if qid not in failure_rates:
            continue

        # Transform query
        query_vector = vectorizer.transform([q.get('question_text', '')])

        # Find similar
        similarities = cosine_similarity(query_vector, train_vectors)[0]
        top_k = 20
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Weighted average
        total_weight = 0.0
        weighted_sum = 0.0

        for idx in top_indices:
            train_qid = str(train_questions[idx]['question_id'])
            sim = similarities[idx]

            if train_qid in train_failure_rates and sim > 0:
                total_weight += sim
                weighted_sum += sim * train_failure_rates[train_qid]

        if total_weight > 0:
            pred_fr = weighted_sum / total_weight
            conf = total_weight / top_k
        else:
            pred_fr = 0.5
            conf = 0.0

        predictions.append(pred_fr)
        actuals.append(failure_rates[qid])
        confidences.append(conf)

    predictions = np.array(predictions)
    actuals = np.array(actuals)

    # Compute metrics
    mae = np.mean(np.abs(predictions - actuals)) * 100
    rmse = np.sqrt(np.mean((predictions - actuals) ** 2)) * 100
    correlation = np.corrcoef(predictions, actuals)[0, 1] if len(predictions) > 1 else 0.0

    # ECE
    ece = 0.0
    n_bins = 10
    for i in range(n_bins):
        bin_lower = i / n_bins
        bin_upper = (i + 1) / n_bins
        in_bin = (predictions >= bin_lower) & (predictions < bin_upper)
        if np.sum(in_bin) > 0:
            bin_pred = np.mean(predictions[in_bin])
            bin_actual = np.mean(actuals[in_bin])
            bin_size = np.sum(in_bin) / len(predictions)
            ece += bin_size * abs(bin_pred - bin_actual)

    print(f"\n{'='*80}")
    print("RESULTS WITH FULL 12,252 QUESTIONS")
    print(f"{'='*80}\n")

    print(f"  MAE:         {mae:.2f}%")
    print(f"  RMSE:        {rmse:.2f}%")
    print(f"  Correlation: {correlation:.3f}")
    print(f"  ECE:         {ece:.3f}")
    print(f"  Confidence:  {np.mean(confidences):.3f}")
    print(f"  Test size:   {len(predictions):,}")

    # Compare to previous results
    print(f"\n{'='*80}")
    print("COMPARISON TO 252-ONLY APPROACH")
    print(f"{'='*80}\n")

    try:
        with open('data/cv_results.json') as f:
            cv_results = json.load(f)
        prev_corr = cv_results['word_overlap']['summary']['correlation']['mean']
        prev_mae = cv_results['word_overlap']['summary']['mae']['mean']

        print(f"| Metric | 252 only | Full 12,252 | Improvement |")
        print(f"|--------|----------|-------------|-------------|")
        print(f"| Correlation | {prev_corr:.3f} | {correlation:.3f} | {correlation - prev_corr:+.3f} |")
        print(f"| MAE | {prev_mae:.1f}% | {mae:.1f}% | {prev_mae - mae:+.1f}% |")
        print(f"| Training size | 200 | {len(train_questions):,} | +{len(train_questions) - 200:,} |")

        if correlation > prev_corr:
            improvement_pct = (correlation - prev_corr) / abs(prev_corr) * 100
            print(f"\n  ✅ Correlation improved by {improvement_pct:.1f}%!")
            print(f"  ✅ Training set {len(train_questions)/200:.1f}x larger!")

    except Exception as e:
        print(f"  (Could not load previous results: {e})")

    # Save results
    results = {
        'approach': 'full_dataset',
        'total_questions': len(known_questions),
        'train_size': len(train_questions),
        'test_size': len(test_questions),
        'metrics': {
            'mae': mae,
            'rmse': rmse,
            'correlation': correlation,
            'ece': ece,
            'confidence': float(np.mean(confidences))
        }
    }

    with open('data/full_dataset_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: data/full_dataset_results.json")

    print(f"\n{'='*80}")
    print("KEY INSIGHT")
    print(f"{'='*80}\n")
    print(f"""
We were artificially limiting ourselves to 252 questions when we had
{len(known_questions):,} questions with validated model performance!

This was the confusion:
- Performance DB had 252 questions with Llama models
- But unified DB had 12,000 questions with Claude/Gemini/other models
- Both are equally valid "known" failure rates!

Using all {len(known_questions):,} questions gives us:
- Correlation: {correlation:.3f}
- MAE: {mae:.2f}%
- Much larger training set ({len(train_questions):,} vs 200)
""")


if __name__ == "__main__":
    main()
