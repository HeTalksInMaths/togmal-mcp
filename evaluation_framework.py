#!/usr/bin/env python3
"""
Evaluation Framework for Lightweight Checker and Taxonomy Scoring
==================================================================

Creates train/test/val splits from holdout benchmarks and tunes hyperparameters
to minimize loss (classification error, calibration error, etc.).

Approach:
1. Use real benchmark data (MMLU-Pro + DS-1000) with model outputs as ground truth
2. Create stratified train/test/val splits (70/15/15) by domain
3. Tune hyperparameters on train set
4. Validate on val set
5. Final evaluation on test set
6. Metrics: Accuracy, F1, calibration error, Brier score
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from collections import defaultdict, Counter
from dataclasses import dataclass
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Metrics for evaluating checker/taxonomy performance"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    calibration_error: float  # Expected Calibration Error (ECE)
    brier_score: float  # Probabilistic accuracy
    confusion_matrix: Dict[str, Dict[str, int]]
    per_domain_metrics: Dict[str, Dict[str, float]]


class BenchmarkDataSplitter:
    """Creates train/test/val splits from benchmark data"""

    def __init__(
        self,
        data_path: Path = Path("./data/unified_database_complete.json"),
        eval_cache_dir: Path = Path("./data/eval_cache"),
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42
    ):
        self.data_path = data_path
        self.eval_cache_dir = eval_cache_dir
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed

        random.seed(random_seed)
        np.random.seed(random_seed)

        # Load data
        self.questions = self._load_questions()
        self.model_outputs = self._load_model_outputs()

    def _load_questions(self) -> List[Dict[str, Any]]:
        """Load unified database"""
        logger.info(f"Loading questions from {self.data_path}...")
        with open(self.data_path, 'r') as f:
            data = json.load(f)

        questions = data['questions']
        logger.info(f"✅ Loaded {len(questions):,} questions")
        return questions

    def _load_model_outputs(self) -> Dict[str, Dict]:
        """Load model outputs from eval_cache"""
        logger.info(f"Loading model outputs from {self.eval_cache_dir}...")

        model_outputs = {}
        for file_path in self.eval_cache_dir.glob("mmlu_pro_model_outputs_*.json"):
            model_name = file_path.stem.replace("mmlu_pro_model_outputs_", "")

            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    model_outputs[model_name] = data
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")

        logger.info(f"✅ Loaded outputs for {len(model_outputs)} models")
        return model_outputs

    def create_stratified_splits(
        self,
        stratify_by: str = "domain"
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Create stratified train/test/val splits

        Args:
            stratify_by: Field to stratify on ('domain', 'difficulty_label', 'benchmark')

        Returns:
            (train_set, val_set, test_set)
        """
        logger.info(f"Creating stratified splits by {stratify_by}...")

        # Group questions by stratification key
        groups = defaultdict(list)
        for q in self.questions:
            key = q.get(stratify_by, 'unknown')
            groups[key].append(q)

        # Split each group
        train_set = []
        val_set = []
        test_set = []

        for group_key, group_questions in groups.items():
            # Shuffle group
            random.shuffle(group_questions)

            n = len(group_questions)
            train_end = int(n * self.train_ratio)
            val_end = train_end + int(n * self.val_ratio)

            train_set.extend(group_questions[:train_end])
            val_set.extend(group_questions[train_end:val_end])
            test_set.extend(group_questions[val_end:])

            logger.info(f"  {group_key}: {len(group_questions)} → "
                       f"{train_end} train, {val_end - train_end} val, "
                       f"{n - val_end} test")

        # Shuffle final sets
        random.shuffle(train_set)
        random.shuffle(val_set)
        random.shuffle(test_set)

        logger.info(f"\n✅ Final splits:")
        logger.info(f"  Train: {len(train_set):,} ({len(train_set)/len(self.questions)*100:.1f}%)")
        logger.info(f"  Val:   {len(val_set):,} ({len(val_set)/len(self.questions)*100:.1f}%)")
        logger.info(f"  Test:  {len(test_set):,} ({len(test_set)/len(self.questions)*100:.1f}%)")

        return train_set, val_set, test_set

    def save_splits(
        self,
        train_set: List[Dict],
        val_set: List[Dict],
        test_set: List[Dict],
        output_dir: Path = Path("./data/splits")
    ):
        """Save splits to disk"""
        output_dir.mkdir(exist_ok=True)

        splits = {
            'train': train_set,
            'val': val_set,
            'test': test_set
        }

        for split_name, split_data in splits.items():
            output_path = output_dir / f"{split_name}.json"

            with open(output_path, 'w') as f:
                json.dump({
                    'split': split_name,
                    'size': len(split_data),
                    'questions': split_data
                }, f, indent=2)

            logger.info(f"  Saved {split_name} set to {output_path} ({len(split_data):,} questions)")

        # Save split metadata
        metadata = {
            'random_seed': self.random_seed,
            'train_ratio': self.train_ratio,
            'val_ratio': self.val_ratio,
            'test_ratio': self.test_ratio,
            'total_questions': len(self.questions),
            'train_size': len(train_set),
            'val_size': len(val_set),
            'test_size': len(test_set),
            'domain_distribution': self._get_distribution(train_set, val_set, test_set, 'domain'),
            'difficulty_distribution': self._get_distribution(train_set, val_set, test_set, 'difficulty_label'),
        }

        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"\n✅ Splits saved to {output_dir}/")

    def _get_distribution(
        self,
        train_set: List[Dict],
        val_set: List[Dict],
        test_set: List[Dict],
        field: str
    ) -> Dict[str, Dict[str, int]]:
        """Get distribution of a field across splits"""
        distribution = {}

        for split_name, split_data in [('train', train_set), ('val', val_set), ('test', test_set)]:
            counts = Counter(q.get(field, 'unknown') for q in split_data)
            distribution[split_name] = dict(counts)

        return distribution


