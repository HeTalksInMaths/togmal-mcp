#!/usr/bin/env python3
"""
Test Sample Prompts with Lightweight Checker
=============================================

Tests various prompts to see:
1. What difficulty the checker predicts
2. Whether it should trigger the lightweight checker
3. What confidence level it has

Trigger Logic:
- If predicted failure rate >= 60%: Use full model (too hard for lightweight)
- If predicted failure rate < 60%: Use lightweight checker (should handle it)
"""

import json
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_data():
    """Load the expanded unified database"""
    with open('data/unified_database_with_real_mle.json') as f:
        unified_db = json.load(f)

    with open('data/model_performance_database.json') as f:
        perf_db = json.load(f)

    return unified_db, perf_db


def extract_failure_rates(unified_db, perf_db):
    """Extract failure rates"""
    failure_rates = {}

    # From unified DB
    for q in unified_db['questions']:
        qid = str(q['question_id'])
        if 'success_rate' in q and q['success_rate'] is not None:
            failure_rate = 1.0 - q['success_rate']
            failure_rates[qid] = failure_rate

    # Override with performance DB
    for qid, data in perf_db['questions'].items():
        if 'failure_rate' in data:
            failure_rates[str(qid)] = data['failure_rate']

    return failure_rates


def train_predictor(unified_db, failure_rates):
    """Train TF-IDF predictor on all data"""
    print("Training predictor on full dataset...")

    # Get all questions with known failure rates
    all_questions = [q for q in unified_db['questions']
                    if str(q['question_id']) in failure_rates]

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
        str(q['question_id']): failure_rates[str(q['question_id'])]
        for q in all_questions
    }

    print(f"  Trained on {len(all_questions):,} questions")

    return {
        'vectorizer': vectorizer,
        'train_vectors': train_vectors,
        'train_questions': all_questions,
        'train_failure_rates': train_failure_rates
    }


