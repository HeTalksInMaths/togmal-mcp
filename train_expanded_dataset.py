#!/usr/bin/env python3
"""
Re-train Predictor with Expanded Dataset (14,766 Questions)
===========================================================

After integrating Phase 1 & 2 AI/ML/DS benchmarks:
- RE-Bench: 7 tasks
- MLAgentBench: 13 tasks
- ML-Bench: 1,494 tasks

Total: 13,252 → 14,766 questions (+11.4%)
ML/DS coverage: 8.2% → 14.4%

Evaluate improvements over baseline:
- Baseline correlation: 0.500
- Baseline MAE: 23.3%
- Baseline confidence: 0.406
"""

import json
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.stats import pearsonr


def load_data():
    """Load the expanded unified database"""

    with open('data/unified_database_with_real_mle.json') as f:
        unified_db = json.load(f)

    with open('data/model_performance_database.json') as f:
        perf_db = json.load(f)

    return unified_db, perf_db


def extract_failure_rates(unified_db, perf_db):
    """Extract ALL failure rates from both databases"""

    failure_rates = {}

    # 1. Extract from unified DB (now 14,766 questions!)
    print("Extracting failure rates from unified database...")
    for q in unified_db['questions']:
        qid = str(q['question_id'])
        if 'success_rate' in q and q['success_rate'] is not None:
            failure_rate = 1.0 - q['success_rate']
            failure_rates[qid] = failure_rate

    print(f"  Found {len(failure_rates):,} questions from unified DB")

    # 2. Override with performance DB if available (252 questions)
    override_count = 0
    for qid, data in perf_db['questions'].items():
        if 'failure_rate' in data:
            failure_rates[str(qid)] = data['failure_rate']
            override_count += 1
        else:
            # Compute from model results
            correct_count = sum(1 for m, r in data.items()
                              if isinstance(r, dict) and r.get('is_correct', False))
            total_count = sum(1 for m, r in data.items()
                            if isinstance(r, dict) and 'is_correct' in r)
            if total_count > 0:
                failure_rates[str(qid)] = 1.0 - (correct_count / total_count)
                override_count += 1

    print(f"  Overrode {override_count} with performance DB values")
    print(f"  Total failure rates: {len(failure_rates):,}")

    return failure_rates


def train_test_split(unified_db, failure_rates, test_size=0.2, seed=42):
    """Split into train/test sets"""

    # Get all questions with known failure rates
    all_questions = [q for q in unified_db['questions']
                    if str(q['question_id']) in failure_rates]

    print(f"\nSplitting {len(all_questions):,} questions into train/test...")

    # Shuffle and split
    np.random.seed(seed)
    indices = np.random.permutation(len(all_questions))
    n_test = int(len(all_questions) * test_size)

    test_indices = indices[:n_test]
    train_indices = indices[n_test:]

    train_questions = [all_questions[i] for i in train_indices]
    test_questions = [all_questions[i] for i in test_indices]

    print(f"  Training set: {len(train_questions):,} questions")
    print(f"  Test set: {len(test_questions):,} questions")

    return train_questions, test_questions


def train_predictor(train_questions, failure_rates):
    """Train TF-IDF predictor"""

    print("\nTraining TF-IDF predictor...")

    # Extract texts
    train_texts = [q.get('question_text', '') for q in train_questions]

    # Train TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=2000,
        ngram_range=(1, 2),
        min_df=1,
        stop_words='english'
    )

    train_vectors = vectorizer.fit_transform(train_texts)

    # Store failure rates
    train_failure_rates = {
        str(q['question_id']): failure_rates[str(q['question_id'])]
        for q in train_questions
    }

    print(f"  TF-IDF vocabulary: {len(vectorizer.vocabulary_):,} terms")
    print(f"  Training samples: {len(train_questions):,}")

    return {
        'vectorizer': vectorizer,
        'train_vectors': train_vectors,
        'train_questions': train_questions,
        'train_failure_rates': train_failure_rates
    }


