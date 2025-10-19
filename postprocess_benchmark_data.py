#!/usr/bin/env python3
"""
Post-Process Benchmark Data
============================

Strategy:
1. Load raw benchmark results
2. Stratify by difficulty tier (low/medium/high success)
3. Select balanced sample for vector DB:
   - 30% LOW success (0-30%): Hard questions - model limitations
   - 40% MEDIUM success (30-70%): Capability boundary - most interesting
   - 30% HIGH success (70-100%): Within capability - baseline
4. Export stratified sample for vector DB indexing

This ensures we have good coverage across the capability spectrum.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BenchmarkDataPostProcessor:
    """Post-process raw benchmark data for vector DB"""
    
    def __init__(self, input_file: Path = Path("./data/benchmark_results/raw_benchmark_results.json")):
        self.input_file = input_file
        self.questions = {}
        self.stratified_sample = {}
    
    def load_raw_data(self):
        """Load raw benchmark results"""
        logger.info(f"Loading raw data from {self.input_file}...")
        
        with open(self.input_file, 'r') as f:
            data = json.load(f)
        
        self.questions = data['questions']
        logger.info(f"Loaded {len(self.questions)} questions")
        
        return self.questions
    
    def analyze_difficulty_distribution(self) -> Dict[str, Any]:
        """Analyze distribution across difficulty tiers"""
        logger.info("Analyzing difficulty distribution...")
        
        distribution = {
            "low": [],  # 0-30% success
            "medium": [],  # 30-70% success
            "high": []  # 70-100% success
        }
        
        for qid, q in self.questions.items():
            tier = q.get('difficulty_tier')
            if tier and tier in distribution:
                distribution[tier].append(qid)
        
        stats = {
            "total_questions": len(self.questions),
            "low_success_count": len(distribution["low"]),
            "medium_success_count": len(distribution["medium"]),
            "high_success_count": len(distribution["high"]),
            "low_success_pct": len(distribution["low"]) / len(self.questions) * 100,
            "medium_success_pct": len(distribution["medium"]) / len(self.questions) * 100,
            "high_success_pct": len(distribution["high"]) / len(self.questions) * 100
        }
        
        logger.info(f"  LOW success (0-30%): {stats['low_success_count']} ({stats['low_success_pct']:.1f}%)")
        logger.info(f"  MEDIUM success (30-70%): {stats['medium_success_count']} ({stats['medium_success_pct']:.1f}%)")
        logger.info(f"  HIGH success (70-100%): {stats['high_success_count']} ({stats['high_success_pct']:.1f}%)")
        
        return distribution, stats
    
    def stratified_sampling(
        self,
        target_size: int = 1000,
        low_pct: float = 0.30,
        medium_pct: float = 0.40,
        high_pct: float = 0.30
    ) -> Dict[str, Any]:
        """
        Create stratified sample with balanced difficulty distribution.
        
        Args:
            target_size: Total number of questions to sample
            low_pct: Percentage of LOW success questions (0-30% success)
            medium_pct: Percentage of MEDIUM success questions (30-70%)
            high_pct: Percentage of HIGH success questions (70-100%)
        """
        logger.info(f"Creating stratified sample (target: {target_size} questions)...")
        logger.info(f"  Target distribution: {low_pct*100:.0f}% low, {medium_pct*100:.0f}% medium, {high_pct*100:.0f}% high")
        
        distribution, _ = self.analyze_difficulty_distribution()
        
        # Calculate target counts per tier
        target_counts = {
            "low": int(target_size * low_pct),
            "medium": int(target_size * medium_pct),
            "high": int(target_size * high_pct)
        }
        
        sampled = {}
        random.seed(42)  # Reproducibility
        
        for tier, target_count in target_counts.items():
            available = distribution[tier]
            
            if len(available) >= target_count:
                # Sample from available
                selected = random.sample(available, target_count)
            else:
                # Take all available
                selected = available
                logger.warning(f"  Only {len(available)} {tier} questions available (target: {target_count})")
            
            for qid in selected:
                sampled[qid] = self.questions[qid]
            
            logger.info(f"  Sampled {len(selected)} {tier} success questions")
        
        self.stratified_sample = sampled
        logger.info(f"Total sampled: {len(sampled)} questions")
        
        return sampled
    
    def export_for_vector_db(self, output_file: Path = Path("./data/benchmark_results/stratified_sample.json")):
        """Export stratified sample in format ready for vector DB"""
        logger.info(f"Exporting stratified sample to {output_file}...")
        
        # Create output format
        export_data = {
            "metadata": {
                "total_questions": len(self.stratified_sample),
                "sampling_strategy": "stratified_by_difficulty",
                "tiers": {
                    "low": "0-30% success rate",
                    "medium": "30-70% success rate",
                    "high": "70-100% success rate"
                }
            },
            "questions": []
        }
        
        # Group by tier for summary
        tier_counts = defaultdict(int)
        benchmark_counts = defaultdict(int)
        
        for qid, q in self.stratified_sample.items():
            tier_counts[q.get('difficulty_tier', 'unknown')] += 1
            benchmark_counts[q.get('source_benchmark', 'unknown')] += 1
            
            # Simplify for export
            export_q = {
                "question_id": qid,
                "source_benchmark": q['source_benchmark'],
                "domain": q['domain'],
                "question_text": q['question_text'],
                "correct_answer": q['correct_answer'],
                "choices": q.get('choices'),
                "success_rate": q.get('success_rate'),
                "difficulty_tier": q.get('difficulty_tier'),
                "difficulty_label": q.get('difficulty_label'),
                "num_models_tested": q.get('num_models', 0)
            }
            
            export_data["questions"].append(export_q)
        
        export_data["metadata"]["distribution"] = {
            "by_tier": dict(tier_counts),
            "by_benchmark": dict(benchmark_counts)
        }
        
        # Save
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"✓ Exported {len(export_data['questions'])} questions")
        logger.info(f"  By tier: {dict(tier_counts)}")
        logger.info(f"  By benchmark: {dict(benchmark_counts)}")
        
        return output_file
    
    def generate_summary_report(self) -> str:
        """Generate markdown summary report"""
        report = ["# Benchmark Data Post-Processing Report\n"]
        
        # Overall stats
        report.append("## Overall Statistics\n")
        report.append(f"- **Total questions collected**: {len(self.questions)}")
        report.append(f"- **Stratified sample size**: {len(self.stratified_sample)}\n")
        
        # Difficulty distribution
        report.append("## Difficulty Distribution\n")
        tier_counts = defaultdict(int)
        for q in self.stratified_sample.values():
            tier_counts[q.get('difficulty_tier', 'unknown')] += 1
        
        report.append("| Tier | Count | Percentage | Description |")
        report.append("|------|-------|------------|-------------|")
        total = len(self.stratified_sample)
        for tier in ['low', 'medium', 'high']:
            count = tier_counts[tier]
            pct = count / total * 100 if total > 0 else 0
            desc = {
                'low': 'Hard - model limitations (0-30% success)',
                'medium': 'Capability boundary (30-70% success)',
                'high': 'Within capability (70-100% success)'
            }[tier]
            report.append(f"| {tier.upper()} | {count} | {pct:.1f}% | {desc} |")
        
        report.append("\n")
        
        # Benchmark distribution
        report.append("## Source Benchmark Distribution\n")
        benchmark_counts = defaultdict(int)
        for q in self.stratified_sample.values():
            benchmark_counts[q.get('source_benchmark', 'unknown')] += 1
        
        report.append("| Benchmark | Count | Percentage |")
        report.append("|-----------|-------|------------|")
        for benchmark, count in sorted(benchmark_counts.items()):
            pct = count / total * 100 if total > 0 else 0
            report.append(f"| {benchmark} | {count} | {pct:.1f}% |")
        
        report.append("\n")
        
        # Success rate stats
        report.append("## Success Rate Statistics\n")
        success_rates = [q.get('success_rate', 0) for q in self.stratified_sample.values() if q.get('success_rate') is not None]
        
        if success_rates:
            import numpy as np
            report.append(f"- **Min**: {np.min(success_rates):.1%}")
            report.append(f"- **Max**: {np.max(success_rates):.1%}")
            report.append(f"- **Mean**: {np.mean(success_rates):.1%}")
            report.append(f"- **Median**: {np.median(success_rates):.1%}\n")
        
        # Next steps
        report.append("## Next Steps\n")
        report.append("1. Load stratified sample into vector database")
        report.append("2. Generate embeddings for all questions")
        report.append("3. Test difficulty assessment on real prompts")
        report.append("4. Validate accuracy against known hard/easy questions\n")
        
        return "\n".join(report)
    
    def save_summary_report(self, output_file: Path = Path("./data/benchmark_results/PROCESSING_REPORT.md")):
        """Save summary report"""
        report = self.generate_summary_report()
        
        with open(output_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Saved summary report to {output_file}")
        return output_file


def main():
    """Main execution"""
    logger.info("="*80)
    logger.info("Post-Processing Benchmark Data")
    logger.info("="*80)
    
    # Initialize
    processor = BenchmarkDataPostProcessor()
    
    # Load raw data
    processor.load_raw_data()
    
    # Analyze distribution
    processor.analyze_difficulty_distribution()
    
    # Create stratified sample
    # Target: 1000 questions with 30% low, 40% medium, 30% high
    processor.stratified_sampling(
        target_size=1000,
        low_pct=0.30,
        medium_pct=0.40,
        high_pct=0.30
    )
    
    # Export for vector DB
    export_path = processor.export_for_vector_db()
    
    # Generate summary report
    report_path = processor.save_summary_report()
    
    # Print summary
    print("\n" + processor.generate_summary_report())
    
    print("="*80)
    print("✓ Post-processing complete!")
    print("="*80)
    print(f"\nOutput files:")
    print(f"  - Stratified sample: {export_path}")
    print(f"  - Summary report: {report_path}")
    print(f"\nNext: Run vector DB builder with stratified sample")


if __name__ == "__main__":
    main()
