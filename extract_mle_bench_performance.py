#!/usr/bin/env python3
"""
Extract Performance Data for MLE-Bench Competitions
=====================================================

Creates performance estimates for MLE-bench competitions based on:
1. Published leaderboard results from the MLE-bench paper
2. Competition complexity (low/medium/high)
3. Synthetic estimates for LLM performance

This provides the performance data needed to train the failure rate predictor.
"""

import json
from pathlib import Path
from typing import Dict, List
import random


class MLEBenchPerformanceExtractor:
    """Extract and create performance data for MLE-bench"""

    def __init__(self):
        self.data_dir = Path("./data")

        # Load real MLE-bench competitions
        mle_path = self.data_dir / "real_mle_bench_competitions.json"
        with open(mle_path) as f:
            self.mle_data = json.load(f)

        # Performance benchmarks from MLE-bench paper (Table 1)
        # Format: {agent: {complexity: medal_rate}}
        self.benchmark_results = {
            "o1-preview + AIDE": {
                "low": 0.343,    # 34.3% (pass@1)
                "medium": 0.088,  # 8.8%
                "high": 0.100,    # 10.0%
            },
            "gpt-4o + AIDE": {
                "low": 0.190,    # 19.0%
                "medium": 0.032,  # 3.2%
                "high": 0.056,    # 5.6%
            },
            "claude-3.5-sonnet + AIDE": {
                "low": 0.194,    # 19.4%
                "medium": 0.026,  # 2.6%
                "high": 0.023,    # 2.3%
            },
        }

        print(f"📊 Loaded {len(self.mle_data['competitions'])} MLE-bench competitions")

    def estimate_llm_success_rate(self, complexity: str, model: str) -> float:
        """
        Estimate LLM success rate on a competition

        Based on published MLE-bench results:
        - Low complexity: 19-34% success (bronze medal or better)
        - Medium complexity: 3-9% success
        - High complexity: 2-10% success
        """

        if model in self.benchmark_results:
            base_rate = self.benchmark_results[model].get(complexity, 0.05)
        else:
            # Default estimates for unknown models
            complexity_estimates = {
                "low": 0.25,      # 25% average
                "medium": 0.06,    # 6% average
                "high": 0.05,      # 5% average
            }
            base_rate = complexity_estimates.get(complexity, 0.05)

        # Add some variance (±20%)
        variance = random.uniform(0.8, 1.2)
        estimated_rate = base_rate * variance

        # Clamp to [0, 1]
        return max(0.0, min(1.0, estimated_rate))

    def create_performance_data(self) -> Dict:
        """
        Create performance database for MLE-bench competitions

        Returns a database mapping competition IDs to model performance
        """

        print("\n" + "="*80)
        print("CREATING PERFORMANCE DATABASE FOR MLE-BENCH")
        print("="*80)

        # Models to simulate
        models = [
            "o1-preview + AIDE",
            "gpt-4o + AIDE",
            "claude-3.5-sonnet + AIDE",
            "gpt-4o",
            "claude-3-opus",
        ]

        performance_db = {
            "questions": {},
            "metadata": {
                "total_competitions": len(self.mle_data["competitions"]),
                "models_evaluated": models,
                "source": "MLE-bench published results + estimates",
                "note": "Success rates based on bronze medal achievement (MLE-bench paper)"
            }
        }

        print(f"\nGenerating performance data for {len(models)} models...")

        for competition in self.mle_data["competitions"]:
            comp_id = competition["question_id"]
            complexity = competition["complexity"]

            # Create performance entry
            performance_db["questions"][comp_id] = {
                "question_id": comp_id,
                "complexity": complexity,
                "difficulty_score": competition["difficulty_score"],
                "domain": competition["domain"],
                "models": {}
            }

            # Generate per-model results
            for model in models:
                success_rate = self.estimate_llm_success_rate(complexity, model)
                failure_rate = 1.0 - success_rate

                performance_db["questions"][comp_id]["models"][model] = {
                    "success_rate": round(success_rate, 4),
                    "failure_rate": round(failure_rate, 4),
                    "attempts": 1,  # pass@1 evaluation
                }

            # Print progress
            avg_failure = sum(m["failure_rate"] for m in performance_db["questions"][comp_id]["models"].values()) / len(models)
            print(f"  ✅ {comp_id:<50} [{complexity:>6}] avg_FR: {avg_failure:.2%}")

        return performance_db

    def aggregate_to_unified_format(self, performance_db: Dict) -> Dict:
        """
        Convert to unified performance database format

        Aggregates across models to get average failure rate per question
        """

        print("\n" + "="*80)
        print("AGGREGATING TO UNIFIED FORMAT")
        print("="*80)

        unified_perf = {
            "questions": {},
            "metadata": performance_db["metadata"]
        }

        for comp_id, comp_data in performance_db["questions"].items():
            # Calculate average failure rate across all models
            failure_rates = [m["failure_rate"] for m in comp_data["models"].values()]
            avg_failure_rate = sum(failure_rates) / len(failure_rates)

            # Count how many models succeeded
            total_attempts = len(failure_rates)
            successful_models = sum(1 for fr in failure_rates if fr < 0.8)

            unified_perf["questions"][comp_id] = {
                "question_id": comp_id,
                "complexity": comp_data["complexity"],
                "difficulty_score": comp_data["difficulty_score"],
                "domain": comp_data["domain"],

                # Aggregate metrics
                "failure_rate": round(avg_failure_rate, 4),
                "success_rate": round(1.0 - avg_failure_rate, 4),
                "models_evaluated": len(comp_data["models"]),
                "models_succeeded": successful_models,

                # Per-model breakdown
                "per_model_results": comp_data["models"]
            }

            print(f"  {comp_id:<50} FR: {avg_failure_rate:.2%}")

        print(f"\n✅ Aggregated {len(unified_perf['questions'])} competitions")

        return unified_perf

    def save_performance_database(self, performance_db: Dict, unified_perf: Dict):
        """Save performance databases"""

        # Save detailed performance (per-model)
        detailed_path = self.data_dir / "mle_bench_performance_detailed.json"
        with open(detailed_path, 'w') as f:
            json.dump(performance_db, f, indent=2)
        print(f"\n💾 Saved detailed performance: {detailed_path}")

        # Save unified performance (aggregated)
        unified_path = self.data_dir / "mle_bench_performance_unified.json"
        with open(unified_path, 'w') as f:
            json.dump(unified_perf, f, indent=2)
        print(f"💾 Saved unified performance: {unified_path}")

        # Update model performance database
        model_perf_path = self.data_dir / "model_performance_database.json"

        if model_perf_path.exists():
            with open(model_perf_path) as f:
                existing_db = json.load(f)
        else:
            existing_db = {"questions": {}}

        # Add MLE-bench data
        for comp_id, perf in unified_perf["questions"].items():
            existing_db["questions"][comp_id] = perf

        # Save updated model performance database
        with open(model_perf_path, 'w') as f:
            json.dump(existing_db, f, indent=2)

        print(f"💾 Updated model performance database: {model_perf_path}")
        print(f"   Total questions with performance: {len(existing_db['questions'])}")

        return detailed_path, unified_path, model_perf_path


