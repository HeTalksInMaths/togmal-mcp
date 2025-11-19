#!/usr/bin/env python3
"""
Comprehensive Benchmark Data Expansion
=======================================

Fetch and integrate multiple benchmark datasets with LLM evaluation results:
1. MLE-Bench (ML engineering tasks)
2. MATH dataset (mathematical reasoning)
3. HumanEval (code generation)
4. MBPP (code generation)
5. BigCodeBench (code tasks)
6. Additional MMLU-Pro results

Goal: Expand from 170 → 5,000+ questions with performance data
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import requests
from datasets import load_dataset
from tqdm import tqdm


class BenchmarkExpander:
    """Fetch and integrate multiple benchmarks with LLM results"""

    def __init__(self):
        self.output_dir = Path("./data")
        self.output_dir.mkdir(exist_ok=True)

        # Load existing data
        self.existing_questions = self._load_existing_questions()
        self.existing_performance = self._load_existing_performance()

        print(f"📊 Current state:")
        print(f"   Questions: {len(self.existing_questions):,}")
        print(f"   With performance data: {len(self.existing_performance)}")

    def _load_existing_questions(self) -> Dict:
        """Load existing unified question database"""
        path = self.output_dir / "unified_database_with_mmlu_pro.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                return {q['question_id']: q for q in data['questions']}
        return {}

    def _load_existing_performance(self) -> Dict:
        """Load existing performance database"""
        path = self.output_dir / "model_performance_database.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                return data['questions']
        return {}

    def fetch_math_dataset(self) -> int:
        """
        Fetch MATH dataset (mathematical reasoning)
        Source: hendrycksTest MATH (12,500 problems)
        """
        print("\n🔢 Fetching MATH dataset...")

        try:
            dataset = load_dataset("hendrycksTest/MATH", split="test")
            print(f"   Loaded {len(dataset)} MATH problems")

            added = 0
            for idx, item in enumerate(tqdm(dataset, desc="Processing MATH")):
                question_id = f"math_{idx}"

                # Create question entry
                question = {
                    'question_id': question_id,
                    'question_text': item['problem'],
                    'domain': 'mathematics',
                    'subdomain': item.get('subject', 'general'),
                    'difficulty_score': self._estimate_difficulty(item.get('level', 3)) / 5,
                    'source': 'MATH',
                    'answer': item.get('solution'),
                    'options': []
                }

                self.existing_questions[question_id] = question
                added += 1

            print(f"   ✅ Added {added} MATH questions")
            return added

        except Exception as e:
            print(f"   ❌ Failed to fetch MATH: {e}")
            return 0

    def fetch_humaneval(self) -> int:
        """
        Fetch HumanEval (code generation)
        Source: openai/HumanEval (164 problems)
        """
        print("\n💻 Fetching HumanEval...")

        try:
            dataset = load_dataset("openai_humaneval", split="test")
            print(f"   Loaded {len(dataset)} HumanEval problems")

            added = 0
            for idx, item in enumerate(tqdm(dataset, desc="Processing HumanEval")):
                question_id = f"humaneval_{item['task_id']}"

                question = {
                    'question_id': question_id,
                    'question_text': item['prompt'],
                    'domain': 'programming',
                    'subdomain': 'python',
                    'difficulty_score': 0.6,  # Generally medium-hard
                    'source': 'HumanEval',
                    'canonical_solution': item.get('canonical_solution'),
                    'test_cases': item.get('test'),
                    'entry_point': item.get('entry_point'),
                    'options': []
                }

                self.existing_questions[question_id] = question
                added += 1

            print(f"   ✅ Added {added} HumanEval questions")
            return added

        except Exception as e:
            print(f"   ❌ Failed to fetch HumanEval: {e}")
            return 0

    def fetch_mbpp(self) -> int:
        """
        Fetch MBPP (Mostly Basic Python Problems)
        Source: google-research-datasets/mbpp (974 problems)
        """
        print("\n🐍 Fetching MBPP...")

        try:
            dataset = load_dataset("mbpp", split="test")
            print(f"   Loaded {len(dataset)} MBPP problems")

            added = 0
            for idx, item in enumerate(tqdm(dataset, desc="Processing MBPP")):
                question_id = f"mbpp_{item['task_id']}"

                question = {
                    'question_id': question_id,
                    'question_text': item['text'],
                    'domain': 'programming',
                    'subdomain': 'python_basic',
                    'difficulty_score': 0.4,  # Generally easier than HumanEval
                    'source': 'MBPP',
                    'code': item.get('code'),
                    'test_list': item.get('test_list'),
                    'options': []
                }

                self.existing_questions[question_id] = question
                added += 1

            print(f"   ✅ Added {added} MBPP questions")
            return added

        except Exception as e:
            print(f"   ❌ Failed to fetch MBPP: {e}")
            return 0

    def fetch_mle_bench_real(self) -> int:
        """
        Fetch real MLE-Bench data
        NOTE: MLE-Bench may not have public dataset - check availability
        """
        print("\n🏆 Fetching MLE-Bench (real)...")

        # TODO: Check if MLE-Bench has public HuggingFace dataset
        # For now, note that we need to find the source

        print("   ⚠️  MLE-Bench real data not yet available publicly")
        print("   Consider: papers with code, GitHub releases, author contact")
        return 0

    def fetch_additional_mmlu_pro_results(self) -> int:
        """
        Fetch MORE MMLU-Pro evaluation results from various sources

        Sources:
        - OpenLLM Leaderboard detailed results
        - Model cards with MMLU-Pro scores
        - Evaluation harness outputs
        """
        print("\n📚 Fetching additional MMLU-Pro results...")

        # This requires accessing evaluation result datasets
        # Common sources:
        # 1. open-llm-leaderboard detailed results
        # 2. Individual model evaluation reports

        print("   ⚠️  Need to implement OpenLLM Leaderboard scraping")
        print("   See: fetch_real_benchmark_data.py for infrastructure")
        return 0

    def _estimate_difficulty(self, level: int) -> float:
        """Estimate difficulty from level (1-5 scale)"""
        # Map to 0-1 scale
        return min(max(level / 5.0, 0.0), 1.0)

    def save_expanded_database(self):
        """Save expanded question database"""
        output_path = self.output_dir / "unified_database_expanded.json"

        questions_list = list(self.existing_questions.values())

        database = {
            'questions': questions_list,
            'metadata': {
                'total_questions': len(questions_list),
                'sources': list(set(q['source'] for q in questions_list)),
                'last_updated': '2025-11-19'
            }
        }

        with open(output_path, 'w') as f:
            json.dump(database, f, indent=2)

        print(f"\n💾 Saved expanded database: {output_path}")
        print(f"   Total questions: {len(questions_list):,}")

        # Statistics
        by_source = {}
        for q in questions_list:
            source = q['source']
            by_source[source] = by_source.get(source, 0) + 1

        print(f"\n   By source:")
        for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
            print(f"     {source}: {count:,}")

    def expand_all(self):
        """Run all expansion steps"""
        print("="*80)
        print("COMPREHENSIVE BENCHMARK EXPANSION")
        print("="*80)

        total_added = 0

        # Fetch datasets
        total_added += self.fetch_math_dataset()
        total_added += self.fetch_humaneval()
        total_added += self.fetch_mbpp()
        total_added += self.fetch_mle_bench_real()
        total_added += self.fetch_additional_mmlu_pro_results()

        # Save expanded database
        self.save_expanded_database()

        print("\n" + "="*80)
        print(f"✅ EXPANSION COMPLETE")
        print("="*80)
        print(f"   Questions added: {total_added:,}")
        print(f"   Total questions: {len(self.existing_questions):,}")

        # Next steps
        print("\n⚠️  NEXT STEPS:")
        print("   1. ❌ Need LLM evaluation results for new questions")
        print("   2. ❌ Run evaluations OR fetch from published results")
        print("   3. ❌ Update model_performance_database.json")
        print("   4. ✅ Then retrain Phase 2 meta-predictor")

        return total_added


if __name__ == "__main__":
    expander = BenchmarkExpander()
    expander.expand_all()
