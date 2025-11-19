#!/usr/bin/env python3
"""
Meta-Learned Difficulty Predictor
==================================

Train a model to predict failure rate from question features using:
1. Extracted difficulty features (beyond semantic similarity)
2. Curriculum learning (train on easy questions first)
3. Gradient boosting for interpretable feature importance

This provides a complementary prediction to semantic similarity.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
import pickle

from difficulty_feature_extractor import DifficultyFeatureExtractor


class MetaDifficultyPredictor:
    """Predict failure rate from question features using meta-learning"""

    def __init__(self):
        self.feature_extractor = DifficultyFeatureExtractor()
        self.model = None
        self.feature_names = None
        self.is_trained = False

    def train_with_curriculum(
        self,
        questions: List[Dict],
        failure_rates: List[float],
        curriculum_stages: List[float] = [0.3, 0.6, 1.0],
        verbose: bool = True
    ):
        """
        Train with curriculum learning (easy to hard)

        Args:
            questions: List of question dicts
            failure_rates: Corresponding failure rates (0-100)
            curriculum_stages: Fraction of data to use at each stage
            verbose: Print progress
        """
        if verbose:
            print("\n" + "="*80)
            print("META-LEARNING WITH CURRICULUM")
            print("="*80)

        # Extract features
        if verbose:
            print("\n1. Extracting features...")

        X, self.feature_names = self.feature_extractor.extract_batch(questions)
        y = np.array(failure_rates)

        if verbose:
            print(f"   Features: {X.shape[1]}")
            print(f"   Questions: {X.shape[0]}")

        # Sort by difficulty (curriculum: easy to hard)
        difficulty_order = np.argsort(y)

        # Initialize model
        self.model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            verbose=0
        )

        # Progressive training (curriculum)
        if verbose:
            print(f"\n2. Curriculum learning with {len(curriculum_stages)} stages:")

        for stage_idx, fraction in enumerate(curriculum_stages, 1):
            n_samples = int(len(difficulty_order) * fraction)
            indices = difficulty_order[:n_samples]

            X_stage = X[indices]
            y_stage = y[indices]

            if verbose:
                print(f"\n   Stage {stage_idx}/{len(curriculum_stages)}: Training on {n_samples} questions ({fraction*100:.0f}%)")
                print(f"   Difficulty range: {y_stage.min():.1f}% - {y_stage.max():.1f}%")

            # Fit model
            self.model.fit(X_stage, y_stage)

            # Evaluate on this stage
            if verbose and len(X_stage) > 10:
                cv_scores = cross_val_score(
                    self.model, X_stage, y_stage,
                    cv=min(5, len(X_stage)//2),
                    scoring='neg_mean_absolute_error'
                )
                mae = -cv_scores.mean()
                print(f"   Cross-validation MAE: {mae:.2f}%")

        # Final evaluation on all data
        if verbose:
            print(f"\n3. Final model evaluation:")
            predictions = self.model.predict(X)
            mae = np.mean(np.abs(predictions - y))
            rmse = np.sqrt(np.mean((predictions - y) ** 2))
            corr = np.corrcoef(y, predictions)[0, 1]

            print(f"   MAE: {mae:.2f}%")
            print(f"   RMSE: {rmse:.2f}%")
            print(f"   Correlation: {corr:.3f}")

            # Feature importance
            print(f"\n4. Top 10 most important features:")
            importances = self.model.feature_importances_
            sorted_idx = np.argsort(importances)[::-1]

            for i in range(min(10, len(sorted_idx))):
                idx = sorted_idx[i]
                print(f"   {i+1}. {self.feature_names[idx]:<35} {importances[idx]:.3f}")

        self.is_trained = True

        return {
            'mae': mae,
            'rmse': rmse,
            'correlation': corr,
            'feature_importances': dict(zip(self.feature_names, importances))
        }

    def predict(self, question: Dict) -> Dict:
        """
        Predict failure rate for a question

        Returns:
            Dict with prediction, confidence, and feature contributions
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train_with_curriculum() first.")

        # Extract features
        features = self.feature_extractor.extract_features(question)

        # Convert to array in correct order
        X = np.array([features.get(name, 0.0) for name in self.feature_names]).reshape(1, -1)

        # Predict
        prediction = self.model.predict(X)[0]

        # Estimate confidence based on feature values
        # (questions similar to training data have higher confidence)
        confidence = self._estimate_confidence(X)

        # Feature contributions (approximate with feature * importance)
        contributions = {}
        for i, name in enumerate(self.feature_names):
            importance = self.model.feature_importances_[i]
            value = X[0, i]
            if importance > 0.01:  # Only significant features
                contributions[name] = {
                    'value': value,
                    'importance': importance,
                    'contribution': value * importance
                }

        # Top contributing features
        top_contributors = sorted(
            contributions.items(),
            key=lambda x: abs(x[1]['contribution']),
            reverse=True
        )[:5]

        return {
            'predicted_failure_rate': max(0, min(100, prediction)),  # Clip to [0, 100]
            'confidence': confidence,
            'top_contributing_features': [
                {'name': name, **data} for name, data in top_contributors
            ],
            'method': 'meta_learned_features'
        }

    def _estimate_confidence(self, X: np.ndarray) -> float:
        """
        Estimate confidence based on how similar features are to training data

        Simple heuristic: use ensemble variance from multiple predictions
        """
        # For GradientBoosting, we can use the variance of tree predictions
        # as a proxy for uncertainty
        # (not directly available, so we use a simplified confidence metric)

        # Confidence based on feature magnitudes (normalized)
        # Features far from typical values → lower confidence
        feature_stds = np.std(X, axis=1)
        confidence = 1.0 / (1.0 + feature_stds[0])

        return float(np.clip(confidence, 0.3, 0.95))

    def save(self, path: str):
        """Save trained model"""
        if not self.is_trained:
            raise ValueError("Model not trained")

        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names,
                'feature_extractor': self.feature_extractor
            }, f)

        print(f"✅ Model saved to {path}")

    def load(self, path: str):
        """Load trained model"""
        with open(path, 'rb') as f:
            data = pickle.load(f)

        self.model = data['model']
        self.feature_names = data['feature_names']
        self.feature_extractor = data['feature_extractor']
        self.is_trained = True

        print(f"✅ Model loaded from {path}")


