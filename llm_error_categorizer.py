#!/usr/bin/env python3
"""
LLM Error Categorizer
=====================

Uses LLMs to analyze why models fail on specific questions and
build a hierarchical taxonomy of conceptual errors.

Taxonomy Structure:
Category (e.g., "engineering")
  └── Subject (e.g., "thermodynamics")
      └── Error Type (e.g., "multi-step calculation", "formula application")
          └── Root Cause (e.g., "missing intermediate steps", "wrong equation")

Author: ToGMAL Project
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
import statistics


class LLMErrorCategorizer:
    """Categorizes model failures using pattern analysis."""

    # Error type taxonomy (hierarchical)
    ERROR_TYPES = {
        "calculation": {
            "description": "Mathematical or numerical computation errors",
            "indicators": [
                "calculate", "compute", "find the value", "what is",
                "diameter", "temperature", "velocity", "coefficient"
            ]
        },
        "multi_step_reasoning": {
            "description": "Requires multiple steps or chained reasoning",
            "indicators": [
                "given", "calculate", "then", "using",
                "equilibrium constant", "modulus", "carrying"
            ]
        },
        "domain_knowledge": {
            "description": "Requires specialized domain knowledge",
            "indicators": [
                "thermodynamics", "equilibrium", "viscosity",
                "specific heat", "enthalpy", "entropy"
            ]
        },
        "formula_application": {
            "description": "Requires knowing and applying specific formulas",
            "indicators": [
                "formula", "equation", "law", "principle",
                "modulus of elasticity", "coefficient", "constant"
            ]
        },
        "unit_conversion": {
            "description": "Requires converting between units or scales",
            "indicators": [
                "psi", "atm", "°F", "°C", "Btu", "ft", "in",
                "lb", "mol", "cfs"
            ]
        },
        "complex_constraints": {
            "description": "Multiple constraints or boundary conditions",
            "indicators": [
                "subjected to", "given that", "with",
                "initial", "entrance", "radial"
            ]
        }
    }

    def __init__(self):
        """Initialize categorizer."""
        # Load error taxonomy
        taxonomy_file = Path("data/error_taxonomy.json")
        with open(taxonomy_file) as f:
            self.taxonomy = json.load(f)

    def categorize_question(self, question: str, category: str) -> Dict[str, Any]:
        """Categorize a question's error type based on content analysis."""
        question_lower = question.lower()

        # Score each error type
        error_scores = {}
        for error_type, info in self.ERROR_TYPES.items():
            score = sum(
                1 for indicator in info["indicators"]
                if indicator.lower() in question_lower
            )
            if score > 0:
                error_scores[error_type] = score

        # Get primary and secondary error types
        sorted_errors = sorted(error_scores.items(), key=lambda x: x[1], reverse=True)

        primary_error = sorted_errors[0][0] if sorted_errors else "unknown"
        secondary_errors = [et for et, _ in sorted_errors[1:3]] if len(sorted_errors) > 1 else []

        return {
            "primary_error_type": primary_error,
            "secondary_error_types": secondary_errors,
            "error_scores": error_scores,
            "complexity_indicators": len(error_scores)
        }

    def analyze_universal_failures(self) -> Dict[str, Any]:
        """Analyze questions where ALL models failed."""
        universal = self.taxonomy["universal_failures"]

        categorized = defaultdict(lambda: defaultdict(list))

        for failure in universal:
            cat = failure["category"]
            analysis = self.categorize_question(
                failure["question"],
                cat
            )

            error_type = analysis["primary_error_type"]
            categorized[cat][error_type].append({
                "question": failure["question"],
                "success_rate": failure["success_rate"],
                "analysis": analysis
            })

        return dict(categorized)

    def build_hierarchical_taxonomy(self) -> Dict[str, Any]:
        """Build hierarchical error taxonomy: Category → Subject → Error Type."""
        taxonomy = {
            "schema": {
                "description": "Hierarchical taxonomy of model errors",
                "levels": [
                    "category (e.g., engineering, math)",
                    "error_type (e.g., calculation, multi_step)",
                    "question_examples"
                ]
            },
            "categories": {}
        }

        # Analyze universal failures
        universal_categorized = self.analyze_universal_failures()

        for category, error_types in universal_categorized.items():
            taxonomy["categories"][category] = {
                "total_universal_failures": sum(len(qs) for qs in error_types.values()),
                "error_types": {}
            }

            for error_type, questions in error_types.items():
                taxonomy["categories"][category]["error_types"][error_type] = {
                    "description": self.ERROR_TYPES.get(error_type, {}).get("description", "Unknown error type"),
                    "count": len(questions),
                    "avg_complexity": statistics.mean(
                        q["analysis"]["complexity_indicators"] for q in questions
                    ),
                    "examples": [
                        {
                            "question": q["question"][:200],
                            "success_rate": q["success_rate"],
                            "secondary_errors": q["analysis"]["secondary_error_types"]
                        }
                        for q in questions[:5]
                    ]
                }

        return taxonomy

    def generate_insights(self) -> Dict[str, Any]:
        """Generate high-level insights from error patterns."""
        hierarchical = self.build_hierarchical_taxonomy()

        insights = {
            "top_level_summary": {},
            "critical_patterns": [],
            "recommendations": []
        }

        # Analyze by category
        for cat, data in hierarchical["categories"].items():
            total = data["total_universal_failures"]
            error_types = data["error_types"]

            insights["top_level_summary"][cat] = {
                "universal_failures": total,
                "primary_error_types": sorted(
                    error_types.keys(),
                    key=lambda x: error_types[x]["count"],
                    reverse=True
                )[:3]
            }

        # Identify critical patterns
        all_error_types = defaultdict(int)
        for cat, data in hierarchical["categories"].items():
            for error_type, info in data["error_types"].items():
                all_error_types[error_type] += info["count"]

        for error_type, count in sorted(all_error_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            insights["critical_patterns"].append({
                "error_type": error_type,
                "frequency": count,
                "description": self.ERROR_TYPES.get(error_type, {}).get("description", "Unknown")
            })

        # Generate recommendations
        if "calculation" in all_error_types and all_error_types["calculation"] > 10:
            insights["recommendations"].append({
                "issue": "High calculation error rate",
                "recommendation": "Models struggle with multi-step numerical calculations. Consider warning users about numerical precision requirements."
            })

        if "formula_application" in all_error_types:
            insights["recommendations"].append({
                "issue": "Formula application failures",
                "recommendation": "Models may not have domain-specific formulas memorized. Suggest providing formula references for complex engineering problems."
            })

        if "multi_step_reasoning" in all_error_types:
            insights["recommendations"].append({
                "issue": "Multi-step reasoning failures",
                "recommendation": "Break complex problems into smaller steps. ToGMAL should recommend step-by-step approaches for multi-part questions."
            })

        return insights

    def generate_report(self, output_file: Path = Path("data/error_categorization.json")):
        """Generate comprehensive error categorization report."""
        print("\n" + "="*70)
        print("🔬 LLM ERROR CATEGORIZATION ANALYSIS")
        print("="*70)

        # Build hierarchical taxonomy
        print("\n🏗️  Building hierarchical error taxonomy...")
        hierarchical = self.build_hierarchical_taxonomy()

        # Generate insights
        print("💡 Generating insights...")
        insights = self.generate_insights()

        # Combine into final report
        report = {
            "metadata": {
                "description": "Hierarchical taxonomy of model errors with LLM-based categorization",
                "total_categories": len(hierarchical["categories"]),
                "analysis_method": "Pattern-based categorization with domain indicators"
            },
            "taxonomy": hierarchical,
            "insights": insights
        }

        # Save report
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Report saved to: {output_file}")

        # Print summary
        print("\n" + "="*70)
        print("📊 ERROR CATEGORIZATION SUMMARY")
        print("="*70)

        print("\n📚 By Category:")
        for cat, summary in insights["top_level_summary"].items():
            print(f"\n  {cat.upper()}:")
            print(f"    Universal failures: {summary['universal_failures']}")
            print(f"    Top error types:")
            for et in summary['primary_error_types']:
                count = hierarchical["categories"][cat]["error_types"][et]["count"]
                desc = hierarchical["categories"][cat]["error_types"][et]["description"]
                print(f"      • {et:25s}: {count:3d} ({desc})")

        print("\n🔴 Critical Patterns (Across All Categories):")
        for pattern in insights["critical_patterns"]:
            print(f"  • {pattern['error_type']:25s}: {pattern['frequency']:3d} occurrences")
            print(f"    → {pattern['description']}")

        print("\n💡 Recommendations for ToGMAL:")
        for i, rec in enumerate(insights["recommendations"], 1):
            print(f"\n  {i}. {rec['issue']}")
            print(f"     → {rec['recommendation']}")

        print("\n" + "="*70)

        return report


if __name__ == '__main__':
    categorizer = LLMErrorCategorizer()
    report = categorizer.generate_report()
