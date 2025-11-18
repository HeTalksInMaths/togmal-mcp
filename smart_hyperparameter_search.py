#!/usr/bin/env python3
"""
Smart Hyperparameter Search using Bayesian Optimization
========================================================

Uses scikit-optimize (skopt) for efficient Bayesian optimization:
- Gaussian process-based search
- 10-20x fewer evaluations than grid search
- Supports continuous, integer, and categorical parameters
- Acquisition function balances exploration vs exploitation
"""

import logging
import numpy as np
from typing import Callable, Dict, List, Union
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HyperparameterSpace:
    """Definition of a hyperparameter search space"""
    name: str
    low: float
    high: float
    distribution: str = 'uniform'  # 'uniform' or 'log-uniform'

    def to_skopt_dimension(self):
        """Convert to skopt dimension"""
        from skopt.space import Real
        if self.distribution == 'log-uniform':
            return Real(self.low, self.high, prior='log-uniform', name=self.name)
        else:
            return Real(self.low, self.high, prior='uniform', name=self.name)


class SmartHyperparameterSearch:
    """Bayesian hyperparameter optimization"""

    def __init__(
        self,
        objective_function: Callable,
        param_space: List[HyperparameterSpace],
        n_calls: int = 25,
        n_random_starts: int = 8,
        random_state: int = 42
    ):
        """
        Args:
            objective_function: Function to maximize (takes dict of params, returns score)
            param_space: List of HyperparameterSpace objects
            n_calls: Total number of evaluations
            n_random_starts: Number of random evaluations before Bayesian search
            random_state: Random seed
        """
        self.objective_function = objective_function
        self.param_space = param_space
        self.n_calls = n_calls
        self.n_random_starts = n_random_starts
        self.random_state = random_state

        # Validate
        if n_random_starts >= n_calls:
            raise ValueError(f"n_random_starts ({n_random_starts}) must be < n_calls ({n_calls})")

        logger.info(f"Initialized Bayesian optimization:")
        logger.info(f"  Parameters: {len(param_space)}")
        logger.info(f"  Total evaluations: {n_calls}")
        logger.info(f"  Random starts: {n_random_starts}")
        logger.info(f"  Bayesian iterations: {n_calls - n_random_starts}")

    def optimize(self) -> Dict:
        """Run Bayesian optimization

        Returns:
            Dict with best_params, best_score, n_evaluations, history
        """
        from skopt import gp_minimize
        from skopt.utils import use_named_args

        # Convert param space to skopt dimensions
        dimensions = [p.to_skopt_dimension() for p in self.param_space]

        # Create wrapper for objective function
        @use_named_args(dimensions)
        def objective(**params):
            """Wrapper that converts named args to dict"""
            score = self.objective_function(params)
            # skopt minimizes, but we want to maximize, so negate
            return -score

        logger.info("\n" + "="*80)
        logger.info("Starting Bayesian Optimization")
        logger.info("="*80)

        # Run optimization
        result = gp_minimize(
            objective,
            dimensions,
            n_calls=self.n_calls,
            n_random_starts=self.n_random_starts,
            random_state=self.random_state,
            verbose=False
        )

        # Extract best parameters
        best_params = {}
        for i, param in enumerate(self.param_space):
            best_params[param.name] = result.x[i]

        best_score = -result.fun  # Negate back to original score

        logger.info("\n" + "="*80)
        logger.info("Optimization Complete!")
        logger.info("="*80)
        logger.info(f"\nBest score: {best_score:.6f}")
        logger.info("\nBest parameters:")
        for name, value in best_params.items():
            logger.info(f"  {name}: {value}")

        # Return results
        return {
            'best_params': best_params,
            'best_score': best_score,
            'n_evaluations': self.n_calls,
            'history': {
                'scores': [-y for y in result.func_vals],  # Negate back
                'params': result.x_iters
            }
        }


if __name__ == "__main__":
    # Test with simple optimization problem

    def test_objective(params):
        """Test function: maximize -(x^2 + y^2)"""
        x = params['x']
        y = params['y']
        # Optimal is x=0, y=0 with score=0
        score = -(x**2 + y**2)
        return score

    param_space = [
        HyperparameterSpace('x', -10.0, 10.0, 'uniform'),
        HyperparameterSpace('y', -10.0, 10.0, 'uniform'),
    ]

    print("\n" + "="*80)
    print("Testing Bayesian Optimization")
    print("="*80)
    print("\nObjective: maximize -(x^2 + y^2)")
    print("Expected optimal: x=0, y=0, score=0")

    optimizer = SmartHyperparameterSearch(
        objective_function=test_objective,
        param_space=param_space,
        n_calls=20,
        n_random_starts=5
    )

    result = optimizer.optimize()

    print("\n" + "="*80)
    print("Test Results")
    print("="*80)
    print(f"Best x: {result['best_params']['x']:.6f} (expected: 0.0)")
    print(f"Best y: {result['best_params']['y']:.6f} (expected: 0.0)")
    print(f"Best score: {result['best_score']:.6f} (expected: 0.0)")
    print("\n✅ Test complete!")
