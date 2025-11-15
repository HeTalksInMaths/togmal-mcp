#!/usr/bin/env python3
"""
Error Taxonomy Analyzer
=======================

Analyzes why SOTA models fail on specific questions and builds a hierarchical
taxonomy of conceptual errors to guide ToGMAL risk assessment.

Approach:
1. Extract questions where SOTA models fail
2. Cluster by category/difficulty/failure patterns
3. Use LLM to analyze failure modes
4. Build nested taxonomy: Category → Subject → Error Type

Author: ToGMAL Project
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import statistics


@dataclass
class QuestionFailure:
    """Represents a question where models failed."""
    question_id: int
    question: str
    category: str
    success_rate: float
    sota_failures: List[str]  # Which SOTA models failed
    all_model_scores: Dict[str, bool]
    metadata: Dict[str, Any]


@dataclass
class ErrorPattern:
    """Represents an identified error pattern."""
    category: str
    subject: str
    error_type: str
    description: str
    example_questions: List[str]
    affected_models: List[str]
    frequency: int
    avg_success_rate: float


class ErrorTaxonomyAnalyzer:
    """Analyzes model failures and builds error taxonomy."""

    # Define SOTA model threshold (top performers)
    SOTA_ACCURACY_THRESHOLD = 0.70  # Models with >70% overall accuracy

    # Error type categories (to be populated by analysis)
    ERROR_TAXONOMY = {
        "knowledge_gaps": {
            "description": "Missing factual knowledge",
            "subtypes": {
                "domain_specific": "Specialized domain knowledge not in training",
                "temporal": "Recent events or updated information",
                "niche_facts": "Obscure facts or edge cases"
            }
        },
        "reasoning_failures": {
            "description": "Logical or mathematical reasoning errors",
            "subtypes": {
                "multi_step": "Failure in multi-step reasoning chains",
                "mathematical": "Calculation or formula application errors",
                "causal": "Incorrect causal inference",
                "counterfactual": "Difficulty with hypothetical scenarios"
            }
        },
        "comprehension_issues": {
            "description": "Misunderstanding question or context",
            "subtypes": {
                "ambiguity": "Confusion from ambiguous wording",
                "negation": "Mishandling of negations (not, except, etc.)",
                "complex_syntax": "Difficulty parsing complex sentence structure",
                "implicit_info": "Missing implicit information"
            }
        },
        "pattern_matching_failures": {
            "description": "Superficial pattern matching instead of understanding",
            "subtypes": {
                "keyword_bias": "Biased by misleading keywords",
                "format_confusion": "Confused by unusual question format",
                "option_artifacts": "Misled by answer choice patterns"
            }
        },
        "domain_specific_errors": {
            "description": "Category-specific failure patterns",
            "subtypes": {}  # Will be populated per category
        }
    }

    def __init__(
        self,
        dataset_file: Path = Path("data/autonomous_benchmarks/autonomous_dataset.json")
    ):
        """Initialize analyzer."""
        self.dataset_file = dataset_file

        # Load dataset
        with open(dataset_file) as f:
            self.dataset = json.load(f)

        # Identify SOTA models
        self.sota_models = self._identify_sota_models()
        print(f"Identified {len(self.sota_models)} SOTA models (>{self.SOTA_ACCURACY_THRESHOLD*100}% accuracy)")
        for model, acc in sorted(self.sota_models.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  • {model:50s}: {acc*100:.1f}%")

    def _identify_sota_models(self) -> Dict[str, float]:
        """Identify SOTA models based on overall accuracy."""
        model_accuracies = {}

        for model_info in self.dataset['metadata']['models']:
            model_name = model_info['name']
            accuracy = model_info.get('accuracy', 0.0)
            if accuracy >= self.SOTA_ACCURACY_THRESHOLD:
                model_accuracies[model_name] = accuracy

        return model_accuracies

    def extract_sota_failures(self) -> List[QuestionFailure]:
        """Extract questions where SOTA models failed."""
        failures = []

        for i, q in enumerate(self.dataset['questions']):
            # Check which SOTA models failed
            sota_failures = []
            for model_name in self.sota_models.keys():
                # Model might be in different formats in the data
                model_score = q['model_scores'].get(model_name)
                if model_score is None:
                    # Try variations (with/without suffixes)
                    for key in q['model_scores'].keys():
                        if model_name in key:
                            model_score = q['model_scores'][key]
                            break

                if model_score is False:
                    sota_failures.append(model_name)

            # If at least one SOTA model failed, record it
            if sota_failures:
                failure = QuestionFailure(
                    question_id=i,
                    question=q['question'],
                    category=q.get('metadata', {}).get('category', 'unknown'),
                    success_rate=q['success_rate'],
                    sota_failures=sota_failures,
                    all_model_scores=q['model_scores'],
                    metadata=q.get('metadata', {})
                )
                failures.append(failure)

        return failures

    def analyze_by_category(self, failures: List[QuestionFailure]) -> Dict[str, Any]:
        """Analyze failure patterns by category."""
        by_category = defaultdict(list)

        for failure in failures:
            by_category[failure.category].append(failure)

        analysis = {}
        for cat, cat_failures in by_category.items():
            analysis[cat] = {
                "total_failures": len(cat_failures),
                "avg_success_rate": statistics.mean(f.success_rate for f in cat_failures),
                "sota_failure_rate": len([f for f in cat_failures if len(f.sota_failures) > len(self.sota_models) / 2]) / len(cat_failures),
                "hardest_questions": sorted(cat_failures, key=lambda x: x.success_rate)[:5]
            }

        return analysis

    def analyze_by_difficulty(self, failures: List[QuestionFailure]) -> Dict[str, Any]:
        """Analyze failure patterns by difficulty tier."""
        tiers = {
            "very_hard": [],  # <20% success
            "hard": [],       # 20-40% success
            "medium": [],     # 40-60% success
            "easy": [],       # >60% success
        }

        for failure in failures:
            if failure.success_rate < 0.20:
                tiers["very_hard"].append(failure)
            elif failure.success_rate < 0.40:
                tiers["hard"].append(failure)
            elif failure.success_rate < 0.60:
                tiers["medium"].append(failure)
            else:
                tiers["easy"].append(failure)

        return {
            tier: {
                "count": len(failures),
                "avg_success_rate": statistics.mean(f.success_rate for f in failures) if failures else 0,
                "examples": [f.question[:100] for f in failures[:3]]
            }
            for tier, failures in tiers.items()
        }

    def identify_common_failures(self, failures: List[QuestionFailure], top_n: int = 20) -> List[Tuple[str, int]]:
        """Identify questions that failed across most SOTA models."""
        failure_counts = {}

        for failure in failures:
            num_sota_failed = len(failure.sota_failures)
            failure_counts[failure.question_id] = (
                num_sota_failed,
                failure.question,
                failure.category,
                failure.success_rate
            )

        # Sort by number of SOTA failures
        sorted_failures = sorted(
            failure_counts.items(),
            key=lambda x: x[1][0],
            reverse=True
        )

        return sorted_failures[:top_n]

    def build_error_taxonomy(self, failures: List[QuestionFailure]) -> Dict[str, Any]:
        """Build hierarchical error taxonomy."""
        taxonomy = {
            "metadata": {
                "total_questions": len(self.dataset['questions']),
                "total_failures": len(failures),
                "sota_models": list(self.sota_models.keys()),
                "failure_rate": len(failures) / len(self.dataset['questions'])
            },
            "by_category": {},
            "by_error_type": {},
            "common_patterns": []
        }

        # Analyze by category
        cat_analysis = self.analyze_by_category(failures)
        for cat, data in cat_analysis.items():
            taxonomy["by_category"][cat] = {
                "total_failures": data["total_failures"],
                "avg_success_rate": round(data["avg_success_rate"], 3),
                "sota_failure_rate": round(data["sota_failure_rate"], 3),
                "hardest_examples": [
                    {
                        "question": f.question[:150],
                        "success_rate": round(f.success_rate, 3),
                        "sota_failures": f.sota_failures
                    }
                    for f in data["hardest_questions"]
                ]
            }

        # Analyze by difficulty
        diff_analysis = self.analyze_by_difficulty(failures)
        taxonomy["by_difficulty"] = diff_analysis

        # Identify common failures
        common = self.identify_common_failures(failures, top_n=20)
        taxonomy["universal_failures"] = [
            {
                "question_id": q_id,
                "sota_failed": count,
                "total_sota": len(self.sota_models),
                "question": question[:150],
                "category": cat,
                "success_rate": round(sr, 3)
            }
            for q_id, (count, question, cat, sr) in common
        ]

        return taxonomy

    def generate_report(self, output_file: Path = Path("data/error_taxonomy.json")):
        """Generate comprehensive error taxonomy report."""
        print("\n" + "="*70)
        print("🔍 ANALYZING MODEL FAILURES")
        print("="*70)

        # Extract failures
        print("\n📊 Extracting SOTA model failures...")
        failures = self.extract_sota_failures()
        print(f"Found {len(failures):,} questions where at least one SOTA model failed")
        print(f"({len(failures)/len(self.dataset['questions'])*100:.1f}% of all questions)")

        # Build taxonomy
        print("\n🏗️  Building error taxonomy...")
        taxonomy = self.build_error_taxonomy(failures)

        # Save to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(taxonomy, f, indent=2)

        print(f"\n💾 Error taxonomy saved to: {output_file}")

        # Print summary
        print("\n" + "="*70)
        print("📈 FAILURE ANALYSIS SUMMARY")
        print("="*70)

        print("\n🎯 By Category:")
        for cat in sorted(taxonomy["by_category"].keys(),
                         key=lambda x: taxonomy["by_category"][x]["total_failures"],
                         reverse=True)[:10]:
            data = taxonomy["by_category"][cat]
            print(f"  • {cat:20s}: {data['total_failures']:5d} failures "
                  f"(avg success: {data['avg_success_rate']*100:5.1f}%)")

        print("\n🎚️  By Difficulty:")
        for tier, data in taxonomy["by_difficulty"].items():
            if data["count"] > 0:
                print(f"  • {tier:12s}: {data['count']:5d} failures "
                      f"(avg success: {data['avg_success_rate']*100:5.1f}%)")

        print("\n🔴 Universal Failures (All SOTA models struggled):")
        for item in taxonomy["universal_failures"][:10]:
            print(f"\n  Question: {item['question']}...")
            print(f"  Category: {item['category']}")
            print(f"  SOTA failures: {item['sota_failed']}/{item['total_sota']}")
            print(f"  Overall success: {item['success_rate']*100:.1f}%")

        print("\n" + "="*70)

        return taxonomy


if __name__ == '__main__':
    analyzer = ErrorTaxonomyAnalyzer()
    taxonomy = analyzer.generate_report()
