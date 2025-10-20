#!/usr/bin/env python3
"""
Expand Vector Database with Comprehensive Data
==============================================

This script loads data from multiple sources to create a comprehensive
vector database with better domain coverage:

1. Full MMLU dataset (all domains, no sampling)
2. MMLU-Pro (harder questions)
3. GPQA Diamond (graduate-level questions)
4. MATH dataset (competition mathematics)

Target: 20,000+ questions across 20+ domains
"""

from pathlib import Path
from benchmark_vector_db import BenchmarkVectorDB
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def expand_database():
    """Build comprehensive vector database"""
    
    logger.info("=" * 60)
    logger.info("Expanding Vector Database with Comprehensive Data")
    logger.info("=" * 60)
    
    # Initialize new database
    db = BenchmarkVectorDB(
        db_path=Path("./data/benchmark_vector_db_expanded"),
        embedding_model="all-MiniLM-L6-v2"
    )
    
    # Build with significantly higher limits
    logger.info("\nPhase 1: Loading MMLU-Pro (harder subset)")
    logger.info("-" * 40)
    mmlu_pro_questions = db.load_mmlu_pro_dataset(max_samples=5000)
    logger.info(f"Loaded {len(mmlu_pro_questions)} MMLU-Pro questions")
    
    logger.info("\nPhase 2: Loading GPQA Diamond (graduate-level)")
    logger.info("-" * 40)
    gpqa_questions = db.load_gpqa_dataset(fetch_real_scores=False)
    logger.info(f"Loaded {len(gpqa_questions)} GPQA questions")
    
    logger.info("\nPhase 3: Loading MATH dataset (competition math)")
    logger.info("-" * 40)
    math_questions = db.load_math_dataset(max_samples=2000)
    logger.info(f"Loaded {len(math_questions)} MATH questions")
    
    # Combine all questions
    all_questions = mmlu_pro_questions + gpqa_questions + math_questions
    logger.info(f"\nTotal questions to index: {len(all_questions)}")
    
    # Index into vector database
    if all_questions:
        logger.info("\nIndexing questions into vector database...")
        logger.info("This may take several minutes...")
        db.index_questions(all_questions)
    
    # Get final statistics
    logger.info("\n" + "=" * 60)
    logger.info("Database Statistics")
    logger.info("=" * 60)
    
    stats = db.get_statistics()
    logger.info(f"\nTotal Questions: {stats['total_questions']}")
    logger.info(f"\nSources:")
    for source, count in stats.get('sources', {}).items():
        logger.info(f"  {source}: {count}")
    
    logger.info(f"\nDomains:")
    for domain, count in sorted(stats.get('domains', {}).items(), key=lambda x: x[1], reverse=True)[:20]:
        logger.info(f"  {domain}: {count}")
    
    logger.info(f"\nDifficulty Levels:")
    for level, count in stats.get('difficulty_levels', {}).items():
        logger.info(f"  {level}: {count}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Database expansion complete!")
    logger.info("=" * 60)
    
    return db, stats


def test_expanded_database(db):
    """Test the expanded database with example queries"""
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing Expanded Database")
    logger.info("=" * 60)
    
    test_prompts = [
        # Hard prompts
        ("Graduate-level physics", "Calculate the quantum correction to the partition function for a 3D harmonic oscillator"),
        ("Abstract mathematics", "Prove that every field is also a ring"),
        ("Competition math", "Find all zeros of the polynomial x^3 + 2x + 2 in Z_7"),
        
        # Easy prompts
        ("Basic arithmetic", "What is 2 + 2?"),
        ("General knowledge", "What is the capital of France?"),
        
        # Domain-specific
        ("Medical reasoning", "Diagnose a patient with acute chest pain"),
        ("Legal knowledge", "Explain the doctrine of precedent in common law"),
        ("Computer science", "Implement a binary search tree"),
    ]
    
    for category, prompt in test_prompts:
        logger.info(f"\n{category}: '{prompt[:50]}...'")
        result = db.query_similar_questions(prompt, k=3)
        logger.info(f"  Risk Level: {result['risk_level']}")
        logger.info(f"  Success Rate: {result['weighted_success_rate']:.1%}")
        logger.info(f"  Recommendation: {result['recommendation']}")


if __name__ == "__main__":
    # Expand database
    db, stats = expand_database()
    
    # Test with example queries
    test_expanded_database(db)
    
    logger.info("\n🎉 All done! You can now use the expanded database.")
    logger.info("To switch to the expanded database, update your demo files:")
    logger.info("  db_path=Path('./data/benchmark_vector_db_expanded')")
