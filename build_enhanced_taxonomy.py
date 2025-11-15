#!/usr/bin/env python3
"""
Enhanced Taxonomy Builder
=========================

Combines all analysis layers into a comprehensive taxonomy:
- Category (14) → Subject (90) → Error Type → Specific Failures
- Enriched with CoT analysis and failure patterns

Final output: Complete nested JSON taxonomy for ToGMAL integration

Author: ToGMAL Project
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any
import statistics


class EnhancedTaxonomyBuilder:
    """Builds comprehensive multi-level taxonomy."""

    def __init__(self):
        """Initialize builder with all analysis data."""

        # Load enriched dataset
        with open("data/autonomous_benchmarks/autonomous_dataset_enriched.json") as f:
            self.dataset = json.load(f)

        # Load error taxonomy
        with open("data/error_taxonomy.json") as f:
            self.error_taxonomy = json.load(f)

        # Load error categorization
        with open("data/error_categorization.json") as f:
            self.error_categorization = json.load(f)

        # Load CoT analysis
        with open("data/cot_failure_analysis.json") as f:
            self.cot_analysis = json.load(f)

    def build_complete_taxonomy(self) -> Dict[str, Any]:
        """Build complete multi-level taxonomy."""

        print("\n" + "="*70)
        print("🏗️  BUILDING ENHANCED TAXONOMY")
        print("="*70)

        taxonomy = {
            "schema": {
                "description": "Complete error taxonomy with subject-level granularity",
                "levels": [
                    "1. Category (e.g., engineering, math) - 14 total",
                    "2. Subject (e.g., thermodynamics, algebra) - 90 total",
                    "3. Error Type (e.g., unit_conversion, multi_step) - 6 types",
                    "4. Specific Failures (individual questions with analysis)"
                ],
                "created": "2025-11-15",
                "total_questions": len(self.dataset['questions']),
                "total_models": len(self.dataset['metadata']['models']),
                "total_predictions": len(self.dataset['questions']) * len(self.dataset['metadata']['models'])
            },
            "categories": {}
        }

        # Group questions by category → subject
        by_category_subject = defaultdict(lambda: defaultdict(list))

        for q in self.dataset['questions']:
            cat = q.get('metadata', {}).get('category', 'unknown')
            subj = q.get('metadata', {}).get('subject', 'unknown')
            by_category_subject[cat][subj].append(q)

        print(f"\n📊 Processing {len(by_category_subject)} categories...")

        # Build taxonomy for each category
        for category, subjects in sorted(by_category_subject.items()):
            print(f"\n  Processing {category}...")

            taxonomy["categories"][category] = {
                "total_questions": sum(len(qs) for qs in subjects.values()),
                "total_subjects": len(subjects),
                "subjects": {}
            }

            # Process each subject
            for subject, questions in sorted(subjects.items()):
                # Calculate statistics
                success_rates = [q['success_rate'] for q in questions]
                avg_success = statistics.mean(success_rates) if success_rates else 0

                # Count difficulty tiers
                difficulty_tiers = {
                    "very_hard": len([q for q in questions if q['success_rate'] < 0.2]),
                    "hard": len([q for q in questions if 0.2 <= q['success_rate'] < 0.4]),
                    "medium": len([q for q in questions if 0.4 <= q['success_rate'] < 0.6]),
                    "easy": len([q for q in questions if q['success_rate'] >= 0.6])
                }

                # Find universal failures in this subject
                universal_failures = [q for q in questions if q['success_rate'] == 0.0]

                # Get CoT analysis for these failures
                failure_analysis = []
                for failure in universal_failures[:5]:  # Limit to 5 examples
                    # Find matching CoT analysis
                    q_text = failure['question'][:100]
                    matching_cot = None
                    for cot in self.cot_analysis['analyses']:
                        if cot['question'][:100] == q_text:
                            matching_cot = cot
                            break

                    if matching_cot:
                        failure_analysis.append({
                            "question": failure['question'][:150],
                            "success_rate": failure['success_rate'],
                            "complexity": {
                                "numeric_values": matching_cot['numeric_complexity'],
                                "unit_types": matching_cot['unit_count'],
                                "formula_indicators": matching_cot['formula_indicators']
                            },
                            "failure_mode": matching_cot['primary_failure_mode'],
                            "required_knowledge": matching_cot['required_knowledge'],
                            "difficulty": matching_cot['difficulty_estimate']
                        })

                # Build subject entry
                taxonomy["categories"][category]["subjects"][subject] = {
                    "total_questions": len(questions),
                    "avg_success_rate": round(avg_success, 3),
                    "difficulty_distribution": difficulty_tiers,
                    "universal_failures": len(universal_failures),
                    "failure_examples": failure_analysis,
                    "risk_assessment": self._assess_risk(avg_success, len(universal_failures), len(questions))
                }

        # Add aggregated insights
        taxonomy["global_insights"] = self._generate_global_insights()

        # Add recommendations
        taxonomy["recommendations"] = self._generate_recommendations()

        print("\n✓ Taxonomy building complete")

        return taxonomy

    def _assess_risk(self, avg_success: float, universal_failures: int, total_questions: int) -> Dict[str, Any]:
        """Assess risk level for a subject."""

        if avg_success >= 0.7:
            level = "LOW"
            color = "🟢"
        elif avg_success >= 0.4:
            level = "MEDIUM"
            color = "🟡"
        else:
            level = "HIGH"
            color = "🔴"

        return {
            "level": level,
            "color": color,
            "avg_success_rate": round(avg_success, 3),
            "universal_failure_rate": round(universal_failures / total_questions, 3) if total_questions > 0 else 0,
            "recommendation": self._get_recommendation(level)
        }

    def _get_recommendation(self, risk_level: str) -> str:
        """Get recommendation based on risk level."""
        recommendations = {
            "LOW": "Safe for general use with SOTA models",
            "MEDIUM": "Verify outputs, especially for complex questions. Consider using larger models.",
            "HIGH": "High failure rate. Use computational tools (Python, Wolfram Alpha) for calculations. Double-check all outputs."
        }
        return recommendations.get(risk_level, "Unknown risk level")

    def _generate_global_insights(self) -> Dict[str, Any]:
        """Generate global insights across all data."""

        return {
            "universal_failures": {
                "total": len([a for a in self.cot_analysis['analyses']]),
                "by_calculation_type": self.cot_analysis['insights']['by_calculation_type'],
                "primary_failure_modes": self.cot_analysis['insights']['by_failure_mode']
            },
            "complexity_averages": self.cot_analysis['insights']['complexity_stats'],
            "top_required_knowledge": dict(list(self.cot_analysis['insights']['top_required_knowledge'].items())[:10])
        }

    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate actionable recommendations for ToGMAL."""

        return [
            {
                "issue": "Unit Conversion Complexity",
                "finding": "148/150 universal failures involve multiple unit systems",
                "recommendation": "Detect questions with 3+ unit types. Flag as HIGH RISK. Recommend using computational tools.",
                "implementation": "Check for unit keywords: psi, atm, °F, °C, Btu, ft, in, lb, etc."
            },
            {
                "issue": "Subject-Specific Failure Rates",
                "finding": "90 subjects identified with varying difficulty (see taxonomy)",
                "recommendation": "Use subject-level risk assessment. Law: 28 failures. Engineering: 13 failures.",
                "implementation": "Map user query to subject using semantic similarity. Return subject risk level."
            },
            {
                "issue": "Multi-Step Calculation Failures",
                "finding": "26 failures require multi-step derivations",
                "recommendation": "Warn users about multi-step problems. Suggest breaking into smaller steps.",
                "implementation": "Detect keywords: 'calculate', 'then', 'using', 'given', 'find'"
            },
            {
                "issue": "Specialized Domain Formulas",
                "finding": "Engineering subjects show high failure rates (thermodynamics, heat transfer)",
                "recommendation": "For specialized engineering/science questions, recommend domain-specific tools or references.",
                "implementation": "Check if category=engineering AND subject in [Thermodynamics, HeatTransfer, etc.]"
            },
            {
                "issue": "Graduate-Level Complexity",
                "finding": "Most universal failures are EXTREME difficulty (graduate level)",
                "recommendation": "Set expectations: 'This question is graduate-level difficulty. Current models may struggle.'",
                "implementation": "Use complexity metrics: >15 complexity score = EXTREME"
            }
        ]

    def generate_report(self, output_file: Path = Path("data/enhanced_taxonomy.json")):
        """Generate and save enhanced taxonomy."""

        # Build taxonomy
        taxonomy = self.build_complete_taxonomy()

        # Save to file
        print(f"\n💾 Saving enhanced taxonomy to {output_file}...")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(taxonomy, f, indent=2)

        print(f"✓ Saved {output_file.stat().st_size / 1024 / 1024:.1f} MB")

        # Print summary
        self._print_summary(taxonomy)

        return taxonomy

    def _print_summary(self, taxonomy: Dict[str, Any]):
        """Print summary of enhanced taxonomy."""

        print("\n" + "="*70)
        print("📊 ENHANCED TAXONOMY SUMMARY")
        print("="*70)

        schema = taxonomy['schema']
        print(f"\n📐 Schema:")
        print(f"  • Total Questions: {schema['total_questions']:,}")
        print(f"  • Total Models: {schema['total_models']}")
        print(f"  • Total Predictions: {schema['total_predictions']:,}")

        print(f"\n🏗️  Taxonomy Levels:")
        for level in schema['levels']:
            print(f"  {level}")

        print(f"\n📚 By Category:")
        for cat, data in sorted(taxonomy['categories'].items(), key=lambda x: x[1]['total_questions'], reverse=True)[:10]:
            print(f"  • {cat:20s}: {data['total_subjects']:2d} subjects, {data['total_questions']:5d} questions")

        print(f"\n🔴 Highest Risk Subjects:")
        high_risk_subjects = []
        for cat, data in taxonomy['categories'].items():
            for subj, subj_data in data['subjects'].items():
                risk = subj_data['risk_assessment']
                if risk['level'] == 'HIGH':
                    high_risk_subjects.append((cat, subj, risk['avg_success_rate'], subj_data['universal_failures']))

        for cat, subj, success, failures in sorted(high_risk_subjects, key=lambda x: x[2])[:10]:
            print(f"  🔴 {cat}/{subj:30s}: {success*100:5.1f}% success, {failures} universal failures")

        print(f"\n💡 Top Recommendations:")
        for i, rec in enumerate(taxonomy['recommendations'][:3], 1):
            print(f"\n  {i}. {rec['issue']}")
            print(f"     Finding: {rec['finding']}")
            print(f"     → {rec['recommendation']}")

        print("\n" + "="*70)


if __name__ == '__main__':
    builder = EnhancedTaxonomyBuilder()
    taxonomy = builder.generate_report()
