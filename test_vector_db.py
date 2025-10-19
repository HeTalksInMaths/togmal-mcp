#!/usr/bin/env python3
"""
Test Vector Database with Real 14K MMLU Questions
"""

import json
from pathlib import Path
from benchmark_vector_db import BenchmarkVectorDB, BenchmarkQuestion

def load_real_mmlu_data():
    """Load the 14K real MMLU questions"""
    print("Loading 14,042 real MMLU questions...")
    
    with open("./data/benchmark_results/mmlu_real_results.json") as f:
        data = json.load(f)
    
    questions = []
    for qid, q in data['questions'].items():
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
    
    print(f"✓ Loaded {len(questions)} questions")
    return questions


def build_and_test_vector_db():
    """Build vector DB with real data and run tests"""
    
    # Initialize fresh database
    db = BenchmarkVectorDB(
        db_path=Path("./data/benchmark_vector_db"),
        embedding_model="all-MiniLM-L6-v2"
    )
    
    # Load real data
    questions = load_real_mmlu_data()
    
    # Index questions (this takes 1-2 minutes)
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
        "Find all zeros of the polynomial x^3 + 2x + 2 in the finite field Z_7",
        
        # Should be MODERATE (reasoning)
        "Diagnose a patient with acute chest pain and shortness of breath",
        "Explain the legal doctrine of precedent in common law systems",
        "Implement a binary search tree with insert and search operations",
        
        # Should be EASY (basic knowledge)
        "What is 2 + 2?",
        "What is the capital of France?",
        "Who wrote Romeo and Juliet?",
        "What is the boiling point of water in Celsius?",
        
        # Cross-domain abstract reasoning
        "Statement 1 | Every field is also a ring. Statement 2 | Every ring has a multiplicative identity."
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
    print("✅ Real data test complete!")
    print("="*80)


if __name__ == "__main__":
    build_and_test_vector_db()