#!/usr/bin/env python3
"""
K-Fold Cross-Validation for Failure Rate Predictor
===================================================

Implements k-fold cross-validation to provide confidence intervals
on predictor performance metrics. This addresses the concern about
having "better confidence things are working".

Features:
- 5-fold stratified cross-validation
- 95% confidence intervals on all metrics
- Comparison of word overlap vs TF-IDF approaches
- Statistical significance testing

Usage:
    python train_with_cv.py --method word_overlap
    python train_with_cv.py --method tfidf
    python train_with_cv.py --method both
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
import argparse
import scipy.stats as stats


@dataclass
class CVResults:
    """Results from cross-validation"""
    method: str
    mae_scores: List[float]
    rmse_scores: List[float]
    correlation_scores: List[float]
    ece_scores: List[float]
    confidence_scores: List[float]

    def get_summary(self) -> Dict:
        """Compute mean ± std and 95% CI for all metrics"""
        return {
            'mae': {
                'mean': np.mean(self.mae_scores),
                'std': np.std(self.mae_scores),
                'ci_95': self._confidence_interval(self.mae_scores)
            },
            'rmse': {
                'mean': np.mean(self.rmse_scores),
                'std': np.std(self.rmse_scores),
                'ci_95': self._confidence_interval(self.rmse_scores)
            },
            'correlation': {
                'mean': np.mean(self.correlation_scores),
                'std': np.std(self.correlation_scores),
                'ci_95': self._confidence_interval(self.correlation_scores)
            },
            'ece': {
                'mean': np.mean(self.ece_scores),
                'std': np.std(self.ece_scores),
                'ci_95': self._confidence_interval(self.ece_scores)
            },
            'confidence': {
                'mean': np.mean(self.confidence_scores),
                'std': np.std(self.confidence_scores),
                'ci_95': self._confidence_interval(self.confidence_scores)
            }
        }

    def _confidence_interval(self, scores: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """Compute confidence interval using t-distribution"""
        n = len(scores)
        mean = np.mean(scores)
        std_err = stats.sem(scores)
        margin = std_err * stats.t.ppf((1 + confidence) / 2, n - 1)
        return (mean - margin, mean + margin)


class WordOverlapPredictor:
    """Simple word overlap predictor (current baseline)"""

    def __init__(self):
        self.training_questions = []
        self.failure_rates = {}

    def fit(self, questions: List[Dict], failure_rates: Dict[str, float]):
        """Fit predictor on training data"""
        self.training_questions = questions
        self.failure_rates = failure_rates

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute Jaccard similarity"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def predict(self, query_text: str, top_k: int = 10) -> Dict:
        """Predict failure rate for query"""
        # Find similar questions
        similarities = []
        for q in self.training_questions:
            qid = str(q['question_id'])
            q_text = q.get('question_text', '')
            sim = self.compute_similarity(query_text, q_text)
            if qid in self.failure_rates:
                similarities.append((qid, sim))

        if not similarities:
            return {'failure_rate': 0.5, 'confidence': 0.0}

        # Sort and take top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_similar = similarities[:top_k]

        # Weighted average
        total_weight = sum(sim for _, sim in top_similar)
        if total_weight == 0:
            return {'failure_rate': 0.5, 'confidence': 0.0}

        weighted_sum = sum(self.failure_rates[qid] * sim
                          for qid, sim in top_similar)
        failure_rate = weighted_sum / total_weight
        confidence = total_weight / top_k  # Normalized

        return {
            'failure_rate': failure_rate,
            'confidence': confidence
        }


class TfidfPredictor:
    """TF-IDF based predictor (improved approach)"""

    def __init__(self):
        self.training_questions = []
        self.failure_rates = {}
        self.vectorizer = None
        self.training_vectors = None

    def fit(self, questions: List[Dict], failure_rates: Dict[str, float]):
        """Fit predictor on training data"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            self.training_questions = questions
            self.failure_rates = failure_rates

            # Extract texts
            texts = [q.get('question_text', '') for q in questions]

            # Fit TF-IDF vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                min_df=1,
                stop_words='english'
            )
            self.training_vectors = self.vectorizer.fit_transform(texts)

        except ImportError:
            print("⚠️  sklearn not available, falling back to word overlap")
            self.vectorizer = None

    def predict(self, query_text: str, top_k: int = 10) -> Dict:
        """Predict failure rate for query"""
        if self.vectorizer is None:
            # Fallback to word overlap
            predictor = WordOverlapPredictor()
            predictor.fit(self.training_questions, self.failure_rates)
            return predictor.predict(query_text, top_k)

        from sklearn.metrics.pairwise import cosine_similarity

        # Transform query
        query_vector = self.vectorizer.transform([query_text])

        # Compute similarities
        similarities = cosine_similarity(query_vector, self.training_vectors)[0]

        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        top_sims = similarities[top_indices]

        # Weighted average
        total_weight = np.sum(top_sims)
        if total_weight == 0:
            return {'failure_rate': 0.5, 'confidence': 0.0}

        weighted_sum = sum(
            self.failure_rates[str(self.training_questions[idx]['question_id'])] * top_sims[i]
            for i, idx in enumerate(top_indices)
            if str(self.training_questions[idx]['question_id']) in self.failure_rates
        )

        failure_rate = weighted_sum / total_weight
        confidence = total_weight / top_k

        return {
            'failure_rate': failure_rate,
            'confidence': confidence
        }


