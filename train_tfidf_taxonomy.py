#!/usr/bin/env python3
"""
Train Predictor Using Full 13k Taxonomy for Similarity Matching
================================================================

CORRECT APPROACH:
- Use ALL 13,252 questions for TF-IDF vectorization (rich semantic space)
- Only use 252 questions with known failure rates for training/validation
- Prediction: Find similar questions in 13k taxonomy → weight by failure rates from 252

This is k-NN with large feature space - much more powerful than only using 252!
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class PredictionResult:
    """Result of a failure rate prediction"""
    failure_rate: float
    confidence: float
    n_similar: int
    similar_questions: List[Tuple[str, float]]  # (qid, similarity)


class TaxonomyBasedPredictor:
    """
    Predictor that uses full taxonomy for similarity matching

    Design:
    1. Fit TF-IDF on ALL 13k questions (rich semantic space)
    2. Store failure rates for 252 known questions
    3. Predict: Find k-NN in 13k → aggregate failure rates from known questions
    """

    def __init__(self, max_features: int = 2000):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            min_df=1,
            stop_words='english'
        )

        # Full taxonomy (13k questions)
        self.taxonomy_questions = []
        self.taxonomy_vectors = None

        # Known failure rates (252 questions)
        self.failure_rates = {}

    def fit_taxonomy(self, all_questions: List[Dict]):
        """Fit TF-IDF on FULL taxonomy (13k questions)"""
        print(f"  Fitting TF-IDF on {len(all_questions):,} questions in taxonomy...")

        self.taxonomy_questions = all_questions
        texts = [q.get('question_text', '') for q in all_questions]

        self.taxonomy_vectors = self.vectorizer.fit_transform(texts)

        print(f"  ✅ Taxonomy indexed: {self.taxonomy_vectors.shape[0]:,} questions")
        print(f"  ✅ TF-IDF features: {self.taxonomy_vectors.shape[1]:,} terms")

    def set_failure_rates(self, failure_rates: Dict[str, float]):
        """Set known failure rates (252 questions)"""
        self.failure_rates = failure_rates
        print(f"  Known failure rates: {len(failure_rates)} questions")

    def predict(self, query_text: str, top_k: int = 20) -> PredictionResult:
        """
        Predict failure rate using taxonomy-based k-NN

        Process:
        1. Find k most similar questions in 13k taxonomy
        2. Filter to only those with known failure rates (from 252)
        3. Weighted average by similarity
        """

        # Transform query
        query_vector = self.vectorizer.transform([query_text])

        # Find similar in FULL taxonomy
        similarities = cosine_similarity(query_vector, self.taxonomy_vectors)[0]

        # Get top-k most similar
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Collect similar questions with known failure rates
        similar_with_rates = []
        for idx in top_indices:
            qid = str(self.taxonomy_questions[idx]['question_id'])
            sim = similarities[idx]

            # Only include if we have failure rate
            if qid in self.failure_rates:
                similar_with_rates.append((qid, sim, self.failure_rates[qid]))

        if not similar_with_rates:
            return PredictionResult(
                failure_rate=0.5,
                confidence=0.0,
                n_similar=0,
                similar_questions=[]
            )

        # Weighted average by similarity
        total_weight = sum(sim for _, sim, _ in similar_with_rates)

        if total_weight > 0:
            weighted_sum = sum(sim * fr for _, sim, fr in similar_with_rates)
            failure_rate = weighted_sum / total_weight
            confidence = total_weight / len(similar_with_rates)
        else:
            failure_rate = 0.5
            confidence = 0.0

        return PredictionResult(
            failure_rate=failure_rate,
            confidence=confidence,
            n_similar=len(similar_with_rates),
            similar_questions=[(qid, sim) for qid, sim, _ in similar_with_rates[:5]]
        )


class TaxonomyTrainer:
    """Train and evaluate taxonomy-based predictor"""

    def __init__(self):
        self.data_dir = Path("./data")

        print("Loading data...")
        self.unified_db = self._load_unified_db()
        self.performance_db = self._load_performance_db()

        print(f"  Taxonomy: {len(self.unified_db['questions']):,} questions")
        print(f"  Performance DB: {len(self.performance_db['questions'])} questions")

    def _load_unified_db(self) -> Dict:
        """Load unified question database (13k taxonomy)"""
        path = self.data_dir / "unified_database_with_real_mle.json"
        with open(path) as f:
            return json.load(f)

    def _load_performance_db(self) -> Dict:
        """Load model performance database (252 questions)"""
        path = self.data_dir / "model_performance_database.json"
        with open(path) as f:
            return json.load(f)

    def compute_failure_rates(self) -> Dict[str, float]:
        """Compute failure rates for questions with performance data"""
        failure_rates = {}

        for qid, data in self.performance_db['questions'].items():
            if isinstance(data, dict):
                # MLE-bench format: has failure_rate directly
                if 'failure_rate' in data:
                    failure_rates[str(qid)] = data['failure_rate']
                else:
                    # MMLU-Pro format: compute from model results
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

        return failure_rates

    def split_known_questions(self, failure_rates: Dict[str, float],
                              test_ratio: float = 0.2, seed: int = 42):
        """Split the 252 known questions into train/test"""
        np.random.seed(seed)

        # Get questions with known failure rates
        known_ids = list(failure_rates.keys())

        # Find corresponding questions in taxonomy
        known_questions = []
        for q in self.unified_db['questions']:
            if str(q['question_id']) in failure_rates:
                known_questions.append(q)

        print(f"\n  Questions with known failure rates: {len(known_questions)}")

        # Split
        indices = np.random.permutation(len(known_questions))
        n_test = int(len(known_questions) * test_ratio)

        test_indices = indices[:n_test]
        train_indices = indices[n_test:]

        train_questions = [known_questions[i] for i in train_indices]
        test_questions = [known_questions[i] for i in test_indices]

        print(f"  Train: {len(train_questions)} (for failure rate lookup)")
        print(f"  Test:  {len(test_questions)} (held-out evaluation)")

        return train_questions, test_questions

    def train_predictor(self, train_questions: List[Dict],
                       failure_rates: Dict[str, float]) -> TaxonomyBasedPredictor:
        """
        Train predictor

        Key: Fit TF-IDF on FULL taxonomy, but only use training failure rates
        """
        print(f"\nTraining taxonomy-based predictor...")

        predictor = TaxonomyBasedPredictor(max_features=2000)

        # Fit on FULL taxonomy (13k questions)
        predictor.fit_taxonomy(self.unified_db['questions'])

        # Set failure rates only for training questions
        train_failure_rates = {
            str(q['question_id']): failure_rates[str(q['question_id'])]
            for q in train_questions
            if str(q['question_id']) in failure_rates
        }
        predictor.set_failure_rates(train_failure_rates)

        return predictor

    def evaluate(self, predictor: TaxonomyBasedPredictor,
                test_questions: List[Dict],
                failure_rates: Dict[str, float]) -> Dict:
        """Evaluate predictor on held-out test set"""

        print(f"\nEvaluating on {len(test_questions)} test questions...")

        predictions = []
        actuals = []
        confidences = []
        n_similar_counts = []

        for q in test_questions:
            qid = str(q['question_id'])
            if qid not in failure_rates:
                continue

            # Predict
            result = predictor.predict(q.get('question_text', ''))

            predictions.append(result.failure_rate)
            actuals.append(failure_rates[qid])
            confidences.append(result.confidence)
            n_similar_counts.append(result.n_similar)

        predictions = np.array(predictions)
        actuals = np.array(actuals)

        # Metrics
        mae = np.mean(np.abs(predictions - actuals)) * 100
        rmse = np.sqrt(np.mean((predictions - actuals) ** 2)) * 100
        correlation = np.corrcoef(predictions, actuals)[0, 1] if len(predictions) > 1 else 0.0

        # ECE
        ece = self._compute_ece(predictions, actuals)

        metrics = {
            'mae': mae,
            'rmse': rmse,
            'correlation': correlation,
            'ece': ece,
            'mean_confidence': float(np.mean(confidences)),
            'mean_n_similar': float(np.mean(n_similar_counts)),
            'n_test': len(predictions)
        }

        print(f"\n  Results:")
        print(f"    MAE:         {mae:.2f}%")
        print(f"    RMSE:        {rmse:.2f}%")
        print(f"    Correlation: {correlation:.3f}")
        print(f"    ECE:         {ece:.3f}")
        print(f"    Confidence:  {np.mean(confidences):.3f}")
        print(f"    Avg similar: {np.mean(n_similar_counts):.1f} questions with known rates")

        return metrics

    def _compute_ece(self, predictions: np.ndarray, actuals: np.ndarray, n_bins: int = 10) -> float:
        """Compute Expected Calibration Error"""
        ece = 0.0
        for i in range(n_bins):
            bin_lower = i / n_bins
            bin_upper = (i + 1) / n_bins
            in_bin = (predictions >= bin_lower) & (predictions < bin_upper)
            if np.sum(in_bin) > 0:
                bin_pred = np.mean(predictions[in_bin])
                bin_actual = np.mean(actuals[in_bin])
                bin_size = np.sum(in_bin) / len(predictions)
                ece += bin_size * abs(bin_pred - bin_actual)
        return ece

    def run_full_pipeline(self):
        """Run complete training and evaluation"""

        print("="*80)
        print("TAXONOMY-BASED PREDICTOR (13k taxonomy + 252 known rates)")
        print("="*80)

        # Get failure rates
        failure_rates = self.compute_failure_rates()
        print(f"\n  Total failure rates available: {len(failure_rates)}")

        # Split known questions
        train_questions, test_questions = self.split_known_questions(failure_rates)

        # Train predictor
        predictor = self.train_predictor(train_questions, failure_rates)

        # Evaluate
        metrics = self.evaluate(predictor, test_questions, failure_rates)

        # Compare to previous CV results
        print("\n" + "="*80)
        print("COMPARISON TO PREVIOUS APPROACH")
        print("="*80)

        try:
            with open(self.data_dir / "cv_results.json") as f:
                cv_results = json.load(f)

            # Previous approach: trained on ~200, matched against same 200
            prev_correlation = cv_results['word_overlap']['summary']['correlation']['mean']
            prev_mae = cv_results['word_overlap']['summary']['mae']['mean']

            print("\n| Approach | Correlation | MAE | Similarity Space |")
            print("|----------|-------------|-----|------------------|")
            print(f"| Previous (CV) | {prev_correlation:.3f} | {prev_mae:.1f}% | 200 questions |")
            print(f"| Taxonomy | {metrics['correlation']:.3f} | {metrics['mae']:.1f}% | 13,252 questions |")

            corr_change = metrics['correlation'] - prev_correlation
            mae_change = prev_mae - metrics['mae']

            print(f"\n  Correlation change: {corr_change:+.3f}")
            print(f"  MAE change: {mae_change:+.1f}% ({'better' if mae_change > 0 else 'worse'})")

            if metrics['correlation'] > prev_correlation:
                print(f"\n  ✅ Using full taxonomy IMPROVES correlation!")

        except Exception as e:
            print(f"\n  (Could not load previous results: {e})")

        # Save results
        results = {
            'approach': 'taxonomy_based',
            'taxonomy_size': len(self.unified_db['questions']),
            'known_failure_rates': len(failure_rates),
            'train_size': len(train_questions),
            'test_size': len(test_questions),
            'metrics': metrics,
            'tfidf_features': predictor.taxonomy_vectors.shape[1]
        }

        results_path = self.data_dir / "taxonomy_predictor_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 Results saved to: {results_path}")

        return results


def main():
    """Main training workflow"""

    trainer = TaxonomyTrainer()
    results = trainer.run_full_pipeline()

    print("\n" + "="*80)
    print("✅ TAXONOMY-BASED TRAINING COMPLETE!")
    print("="*80)

    print("\n📊 KEY FINDINGS:")
    print(f"  • Taxonomy size: {results['taxonomy_size']:,} questions")
    print(f"  • Known failure rates: {results['known_failure_rates']} questions")
    print(f"  • Correlation: {results['metrics']['correlation']:.3f}")
    print(f"  • MAE: {results['metrics']['mae']:.2f}%")
    print(f"  • Avg similar questions found: {results['metrics']['mean_n_similar']:.1f}")

    print(f"\n  💡 Key advantage: Rich semantic space from {results['taxonomy_size']:,} questions")
    print(f"     vs previous approach using only ~200 questions")

    return results


if __name__ == "__main__":
    main()
