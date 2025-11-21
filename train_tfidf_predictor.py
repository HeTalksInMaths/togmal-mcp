#!/usr/bin/env python3
"""
Train Phase 1 Predictor with TF-IDF Embeddings (No HuggingFace Required!)
==========================================================================

Uses sklearn's TfidfVectorizer for semantic similarity instead of HuggingFace.
Works offline, no downloads required, already installed.

Expected to significantly improve over word overlap.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
import scipy.optimize as optimize

# Use sklearn's TF-IDF (already installed!)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class PredictionResult:
    """Result of a failure rate prediction"""
    failure_rate: float
    confidence: float
    epistemic_uncertainty: float
    aleatoric_uncertainty: float
    n_similar: int
    similar_questions: List[str]


class TfidfFailureRatePredictor:
    """
    Improved Predictor with TF-IDF Embeddings

    Uses sklearn's TfidfVectorizer for document similarity.
    Better than word overlap, no external downloads needed.
    """

    def __init__(self, use_weighted_similarity: bool = True,
                 use_temperature_scaling: bool = True):
        self.use_weighted_similarity = use_weighted_similarity
        self.use_temperature_scaling = use_temperature_scaling
        self.temperature = 1.0

        # TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=1000,  # Top 1000 terms
            ngram_range=(1, 2),  # Unigrams and bigrams
            min_df=1,  # Minimum document frequency
            stop_words='english'  # Remove common words
        )

        # Will be populated during training
        self.training_questions = []
        self.training_vectors = None  # TF-IDF matrix
        self.failure_rates = {}

    def fit_vectorizer(self, texts: List[str]):
        """Fit TF-IDF vectorizer on training texts"""
        print(f"  Fitting TF-IDF vectorizer on {len(texts)} questions...")
        self.training_vectors = self.vectorizer.fit_transform(texts)
        print(f"  ✅ Vectorizer fitted ({self.training_vectors.shape[1]} features)")

    def compute_tfidf_similarity(self, query_text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Compute TF-IDF similarity between query and all training questions

        Returns: List of (question_id, similarity_score) tuples
        """
        # Transform query
        query_vector = self.vectorizer.transform([query_text])

        # Compute cosine similarity with all training vectors
        similarities = cosine_similarity(query_vector, self.training_vectors)[0]

        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            qid = str(self.training_questions[idx]['question_id'])
            sim = similarities[idx]
            results.append((qid, float(sim)))

        return results

    def find_similar_questions(self, query_text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Find most similar questions using TF-IDF"""
        return self.compute_tfidf_similarity(query_text, top_k)

    def predict_failure_rate(self, query_text: str, top_k: int = 10) -> PredictionResult:
        """
        Predict failure rate using TF-IDF similarity-weighted aggregation
        """

        # Find similar questions
        similar = self.find_similar_questions(query_text, top_k=top_k)

        if not similar or all(sim == 0 for _, sim in similar):
            # No similar questions found
            return PredictionResult(
                failure_rate=0.5,
                confidence=0.0,
                epistemic_uncertainty=1.0,
                aleatoric_uncertainty=0.0,
                n_similar=0,
                similar_questions=[]
            )

        # Aggregate failure rates
        if self.use_weighted_similarity:
            # Weighted by similarity scores
            total_weight = 0.0
            weighted_failure = 0.0

            for qid, sim_score in similar:
                if qid in self.failure_rates and sim_score > 0:
                    fr = self.failure_rates[qid]
                    weighted_failure += sim_score * fr
                    total_weight += sim_score

            if total_weight > 0:
                predicted_fr = weighted_failure / total_weight
            else:
                predicted_fr = 0.5
        else:
            # Simple average (baseline)
            valid_frs = [self.failure_rates[qid] for qid, _ in similar
                        if qid in self.failure_rates]
            predicted_fr = np.mean(valid_frs) if valid_frs else 0.5

        # Apply temperature scaling
        if self.use_temperature_scaling and self.temperature != 1.0:
            predicted_fr = self._apply_temperature(predicted_fr, self.temperature)

        # Compute uncertainties
        sim_scores = [s for _, s in similar]
        mean_similarity = np.mean(sim_scores) if sim_scores else 0.0

        # Epistemic uncertainty: low similarity = high uncertainty
        epistemic_uncertainty = 1.0 - mean_similarity

        # Aleatoric uncertainty: variance in similar questions' failure rates
        valid_frs = [self.failure_rates[qid] for qid, _ in similar
                    if qid in self.failure_rates]
        aleatoric_uncertainty = np.std(valid_frs) if len(valid_frs) > 1 else 0.5

        # Overall confidence
        confidence = 1.0 - epistemic_uncertainty

        return PredictionResult(
            failure_rate=predicted_fr,
            confidence=confidence,
            epistemic_uncertainty=epistemic_uncertainty,
            aleatoric_uncertainty=aleatoric_uncertainty,
            n_similar=len(similar),
            similar_questions=[qid for qid, _ in similar[:5]]
        )

    def _apply_temperature(self, probability: float, temperature: float) -> float:
        """Apply temperature scaling to probability"""
        # Clamp to avoid numerical issues
        p = np.clip(probability, 1e-7, 1.0 - 1e-7)

        # Logit transform
        logit = np.log(p / (1 - p))

        # Scale by temperature
        scaled_logit = logit / temperature

        # Back to probability
        scaled_p = 1 / (1 + np.exp(-scaled_logit))

        return scaled_p

    def learn_temperature(self, val_questions: List[Dict], val_failure_rates: Dict[str, float]):
        """Learn optimal temperature on validation set"""

        def calibration_error(T):
            """Compute ECE for given temperature"""
            predictions = []
            actuals = []

            for q in val_questions:
                qid = str(q['question_id'])
                if qid not in val_failure_rates:
                    continue

                # Predict
                result = self.predict_failure_rate(q.get('question_text', ''))
                pred_fr = self._apply_temperature(result.failure_rate, T[0])

                predictions.append(pred_fr)
                actuals.append(val_failure_rates[qid])

            if not predictions:
                return 1.0

            # Compute ECE
            ece = self._compute_ece(np.array(predictions), np.array(actuals))
            return ece

        # Optimize temperature
        result = optimize.minimize(
            calibration_error,
            x0=[1.0],
            bounds=[(0.1, 5.0)],
            method='L-BFGS-B'
        )

        self.temperature = result.x[0]
        print(f"  Learned temperature: T = {self.temperature:.3f}")

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


class TfidfDatasetTrainer:
    """Train and validate predictor with TF-IDF embeddings"""

    def __init__(self):
        self.data_dir = Path("./data")

        # Load data
        print("Loading expanded dataset...")
        self.unified_db = self._load_unified_db()
        self.performance_db = self._load_performance_db()

        print(f"  Unified DB: {len(self.unified_db['questions']):,} questions")
        print(f"  Performance DB: {len(self.performance_db['questions'])} questions")

    def _load_unified_db(self) -> Dict:
        """Load unified question database"""
        path = self.data_dir / "unified_database_with_real_mle.json"
        with open(path) as f:
            return json.load(f)

    def _load_performance_db(self) -> Dict:
        """Load model performance database"""
        path = self.data_dir / "model_performance_database.json"
        with open(path) as f:
            return json.load(f)

    def compute_aggregate_failure_rates(self) -> Dict[str, float]:
        """Compute aggregate failure rate for each question"""
        failure_rates = {}

        for qid, perf_data in self.performance_db['questions'].items():
            # Handle both old format (per-model) and new format (aggregated)
            if 'failure_rate' in perf_data:
                # New format (from MLE-bench)
                failure_rates[str(qid)] = perf_data['failure_rate']
            else:
                # Old format (per-model results)
                model_results = []
                for model_name, model_data in perf_data.items():
                    if isinstance(model_data, dict) and 'is_correct' in model_data:
                        is_correct = model_data['is_correct']
                        model_results.append(0.0 if is_correct else 1.0)

                if model_results:
                    failure_rates[str(qid)] = np.mean(model_results)

        return failure_rates

    def split_data(self, test_ratio: float = 0.2, val_ratio: float = 0.1,
                   seed: int = 42) -> Tuple[List, List, List]:
        """Split data into train/val/test"""

        np.random.seed(seed)

        # Get all questions with performance data
        questions_with_perf = []
        failure_rates = self.compute_aggregate_failure_rates()

        for q in self.unified_db['questions']:
            qid = str(q['question_id'])
            if qid in failure_rates:
                questions_with_perf.append(q)
            elif q['question_id'] in failure_rates:
                questions_with_perf.append(q)

        print(f"\n  Questions with performance data: {len(questions_with_perf)}")
        print(f"  Available failure rates: {len(failure_rates)}")

        # Shuffle
        indices = np.random.permutation(len(questions_with_perf))

        # Split
        n_test = int(len(questions_with_perf) * test_ratio)
        n_val = int(len(questions_with_perf) * val_ratio)

        test_indices = indices[:n_test]
        val_indices = indices[n_test:n_test + n_val]
        train_indices = indices[n_test + n_val:]

        train_questions = [questions_with_perf[i] for i in train_indices]
        val_questions = [questions_with_perf[i] for i in val_indices]
        test_questions = [questions_with_perf[i] for i in test_indices]

        print(f"  Train: {len(train_questions)}")
        print(f"  Val:   {len(val_questions)}")
        print(f"  Test:  {len(test_questions)}")

        return train_questions, val_questions, test_questions

    def train_predictor(self, train_questions: List[Dict], val_questions: List[Dict],
                       use_weighted: bool = True, use_temperature: bool = True) -> TfidfFailureRatePredictor:
        """Train predictor on training set"""

        print(f"\nTraining TF-IDF predictor...")
        print(f"  Weighted similarity: {use_weighted}")
        print(f"  Temperature scaling: {use_temperature}")

        predictor = TfidfFailureRatePredictor(
            use_weighted_similarity=use_weighted,
            use_temperature_scaling=use_temperature
        )

        # Set training data
        predictor.training_questions = train_questions

        # Fit TF-IDF vectorizer
        train_texts = [q.get('question_text', '') for q in train_questions]
        predictor.fit_vectorizer(train_texts)

        # Compute failure rates
        failure_rates = self.compute_aggregate_failure_rates()
        predictor.failure_rates = {str(q['question_id']): failure_rates[str(q['question_id'])]
                                  for q in train_questions
                                  if str(q['question_id']) in failure_rates}

        # Learn temperature on validation set
        if use_temperature and val_questions:
            val_failure_rates = {str(q['question_id']): failure_rates[str(q['question_id'])]
                                for q in val_questions
                                if str(q['question_id']) in failure_rates}
            predictor.learn_temperature(val_questions, val_failure_rates)

        return predictor

    def evaluate_predictor(self, predictor: TfidfFailureRatePredictor,
                          test_questions: List[Dict]) -> Dict:
        """Evaluate predictor on test set"""

        print(f"\nEvaluating on test set ({len(test_questions)} questions)...")

        failure_rates = self.compute_aggregate_failure_rates()

        predictions = []
        actuals = []
        confidences = []

        for q in test_questions:
            qid = str(q['question_id'])
            if qid not in failure_rates:
                continue

            # Predict
            result = predictor.predict_failure_rate(q.get('question_text', ''))

            predictions.append(result.failure_rate)
            actuals.append(failure_rates[qid])
            confidences.append(result.confidence)

        predictions = np.array(predictions)
        actuals = np.array(actuals)

        # Compute metrics
        mae = np.mean(np.abs(predictions - actuals)) * 100
        rmse = np.sqrt(np.mean((predictions - actuals) ** 2)) * 100

        # Correlation
        if len(predictions) > 1:
            correlation = np.corrcoef(predictions, actuals)[0, 1]
        else:
            correlation = 0.0

        # ECE
        ece = self._compute_ece(predictions, actuals)

        metrics = {
            'mae': mae,
            'rmse': rmse,
            'correlation': correlation,
            'ece': ece,
            'n_test': len(predictions),
            'mean_confidence': np.mean(confidences)
        }

        print(f"\n  Metrics:")
        print(f"    MAE:         {mae:.2f}%")
        print(f"    RMSE:        {rmse:.2f}%")
        print(f"    Correlation: {correlation:.3f}")
        print(f"    ECE:         {ece:.3f}")
        print(f"    Confidence:  {np.mean(confidences):.3f}")

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

    def run_full_training(self):
        """Run complete training and evaluation"""

        print("="*80)
        print("TRAINING WITH TF-IDF EMBEDDINGS (252-QUESTION DATASET)")
        print("="*80)

        # Split data
        train, val, test = self.split_data()

        # Train TF-IDF predictor
        print("\n" + "-"*80)
        print("1. TF-IDF PREDICTOR (Weighted + Temperature)")
        print("-"*80)
        tfidf_predictor = self.train_predictor(
            train, val,
            use_weighted=True,
            use_temperature=True
        )
        tfidf_metrics = self.evaluate_predictor(tfidf_predictor, test)

        # Load previous word-overlap results for comparison
        try:
            with open(self.data_dir / "expanded_training_results.json") as f:
                previous_results = json.load(f)
                word_overlap_metrics = previous_results['improved_metrics']
                print("\n" + "-"*80)
                print("2. WORD OVERLAP BASELINE (Previous Results)")
                print("-"*80)
                print(f"  (Loaded from previous run)")
                print(f"\n  Metrics:")
                print(f"    MAE:         {word_overlap_metrics['mae']:.2f}%")
                print(f"    RMSE:        {word_overlap_metrics['rmse']:.2f}%")
                print(f"    Correlation: {word_overlap_metrics['correlation']:.3f}")
                print(f"    ECE:         {word_overlap_metrics['ece']:.3f}")
        except:
            word_overlap_metrics = None
            print("\n  (No previous results found)")

        # Compare
        print("\n" + "="*80)
        print("COMPARISON: TF-IDF vs WORD OVERLAP")
        print("="*80)

        if word_overlap_metrics:
            print("\n| Metric | Word Overlap | TF-IDF | Improvement |")
            print("|--------|-------------|--------|-------------|")

            for metric in ['mae', 'rmse', 'correlation', 'ece']:
                word_val = word_overlap_metrics[metric]
                tfidf_val = tfidf_metrics[metric]

                if metric in ['mae', 'rmse', 'ece']:
                    # Lower is better
                    if word_val != 0:
                        improvement = (word_val - tfidf_val) / word_val * 100
                    else:
                        improvement = 0
                    change_str = f"-{improvement:.1f}%" if improvement > 0 else f"+{abs(improvement):.1f}%"
                else:
                    # Higher is better (correlation)
                    if word_val != 0:
                        improvement = (tfidf_val - word_val) / abs(word_val) * 100
                    else:
                        improvement = float('inf') if tfidf_val > 0 else 0
                    change_str = f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"

                if metric in ['mae', 'rmse']:
                    print(f"| {metric.upper():<6} | {word_val:>11.2f}% | {tfidf_val:>6.2f}% | {change_str:>11} |")
                else:
                    print(f"| {metric.upper():<6} | {word_val:>11.3f}  | {tfidf_val:>6.3f}  | {change_str:>11} |")

            # Check if correlation is positive now
            if tfidf_metrics['correlation'] > 0 and word_overlap_metrics['correlation'] < 0:
                print(f"\n  🎉 CORRELATION FIXED: {word_overlap_metrics['correlation']:.3f} → {tfidf_metrics['correlation']:.3f} (POSITIVE!)")
            elif tfidf_metrics['correlation'] > word_overlap_metrics['correlation']:
                print(f"\n  ✅ Correlation improved: {word_overlap_metrics['correlation']:.3f} → {tfidf_metrics['correlation']:.3f}")

        # Save results
        results = {
            'dataset_size': len(self.performance_db['questions']),
            'train_size': len(train),
            'val_size': len(val),
            'test_size': len(test),
            'tfidf_metrics': tfidf_metrics,
            'word_overlap_metrics': word_overlap_metrics,
            'temperature': tfidf_predictor.temperature,
            'embedding_method': 'TF-IDF (sklearn)',
        }

        results_path = self.data_dir / "tfidf_training_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 Results saved to: {results_path}")

        return results


def main():
    """Main training workflow"""

    trainer = TfidfDatasetTrainer()
    results = trainer.run_full_training()

    print("\n" + "="*80)
    print("✅ TF-IDF TRAINING COMPLETE!")
    print("="*80)

    print("\n📊 KEY FINDINGS:")
    tfidf = results['tfidf_metrics']
    word_overlap = results.get('word_overlap_metrics')

    if word_overlap:
        correlation_change = tfidf['correlation'] - word_overlap['correlation']
        mae_change = (word_overlap['mae'] - tfidf['mae']) / word_overlap['mae'] * 100

        print(f"  • Correlation: {word_overlap['correlation']:.3f} → {tfidf['correlation']:.3f} ({correlation_change:+.3f})")
        print(f"  • MAE: {word_overlap['mae']:.2f}% → {tfidf['mae']:.2f}% ({mae_change:+.1f}%)")
        print(f"  • Confidence: {word_overlap['mean_confidence']:.3f} → {tfidf['mean_confidence']:.3f}")

        if tfidf['correlation'] > 0:
            print(f"\n  🎉 SUCCESS: Correlation is POSITIVE!")
        else:
            print(f"\n  ⚠️  Correlation still negative but improved")
    else:
        print(f"  • Correlation: {tfidf['correlation']:.3f}")
        print(f"  • MAE: {tfidf['mae']:.2f}%")
        print(f"  • Confidence: {tfidf['mean_confidence']:.3f}")

    print(f"  • Dataset size: {results['dataset_size']} questions")
    print(f"  • Embedding method: TF-IDF (sklearn, no downloads needed!)")

    return results


if __name__ == "__main__":
    main()