def load_data() -> Tuple[List[Dict], Dict[str, float]]:
    """Load unified database and performance data"""
    print("Loading data...")

    # Load unified database
    unified_db_path = Path('data/unified_database_with_real_mle.json')
    with open(unified_db_path) as f:
        unified_db = json.load(f)

    # Load performance database
    perf_db_path = Path('data/model_performance_database.json')
    with open(perf_db_path) as f:
        perf_db = json.load(f)

    # Extract failure rates
    failure_rates = {}
    if 'questions' in perf_db:
        # Two possible formats:
        # 1. MLE-bench: {"questions": {"qid": {"failure_rate": 0.X, ...}}}
        # 2. MMLU-Pro: {"questions": {"qid": {"model1": {"is_correct": ...}, ...}}}
        for qid, data in perf_db['questions'].items():
            if isinstance(data, dict):
                # Check if this is MLE-bench format (has failure_rate directly)
                if 'failure_rate' in data:
                    failure_rates[str(qid)] = data['failure_rate']
                else:
                    # MMLU-Pro format - compute from model results
                    correct_count = 0
                    total_count = 0
                    for model_name, result in data.items():
                        if isinstance(result, dict) and 'is_correct' in result:
                            total_count += 1
                            if result['is_correct']:
                                correct_count += 1

                    if total_count > 0:
                        failure_rate = 1.0 - (correct_count / total_count)
                        failure_rates[str(qid)] = failure_rate
    else:
        # Old format: {"qid": {"overall_stats": {...}}}
        for qid, perf in perf_db.items():
            if isinstance(perf, dict) and 'overall_stats' in perf:
                stats = perf['overall_stats']
                failure_rate = stats.get('failure_rate', stats.get('mean_failure_rate', 0.5))
                failure_rates[str(qid)] = failure_rate

    # Filter questions with performance data
    questions_with_perf = []
    for q in unified_db['questions']:
        qid = str(q['question_id'])
        if qid in failure_rates:
            questions_with_perf.append(q)

    print(f"  Total questions: {len(unified_db['questions'])}")
    print(f"  Questions with performance data: {len(questions_with_perf)}")

    return questions_with_perf, failure_rates


def stratified_kfold_split(questions: List[Dict], n_splits: int = 5, random_state: int = 42) -> List[Tuple[List[int], List[int]]]:
    """
    Create stratified k-fold splits based on domain/difficulty

    Returns list of (train_indices, test_indices) tuples
    """
    np.random.seed(random_state)

    # Group questions by domain
    domain_groups = defaultdict(list)
    for i, q in enumerate(questions):
        domain = q.get('domain', 'unknown')
        domain_groups[domain].append(i)

    # Shuffle each domain group
    for domain in domain_groups:
        np.random.shuffle(domain_groups[domain])

    # Create folds
    folds = [[] for _ in range(n_splits)]
    for domain, indices in domain_groups.items():
        # Distribute indices across folds
        for i, idx in enumerate(indices):
            fold_idx = i % n_splits
            folds[fold_idx].append(idx)

    # Create train/test splits
    splits = []
    for i in range(n_splits):
        test_indices = folds[i]
        train_indices = []
        for j in range(n_splits):
            if j != i:
                train_indices.extend(folds[j])
        splits.append((train_indices, test_indices))

    return splits


