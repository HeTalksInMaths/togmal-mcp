"""
Advanced Error Analysis with Research-Based Taxonomy

Incorporates findings from:
- MMLU-Pro error analysis (39% reasoning, 35% knowledge, 12% computational)
- "Are We Done with MMLU?" dataset quality framework
- Hierarchical Error Framework (HEC) - Reason's error hierarchy
- Bloom's Taxonomy for cognitive complexity
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import numpy as np
from collections import Counter, defaultdict
import re

from error_taxonomy import (
    ErrorRecord, ErrorCategory, ErrorSubtype,
    ErrorDetector, SUBTYPE_TO_CATEGORY
)


# ============================================================================
# Dataset Quality Validation (from "Are We Done with MMLU?")
# ============================================================================

class DatasetQualityIssue(Enum):
    """Issues with the dataset itself, not model performance"""
    BAD_QUESTION_CLARITY = "bad_question_clarity"  # Ambiguous or poorly written
    BAD_OPTIONS = "bad_options"  # Implausible or duplicate options
    NO_CORRECT_OPTION = "no_correct_option"  # All answers wrong
    MULTIPLE_CORRECT = "multiple_correct"  # Multiple valid answers
    VALID = "valid"  # No issues detected


@dataclass
class QuestionQualityAnalysis:
    """Analysis of dataset question quality"""
    question_id: str
    issue_type: DatasetQualityIssue
    confidence: float  # 0-1, how confident we are in this assessment
    evidence: List[str]  # Reasons for flagging
    needs_human_review: bool


class DatasetQualityValidator:
    """Validates MMLU-Pro questions for dataset errors"""

    @staticmethod
    def check_option_quality(choices: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if options are reasonable.
        Returns (is_bad, evidence)
        """
        evidence = []

        # Check for duplicates
        if len(choices) != len(set(choices)):
            evidence.append("Duplicate answer choices")

        # Check for very short options (might be placeholders)
        very_short = [c for c in choices if len(c.strip()) < 3]
        if len(very_short) >= 2:
            evidence.append(f"{len(very_short)} options are unusually short")

        # Check for identical lengths (might indicate auto-generated)
        lengths = [len(c) for c in choices]
        if len(set(lengths)) == 1 and lengths[0] > 50:
            evidence.append("All options have identical length")

        return len(evidence) > 0, evidence

    @staticmethod
    def check_question_clarity(question_text: str) -> Tuple[bool, List[str]]:
        """
        Check if question is clearly written.
        Returns (is_unclear, evidence)
        """
        evidence = []

        # Too short (incomplete question)
        if len(question_text.strip()) < 20:
            evidence.append("Question is unusually short")

        # Multiple question marks (confusion)
        if question_text.count('?') > 2:
            evidence.append("Multiple question marks")

        # Contains "[unclear]" or similar markers
        unclear_markers = ['[unclear]', '[?]', '___', '[missing]']
        if any(marker in question_text.lower() for marker in unclear_markers):
            evidence.append("Contains unclear/missing content markers")

        # Excessive punctuation (formatting error)
        if question_text.count('..') > 2:
            evidence.append("Excessive ellipsis usage")

        return len(evidence) > 0, evidence

    @staticmethod
    def detect_multiple_correct_heuristic(
        question_text: str,
        choices: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Heuristic check for potentially multiple correct answers.
        This requires LLM or human verification.
        """
        evidence = []

        # Questions asking for "all of the following" but giving single answer
        if any(phrase in question_text.lower() for phrase in
               ['all of the following', 'all of these', 'which are true']):
            if not any('all of the above' in c.lower() for c in choices):
                evidence.append("'All of the following' question without 'all of the above' option")

        # Very similar answer choices (might all be partially correct)
        if len(choices) >= 4:
            # Check if many choices share common prefixes
            prefixes = [c[:20] for c in choices if len(c) >= 20]
            if len(set(prefixes)) < len(prefixes) * 0.5:
                evidence.append("Many answer choices are very similar")

        return len(evidence) > 0, evidence

    @classmethod
    def validate_question(
        cls,
        question_id: str,
        question_text: str,
        choices: List[str],
        correct_answer: str
    ) -> QuestionQualityAnalysis:
        """
        Comprehensive quality check for a single question.
        """
        all_evidence = []
        issue_type = DatasetQualityIssue.VALID

        # Check option quality
        bad_options, opt_evidence = cls.check_option_quality(choices)
        if bad_options:
            all_evidence.extend(opt_evidence)
            issue_type = DatasetQualityIssue.BAD_OPTIONS

        # Check question clarity
        unclear, clarity_evidence = cls.check_question_clarity(question_text)
        if unclear:
            all_evidence.extend(clarity_evidence)
            if issue_type == DatasetQualityIssue.VALID:
                issue_type = DatasetQualityIssue.BAD_QUESTION_CLARITY

        # Check for multiple correct (heuristic)
        multi_correct, multi_evidence = cls.detect_multiple_correct_heuristic(
            question_text, choices
        )
        if multi_correct:
            all_evidence.extend(multi_evidence)
            # This is tentative - needs review
            if issue_type == DatasetQualityIssue.VALID:
                issue_type = DatasetQualityIssue.MULTIPLE_CORRECT

        # Confidence based on evidence strength
        confidence = min(len(all_evidence) * 0.3, 0.9)

        # Flag for human review if evidence found
        needs_review = len(all_evidence) > 0

        return QuestionQualityAnalysis(
            question_id=question_id,
            issue_type=issue_type,
            confidence=confidence,
            evidence=all_evidence,
            needs_human_review=needs_review
        )


# ============================================================================
# Hierarchical Error Attribution (Reason's Error Hierarchy)
# ============================================================================

class ErrorLayer(Enum):
    """
    Reason's error hierarchy adapted for LLMs.
    From most fundamental to most superficial.
    """
    KNOWLEDGE = "knowledge"  # Missing or wrong knowledge (58.4% per HEC paper)
    REASONING = "reasoning"  # Logical inference failures (39% per MMLU-Pro)
    EXECUTION = "execution"  # Computational/format errors (12% per MMLU-Pro)
    SKILL = "skill"  # Output generation slips


@dataclass
class HierarchicalErrorAnalysis:
    """
    Multi-layer error attribution.
    An error can have multiple contributing factors across layers.
    """
    error_record: ErrorRecord

    # Primary layer (main cause)
    primary_layer: ErrorLayer

    # Secondary layers (contributing factors)
    secondary_layers: List[ErrorLayer] = field(default_factory=list)

    # Layer-specific diagnostics
    knowledge_gaps: List[str] = field(default_factory=list)  # What knowledge is missing
    reasoning_failures: List[str] = field(default_factory=list)  # What inference failed
    execution_errors: List[str] = field(default_factory=list)  # What went wrong technically

    # Intervention recommendations
    recommended_interventions: List[str] = field(default_factory=list)


class HierarchicalErrorAnalyzer:
    """
    Analyzes errors across multiple layers of the hierarchy.
    """

    @staticmethod
    def attribute_to_layer(error: ErrorRecord) -> ErrorLayer:
        """
        Determine primary error layer based on error subtype.
        """
        if error.error_category == ErrorCategory.KNOWLEDGE_DEFICIT:
            return ErrorLayer.KNOWLEDGE

        elif error.error_category == ErrorCategory.REASONING_FAILURE:
            return ErrorLayer.REASONING

        elif error.error_category in [ErrorCategory.FORMAT_ERROR]:
            return ErrorLayer.EXECUTION

        elif error.error_category == ErrorCategory.COMPREHENSION_ERROR:
            # Comprehension can be knowledge or reasoning
            if error.error_subtype in [ErrorSubtype.CONTEXT_NEGLECT,
                                       ErrorSubtype.AMBIGUITY_MISHANDLING]:
                return ErrorLayer.REASONING
            else:
                return ErrorLayer.KNOWLEDGE

        else:
            return ErrorLayer.KNOWLEDGE  # Default

    @staticmethod
    def recommend_interventions(layer: ErrorLayer, error: ErrorRecord) -> List[str]:
        """
        Recommend interventions based on error layer.
        Based on research findings about what works for each layer.
        """
        interventions = []

        if layer == ErrorLayer.KNOWLEDGE:
            interventions.append("RAG: Retrieve relevant knowledge from external sources")
            interventions.append("Fine-tuning: Add more training data in this domain")
            if error.domain:
                interventions.append(f"Domain-specific pretraining: {error.domain}")

        elif layer == ErrorLayer.REASONING:
            interventions.append("Chain-of-thought: Prompt for step-by-step reasoning")
            interventions.append("Self-consistency: Sample multiple reasoning paths")
            interventions.append("Verification: Ask model to double-check logic")

        elif layer == ErrorLayer.EXECUTION:
            interventions.append("Tool use: Delegate calculations to external tools")
            interventions.append("Format constraints: Provide output schema")
            interventions.append("Post-processing: Validate and correct format")

        # Subtype-specific recommendations
        if error.error_subtype == ErrorSubtype.NEGATION_BLINDNESS:
            interventions.append("Highlight negations: Use formatting to emphasize 'not', 'except'")

        if error.error_subtype == ErrorSubtype.QUANTITATIVE_REASONING:
            interventions.append("Calculator tool: Use external computation")
            interventions.append("Symbolic solver: Use SymPy or similar")

        return interventions

    @classmethod
    def analyze(cls, error: ErrorRecord) -> HierarchicalErrorAnalysis:
        """
        Perform full hierarchical analysis of an error.
        """
        primary_layer = cls.attribute_to_layer(error)
        secondary_layers = []

        # Determine secondary factors
        # E.g., a knowledge error might also have reasoning components
        if primary_layer == ErrorLayer.KNOWLEDGE:
            # Check if reasoning was also required
            if any(pattern in error.error_patterns for pattern in
                   ['multi_step', 'causal', 'counterfactual']):
                secondary_layers.append(ErrorLayer.REASONING)

        # Generate diagnostics
        knowledge_gaps = []
        reasoning_failures = []
        execution_errors = []

        if ErrorLayer.KNOWLEDGE in [primary_layer] + secondary_layers:
            if error.error_subtype == ErrorSubtype.FACTUAL_GAP:
                knowledge_gaps.append(f"Missing factual knowledge in {error.domain}")
            elif error.error_subtype == ErrorSubtype.DOMAIN_BLIND_SPOT:
                knowledge_gaps.append(f"Weak understanding of {error.domain} domain")
            elif error.error_subtype == ErrorSubtype.MISCONCEPTION:
                knowledge_gaps.append("Active incorrect belief")

        if ErrorLayer.REASONING in [primary_layer] + secondary_layers:
            if error.error_subtype == ErrorSubtype.MULTI_STEP_REASONING:
                reasoning_failures.append("Failed to chain multiple logical steps")
            elif error.error_subtype == ErrorSubtype.CAUSAL_REASONING:
                reasoning_failures.append("Confused correlation with causation")

        if ErrorLayer.EXECUTION in [primary_layer] + secondary_layers:
            if error.error_subtype == ErrorSubtype.QUANTITATIVE_REASONING:
                execution_errors.append("Calculation error")

        # Get intervention recommendations
        interventions = cls.recommend_interventions(primary_layer, error)

        return HierarchicalErrorAnalysis(
            error_record=error,
            primary_layer=primary_layer,
            secondary_layers=secondary_layers,
            knowledge_gaps=knowledge_gaps,
            reasoning_failures=reasoning_failures,
            execution_errors=execution_errors,
            recommended_interventions=interventions
        )


# ============================================================================
# Cognitive Complexity Scoring (Bloom's Taxonomy)
# ============================================================================

class CognitiveLevel(Enum):
    """
    Bloom's Taxonomy levels adapted for MMLU-Pro.
    From simplest to most complex.
    """
    REMEMBER = 1  # Recall facts
    UNDERSTAND = 2  # Explain concepts
    APPLY = 3  # Use knowledge in new situations
    ANALYZE = 4  # Break down, compare
    EVALUATE = 5  # Judge, critique
    CREATE = 6  # Generate novel solutions


@dataclass
class CognitiveComplexityScore:
    """Cognitive complexity assessment for a question"""
    question_id: str
    cognitive_level: CognitiveLevel
    confidence: float
    indicators: List[str]  # Why we assigned this level


class CognitiveComplexityAnalyzer:
    """
    Classify questions by cognitive complexity using Bloom's Taxonomy.
    """

    # Keyword indicators for each level
    REMEMBER_KEYWORDS = [
        'what is', 'define', 'list', 'name', 'identify', 'recall',
        'who', 'when', 'where', 'which'
    ]

    UNDERSTAND_KEYWORDS = [
        'explain', 'describe', 'summarize', 'interpret', 'compare',
        'contrast', 'classify', 'why does'
    ]

    APPLY_KEYWORDS = [
        'apply', 'demonstrate', 'calculate', 'solve', 'use',
        'implement', 'show how', 'compute'
    ]

    ANALYZE_KEYWORDS = [
        'analyze', 'differentiate', 'distinguish', 'examine',
        'investigate', 'categorize', 'infer', 'determine'
    ]

    EVALUATE_KEYWORDS = [
        'evaluate', 'assess', 'judge', 'critique', 'justify',
        'argue', 'defend', 'support', 'which is best'
    ]

    CREATE_KEYWORDS = [
        'create', 'design', 'develop', 'formulate', 'construct',
        'propose', 'devise', 'generate', 'hypothesize'
    ]

    @classmethod
    def classify_cognitive_level(
        cls,
        question_text: str,
        domain: str
    ) -> CognitiveComplexityScore:
        """
        Classify question by cognitive complexity.
        """
        text_lower = question_text.lower()
        indicators = []
        level = CognitiveLevel.UNDERSTAND  # Default

        # Check from highest to lowest (higher levels often include lower)
        if any(kw in text_lower for kw in cls.CREATE_KEYWORDS):
            level = CognitiveLevel.CREATE
            indicators.append("Contains creation/generation verbs")

        elif any(kw in text_lower for kw in cls.EVALUATE_KEYWORDS):
            level = CognitiveLevel.EVALUATE
            indicators.append("Requires judgment/evaluation")

        elif any(kw in text_lower for kw in cls.ANALYZE_KEYWORDS):
            level = CognitiveLevel.ANALYZE
            indicators.append("Requires analysis/differentiation")

        elif any(kw in text_lower for kw in cls.APPLY_KEYWORDS):
            level = CognitiveLevel.APPLY
            indicators.append("Requires application of knowledge")

        elif any(kw in text_lower for kw in cls.REMEMBER_KEYWORDS):
            level = CognitiveLevel.REMEMBER
            indicators.append("Simple factual recall")

        else:
            level = CognitiveLevel.UNDERSTAND
            indicators.append("Requires understanding/explanation")

        # Adjust based on question length and structure
        sentences = question_text.split('.')
        if len(sentences) >= 4:
            # Long complex questions likely higher-order
            if level.value < CognitiveLevel.ANALYZE.value:
                level = CognitiveLevel.ANALYZE
                indicators.append("Complex multi-sentence question")

        # Domain-specific adjustments
        if domain in ['math', 'physics', 'chemistry']:
            # STEM questions often require application
            if level.value < CognitiveLevel.APPLY.value:
                level = CognitiveLevel.APPLY
                indicators.append("STEM domain requires application")

        # Confidence based on evidence
        confidence = 0.7 if len(indicators) >= 2 else 0.5

        return CognitiveComplexityScore(
            question_id="",  # Fill in when called
            cognitive_level=level,
            confidence=confidence,
            indicators=indicators
        )


# ============================================================================
# Comparison to Published Baselines
# ============================================================================

@dataclass
class BaselineComparison:
    """
    Compare our error distribution to published MMLU-Pro baseline.

    Published baseline (GPT-4o on MMLU-Pro):
    - 39% Reasoning process flaws
    - 35% Domain expertise gaps
    - 12% Computational errors
    - 14% Other
    """
    model_name: str

    # Our measured distribution
    knowledge_errors_pct: float
    reasoning_errors_pct: float
    execution_errors_pct: float
    other_errors_pct: float

    # Published baseline
    baseline_reasoning_pct: float = 39.0
    baseline_knowledge_pct: float = 35.0
    baseline_execution_pct: float = 12.0
    baseline_other_pct: float = 14.0

    # Comparison metrics
    deviation_from_baseline: Dict[str, float] = field(default_factory=dict)
    similar_to_gpt4o: bool = False


class BaselineComparer:
    """Compare model error profiles to published baselines"""

    @staticmethod
    def compare_to_mmlu_pro_baseline(
        errors: List[ErrorRecord],
        model_name: str
    ) -> BaselineComparison:
        """
        Compare error distribution to GPT-4o baseline from MMLU-Pro paper.
        """
        total = len(errors)
        if total == 0:
            return None

        # Count by layer
        knowledge_count = len([e for e in errors
                              if e.error_category == ErrorCategory.KNOWLEDGE_DEFICIT])
        reasoning_count = len([e for e in errors
                              if e.error_category == ErrorCategory.REASONING_FAILURE])
        execution_count = len([e for e in errors
                              if e.error_category == ErrorCategory.FORMAT_ERROR])
        other_count = total - knowledge_count - reasoning_count - execution_count

        # Convert to percentages
        knowledge_pct = (knowledge_count / total) * 100
        reasoning_pct = (reasoning_count / total) * 100
        execution_pct = (execution_count / total) * 100
        other_pct = (other_count / total) * 100

        # Calculate deviations
        deviations = {
            'knowledge': knowledge_pct - 35.0,
            'reasoning': reasoning_pct - 39.0,
            'execution': execution_pct - 12.0,
            'other': other_pct - 14.0
        }

        # Check if similar to GPT-4o (within 10% on all categories)
        similar = all(abs(dev) < 10.0 for dev in deviations.values())

        return BaselineComparison(
            model_name=model_name,
            knowledge_errors_pct=knowledge_pct,
            reasoning_errors_pct=reasoning_pct,
            execution_errors_pct=execution_pct,
            other_errors_pct=other_pct,
            deviation_from_baseline=deviations,
            similar_to_gpt4o=similar
        )


# ============================================================================
# Integrated Advanced Analyzer
# ============================================================================

class AdvancedErrorAnalyzer:
    """
    Integrated error analysis system incorporating all research findings.
    """

    def __init__(self):
        self.quality_validator = DatasetQualityValidator()
        self.hierarchical_analyzer = HierarchicalErrorAnalyzer()
        self.cognitive_analyzer = CognitiveComplexityAnalyzer()
        self.baseline_comparer = BaselineComparer()

    def analyze_error_comprehensive(
        self,
        error: ErrorRecord
    ) -> Dict:
        """
        Comprehensive multi-faceted error analysis.
        """
        # 1. Validate question quality
        quality = self.quality_validator.validate_question(
            error.question_id,
            error.question_text,
            error.choices,
            error.correct_answer
        )

        # 2. Hierarchical error attribution
        hierarchical = self.hierarchical_analyzer.analyze(error)

        # 3. Cognitive complexity
        cognitive = self.cognitive_analyzer.classify_cognitive_level(
            error.question_text,
            error.domain
        )

        return {
            'error_record': error,
            'dataset_quality': quality,
            'hierarchical_analysis': hierarchical,
            'cognitive_complexity': cognitive,
        }

    def generate_research_report(
        self,
        errors: List[ErrorRecord],
        model_name: str
    ) -> Dict:
        """
        Generate comprehensive research report comparing to baselines.
        """
        # Baseline comparison
        baseline_comp = self.baseline_comparer.compare_to_mmlu_pro_baseline(
            errors, model_name
        )

        # Cognitive complexity distribution
        cognitive_dist = Counter()
        for error in errors:
            cog = self.cognitive_analyzer.classify_cognitive_level(
                error.question_text, error.domain
            )
            cognitive_dist[cog.cognitive_level] += 1

        # Error layer distribution
        layer_dist = Counter()
        for error in errors:
            layer = self.hierarchical_analyzer.attribute_to_layer(error)
            layer_dist[layer] += 1

        return {
            'model_name': model_name,
            'total_errors': len(errors),

            'baseline_comparison': baseline_comp,

            'error_layer_distribution': {
                layer.value: count
                for layer, count in layer_dist.items()
            },

            'cognitive_complexity_distribution': {
                level.name: count
                for level, count in cognitive_dist.items()
            },

            'comparison_to_gpt4o': {
                'similar': baseline_comp.similar_to_gpt4o if baseline_comp else False,
                'deviations': baseline_comp.deviation_from_baseline if baseline_comp else {}
            },

            'key_findings': self._generate_key_findings(
                errors, baseline_comp, cognitive_dist, layer_dist
            )
        }

    def _generate_key_findings(
        self,
        errors: List[ErrorRecord],
        baseline_comp: BaselineComparison,
        cognitive_dist: Counter,
        layer_dist: Counter
    ) -> List[str]:
        """Generate human-readable key findings"""
        findings = []

        if baseline_comp:
            # Compare to GPT-4o
            if baseline_comp.similar_to_gpt4o:
                findings.append(f"{baseline_comp.model_name} shows similar error profile to GPT-4o")
            else:
                # Find biggest deviation
                max_dev = max(baseline_comp.deviation_from_baseline.items(),
                             key=lambda x: abs(x[1]))
                findings.append(
                    f"{baseline_comp.model_name} differs from GPT-4o: "
                    f"{abs(max_dev[1]):.1f}% {'more' if max_dev[1] > 0 else 'fewer'} "
                    f"{max_dev[0]} errors"
                )

        # Cognitive complexity findings
        if cognitive_dist:
            hardest_level = max(cognitive_dist.items(), key=lambda x: x[1])
            findings.append(
                f"Most errors occur at {hardest_level[0].name} level "
                f"({hardest_level[1]} errors, {hardest_level[1]/len(errors)*100:.1f}%)"
            )

        # Domain findings
        domain_dist = Counter(e.domain for e in errors)
        if domain_dist:
            weakest_domain = max(domain_dist.items(), key=lambda x: x[1])
            findings.append(
                f"Weakest domain: {weakest_domain[0]} "
                f"({weakest_domain[1]} errors)"
            )

        return findings
