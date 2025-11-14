#!/usr/bin/env python3
"""
Infinite Evaluation-Based Vector Database Builder
==================================================

Builds vector database with REAL benchmark questions and model performance scores.
Alternative to HuggingFace-based approach for restricted networks.

Author: ToGMAL Project
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import time

from evaluation_results_scraper import EvaluationResultsScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('eval_vector_build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InfiniteEvalVectorBuilder:
    """Builds infinite vector DB with real benchmark evaluation results."""

    def __init__(
        self,
        data_dir: Path = Path("./data/eval_benchmarks"),
        state_file: Path = Path("./data/eval_builder_state.json")
    ):
        """Initialize the builder."""
        self.data_dir = data_dir
        self.state_file = state_file
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.scraper = EvaluationResultsScraper()
        self.state = self._load_state()

        logger.info("="*70)
        logger.info("INFINITE EVALUATION VECTOR DB BUILDER")
        logger.info("="*70)
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Total questions: {self.state['total_questions']}")
        logger.info(f"Benchmarks processed: {len(self.state['processed_benchmarks'])}")

    def _load_state(self) -> Dict[str, Any]:
        """Load builder state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)

        return {
            'total_questions': 0,
            'processed_benchmarks': [],
            'models_tracked': [],
            'last_check': None,
            'start_time': datetime.now().isoformat()
        }

    def _save_state(self):
        """Save builder state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def build_from_aggregate_scores(self) -> int:
        """
        Build dataset from aggregate model scores.
        Creates synthetic "questions" representing each benchmark.

        Returns:
            Number of data points added
        """
        logger.info("\n" + "="*70)
        logger.info("BUILDING FROM AGGREGATE SCORES")
        logger.info("="*70)

        # Fetch aggregate scores
        logger.info("📊 Fetching aggregate model scores...")
        results = self.scraper.fetch_all_sources(include_per_question=False)

        if not results:
            logger.warning("No aggregate scores found")
            return 0

        # Group by benchmark
        benchmarks = {}
        for result in results:
            bench = result.benchmark_name
            if bench not in benchmarks:
                benchmarks[bench] = []
            benchmarks[bench].append(result)

        logger.info(f"Found {len(benchmarks)} benchmarks:")
        for name, models in benchmarks.items():
            logger.info(f"  - {name}: {len(models)} models")

        # Create synthetic questions for each benchmark metric
        questions = []
        for benchmark_name, model_results in benchmarks.items():
            # Get all unique metrics
            all_metrics = set()
            for result in model_results:
                all_metrics.update(result.metrics.keys())

            # Create a "question" for each metric
            for metric in all_metrics:
                # Collect model scores for this metric
                model_scores = {}
                for result in model_results:
                    if metric in result.metrics:
                        score = result.metrics[metric]
                        # Normalize to 0-1 range (assuming scores are 0-100)
                        normalized = score / 100.0 if score <= 100 else score
                        # Convert to boolean (>0.5 = pass)
                        model_scores[result.model_name] = normalized > 0.5

                if model_scores:
                    # Calculate success rate
                    success_rate = sum(1 for v in model_scores.values() if v) / len(model_scores)

                    question = {
                        'question': f"Benchmark: {benchmark_name} - Metric: {metric}",
                        'benchmark': benchmark_name,
                        'metric': metric,
                        'model_scores': model_scores,
                        'success_rate': success_rate,
                        'metadata': {
                            'type': 'aggregate',
                            'num_models': len(model_scores)
                        }
                    }
                    questions.append(question)

        logger.info(f"\n✓ Created {len(questions)} synthetic questions from aggregate scores")
        return questions

    def build_from_per_question_predictions(self, max_questions: int = 5000) -> List[Dict[str, Any]]:
        """
        Build dataset from per-question model predictions.

        Returns:
            List of questions with model scores
        """
        logger.info("\n" + "="*70)
        logger.info("BUILDING FROM PER-QUESTION PREDICTIONS")
        logger.info("="*70)

        # Check if already processed
        if 'MMLU-Pro' in self.state['processed_benchmarks']:
            logger.info("✓ MMLU-Pro already processed")
            # Load from cache
            cache_file = self.data_dir / "mmlu_pro_questions.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)

        logger.info("📝 Extracting per-question predictions from MMLU-Pro...")
        questions = self.scraper.get_benchmark_questions(
            benchmark_name='MMLU-Pro',
            max_questions=max_questions
        )

        if questions:
            # Save to cache
            cache_file = self.data_dir / "mmlu_pro_questions.json"
            with open(cache_file, 'w') as f:
                json.dump(questions, f, indent=2)

            logger.info(f"✓ Cached {len(questions)} questions ({cache_file.stat().st_size / 1024 / 1024:.1f} MB)")

            # Update state
            self.state['processed_benchmarks'].append('MMLU-Pro')
            models = set()
            for q in questions:
                models.update(q['model_scores'].keys())
            self.state['models_tracked'].extend(list(models))
            self.state['models_tracked'] = list(set(self.state['models_tracked']))

        return questions

    def build_complete_dataset(self, max_per_question: int = 5000) -> Dict[str, Any]:
        """
        Build complete dataset combining aggregate and per-question data.

        Returns:
            Complete dataset dictionary
        """
        logger.info("\n" + "="*70)
        logger.info("BUILDING COMPLETE EVALUATION DATASET")
        logger.info("="*70)

        all_questions = []

        # 1. Aggregate scores (synthetic questions)
        logger.info("\n### Step 1: Aggregate Scores ###")
        aggregate_questions = self.build_from_aggregate_scores()
        all_questions.extend(aggregate_questions)
        logger.info(f"Added {len(aggregate_questions)} aggregate-based questions")

        # 2. Per-question predictions (real questions with model scores)
        logger.info("\n### Step 2: Per-Question Predictions ###")
        per_question = self.build_from_per_question_predictions(max_questions=max_per_question)
        all_questions.extend(per_question)
        logger.info(f"Added {len(per_question)} per-question predictions")

        # Update state
        self.state['total_questions'] = len(all_questions)
        self.state['last_check'] = datetime.now().isoformat()
        self._save_state()

        # Create complete dataset
        dataset = {
            'metadata': {
                'total_questions': len(all_questions),
                'num_models': len(self.state['models_tracked']),
                'benchmarks': self.state['processed_benchmarks'],
                'created_at': datetime.now().isoformat(),
                'description': 'Benchmark questions with real model evaluation scores'
            },
            'questions': all_questions
        }

        logger.info("\n" + "="*70)
        logger.info("DATASET COMPLETE")
        logger.info("="*70)
        logger.info(f"Total questions: {len(all_questions):,}")
        logger.info(f"Models tracked: {len(self.state['models_tracked'])}")
        logger.info(f"Benchmarks: {', '.join(self.state['processed_benchmarks'])}")

        return dataset

    def save_dataset(self, dataset: Dict[str, Any], output_file: Path = None):
        """Save dataset to file."""
        if output_file is None:
            output_file = self.data_dir / "complete_evaluation_dataset.json"

        with open(output_file, 'w') as f:
            json.dump(dataset, f, indent=2)

        logger.info(f"\n💾 Saved to {output_file}")
        logger.info(f"   Size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")

    def export_for_vector_db(self, dataset: Dict[str, Any], output_file: Path = None):
        """
        Export in format optimized for ChromaDB vector database.

        Format:
        {
            'documents': [question_text, ...],
            'metadatas': [{model_scores, success_rate, ...}, ...],
            'ids': [unique_id, ...]
        }
        """
        if output_file is None:
            output_file = self.data_dir / "vector_db_ready.json"

        logger.info("\n📦 Preparing for vector database...")

        documents = []
        metadatas = []
        ids = []

        for i, q in enumerate(dataset['questions']):
            # Document is the question text
            documents.append(q['question'])

            # Metadata includes everything except the question text
            metadata = {
                'benchmark': q.get('benchmark', ''),
                'metric': q.get('metric', ''),
                'success_rate': q['success_rate'],
                'num_models': len(q['model_scores']),
                'model_scores': json.dumps(q['model_scores']),  # Serialize for storage
                'metadata': json.dumps(q.get('metadata', {}))
            }
            metadatas.append(metadata)

            # ID is unique identifier
            ids.append(f"q_{i}")

        vector_data = {
            'documents': documents,
            'metadatas': metadatas,
            'ids': ids,
            'source_metadata': dataset['metadata']
        }

        with open(output_file, 'w') as f:
            json.dump(vector_data, f, indent=2)

        logger.info(f"✅ Vector DB data ready: {output_file}")
        logger.info(f"   Size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
        logger.info(f"   Documents: {len(documents):,}")


def main():
    """Main entry point."""
    import sys

    builder = InfiniteEvalVectorBuilder()

    if len(sys.argv) > 1 and sys.argv[1] == 'full':
        # Full build with per-question data
        max_questions = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
        logger.info(f"\n🚀 FULL BUILD MODE (up to {max_questions} per-question predictions)")

        dataset = builder.build_complete_dataset(max_per_question=max_questions)
        builder.save_dataset(dataset)
        builder.export_for_vector_db(dataset)

    else:
        # Quick test - aggregate only
        logger.info("\n🧪 QUICK TEST MODE (aggregate scores only)")
        logger.info("Usage:")
        logger.info("  python infinite_eval_vector_builder.py full 5000  # Full build with per-question data")
        logger.info("")

        dataset = builder.build_complete_dataset(max_per_question=10)  # Just 10 for testing
        builder.save_dataset(dataset)
        builder.export_for_vector_db(dataset)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n⏹️  Stopped by user")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
