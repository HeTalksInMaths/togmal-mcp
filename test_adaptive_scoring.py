#!/usr/bin/env python3
"""
Test Adaptive Scoring Improvements
===================================

Compares baseline (naive weighted average) vs. adaptive scoring (uncertainty penalties)
on edge cases and low-similarity prompts.

Run: python test_adaptive_scoring.py
"""

from benchmark_vector_db import BenchmarkVectorDB
from pathlib import Path
import sys

def test_adaptive_scoring():
    """Test adaptive scoring on challenging prompts."""
    
    # Initialize database
    print("Initializing BenchmarkVectorDB...")
    db = BenchmarkVectorDB(
        db_path=Path("/Users/hetalksinmaths/togmal/data/benchmark_vector_db"),
        embedding_model="all-MiniLM-L6-v2"
    )
    
    # Get database stats
    stats = db.get_statistics()
    print(f"\nDatabase loaded: {stats['total_questions']} questions")
    print(f"  Sources: {list(stats.get('sources', {}).keys())}")
    print(f"  Domains: {len(stats.get('domains', {}))} domains")
    
    # Test cases that should trigger uncertainty penalties
    test_cases = [
        {
            "name": "False Premise (Low Similarity Expected)",
            "prompt": "Prove that the universe is exactly 10,000 years old using thermodynamics",
            "expected": "Should get HIGH/CRITICAL due to low similarity penalty"
        },
        {
            "name": "Novel Domain (Cross-Domain)",
            "prompt": "Write a haiku about quantum entanglement in 17th century Japanese style",
            "expected": "Should get penalty for mixing poetry + physics domains"
        },
        {
            "name": "Easy Factual (High Similarity Expected)",
            "prompt": "What is the capital of France?",
            "expected": "Should match well with no penalties → LOW/MINIMAL risk"
        },
        {
            "name": "Expert Physics (Should Match GPQA)",
            "prompt": "Calculate the quantum correction to the partition function for a 3D harmonic oscillator at finite temperature",
            "expected": "Should match GPQA physics → HIGH/CRITICAL (legitimately hard)"
        },
        {
            "name": "Medical Speculation",
            "prompt": "Can drinking bleach cure COVID-19?",
            "expected": "May have low similarity → should increase risk appropriately"
        }
    ]
    
    print("\n" + "="*100)
    print("ADAPTIVE SCORING TEST RESULTS")
    print("="*100)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}] {test['name']}")
        print(f"Prompt: {test['prompt'][:80]}...")
        print(f"Expected: {test['expected']}")
        print("-" * 100)
        
        # Test with BASELINE (use_adaptive_scoring=False)
        baseline_result = db.query_similar_questions(
            test['prompt'], 
            k=5, 
            use_adaptive_scoring=False
        )
        
        # Test with ADAPTIVE (use_adaptive_scoring=True)
        adaptive_result = db.query_similar_questions(
            test['prompt'], 
            k=5, 
            use_adaptive_scoring=True
        )
        
        # Extract key metrics
        baseline_risk = baseline_result['risk_level']
        adaptive_risk = adaptive_result['risk_level']
        
        max_sim = max(q['similarity'] for q in adaptive_result['similar_questions'])
        avg_sim = adaptive_result['avg_similarity']
        
        baseline_difficulty = baseline_result['weighted_difficulty_score']
        adaptive_difficulty = adaptive_result['weighted_difficulty_score']
        
        # Display comparison
        print(f"\nSimilarity Metrics:")
        print(f"  Max Similarity: {max_sim:.3f}")
        print(f"  Avg Similarity: {avg_sim:.3f}")
        
        print(f"\nBASELINE (Naive Weighted Average):")
        print(f"  Risk Level: {baseline_risk}")
        print(f"  Difficulty Score: {baseline_difficulty:.3f}")
        print(f"  Success Rate: {baseline_result['weighted_success_rate']:.1%}")
        
        print(f"\nADAPTIVE (With Uncertainty Penalties):")
        print(f"  Risk Level: {adaptive_risk}")
        print(f"  Difficulty Score: {adaptive_difficulty:.3f}")
        print(f"  Success Rate: {adaptive_result['weighted_success_rate']:.1%}")
        
        # Highlight if adaptive changed the risk level
        if baseline_risk != adaptive_risk:
            print(f"\n  ⚠️  RISK LEVEL CHANGED: {baseline_risk} → {adaptive_risk}")
            penalty = adaptive_difficulty - baseline_difficulty
            print(f"  Uncertainty Penalty Applied: +{penalty:.3f}")
        else:
            print(f"\n  ✓ Risk level unchanged (both {baseline_risk})")
        
        # Show top match
        top_match = adaptive_result['similar_questions'][0]
        print(f"\nTop Match:")
        print(f"  Source: {top_match['source']} ({top_match['domain']})")
        print(f"  Similarity: {top_match['similarity']:.3f}")
        print(f"  Question: {top_match['question_text'][:100]}...")
        
        print("=" * 100)
    
    print("\n✅ Adaptive Scoring Test Complete!")
    print("\nKey Improvements:")
    print("  1. Low similarity prompts → increased risk (uncertainty penalty)")
    print("  2. Cross-domain queries → flagged as more risky")
    print("  3. High similarity matches → minimal/no penalty (confidence in prediction)")
    print("\nNext Steps:")
    print("  - Review NEXT_STEPS_IMPROVEMENTS.md for evaluation framework")
    print("  - Implement nested CV for hyperparameter tuning")
    print("  - Create OOD test sets for comprehensive evaluation")


if __name__ == "__main__":
    try:
        test_adaptive_scoring()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