def evaluate_predictions(predictions: List[Dict], actuals: List[float]) -> Dict:
    """Compute evaluation metrics"""
    pred_rates = np.array([p['failure_rate'] for p in predictions])
    actual_rates = np.array(actuals)
    confidences = np.array([p['confidence'] for p in predictions])

    # MAE
    mae = np.mean(np.abs(pred_rates - actual_rates)) * 100

    # RMSE
    rmse = np.sqrt(np.mean((pred_rates - actual_rates) ** 2)) * 100

    # Correlation
    if len(pred_rates) > 1:
        correlation = np.corrcoef(pred_rates, actual_rates)[0, 1]
    else:
        correlation = 0.0

    # ECE (Expected Calibration Error)
    n_bins = 10
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (pred_rates >= bin_edges[i]) & (pred_rates < bin_edges[i + 1])
        if np.sum(mask) > 0:
            bin_pred = np.mean(pred_rates[mask])
            bin_actual = np.mean(actual_rates[mask])
            bin_weight = np.sum(mask) / len(pred_rates)
            ece += bin_weight * np.abs(bin_pred - bin_actual)

    return {
        'mae': mae,
        'rmse': rmse,
        'correlation': correlation,
        'ece': ece,
        'confidence': float(np.mean(confidences))
    }


def run_cv(questions: List[Dict], failure_rates: Dict[str, float],
           method: str = 'word_overlap', n_splits: int = 5) -> CVResults:
    """Run k-fold cross-validation"""

    print(f"\n{'='*80}")
    print(f"Running {n_splits}-Fold Cross-Validation: {method.upper()}")
    print(f"{'='*80}\n")

    # Create predictor
    if method == 'word_overlap':
        predictor_class = WordOverlapPredictor
    elif method == 'tfidf':
        predictor_class = TfidfPredictor
    else:
        raise ValueError(f"Unknown method: {method}")

    # Create splits
    splits = stratified_kfold_split(questions, n_splits=n_splits)

    # Store results for each fold
    mae_scores = []
    rmse_scores = []
    correlation_scores = []
    ece_scores = []
    confidence_scores = []

    for fold_idx, (train_indices, test_indices) in enumerate(splits):
        print(f"Fold {fold_idx + 1}/{n_splits}")
        print(f"  Train: {len(train_indices)} questions")
        print(f"  Test:  {len(test_indices)} questions")

        # Split data
        train_questions = [questions[i] for i in train_indices]
        test_questions = [questions[i] for i in test_indices]

        # Train predictor
        predictor = predictor_class()
        predictor.fit(train_questions, failure_rates)

        # Make predictions
        predictions = []
        actuals = []
        for q in test_questions:
            qid = str(q['question_id'])
            if qid in failure_rates:
                pred = predictor.predict(q.get('question_text', ''))
                predictions.append(pred)
                actuals.append(failure_rates[qid])

        # Evaluate
        metrics = evaluate_predictions(predictions, actuals)

        print(f"  MAE:         {metrics['mae']:.2f}%")
        print(f"  RMSE:        {metrics['rmse']:.2f}%")
        print(f"  Correlation: {metrics['correlation']:.3f}")
        print(f"  ECE:         {metrics['ece']:.3f}")
        print(f"  Confidence:  {metrics['confidence']:.3f}")
        print()

        mae_scores.append(metrics['mae'])
        rmse_scores.append(metrics['rmse'])
        correlation_scores.append(metrics['correlation'])
        ece_scores.append(metrics['ece'])
        confidence_scores.append(metrics['confidence'])

    return CVResults(
        method=method,
        mae_scores=mae_scores,
        rmse_scores=rmse_scores,
        correlation_scores=correlation_scores,
        ece_scores=ece_scores,
        confidence_scores=confidence_scores
    )


