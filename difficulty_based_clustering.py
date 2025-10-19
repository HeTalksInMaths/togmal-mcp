#!/usr/bin/env python3
"""
Difficulty-Based Benchmark Clustering
======================================

Instead of clustering by domain (all math together, all medicine together),
this clusters by difficulty - what's actually hard vs easy for LLMs.

Goal: Identify the "LLM capability boundary" - what's possible vs impossible
regardless of domain.

Key Innovation:
- Cluster questions from MMLU, GPQA, MATH, GSM8K, etc. by LLM success rate
- Create clusters: "Too Easy" (>90% correct), "Moderate" (50-90%), 
  "Hard" (10-50%), "Nearly Impossible" (<10%)
- Analyze what makes questions hard across domains
"""

import json
import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkQuestion:
    """Represents a single question with performance data"""
    question_id: str
    source_benchmark: str  # MMLU, GPQA, MATH, etc.
    domain: str  # math, science, law, medicine, etc.
    question_text: str
    correct_answer: str
    difficulty_label: str = None  # Easy, Medium, Hard from original benchmark
    
    # Performance metrics across different LLM tiers
    gpt4_correct: bool = None
    claude_correct: bool = None
    llama_70b_correct: bool = None
    avg_success_rate: float = None  # Average across multiple models
    
    # Computed difficulty score
    computed_difficulty: float = None


@dataclass
class DifficultyCluster:
    """A cluster of questions with similar difficulty"""
    cluster_id: int
    difficulty_range: str  # "Too Easy", "Moderate", "Hard", "Nearly Impossible"
    questions: List[BenchmarkQuestion]
    avg_success_rate: float
    domain_distribution: Dict[str, int]  # Count of questions per domain
    common_patterns: List[str]  # What makes these hard?


