#!/usr/bin/env python3
"""
Chain-of-Thought Failure Analyzer
==================================

Analyzes universal failures (100% model failure rate) to understand
WHY all models failed. Simulates CoT reasoning by analyzing:
- Question structure and complexity
- Required knowledge and reasoning steps
- Common pitfalls and error patterns

Author: ToGMAL Project
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass, asdict


@dataclass
class FailureAnalysis:
    """Analysis of why a question caused universal failure."""
    question: str
    category: str
    subject: str
    success_rate: float

    # Structural analysis
    question_length: int
    numeric_complexity: int  # Count of numbers
    formula_indicators: int  # Count of formulas/equations
    unit_count: int  # Count of units (psi, °F, etc.)

    # Reasoning requirements
    reasoning_steps: List[str]
    required_knowledge: List[str]
    calculation_type: str

    # Error hypothesis
    primary_failure_mode: str
    contributing_factors: List[str]
    difficulty_estimate: str


class CoTFailureAnalyzer:
    """Analyzes failures using pattern-based reasoning simulation."""

    # Unit indicators
    UNITS = [
        'psi', 'atm', 'pa', 'bar',  # Pressure
        '°f', '°c', '°k', 'fahrenheit', 'celsius', 'kelvin',  # Temperature
        'btu', 'j', 'cal', 'joule', 'calorie',  # Energy
        'ft', 'in', 'm', 'cm', 'mm', 'inch', 'meter',  # Length
        'lb', 'kg', 'g', 'pound', 'kilogram', 'gram',  # Mass
        'cfs', 'm³/s', 'gpm', 'lpm',  # Flow rate
        'mph', 'ft/min', 'm/s', 'km/h',  # Velocity
        'w', 'watt', 'hp', 'horsepower',  # Power
        'mol', 'mole', 'lbmol',  # Amount
        'v', 'volt', 'a', 'ampere', 'ohm', 'ω',  # Electrical
    ]

    # Formula indicators
    FORMULA_INDICATORS = [
        '=', '×', '÷', '∫', '∂', '∑', '√',  # Math symbols
        'formula', 'equation', 'calculate', 'compute',
        'modulus', 'coefficient', 'constant',
        'equilibrium', 'derivative', 'integral',
    ]

    # Calculation type keywords
    CALCULATION_TYPES = {
        'multi_step_derivation': ['calculate', 'then', 'using', 'given', 'find'],
        'unit_conversion': ['convert', 'psi', 'atm', '°f', '°c', 'btu'],
        'equilibrium_calculation': ['equilibrium', 'constant', 'kp', 'reaction'],
        'heat_transfer': ['heat', 'transfer', 'temperature', 'thermal'],
        'fluid_mechanics': ['flow', 'velocity', 'pressure', 'fluid'],
        'electrical_engineering': ['circuit', 'voltage', 'current', 'resistance'],
        'structural_analysis': ['load', 'stress', 'strain', 'modulus'],
    }

    def __init__(self):
        """Initialize analyzer."""
        # Load error taxonomy
        taxonomy_file = Path("data/error_taxonomy.json")
        with open(taxonomy_file) as f:
            self.taxonomy = json.load(f)

        # Load enriched dataset
        enriched_file = Path("data/autonomous_benchmarks/autonomous_dataset_enriched.json")
        with open(enriched_file) as f:
            self.dataset = json.load(f)

    def count_numbers(self, text: str) -> int:
        """Count numeric values in text."""
        # Match numbers including scientific notation
        pattern = r'\d+\.?\d*(?:[eE][+-]?\d+)?'
        return len(re.findall(pattern, text))

    def count_units(self, text: str) -> int:
        """Count unit indicators."""
        text_lower = text.lower()
        return sum(1 for unit in self.UNITS if unit in text_lower)

    def count_formulas(self, text: str) -> int:
        """Count formula indicators."""
        text_lower = text.lower()
        return sum(1 for indicator in self.FORMULA_INDICATORS if indicator in text_lower)

    def identify_calculation_type(self, text: str) -> str:
        """Identify the type of calculation required."""
        text_lower = text.lower()

        scores = {}
        for calc_type, keywords in self.CALCULATION_TYPES.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[calc_type] = score

        if not scores:
            return "unknown"

        return max(scores.items(), key=lambda x: x[1])[0]

    def infer_reasoning_steps(self, question: str, calc_type: str) -> List[str]:
        """Infer required reasoning steps based on question analysis."""
        steps = []

        # Check for unit conversion needs
        if self.count_units(question) > 2:
            steps.append("1. Convert all values to consistent unit system")

        # Check for formula application
        if 'modulus' in question.lower() or 'coefficient' in question.lower():
            steps.append("2. Identify and apply relevant formula")

        # Check for intermediate calculations
        if 'calculate' in question.lower() and 'given' in question.lower():
            steps.append("3. Calculate intermediate values from given data")

        # Check for final computation
        if 'find' in question.lower() or 'compute' in question.lower():
            steps.append("4. Compute final answer using intermediate results")

        # Check for precision requirements
        if self.count_numbers(question) > 3:
            steps.append("5. Maintain numerical precision throughout calculation")

        if not steps:
            steps = ["1. Understand question requirements", "2. Apply relevant knowledge", "3. Compute answer"]

        return steps

    def identify_required_knowledge(self, question: str, category: str, subject: str, calc_type: str) -> List[str]:
        """Identify required domain knowledge."""
        knowledge = []

        # Domain-specific knowledge
        if category == 'engineering':
            if 'thermodynamics' in subject.lower():
                knowledge.append("Thermodynamic principles and equations")
            if 'heat' in question.lower():
                knowledge.append("Heat transfer mechanisms (conduction, convection, radiation)")
            if 'equilibrium' in question.lower():
                knowledge.append("Chemical/thermodynamic equilibrium constants")
            if 'modulus' in question.lower():
                knowledge.append("Material properties (elastic modulus, strength)")

        # Mathematical knowledge
        if self.count_formulas(question) > 0:
            knowledge.append("Mathematical formulas and equation manipulation")

        # Unit conversion knowledge
        if self.count_units(question) > 2:
            knowledge.append("Unit conversion factors and dimensional analysis")

        # Numerical computation
        if self.count_numbers(question) > 3:
            knowledge.append("Multi-step numerical calculation")

        if not knowledge:
            knowledge = [f"{category.title()} domain knowledge"]

        return knowledge

    def hypothesize_failure_mode(self, analysis_data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Hypothesize why all models failed."""

        # Extract metrics
        units = analysis_data['unit_count']
        numbers = analysis_data['numeric_complexity']
        formulas = analysis_data['formula_indicators']
        calc_type = analysis_data['calculation_type']

        primary_mode = ""
        contributing_factors = []

        # Hypothesis 1: Unit conversion complexity
        if units >= 3:
            primary_mode = "Complex unit conversion requirements"
            contributing_factors.append(f"Question involves {units} different unit types")
            contributing_factors.append("Models struggle with multi-system unit conversions")

        # Hypothesis 2: Multi-step calculation
        elif numbers > 5 and formulas > 2:
            primary_mode = "Multi-step calculation with formula application"
            contributing_factors.append(f"Requires {numbers} numerical values in calculation")
            contributing_factors.append("Multiple formulas must be applied sequentially")
            contributing_factors.append("Precision errors compound through calculation chain")

        # Hypothesis 3: Specialized domain knowledge
        elif 'equilibrium' in calc_type or 'structural' in calc_type:
            primary_mode = "Specialized domain formula not in training data"
            contributing_factors.append(f"Requires {calc_type.replace('_', ' ')}")
            contributing_factors.append("Formula likely rare in general training corpus")

        # Hypothesis 4: Ambiguous or truncated question
        elif len(analysis_data['question']) < 100:
            primary_mode = "Question may be truncated or ambiguous"
            contributing_factors.append("Question appears incomplete")

        # Default
        else:
            primary_mode = "High conceptual difficulty"
            contributing_factors.append("Requires advanced domain expertise")

        return primary_mode, contributing_factors

    def estimate_difficulty(self, analysis_data: Dict[str, Any]) -> str:
        """Estimate difficulty level."""
        # Simple heuristic based on complexity indicators
        total_complexity = (
            analysis_data['numeric_complexity'] +
            analysis_data['formula_indicators'] * 2 +
            analysis_data['unit_count'] * 3 +
            len(analysis_data['reasoning_steps'])
        )

        if total_complexity > 15:
            return "EXTREME (Graduate level)"
        elif total_complexity > 10:
            return "VERY HIGH (Upper undergrad)"
        elif total_complexity > 5:
            return "HIGH (Lower undergrad)"
        else:
            return "MEDIUM (High school advanced)"

    def analyze_failure(self, question_data: Dict[str, Any]) -> FailureAnalysis:
        """Perform detailed failure analysis on a single question."""

        question = question_data['question']
        metadata = question_data['metadata']

        # Structural analysis
        nums = self.count_numbers(question)
        units = self.count_units(question)
        formulas = self.count_formulas(question)

        # Identify calculation type
        calc_type = self.identify_calculation_type(question)

        # Infer reasoning steps
        steps = self.infer_reasoning_steps(question, calc_type)

        # Identify required knowledge
        knowledge = self.identify_required_knowledge(
            question,
            metadata.get('category', ''),
            metadata.get('subject', ''),
            calc_type
        )

        # Build analysis data
        analysis_data = {
            'question': question,
            'unit_count': units,
            'numeric_complexity': nums,
            'formula_indicators': formulas,
            'calculation_type': calc_type,
            'reasoning_steps': steps,
            'required_knowledge': knowledge
        }

        # Hypothesize failure mode
        primary_mode, factors = self.hypothesize_failure_mode(analysis_data)

        # Estimate difficulty
        difficulty = self.estimate_difficulty(analysis_data)

        return FailureAnalysis(
            question=question[:200],
            category=metadata.get('category', 'unknown'),
            subject=metadata.get('subject', 'unknown'),
            success_rate=question_data['success_rate'],
            question_length=len(question),
            numeric_complexity=nums,
            formula_indicators=formulas,
            unit_count=units,
            reasoning_steps=steps,
            required_knowledge=knowledge,
            calculation_type=calc_type,
            primary_failure_mode=primary_mode,
            contributing_factors=factors,
            difficulty_estimate=difficulty
        )

    def analyze_all_universal_failures(self) -> List[FailureAnalysis]:
        """Analyze all questions with 100% failure rate."""
        print("\n" + "="*70)
        print("🔬 CHAIN-OF-THOUGHT FAILURE ANALYSIS")
        print("="*70)

        # Find universal failures
        universal_failures = [
            q for q in self.dataset['questions']
            if q['success_rate'] == 0.0
        ]

        print(f"\n📊 Found {len(universal_failures)} universal failures (0.0% success rate)")

        analyses = []
        for i, question_data in enumerate(universal_failures, 1):
            analysis = self.analyze_failure(question_data)
            analyses.append(analysis)

            if i <= 5:  # Print first 5 in detail
                print(f"\n{'─'*70}")
                print(f"FAILURE #{i}: {analysis.subject}")
                print(f"{'─'*70}")
                print(f"Question: {analysis.question}...")
                print(f"\n📈 Complexity Metrics:")
                print(f"  • Numeric values: {analysis.numeric_complexity}")
                print(f"  • Unit types: {analysis.unit_count}")
                print(f"  • Formula indicators: {analysis.formula_indicators}")
                print(f"  • Calculation type: {analysis.calculation_type}")
                print(f"\n🧠 Required Reasoning:")
                for step in analysis.reasoning_steps:
                    print(f"  {step}")
                print(f"\n📚 Required Knowledge:")
                for know in analysis.required_knowledge:
                    print(f"  • {know}")
                print(f"\n❌ Failure Hypothesis:")
                print(f"  PRIMARY: {analysis.primary_failure_mode}")
                for factor in analysis.contributing_factors:
                    print(f"  • {factor}")
                print(f"\n🎯 Estimated Difficulty: {analysis.difficulty_estimate}")

        return analyses

    def generate_report(self, output_file: Path = Path("data/cot_failure_analysis.json")):
        """Generate comprehensive failure analysis report."""

        # Analyze all universal failures
        analyses = self.analyze_all_universal_failures()

        # Aggregate insights
        insights = self._aggregate_insights(analyses)

        # Build report
        report = {
            "metadata": {
                "description": "Chain-of-Thought analysis of universal failures",
                "total_analyzed": len(analyses),
                "analysis_method": "Pattern-based reasoning simulation"
            },
            "analyses": [asdict(a) for a in analyses],
            "insights": insights
        }

        # Save report
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Report saved to: {output_file}")

        # Print summary
        self._print_summary(insights)

        return report

    def _aggregate_insights(self, analyses: List[FailureAnalysis]) -> Dict[str, Any]:
        """Aggregate insights from all analyses."""

        insights = {
            "by_subject": defaultdict(int),
            "by_calculation_type": defaultdict(int),
            "by_failure_mode": defaultdict(int),
            "by_difficulty": defaultdict(int),
            "complexity_stats": {
                "avg_numeric_complexity": sum(a.numeric_complexity for a in analyses) / len(analyses) if analyses else 0,
                "avg_unit_count": sum(a.unit_count for a in analyses) / len(analyses) if analyses else 0,
                "avg_formula_indicators": sum(a.formula_indicators for a in analyses) / len(analyses) if analyses else 0,
                "avg_reasoning_steps": sum(len(a.reasoning_steps) for a in analyses) / len(analyses) if analyses else 0,
            },
            "top_required_knowledge": defaultdict(int)
        }

        for analysis in analyses:
            insights["by_subject"][analysis.subject] += 1
            insights["by_calculation_type"][analysis.calculation_type] += 1
            insights["by_failure_mode"][analysis.primary_failure_mode] += 1
            insights["by_difficulty"][analysis.difficulty_estimate] += 1

            for knowledge in analysis.required_knowledge:
                insights["top_required_knowledge"][knowledge] += 1

        # Convert defaultdicts to regular dicts for JSON serialization
        return {
            "by_subject": dict(insights["by_subject"]),
            "by_calculation_type": dict(insights["by_calculation_type"]),
            "by_failure_mode": dict(insights["by_failure_mode"]),
            "by_difficulty": dict(insights["by_difficulty"]),
            "complexity_stats": insights["complexity_stats"],
            "top_required_knowledge": dict(sorted(
                insights["top_required_knowledge"].items(),
                key=lambda x: x[1],
                reverse=True
            ))
        }

    def _print_summary(self, insights: Dict[str, Any]):
        """Print summary of insights."""
        print("\n" + "="*70)
        print("📊 AGGREGATED INSIGHTS")
        print("="*70)

        print("\n🎯 By Subject:")
        for subject, count in sorted(insights["by_subject"].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  • {subject:40s}: {count:2d} failures")

        print("\n🧮 By Calculation Type:")
        for calc_type, count in sorted(insights["by_calculation_type"].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {calc_type:40s}: {count:2d} failures")

        print("\n❌ Primary Failure Modes:")
        for mode, count in sorted(insights["by_failure_mode"].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {mode:40s}: {count:2d} occurrences")

        print("\n📈 Complexity Statistics:")
        stats = insights["complexity_stats"]
        print(f"  • Avg numeric values per question: {stats['avg_numeric_complexity']:.1f}")
        print(f"  • Avg unit types per question: {stats['avg_unit_count']:.1f}")
        print(f"  • Avg formula indicators: {stats['avg_formula_indicators']:.1f}")
        print(f"  • Avg reasoning steps required: {stats['avg_reasoning_steps']:.1f}")

        print("\n📚 Top Required Knowledge Areas:")
        for knowledge, count in list(insights["top_required_knowledge"].items())[:10]:
            print(f"  • {knowledge:50s}: {count:2d}")

        print("\n" + "="*70)


if __name__ == '__main__':
    analyzer = CoTFailureAnalyzer()
    report = analyzer.generate_report()