def predict(predictor, query_text, top_k=20):
    """Predict failure rate for a query"""

    # Transform query
    query_vector = predictor['vectorizer'].transform([query_text])

    # Find similar
    similarities = cosine_similarity(query_vector, predictor['train_vectors'])[0]
    top_indices = np.argsort(similarities)[::-1][:top_k]

    # Get similar questions with rates
    similar = []
    for idx in top_indices:
        train_qid = str(predictor['train_questions'][idx]['question_id'])
        sim = similarities[idx]

        if train_qid in predictor['train_failure_rates'] and sim > 0:
            fr = predictor['train_failure_rates'][train_qid]
            similar.append({
                'similarity': float(sim),
                'failure_rate': fr
            })

    # Weighted average
    if similar:
        total_weight = sum(s['similarity'] for s in similar)
        weighted_sum = sum(s['similarity'] * s['failure_rate'] for s in similar)

        pred_fr = weighted_sum / total_weight if total_weight > 0 else 0.5
        confidence = total_weight / top_k
    else:
        pred_fr = 0.5
        confidence = 0.0

    return pred_fr, confidence


def evaluate(predictor, test_questions, failure_rates):
    """Evaluate predictor on test set"""

    print("\nEvaluating on test set...")

    predictions = []
    actuals = []
    confidences = []

    for q in test_questions:
        qid = str(q['question_id'])
        actual_fr = failure_rates[qid]

        query_text = q.get('question_text', '')
        pred_fr, confidence = predict(predictor, query_text)

        predictions.append(pred_fr)
        actuals.append(actual_fr)
        confidences.append(confidence)

    predictions = np.array(predictions)
    actuals = np.array(actuals)
    confidences = np.array(confidences)

    # Compute metrics
    correlation, p_value = pearsonr(predictions, actuals)
    mae = np.mean(np.abs(predictions - actuals))
    avg_confidence = np.mean(confidences)

    return {
        'correlation': correlation,
        'p_value': p_value,
        'mae': mae,
        'avg_confidence': avg_confidence,
        'predictions': predictions,
        'actuals': actuals,
        'confidences': confidences
    }


def analyze_by_domain(test_questions, predictions, actuals, failure_rates):
    """Analyze performance by domain"""

    print("\nAnalyzing performance by domain...")

    domain_stats = {}

    for i, q in enumerate(test_questions):
        domain = q.get('domain', 'unknown')

        if domain not in domain_stats:
            domain_stats[domain] = {
                'predictions': [],
                'actuals': [],
                'count': 0
            }

        domain_stats[domain]['predictions'].append(predictions[i])
        domain_stats[domain]['actuals'].append(actuals[i])
        domain_stats[domain]['count'] += 1

    # Compute per-domain metrics
    results = []
    for domain, stats in domain_stats.items():
        preds = np.array(stats['predictions'])
        acts = np.array(stats['actuals'])

        if len(preds) >= 5:  # Only if enough samples
            corr, _ = pearsonr(preds, acts)
            mae = np.mean(np.abs(preds - acts))

            results.append({
                'domain': domain,
                'count': stats['count'],
                'correlation': corr,
                'mae': mae
            })

    # Sort by count
    results.sort(key=lambda x: x['count'], reverse=True)

    return results