def train_meta_predictor(
    questions_db_path: str = "./data/unified_database_with_mmlu_pro.json",
    performance_db_path: str = "./data/model_performance_database.json",
    output_path: str = "./models/meta_difficulty_predictor.pkl"
):
    """
    Train meta-difficulty predictor on all available data

    Returns:
        Trained MetaDifficultyPredictor
    """
    print("="*80)
    print("TRAINING META-DIFFICULTY PREDICTOR")
    print("="*80)

    # Load data
    print("\n1. Loading data...")
    with open(questions_db_path, 'r') as f:
        questions_data = json.load(f)
    all_questions = questions_data['questions']

    with open(performance_db_path, 'r') as f:
        perf_data = json.load(f)
    performance_data = perf_data['questions']

    print(f"   Total questions: {len(all_questions):,}")
    print(f"   Questions with performance data: {len(performance_data)}")

    # Match questions with performance data
    print("\n2. Matching questions with performance data...")
    training_questions = []
    training_failure_rates = []

    for q in all_questions:
        qid = q['question_id']

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

        if perf_id:
            perf = performance_data[perf_id]

            # Calculate failure rate
            total = len(perf)
            correct = sum(1 for result in perf.values() if result.get('is_correct'))
            failure_rate = (total - correct) / total * 100 if total > 0 else None

            if failure_rate is not None:
                training_questions.append(q)
                training_failure_rates.append(failure_rate)

    print(f"   Matched questions: {len(training_questions)}")

    # Train predictor
    print("\n3. Training meta-predictor with curriculum learning...")
    predictor = MetaDifficultyPredictor()

    metrics = predictor.train_with_curriculum(
        questions=training_questions,
        failure_rates=training_failure_rates,
        curriculum_stages=[0.3, 0.6, 1.0],
        verbose=True
    )

    # Save model
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    predictor.save(output_path)

    print("\n" + "="*80)
    print("✅ Training complete!")
    print("="*80)

    return predictor, metrics


if __name__ == "__main__":
    # Train the meta-predictor
    predictor, metrics = train_meta_predictor()

    # Test on sample questions
    print("\n" + "="*80)
    print("TESTING META-PREDICTOR")
    print("="*80)

    test_questions = [
        {
            'question_text': 'What is 2+2?',
            'domain': 'math',
            'options': ['1', '2', '3', '4']
        },
        {
            'question_text': 'Prove that the eigenvalues of a Hermitian matrix are real.',
            'domain': 'math',
            'options': []
        },
        {
            'question_text': 'Given T_i = 35°C and P = 2.5×10^6 Pa, calculate the final entropy change when 200 kg of water undergoes an isothermal expansion.',
            'domain': 'physics',
            'options': []
        },
    ]

    for i, q in enumerate(test_questions, 1):
        print(f"\n{'='*40}")
        print(f"TEST {i}")
        print(f"{'='*40}")
        print(f"\nQuestion: {q['question_text'][:80]}...")

        result = predictor.predict(q)

        print(f"\n📊 PREDICTION:")
        print(f"   Failure rate: {result['predicted_failure_rate']:.1f}%")
        print(f"   Confidence: {result['confidence']:.2f}")

        print(f"\n🔑 TOP CONTRIBUTING FEATURES:")
        for feat in result['top_contributing_features']:
            print(f"   {feat['name']:<30} value={feat['value']:>6.2f}, imp={feat['importance']:.3f}")

    print("\n" + "="*80)
    print("✅ All tests complete!")
    print("="*80)
