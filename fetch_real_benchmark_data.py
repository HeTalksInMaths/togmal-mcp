#!/usr/bin/env python3
"""
Fetch Real Benchmark Data with Dynamic Top Model Selection
===========================================================

Strategy:
1. Query OpenLLM Leaderboard to find top 5 models per benchmark
2. Fetch per-question results for those models
3. Aggregate success rates across top models
4. Generate stratified sample by difficulty

This ensures we're always using the BEST performing models for each benchmark.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass, asdict
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from datasets import load_dataset
    from huggingface_hub import list_datasets, DatasetInfo
    DATASETS_AVAILABLE = True
except ImportError:
    logger.error("datasets not installed. Run: uv pip install datasets huggingface_hub")
    DATASETS_AVAILABLE = False


@dataclass
class ModelBenchmarkScore:
    """Model performance on a specific benchmark"""
    model_name: str
    benchmark_name: str
    score: float
    config_name: str


class TopModelFinder:
    """
    Find top-performing models for each benchmark on OpenLLM Leaderboard.
    
    Uses the leaderboard's results to dynamically select best models.
    """
    
    def __init__(self):
        self.benchmark_configs = {
            "MMLU": "harness_hendrycksTest_5",
            "ARC": "harness_arc_challenge_25",
            "GSM8K": "harness_gsm8k_5",
            "HellaSwag": "harness_hellaswag_10",
            "TruthfulQA": "harness_truthfulqa_mc_0",
            "Winogrande": "harness_winogrande_5"
        }
        
        self.model_scores: Dict[str, List[ModelBenchmarkScore]] = defaultdict(list)
    
    def find_leaderboard_models(self, limit: int = 50) -> List[str]:
        """
        Find models with detailed results on OpenLLM Leaderboard.
        
        Args:
            limit: Maximum number of models to check
        
        Returns:
            List of model names (in format: owner__model-name)
        """
        logger.info(f"Searching for models on OpenLLM Leaderboard (limit: {limit})...")
        
        try:
            # Search for datasets matching the leaderboard pattern
            datasets = list_datasets(
                filter="open-llm-leaderboard",
                limit=limit
            )
            
            models = []
            for dataset in datasets:
                # Extract model name from dataset ID
                # Format: open-llm-leaderboard/details_owner__model-name
                if dataset.id.startswith("open-llm-leaderboard/details_"):
                    model_name = dataset.id.replace("open-llm-leaderboard/details_", "")
                    models.append(model_name)
            
            logger.info(f"Found {len(models)} models with detailed results")
            return models[:limit]
            
        except Exception as e:
            logger.error(f"Failed to find leaderboard models: {e}")
            # Fallback to known top models
            logger.info("Using fallback list of known top models")
            return self._get_fallback_models()
    
    def _get_fallback_models(self) -> List[str]:
        """Fallback list of known top models"""
        return [
            "meta-llama__Meta-Llama-3.1-70B-Instruct",
            "meta-llama__Meta-Llama-3.1-8B-Instruct",
            "Qwen__Qwen2.5-72B-Instruct",
            "Qwen__Qwen2.5-7B-Instruct",
            "mistralai__Mixtral-8x22B-Instruct-v0.1",
            "mistralai__Mistral-7B-Instruct-v0.3",
            "google__gemma-2-27b-it",
            "google__gemma-2-9b-it",
            "microsoft__Phi-3-medium-128k-instruct",
            "microsoft__Phi-3-mini-128k-instruct"
        ]
    
    def get_model_benchmark_score(
        self,
        model_name: str,
        benchmark_name: str,
        config_name: str
    ) -> float:
        """
        Get a model's score on a specific benchmark.
        
        Args:
            model_name: Model name (format: owner__model-name)
            benchmark_name: Benchmark name (e.g., "MMLU")
            config_name: Config name (e.g., "harness_hendrycksTest_5")
        
        Returns:
            Score (0.0 to 1.0), or -1.0 if not available
        """
        try:
            dataset_name = f"open-llm-leaderboard/details_{model_name}"
            
            # Load the results config
            results = load_dataset(dataset_name, "results", split="latest")
            
            # Results typically has one row with all scores
            if len(results) > 0:
                row = results[0]
                
                # Look for the benchmark score in the row
                # Different benchmarks may have different field names
                possible_keys = [
                    benchmark_name.lower(),
                    config_name,
                    f"{benchmark_name}_acc",
                    f"{benchmark_name}_acc_norm"
                ]
                
                for key in possible_keys:
                    if key in row:
                        score = row[key]
                        if isinstance(score, (int, float)):
                            return float(score)
                
                # If we have a 'results' field with nested data
                if 'results' in row and isinstance(row['results'], dict):
                    for key, value in row['results'].items():
                        if benchmark_name.lower() in key.lower():
                            if isinstance(value, dict) and 'acc' in value:
                                return float(value['acc'])
                            elif isinstance(value, (int, float)):
                                return float(value)
            
            logger.debug(f"No score found for {model_name} on {benchmark_name}")
            return -1.0
            
        except Exception as e:
            logger.debug(f"Failed to get score for {model_name} on {benchmark_name}: {e}")
            return -1.0
    
    def find_top_models_for_benchmark(
        self,
        benchmark_name: str,
        top_k: int = 5,
        candidate_models: List[str] = None
    ) -> List[str]:
        """
        Find top K models for a specific benchmark.
        
        Args:
            benchmark_name: Benchmark name (e.g., "MMLU")
            top_k: Number of top models to return
            candidate_models: List of models to check (if None, auto-discover)
        
        Returns:
            List of top model names
        """
        logger.info(f"Finding top {top_k} models for {benchmark_name}...")
        
        if candidate_models is None:
            candidate_models = self.find_leaderboard_models(limit=50)
        
        config_name = self.benchmark_configs.get(benchmark_name, "")
        if not config_name:
            logger.error(f"Unknown benchmark: {benchmark_name}")
            return []
        
        # Get scores for all candidates
        model_scores = []
        for model_name in candidate_models:
            score = self.get_model_benchmark_score(model_name, benchmark_name, config_name)
            if score >= 0:
                model_scores.append((model_name, score))
                logger.debug(f"  {model_name}: {score:.3f}")
            time.sleep(0.1)  # Rate limiting
        
        # Sort by score (descending)
        model_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Get top K
        top_models = [name for name, score in model_scores[:top_k]]
        
        logger.info(f"Top {len(top_models)} models for {benchmark_name}:")
        for i, (name, score) in enumerate(model_scores[:top_k], 1):
            logger.info(f"  {i}. {name}: {score:.3f}")
        
        return top_models


class RealBenchmarkDataFetcher:
    """
    Fetch real per-question benchmark data using dynamic top model selection.
    """
    
    def __init__(self, output_dir: Path = Path("./data/benchmark_results")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.top_model_finder = TopModelFinder()
        self.questions: Dict[str, Dict[str, Any]] = {}
    
    def fetch_mmlu_with_top_models(
        self,
        top_k: int = 5,
        max_questions: int = 1000
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch MMLU questions with results from top K models.
        
        Args:
            top_k: Number of top models to use
            max_questions: Maximum questions to fetch
        
        Returns:
            Dictionary of questions with aggregated results
        """
        logger.info("="*80)
        logger.info(f"Fetching MMLU data with top {top_k} models")
        logger.info("="*80)
        
        # Find top models for MMLU
        top_models = self.top_model_finder.find_top_models_for_benchmark(
            "MMLU",
            top_k=top_k
        )
        
        if not top_models:
            logger.error("No top models found for MMLU")
            return {}
        
        # Fetch per-question results for each top model
        question_results = defaultdict(lambda: {
            'model_results': {},
            'metadata': {}
        })
        
        for model_name in top_models:
            logger.info(f"\nFetching results for {model_name}...")
            
            try:
                dataset_name = f"open-llm-leaderboard/details_{model_name}"
                results = load_dataset(
                    dataset_name,
                    "harness_hendrycksTest_5",
                    split="latest"
                )
                
                logger.info(f"  Loaded {len(results)} questions")
                
                # Process each question
                for idx, row in enumerate(results):
                    # Use 'example' field as unique ID (or doc_id if available)
                    question_id = f"mmlu_{idx}"
                    
                    # Store metadata from first model
                    if not question_results[question_id]['metadata']:
                        question_results[question_id]['metadata'] = {
                            'question_text': row.get('example', ''),
                            'instruction': row.get('instruction', ''),
                            'choices': row.get('choices', []),
                            'source_benchmark': 'MMLU',
                            'domain': 'general'  # MMLU is cross-domain
                        }
                    
                    # Store correctness for this model
                    is_correct = row.get('metrics', {}).get('acc', 0.0) == 1.0
                    question_results[question_id]['model_results'][model_name] = is_correct
                
                logger.info(f"  ✓ Processed {len(results)} questions")
                
                # Limit questions if needed
                if len(question_results) >= max_questions:
                    logger.info(f"  Reached max questions limit: {max_questions}")
                    break
                
            except Exception as e:
                logger.error(f"  Failed to fetch {model_name}: {e}")
                continue
        
        # Compute success rates
        final_questions = {}
        for qid, data in question_results.items():
            if len(data['model_results']) == 0:
                continue
            
            # Calculate success rate across models
            correct_count = sum(1 for v in data['model_results'].values() if v)
            total_models = len(data['model_results'])
            success_rate = correct_count / total_models
            
            # Classify difficulty
            if success_rate < 0.3:
                difficulty_tier = "low"
                difficulty_label = "Hard"
            elif success_rate < 0.7:
                difficulty_tier = "medium"
                difficulty_label = "Moderate"
            else:
                difficulty_tier = "high"
                difficulty_label = "Easy"
            
            final_questions[qid] = {
                **data['metadata'],
                'model_results': data['model_results'],
                'success_rate': success_rate,
                'num_models_tested': total_models,
                'difficulty_tier': difficulty_tier,
                'difficulty_label': difficulty_label
            }
        
        logger.info(f"\n✓ Collected {len(final_questions)} questions with {top_k} models")
        return final_questions
    
    def save_results(self, questions: Dict[str, Dict[str, Any]], filename: str = "real_benchmark_data.json"):
        """Save fetched results"""
        output_path = self.output_dir / filename
        
        data = {
            "metadata": {
                "total_questions": len(questions),
                "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "questions": questions
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved results to {output_path}")
        return output_path
    
    def print_summary(self, questions: Dict[str, Dict[str, Any]]):
        """Print summary statistics"""
        tier_counts = defaultdict(int)
        success_rates = []
        
        for q in questions.values():
            tier_counts[q['difficulty_tier']] += 1
            success_rates.append(q['success_rate'])
        
        print("\n" + "="*80)
        print("BENCHMARK DATA SUMMARY")
        print("="*80)
        print(f"\nTotal Questions: {len(questions)}")
        
        print(f"\nDifficulty Distribution:")
        total = len(questions)
        for tier in ['low', 'medium', 'high']:
            count = tier_counts[tier]
            pct = count / total * 100 if total > 0 else 0
            print(f"  {tier.upper()}: {count} ({pct:.1f}%)")
        
        if success_rates:
            import numpy as np
            print(f"\nSuccess Rate Statistics:")
            print(f"  Min: {np.min(success_rates):.1%}")
            print(f"  Max: {np.max(success_rates):.1%}")
            print(f"  Mean: {np.mean(success_rates):.1%}")
            print(f"  Median: {np.median(success_rates):.1%}")
        
        print("\n" + "="*80)


def main():
    """Main execution"""
    logger.info("="*80)
    logger.info("Real Benchmark Data Fetcher with Dynamic Top Model Selection")
    logger.info("="*80)
    
    fetcher = RealBenchmarkDataFetcher()
    
    # Fetch MMLU with top 5 models (dynamically selected)
    questions = fetcher.fetch_mmlu_with_top_models(
        top_k=5,
        max_questions=1000
    )
    
    # Save results
    fetcher.save_results(questions)
    
    # Print summary
    fetcher.print_summary(questions)
    
    print("\n" + "="*80)
    print("✓ Data collection complete!")
    print("="*80)
    print("\nNext steps:")
    print("1. Review real_benchmark_data.json")
    print("2. Build vector database with real success rates")
    print("3. Test difficulty assessment on real prompts")


if __name__ == "__main__":
    main()
