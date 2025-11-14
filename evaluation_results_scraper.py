#!/usr/bin/env python3
"""
Evaluation Results Scraper
===========================

Alternative to HuggingFace for getting benchmark evaluation results.
Scrapes model performance data from public GitHub repos and leaderboards.

Author: ToGMAL Project
"""

import json
import logging
import os
import requests
import zipfile
import io
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
import time
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ModelBenchmarkScore:
    """Model performance on a benchmark."""
    model_name: str
    benchmark_name: str

    # Aggregate scores
    overall_score: Optional[float] = None

    # Individual benchmark metrics
    metrics: Dict[str, float] = None

    # Per-question predictions (if available)
    predictions: List[Dict[str, Any]] = None

    # Metadata
    parameters: Optional[str] = None
    source_url: str = ""
    last_updated: str = ""

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
        if self.predictions is None:
            self.predictions = []


class EvaluationResultsScraper:
    """Scrapes evaluation results from public sources."""

    # Known sources with model evaluation data
    GITHUB_SOURCES = [
        {
            'name': 'open-llm-leaderboard-archive',
            'repo': 'dsdanielpark/open-llm-leaderboard-report',
            'data_url': 'https://raw.githubusercontent.com/dsdanielpark/open-llm-leaderboard-report/main/assets/20231031/20231031.csv',
            'format': 'csv',
            'benchmarks': ['ARC', 'HellaSwag', 'MMLU', 'TruthfulQA']
        },
        {
            'name': 'mmlu-pro-predictions',
            'repo': 'TIGER-AI-Lab/MMLU-Pro',
            'api_url': 'https://api.github.com/repos/TIGER-AI-Lab/MMLU-Pro/contents/eval_results',
            'format': 'zip',
            'benchmarks': ['MMLU-Pro']
        }
    ]

    def __init__(self, cache_dir: Path = Path("./data/eval_cache")):
        """Initialize the scraper."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ToGMAL-Benchmark-Scraper/1.0'
        })

        logger.info("Evaluation Results Scraper initialized")

    def fetch_all_sources(self, include_per_question: bool = False) -> List[ModelBenchmarkScore]:
        """
        Fetch evaluation results from all sources.

        Args:
            include_per_question: Whether to fetch per-question predictions (slower)

        Returns:
            List of model benchmark scores
        """
        logger.info("🔍 Fetching evaluation results from all sources...")
        all_results = []

        for source in self.GITHUB_SOURCES:
            try:
                logger.info(f"\n📊 Processing: {source['name']}")

                if source['format'] == 'csv':
                    results = self._fetch_csv_source(source)
                elif source['format'] == 'zip' and include_per_question:
                    results = self._fetch_zip_predictions(source)
                else:
                    logger.info(f"  ⏩ Skipping {source['format']} (per-question disabled)")
                    continue

                all_results.extend(results)
                logger.info(f"  ✓ Loaded {len(results)} model evaluations")

                time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.warning(f"  ✗ Error with {source['name']}: {e}")

        logger.info(f"\n✅ Total: {len(all_results)} model benchmark evaluations")
        return all_results

    def _fetch_csv_source(self, source: Dict[str, Any]) -> List[ModelBenchmarkScore]:
        """Fetch aggregate scores from CSV source."""
        cache_file = self.cache_dir / f"{source['name']}.json"

        # Check cache
        if cache_file.exists():
            logger.info("  Using cached data")
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return [ModelBenchmarkScore(**item) for item in data]

        # Fetch
        logger.info(f"  Downloading: {source['data_url']}")
        response = self.session.get(source['data_url'], timeout=30)
        response.raise_for_status()

        # Parse CSV
        results = []
        csv_data = csv.DictReader(response.text.strip().split('\n'))

        for row in csv_data:
            # Extract metrics from row
            metrics = {}
            for benchmark in source['benchmarks']:
                # Try to find the column (might have shot annotation)
                for col_name in row.keys():
                    if benchmark.lower() in col_name.lower():
                        try:
                            metrics[benchmark] = float(row[col_name])
                        except (ValueError, KeyError):
                            pass
                        break

            score = ModelBenchmarkScore(
                model_name=row.get('Model', ''),
                benchmark_name='Open-LLM-Leaderboard',
                overall_score=float(row.get('Average', 0)) if row.get('Average') else None,
                metrics=metrics,
                parameters=row.get('Parameters', ''),
                source_url=row.get('URL', source['data_url']),
                last_updated='2023-10-31'
            )
            results.append(score)

        # Cache
        with open(cache_file, 'w') as f:
            json.dump([asdict(s) for s in results], f, indent=2)

        return results

    def _fetch_zip_predictions(self, source: Dict[str, Any]) -> List[ModelBenchmarkScore]:
        """Fetch per-question predictions from ZIP files."""
        logger.info("  Fetching ZIP prediction files...")

        # Get list of files
        response = self.session.get(source['api_url'], timeout=30)
        response.raise_for_status()
        files = response.json()

        results = []
        zip_files = [f for f in files if f['name'].endswith('.zip')]

        logger.info(f"  Found {len(zip_files)} prediction files (sampling 5 for speed)")

        # Sample a few files to avoid downloading everything
        sample_files = zip_files[:5]

        for file_info in sample_files:
            try:
                model_name = file_info['name'].replace('.zip', '')
                cache_file = self.cache_dir / f"mmlu_pro_{model_name}.json"

                if cache_file.exists():
                    logger.info(f"    ✓ {model_name} (cached)")
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        results.append(ModelBenchmarkScore(**data))
                    continue

                logger.info(f"    ⬇️ {model_name}")

                # Download ZIP
                zip_response = self.session.get(file_info['download_url'], timeout=60)
                zip_response.raise_for_status()

                # Extract and parse
                with zipfile.ZipFile(io.BytesIO(zip_response.content)) as zf:
                    # Find JSON file inside
                    json_files = [name for name in zf.namelist() if name.endswith('.json')]

                    if json_files:
                        with zf.open(json_files[0]) as json_file:
                            predictions_data = json.load(json_file)

                            # Calculate accuracy
                            # Check if predictions have 'correct' field or need to compare 'pred' vs 'answer'
                            if predictions_data and 'correct' in predictions_data[0]:
                                correct = sum(1 for p in predictions_data if p.get('correct', False))
                            else:
                                # Compare pred vs answer
                                correct = sum(1 for p in predictions_data
                                            if p.get('pred') == p.get('answer'))

                            total = len(predictions_data)
                            accuracy = (correct / total * 100) if total > 0 else 0

                            score = ModelBenchmarkScore(
                                model_name=model_name,
                                benchmark_name='MMLU-Pro',
                                overall_score=accuracy,
                                metrics={'accuracy': accuracy, 'total_questions': total},
                                predictions=predictions_data[:100],  # Store sample
                                source_url=file_info['html_url'],
                                last_updated=file_info.get('sha', '')[:7]
                            )

                            results.append(score)

                            # Cache
                            with open(cache_file, 'w') as f:
                                json.dump(asdict(score), f, indent=2)

                            logger.info(f"      Accuracy: {accuracy:.1f}% ({correct}/{total})")

                time.sleep(2)  # Rate limiting

            except Exception as e:
                logger.warning(f"    ✗ Error with {file_info['name']}: {e}")

        return results

    def get_benchmark_questions(
        self,
        benchmark_name: str = 'MMLU-Pro',
        max_questions: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Extract unique questions with model performance data.

        Returns questions in ToGMAL format:
        {
            'question': str,
            'benchmark': str,
            'model_scores': {model_name: correct/incorrect},
            'success_rate': float,
            'metadata': {...}
        }
        """
        logger.info(f"📝 Extracting questions from {benchmark_name}...")

        # For MMLU-Pro, fetch a few model predictions
        results = self._fetch_zip_predictions({
            'api_url': 'https://api.github.com/repos/TIGER-AI-Lab/MMLU-Pro/contents/eval_results',
            'benchmarks': ['MMLU-Pro']
        })

        if not results:
            logger.warning("No predictions found")
            return []

        # Combine predictions from multiple models
        question_map = {}

        for model_result in results:
            model_name = model_result.model_name

            for pred in model_result.predictions:
                # Extract question identifier
                q_id = pred.get('question_id') or pred.get('question', '')[:100]

                if q_id not in question_map:
                    question_map[q_id] = {
                        'question': pred.get('question', ''),
                        'benchmark': benchmark_name,
                        'model_scores': {},
                        'metadata': {
                            'subject': pred.get('subject', ''),
                            'category': pred.get('category', ''),
                            'options': pred.get('options', [])
                        }
                    }

                # Add this model's result
                # Check if 'correct' field exists, otherwise compare pred vs answer
                if 'correct' in pred:
                    is_correct = pred['correct']
                else:
                    is_correct = pred.get('pred') == pred.get('answer')

                question_map[q_id]['model_scores'][model_name] = is_correct

        # Calculate success rates
        questions = []
        for q_data in list(question_map.values())[:max_questions]:
            scores = q_data['model_scores']
            if scores:
                correct_count = sum(1 for v in scores.values() if v)
                q_data['success_rate'] = correct_count / len(scores)
            else:
                q_data['success_rate'] = 0.0

            questions.append(q_data)

        logger.info(f"✓ Extracted {len(questions)} questions with model scores")
        return questions

    def export_to_json(self, output_file: Path, include_per_question: bool = False):
        """Export all results to JSON file."""
        logger.info(f"\n💾 Exporting to {output_file}...")

        results = self.fetch_all_sources(include_per_question=include_per_question)

        data = {
            'metadata': {
                'total_models': len(results),
                'sources': [s['name'] for s in self.GITHUB_SOURCES],
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'results': [asdict(r) for r in results]
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"✅ Exported {len(results)} evaluations ({output_file.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == '__main__':
    logger.info("="*70)
    logger.info("EVALUATION RESULTS SCRAPER - Test Run")
    logger.info("="*70)

    scraper = EvaluationResultsScraper()

    # Test 1: Fetch aggregate scores
    logger.info("\n### TEST 1: Aggregate Scores ###")
    results = scraper.fetch_all_sources(include_per_question=False)

    if results:
        logger.info(f"\nSample result:")
        sample = results[0]
        logger.info(f"  Model: {sample.model_name}")
        logger.info(f"  Benchmark: {sample.benchmark_name}")
        logger.info(f"  Overall: {sample.overall_score}")
        logger.info(f"  Metrics: {sample.metrics}")

    # Test 2: Fetch per-question predictions (sample)
    logger.info("\n\n### TEST 2: Per-Question Predictions ###")
    questions = scraper.get_benchmark_questions(max_questions=10)

    if questions:
        logger.info(f"\nSample question:")
        q = questions[0]
        logger.info(f"  Question: {q['question'][:100]}...")
        logger.info(f"  Models tested: {len(q['model_scores'])}")
        logger.info(f"  Success rate: {q['success_rate']*100:.1f}%")

    # Export
    logger.info("\n\n### Exporting Results ###")
    scraper.export_to_json(
        Path("./data/evaluation_results.json"),
        include_per_question=False
    )

    logger.info("\n" + "="*70)
    logger.info("✅ Test complete!")
    logger.info("="*70)
