#!/usr/bin/env python3
"""
LLM Failure Rate Predictor - IMPROVED VERSION
==============================================

Phase 1 Improvements:
1. ✅ Weighted semantic similarity (not equal weighting)
2. ✅ Temperature-scaled calibration
3. ✅ Confidence estimation based on coverage and agreement

Predicts likely LLM failure rate for a given question based on:
1. Semantic similarity to benchmark questions (WEIGHTED by similarity score)
2. Model performance on similar questions
3. Aggregated statistics across multiple models
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from local_embedding_scorer import LocalSemanticScorer


class ImprovedFailureRatePredictor:
    """Predicts LLM failure rates with weighted similarity and calibration"""

    def __init__(self, questions_db_path: str = "./data/unified_database_with_mmlu_pro.json",
                 performance_db_path: str = "./data/model_performance_database.json",
                 use_weighted_similarity: bool = True,
                 use_temperature_scaling: bool = True):
        """
        Args:
            questions_db_path: Path to unified questions database
            performance_db_path: Path to model performance database
            use_weighted_similarity: If True, weight by similarity scores
            use_temperature_scaling: If True, apply temperature calibration
        """

        # Load questions database
        with open(questions_db_path, 'r') as f:
            questions_data = json.load(f)
        self.all_questions = questions_data['questions']

        # Load performance database
        with open(performance_db_path, 'r') as f:
            perf_data = json.load(f)

        self.performance_data = perf_data['questions']
        self.overall_stats = perf_data['overall_stats']
        self.models = perf_data['metadata']['models']

        # Configuration
        self.use_weighted_similarity = use_weighted_similarity
        self.use_temperature_scaling = use_temperature_scaling

        # Temperature parameter (learned from calibration set)
        self.temperature = 1.0  # Will be learned if use_temperature_scaling=True

        # Build semantic scorer (using optimized parameters)
        tuning_results_path = Path("./tuning_results_semantic.json")
        if tuning_results_path.exists():
            with open(tuning_results_path, 'r') as f:
                tuning_results = json.load(f)
            params = tuning_results['best_params']
        else:
            params = {'embedding_dim': 488, 'max_features': 5004, 'domain_boost': 0.496}

        print(f"Building semantic scorer for failure prediction...")
        self.scorer = LocalSemanticScorer(
            questions=self.all_questions,
            embedding_dim=params['embedding_dim'],
            max_features=params['max_features'],
            domain_boost=params['domain_boost']
        )

        # Map question IDs to questions for quick lookup
        self.questions_by_id = {q['question_id']: q for q in self.all_questions}

        print(f"✅ Loaded {len(self.all_questions):,} questions")
        print(f"✅ Loaded {len(self.performance_data)} questions with model performance")
        print(f"✅ Tracking {len(self.models)} models")
        print(f"✅ Weighted similarity: {self.use_weighted_similarity}")
        print(f"✅ Temperature scaling: {self.use_temperature_scaling}")

    def predict_failure_rate(
        self,
        query: str,
        model_name: Optional[str] = None,
        top_k_similar: int = 10,
        domain: Optional[str] = None
    ) -> Dict:
        """
        Predict failure rate for a query based on similar questions

        IMPROVEMENT: Now uses weighted aggregation based on similarity scores

        Args:
            query: User's question
            model_name: Specific model to analyze (or aggregate across all)
            top_k_similar: Number of similar questions to consider
            domain: Optional domain filter

        Returns:
            Dict with failure predictions, similar questions, and statistics
        """

        # Find similar questions
        similar_questions = self.scorer.search(
            query=query,
            top_k=top_k_similar,
            query_domain=domain
        )

        # Aggregate performance across similar questions (WEIGHTED)
        model_performance = {}
        questions_with_perf = []
        similarity_scores = []  # Track scores for variance computation

        for sim_q in similar_questions:
            qid = sim_q['question_id']
            similarity_score = sim_q['score']

            # Try to match with performance data
            perf_id = None
            if str(qid) in self.performance_data:
                perf_id = str(qid)
            elif qid in self.performance_data:
                perf_id = qid
            elif qid.startswith('mmlu_pro_'):
                original_id = qid.replace('mmlu_pro_', '')
                if original_id in self.performance_data:
                    perf_id = original_id
                elif int(original_id) in self.performance_data:
                    perf_id = int(original_id)

            # Check if we have performance data for this question
            if perf_id:
                perf = self.performance_data[perf_id]

                questions_with_perf.append({
                    'question_id': qid,
                    'question_text': sim_q['question']['question_text'][:150],
                    'similarity_score': similarity_score,
                    'domain': sim_q['question']['domain'],
                    'models_tested': list(perf.keys()),
                    'model_results': perf
                })

                similarity_scores.append(similarity_score)

                # IMPROVEMENT: Weighted aggregation by model
                for model, result in perf.items():
                    if model not in model_performance:
                        model_performance[model] = {
                            'weighted_correct': 0.0,
                            'weighted_total': 0.0,
                            'count': 0,
                            'questions': []
                        }

                    # WEIGHTED: Use similarity score as weight
                    weight = similarity_score if self.use_weighted_similarity else 1.0

                    model_performance[model]['weighted_total'] += weight
                    if result.get('is_correct'):
                        model_performance[model]['weighted_correct'] += weight
                    model_performance[model]['count'] += 1

                    model_performance[model]['questions'].append({
                        'qid': qid,
                        'similarity': similarity_score,
                        'correct': result.get('is_correct'),
                        'weight': weight
                    })

        # Calculate failure rates (WEIGHTED)
        failure_rates = {}
        for model, data in model_performance.items():
            # WEIGHTED success rate
            weighted_success_rate = (data['weighted_correct'] / data['weighted_total']) if data['weighted_total'] > 0 else 0
            weighted_failure_rate = 1 - weighted_success_rate

            failure_rates[model] = {
                'failure_rate': weighted_failure_rate * 100,  # Percentage
                'success_rate': weighted_success_rate * 100,
                'weighted_correct': data['weighted_correct'],
                'weighted_total': data['weighted_total'],
                'count': data['count'],
                'confidence': self._compute_confidence(data['count'], top_k_similar, similarity_scores)
            }

        # Overall aggregated failure rate (WEIGHTED across all models)
        if model_performance:
            total_weighted_correct = sum(d['weighted_correct'] for d in model_performance.values())
            total_weighted_attempts = sum(d['weighted_total'] for d in model_performance.values())
            overall_success = total_weighted_correct / total_weighted_attempts if total_weighted_attempts > 0 else 0
            overall_failure = 1 - overall_success

            # Apply temperature scaling if enabled
            if self.use_temperature_scaling:
                # Convert to probability space
                prob_failure = overall_failure
                # Temperature scaling (will be calibrated)
                calibrated_prob = self._apply_temperature(prob_failure, self.temperature)
                calibrated_failure = calibrated_prob
                calibrated_success = 1 - calibrated_failure
            else:
                calibrated_failure = overall_failure
                calibrated_success = overall_success

            aggregated = {
                'overall_failure_rate': calibrated_failure * 100,
                'overall_success_rate': calibrated_success * 100,
                'raw_failure_rate': overall_failure * 100,  # Before temperature scaling
                'total_evaluations': sum(d['count'] for d in model_performance.values()),
                'models_evaluated': len(model_performance),
                'temperature': self.temperature if self.use_temperature_scaling else None,
                'weighted': self.use_weighted_similarity
            }
        else:
            aggregated = {
                'overall_failure_rate': None,
                'overall_success_rate': None,
                'raw_failure_rate': None,
                'total_evaluations': 0,
                'models_evaluated': 0,
                'warning': 'No benchmark performance data available for similar questions'
            }

        # Build result
        result = {
            'query': query,
            'similar_questions_found': len(similar_questions),
            'questions_with_performance_data': len(questions_with_perf),
            'coverage': len(questions_with_perf) / len(similar_questions) if similar_questions else 0,

            'aggregated_prediction': aggregated,
            'by_model': failure_rates,

            'similar_questions': questions_with_perf[:5],  # Top 5 for display

            'recommendation': self._generate_recommendation(aggregated, failure_rates, model_name),

            # NEW: Uncertainty estimates
            'uncertainty': self._estimate_uncertainty(similarity_scores, questions_with_perf) if questions_with_perf else None
        }

        return result

    def _compute_confidence(self, count: int, top_k: int, similarity_scores: List[float]) -> float:
        """
        Compute confidence in prediction

        IMPROVEMENT: Consider both coverage and similarity distribution
        """
        # Coverage component (how many similar questions have data)
        coverage = min(count / top_k, 1.0)

        # Similarity concentration (higher if top results are very similar)
        if similarity_scores:
            mean_sim = np.mean(similarity_scores)
            concentration = min(mean_sim, 1.0)
        else:
            concentration = 0.0

        # Combined confidence
        confidence = 0.6 * coverage + 0.4 * concentration

        return confidence

    def _estimate_uncertainty(self, similarity_scores: List[float], questions_with_perf: List[Dict]) -> Dict:
        """
        NEW: Estimate prediction uncertainty

        Returns aleatoric (data noise) and epistemic (model uncertainty) estimates
        """
        if not questions_with_perf:
            return {'total': 1.0, 'aleatoric': 1.0, 'epistemic': 1.0}

        # Simple uncertainty estimate based on:
        # 1. Similarity variance (epistemic - model uncertainty)
        # 2. Performance variance (aleatoric - data noise)

        if len(similarity_scores) > 1:
            # Epistemic: variance in similarity scores
            # (lower similarity = higher uncertainty about relevance)
            epistemic = 1.0 - np.mean(similarity_scores)
        else:
            epistemic = 0.5

        # Aleatoric: variance in actual performance on similar questions
        # Extract failure rates for similar questions
        failure_rates_observed = []
        for q in questions_with_perf:
            model_results = q['model_results']
            n_correct = sum(1 for r in model_results.values() if r.get('is_correct'))
            n_total = len(model_results)
            failure_rate = 1.0 - (n_correct / n_total) if n_total > 0 else 0.5
            failure_rates_observed.append(failure_rate)

        if len(failure_rates_observed) > 1:
            aleatoric = np.std(failure_rates_observed)
        else:
            aleatoric = 0.5

        total = epistemic + aleatoric

        return {
            'total': total,
            'epistemic': epistemic,
            'aleatoric': aleatoric,
            'interpretation': self._interpret_uncertainty(epistemic, aleatoric)
        }

    def _interpret_uncertainty(self, epistemic: float, aleatoric: float) -> str:
        """Provide actionable interpretation of uncertainty"""
        if epistemic > aleatoric * 2:
            return "HIGH_MODEL_UNCERTAINTY: Low similarity to benchmark questions. Consider gathering more data in this domain."
        elif aleatoric > epistemic * 2:
            return "HIGH_DATA_NOISE: Similar questions have variable outcomes. This is inherently difficult."
        else:
            return "BALANCED_UNCERTAINTY: Standard prediction confidence applies."

    def _apply_temperature(self, prob: float, temperature: float) -> float:
        """
        Apply temperature scaling to probability

        For regression (not classification), we use a simple rescaling
        """
        # Clip to valid range
        prob = np.clip(prob, 0.01, 0.99)

        # Simple temperature scaling for regression
        # Higher temperature = more conservative (closer to 0.5)
        # Lower temperature = more confident (closer to extremes)
        scaled = 0.5 + (prob - 0.5) / temperature

        return np.clip(scaled, 0.0, 1.0)

    def _generate_recommendation(self, aggregated, failure_rates, target_model):
        """Generate recommendation based on failure rates"""

        if not failure_rates:
            return {
                'level': 'UNKNOWN',
                'message': 'No benchmark data available for similar questions. Proceed with caution.',
                'suggested_action': 'Consider manual verification or testing on similar questions first.'
            }

        overall_failure = aggregated.get('overall_failure_rate', 0)

        if overall_failure is None:
            level = 'UNKNOWN'
            message = 'Insufficient data for prediction'
            action = 'Test manually'

        elif overall_failure < 20:
            level = 'LOW_RISK'
            message = f'Low failure risk ({overall_failure:.1f}% average failure rate on similar questions)'
            action = 'Proceed normally'

        elif overall_failure < 40:
            level = 'MODERATE_RISK'
            message = f'Moderate failure risk ({overall_failure:.1f}% average failure rate)'
            action = 'Consider adding verification or using a stronger model'

        elif overall_failure < 60:
            level = 'HIGH_RISK'
            message = f'High failure risk ({overall_failure:.1f}% average failure rate)'
            action = 'Recommend: Use best available model, add human verification, or break down the task'

        else:
            level = 'VERY_HIGH_RISK'
            message = f'Very high failure risk ({overall_failure:.1f}% average failure rate)'
            action = 'CAUTION: This type of question has consistently failed. Consider alternative approaches.'

        # Model-specific recommendation
        if target_model and target_model in failure_rates:
            model_failure = failure_rates[target_model]['failure_rate']
            message += f" | {target_model}: {model_failure:.1f}% failure rate"

        # Add temperature scaling note if enabled
        if self.use_temperature_scaling and aggregated.get('raw_failure_rate') is not None:
            raw = aggregated['raw_failure_rate']
            if abs(overall_failure - raw) > 2:
                message += f" (calibrated from {raw:.1f}%)"

        return {
            'level': level,
            'message': message,
            'suggested_action': action,
            'overall_failure_rate': overall_failure
        }

    def learn_temperature(self, calibration_questions: List[Dict]):
        """
        Learn optimal temperature parameter from calibration set

        Args:
            calibration_questions: List of dicts with 'text' and 'actual_failure_rate'
        """
        from scipy.optimize import minimize

        print(f"\nLearning temperature from {len(calibration_questions)} calibration questions...")

        def calibration_error(T):
            """Expected Calibration Error"""
            predictions = []
            actuals = []

            for q in calibration_questions:
                # Get raw prediction (without temperature)
                old_temp = self.temperature
                old_use_temp = self.use_temperature_scaling

                self.temperature = 1.0
                self.use_temperature_scaling = False

                pred = self.predict_failure_rate(q['text'], top_k_similar=20)
                raw_failure = pred['aggregated_prediction'].get('overall_failure_rate')

                self.temperature = old_temp
                self.use_temperature_scaling = old_use_temp

                if raw_failure is not None:
                    # Apply temperature
                    prob_failure = raw_failure / 100.0
                    calibrated_prob = self._apply_temperature(prob_failure, T)

                    predictions.append(calibrated_prob)
                    actuals.append(q['actual_failure_rate'] / 100.0)

            if len(predictions) < 10:
                return 1.0  # Not enough data

            # Compute ECE
            ece = self._compute_ece(np.array(predictions), np.array(actuals), n_bins=10)
            return ece

        # Optimize temperature
        result = minimize(calibration_error, x0=1.0, bounds=[(0.1, 5.0)], method='L-BFGS-B')
        optimal_temp = result.x[0]

        print(f"✅ Optimal temperature: {optimal_temp:.3f}")
        print(f"   Calibration error (ECE): {result.fun:.3f}")

        self.temperature = optimal_temp
        return optimal_temp

    def _compute_ece(self, predictions: np.ndarray, actuals: np.ndarray, n_bins: int = 10) -> float:
        """
        Compute Expected Calibration Error

        Measures how well predicted probabilities match actual frequencies
        """
        # Ensure arrays are 1D
        predictions = np.asarray(predictions).flatten()
        actuals = np.asarray(actuals).flatten()

        if len(predictions) == 0:
            return 0.0

        # Bin predictions
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]

        ece = 0.0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            in_bin = (predictions >= bin_lower) & (predictions < bin_upper)

            if np.sum(in_bin) > 0:
                avg_pred = np.mean(predictions[in_bin])
                avg_actual = np.mean(actuals[in_bin])
                bin_weight = np.sum(in_bin) / len(predictions)
                ece += bin_weight * abs(avg_pred - avg_actual)

        return ece

    def compare_models(self, query: str, top_k_similar: int = 10, domain: Optional[str] = None) -> Dict:
        """Compare how different models perform on similar questions"""

        prediction = self.predict_failure_rate(query, top_k_similar=top_k_similar, domain=domain)

        # Rank models by success rate
        model_rankings = []
        for model, data in prediction['by_model'].items():
            model_rankings.append({
                'model': model,
                'success_rate': data['success_rate'],
                'failure_rate': data['failure_rate'],
                'weighted_correct': data['weighted_correct'],
                'weighted_total': data['weighted_total'],
                'count': data['count'],
                'confidence': data['confidence']
            })

        model_rankings.sort(key=lambda x: x['success_rate'], reverse=True)

        return {
            'query': query,
            'model_rankings': model_rankings,
            'best_model': model_rankings[0] if model_rankings else None,
            'worst_model': model_rankings[-1] if model_rankings else None,
            'performance_gap': (model_rankings[0]['success_rate'] - model_rankings[-1]['success_rate']) if len(model_rankings) >= 2 else 0
        }


if __name__ == "__main__":
    print("="*80)
    print("IMPROVED FAILURE RATE PREDICTOR - DEMO")
    print("Phase 1: Weighted Similarity + Temperature Scaling")
    print("="*80)

    # Initialize predictor
    predictor = ImprovedFailureRatePredictor(
        use_weighted_similarity=True,
        use_temperature_scaling=True
    )

    # Test queries
    test_queries = [
        {
            "query": "A highway patrol officer stopped a driver for speeding. Is the search legal?",
            "domain": "law",
            "description": "Legal reasoning question"
        },
        {
            "query": "Explain the principles of business ethics in corporate management",
            "domain": "business",
            "description": "Business ethics question"
        },
        {
            "query": "Calculate the eigenvalues of a 3x3 matrix",
            "domain": "math",
            "description": "Mathematical computation"
        }
    ]

    for i, test in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {test['description']}")
        print(f"{'='*80}")
        print(f"\nQuery: \"{test['query']}\"")
        print(f"Domain: {test['domain']}")

        # Predict failure rate
        result = predictor.predict_failure_rate(
            query=test['query'],
            domain=test['domain'],
            top_k_similar=10
        )

        print(f"\n📊 FAILURE PREDICTION:")
        print(f"   Similar questions found: {result['similar_questions_found']}")
        print(f"   With performance data: {result['questions_with_performance_data']}")
        print(f"   Coverage: {result['coverage']*100:.0f}%")

        agg = result['aggregated_prediction']
        failure_rate = agg.get('overall_failure_rate')
        success_rate = agg.get('overall_success_rate')
        raw_failure = agg.get('raw_failure_rate')

        if failure_rate is not None:
            print(f"\n   Calibrated Failure Rate: {failure_rate:.1f}%")
            if raw_failure is not None and abs(failure_rate - raw_failure) > 0.1:
                print(f"   Raw Failure Rate: {raw_failure:.1f}% (before temperature scaling)")
            print(f"   Success Rate: {success_rate:.1f}%")
        else:
            print(f"\n   Failure Rate: N/A (no benchmark data)")

        print(f"   Based on: {agg.get('total_evaluations', 0)} evaluations across {agg.get('models_evaluated', 0)} models")
        print(f"   Weighted aggregation: {agg.get('weighted', False)}")

        # Uncertainty
        if result.get('uncertainty'):
            unc = result['uncertainty']
            print(f"\n🎲 UNCERTAINTY ANALYSIS:")
            print(f"   Total uncertainty: {unc['total']:.2f}")
            print(f"   Epistemic (model): {unc['epistemic']:.2f}")
            print(f"   Aleatoric (data): {unc['aleatoric']:.2f}")
            print(f"   Interpretation: {unc['interpretation']}")

        print(f"\n🤖 BY MODEL:")
        for model, data in sorted(result['by_model'].items(), key=lambda x: x[1]['failure_rate']):
            print(f"   {model:<40} Failure: {data['failure_rate']:>5.1f}%  Success: {data['success_rate']:>5.1f}%  (n={data['count']}, conf={data['confidence']:.2f})")

        rec = result['recommendation']
        print(f"\n⚠️  RECOMMENDATION: {rec['level']}")
        print(f"   {rec['message']}")
        print(f"   Action: {rec['suggested_action']}")

    print("\n" + "="*80)
    print("✅ Demo Complete!")
    print("="*80)
