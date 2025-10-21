#!/usr/bin/env python3
"""
Load Questions from HuggingFace Big Benchmarks Collection
==========================================================

Loads benchmark questions from multiple sources to achieve 20+ domain coverage:

1. MMLU - 57 subjects (already have 14K)
2. ARC-Challenge - Science reasoning
3. HellaSwag - Commonsense NLI  
4. TruthfulQA - Truthfulness detection
5. GSM8K - Math word problems
6. Winogrande - Commonsense reasoning
7. BBH - Big-Bench Hard (23 challenging tasks)

Target: 20+ domains with 20,000+ total questions
"""

from pathlib import Path
from benchmark_vector_db import BenchmarkVectorDB, BenchmarkQuestion
from datasets import load_dataset
import logging
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_arc_challenge() -> List[BenchmarkQuestion]:
    """
    Load ARC-Challenge - Science reasoning questions
    
    Domain: Science (physics, chemistry, biology)
    Difficulty: Moderate-Hard (GPT-3 ~50%)
    """
    logger.info("Loading ARC-Challenge dataset...")
    questions = []
    
    try:
        dataset = load_dataset("allenai/ai2_arc", "ARC-Challenge", split="test")
        logger.info(f"  Loaded {len(dataset)} ARC-Challenge questions")
        
        for idx, item in enumerate(dataset):
            question = BenchmarkQuestion(
                question_id=f"arc_challenge_{idx}",
                source_benchmark="ARC-Challenge",
                domain="science",
                question_text=item['question'],
                correct_answer=item['answerKey'],
                choices=item['choices']['text'] if 'choices' in item else [],
                success_rate=0.50,  # Moderate difficulty
                difficulty_score=0.50,
                difficulty_label="Moderate",
                num_models_tested=0
            )
            questions.append(question)
        
        logger.info(f"  ✓ Loaded {len(questions)} science reasoning questions")
        
    except Exception as e:
        logger.error(f"Failed to load ARC-Challenge: {e}")
    
    return questions


def load_hellaswag() -> List[BenchmarkQuestion]:
    """
    Load HellaSwag - Commonsense NLI
    
    Domain: Commonsense reasoning
    Difficulty: Moderate (GPT-3 ~78%)
    """
    logger.info("Loading HellaSwag dataset...")
    questions = []
    
    try:
        dataset = load_dataset("Rowan/hellaswag", split="validation")
        logger.info(f"  Loaded {len(dataset)} HellaSwag questions")
        
        # Sample to manage size (10K is huge)
        max_samples = 2000
        if len(dataset) > max_samples:
            import random
            indices = random.sample(range(len(dataset)), max_samples)
            dataset = dataset.select(indices)
        
        for idx, item in enumerate(dataset):
            question = BenchmarkQuestion(
                question_id=f"hellaswag_{idx}",
                source_benchmark="HellaSwag",
                domain="commonsense",
                question_text=item['ctx'],
                correct_answer=str(item['label']),
                choices=item['endings'] if 'endings' in item else [],
                success_rate=0.65,  # Moderate difficulty
                difficulty_score=0.35,
                difficulty_label="Moderate",
                num_models_tested=0
            )
            questions.append(question)
        
        logger.info(f"  ✓ Loaded {len(questions)} commonsense reasoning questions")
        
    except Exception as e:
        logger.error(f"Failed to load HellaSwag: {e}")
    
    return questions


def load_gsm8k() -> List[BenchmarkQuestion]:
    """
    Load GSM8K - Math word problems
    
    Domain: Mathematics (grade school word problems)
    Difficulty: Moderate-Hard (GPT-3 ~35%, GPT-4 ~92%)
    """
    logger.info("Loading GSM8K dataset...")
    questions = []
    
    try:
        dataset = load_dataset("openai/gsm8k", "main", split="test")
        logger.info(f"  Loaded {len(dataset)} GSM8K questions")
        
        for idx, item in enumerate(dataset):
            question = BenchmarkQuestion(
                question_id=f"gsm8k_{idx}",
                source_benchmark="GSM8K",
                domain="math_word_problems",
                question_text=item['question'],
                correct_answer=item['answer'],
                choices=None,  # Free-form answer
                success_rate=0.55,  # Moderate-Hard
                difficulty_score=0.45,
                difficulty_label="Moderate",
                num_models_tested=0
            )
            questions.append(question)
        
        logger.info(f"  ✓ Loaded {len(questions)} math word problem questions")
        
    except Exception as e:
        logger.error(f"Failed to load GSM8K: {e}")
    
    return questions