class DifficultyBasedClusterer:
    """
    Clusters benchmark questions by difficulty rather than domain.
    
    This is the core innovation - we want to know which questions are hard
    regardless of whether they're about math, law, or medicine.
    """
    
    def __init__(self, output_dir: Path = Path("./difficulty_clusters")):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        self.questions: List[BenchmarkQuestion] = []
        self.clusters: List[DifficultyCluster] = []
        
    def load_huggingface_benchmark_results(self) -> List[BenchmarkQuestion]:
        """
        Load benchmark results from HuggingFace datasets with per-question performance.
        
        Key datasets to use:
        1. open-llm-leaderboard/details_* - Individual model results on benchmarks
        2. MMLU, GPQA, MATH, GSM8K datasets with answer keys
        3. Per-question evaluation results from multiple models
        
        Returns synthetic data for now - replace with actual HF dataset loading.
        """
        logger.info("Loading benchmark results from HuggingFace...")
        
        # TODO: Replace with actual HuggingFace dataset loading
        # from datasets import load_dataset
        # mmlu_data = load_dataset("cais/mmlu", "all")
        # results = load_dataset("open-llm-leaderboard/details_meta-llama__Meta-Llama-3-70B-Instruct", 
        #                        "harness_mmlu_pro_5")
        
        # For now, create synthetic data demonstrating the concept
        synthetic_questions = self._generate_synthetic_questions()
        
        logger.info(f"Loaded {len(synthetic_questions)} questions from benchmarks")
        return synthetic_questions
    
    def _generate_synthetic_questions(self) -> List[BenchmarkQuestion]:
        """Generate synthetic benchmark data to demonstrate the concept"""
        
        questions = []
        
        # Example 1: Easy math question (high success rate across domains)
        questions.append(BenchmarkQuestion(
            question_id="math_easy_001",
            source_benchmark="GSM8K",
            domain="mathematics",
            question_text="If John has 5 apples and buys 3 more, how many does he have?",
            correct_answer="8",
            difficulty_label="Easy",
            gpt4_correct=True,
            claude_correct=True,
            llama_70b_correct=True,
            avg_success_rate=0.98
        ))
        
        # Example 2: Hard medical reasoning (low success across all models)
        questions.append(BenchmarkQuestion(
            question_id="med_hard_001",
            source_benchmark="MedQA",
            domain="medicine",
            question_text="A 45-year-old presents with episodic vertigo, tinnitus, and fluctuating hearing loss. What's the most likely diagnosis considering the combination of cochlear and vestibular symptoms?",
            correct_answer="Meniere's disease",
            difficulty_label="Hard",
            gpt4_correct=True,
            claude_correct=False,
            llama_70b_correct=False,
            avg_success_rate=0.23
        ))
        
        # Example 3: Hard math reasoning (similar difficulty to hard medicine!)
        questions.append(BenchmarkQuestion(
            question_id="math_hard_001",
            source_benchmark="MATH",
            domain="mathematics",
            question_text="Find the number of ordered triples (a,b,c) of positive integers satisfying a*b*c = 1000",
            correct_answer="60",
            difficulty_label="Hard",
            gpt4_correct=True,
            claude_correct=False,
            llama_70b_correct=False,
            avg_success_rate=0.19
        ))
        
        # Example 4: Easy law question (but still high success)
        questions.append(BenchmarkQuestion(
            question_id="law_easy_001",
            source_benchmark="LegalBench",
            domain="law",
            question_text="Is evidence obtained through an illegal search admissible in court?",
            correct_answer="No, generally excluded under exclusionary rule",
            difficulty_label="Easy",
            gpt4_correct=True,
            claude_correct=True,
            llama_70b_correct=True,
            avg_success_rate=0.94
        ))
        
        # Example 5: Very hard physics (nearly impossible)
        questions.append(BenchmarkQuestion(
            question_id="physics_vhard_001",
            source_benchmark="GPQA",
            domain="physics",
            question_text="Calculate the quantum correction to the classical partition function for a 3D harmonic oscillator at temperature T, including anharmonic terms to second order.",
            correct_answer="[Complex derivation]",
            difficulty_label="Expert",
            gpt4_correct=False,
            claude_correct=False,
            llama_70b_correct=False,
            avg_success_rate=0.03
        ))
        
        # Add more examples across domains with varying difficulty
        # The key insight: hard questions cluster together regardless of domain
        
        return questions
    
    def compute_difficulty_scores(self, questions: List[BenchmarkQuestion]) -> List[BenchmarkQuestion]:
        """
        Compute difficulty score for each question based on LLM performance.
        
        Difficulty = 1 - avg_success_rate
        Higher score = harder question
        """
        logger.info("Computing difficulty scores...")
        
        for q in questions:
            if q.avg_success_rate is not None:
                q.computed_difficulty = 1.0 - q.avg_success_rate
            else:
                # If no performance data, try to infer from individual model results
                results = [q.gpt4_correct, q.claude_correct, q.llama_70b_correct]
                results = [r for r in results if r is not None]
                if results:
                    success_rate = sum(results) / len(results)
                    q.avg_success_rate = success_rate
                    q.computed_difficulty = 1.0 - success_rate
        
        return questions
    
    def cluster_by_difficulty(self, questions: List[BenchmarkQuestion]) -> List[DifficultyCluster]:
        """
        Cluster questions by difficulty rather than domain.
        
        Creates 4 difficulty tiers:
        1. Too Easy (>90% success) - LLMs have mastered
        2. Moderate (50-90% success) - Within capability with effort  
        3. Hard (10-50% success) - At the capability boundary
        4. Nearly Impossible (<10% success) - Beyond current LLM capability
        """
        logger.info("Clustering questions by difficulty...")
        
        # Define difficulty ranges
        difficulty_ranges = [
            (0.0, 0.1, "Nearly Impossible"),
            (0.1, 0.5, "Hard"),
            (0.5, 0.9, "Moderate"),
            (0.9, 1.0, "Too Easy")
        ]
        
        clusters = []
        
        for cluster_id, (min_rate, max_rate, label) in enumerate(difficulty_ranges):
            # Filter questions in this difficulty range
            cluster_questions = [
                q for q in questions
                if q.avg_success_rate is not None and min_rate <= q.avg_success_rate < max_rate
            ]
            
            if not cluster_questions:
                continue
            
            # Compute domain distribution
            domain_dist = defaultdict(int)
            for q in cluster_questions:
                domain_dist[q.domain] += 1
            
            # Compute average success rate for cluster
            avg_success = np.mean([q.avg_success_rate for q in cluster_questions])
            
            # Identify common patterns (simplified for now)
            patterns = self._identify_difficulty_patterns(cluster_questions)
            
            cluster = DifficultyCluster(
                cluster_id=cluster_id,
                difficulty_range=label,
                questions=cluster_questions,
                avg_success_rate=avg_success,
                domain_distribution=dict(domain_dist),
                common_patterns=patterns
            )
            
            clusters.append(cluster)
        
        logger.info(f"Created {len(clusters)} difficulty-based clusters")
        return clusters
    
    def _identify_difficulty_patterns(self, questions: List[BenchmarkQuestion]) -> List[str]:
        """
        Analyze what makes questions in this cluster hard.
        
        This is where the magic happens - finding commonalities in hard questions
        across different domains.
        """
        patterns = []
        
        # Check for multi-step reasoning
        multi_step_keywords = ["calculate", "derive", "prove", "step", "first", "then"]
        multi_step_count = sum(
            1 for q in questions 
            if any(kw in q.question_text.lower() for kw in multi_step_keywords)
        )
        if multi_step_count / len(questions) > 0.3:
            patterns.append("Requires multi-step reasoning")
        
        # Check for domain-specific jargon
        has_technical_terms = sum(
            1 for q in questions
            if any(char.isupper() for char in q.question_text[1:])  # Capitalized technical terms
        )
        if has_technical_terms / len(questions) > 0.4:
            patterns.append("Contains specialized terminology")
        
        # Check for numerical/symbolic computation
        has_numbers = sum(1 for q in questions if any(c.isdigit() for c in q.question_text))
        if has_numbers / len(questions) > 0.5:
            patterns.append("Involves numerical computation")
        
        # Add more pattern detection logic here
        
        return patterns
    
    def analyze_capability_boundary(self, clusters: List[DifficultyCluster]) -> Dict[str, Any]:
        """
        Analyze the LLM capability boundary - what separates possible from impossible.
        
        This answers: "What makes a question hard for LLMs across all domains?"
        """
        logger.info("Analyzing LLM capability boundary...")
        
        analysis = {
            "total_questions": sum(len(c.questions) for c in clusters),
            "cluster_summary": [],
            "cross_domain_insights": {},
            "capability_boundary": {}
        }
        
        for cluster in clusters:
            cluster_info = {
                "difficulty_range": cluster.difficulty_range,
                "num_questions": len(cluster.questions),
                "avg_success_rate": cluster.avg_success_rate,
                "domains": cluster.domain_distribution,
                "patterns": cluster.common_patterns
            }
            analysis["cluster_summary"].append(cluster_info)
        
        # Find hard questions across different domains
        hard_clusters = [c for c in clusters if c.difficulty_range in ["Hard", "Nearly Impossible"]]
        if hard_clusters:
            all_hard_questions = []
            for c in hard_clusters:
                all_hard_questions.extend(c.questions)
            
            # Group hard questions by domain
            hard_by_domain = defaultdict(list)
            for q in all_hard_questions:
                hard_by_domain[q.domain].append(q)
            
            analysis["cross_domain_insights"] = {
                "hard_domains": {
                    domain: len(questions) 
                    for domain, questions in hard_by_domain.items()
                },
                "common_difficulty_factors": self._identify_difficulty_patterns(all_hard_questions)
            }
        
        # Define capability boundary
        moderate_cluster = next((c for c in clusters if c.difficulty_range == "Moderate"), None)
        hard_cluster = next((c for c in clusters if c.difficulty_range == "Hard"), None)
        
        if moderate_cluster and hard_cluster:
            analysis["capability_boundary"] = {
                "boundary_success_rate": 0.5,  # 50% success marks the boundary
                "above_boundary": {
                    "count": len(moderate_cluster.questions),
                    "characteristics": moderate_cluster.common_patterns
                },
                "below_boundary": {
                    "count": len(hard_cluster.questions),
                    "characteristics": hard_cluster.common_patterns
                }
            }
        
        return analysis
    
    def save_results(self, clusters: List[DifficultyCluster], analysis: Dict[str, Any]):
        """Save clustering results and analysis"""
        
        # Save clusters
        clusters_data = []
        for cluster in clusters:
            cluster_dict = {
                "cluster_id": cluster.cluster_id,
                "difficulty_range": cluster.difficulty_range,
                "avg_success_rate": cluster.avg_success_rate,
                "num_questions": len(cluster.questions),
                "domain_distribution": cluster.domain_distribution,
                "common_patterns": cluster.common_patterns,
                "example_questions": [
                    {
                        "id": q.question_id,
                        "source": q.source_benchmark,
                        "domain": q.domain,
                        "question": q.question_text[:100] + "..." if len(q.question_text) > 100 else q.question_text,
                        "success_rate": q.avg_success_rate
                    }
                    for q in cluster.questions[:5]  # Include up to 5 examples
                ]
            }
            clusters_data.append(cluster_dict)
        
        clusters_file = self.output_dir / "difficulty_clusters.json"
        with open(clusters_file, 'w') as f:
            json.dump(clusters_data, f, indent=2)
        logger.info(f"Saved clusters to {clusters_file}")
        
        # Save analysis
        analysis_file = self.output_dir / "capability_boundary_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Saved analysis to {analysis_file}")
        
        # Generate taxonomy for ToGMAL
        taxonomy = self._generate_togmal_taxonomy(clusters)
        taxonomy_file = self.output_dir / "togmal_difficulty_taxonomy.json"
        with open(taxonomy_file, 'w') as f:
            json.dump(taxonomy, f, indent=2)
        logger.info(f"Saved ToGMAL taxonomy to {taxonomy_file}")
    
    def _generate_togmal_taxonomy(self, clusters: List[DifficultyCluster]) -> Dict[str, Any]:
        """
        Generate a taxonomy for ToGMAL based on difficulty clusters.
        
        This maps difficulty patterns to limitation categories.
        """
        taxonomy = {
            "version": "1.0",
            "source": "difficulty_based_clustering",
            "limitation_categories": []
        }
        
        # Create limitations for "Hard" and "Nearly Impossible" clusters
        hard_clusters = [c for c in clusters if c.difficulty_range in ["Hard", "Nearly Impossible"]]
        
        for cluster in hard_clusters:
            category = {
                "id": f"difficulty_{cluster.cluster_id}",
                "name": f"{cluster.difficulty_range} Questions",
                "severity": "high" if cluster.difficulty_range == "Nearly Impossible" else "medium",
                "success_rate_range": f"{cluster.avg_success_rate:.1%}",
                "domains_affected": list(cluster.domain_distribution.keys()),
                "patterns": cluster.common_patterns,
                "example_heuristics": [
                    f"Question requires {pattern.lower()}" 
                    for pattern in cluster.common_patterns
                ]
            }
            taxonomy["limitation_categories"].append(category)
        
        return taxonomy
    
    def run_pipeline(self):
        """Run the complete difficulty-based clustering pipeline"""
        
        logger.info("="*80)
        logger.info("Difficulty-Based Benchmark Clustering Pipeline")
        logger.info("="*80)
        
        # Step 1: Load benchmark results
        self.questions = self.load_huggingface_benchmark_results()
        
        # Step 2: Compute difficulty scores
        self.questions = self.compute_difficulty_scores(self.questions)
        
        # Step 3: Cluster by difficulty (not domain!)
        self.clusters = self.cluster_by_difficulty(self.questions)
        
        # Step 4: Analyze capability boundary
        analysis = self.analyze_capability_boundary(self.clusters)
        
        # Step 5: Save results
        self.save_results(self.clusters, analysis)
        
        # Print summary
        self._print_summary(analysis)
        
        logger.info("="*80)
        logger.info("Pipeline complete!")
        logger.info("="*80)
    
    def _print_summary(self, analysis: Dict[str, Any]):
        """Print a human-readable summary"""
        
        print("\n" + "="*80)
        print("DIFFICULTY-BASED CLUSTERING RESULTS")
        print("="*80)
        
        print(f"\nTotal questions analyzed: {analysis['total_questions']}")
        
        print("\nDifficulty Clusters:")
        for cluster_info in analysis['cluster_summary']:
            print(f"\n  {cluster_info['difficulty_range']}:")
            print(f"    Questions: {cluster_info['num_questions']}")
            print(f"    Avg Success Rate: {cluster_info['avg_success_rate']:.1%}")
            print(f"    Domains: {', '.join(f'{k}({v})' for k, v in cluster_info['domains'].items())}")
            if cluster_info['patterns']:
                print(f"    Patterns: {', '.join(cluster_info['patterns'])}")
        
        if analysis.get("cross_domain_insights"):
            print("\nCross-Domain Insights:")
            hard_domains = analysis["cross_domain_insights"]["hard_domains"]
            print(f"  Hard questions by domain: {hard_domains}")
            print(f"  Common difficulty factors:")
            for factor in analysis["cross_domain_insights"]["common_difficulty_factors"]:
                print(f"    - {factor}")
        
        if analysis.get("capability_boundary"):
            boundary = analysis["capability_boundary"]
            print(f"\nLLM Capability Boundary (at ~{boundary['boundary_success_rate']:.0%} success rate):")
            print(f"  Above boundary: {boundary['above_boundary']['count']} questions")
            print(f"  Below boundary: {boundary['below_boundary']['count']} questions")
        
        print("\n" + "="*80)


def main():
    """Main entry point"""
    
    clusterer = DifficultyBasedClusterer(output_dir=Path("/home/claude/difficulty_clusters"))
    clusterer.run_pipeline()
    
    print("\nNext steps:")
    print("1. Replace synthetic data with actual HuggingFace benchmark results")
    print("2. Integrate with ToGMAL MCP server to use difficulty taxonomy")
    print("3. Use clusters to generate adversarial questions in Aqumen")
    print("4. Track changes in capability boundary over time")


if __name__ == "__main__":
    main()