def main():
    print("="*80)
    print("TRAINING WITH EXPANDED DATASET (14,766 QUESTIONS)")
    print("="*80)

    # Load data
    print("\nLoading data...")
    unified_db, perf_db = load_data()
    print(f"  Unified DB size: {len(unified_db['questions']):,} questions")

    # Extract failure rates
    failure_rates = extract_failure_rates(unified_db, perf_db)

    # Split
    train_questions, test_questions = train_test_split(unified_db, failure_rates)

    # Train
    predictor = train_predictor(train_questions, failure_rates)

    # Evaluate
    results = evaluate(predictor, test_questions, failure_rates)

    # Print results
    print("\n" + "="*80)
    print("OVERALL RESULTS")
    print("="*80)
    print(f"\nCorrelation: {results['correlation']:.3f} (p={results['p_value']:.2e})")
    print(f"MAE: {results['mae']:.1%}")
    print(f"Average confidence: {results['avg_confidence']:.3f}")

    # Compare to baseline
    print("\n" + "="*80)
    print("COMPARISON TO BASELINE (13,252 Questions)")
    print("="*80)

    baseline = {
        'correlation': 0.500,
        'mae': 0.233,
        'confidence': 0.406,
        'train_size': 9277
    }

    corr_change = results['correlation'] - baseline['correlation']
    mae_change = results['mae'] - baseline['mae']
    conf_change = results['avg_confidence'] - baseline['confidence']

    print(f"\nCorrelation: {baseline['correlation']:.3f} → {results['correlation']:.3f} "
          f"({corr_change:+.3f}, {(corr_change/baseline['correlation']*100):+.1f}%)")

    print(f"MAE: {baseline['mae']:.1%} → {results['mae']:.1%} "
          f"({mae_change:+.1%}, {(mae_change/baseline['mae']*100):+.1f}%)")

    print(f"Confidence: {baseline['confidence']:.3f} → {results['avg_confidence']:.3f} "
          f"({conf_change:+.3f}, {(conf_change/baseline['confidence']*100):+.1f}%)")

    print(f"\nTraining size: {baseline['train_size']:,} → {len(train_questions):,} "
          f"(+{len(train_questions) - baseline['train_size']:,}, "
          f"+{((len(train_questions) - baseline['train_size'])/baseline['train_size']*100):.1f}%)")

    # Domain analysis
    domain_results = analyze_by_domain(test_questions, results['predictions'],
                                       results['actuals'], failure_rates)

    print("\n" + "="*80)
    print("PERFORMANCE BY DOMAIN (Top 10)")
    print("="*80)
    print(f"\n{'Domain':<25} {'Count':>8} {'Correlation':>12} {'MAE':>10}")
    print("-"*80)

    for dr in domain_results[:10]:
        print(f"{dr['domain']:<25} {dr['count']:>8,} {dr['correlation']:>12.3f} {dr['mae']:>10.1%}")

    # Analyze ML/DS benchmarks specifically
    print("\n" + "="*80)
    print("ML/AI/DS BENCHMARK PERFORMANCE")
    print("="*80)

    ml_benchmarks = ['RE-Bench', 'MLAgentBench', 'ML-Bench', 'DS-1000', 'MLE-bench']

    for benchmark in ml_benchmarks:
        benchmark_questions = [q for q in test_questions
                              if q.get('benchmark', '') == benchmark]

        if benchmark_questions:
            bench_preds = []
            bench_acts = []

            for q in benchmark_questions:
                idx = test_questions.index(q)
                bench_preds.append(results['predictions'][idx])
                bench_acts.append(results['actuals'][idx])

            bench_preds = np.array(bench_preds)
            bench_acts = np.array(bench_acts)

            if len(bench_preds) >= 3:
                corr, _ = pearsonr(bench_preds, bench_acts)
                mae = np.mean(np.abs(bench_preds - bench_acts))

                print(f"\n{benchmark}:")
                print(f"  Questions: {len(benchmark_questions)}")
                print(f"  Correlation: {corr:.3f}")
                print(f"  MAE: {mae:.1%}")

    # Save results
    output = {
        'expanded_dataset': {
            'total_questions': len(unified_db['questions']),
            'train_size': len(train_questions),
            'test_size': len(test_questions),
            'correlation': float(results['correlation']),
            'p_value': float(results['p_value']),
            'mae': float(results['mae']),
            'avg_confidence': float(results['avg_confidence'])
        },
        'baseline': baseline,
        'improvements': {
            'correlation_change': float(corr_change),
            'correlation_pct': float(corr_change/baseline['correlation']*100),
            'mae_change': float(mae_change),
            'mae_pct': float(mae_change/baseline['mae']*100),
            'confidence_change': float(conf_change),
            'confidence_pct': float(conf_change/baseline['confidence']*100)
        },
        'domain_performance': domain_results
    }

    with open('data/expanded_dataset_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Results saved to: data/expanded_dataset_results.json")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if corr_change > 0.02:
        print("\n✅ SIGNIFICANT IMPROVEMENT in correlation")
    elif corr_change > 0:
        print("\n⚠️  SLIGHT IMPROVEMENT in correlation")
    else:
        print("\n❌ NO IMPROVEMENT in correlation")

    if mae_change < -0.01:
        print("✅ SIGNIFICANT IMPROVEMENT in MAE (lower error)")
    elif mae_change < 0:
        print("⚠️  SLIGHT IMPROVEMENT in MAE")
    else:
        print("❌ NO IMPROVEMENT in MAE (higher error)")

    if conf_change > 0.02:
        print("✅ SIGNIFICANT IMPROVEMENT in confidence")
    elif conf_change > 0:
        print("⚠️  SLIGHT IMPROVEMENT in confidence")
    else:
        print("❌ NO IMPROVEMENT in confidence")

    print(f"\nAdded {len(train_questions) - baseline['train_size']:,} training samples "
          f"from AI/ML/DS benchmarks")

    return output


if __name__ == "__main__":
    main()
