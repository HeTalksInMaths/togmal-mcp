#!/usr/bin/env python3
"""
LLM Failure Rate Predictor
===========================

Predicts likely LLM failure rate for a given question based on:
1. Semantic similarity to benchmark questions
2. Model performance on similar questions
3. Aggregated statistics across multiple models

This is the core of the ToGMAL taxonomy - showing likely failure modes.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from local_embedding_scorer import LocalSemanticScorer


class FailureRatePredictor:
    """Predicts LLM failure rates based on similar question performance"""

    def __init__(self, questions_db_path: str = "./data/unified_database_with_mmlu_pro.json",
                 performance_db_path: str = "./data/model_performance_database.json"):
        """
        Args:
            questions_db_path: Path to unified questions database
            performance_db_path: Path to model performance database
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

    def predict_failure_rate(
        self,
        query: str,
        model_name: Optional[str] = None,
        top_k_similar: int = 10,
        domain: Optional[str] = None
    ) -> Dict:
        """
        Predict failure rate for a query based on similar questions

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

        # Aggregate performance across similar questions
        model_performance = {}
        questions_with_perf = []

        for sim_q in similar_questions:
            qid = sim_q['question_id']

            # Try to match with performance data
            # Performance data has integer IDs, our DB has "mmlu_pro_{id}" format
            perf_id = None
            if str(qid) in self.performance_data:
                perf_id = str(qid)
            elif qid in self.performance_data:
                perf_id = qid
            elif qid.startswith('mmlu_pro_'):
                # Extract original ID
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
                    'similarity_score': sim_q['score'],
                    'domain': sim_q['question']['domain'],
                    'models_tested': list(perf.keys()),
                    'model_results': perf
                })

                # Aggregate by model
                for model, result in perf.items():
                    if model not in model_performance:
                        model_performance[model] = {
                            'correct': 0,
                            'total': 0,
                            'questions': []
                        }

                    model_performance[model]['total'] += 1
                    if result.get('is_correct'):
                        model_performance[model]['correct'] += 1

                    model_performance[model]['questions'].append({
                        'qid': qid,
                        'similarity': sim_q['score'],
                        'correct': result.get('is_correct')
                    })

        # Calculate failure rates
        failure_rates = {}
        for model, data in model_performance.items():
            success_rate = (data['correct'] / data['total']) if data['total'] > 0 else 0
            failure_rate = 1 - success_rate

            failure_rates[model] = {
                'failure_rate': failure_rate * 100,  # Percentage
                'success_rate': success_rate * 100,
                'correct': data['correct'],
                'total': data['total'],
                'confidence': min(data['total'] / top_k_similar, 1.0)  # Confidence based on coverage
            }

        # Overall aggregated failure rate (across all models)
        if model_performance:
            total_correct = sum(d['correct'] for d in model_performance.values())
            total_attempts = sum(d['total'] for d in model_performance.values())
            overall_success = total_correct / total_attempts if total_attempts > 0 else 0
            overall_failure = 1 - overall_success

            aggregated = {
                'overall_failure_rate': overall_failure * 100,
                'overall_success_rate': overall_success * 100,
                'total_evaluations': total_attempts,
                'models_evaluated': len(model_performance)
            }
        else:
            aggregated = {
                'overall_failure_rate': None,
                'overall_success_rate': None,
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

            'recommendation': self._generate_recommendation(aggregated, failure_rates, model_name)
        }

        return result

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

        return {
            'level': level,
            'message': message,
            'suggested_action': action,
            'overall_failure_rate': overall_failure
        }

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
                'correct': data['correct'],
                'total': data['total'],
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
    print("FAILURE RATE PREDICTOR - DEMO")
    print("="*80)

    # Initialize predictor
    predictor = FailureRatePredictor()

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

        if failure_rate is not None:
            print(f"\n   Overall Failure Rate: {failure_rate:.1f}%")
            print(f"   Overall Success Rate: {success_rate:.1f}%")
        else:
            print(f"\n   Overall Failure Rate: N/A (no benchmark data)")
            print(f"   Overall Success Rate: N/A")

        print(f"   Based on: {agg.get('total_evaluations', 0)} evaluations across {agg.get('models_evaluated', 0)} models")

        print(f"\n🤖 BY MODEL:")
        for model, data in sorted(result['by_model'].items(), key=lambda x: x[1]['failure_rate']):
            print(f"   {model:<40} Failure: {data['failure_rate']:>5.1f}%  Success: {data['success_rate']:>5.1f}%  ({data['correct']}/{data['total']})")

        rec = result['recommendation']
        print(f"\n⚠️  RECOMMENDATION: {rec['level']}")
        print(f"   {rec['message']}")
        print(f"   Action: {rec['suggested_action']}")

    print("\n" + "="*80)
    print("✅ Demo Complete!")
    print("="*80)
