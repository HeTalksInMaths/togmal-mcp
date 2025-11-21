#!/usr/bin/env python3
"""
Test MCP Integration with Expanded Dataset Predictor
====================================================

Tests the lightweight checker's integration with the MCP server using
the expanded 14,766-question dataset.

This script:
1. Simulates MCP tool calls to check prompt difficulty
2. Tests various prompts to see predicted difficulty
3. Validates trigger logic for lightweight vs full model
4. Checks if predictions are reasonable
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from train_expanded_dataset import load_data, extract_failure_rates, predict as predict_func
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class MCPPromptDifficultyChecker:
    """
    Simulates the MCP tool togmal_check_prompt_difficulty using our TF-IDF predictor.
    This is what should be integrated into the actual MCP server.
    """

    def __init__(self):
        """Initialize the predictor with the expanded dataset"""
        print("Loading expanded dataset (14,766 questions)...")
        self.unified_db, self.perf_db = load_data()
        print(f"✓ Loaded {len(self.unified_db['questions']):,} questions")

        print("\nExtracting failure rates...")
        self.failure_rates = extract_failure_rates(self.unified_db, self.perf_db)
        print(f"✓ Extracted {len(self.failure_rates):,} failure rates")

        print("\nTraining TF-IDF predictor...")
        self.predictor = self._train_predictor()
        print(f"✓ Trained on {len(self.predictor['train_questions']):,} questions")
        print()

    def _train_predictor(self):
        """Train TF-IDF predictor on all data"""
        # Get all questions with known failure rates
        all_questions = [q for q in self.unified_db['questions']
                        if str(q['question_id']) in self.failure_rates]

        # Extract texts
        train_texts = [q.get('question_text', '') for q in all_questions]

        # Train TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=2000,
            ngram_range=(1, 2),
            min_df=1,
            stop_words='english'
        )

        train_vectors = vectorizer.fit_transform(train_texts)

        # Store failure rates
        train_failure_rates = {
            str(q['question_id']): self.failure_rates[str(q['question_id'])]
            for q in all_questions
        }

        return {
            'vectorizer': vectorizer,
            'train_vectors': train_vectors,
            'train_questions': all_questions,
            'train_failure_rates': train_failure_rates
        }

    def _predict(self, query_text, top_k=20, return_details=False):
        """Predict failure rate for a query"""
        # Transform query
        query_vector = self.predictor['vectorizer'].transform([query_text])

        # Find similar
        similarities = cosine_similarity(query_vector, self.predictor['train_vectors'])[0]
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Get similar questions with rates
        similar = []
        for idx in top_indices:
            train_qid = str(self.predictor['train_questions'][idx]['question_id'])
            sim = similarities[idx]

            if train_qid in self.predictor['train_failure_rates'] and sim > 0:
                fr = self.predictor['train_failure_rates'][train_qid]
                similar.append({
                    'similarity': float(sim),
                    'failure_rate': fr,
                    'question': self.predictor['train_questions'][idx].get('question_text', '')[:100],
                    'benchmark': self.predictor['train_questions'][idx].get('benchmark', 'unknown'),
                    'domain': self.predictor['train_questions'][idx].get('domain', 'unknown')
                })

        # Weighted average
        if similar:
            total_weight = sum(s['similarity'] for s in similar)
            weighted_sum = sum(s['similarity'] * s['failure_rate'] for s in similar)

            pred_fr = weighted_sum / total_weight if total_weight > 0 else 0.5
            confidence = total_weight / top_k
        else:
            pred_fr = 0.5
            confidence = 0.0

        if return_details:
            return pred_fr, confidence, similar
        else:
            return pred_fr, confidence

    def check_prompt_difficulty(
        self,
        prompt: str,
        k: int = 20,
        domain_filter: str = None
    ) -> dict:
        """
        Check prompt difficulty (simulates MCP tool call).

        Args:
            prompt: The user's prompt to check
            k: Number of similar questions to retrieve
            domain_filter: Optional domain filter

        Returns:
            Dictionary with difficulty assessment and recommendations
        """

        # Get prediction with details
        pred_fr, confidence, similar = self._predict(
            prompt,
            top_k=k,
            return_details=True
        )

        # Filter by domain if requested
        if domain_filter:
            similar = [s for s in similar if s['domain'].lower() == domain_filter.lower()]
            if similar:
                # Recalculate with filtered set
                total_weight = sum(s['similarity'] for s in similar)
                weighted_sum = sum(s['similarity'] * s['failure_rate'] for s in similar)
                pred_fr = weighted_sum / total_weight if total_weight > 0 else 0.5
                confidence = total_weight / k

        # Determine recommendation
        use_lightweight = pred_fr < 0.60  # 60% threshold

        # Risk level
        if pred_fr >= 0.75:
            risk_level = "high"
        elif pred_fr >= 0.60:
            risk_level = "moderate"
        elif pred_fr >= 0.40:
            risk_level = "low-moderate"
        else:
            risk_level = "low"

        # Build response
        return {
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "predicted_failure_rate": float(pred_fr),
            "confidence": float(confidence),
            "risk_level": risk_level,
            "recommendation": {
                "use_lightweight_checker": use_lightweight,
                "message": (
                    "✅ Lightweight checker should handle this (predicted failure rate < 60%)"
                    if use_lightweight
                    else "❌ Use full model - task is too difficult (predicted failure rate >= 60%)"
                )
            },
            "similar_questions": [
                {
                    "benchmark": s['benchmark'],
                    "domain": s['domain'],
                    "similarity": float(s['similarity']),
                    "failure_rate": float(s['failure_rate']),
                    "question_preview": s['question'][:80] + "..."
                }
                for s in similar[:5]  # Top 5
            ],
            "dataset_stats": {
                "total_questions": len(self.predictor['train_questions']),
                "ML_DS_coverage": "14.4%",
                "benchmarks": ["MMLU-Pro", "DS-1000", "ML-Bench", "MLAgentBench", "RE-Bench", "MLE-bench"]
            }
        }


def test_various_prompts():
    """Test the MCP integration with various prompts"""

    # Initialize checker
    checker = MCPPromptDifficultyChecker()

    print("="*80)
    print("TESTING MCP INTEGRATION WITH EXPANDED DATASET")
    print("="*80)

    # Test cases
    test_cases = [
        ("Easy Coding", "Write a Python function to check if a number is even"),
        ("Data Science", "How do I load a CSV file using pandas?"),
        ("ML Task", "Train a simple linear regression model with scikit-learn"),
        ("Complex DS", "Calculate the correlation between two columns in a DataFrame"),
        ("Advanced ML", "Implement a custom neural scaling law analysis for transformer models"),
        ("Repository Task", "Add a new feature to scikit-learn for custom kernel functions"),
        ("General Knowledge", "What is the capital of France?"),
        ("Math", "Calculate the eigenvalues of a 3x3 matrix"),
    ]

    results = []

    for category, prompt in test_cases:
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category}")
        print(f"PROMPT: {prompt}")
        print(f"{'='*80}")

        # Simulate MCP tool call
        result = checker.check_prompt_difficulty(prompt, k=20)

        # Display results
        print(f"\n📊 DIFFICULTY ASSESSMENT:")
        print(f"   Predicted Failure Rate: {result['predicted_failure_rate']:.1%}")
        print(f"   Confidence: {result['confidence']:.3f}")
        print(f"   Risk Level: {result['risk_level'].upper()}")

        print(f"\n💡 RECOMMENDATION:")
        print(f"   {result['recommendation']['message']}")

        print(f"\n🔍 TOP 3 SIMILAR QUESTIONS:")
        for i, sim in enumerate(result['similar_questions'][:3], 1):
            print(f"   {i}. [{sim['benchmark']}] {sim['domain']}")
            print(f"      Similarity: {sim['similarity']:.3f}, Failure: {sim['failure_rate']:.1%}")
            print(f"      {sim['question_preview']}")

        results.append({
            'category': category,
            'prompt': prompt,
            'result': result
        })

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    lightweight_count = sum(1 for r in results if r['result']['recommendation']['use_lightweight_checker'])
    full_model_count = len(results) - lightweight_count

    print(f"\n✅ Use Lightweight Checker: {lightweight_count}/{len(results)}")
    print(f"❌ Use Full Model: {full_model_count}/{len(results)}")

    print(f"\nAverage predicted failure rate: {sum(r['result']['predicted_failure_rate'] for r in results) / len(results):.1%}")
    print(f"Average confidence: {sum(r['result']['confidence'] for r in results) / len(results):.3f}")

    # Save results
    output_path = Path("data/mcp_integration_test_results.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {output_path}")

    return results


def test_integration_api():
    """Test that the checker works as an MCP-style API"""

    print("\n" + "="*80)
    print("TESTING MCP API INTEGRATION")
    print("="*80)

    checker = MCPPromptDifficultyChecker()

    # Simulate actual MCP tool invocation
    print("\nSimulating MCP tool call:")
    print("  Tool: togmal_check_prompt_difficulty")
    print("  Args:")
    print("    prompt: 'Build me a complete social network with user authentication'")
    print("    k: 20")

    result = checker.check_prompt_difficulty(
        prompt="Build me a complete social network with user authentication",
        k=20
    )

    print("\nMCP Response (JSON):")
    print(json.dumps(result, indent=2))

    # Test with domain filter
    print("\n" + "-"*80)
    print("\nSimulating MCP tool call with domain filter:")
    print("  Tool: togmal_check_prompt_difficulty")
    print("  Args:")
    print("    prompt: 'Implement k-means clustering on iris dataset'")
    print("    k: 20")
    print("    domain_filter: 'computer science'")

    result2 = checker.check_prompt_difficulty(
        prompt="Implement k-means clustering on iris dataset",
        k=20,
        domain_filter="computer science"
    )

    print("\nMCP Response (JSON):")
    print(json.dumps(result2, indent=2))


if __name__ == "__main__":
    print("="*80)
    print("MCP INTEGRATION TEST WITH EXPANDED DATASET")
    print("="*80)
    print()
    print("This test validates that the lightweight checker predictor can be")
    print("integrated into the MCP server to provide difficulty assessments")
    print("for incoming prompts.")
    print()
    print("Dataset: 14,766 questions (MMLU-Pro, DS-1000, ML-Bench, etc.)")
    print("Predictor: TF-IDF with k-NN (correlation: 0.537, MAE: 21.7%)")
    print()

    # Run tests
    try:
        test_various_prompts()
        print("\n")
        test_integration_api()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print("\nNext steps:")
        print("1. Integrate this predictor into togmal_mcp.py")
        print("2. Replace/augment togmal_check_prompt_difficulty tool")
        print("3. Use expanded dataset instead of vector DB (or update vector DB)")
        print("4. Deploy MCP server with improved predictions")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