def predict(predictor, query_text, top_k=20, return_details=False):
    """Predict failure rate for a query"""

    # Transform query
    query_vector = predictor['vectorizer'].transform([query_text])

    # Find similar
    similarities = cosine_similarity(query_vector, predictor['train_vectors'])[0]
    top_indices = np.argsort(similarities)[::-1][:top_k]

    # Get similar questions with rates
    similar = []
    for idx in top_indices:
        train_qid = str(predictor['train_questions'][idx]['question_id'])
        sim = similarities[idx]

        if train_qid in predictor['train_failure_rates'] and sim > 0:
            fr = predictor['train_failure_rates'][train_qid]
            similar.append({
                'similarity': float(sim),
                'failure_rate': fr,
                'question': predictor['train_questions'][idx].get('question_text', '')[:100],
                'benchmark': predictor['train_questions'][idx].get('benchmark', 'unknown'),
                'domain': predictor['train_questions'][idx].get('domain', 'unknown')
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


def should_use_lightweight(failure_rate, threshold=0.60):
    """
    Determine if lightweight checker should be used

    Returns:
        - True: Use lightweight checker (task is easy/medium)
        - False: Use full model (task is too hard)
    """
    return failure_rate < threshold


def test_prompts():
    """Test various sample prompts"""

    # Load and train
    print("="*80)
    print("LOADING AND TRAINING PREDICTOR")
    print("="*80)
    unified_db, perf_db = load_data()
    failure_rates = extract_failure_rates(unified_db, perf_db)
    predictor = train_predictor(unified_db, failure_rates)

    # Define test prompts
    test_cases = [
        {
            'category': 'Easy Coding',
            'prompts': [
                "Write a Python function to check if a number is even",
                "Create a function that reverses a string",
                "Write a function to find the maximum element in a list",
                "How do I print 'Hello World' in Python?"
            ]
        },
        {
            'category': 'Medium Coding',
            'prompts': [
                "Implement a binary search algorithm in Python",
                "Write a function to detect cycles in a linked list",
                "Create a LRU cache implementation",
                "Implement merge sort in Python"
            ]
        },
        {
            'category': 'Data Science',
            'prompts': [
                "How do I load a CSV file using pandas?",
                "Calculate the correlation between two columns in a DataFrame",
                "How to handle missing values in pandas?",
                "Create a scatter plot with matplotlib"
            ]
        },
        {
            'category': 'Machine Learning',
            'prompts': [
                "Train a simple linear regression model with scikit-learn",
                "How to split data into train and test sets?",
                "Implement k-means clustering on iris dataset",
                "Fine-tune a BERT model for text classification"
            ]
        },
        {
            'category': 'Advanced ML/Research',
            'prompts': [
                "Implement a custom neural scaling law analysis for transformer models",
                "Optimize GPU kernel for custom attention mechanism",
                "Detect dataset contamination in pre-training corpus",
                "Implement distributed training with gradient checkpointing and ZeRO optimization"
            ]
        },
        {
            'category': 'Complex Math/Science',
            'prompts': [
                "Prove the Pythagorean theorem",
                "Solve the differential equation dy/dx = xy",
                "Explain quantum entanglement and derive the Bell inequality",
                "Calculate the eigenvalues of a 3x3 matrix"
            ]
        },
        {
            'category': 'General Knowledge',
            'prompts': [
                "What is the capital of France?",
                "Explain how photosynthesis works",
                "Who wrote Romeo and Juliet?",
                "What is the theory of relativity?"
            ]
        },
        {
            'category': 'Repository-Level Tasks',
            'prompts': [
                "Add a new feature to scikit-learn for custom kernel functions",
                "Implement a new optimizer in PyTorch",
                "Create a custom TensorFlow layer with gradient checkpointing",
                "Add support for nested DataFrames in pandas"
            ]
        }
    ]

    # Test each category
    print("\n" + "="*80)
    print("TESTING SAMPLE PROMPTS")
    print("="*80)

    results_by_category = {}

    for test_case in test_cases:
        category = test_case['category']
        prompts = test_case['prompts']

        print(f"\n{'='*80}")
        print(f"{category.upper()}")
        print(f"{'='*80}")

        category_results = []

        for i, prompt in enumerate(prompts, 1):
            pred_fr, confidence, similar = predict(predictor, prompt, return_details=True)
            use_lightweight = should_use_lightweight(pred_fr)

            print(f"\n{i}. {prompt}")
            print(f"   {'─'*75}")
            print(f"   Predicted failure rate: {pred_fr:.1%}")
            print(f"   Confidence: {confidence:.3f}")
            print(f"   Recommendation: {'✅ Use LIGHTWEIGHT checker' if use_lightweight else '❌ Use FULL model (too hard)'}")

            # Show top 3 similar questions
            print(f"\n   Top 3 similar questions:")
            for j, sim_q in enumerate(similar[:3], 1):
                print(f"   {j}. [{sim_q['benchmark']}] Similarity: {sim_q['similarity']:.3f}, "
                      f"Failure: {sim_q['failure_rate']:.1%}")
                print(f"      {sim_q['question'][:80]}...")

            category_results.append({
                'prompt': prompt,
                'predicted_failure_rate': pred_fr,
                'confidence': confidence,
                'use_lightweight': use_lightweight,
                'similar_count': len(similar)
            })

        results_by_category[category] = category_results

    # Summary
    print("\n" + "="*80)
    print("SUMMARY BY CATEGORY")
    print("="*80)

    print(f"\n{'Category':<25} {'Avg FR':>10} {'Avg Conf':>10} {'Use Light':>12} {'Use Full':>10}")
    print("─"*80)

    for category, results in results_by_category.items():
        avg_fr = np.mean([r['predicted_failure_rate'] for r in results])
        avg_conf = np.mean([r['confidence'] for r in results])
        num_lightweight = sum(1 for r in results if r['use_lightweight'])
        num_full = sum(1 for r in results if not r['use_lightweight'])

        print(f"{category:<25} {avg_fr:>10.1%} {avg_conf:>10.3f} {num_lightweight:>12} {num_full:>10}")

    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    print("""
TRIGGER THRESHOLD: 60% failure rate

✅ USE LIGHTWEIGHT CHECKER for:
   - Easy coding tasks (FizzBuzz, string reversal, etc.)
   - Basic data science (pandas operations, plotting)
   - Simple ML tasks (train/test split, basic sklearn)
   - General knowledge questions
   - Medium difficulty coding (binary search, linked lists)

❌ USE FULL MODEL for:
   - Advanced ML/Research tasks (scaling laws, GPU optimization)
   - Repository-level feature additions
   - Complex math/science proofs
   - Fine-tuning large models
   - Distributed training optimization

⚠️  BORDERLINE CASES (~55-65% failure):
   - Custom implementations in ML frameworks
   - Complex algorithms with optimization
   - Advanced pandas/numpy operations

CONFIDENCE INTERPRETATION:
   - High (>0.5): Many similar questions in training, reliable prediction
   - Medium (0.3-0.5): Some similar questions, moderate reliability
   - Low (<0.3): Few similar questions, less reliable
""")

    # Save results
    output = {
        'test_date': '2025-11-21',
        'dataset_size': len(predictor['train_questions']),
        'threshold': 0.60,
        'results_by_category': {
            category: {
                'prompts': [r['prompt'] for r in results],
                'avg_failure_rate': float(np.mean([r['predicted_failure_rate'] for r in results])),
                'avg_confidence': float(np.mean([r['confidence'] for r in results])),
                'num_lightweight': sum(1 for r in results if r['use_lightweight']),
                'num_full': sum(1 for r in results if not r['use_lightweight']),
                'details': results
            }
            for category, results in results_by_category.items()
        }
    }

    with open('data/sample_prompts_test_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Results saved to: data/sample_prompts_test_results.json")

    return results_by_category


if __name__ == "__main__":
    test_prompts()
