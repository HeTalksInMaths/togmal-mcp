#!/usr/bin/env python3
"""
Hybrid Failure Rate Predictor (Phase 2)
========================================

Combines:
1. Weighted semantic similarity (Phase 1)
2. Meta-learned difficulty features (Phase 2)
3. Ensemble with uncertainty decomposition

This is the Phase 2 predictor that should achieve 30-50% MAE reduction
over the original predictor.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from failure_rate_predictor_improved import ImprovedFailureRatePredictor
from meta_difficulty_predictor import MetaDifficultyPredictor


class HybridFailurePredictor:
    """
    Hybrid predictor combining semantic similarity + meta-features

    Phase 2 improvements:
    - Meta-learned difficulty features
    - Ensemble of complementary predictors
    - Enhanced uncertainty decomposition
    """

    def __init__(
        self,
        questions_db_path: str = "./data/unified_database_with_mmlu_pro.json",
        performance_db_path: str = "./data/model_performance_database.json",
        meta_model_path: str = "./models/meta_difficulty_predictor.pkl",
        semantic_weight: float = 0.6,
        meta_weight: float = 0.4
    ):
        """
        Args:
            questions_db_path: Path to questions database
            performance_db_path: Path to performance database
            meta_model_path: Path to trained meta-predictor
            semantic_weight: Weight for semantic similarity prediction
            meta_weight: Weight for meta-features prediction
        """
        print("="*80)
        print("HYBRID FAILURE PREDICTOR (Phase 2)")
        print("="*80)

        # Initialize semantic predictor (Phase 1)
        print("\n1. Loading semantic predictor (Phase 1)...")
        self.semantic_predictor = ImprovedFailureRatePredictor(
            questions_db_path=questions_db_path,
            performance_db_path=performance_db_path,
            use_weighted_similarity=True,
            use_temperature_scaling=True
        )

        # Load meta-predictor (Phase 2)
        print("\n2. Loading meta-predictor (Phase 2)...")
        self.meta_predictor = MetaDifficultyPredictor()

        if Path(meta_model_path).exists():
            self.meta_predictor.load(meta_model_path)
        else:
            print(f"   ⚠️  Meta-predictor not found at {meta_model_path}")
            print(f"   Run meta_difficulty_predictor.py first to train it")
            self.meta_predictor = None

        # Ensemble weights
        self.semantic_weight = semantic_weight
        self.meta_weight = meta_weight

        print(f"\n✅ Hybrid predictor ready!")
        print(f"   Semantic weight: {semantic_weight}")
        print(f"   Meta-features weight: {meta_weight}")

    def predict_failure_rate(
        self,
        query: str,
        model_name: Optional[str] = None,
        top_k_similar: int = 10,
        domain: Optional[str] = None
    ) -> Dict:
        """
        Predict failure rate using hybrid approach

        Returns:
            Dict with ensemble prediction, component predictions, and uncertainty
        """
        # Get semantic similarity prediction
        semantic_result = self.semantic_predictor.predict_failure_rate(
            query=query,
            model_name=model_name,
            top_k_similar=top_k_similar,
            domain=domain
        )

        semantic_pred = semantic_result['aggregated_prediction'].get('overall_failure_rate')
        semantic_confidence = semantic_result.get('uncertainty', {}).get('epistemic', 0.5) if semantic_pred else 0.0

        # Get meta-features prediction (if available)
        meta_pred = None
        meta_confidence = 0.0

        if self.meta_predictor and self.meta_predictor.is_trained:
            # Create question dict for meta-predictor
            question_dict = {
                'question_text': query,
                'domain': domain if domain else 'unknown',
                'options': []  # Don't have options for query
            }

            meta_result = self.meta_predictor.predict(question_dict)
            meta_pred = meta_result['predicted_failure_rate']
            meta_confidence = meta_result['confidence']

        # Ensemble prediction
        if semantic_pred is not None and meta_pred is not None:
            # Adaptive weighting based on confidence
            # Higher confidence predictor gets more weight
            total_confidence = semantic_confidence + meta_confidence

            if total_confidence > 0:
                adaptive_semantic_weight = semantic_confidence / total_confidence
                adaptive_meta_weight = meta_confidence / total_confidence
            else:
                adaptive_semantic_weight = self.semantic_weight
                adaptive_meta_weight = self.meta_weight

            # Weighted ensemble
            ensemble_pred = (adaptive_semantic_weight * semantic_pred +
                           adaptive_meta_weight * meta_pred)

            method = 'hybrid_ensemble'
            components = {
                'semantic': {
                    'prediction': semantic_pred,
                    'confidence': semantic_confidence,
                    'weight': adaptive_semantic_weight
                },
                'meta_features': {
                    'prediction': meta_pred,
                    'confidence': meta_confidence,
                    'weight': adaptive_meta_weight
                }
            }

        elif semantic_pred is not None:
            # Fallback to semantic only
            ensemble_pred = semantic_pred
            method = 'semantic_only'
            components = {
                'semantic': {
                    'prediction': semantic_pred,
                    'confidence': semantic_confidence,
                    'weight': 1.0
                }
            }

        elif meta_pred is not None:
            # Fallback to meta only (rare)
            ensemble_pred = meta_pred
            method = 'meta_only'
            components = {
                'meta_features': {
                    'prediction': meta_pred,
                    'confidence': meta_confidence,
                    'weight': 1.0
                }
            }

        else:
            # No prediction possible
            ensemble_pred = None
            method = 'no_prediction'
            components = {}

        # Enhanced uncertainty decomposition
        uncertainty = self._enhanced_uncertainty_decomposition(
            semantic_result, meta_pred, meta_confidence
        )

        # Build result
        result = {
            'query': query,
            'ensemble_prediction': {
                'failure_rate': ensemble_pred,
                'method': method,
                'components': components
            },

            # Include full semantic results
            'semantic_analysis': semantic_result,

            # Enhanced uncertainty
            'uncertainty': uncertainty,

            # Recommendation
            'recommendation': self._generate_recommendation(
                ensemble_pred, uncertainty, components
            )
        }

        return result

    def _enhanced_uncertainty_decomposition(
        self,
        semantic_result: Dict,
        meta_pred: Optional[float],
        meta_confidence: float
    ) -> Dict:
        """
        Enhanced uncertainty decomposition using ensemble disagreement

        Epistemic uncertainty now includes:
        - Semantic similarity uncertainty (from Phase 1)
        - Ensemble disagreement (difference between predictors)

        Aleatoric uncertainty:
        - Performance variance in similar questions (from Phase 1)
        """
        semantic_unc = semantic_result.get('uncertainty') or {}
        semantic_epistemic = semantic_unc.get('epistemic', 0.5)
        semantic_aleatoric = semantic_unc.get('aleatoric', 0.5)

        # Ensemble disagreement (epistemic)
        semantic_pred = semantic_result['aggregated_prediction'].get('overall_failure_rate')

        if semantic_pred is not None and meta_pred is not None:
            # Disagreement between predictors
            disagreement = abs(semantic_pred - meta_pred) / 100.0  # Normalize to [0, 1]

            # Combined epistemic = base semantic epistemic + ensemble disagreement
            epistemic = (semantic_epistemic + disagreement) / 2

        else:
            # No ensemble, use semantic epistemic
            epistemic = semantic_epistemic
            disagreement = 0.0

        # Aleatoric stays the same (inherent difficulty variance)
        aleatoric = semantic_aleatoric

        # Total uncertainty
        total = epistemic + aleatoric

        return {
            'total': total,
            'epistemic': epistemic,
            'aleatoric': aleatoric,
            'ensemble_disagreement': disagreement,
            'interpretation': self._interpret_uncertainty(epistemic, aleatoric, disagreement)
        }

    def _interpret_uncertainty(
        self,
        epistemic: float,
        aleatoric: float,
        disagreement: float
    ) -> str:
        """Enhanced uncertainty interpretation"""
        if disagreement > 0.3:
            return "HIGH_ENSEMBLE_DISAGREEMENT: Predictors disagree significantly. Prediction is uncertain - consider gathering more data or manual review."

        elif epistemic > aleatoric * 2:
            return "HIGH_MODEL_UNCERTAINTY: Low similarity to benchmarks. Consider evaluating more questions in this domain."

        elif aleatoric > epistemic * 2:
            return "HIGH_DATA_NOISE: Similar questions have variable outcomes. This is inherently difficult."

        else:
            return "BALANCED_UNCERTAINTY: Standard prediction confidence applies."

    def _generate_recommendation(
        self,
        failure_rate: Optional[float],
        uncertainty: Dict,
        components: Dict
    ) -> Dict:
        """Generate recommendation based on ensemble prediction"""
        if failure_rate is None:
            return {
                'level': 'UNKNOWN',
                'message': 'No prediction available',
                'suggested_action': 'Manual evaluation required'
            }

        # Determine risk level
        if failure_rate < 20:
            level = 'LOW_RISK'
        elif failure_rate < 40:
            level = 'MODERATE_RISK'
        elif failure_rate < 60:
            level = 'HIGH_RISK'
        else:
            level = 'VERY_HIGH_RISK'

        # Adjust for uncertainty
        if uncertainty['total'] > 1.0:
            level = level + '_UNCERTAIN'

        # Build message
        message = f"Predicted failure rate: {failure_rate:.1f}%"

        if len(components) > 1:
            # Show component predictions
            comp_msgs = []
            for name, data in components.items():
                comp_msgs.append(f"{name}={data['prediction']:.1f}%")
            message += f" ({', '.join(comp_msgs)})"

        # Add uncertainty info
        if uncertainty.get('ensemble_disagreement', 0) > 0.2:
            message += f" | ⚠️ Predictors disagree ({uncertainty['ensemble_disagreement']*100:.0f}%)"

        # Suggested action
        if level.startswith('VERY_HIGH'):
            action = "CRITICAL: High failure risk. Recommend alternative approaches or extensive verification."
        elif level.startswith('HIGH'):
            action = "Use best available model, add verification, or simplify task."
        elif level.startswith('MODERATE'):
            action = "Consider verification or stronger model."
        else:
            action = "Proceed normally with standard precautions."

        return {
            'level': level,
            'message': message,
            'suggested_action': action,
            'failure_rate': failure_rate
        }

    def compare_methods(self, query: str, domain: Optional[str] = None) -> Dict:
        """Compare predictions from different methods"""
        result = self.predict_failure_rate(query, domain=domain)

        comparison = {
            'query': query,
            'ensemble': result['ensemble_prediction']['failure_rate'],
            'components': result['ensemble_prediction']['components'],
            'uncertainty': result['uncertainty'],
            'recommendation': result['recommendation']
        }

        return comparison


if __name__ == "__main__":
    print("="*80)
    print("HYBRID FAILURE PREDICTOR - DEMO")
    print("="*80)

    # Initialize predictor
    predictor = HybridFailurePredictor()

    # Test queries
    test_queries = [
        {
            "query": "What is 2+2?",
            "domain": "math",
            "description": "Simple math question"
        },
        {
            "query": "Prove that the eigenvalues of a Hermitian matrix are real.",
            "domain": "math",
            "description": "Proof-based question"
        },
        {
            "query": "Calculate the partition function for a 2D Ising model with external magnetic field.",
            "domain": "physics",
            "description": "Advanced physics"
        },
        {
            "query": "A highway patrol officer stopped a driver for speeding. Is the subsequent search legal?",
            "domain": "law",
            "description": "Legal reasoning"
        }
    ]

    for i, test in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {test['description']}")
        print(f"{'='*80}")
        print(f"\nQuery: \"{test['query']}\"")
        print(f"Domain: {test['domain']}")

        # Predict
        result = predictor.predict_failure_rate(
            query=test['query'],
            domain=test['domain'],
            top_k_similar=10
        )

        ensemble = result['ensemble_prediction']
        failure_rate = ensemble['failure_rate']

        print(f"\n📊 HYBRID PREDICTION:")
        if failure_rate is not None:
            print(f"   Ensemble failure rate: {failure_rate:.1f}%")
            print(f"   Method: {ensemble['method']}")

            if 'components' in ensemble:
                print(f"\n   Component predictions:")
                for name, data in ensemble['components'].items():
                    print(f"     {name}: {data['prediction']:.1f}% (weight={data['weight']:.2f}, conf={data['confidence']:.2f})")
        else:
            print(f"   No prediction available")

        # Uncertainty
        unc = result['uncertainty']
        print(f"\n🎲 UNCERTAINTY:")
        print(f"   Total: {unc['total']:.2f}")
        print(f"   Epistemic: {unc['epistemic']:.2f}")
        print(f"   Aleatoric: {unc['aleatoric']:.2f}")
        if 'ensemble_disagreement' in unc:
            print(f"   Ensemble disagreement: {unc['ensemble_disagreement']:.2f}")
        print(f"   {unc['interpretation']}")

        # Recommendation
        rec = result['recommendation']
        print(f"\n⚠️  RECOMMENDATION: {rec['level']}")
        print(f"   {rec['message']}")
        print(f"   Action: {rec['suggested_action']}")

    print("\n" + "="*80)
    print("✅ Demo Complete!")
    print("="*80)