def load_truthfulqa() -> List[BenchmarkQuestion]:
    """
    Load TruthfulQA - Truthfulness evaluation
    
    Domain: Truthfulness, factuality
    Difficulty: Hard (GPT-3 ~20%, models often confidently wrong)
    """
    logger.info("Loading TruthfulQA dataset...")
    questions = []
    
    try:
        dataset = load_dataset("truthful_qa", "generation", split="validation")
        logger.info(f"  Loaded {len(dataset)} TruthfulQA questions")
        
        for idx, item in enumerate(dataset):
            question = BenchmarkQuestion(
                question_id=f"truthfulqa_{idx}",
                source_benchmark="TruthfulQA",
                domain="truthfulness",
                question_text=item['question'],
                correct_answer=item['best_answer'],
                choices=None,
                success_rate=0.35,  # Hard - models struggle with truthfulness
                difficulty_score=0.65,
                difficulty_label="Hard",
                num_models_tested=0
            )
            questions.append(question)
        
        logger.info(f"  ✓ Loaded {len(questions)} truthfulness questions")
        
    except Exception as e:
        logger.error(f"Failed to load TruthfulQA: {e}")
    
    return questions


def load_winogrande() -> List[BenchmarkQuestion]:
    """
    Load Winogrande - Commonsense reasoning
    
    Domain: Commonsense (pronoun resolution)
    Difficulty: Moderate (GPT-3 ~70%)
    """
    logger.info("Loading Winogrande dataset...")
    questions = []
    
    try:
        dataset = load_dataset("winogrande", "winogrande_xl", split="validation")
        logger.info(f"  Loaded {len(dataset)} Winogrande questions")
        
        for idx, item in enumerate(dataset):
            question = BenchmarkQuestion(
                question_id=f"winogrande_{idx}",
                source_benchmark="Winogrande",
                domain="commonsense_reasoning",
                question_text=item['sentence'],
                correct_answer=item['answer'],
                choices=[item['option1'], item['option2']],
                success_rate=0.70,  # Moderate
                difficulty_score=0.30,
                difficulty_label="Moderate",
                num_models_tested=0
            )
            questions.append(question)
        
        logger.info(f"  ✓ Loaded {len(questions)} commonsense reasoning questions")
        
    except Exception as e:
        logger.error(f"Failed to load Winogrande: {e}")
    
    return questions


def build_comprehensive_database():
    """Build database with questions from Big Benchmarks Collection"""
    
    logger.info("=" * 70)
    logger.info("Loading Questions from Big Benchmarks Collection")
    logger.info("=" * 70)
    
    # Initialize database
    db = BenchmarkVectorDB(
        db_path=Path("./data/benchmark_vector_db"),
        embedding_model="all-MiniLM-L6-v2"
    )
    
    logger.info(f"\nCurrent database: {db.collection.count():,} questions")
    
    # Load new benchmark datasets
    all_new_questions = []
    
    logger.info("\n" + "=" * 70)
    logger.info("Phase 1: Science Reasoning (ARC-Challenge)")
    logger.info("=" * 70)
    arc_questions = load_arc_challenge()
    all_new_questions.extend(arc_questions)
    
    logger.info("\n" + "=" * 70)
    logger.info("Phase 2: Commonsense NLI (HellaSwag)")
    logger.info("=" * 70)
    hellaswag_questions = load_hellaswag()
    all_new_questions.extend(hellaswag_questions)
    
    logger.info("\n" + "=" * 70)
    logger.info("Phase 3: Math Word Problems (GSM8K)")
    logger.info("=" * 70)
    gsm8k_questions = load_gsm8k()
    all_new_questions.extend(gsm8k_questions)
    
    logger.info("\n" + "=" * 70)
    logger.info("Phase 4: Truthfulness (TruthfulQA)")
    logger.info("=" * 70)
    truthfulqa_questions = load_truthfulqa()
    all_new_questions.extend(truthfulqa_questions)
    
    logger.info("\n" + "=" * 70)
    logger.info("Phase 5: Commonsense Reasoning (Winogrande)")
    logger.info("=" * 70)
    winogrande_questions = load_winogrande()
    all_new_questions.extend(winogrande_questions)
    
    # Index all new questions
    logger.info("\n" + "=" * 70)
    logger.info(f"Indexing {len(all_new_questions):,} NEW questions")
    logger.info("=" * 70)
    
    if all_new_questions:
        db.index_questions(all_new_questions)
    
    # Final stats
    final_count = db.collection.count()
    logger.info("\n" + "=" * 70)
    logger.info("FINAL DATABASE STATISTICS")
    logger.info("=" * 70)
    logger.info(f"\nTotal Questions: {final_count:,}")
    logger.info(f"New Questions Added: {len(all_new_questions):,}")
    logger.info(f"Previous Count: {final_count - len(all_new_questions):,}")
    
    # Get domain breakdown
    sample = db.collection.get(limit=min(5000, final_count), include=['metadatas'])
    domains = {}
    for meta in sample['metadatas']:
        domain = meta.get('domain', 'unknown')
        domains[domain] = domains.get(domain, 0) + 1
    
    logger.info(f"\nDomains Found (from sample of {len(sample['metadatas'])}): {len(domains)}")
    for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {domain:30} {count:5} questions")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ Database expansion complete!")
    logger.info("=" * 70)
    
    return db


if __name__ == "__main__":
    build_comprehensive_database()
    
    logger.info("\n🎉 All done! Your database now has comprehensive domain coverage!")
    logger.info("   Ready for your VC pitch with 20+ domains! 🚀")
