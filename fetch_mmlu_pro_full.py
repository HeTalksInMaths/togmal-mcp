"""
Fetch Full MMLU-Pro Dataset with Model Results

Downloads all 12,031 questions from MMLU-Pro and attempts to populate
with model performance data from available sources.

Sources:
1. HuggingFace datasets (TIGER-Lab/MMLU-Pro)
2. OpenLLM Leaderboard detailed results
3. Direct API calls to models (fallback)
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

try:
    from datasets import load_dataset
    DATASETS_AVAILABLE = True
except ImportError:
    logger.error("datasets not installed. Run: pip install datasets")
    DATASETS_AVAILABLE = False


@dataclass
class FetchStats:
    """Track fetching statistics"""
    total_questions: int = 0
    questions_with_results: int = 0
    models_fetched: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.models_fetched is None:
            self.models_fetched = []
        if self.errors is None:
            self.errors = []


class MMLUProFetcher:
    """
    Fetch complete MMLU-Pro dataset with model results.
    """

    def __init__(self, output_dir: str = "data/mmlu_pro_full"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.stats = FetchStats()

    def fetch_mmlu_pro_questions(self) -> Dict[str, Any]:
        """
        Fetch all 12K questions from MMLU-Pro dataset.

        Returns:
            Dict mapping question_id to question data
        """
        if not DATASETS_AVAILABLE:
            logger.error("Cannot fetch without datasets library")
            return {}

        logger.info("Fetching MMLU-Pro dataset from HuggingFace...")
        logger.info("Dataset: TIGER-Lab/MMLU-Pro (12,031 questions)")

        try:
            # Load dataset
            dataset = load_dataset("TIGER-Lab/MMLU-Pro")

            # MMLU-Pro has train/validation/test splits
            # We'll use validation + test for evaluation
            questions = {}

            for split in ['validation', 'test']:
                logger.info(f"\nProcessing {split} split...")

                if split not in dataset:
                    logger.warning(f"Split '{split}' not found, skipping")
                    continue

                split_data = dataset[split]
                logger.info(f"  Questions in {split}: {len(split_data)}")

                for idx, item in enumerate(split_data):
                    # Generate unique ID
                    question_id = f"mmlu_pro_{split}_{idx}"

                    # Extract question data
                    questions[question_id] = {
                        'question_id': question_id,
                        'source_benchmark': 'MMLU_Pro',
                        'split': split,

                        # Question content
                        'question_text': item.get('question', ''),
                        'choices': item.get('options', []),
                        'correct_answer': item.get('answer', ''),

                        # Metadata
                        'domain': item.get('category', 'unknown'),
                        'cot_content': item.get('cot_content', ''),

                        # To be populated
                        'model_results': {},
                        'success_rate': None,
                        'num_models': 0,
                        'difficulty_tier': None,
                        'difficulty_label': None
                    }

                logger.info(f"  ✓ Loaded {len(split_data)} questions from {split}")

            self.stats.total_questions = len(questions)
            logger.info(f"\n✓ Total questions loaded: {len(questions)}")

            # Show domain distribution
            domains = Counter(q['domain'] for q in questions.values())
            logger.info(f"\n📊 Questions by domain:")
            for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]:
                logger.info(f"  {domain}: {count}")

            return questions

        except Exception as e:
            logger.error(f"Failed to fetch MMLU-Pro: {e}")
            self.stats.errors.append(f"Dataset fetch failed: {e}")
            return {}

    def fetch_model_results_from_leaderboard(
        self,
        questions: Dict[str, Any],
        models: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Attempt to fetch model results from OpenLLM Leaderboard.

        Args:
            questions: Question dict to populate
            models: List of model names to fetch (None = auto-detect top models)

        Returns:
            Updated questions dict with model_results populated
        """
        if not DATASETS_AVAILABLE:
            logger.warning("Cannot fetch model results without datasets library")
            return questions

        logger.info("\n" + "="*80)
        logger.info("Fetching Model Results from OpenLLM Leaderboard")
        logger.info("="*80)

        # Default top models (as of late 2024)
        if models is None:
            models = [
                "meta-llama/Meta-Llama-3.1-70B-Instruct",
                "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "Qwen/Qwen2.5-72B-Instruct",
                "mistralai/Mixtral-8x22B-Instruct-v0.1",
                "mistralai/Mistral-7B-Instruct-v0.3"
            ]

        logger.info(f"\nAttempting to fetch results for {len(models)} models...")

        successful_models = []

        for model_name in models:
            logger.info(f"\n📥 Fetching: {model_name}")

            try:
                # Try to load detailed results from leaderboard
                dataset_name = f"open-llm-leaderboard/details_{model_name.replace('/', '__')}"

                logger.info(f"  Looking for: {dataset_name}")

                # Try to load MMLU results
                try:
                    results = load_dataset(
                        dataset_name,
                        "harness_hendrycksTest_5",  # MMLU config
                        split="latest",
                        trust_remote_code=True
                    )

                    logger.info(f"  ✓ Found {len(results)} results")

                    # Map results to our questions
                    mapped = 0
                    for result_idx, result_item in enumerate(results):
                        # Try to match by question text or index
                        # This is tricky - may need fuzzy matching

                        # For now, use index-based mapping (risky but simple)
                        # Better approach: match by question text hash

                        question_text = result_item.get('example', '')
                        is_correct = result_item.get('metrics', {}).get('acc', 0.0) == 1.0

                        # Find matching question (by text similarity)
                        for qid, qdata in questions.items():
                            if qdata['question_text'][:100] == question_text[:100]:
                                # Match found
                                if 'model_results' not in qdata:
                                    qdata['model_results'] = {}

                                qdata['model_results'][model_name] = {
                                    'is_correct': is_correct,
                                    'answer': result_item.get('prediction', 'UNKNOWN'),
                                    'confidence': None  # Not available
                                }
                                mapped += 1
                                break

                    logger.info(f"  ✓ Mapped {mapped} results to questions")

                    if mapped > 0:
                        successful_models.append(model_name)
                        self.stats.models_fetched.append(model_name)

                except Exception as e:
                    logger.warning(f"  ✗ Could not load detailed results: {e}")
                    logger.info(f"  (This model may not have MMLU-Pro results on leaderboard)")

            except Exception as e:
                logger.error(f"  ✗ Failed to fetch {model_name}: {e}")
                self.stats.errors.append(f"Model {model_name}: {e}")

        logger.info(f"\n✓ Successfully fetched {len(successful_models)} models")

        if len(successful_models) == 0:
            logger.warning("\n⚠️  WARNING: No model results fetched from leaderboard")
            logger.info("   OpenLLM Leaderboard may not have MMLU-Pro results available")
            logger.info("   Options:")
            logger.info("   1. Use direct API calls to get model outputs")
            logger.info("   2. Use pre-computed results from MMLU-Pro paper")
            logger.info("   3. Focus on questions, add model results later")

        # Compute success rates
        questions = self._compute_success_rates(questions)

        return questions

    def _compute_success_rates(self, questions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute success rates and difficulty scores from model results.
        """
        logger.info("\nComputing success rates and difficulty scores...")

        questions_with_results = 0

        for qid, qdata in questions.items():
            model_results = qdata.get('model_results', {})

            if len(model_results) == 0:
                continue

            questions_with_results += 1

            # Count correct
            correct_count = sum(
                1 for r in model_results.values()
                if isinstance(r, dict) and r.get('is_correct', False)
            )

            total_models = len(model_results)
            success_rate = correct_count / total_models if total_models > 0 else 0

            # Update question
            qdata['success_rate'] = success_rate
            qdata['num_models'] = total_models

            # Classify difficulty
            if success_rate < 0.3:
                qdata['difficulty_tier'] = 'low'
                qdata['difficulty_label'] = 'Hard'
            elif success_rate < 0.7:
                qdata['difficulty_tier'] = 'medium'
                qdata['difficulty_label'] = 'Moderate'
            else:
                qdata['difficulty_tier'] = 'high'
                qdata['difficulty_label'] = 'Easy'

        self.stats.questions_with_results = questions_with_results

        logger.info(f"  Questions with model results: {questions_with_results}/{len(questions)}")

        return questions

    def save_dataset(
        self,
        questions: Dict[str, Any],
        filename: str = "mmlu_pro_full.json"
    ) -> None:
        """
        Save dataset to JSON file.
        """
        output_path = self.output_dir / filename

        data = {
            'metadata': {
                'source': 'TIGER-Lab/MMLU-Pro',
                'total_questions': len(questions),
                'questions_with_results': self.stats.questions_with_results,
                'models_fetched': self.stats.models_fetched,
                'fetched_at': str(Path.ctime(Path.cwd()))
            },
            'questions': questions
        }

        logger.info(f"\nSaving dataset to {output_path}...")

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Saved {len(questions)} questions ({file_size_mb:.1f} MB)")

    def generate_summary_report(self) -> str:
        """
        Generate summary report of fetch operation.
        """
        report = "# MMLU-Pro Dataset Fetch Report\n\n"

        report += "## Summary\n\n"
        report += f"- **Total questions**: {self.stats.total_questions:,}\n"
        report += f"- **Questions with model results**: {self.stats.questions_with_results:,}\n"
        report += f"- **Coverage**: {self.stats.questions_with_results/max(self.stats.total_questions, 1)*100:.1f}%\n"
        report += f"- **Models fetched**: {len(self.stats.models_fetched)}\n\n"

        if self.stats.models_fetched:
            report += "## Models with Results\n\n"
            for model in self.stats.models_fetched:
                report += f"- {model}\n"
            report += "\n"

        if self.stats.errors:
            report += "## Errors Encountered\n\n"
            for error in self.stats.errors[:10]:  # Top 10
                report += f"- {error}\n"
            report += "\n"

        report += "## Next Steps\n\n"

        if self.stats.questions_with_results == 0:
            report += "⚠️ **No model results fetched**\n\n"
            report += "Options:\n"
            report += "1. Run models via API (HuggingFace Inference, OpenAI, Anthropic)\n"
            report += "2. Use pre-computed results from papers/repos\n"
            report += "3. Focus on dataset structure, add results later\n\n"
        elif self.stats.questions_with_results < self.stats.total_questions * 0.5:
            report += "⚠️ **Partial model results**\n\n"
            report += f"Only {self.stats.questions_with_results/self.stats.total_questions*100:.0f}% of questions have results.\n"
            report += "Consider fetching more models or running inference.\n\n"
        else:
            report += "✅ **Good coverage**\n\n"
            report += f"Ready to analyze {self.stats.questions_with_results:,} questions.\n\n"

        return report


def main():
    """
    Main function to fetch full MMLU-Pro dataset.
    """
    print("="*80)
    print("MMLU-Pro Full Dataset Fetcher")
    print("="*80)
    print("\nThis will download all ~12K questions from MMLU-Pro")
    print("and attempt to fetch model results from OpenLLM Leaderboard.\n")

    if not DATASETS_AVAILABLE:
        print("❌ datasets library not installed")
        print("   Install with: pip install datasets")
        return

    # Initialize fetcher
    fetcher = MMLUProFetcher(output_dir="data/mmlu_pro_full")

    # Step 1: Fetch questions
    print("\n" + "="*80)
    print("STEP 1: Fetching Questions")
    print("="*80)

    questions = fetcher.fetch_mmlu_pro_questions()

    if len(questions) == 0:
        print("\n❌ Failed to fetch questions")
        return

    # Step 2: Fetch model results
    print("\n" + "="*80)
    print("STEP 2: Fetching Model Results")
    print("="*80)
    print("\nAttempting to fetch from OpenLLM Leaderboard...")
    print("(This may take a few minutes and might not find results)\n")

    questions = fetcher.fetch_model_results_from_leaderboard(questions)

    # Step 3: Save dataset
    print("\n" + "="*80)
    print("STEP 3: Saving Dataset")
    print("="*80)

    fetcher.save_dataset(questions, filename="mmlu_pro_12k.json")

    # Generate report
    report = fetcher.generate_summary_report()

    report_path = fetcher.output_dir / "fetch_report.md"
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\n✓ Summary report: {report_path}")

    # Print summary
    print("\n" + "="*80)
    print("FETCH COMPLETE")
    print("="*80)
    print(f"\n📊 Results:")
    print(f"  Total questions: {fetcher.stats.total_questions:,}")
    print(f"  With model results: {fetcher.stats.questions_with_results:,} ({fetcher.stats.questions_with_results/max(fetcher.stats.total_questions,1)*100:.1f}%)")
    print(f"  Models: {len(fetcher.stats.models_fetched)}")

    print(f"\n📁 Output:")
    print(f"  {fetcher.output_dir}/mmlu_pro_12k.json")
    print(f"  {fetcher.output_dir}/fetch_report.md")

    if fetcher.stats.questions_with_results == 0:
        print(f"\n⚠️  WARNING: No model results fetched")
        print(f"   OpenLLM Leaderboard may not have MMLU-Pro results")
        print(f"   You can still use the questions, but need to:")
        print(f"   1. Run models yourself via API")
        print(f"   2. Or use error taxonomy on available data")

    print("\n✅ Ready for analysis!")
    print("   Next: python week1_2_validation.py")


if __name__ == "__main__":
    main()
