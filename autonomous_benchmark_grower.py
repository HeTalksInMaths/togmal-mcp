#!/usr/bin/env python3
"""
Autonomous Benchmark Dataset Grower
====================================

Intelligently grows the vector database by selecting top-performing models
across different size categories. Runs continuously to discover and add
new benchmarks and models.

Author: ToGMAL Project
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import requests

from evaluation_results_scraper import EvaluationResultsScraper, ModelBenchmarkScore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('autonomous_growth.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Metadata about a model."""
    name: str
    size_params: Optional[float] = None  # In billions
    size_category: str = "unknown"  # small, medium, large, unknown
    accuracy: float = 0.0
    total_questions: int = 0
    source: str = ""

    def __post_init__(self):
        """Extract size from model name if not provided."""
        if self.size_params is None:
            self.size_params = self._extract_size()
        if self.size_category == "unknown" and self.size_params:
            self.size_category = self._categorize_size()

    def _extract_size(self) -> Optional[float]:
        """Extract parameter count from model name."""
        # Match patterns like 7B, 70B, 8x7B, etc.
        patterns = [
            r'(\d+)B',  # 7B, 70B
            r'(\d+)b',  # 7b, 70b
            r'(\d+\.?\d*)B',  # 3.5B
            r'(\d+)x(\d+)B',  # 8x7B (mixtral)
        ]

        for pattern in patterns:
            match = re.search(pattern, self.name)
            if match:
                if 'x' in pattern:
                    # Mixtral-style: multiply
                    return float(match.group(1)) * float(match.group(2))
                return float(match.group(1))

        return None

    def _categorize_size(self) -> str:
        """Categorize model by size."""
        if self.size_params is None:
            return "unknown"

        if self.size_params <= 10:
            return "small"  # ≤10B
        elif self.size_params <= 40:
            return "medium"  # 10-40B
        else:
            return "large"  # >40B