class LightweightCheckerEvaluator:
    """Evaluates and tunes lightweight checker hyperparameters"""

    def __init__(
        self,
        train_set: List[Dict],
        val_set: List[Dict],
        test_set: List[Dict]
    ):
        self.train_set = train_set
        self.val_set = val_set
        self.test_set = test_set

    def create_ground_truth_labels(
        self,
        dataset: List[Dict],
        difficulty_threshold: float = 0.7
    ) -> List[Tuple[Dict, str]]:
        """Create ground truth labels from success rates

        Ground truth:
        - HIGH_RISK: difficulty_score > difficulty_threshold (success_rate < 0.3)
        - MEDIUM_RISK: 0.3 <= success_rate < 0.7
        - LOW_RISK: success_rate >= 0.7
        """
        labeled_data = []

        for q in dataset:
            success_rate = q['success_rate']

            if success_rate < 0.3:
                label = 'HIGH_RISK'
            elif success_rate < 0.7:
                label = 'MEDIUM_RISK'
            else:
                label = 'LOW_RISK'

            labeled_data.append((q, label))

        return labeled_data

    def evaluate_checker(
        self,
        checker,
        dataset: List[Dict],
        dataset_name: str = "test"
    ) -> EvaluationMetrics:
        """Evaluate checker on a dataset"""
        logger.info(f"\nEvaluating checker on {dataset_name} set ({len(dataset)} questions)...")

        # Get ground truth labels
        labeled_data = self.create_ground_truth_labels(dataset)

        # Predictions
        predictions = []
        true_labels = []
        predicted_probs = []  # For calibration metrics

        confusion_matrix = defaultdict(lambda: defaultdict(int))
        per_domain_correct = defaultdict(int)
        per_domain_total = defaultdict(int)

        for q, true_label in labeled_data:
            # Run checker
            result = checker.quick_check(q['question_text'])
            predicted_label = result['risk_level']
            predicted_prob = result.get('risk_score', 0.5)

            predictions.append(predicted_label)
            true_labels.append(true_label)
            predicted_probs.append(predicted_prob)

            # Confusion matrix
            confusion_matrix[true_label][predicted_label] += 1

            # Per-domain metrics
            domain = q['domain']
            per_domain_total[domain] += 1
            if predicted_label == true_label:
                per_domain_correct[domain] += 1

        # Calculate metrics
        accuracy = sum(p == t for p, t in zip(predictions, true_labels)) / len(predictions)

        # Precision, recall, F1 (macro-averaged across classes)
        precision_per_class = {}
        recall_per_class = {}
        f1_per_class = {}

        for label in ['LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK']:
            tp = confusion_matrix[label][label]
            fp = sum(confusion_matrix[other][label] for other in ['LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK'] if other != label)
            fn = sum(confusion_matrix[label][other] for other in ['LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK'] if other != label)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            precision_per_class[label] = precision
            recall_per_class[label] = recall
            f1_per_class[label] = f1

        macro_precision = np.mean(list(precision_per_class.values()))
        macro_recall = np.mean(list(recall_per_class.values()))
        macro_f1 = np.mean(list(f1_per_class.values()))

        # Calibration error (Expected Calibration Error - ECE)
        calibration_error = self._calculate_ece(true_labels, predicted_probs)

        # Brier score (mean squared error of probability predictions)
        brier_score = self._calculate_brier_score(true_labels, predicted_probs)

        # Per-domain metrics
        per_domain_metrics = {}
        for domain in per_domain_total:
            per_domain_metrics[domain] = {
                'accuracy': per_domain_correct[domain] / per_domain_total[domain],
                'total': per_domain_total[domain]
            }

        metrics = EvaluationMetrics(
            accuracy=accuracy,
            precision=macro_precision,
            recall=macro_recall,
            f1_score=macro_f1,
            calibration_error=calibration_error,
            brier_score=brier_score,
            confusion_matrix=dict(confusion_matrix),
            per_domain_metrics=per_domain_metrics
        )

        # Print results
        logger.info(f"\n{'='*60}")
        logger.info(f"{dataset_name.upper()} SET RESULTS")
        logger.info(f"{'='*60}")
        logger.info(f"Accuracy:          {accuracy:.3f}")
        logger.info(f"Precision (macro): {macro_precision:.3f}")
        logger.info(f"Recall (macro):    {macro_recall:.3f}")
        logger.info(f"F1 Score (macro):  {macro_f1:.3f}")
        logger.info(f"Calibration Error: {calibration_error:.3f}")
        logger.info(f"Brier Score:       {brier_score:.3f}")

        logger.info(f"\nPer-class metrics:")
        for label in ['LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK']:
            logger.info(f"  {label}:")
            logger.info(f"    Precision: {precision_per_class[label]:.3f}")
            logger.info(f"    Recall:    {recall_per_class[label]:.3f}")
            logger.info(f"    F1:        {f1_per_class[label]:.3f}")

        logger.info(f"\nConfusion Matrix:")
        logger.info(f"{'':20} {'LOW':>12} {'MEDIUM':>12} {'HIGH':>12}")
        for true_label in ['LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK']:
            row = f"{true_label:20}"
            for pred_label in ['LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK']:
                count = confusion_matrix[true_label][pred_label]
                row += f" {count:>12}"
            logger.info(row)

        return metrics

    def _calculate_ece(
        self,
        true_labels: List[str],
        predicted_probs: List[float],
        n_bins: int = 10
    ) -> float:
        """Calculate Expected Calibration Error"""
        # Convert labels to binary (for simplicity, use HIGH_RISK vs others)
        true_binary = [1 if label == 'HIGH_RISK' else 0 for label in true_labels]

        # Bin predictions
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]

        ece = 0.0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            # Get predictions in this bin
            in_bin = [(p >= bin_lower) and (p < bin_upper) for p in predicted_probs]

            if sum(in_bin) == 0:
                continue

            # Average confidence and accuracy in this bin
            bin_probs = [p for p, in_b in zip(predicted_probs, in_bin) if in_b]
            bin_true = [t for t, in_b in zip(true_binary, in_bin) if in_b]

            avg_confidence = np.mean(bin_probs)
            avg_accuracy = np.mean(bin_true)

            ece += abs(avg_confidence - avg_accuracy) * len(bin_probs) / len(predicted_probs)

        return ece

    def _calculate_brier_score(
        self,
        true_labels: List[str],
        predicted_probs: List[float]
    ) -> float:
        """Calculate Brier score (MSE of probabilities)"""
        true_binary = [1 if label == 'HIGH_RISK' else 0 for label in true_labels]

        squared_errors = [(p - t) ** 2 for p, t in zip(predicted_probs, true_binary)]
        return np.mean(squared_errors)

    def grid_search_hyperparameters(
        self,
        param_grid: Dict[str, List[Any]],
        checker_class,
        metric: str = 'f1_score'
    ) -> Tuple[Dict[str, Any], EvaluationMetrics]:
        """Grid search over hyperparameters

        Args:
            param_grid: Dictionary of parameter names to lists of values
            checker_class: Checker class to instantiate
            metric: Metric to optimize ('accuracy', 'f1_score', 'calibration_error')

        Returns:
            (best_params, best_metrics)
        """
        logger.info(f"\n{'='*60}")
        logger.info("HYPERPARAMETER GRID SEARCH")
        logger.info(f"{'='*60}")
        logger.info(f"Optimizing for: {metric}")
        logger.info(f"Search space:")
        for param, values in param_grid.items():
            logger.info(f"  {param}: {values}")

        # Generate all combinations
        from itertools import product

        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(product(*param_values))

        logger.info(f"\nTotal combinations: {len(param_combinations)}")

        best_score = -np.inf if metric != 'calibration_error' else np.inf
        best_params = None
        best_metrics = None

        for i, param_combo in enumerate(param_combinations, 1):
            params = dict(zip(param_names, param_combo))

            logger.info(f"\n[{i}/{len(param_combinations)}] Testing: {params}")

            # Create checker with these params
            checker = checker_class(**params)

            # Evaluate on validation set
            metrics = self.evaluate_checker(checker, self.val_set, dataset_name=f"val_{i}")

            score = getattr(metrics, metric)

            # Check if this is the best
            is_better = (score > best_score) if metric != 'calibration_error' else (score < best_score)

            if is_better:
                best_score = score
                best_params = params
                best_metrics = metrics
                logger.info(f"  ✅ NEW BEST! {metric} = {score:.3f}")
            else:
                logger.info(f"  {metric} = {score:.3f} (best: {best_score:.3f})")

        logger.info(f"\n{'='*60}")
        logger.info("BEST HYPERPARAMETERS")
        logger.info(f"{'='*60}")
        logger.info(f"Best {metric}: {best_score:.3f}")
        logger.info(f"Parameters:")
        for param, value in best_params.items():
            logger.info(f"  {param}: {value}")

        return best_params, best_metrics


