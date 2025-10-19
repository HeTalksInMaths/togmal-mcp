#!/usr/bin/env python3
"""
Quick test with real data - sample 1000 questions for faster testing
"""

import json
from pathlib import Path
from benchmark_vector_db import BenchmarkVectorDB, BenchmarkQuestion
import random

def load_sample_mmlu_data(n_samples=1000):
    """Load a sample of real MMLU questions"""
    print(f"Loading sample of {n_samples} real MMLU questions...")
    
    with open("./data/benchmark_results/mmlu_real_results.json") as f:
        data = json.load(f)
    
    # Sample questions
    all_qids = list(data['questions'].keys())
    sampled_qids = random.sample(all_qids, min(n_samples, len(all_qids)))
    
    questions = []
    for qid in sampled_qids:
        q = data['questions'][qid]
        questions.append(BenchmarkQuestion(
            question_id=q['question_id'],
            source_benchmark=q['source_benchmark'],
            domain=q['domain'],
            question_text=q['question_text'],
            correct_answer="",  # Not needed for vector DB
            choices=q.get('choices'),
            success_rate=q['success_rate'],
            difficulty_score=1.0 - q['success_rate'],
            difficulty_label=q['difficulty_label'],
            num_models_tested=q['num_models_tested']
        ))
    
    print(f"✓ Loaded {len(questions)} sampled questions")
    return questions


def quick_test():
    """Quick test with sampled real data"""
    
    # Initialize fresh database
    db = BenchmarkVectorDB(
        db_path=Path("./data/benchmark_vector_db"),
        embedding_model="all-MiniLM-L6-v2"
    )
    
    # Load sample data
    questions = load_sample_mmlu_data(1000)
    
    # Index questions (much faster with 1000 vs 14000)
    print("\nIndexing into vector database...")
    db.index_questions(questions)
    
    # Get stats
    stats = db.get_statistics()
    print(f"\n📊 Database Statistics:")
    print(f"  Total Questions: {stats['total_questions']}")
    print(f"  Difficulty Distribution: {stats.get('difficulty_levels', {})}")
    
    # Test with diverse prompts
    test_prompts = [
        # Should be HARD (physics/abstract math)
        "Calculate the quantum correction to the partition function for a 3D harmonic oscillator",
        "Prove that there are infinitely many prime numbers",
        
        # Should be MODERATE (reasoning)
        "Diagnose a patient with acute chest pain and shortness of breath",
        "Explain the legal doctrine of precedent in common law systems",
        
        # Should be EASY (basic knowledge)
        "What is 2 + 2?",
        "What is the capital of France?",
    ]
    
    print(f"\n🧪 Testing {len(test_prompts)} diverse prompts:")
    print("="*80)
    
    for prompt in test_prompts:
        result = db.query_similar_questions(prompt, k=5)
        
        print(f"\n📝 '{prompt}'")
        print(f"   🎯 Risk: {result['risk_level']}")
        print(f"   📊 Success Rate: {result['weighted_success_rate']:.1%}")
        print(f"   📌 Top Match: {result['similar_questions'][0]['question_text'][:80]}...")
        if result['similar_questions'][0]['success_rate'] < 0.5:
            print(f"   🔍 Found similar hard question (success: {result['similar_questions'][0]['success_rate']:.0%})")
        print(f"   💡 {result['recommendation']}")
    
    print("\n" + "="*80)
    print("✅ Quick real data test complete!")
    print("="*80)


if __name__ == "__main__":
    quick_test()