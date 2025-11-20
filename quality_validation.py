#!/usr/bin/env python3
"""
Quality Validation System for Task-Oriented Taxonomy

This module implements rigorous quality checks to ensure analyses are:
- Evidence-based (not AI slop)
- Internally consistent
- Grounded in established frameworks
- Predictively valid

Key Features:
1. Evidence requirement validation
2. Inter-rater reliability (multi-agent analysis)
3. Capability grounding validation
4. Consistency checks
5. Predictive validation
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter
import re


# Capability Registry: Ground all capabilities in established frameworks
CAPABILITY_REGISTRY = {
    "Prosodic Reasoning": {
        "definition": "Ability to represent and manipulate sound patterns including rhyme, meter, and rhythm",
        "cognitive_basis": "Phonological working memory and phonetic similarity representation",
        "references": [
            "Baddeley, A. (2003). Working memory and language",
            "Hayes, B. (2009). Introductory Phonology"
        ],
        "observable_tasks": [
            "rhyme generation",
            "meter tracking",
            "alliteration",
            "assonance"
        ],
        "failure_modes": [
            "ignores sound patterns",
            "violates phonotactic constraints",
            "cannot identify rhyming words",
            "produces prose instead of poetry"
        ],
        "related_capabilities": ["Phonetic Similarity Modeling"]
    },

    "Constraint Satisfaction": {
        "definition": "Ability to maintain and enforce multiple constraints simultaneously during generation",
        "cognitive_basis": "Executive function and goal management",
        "references": [
            "Russell, S. & Norvig, P. (2020). Artificial Intelligence: A Modern Approach",
            "Miyake, A. et al. (2000). The unity and diversity of executive functions"
        ],
        "observable_tasks": [
            "multi-constraint text generation",
            "format compliance",
            "word count limits",
            "alphabetic sequencing"
        ],
        "failure_modes": [
            "violates constraints after initial attempts",
            "cannot maintain all constraints simultaneously",
            "forgets constraints across generation steps"
        ],
        "related_capabilities": ["Constraint Satisfaction and State Tracking", "Sequential Constraint Propagation"]
    },

    "Theory of Mind": {
        "definition": "Ability to model others' mental states, beliefs, and perspectives distinct from one's own",
        "cognitive_basis": "Perspective-taking and mental state attribution",
        "references": [
            "Premack, D. & Woodruff, G. (1978). Does the chimpanzee have a theory of mind?",
            "Baron-Cohen, S. (1995). Mindblindness: An Essay on Autism and Theory of Mind"
        ],
        "observable_tasks": [
            "perspective-taking in reasoning",
            "false belief understanding",
            "intent recognition",
            "reference resolution from others' viewpoints"
        ],
        "failure_modes": [
            "cannot shift perspective",
            "treats all references as egocentric",
            "creates duplicate entities due to perspective confusion"
        ],
        "related_capabilities": ["Theory of Mind / Perspective Reasoning"]
    },

    "Meta-Cognitive Reasoning": {
        "definition": "Ability to reflect on and evaluate one's own cognitive processes and outputs",
        "cognitive_basis": "Metacognition and self-monitoring",
        "references": [
            "Flavell, J.H. (1979). Metacognition and cognitive monitoring",
            "Schraw, G. & Moshman, D. (1995). Metacognitive theories"
        ],
        "observable_tasks": [
            "self-critique",
            "error detection in own output",
            "confidence calibration",
            "improvement identification"
        ],
        "failure_modes": [
            "cannot adopt critical stance toward own work",
            "only produces positive self-assessment",
            "fails to identify improvements"
        ],
        "related_capabilities": ["Meta-Cognitive Reasoning"]
    },

    "Constraint Propagation": {
        "definition": "Ability to propagate constraint effects across multiple variables and timesteps",
        "cognitive_basis": "Constraint satisfaction and search algorithms",
        "references": [
            "Russell & Norvig (2020). Constraint Satisfaction Problems",
            "Mackworth, A.K. (1977). Consistency in networks of relations"
        ],
        "observable_tasks": [
            "logic puzzles with multiple constraints",
            "scheduling problems",
            "spatial arrangement tasks"
        ],
        "failure_modes": [
            "makes assignments without checking all constraints",
            "cannot systematically backtrack",
            "self-contradictory reasoning"
        ],
        "related_capabilities": ["Constraint Satisfaction Reasoning", "Multi-Step State Tracking"]
    },

    "Contradiction Detection": {
        "definition": "Ability to detect logical impossibilities and contradictory scenarios",
        "cognitive_basis": "Logical reasoning and consistency checking",
        "references": [
            "Johnson-Laird, P.N. (2006). How We Reason",
            "Rips, L.J. (1994). The Psychology of Proof"
        ],
        "observable_tasks": [
            "impossibility detection",
            "consistency validation",
            "paradox recognition"
        ],
        "failure_modes": [
            "accepts impossible scenarios",
            "generates nonsensical answers",
            "fails to check preconditions"
        ],
        "related_capabilities": ["Constraint Validation and Contradiction Detection"]
    },

    "Persona Consistency": {
        "definition": "Ability to maintain character-specific knowledge, personality, and communication style",
        "cognitive_basis": "Character knowledge representation and response filtering",
        "references": [
            "Schank, R.C. & Abelson, R.P. (1977). Scripts, Plans, Goals and Understanding",
            "Bower, G.H. & Morrow, D.G. (1990). Mental models in narrative comprehension"
        ],
        "observable_tasks": [
            "roleplay maintenance",
            "character-appropriate responses",
            "domain expertise consistency"
        ],
        "failure_modes": [
            "breaks character",
            "generates responses inconsistent with persona",
            "ignores character-specific constraints"
        ],
        "related_capabilities": ["Persona Consistency and Knowledge Grounding"]
    }
}


@dataclass
class ValidationResult:
    """Result of validation check"""
    valid: bool
    score: float  # 0-1
    issues: List[str]
    warnings: List[str]


class QualityValidator:
    """
    Validates task-level error analyses for quality and grounding.

    Prevents "AI slop" through rigorous evidence and consistency checks.
    """

    def __init__(self, capability_registry: Dict = None):
        self.registry = capability_registry or CAPABILITY_REGISTRY

    def validate_analysis(self, analysis: Dict) -> ValidationResult:
        """
        Comprehensive validation of a single analysis.

        Returns ValidationResult with score and issues.
        """
        issues = []
        warnings = []
        scores = []

        # Check 1: Evidence requirements
        evidence_result = self._validate_evidence(analysis)
        scores.append(evidence_result.score)
        issues.extend(evidence_result.issues)
        warnings.extend(evidence_result.warnings)

        # Check 2: Capability grounding
        grounding_result = self._validate_capability_grounding(analysis)
        scores.append(grounding_result.score)
        issues.extend(grounding_result.issues)
        warnings.extend(grounding_result.warnings)

        # Check 3: Error chain causality
        causality_result = self._validate_causality(analysis)
        scores.append(causality_result.score)
        issues.extend(causality_result.issues)
        warnings.extend(causality_result.warnings)

        # Check 4: Specificity
        specificity_result = self._validate_specificity(analysis)
        scores.append(specificity_result.score)
        issues.extend(specificity_result.issues)
        warnings.extend(specificity_result.warnings)

        # Overall score: average of component scores
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Valid if score > 0.7 and no critical issues
        critical_issues = [i for i in issues if "CRITICAL" in i]
        valid = overall_score > 0.7 and len(critical_issues) == 0

        return ValidationResult(
            valid=valid,
            score=overall_score,
            issues=issues,
            warnings=warnings
        )

    def _validate_evidence(self, analysis: Dict) -> ValidationResult:
        """Validate that analysis has specific evidence"""
        issues = []
        warnings = []
        score = 1.0

        # Check for required fields
        required = ['losing_response_snippet', 'winning_response_snippet', 'observable_failure']

        for field in required:
            if field not in analysis or not analysis[field]:
                issues.append(f"CRITICAL: Missing required field: {field}")
                score -= 0.3

        # Check for vague/generic descriptions
        conceptual_error = analysis.get('conceptual_error', '')
        if len(conceptual_error) < 20:
            warnings.append("Conceptual error description is very short")
            score -= 0.1

        # Check for specific evidence in observable failure
        observable = analysis.get('observable_failure', '')
        if not any(word in observable.lower() for word in ['instead', 'violates', 'cannot', 'lacks', 'wrong', 'incorrect']):
            warnings.append("Observable failure lacks specific description")
            score -= 0.1

        # Check explanation specificity
        explanation = analysis.get('explanation', '')
        if len(explanation) < 30:
            warnings.append("Explanation is too brief")
            score -= 0.1

        return ValidationResult(
            valid=score > 0.7,
            score=max(0.0, score),
            issues=issues,
            warnings=warnings
        )

    def _validate_capability_grounding(self, analysis: Dict) -> ValidationResult:
        """Validate capability is in registry and properly grounded"""
        issues = []
        warnings = []
        score = 1.0

        capability_cat = analysis.get('capability_category', '')

        # Check if capability exists in registry (or is related to one)
        matched = False
        for registered_cap, details in self.registry.items():
            if capability_cat == registered_cap:
                matched = True
                break
            if capability_cat in details.get('related_capabilities', []):
                matched = True
                warnings.append(f"Capability '{capability_cat}' is related to '{registered_cap}' but not exact match")
                score -= 0.1
                break

        if not matched:
            # Allow new capabilities but flag for review
            warnings.append(f"NEW CAPABILITY: '{capability_cat}' not in registry - needs grounding review")
            score -= 0.2

        # If matched, validate observable failure matches known failure modes
        if matched:
            failure = analysis.get('observable_failure', '').lower()
            known_failures = self.registry.get(capability_cat, {}).get('failure_modes', [])

            if known_failures:
                # Check if observable failure is similar to known modes
                matches_known = any(
                    any(word in failure for word in known_failure.split())
                    for known_failure in known_failures
                )

                if not matches_known:
                    warnings.append(
                        f"Observable failure doesn't match known patterns for {capability_cat}"
                    )
                    score -= 0.15

        return ValidationResult(
            valid=score > 0.7,
            score=max(0.0, score),
            issues=issues,
            warnings=warnings
        )

    def _validate_causality(self, analysis: Dict) -> ValidationResult:
        """Validate error chain shows logical causal progression"""
        issues = []
        warnings = []
        score = 1.0

        error_chain = analysis.get('error_chain', [])

        if not error_chain:
            issues.append("CRITICAL: Missing error chain")
            return ValidationResult(valid=False, score=0.0, issues=issues, warnings=[])

        if len(error_chain) < 2:
            warnings.append("Error chain should have at least 2 steps")
            score -= 0.2

        # Check for causal language
        causal_words = ['because', 'therefore', 'thus', 'leads to', '->', 'causes', 'results in']

        chain_text = ' '.join(error_chain).lower()
        has_causal = any(word in chain_text for word in causal_words)

        if not has_causal:
            warnings.append("Error chain lacks explicit causal connections")
            score -= 0.15

        # Check progression: root cause → intermediate → observable
        if len(error_chain) >= 3:
            # First step should be about missing capability/representation
            first_step = error_chain[0].lower()
            if not any(word in first_step for word in ['no', 'lacks', 'cannot', 'missing', 'without']):
                warnings.append("Error chain should start with root capability gap")
                score -= 0.1

            # Last step should be about observable behavior
            last_step = error_chain[-1].lower()
            observable = analysis.get('observable_failure', '').lower()
            if not any(word in last_step for word in observable.split()[:5]):
                warnings.append("Error chain should end with observable failure")
                score -= 0.1

        return ValidationResult(
            valid=score > 0.7,
            score=max(0.0, score),
            issues=issues,
            warnings=warnings
        )

    def _validate_specificity(self, analysis: Dict) -> ValidationResult:
        """Check that analysis is specific, not generic"""
        issues = []
        warnings = []
        score = 1.0

        # Generic phrases that indicate AI slop
        slop_phrases = [
            "fails to complete",
            "doesn't work properly",
            "has issues with",
            "struggles with the task",
            "makes mistakes",
            "doesn't understand",
            "fails the requirement"
        ]

        fields_to_check = [
            'conceptual_error',
            'observable_failure',
            'explanation'
        ]

        for field in fields_to_check:
            text = analysis.get(field, '').lower()
            for slop in slop_phrases:
                if slop in text:
                    warnings.append(f"Generic phrase '{slop}' in {field}")
                    score -= 0.1

        # Check for technical specificity
        technical_indicators = [
            'representation', 'model', 'pattern', 'constraint', 'state',
            'algorithm', 'mechanism', 'process', 'structure'
        ]

        conceptual = analysis.get('conceptual_error', '').lower()
        has_technical = any(word in conceptual for word in technical_indicators)

        if not has_technical:
            warnings.append("Conceptual error lacks technical specificity")
            score -= 0.15

        return ValidationResult(
            valid=score > 0.7,
            score=max(0.0, score),
            issues=issues,
            warnings=warnings
        )


class InterRaterReliability:
    """
    Compute agreement between multiple independent analyses of the same case.

    This prevents overfitting to a single reasoning path and ensures
    conclusions are robust.
    """

    def __init__(self):
        pass

    def compute_agreement(
        self,
        analyses: List[Dict],
        fields: List[str] = None
    ) -> Dict[str, float]:
        """
        Compute pairwise agreement across multiple analyses.

        Args:
            analyses: List of analysis dicts for same case
            fields: Which fields to check agreement on

        Returns:
            Dict of field -> agreement_score (0-1)
        """
        if fields is None:
            fields = [
                'capability_category',
                'task_domain',
                'is_understanding_failure',
                'error_severity'
            ]

        agreements = {}

        for field in fields:
            values = [a.get(field) for a in analyses]

            if field in ['is_understanding_failure']:
                # Boolean field: exact match percentage
                agreements[field] = self._boolean_agreement(values)
            elif field in ['error_severity']:
                # Ordinal field: allow ±1 difference
                agreements[field] = self._ordinal_agreement(values)
            else:
                # Categorical field: check for matching categories or synonyms
                agreements[field] = self._categorical_agreement(values)

        # Overall agreement: average across fields
        agreements['overall'] = sum(agreements.values()) / len(agreements)

        return agreements

    def _boolean_agreement(self, values: List[bool]) -> float:
        """Exact match for boolean values"""
        if not values:
            return 0.0

        # Count most common value
        counter = Counter(values)
        most_common_count = counter.most_common(1)[0][1]

        return most_common_count / len(values)

    def _ordinal_agreement(self, values: List[str]) -> float:
        """Agreement allowing ±1 for ordinal scales"""
        severity_order = ['minor', 'moderate', 'major', 'critical']

        if not values:
            return 0.0

        # Convert to numeric
        numeric = []
        for v in values:
            try:
                numeric.append(severity_order.index(v))
            except (ValueError, AttributeError):
                numeric.append(-1)

        # Compute pairwise agreement (allow ±1 difference)
        agreements = []
        for i in range(len(numeric)):
            for j in range(i + 1, len(numeric)):
                if numeric[i] == -1 or numeric[j] == -1:
                    agreements.append(0.0)
                elif abs(numeric[i] - numeric[j]) <= 1:
                    agreements.append(1.0)
                else:
                    agreements.append(0.0)

        return sum(agreements) / len(agreements) if agreements else 0.0

    def _categorical_agreement(self, values: List[str]) -> float:
        """Agreement for categorical values with synonym matching"""
        if not values:
            return 0.0

        # Remove None/empty values
        values = [v for v in values if v]

        if not values:
            return 0.0

        # Exact match
        counter = Counter(values)
        most_common_count = counter.most_common(1)[0][1]
        exact_agreement = most_common_count / len(values)

        # Synonym matching (fuzzy)
        # Group similar values
        groups = self._group_similar_values(values)

        largest_group = max(len(g) for g in groups.values())
        synonym_agreement = largest_group / len(values)

        # Return average of exact and synonym agreement
        return (exact_agreement + synonym_agreement) / 2

    def _group_similar_values(self, values: List[str]) -> Dict[str, List[str]]:
        """Group values that are semantically similar"""
        # Simple word overlap heuristic
        groups = defaultdict(list)

        for value in values:
            # Find if value belongs to existing group
            matched = False
            for group_key in groups.keys():
                # Check word overlap
                value_words = set(value.lower().split())
                key_words = set(group_key.lower().split())

                overlap = len(value_words & key_words) / max(len(value_words), len(key_words))

                if overlap > 0.5:  # >50% word overlap
                    groups[group_key].append(value)
                    matched = True
                    break

            if not matched:
                groups[value] = [value]

        return groups


def validate_taxonomy(taxonomy_file: str) -> Dict:
    """
    Validate entire taxonomy for quality and consistency.

    Args:
        taxonomy_file: Path to taxonomy JSON

    Returns:
        Dict with validation statistics and issues
    """
    print("Loading taxonomy...")
    with open(taxonomy_file, 'r') as f:
        data = json.load(f)

    analyses = data.get('detailed_errors', [])

    print(f"Validating {len(analyses)} analyses...")

    validator = QualityValidator()
    results = []

    for i, analysis in enumerate(analyses, 1):
        result = validator.validate_analysis(analysis)
        results.append({
            'question_id': analysis.get('question_id'),
            'valid': result.valid,
            'score': result.score,
            'issues': result.issues,
            'warnings': result.warnings
        })

        if not result.valid:
            print(f"  [{i}] Q{analysis.get('question_id')}: INVALID (score={result.score:.2f})")
            for issue in result.issues:
                print(f"      - {issue}")

    # Statistics
    valid_count = sum(1 for r in results if r['valid'])
    avg_score = sum(r['score'] for r in results) / len(results)

    all_issues = [issue for r in results for issue in r['issues']]
    all_warnings = [warn for r in results for warn in r['warnings']]

    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print(f"\nTotal analyses: {len(analyses)}")
    print(f"Valid: {valid_count} ({100*valid_count/len(analyses):.1f}%)")
    print(f"Invalid: {len(analyses) - valid_count}")
    print(f"Average quality score: {avg_score:.2f}/1.0")
    print(f"\nTotal issues: {len(all_issues)}")
    print(f"Total warnings: {len(all_warnings)}")

    if all_issues:
        print("\nMost common issues:")
        issue_counter = Counter(all_issues)
        for issue, count in issue_counter.most_common(5):
            print(f"  - {issue}: {count}")

    if all_warnings:
        print("\nMost common warnings:")
        warning_counter = Counter(all_warnings)
        for warning, count in warning_counter.most_common(5):
            print(f"  - {warning}: {count}")

    return {
        'total': len(analyses),
        'valid': valid_count,
        'invalid': len(analyses) - valid_count,
        'average_score': avg_score,
        'results': results,
        'issues': all_issues,
        'warnings': all_warnings
    }


def main():
    """Validate taxonomy with optional command-line argument"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Validate task-oriented taxonomy')
    parser.add_argument('--taxonomy-file',
                       default='./data/mt_bench/task_analysis/demo_taxonomy.json',
                       help='Path to taxonomy JSON file')
    parser.add_argument('--output',
                       default='./data/mt_bench/task_analysis/validation_report.json',
                       help='Path to output validation report')

    args = parser.parse_args()
    taxonomy_file = args.taxonomy_file

    if not Path(taxonomy_file).exists():
        print(f"Error: Taxonomy file not found: {taxonomy_file}")
        print("Run demo_task_analysis.py or analyze_complete_mt_bench.py first to generate it.")
        sys.exit(1)

    print(f"Loading taxonomy from {taxonomy_file}...")
    validation_results = validate_taxonomy(taxonomy_file)

    # Save validation report
    output_file = args.output
    with open(output_file, 'w') as f:
        json.dump(validation_results, f, indent=2)

    print(f"\n✓ Validation report saved to: {output_file}")


if __name__ == "__main__":
    main()