def main():
    """Main entry point"""

    print("\n" + "="*80)
    print("Evaluation Framework: Lightweight Checker & Taxonomy Tuning")
    print("="*80)

    # Step 1: Create splits
    print("\nStep 1: Creating train/test/val splits...")
    splitter = BenchmarkDataSplitter()
    train_set, val_set, test_set = splitter.create_stratified_splits(stratify_by='domain')
    splitter.save_splits(train_set, val_set, test_set)

    # Step 2: Create evaluator
    print("\nStep 2: Creating evaluator...")
    evaluator = LightweightCheckerEvaluator(train_set, val_set, test_set)

    # Step 3: Evaluate baseline (V3 checker)
    print("\nStep 3: Evaluating baseline (V3)...")
    from lightweight_prompt_checker_v3 import LightweightPromptChecker as CheckerV3
    baseline_checker = CheckerV3()
    baseline_metrics = evaluator.evaluate_checker(baseline_checker, test_set, dataset_name="test_v3_baseline")

    # Step 4: Evaluate V5 (difficulty-aware checker)
    print("\nStep 4: Evaluating V5 (difficulty-aware) with default hyperparameters...")
    from difficulty_aware_checker_v5 import DifficultyAwareChecker as CheckerV5
    v5_checker = CheckerV5()
    v5_metrics = evaluator.evaluate_checker(v5_checker, test_set, dataset_name="test_v5_default")

    # Step 5: Compare V3 vs V5
    print("\n" + "="*80)
    print("COMPARISON: V3 vs V5")
    print("="*80)
    print(f"\n{'Metric':<25} {'V3 (Baseline)':<20} {'V5 (Difficulty-Aware)':<20} {'Improvement':<15}")
    print("-" * 80)
    print(f"{'Accuracy':<25} {baseline_metrics.accuracy:<20.3f} {v5_metrics.accuracy:<20.3f} {v5_metrics.accuracy - baseline_metrics.accuracy:>+14.3f}")
    print(f"{'Precision (macro)':<25} {baseline_metrics.precision:<20.3f} {v5_metrics.precision:<20.3f} {v5_metrics.precision - baseline_metrics.precision:>+14.3f}")
    print(f"{'Recall (macro)':<25} {baseline_metrics.recall:<20.3f} {v5_metrics.recall:<20.3f} {v5_metrics.recall - baseline_metrics.recall:>+14.3f}")
    print(f"{'F1 Score (macro)':<25} {baseline_metrics.f1_score:<20.3f} {v5_metrics.f1_score:<20.3f} {v5_metrics.f1_score - baseline_metrics.f1_score:>+14.3f}")
    print(f"{'Calibration Error':<25} {baseline_metrics.calibration_error:<20.3f} {v5_metrics.calibration_error:<20.3f} {v5_metrics.calibration_error - baseline_metrics.calibration_error:>+14.3f}")
    print(f"{'Brier Score':<25} {baseline_metrics.brier_score:<20.3f} {v5_metrics.brier_score:<20.3f} {v5_metrics.brier_score - baseline_metrics.brier_score:>+14.3f}")

    # Note: Future hyperparameter tuning can be done here
    logger.info("\nNote: Hyperparameter tuning can further improve V5 performance")

    print("\n" + "="*80)
    print("✅ Evaluation framework complete!")
    print("="*80)
    print("\nNext steps:")
    print("1. Modify V4 checker to accept hyperparameters in __init__")
    print("2. Run grid search on validation set")
    print("3. Evaluate best model on test set")
    print("4. Compare with baseline (V3)")
    print("5. Analyze per-domain performance")
    print("6. Tune taxonomy scoring separately")


if __name__ == "__main__":
    main()