def print_cv_summary(results: CVResults):
    """Print summary of CV results with confidence intervals"""
    print(f"\n{'='*80}")
    print(f"CROSS-VALIDATION SUMMARY: {results.method.upper()}")
    print(f"{'='*80}\n")

    summary = results.get_summary()

    print("Metric          Mean ± Std        95% Confidence Interval")
    print("-" * 80)

    for metric_name, metric_data in summary.items():
        mean = metric_data['mean']
        std = metric_data['std']
        ci_low, ci_high = metric_data['ci_95']

        if metric_name in ['mae', 'rmse']:
            print(f"{metric_name.upper():15s} {mean:6.2f}% ± {std:5.2f}%    [{ci_low:6.2f}%, {ci_high:6.2f}%]")
        else:
            print(f"{metric_name.capitalize():15s} {mean:7.3f} ± {std:6.3f}    [{ci_low:7.3f}, {ci_high:7.3f}]")

    print()

    # Check if correlation is significantly different from zero
    corr_ci = summary['correlation']['ci_95']
    if corr_ci[0] > 0:
        print("✅ Correlation is SIGNIFICANTLY POSITIVE (95% CI > 0)")
    elif corr_ci[1] < 0:
        print("❌ Correlation is SIGNIFICANTLY NEGATIVE (95% CI < 0)")
    else:
        print("⚠️  Correlation NOT significantly different from zero (95% CI includes 0)")

    print()


def compare_methods(results1: CVResults, results2: CVResults):
    """Compare two methods statistically"""
    print(f"\n{'='*80}")
    print(f"STATISTICAL COMPARISON: {results1.method.upper()} vs {results2.method.upper()}")
    print(f"{'='*80}\n")

    metrics = ['mae', 'rmse', 'correlation', 'ece', 'confidence']

    for metric in metrics:
        scores1 = getattr(results1, f'{metric}_scores')
        scores2 = getattr(results2, f'{metric}_scores')

        # Paired t-test
        t_stat, p_value = stats.ttest_rel(scores1, scores2)

        mean1 = np.mean(scores1)
        mean2 = np.mean(scores2)
        diff = mean2 - mean1

        if metric in ['mae', 'rmse', 'ece']:
            improvement = -diff  # Lower is better
            better = "↓" if improvement > 0 else "↑"
        else:
            improvement = diff  # Higher is better
            better = "↑" if improvement > 0 else "↓"

        significance = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"

        print(f"{metric.upper():15s} {results1.method}: {mean1:7.3f}  →  {results2.method}: {mean2:7.3f}  "
              f"{better} {abs(improvement):7.3f} ({significance}, p={p_value:.4f})")

    print()
    print("Significance: *** p<0.001, ** p<0.01, * p<0.05, ns = not significant")
    print()


def main():
    parser = argparse.ArgumentParser(description='K-Fold CV for Failure Rate Predictor')
    parser.add_argument('--method', choices=['word_overlap', 'tfidf', 'both'],
                       default='both', help='Predictor method to evaluate')
    parser.add_argument('--n-splits', type=int, default=5,
                       help='Number of CV folds')
    parser.add_argument('--output', type=str, default='data/cv_results.json',
                       help='Output file for results')

    args = parser.parse_args()

    # Load data
    questions, failure_rates = load_data()

    print(f"\nDataset: {len(questions)} questions with performance data")
    print(f"Running {args.n_splits}-fold cross-validation")

    # Run CV
    results = {}

    if args.method in ['word_overlap', 'both']:
        results['word_overlap'] = run_cv(questions, failure_rates,
                                        method='word_overlap',
                                        n_splits=args.n_splits)
        print_cv_summary(results['word_overlap'])

    if args.method in ['tfidf', 'both']:
        results['tfidf'] = run_cv(questions, failure_rates,
                                 method='tfidf',
                                 n_splits=args.n_splits)
        print_cv_summary(results['tfidf'])

    # Compare if both methods run
    if len(results) == 2:
        compare_methods(results['word_overlap'], results['tfidf'])

    # Save results
    output = {
        method: {
            'summary': res.get_summary(),
            'raw_scores': {
                'mae': res.mae_scores,
                'rmse': res.rmse_scores,
                'correlation': res.correlation_scores,
                'ece': res.ece_scores,
                'confidence': res.confidence_scores
            }
        }
        for method, res in results.items()
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✅ Results saved to {output_path}")


if __name__ == '__main__':
    main()