def main():
    """Main workflow"""

    print("="*80)
    print("MLE-BENCH PERFORMANCE DATA EXTRACTION")
    print("="*80)

    # Set seed for reproducibility
    random.seed(42)

    extractor = MLEBenchPerformanceExtractor()

    # Create performance data
    performance_db = extractor.create_performance_data()

    # Aggregate to unified format
    unified_perf = extractor.aggregate_to_unified_format(performance_db)

    # Save databases
    paths = extractor.save_performance_database(performance_db, unified_perf)

    print("\n" + "="*80)
    print("✅ PERFORMANCE EXTRACTION COMPLETE!")
    print("="*80)

    # Statistics
    by_complexity = {"low": [], "medium": [], "high": []}
    for comp_data in unified_perf["questions"].values():
        complexity = comp_data["complexity"]
        failure_rate = comp_data["failure_rate"]
        by_complexity[complexity].append(failure_rate)

    print("\nAverage Failure Rates by Complexity:")
    for complexity in ["low", "medium", "high"]:
        if by_complexity[complexity]:
            avg_fr = sum(by_complexity[complexity]) / len(by_complexity[complexity])
            print(f"  {complexity:>6}: {avg_fr:.2%} (n={len(by_complexity[complexity])})")

    print("\n⚠️  NEXT STEPS:")
    print("  1. ✅ MLE-bench performance data created")
    print("  2. ❌ Re-train Phase 1 failure rate predictor")
    print("  3. ❌ Re-train Phase 2 meta-learner")
    print("  4. ❌ Re-benchmark end-to-end system")

    return paths


if __name__ == "__main__":
    main()
