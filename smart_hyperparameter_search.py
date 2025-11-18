#!/usr/bin/env python3
"""
Smart Hyperparameter Search using Bayesian Optimization
========================================================

Instead of exhaustive grid search, use Bayesian optimization for efficient tuning:
- Explores promising regions of hyperparameter space
- Balances exploration vs exploitation
- Much faster than grid search (10-20x fewer evaluations)
- Works for both lightweight checker and similarity scorer

Uses scikit-optimize for Bayesian optimization.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Callable
import numpy as np
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HyperparameterSpace:
    """Defines hyperparameter search space"""
    name: str
    low: float
    high: float
    prior: str = 'uniform'  # 'uniform' or 'log-uniform'


class SmartHyperparameterSearch:
    """Bayesian optimization for hyperparameter tuning"""

    def __init__(
        self,
        objective_function: Callable,
        param_space: List[HyperparameterSpace],
        n_calls: int = 50,  # Much less than grid search
        n_random_starts: int = 10,
        random_seed: int = 42
    ):
        """
        Args:
            objective_function: Function that takes hyperparams dict and returns score
            param_space: List of HyperparameterSpace objects
            n_calls: Total number of evaluations (default: 50)
            n_random_starts: Random evaluations before Bayesian optimization (default: 10)
            random_seed: Random seed for reproducibility
        """
        self.objective_function = objective_function
        self.param_space = param_space
        self.n_calls = n_calls
        self.n_random_starts = n_random_starts
        self.random_seed = random_seed

        # Results storage
        self.history = []
        self.best_params = None
        self.best_score = -np.inf

    def optimize(self) -> Dict[str, Any]:
        """Run Bayesian optimization"""
        try:
            from skopt import gp_minimize
            from skopt.space import Real
            from skopt.utils import use_named_args
        except ImportError:
            logger.error("scikit-optimize not installed. Install with: pip install scikit-optimize")
            logger.info("Falling back to random search...")
            return self._random_search_fallback()

        logger.info("="*80)
        logger.info("BAYESIAN HYPERPARAMETER OPTIMIZATION")
        logger.info("="*80)
        logger.info(f"Search space:")
        for param in self.param_space:
            logger.info(f"  {param.name}: [{param.low}, {param.high}] ({param.prior})")
        logger.info(f"\nTotal evaluations: {self.n_calls}")
        logger.info(f"Random starts: {self.n_random_starts}")
        logger.info(f"Bayesian iterations: {self.n_calls - self.n_random_starts}")

        # Define search space for skopt
        dimensions = []
        param_names = []
        for param in self.param_space:
            if param.prior == 'log-uniform':
                dimensions.append(Real(param.low, param.high, prior='log-uniform', name=param.name))
            else:
                dimensions.append(Real(param.low, param.high, name=param.name))
            param_names.append(param.name)

        # Wrapper function for skopt
        @use_named_args(dimensions)
        def objective(**params):
            # Evaluate
            score = self.objective_function(params)

            # Track history
            self.history.append({
                'params': params.copy(),
                'score': score
            })

            # Update best
            if score > self.best_score:
                self.best_score = score
                self.best_params = params.copy()
                logger.info(f"  ✅ NEW BEST! Score: {score:.4f} | Params: {params}")
            else:
                logger.info(f"  Score: {score:.4f} | Params: {params}")

            # Return negative score (skopt minimizes)
            return -score

        # Run optimization
        logger.info("\nStarting optimization...\n")

        result = gp_minimize(
            objective,
            dimensions,
            n_calls=self.n_calls,
            n_random_starts=self.n_random_starts,
            random_state=self.random_seed,
            verbose=False
        )

        logger.info("\n" + "="*80)
        logger.info("OPTIMIZATION COMPLETE")
        logger.info("="*80)
        logger.info(f"Best score: {self.best_score:.4f}")
        logger.info(f"Best parameters:")
        for name, value in self.best_params.items():
            logger.info(f"  {name}: {value:.4f}")

        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'history': self.history,
            'n_evaluations': len(self.history)
        }

    def _random_search_fallback(self) -> Dict[str, Any]:
        """Fallback to random search if scikit-optimize not available"""
        logger.info("="*80)
        logger.info("RANDOM HYPERPARAMETER SEARCH (Fallback)")
        logger.info("="*80)

        np.random.seed(self.random_seed)

        for i in range(self.n_calls):
            # Sample random parameters
            params = {}
            for param in self.param_space:
                if param.prior == 'log-uniform':
                    # Log-uniform sampling
                    log_low = np.log(param.low)
                    log_high = np.log(param.high)
                    params[param.name] = np.exp(np.random.uniform(log_low, log_high))
                else:
                    # Uniform sampling
                    params[param.name] = np.random.uniform(param.low, param.high)

            # Evaluate
            score = self.objective_function(params)

            # Track
            self.history.append({
                'params': params.copy(),
                'score': score
            })

            # Update best
            if score > self.best_score:
                self.best_score = score
                self.best_params = params.copy()
                logger.info(f"[{i+1}/{self.n_calls}] ✅ NEW BEST! Score: {score:.4f}")
            else:
                logger.info(f"[{i+1}/{self.n_calls}] Score: {score:.4f}")

        logger.info("\n" + "="*80)
        logger.info("SEARCH COMPLETE")
        logger.info("="*80)
        logger.info(f"Best score: {self.best_score:.4f}")
        logger.info(f"Best parameters:")
        for name, value in self.best_params.items():
            logger.info(f"  {name}: {value:.4f}")

        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'history': self.history,
            'n_evaluations': len(self.history)
        }


def tune_lightweight_checker():
    """Smart tuning for lightweight checker V5"""

    from evaluation_framework import BenchmarkDataSplitter, LightweightCheckerEvaluator
    from difficulty_aware_checker_v5 import DifficultyAwareChecker

    logger.info("\n" + "="*80)
    logger.info("TUNING: Lightweight Checker V5")
    logger.info("="*80)

    # Load data
    splitter = BenchmarkDataSplitter()
    train_set, val_set, test_set = splitter.create_stratified_splits()
    evaluator = LightweightCheckerEvaluator(train_set, val_set, test_set)

    # Define objective function
    def objective(params):
        """Evaluate checker with given hyperparameters"""

        # Normalize weights to sum to 1.0
        total_weight = params['domain_weight'] + params['complexity_weight'] + params['similarity_weight']
        normalized_params = {
            'domain_weight': params['domain_weight'] / total_weight,
            'complexity_weight': params['complexity_weight'] / total_weight,
            'similarity_weight': params['similarity_weight'] / total_weight,
            'high_risk_threshold': params['high_risk_threshold'],
            'medium_risk_threshold': params['medium_risk_threshold'],
            'math_notation_weight': params['math_notation_weight'],
            'technical_terms_weight': params['technical_terms_weight'],
        }

        # Create checker with these params
        checker = DifficultyAwareChecker(**normalized_params)

        # Evaluate on validation set
        metrics = evaluator.evaluate_checker(checker, val_set, dataset_name="val")

        # Return F1 score (metric to maximize)
        return metrics.f1_score

    # Define search space
    param_space = [
        HyperparameterSpace('domain_weight', 0.2, 0.6, 'uniform'),
        HyperparameterSpace('complexity_weight', 0.1, 0.5, 'uniform'),
        HyperparameterSpace('similarity_weight', 0.1, 0.5, 'uniform'),
        HyperparameterSpace('high_risk_threshold', 0.60, 0.80, 'uniform'),
        HyperparameterSpace('medium_risk_threshold', 0.30, 0.50, 'uniform'),
        HyperparameterSpace('math_notation_weight', 0.5, 2.0, 'uniform'),
        HyperparameterSpace('technical_terms_weight', 0.5, 2.0, 'uniform'),
    ]

    # Run optimization
    optimizer = SmartHyperparameterSearch(
        objective_function=objective,
        param_space=param_space,
        n_calls=30,  # Much less than grid search (which would be 1000s)
        n_random_starts=10
    )

    result = optimizer.optimize()

    # Evaluate best model on test set
    logger.info("\n" + "="*80)
    logger.info("FINAL TEST SET EVALUATION")
    logger.info("="*80)

    best_params = result['best_params']
    total_weight = best_params['domain_weight'] + best_params['complexity_weight'] + best_params['similarity_weight']
    normalized_best = {
        'domain_weight': best_params['domain_weight'] / total_weight,
        'complexity_weight': best_params['complexity_weight'] / total_weight,
        'similarity_weight': best_params['similarity_weight'] / total_weight,
        'high_risk_threshold': best_params['high_risk_threshold'],
        'medium_risk_threshold': best_params['medium_risk_threshold'],
        'math_notation_weight': best_params['math_notation_weight'],
        'technical_terms_weight': best_params['technical_terms_weight'],
    }

    best_checker = DifficultyAwareChecker(**normalized_best)
    test_metrics = evaluator.evaluate_checker(best_checker, test_set, dataset_name="test_tuned")

    logger.info(f"\n✅ Tuned model test accuracy: {test_metrics.accuracy:.3f}")
    logger.info(f"✅ Tuned model test F1: {test_metrics.f1_score:.3f}")

    # Save results
    results_path = Path("./tuning_results_checker.json")
    with open(results_path, 'w') as f:
        json.dump({
            'best_params': normalized_best,
            'val_score': result['best_score'],
            'test_accuracy': test_metrics.accuracy,
            'test_f1': test_metrics.f1_score,
            'test_precision': test_metrics.precision,
            'test_recall': test_metrics.recall,
            'n_evaluations': result['n_evaluations']
        }, f, indent=2)

    logger.info(f"\n✅ Results saved to {results_path}")

    return result


def tune_similarity_scorer():
    """Smart tuning for similarity scorer (BM25 parameters)"""

    logger.info("\n" + "="*80)
    logger.info("TUNING: Adaptive Similarity Scorer")
    logger.info("="*80)
    logger.info("NOTE: This requires evaluation metric for similarity scoring")
    logger.info("      (e.g., precision@k, recall@k, MRR on labeled query-document pairs)")
    logger.info("\nSkipping for now - needs labeled similarity data")

    # TODO: Implement when we have:
    # 1. Query-document pairs with relevance labels
    # 2. Evaluation metric (e.g., nDCG, MAP, MRR)
    # 3. BM25 parameters to tune (k1, b, etc.)

    return None


def main():
    """Main entry point"""

    print("\n" + "="*80)
    print("Smart Hyperparameter Search")
    print("="*80)
    print("\nOptions:")
    print("1. Tune Lightweight Checker V5 (difficulty prediction)")
    print("2. Tune Similarity Scorer (semantic search) - NOT IMPLEMENTED YET")
    print("="*80)

    # For now, just tune the checker
    print("\nTuning Lightweight Checker V5...")
    result = tune_lightweight_checker()

    print("\n" + "="*80)
    print("✅ Tuning complete!")
    print("="*80)


if __name__ == "__main__":
    main()