class AutonomousBenchmarkGrower:
    """Autonomously grows benchmark dataset with intelligent model selection."""

    def __init__(
        self,
        data_dir: Path = Path("./data/autonomous_benchmarks"),
        state_file: Path = Path("./data/autonomous_state.json")
    ):
        """Initialize the autonomous grower."""
        self.data_dir = data_dir
        self.state_file = state_file
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.scraper = EvaluationResultsScraper()
        self.state = self._load_state()

        logger.info("="*70)
        logger.info("AUTONOMOUS BENCHMARK DATASET GROWER")
        logger.info("="*70)
        logger.info(f"Target: Top 5 SOTA + Top 1 medium (~32B) + Top 1 small (~8B)")
        logger.info(f"Current questions: {self.state['total_questions']}")
        logger.info(f"Models selected: {len(self.state['selected_models'])}")

    def _load_state(self) -> Dict[str, Any]:
        """Load grower state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)

        return {
            'total_questions': 0,
            'selected_models': [],
            'model_metadata': {},
            'benchmarks_processed': [],
            'last_check': None,
            'selection_criteria': {
                'top_sota': 5,
                'top_medium': 1,
                'top_small': 1
            },
            'start_time': datetime.now().isoformat()
        }

    def _save_state(self):
        """Save grower state."""
        self.state['last_check'] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def discover_available_models(self, benchmark: str = "MMLU-Pro") -> List[ModelMetadata]:
        """
        Discover all available models for a benchmark.

        Returns:
            List of model metadata sorted by performance
        """
        logger.info(f"\n🔍 Discovering available models for {benchmark}...")

        # Get list of all prediction files
        api_url = 'https://api.github.com/repos/TIGER-AI-Lab/MMLU-Pro/contents/eval_results'
        response = self.scraper.session.get(api_url, timeout=30)
        response.raise_for_status()
        files = response.json()

        zip_files = [f for f in files if f['name'].endswith('.zip')]
        logger.info(f"Found {len(zip_files)} model prediction files")

        # Sample a few to get performance data
        logger.info("📊 Sampling models to determine rankings...")
        models = []

        for i, file_info in enumerate(zip_files):
            try:
                model_name = file_info['name'].replace('.zip', '').replace('model_outputs_', '')

                # Check cache first
                cache_file = self.scraper.cache_dir / f"mmlu_pro_model_outputs_{model_name}.json"

                if cache_file.exists():
                    with open(cache_file, 'r') as f:
                        cached = json.load(f)
                        metadata = ModelMetadata(
                            name=model_name,
                            accuracy=cached.get('overall_score', 0),
                            total_questions=cached.get('metrics', {}).get('total_questions', 0),
                            source=file_info['html_url']
                        )
                        models.append(metadata)
                        logger.info(f"  ✓ {model_name:50s} {metadata.size_params or '?':>5}B  {metadata.accuracy:>5.1f}% (cached)")
                    continue

                # Download and parse
                logger.info(f"  ⬇️ [{i+1}/{len(zip_files)}] {model_name}")

                import zipfile
                import io

                zip_response = self.scraper.session.get(file_info['download_url'], timeout=60)
                zip_response.raise_for_status()

                with zipfile.ZipFile(io.BytesIO(zip_response.content)) as zf:
                    json_files = [name for name in zf.namelist() if name.endswith('.json')]

                    if json_files:
                        with zf.open(json_files[0]) as json_file:
                            predictions_data = json.load(json_file)

                            # Calculate accuracy
                            if predictions_data and 'correct' in predictions_data[0]:
                                correct = sum(1 for p in predictions_data if p.get('correct', False))
                            else:
                                correct = sum(1 for p in predictions_data
                                            if p.get('pred') == p.get('answer'))

                            total = len(predictions_data)
                            accuracy = (correct / total * 100) if total > 0 else 0

                            metadata = ModelMetadata(
                                name=model_name,
                                accuracy=accuracy,
                                total_questions=total,
                                source=file_info['html_url']
                            )
                            models.append(metadata)

                            # Cache the result
                            with open(cache_file, 'w') as f:
                                json.dump({
                                    'model_name': f'model_outputs_{model_name}',
                                    'benchmark_name': 'MMLU-Pro',
                                    'overall_score': accuracy,
                                    'metrics': {'accuracy': accuracy, 'total_questions': total},
                                    'source_url': file_info['html_url']
                                }, f, indent=2)

                            logger.info(f"      {metadata.size_params or '?':>5}B  {accuracy:>5.1f}% ({correct}/{total})")

                time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.warning(f"    ✗ Error with {file_info['name']}: {e}")

        # Sort by accuracy
        models.sort(key=lambda m: m.accuracy, reverse=True)

        logger.info(f"\n✅ Discovered {len(models)} models")
        return models

    def select_top_models(self, models: List[ModelMetadata]) -> List[ModelMetadata]:
        """
        Intelligently select top models across size categories.

        Selection strategy:
        - Top 5 overall (SOTA)
        - Top 1 medium (~10-40B)
        - Top 1 small (≤10B)
        """
        logger.info("\n🎯 Selecting top models...")

        # Separate by size category
        by_category = {
            'small': [m for m in models if m.size_category == 'small'],
            'medium': [m for m in models if m.size_category == 'medium'],
            'large': [m for m in models if m.size_category == 'large'],
            'unknown': [m for m in models if m.size_category == 'unknown']
        }

        logger.info(f"\nCategory breakdown:")
        for cat, mods in by_category.items():
            if mods:
                avg_acc = sum(m.accuracy for m in mods) / len(mods)
                logger.info(f"  {cat:8s}: {len(mods):2d} models (avg: {avg_acc:.1f}%)")

        selected = []

        # 1. Top 5 overall (SOTA)
        logger.info(f"\n📈 Top 5 SOTA models:")
        top_sota = models[:self.state['selection_criteria']['top_sota']]
        for i, model in enumerate(top_sota, 1):
            logger.info(f"  {i}. {model.name:50s} {model.size_params or '?':>5}B  {model.accuracy:>5.1f}%")
        selected.extend(top_sota)

        # 2. Top 1 medium (if not already in top 5)
        medium_models = [m for m in by_category['medium'] if m not in selected]
        if medium_models:
            top_medium = medium_models[:self.state['selection_criteria']['top_medium']]
            logger.info(f"\n🏢 Top 1 Medium (~10-40B):")
            for model in top_medium:
                logger.info(f"  • {model.name:50s} {model.size_params or '?':>5}B  {model.accuracy:>5.1f}%")
            selected.extend(top_medium)

        # 3. Top 1 small (if not already selected)
        small_models = [m for m in by_category['small'] if m not in selected]
        if small_models:
            top_small = small_models[:self.state['selection_criteria']['top_small']]
            logger.info(f"\n📱 Top 1 Small (≤10B):")
            for model in top_small:
                logger.info(f"  • {model.name:50s} {model.size_params or '?':>5}B  {model.accuracy:>5.1f}%")
            selected.extend(top_small)

        logger.info(f"\n✅ Selected {len(selected)} models total")
        return selected

    def build_dataset_from_selected(
        self,
        selected_models: List[ModelMetadata],
        max_questions: int = 10000
    ) -> Dict[str, Any]:
        """Build dataset using only selected models."""
        logger.info("\n" + "="*70)
        logger.info("BUILDING DATASET FROM SELECTED MODELS")
        logger.info("="*70)

        all_questions = []

        # Load predictions for each selected model
        question_map = {}

        for model in selected_models:
            cache_file = self.scraper.cache_dir / f"mmlu_pro_model_outputs_{model.name}.json"

            if not cache_file.exists():
                logger.warning(f"⚠️  No cache for {model.name}, skipping")
                continue

            logger.info(f"📖 Loading: {model.name}")

            # Re-download full predictions
            try:
                # Find the file
                api_url = 'https://api.github.com/repos/TIGER-AI-Lab/MMLU-Pro/contents/eval_results'
                response = self.scraper.session.get(api_url, timeout=30)
                files = response.json()

                file_info = next((f for f in files if model.name in f['name']), None)
                if not file_info:
                    continue

                import zipfile
                import io

                zip_response = self.scraper.session.get(file_info['download_url'], timeout=60)
                zip_response.raise_for_status()

                with zipfile.ZipFile(io.BytesIO(zip_response.content)) as zf:
                    json_files = [name for name in zf.namelist() if name.endswith('.json')]

                    if json_files:
                        with zf.open(json_files[0]) as json_file:
                            predictions_data = json.load(json_file)

                            logger.info(f"  Loaded {len(predictions_data)} predictions")

                            # Add to question map
                            for pred in predictions_data:
                                q_id = pred.get('question_id') or pred.get('question', '')[:100]

                                if q_id not in question_map:
                                    question_map[q_id] = {
                                        'question': pred.get('question', ''),
                                        'benchmark': 'MMLU-Pro',
                                        'model_scores': {},
                                        'metadata': {
                                            'subject': pred.get('subject', ''),
                                            'category': pred.get('category', ''),
                                            'options': pred.get('options', [])
                                        }
                                    }

                                # Calculate correctness
                                if 'correct' in pred:
                                    is_correct = pred['correct']
                                else:
                                    is_correct = pred.get('pred') == pred.get('answer')

                                question_map[q_id]['model_scores'][model.name] = is_correct

                time.sleep(1)

            except Exception as e:
                logger.warning(f"  ✗ Error loading {model.name}: {e}")

        # Convert to list and calculate success rates
        logger.info(f"\n📊 Processing {len(question_map)} unique questions...")

        for q_id, q_data in question_map.items():
            scores = q_data['model_scores']
            if scores:
                correct_count = sum(1 for v in scores.values() if v)
                q_data['success_rate'] = correct_count / len(scores)
            else:
                q_data['success_rate'] = 0.0

            all_questions.append(q_data)

            if len(all_questions) >= max_questions:
                break

        # Update state
        self.state['total_questions'] = len(all_questions)
        self.state['selected_models'] = [m.name for m in selected_models]
        self.state['model_metadata'] = {m.name: asdict(m) for m in selected_models}
        self.state['benchmarks_processed'] = ['MMLU-Pro']
        self._save_state()

        # Create dataset
        dataset = {
            'metadata': {
                'total_questions': len(all_questions),
                'num_models': len(selected_models),
                'models': [asdict(m) for m in selected_models],
                'selection_criteria': self.state['selection_criteria'],
                'benchmarks': ['MMLU-Pro'],
                'created_at': datetime.now().isoformat()
            },
            'questions': all_questions
        }

        logger.info(f"\n✅ Dataset complete: {len(all_questions):,} questions from {len(selected_models)} models")
        return dataset

    def save_dataset(self, dataset: Dict[str, Any], output_file: Path = None):
        """Save dataset to file."""
        if output_file is None:
            output_file = self.data_dir / "autonomous_dataset.json"

        with open(output_file, 'w') as f:
            json.dump(dataset, f, indent=2)

        size_mb = output_file.stat().st_size / 1024 / 1024
        logger.info(f"\n💾 Saved: {output_file} ({size_mb:.1f} MB)")

    def export_for_vector_db(self, dataset: Dict[str, Any], output_file: Path = None):
        """Export in ChromaDB-compatible format."""
        if output_file is None:
            output_file = self.data_dir / "vector_db_ready.json"

        documents = []
        metadatas = []
        ids = []

        for i, q in enumerate(dataset['questions']):
            documents.append(q['question'])

            metadata = {
                'benchmark': q.get('benchmark', ''),
                'success_rate': q['success_rate'],
                'num_models': len(q['model_scores']),
                'model_scores': json.dumps(q['model_scores']),
                'category': q.get('metadata', {}).get('category', ''),
                'subject': q.get('metadata', {}).get('subject', '')
            }
            metadatas.append(metadata)
            ids.append(f"q_{i}")

        vector_data = {
            'documents': documents,
            'metadatas': metadatas,
            'ids': ids,
            'source_metadata': dataset['metadata']
        }

        with open(output_file, 'w') as f:
            json.dump(vector_data, f, indent=2)

        size_mb = output_file.stat().st_size / 1024 / 1024
        logger.info(f"💾 Vector DB ready: {output_file} ({size_mb:.1f} MB)")

    def run_autonomous_growth(self, max_questions: int = 10000):
        """Run one cycle of autonomous growth."""
        logger.info("\n" + "="*70)
        logger.info("🚀 AUTONOMOUS GROWTH CYCLE")
        logger.info("="*70)

        # 1. Discover available models
        models = self.discover_available_models("MMLU-Pro")

        # 2. Select top models
        selected = self.select_top_models(models)

        # 3. Build dataset
        dataset = self.build_dataset_from_selected(selected, max_questions=max_questions)

        # 4. Save
        self.save_dataset(dataset)
        self.export_for_vector_db(dataset)

        logger.info("\n" + "="*70)
        logger.info("✅ GROWTH CYCLE COMPLETE")
        logger.info("="*70)
        logger.info(f"Questions: {len(dataset['questions']):,}")
        logger.info(f"Models: {len(selected)}")
        logger.info(f"Next check: Run again or schedule periodic updates")


def main():
    """Main entry point."""
    import sys

    grower = AutonomousBenchmarkGrower()

    max_questions = int(sys.argv[1]) if len(sys.argv) > 1 else 10000

    logger.info(f"\nTarget: {max_questions:,} questions")
    logger.info("Press Ctrl+C to stop\n")

    try:
        grower.run_autonomous_growth(max_questions=max_questions)
    except KeyboardInterrupt:
        logger.info("\n\n⏹️  Stopped by user")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)


if __name__ == '__main__':
    main()
