#!/usr/bin/env python3
"""
Fetch MMLU Data from Top 5+ Models
===================================

Fetches per-question results from top-performing models on MMLU.
Computes real success rates by aggregating across models.

Runtime: ~10-15 minutes for 5 models x 14K questions
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from datasets import load_dataset


# Top models on OpenLLM Leaderboard (as of Oct 2024)
# Selected based on MMLU performance
TOP_MODELS = [
    "meta-llama__Meta-Llama-3.1-70B-Instruct",  # ~85% MMLU
    "Qwen__Qwen2.5-72B-Instruct",                # ~85% MMLU
    "mistralai__Mixtral-8x22B-Instruct-v0.1",    # ~77% MMLU
    "google__gemma-2-27b-it",                    # ~75% MMLU
    "microsoft__Phi-3-medium-128k-instruct",     # ~78% MMLU
    "meta-llama__Meta-Llama-3.1-8B-Instruct",    # ~69% MMLU
    "Qwen__Qwen2.5-7B-Instruct",                 # ~74% MMLU
]


def fetch_mmlu_data(
    models: List[str] = TOP_MODELS,
    max_questions: int = 1000,
    output_dir: Path = Path("./data/benchmark_results")
) -> Dict[str, Dict[str, Any]]:
    """
    Fetch MMLU per-question results from multiple top models.
    
    Args:
        models: List of model names to fetch
        max_questions: Maximum questions to collect
        output_dir: Where to save results
    
    Returns:
        Dictionary of questions with aggregated success rates
    """
    logger.info("="*80)
    logger.info(f"Fetching MMLU data from {len(models)} top models")
    logger.info("="*80)
    
    for i, model in enumerate(models, 1):
        logger.info(f"  {i}. {model}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Store per-question results
    question_data = defaultdict(lambda: {
        'model_results': {},
        'metadata': {}
    })
    
    # Fetch from each model
    for model_idx, model_name in enumerate(models, 1):
        logger.info(f"\n[{model_idx}/{len(models)}] Fetching {model_name}...")
        
        try:
            dataset_name = f"open-llm-leaderboard/details_{model_name}"
            
            # Load MMLU results
            logger.info(f"  Loading dataset...")
            results = load_dataset(
                dataset_name,
                "harness_hendrycksTest_5",
                split="latest"
            )
            
            logger.info(f"  Processing {len(results)} questions...")
            
            # Process each question
            for idx, row in enumerate(results):
                question_id = f"mmlu_{idx}"
                
                # Store metadata on first encounter
                if not question_data[question_id]['metadata']:
                    question_data[question_id]['metadata'] = {
                        'question_id': question_id,
                        'question_text': row.get('example', ''),
                        'instruction': row.get('instruction', ''),
                        'choices': row.get('choices', []),
                        'source_benchmark': 'MMLU',
                        'domain': 'cross_domain'
                    }
                
                # Store this model's result
                is_correct = row.get('metrics', {}).get('acc', 0.0) == 1.0
                question_data[question_id]['model_results'][model_name] = is_correct
            
            logger.info(f"  ✓ Processed {len(results)} questions")
            
            # Check if we have enough
            if len(question_data) >= max_questions:
                logger.info(f"  Reached target of {max_questions} questions")
                break
            
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            continue
    
    # Compute aggregated success rates
    logger.info(f"\nComputing success rates across {len(models)} models...")
    
    final_questions = {}
    for qid, data in question_data.items():
        if len(data['model_results']) == 0:
            continue
        
        # Calculate success rate
        correct_count = sum(1 for v in data['model_results'].values() if v)
        total_models = len(data['model_results'])
        success_rate = correct_count / total_models
        
        # Classify difficulty
        if success_rate < 0.3:
            tier = "low"
            label = "Hard"
        elif success_rate < 0.7:
            tier = "medium"
            label = "Moderate"
        else:
            tier = "high"
            label = "Easy"
        
        final_questions[qid] = {
            **data['metadata'],
            'success_rate': success_rate,
            'num_models_tested': total_models,
            'difficulty_tier': tier,
            'difficulty_label': label,
            'model_results': {m: int(v) for m, v in data['model_results'].items()}  # Convert bool to int for JSON
        }
    
    logger.info(f"✓ Collected {len(final_questions)} questions")
    
    # Print distribution
    tier_counts = defaultdict(int)
    for q in final_questions.values():
        tier_counts[q['difficulty_tier']] += 1
    
    logger.info(f"\nDifficulty Distribution:")
    total = len(final_questions)
    for tier in ['low', 'medium', 'high']:
        count = tier_counts[tier]
        pct = count / total * 100 if total > 0 else 0
        logger.info(f"  {tier.upper()}: {count} ({pct:.1f}%)")
    
    # Save results
    output_file = output_dir / "mmlu_real_results.json"
    data = {
        "metadata": {
            "total_questions": len(final_questions),
            "num_models": len(models),
            "models": models,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "questions": final_questions
    }
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"\n✓ Saved to {output_file}")
    
    return final_questions


def main():
    """Main execution"""
    logger.info("Starting MMLU data fetch from top models...")
    logger.info("This will take ~10-15 minutes\n")
    
    start_time = time.time()
    
    questions = fetch_mmlu_data(
        models=TOP_MODELS[:5],  # Use top 5 for speed
        max_questions=1000
    )
    
    elapsed = time.time() - start_time
    logger.info(f"\n{'='*80}")
    logger.info(f"✓ Complete! Fetched {len(questions)} questions in {elapsed/60:.1f} minutes")
    logger.info(f"{'='*80}")
    
    logger.info("\nNext steps:")
    logger.info("1. Load this data into vector database")
    logger.info("2. Build embeddings for questions")
    logger.info("3. Test difficulty assessment")


if __name__ == "__main__":
    main()
