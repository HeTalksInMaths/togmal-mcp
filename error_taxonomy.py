"""
Hierarchical Error Taxonomy System for LLM Analysis

This module provides tools to analyze MMLU-Pro errors and build a taxonomy
of conceptual mistakes that LLMs make.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from collections import Counter, defaultdict
from enum import Enum
import numpy as np
import json
from pathlib import Path
import re


# ============================================================================
# Error Taxonomy Definition
# ============================================================================

class ErrorCategory(Enum):
    """Level 1: High-level error categories"""
    KNOWLEDGE_DEFICIT = "knowledge_deficit"
    REASONING_FAILURE = "reasoning_failure"
    COMPREHENSION_ERROR = "comprehension_error"
    FORMAT_ERROR = "format_error"
    SYSTEMATIC_BIAS = "systematic_bias"
    UNKNOWN = "unknown"


class ErrorSubtype(Enum):
    """Level 2: Detailed error subtypes"""
    # Knowledge Deficits (1.x)
    FACTUAL_GAP = "factual_gap"
    DOMAIN_BLIND_SPOT = "domain_blind_spot"
    OUTDATED_INFO = "outdated_info"
    MISCONCEPTION = "misconception"

    # Reasoning Failures (2.x)
    MULTI_STEP_REASONING = "multi_step_reasoning"
    COUNTERFACTUAL_REASONING = "counterfactual_reasoning"
    QUANTITATIVE_REASONING = "quantitative_reasoning"
    CAUSAL_REASONING = "causal_reasoning"
    ANALOGICAL_REASONING = "analogical_reasoning"

    # Comprehension Errors (3.x)
    NEGATION_BLINDNESS = "negation_blindness"
    QUALIFIER_CONFUSION = "qualifier_confusion"
    CONTEXT_NEGLECT = "context_neglect"
    AMBIGUITY_MISHANDLING = "ambiguity_mishandling"

    # Format/Parsing Errors (4.x)
    OUTPUT_FORMAT = "output_format"
    CHOICE_EXTRACTION = "choice_extraction"
    REFUSAL_ERROR = "refusal_error"

    # Systematic Biases (5.x)
    POSITION_BIAS = "position_bias"
    LENGTH_BIAS = "length_bias"
    CONFIDENCE_MISCALIBRATION = "confidence_miscalibration"
    DOMAIN_TRANSFER_FAILURE = "domain_transfer_failure"

    UNKNOWN = "unknown"


# Mapping from subtypes to categories
SUBTYPE_TO_CATEGORY = {
    # Knowledge Deficits
    ErrorSubtype.FACTUAL_GAP: ErrorCategory.KNOWLEDGE_DEFICIT,
    ErrorSubtype.DOMAIN_BLIND_SPOT: ErrorCategory.KNOWLEDGE_DEFICIT,
    ErrorSubtype.OUTDATED_INFO: ErrorCategory.KNOWLEDGE_DEFICIT,
    ErrorSubtype.MISCONCEPTION: ErrorCategory.KNOWLEDGE_DEFICIT,

    # Reasoning Failures
    ErrorSubtype.MULTI_STEP_REASONING: ErrorCategory.REASONING_FAILURE,
    ErrorSubtype.COUNTERFACTUAL_REASONING: ErrorCategory.REASONING_FAILURE,
    ErrorSubtype.QUANTITATIVE_REASONING: ErrorCategory.REASONING_FAILURE,
    ErrorSubtype.CAUSAL_REASONING: ErrorCategory.REASONING_FAILURE,
    ErrorSubtype.ANALOGICAL_REASONING: ErrorCategory.REASONING_FAILURE,

    # Comprehension Errors
    ErrorSubtype.NEGATION_BLINDNESS: ErrorCategory.COMPREHENSION_ERROR,
    ErrorSubtype.QUALIFIER_CONFUSION: ErrorCategory.COMPREHENSION_ERROR,
    ErrorSubtype.CONTEXT_NEGLECT: ErrorCategory.COMPREHENSION_ERROR,
    ErrorSubtype.AMBIGUITY_MISHANDLING: ErrorCategory.COMPREHENSION_ERROR,

    # Format Errors
    ErrorSubtype.OUTPUT_FORMAT: ErrorCategory.FORMAT_ERROR,
    ErrorSubtype.CHOICE_EXTRACTION: ErrorCategory.FORMAT_ERROR,
    ErrorSubtype.REFUSAL_ERROR: ErrorCategory.FORMAT_ERROR,

    # Systematic Biases
    ErrorSubtype.POSITION_BIAS: ErrorCategory.SYSTEMATIC_BIAS,
    ErrorSubtype.LENGTH_BIAS: ErrorCategory.SYSTEMATIC_BIAS,
    ErrorSubtype.CONFIDENCE_MISCALIBRATION: ErrorCategory.SYSTEMATIC_BIAS,
    ErrorSubtype.DOMAIN_TRANSFER_FAILURE: ErrorCategory.SYSTEMATIC_BIAS,
}


@dataclass
class ErrorRecord:
    """Individual error instance with full context"""
    question_id: str
    model_name: str
    correct_answer: str
    model_answer: str
    is_correct: bool

    # Question metadata
    question_text: str
    choices: List[str]
    domain: str
    difficulty_score: float

    # Error classification (populated during analysis)
    error_category: Optional[ErrorCategory] = None
    error_subtype: Optional[ErrorSubtype] = None
    error_patterns: List[str] = field(default_factory=list)
    confidence_score: float = 0.0

    # Embedding for clustering (populated during analysis)
    question_embedding: Optional[np.ndarray] = None

    # Additional analysis fields
    other_models_failed: List[str] = field(default_factory=list)
    consensus_wrong_answer: Optional[str] = None
    root_cause_explanation: str = ""


@dataclass
class ErrorCluster:
    """Discovered pattern of related errors"""
    cluster_id: int
    size: int
    error_records: List[ErrorRecord]

    # Cluster characteristics
    common_domains: Dict[str, int]
    avg_difficulty: float
    affected_models: Set[str]

    # Pattern analysis
    common_keywords: List[Tuple[str, float]]  # (keyword, tfidf_score)
    sample_questions: List[str]
    dominant_error_type: Optional[ErrorSubtype] = None

    # Interpretability
    cluster_name: str = ""
    cluster_description: str = ""


@dataclass
class ModelErrorProfile:
    """Error profile for a specific model"""
    model_name: str
    total_questions: int
    total_errors: int
    error_rate: float

    # Breakdown by category
    errors_by_category: Dict[ErrorCategory, int]
    errors_by_subtype: Dict[ErrorSubtype, int]
    errors_by_domain: Dict[str, int]

    # Strengths and weaknesses
    strongest_categories: List[ErrorCategory]
    weakest_categories: List[ErrorCategory]

    # Comparative metrics
    relative_performance: Dict[str, float] = field(default_factory=dict)


@dataclass
class ErrorConsensusAnalysis:
    """Analysis of multi-model agreement on errors"""
    question_id: str
    question_text: str
    correct_answer: str

    num_models_tested: int
    num_models_failed: int
    models_failed: List[str]

    # Consensus metrics
    wrong_answer_distribution: Dict[str, int]  # answer -> count
    consensus_score: float  # 0-1, how much models agree on wrong answer
    most_common_wrong_answer: str

    # Interpretation
    is_systematic_error: bool  # All models made same mistake
    is_ambiguous_question: bool  # Models disagree on answer
    likely_cause: str = ""


# ============================================================================
# Rule-Based Error Detection
# ============================================================================

class ErrorDetector:
    """Rule-based error type detection"""

    # Keywords for different error patterns
    NEGATION_KEYWORDS = [
        'not', 'never', 'except', 'least', 'cannot', 'won\'t',
        'neither', 'nor', 'without', 'exclude', 'excluding'
    ]

    QUALIFIER_KEYWORDS = [
        'always', 'sometimes', 'often', 'rarely', 'never',
        'all', 'most', 'some', 'few', 'none',
        'must', 'should', 'may', 'might', 'can'
    ]

    COUNTERFACTUAL_KEYWORDS = [
        'if', 'suppose', 'assume', 'hypothetical', 'would',
        'could', 'imagine', 'what if', 'in case', 'assuming'
    ]

    CAUSAL_KEYWORDS = [
        'because', 'therefore', 'thus', 'hence', 'causes',
        'results in', 'leads to', 'due to', 'reason', 'why'
    ]

    QUANTITATIVE_PATTERNS = [
        r'\d+', r'calculate', r'compute', r'how many',
        r'percent', r'ratio', r'proportion', r'average',
        r'sum', r'difference', r'product', r'quotient'
    ]

    @staticmethod
    def detect_negation_blindness(question_text: str) -> bool:
        """Check if question contains negation that might be missed"""
        text_lower = question_text.lower()
        return any(kw in text_lower for kw in ErrorDetector.NEGATION_KEYWORDS)

    @staticmethod
    def detect_qualifier_confusion(question_text: str) -> bool:
        """Check if question has qualifiers that require careful attention"""
        text_lower = question_text.lower()
        return any(kw in text_lower for kw in ErrorDetector.QUALIFIER_KEYWORDS)

    @staticmethod
    def detect_counterfactual_reasoning(question_text: str) -> bool:
        """Check if question involves hypothetical scenarios"""
        text_lower = question_text.lower()
        return any(kw in text_lower for kw in ErrorDetector.COUNTERFACTUAL_KEYWORDS)

    @staticmethod
    def detect_causal_reasoning(question_text: str) -> bool:
        """Check if question involves causal relationships"""
        text_lower = question_text.lower()
        return any(kw in text_lower for kw in ErrorDetector.CAUSAL_KEYWORDS)

    @staticmethod
    def detect_quantitative_reasoning(question_text: str) -> bool:
        """Check if question involves calculations or numbers"""
        text_lower = question_text.lower()
        for pattern in ErrorDetector.QUANTITATIVE_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    @staticmethod
    def detect_multi_step_reasoning(question_text: str) -> bool:
        """
        Heuristic: questions with multiple sentences or conjunctions
        often require multi-step reasoning
        """
        # Count sentences
        sentences = re.split(r'[.!?]+', question_text)
        if len(sentences) >= 3:
            return True

        # Check for conjunctions indicating multiple steps
        conjunctions = ['and then', 'after', 'before', 'first', 'second',
                       'next', 'finally', 'subsequently']
        text_lower = question_text.lower()
        return any(conj in text_lower for conj in conjunctions)

    @classmethod
    def classify_error(cls, error: ErrorRecord) -> ErrorRecord:
        """
        Apply rule-based classification to an error.
        Returns updated error record with detected patterns.
        """
        question_text = error.question_text
        patterns = []

        # Run detection rules
        if cls.detect_negation_blindness(question_text):
            patterns.append('contains_negation')
            if not error.error_subtype:
                error.error_subtype = ErrorSubtype.NEGATION_BLINDNESS

        if cls.detect_qualifier_confusion(question_text):
            patterns.append('contains_qualifiers')
            if not error.error_subtype:
                error.error_subtype = ErrorSubtype.QUALIFIER_CONFUSION

        if cls.detect_counterfactual_reasoning(question_text):
            patterns.append('counterfactual')
            if not error.error_subtype:
                error.error_subtype = ErrorSubtype.COUNTERFACTUAL_REASONING

        if cls.detect_causal_reasoning(question_text):
            patterns.append('causal')
            if not error.error_subtype:
                error.error_subtype = ErrorSubtype.CAUSAL_REASONING

        if cls.detect_quantitative_reasoning(question_text):
            patterns.append('quantitative')
            if not error.error_subtype:
                error.error_subtype = ErrorSubtype.QUANTITATIVE_REASONING

        if cls.detect_multi_step_reasoning(question_text):
            patterns.append('multi_step')
            if not error.error_subtype:
                error.error_subtype = ErrorSubtype.MULTI_STEP_REASONING

        # Check for position bias (model always picks A or similar)
        if error.model_answer in ['A', 'B', 'C', 'D', 'E']:
            patterns.append(f'answered_{error.model_answer}')

        # Check for length bias
        if error.choices:
            choice_lengths = [len(c) for c in error.choices]
            answer_idx = ord(error.model_answer) - ord('A')
            if 0 <= answer_idx < len(choice_lengths):
                answer_length = choice_lengths[answer_idx]
                if answer_length == max(choice_lengths):
                    patterns.append('chose_longest')
                elif answer_length == min(choice_lengths):
                    patterns.append('chose_shortest')

        error.error_patterns.extend(patterns)

        # Set category from subtype if available
        if error.error_subtype and not error.error_category:
            error.error_category = SUBTYPE_TO_CATEGORY.get(
                error.error_subtype,
                ErrorCategory.UNKNOWN
            )

        return error


# ============================================================================
# Error Analysis Pipeline
# ============================================================================

class ErrorAnalyzer:
    """Main error analysis and taxonomy building system"""

    def __init__(self, vector_db=None):
        self.vector_db = vector_db
        self.errors: List[ErrorRecord] = []
        self.clusters: List[ErrorCluster] = []
        self.model_profiles: Dict[str, ModelErrorProfile] = {}

    def load_errors_from_benchmark_data(self, data_path: str) -> int:
        """
        Load errors from benchmark results JSON.

        Expected format:
        {
            "question_id": "...",
            "question_text": "...",
            "correct_answer": "A",
            "choices": [...],
            "domain": "law",
            "model_results": {
                "model1": 0,  # 0 = incorrect
                "model2": 1   # 1 = correct
            },
            "success_rate": 0.5,
            "difficulty_score": 0.5
        }
        """
        with open(data_path, 'r') as f:
            data = json.load(f)

        errors_loaded = 0

        for item in data:
            question_id = item['question_id']
            question_text = item['question_text']
            correct_answer = item['correct_answer']
            choices = item.get('choices', [])
            domain = item.get('domain', 'unknown')
            difficulty_score = item.get('difficulty_score', 0.5)

            model_results = item.get('model_results', {})

            for model_name, result in model_results.items():
                is_correct = bool(result)

                if not is_correct:  # Only collect errors
                    # We need the actual wrong answer - for now use placeholder
                    # This should be populated from actual model outputs
                    model_answer = "UNKNOWN"

                    error = ErrorRecord(
                        question_id=question_id,
                        model_name=model_name,
                        correct_answer=correct_answer,
                        model_answer=model_answer,
                        is_correct=False,
                        question_text=question_text,
                        choices=choices,
                        domain=domain,
                        difficulty_score=difficulty_score
                    )

                    self.errors.append(error)
                    errors_loaded += 1

        return errors_loaded

    def classify_errors(self) -> None:
        """Apply rule-based classification to all errors"""
        for i, error in enumerate(self.errors):
            self.errors[i] = ErrorDetector.classify_error(error)

    def analyze_consensus(self, question_id: str) -> Optional[ErrorConsensusAnalysis]:
        """
        Analyze how models agree/disagree on errors for a specific question.
        """
        # Get all errors for this question
        question_errors = [e for e in self.errors if e.question_id == question_id]

        if len(question_errors) == 0:
            return None

        # Get question details from first error
        first_error = question_errors[0]

        # Count wrong answers
        wrong_answers = [e.model_answer for e in question_errors
                        if e.model_answer != "UNKNOWN"]

        if not wrong_answers:
            return None

        answer_counts = Counter(wrong_answers)
        most_common = answer_counts.most_common(1)[0][0]
        consensus_score = answer_counts[most_common] / len(wrong_answers)

        # Determine if systematic or ambiguous
        is_systematic = consensus_score >= 0.7
        is_ambiguous = consensus_score < 0.4

        return ErrorConsensusAnalysis(
            question_id=question_id,
            question_text=first_error.question_text,
            correct_answer=first_error.correct_answer,
            num_models_tested=len(set(e.model_name for e in self.errors
                                     if e.question_id == question_id)),
            num_models_failed=len(question_errors),
            models_failed=[e.model_name for e in question_errors],
            wrong_answer_distribution=dict(answer_counts),
            consensus_score=consensus_score,
            most_common_wrong_answer=most_common,
            is_systematic_error=is_systematic,
            is_ambiguous_question=is_ambiguous,
            likely_cause=(
                f"Systematic error - {consensus_score*100:.0f}% chose {most_common}"
                if is_systematic else
                f"Ambiguous question - answers spread across {len(answer_counts)} choices"
            )
        )

    def build_model_profile(self, model_name: str) -> ModelErrorProfile:
        """Build error profile for a specific model"""
        model_errors = [e for e in self.errors if e.model_name == model_name]

        # Count total questions this model was tested on
        # (for now, assume all errors are from same question set)
        total_questions = len(set(e.question_id for e in self.errors))

        # Count by category
        errors_by_category = defaultdict(int)
        for error in model_errors:
            if error.error_category:
                errors_by_category[error.error_category] += 1

        # Count by subtype
        errors_by_subtype = defaultdict(int)
        for error in model_errors:
            if error.error_subtype:
                errors_by_subtype[error.error_subtype] += 1

        # Count by domain
        errors_by_domain = Counter(e.domain for e in model_errors)

        # Find strengths (fewest errors) and weaknesses (most errors)
        sorted_categories = sorted(
            errors_by_category.items(),
            key=lambda x: x[1]
        )

        strongest = [cat for cat, _ in sorted_categories[:2]]
        weakest = [cat for cat, _ in sorted_categories[-2:]]

        profile = ModelErrorProfile(
            model_name=model_name,
            total_questions=total_questions,
            total_errors=len(model_errors),
            error_rate=len(model_errors) / total_questions if total_questions > 0 else 0,
            errors_by_category=dict(errors_by_category),
            errors_by_subtype=dict(errors_by_subtype),
            errors_by_domain=dict(errors_by_domain),
            strongest_categories=strongest,
            weakest_categories=weakest
        )

        self.model_profiles[model_name] = profile
        return profile

    def generate_taxonomy_tree(self) -> Dict:
        """
        Generate hierarchical tree structure of all errors.
        Suitable for visualization with D3.js or similar.
        """
        tree = {
            'name': 'All LLM Errors',
            'value': len(self.errors),
            'children': []
        }

        # Group by category
        for category in ErrorCategory:
            cat_errors = [e for e in self.errors
                         if e.error_category == category]

            if not cat_errors:
                continue

            category_node = {
                'name': category.value.replace('_', ' ').title(),
                'value': len(cat_errors),
                'percentage': len(cat_errors) / len(self.errors) * 100,
                'children': []
            }

            # Group by subtype within category
            subtypes_in_category = [
                st for st, cat in SUBTYPE_TO_CATEGORY.items()
                if cat == category
            ]

            for subtype in subtypes_in_category:
                sub_errors = [e for e in cat_errors
                             if e.error_subtype == subtype]

                if not sub_errors:
                    continue

                subtype_node = {
                    'name': subtype.value.replace('_', ' ').title(),
                    'value': len(sub_errors),
                    'percentage': len(sub_errors) / len(cat_errors) * 100,
                    'examples': [
                        {
                            'question_id': e.question_id,
                            'domain': e.domain,
                            'model': e.model_name
                        }
                        for e in sub_errors[:3]
                    ]
                }

                category_node['children'].append(subtype_node)

            tree['children'].append(category_node)

        return tree

    def get_error_summary_stats(self) -> Dict:
        """Get summary statistics across all errors"""
        total_errors = len(self.errors)

        if total_errors == 0:
            return {}

        return {
            'total_errors': total_errors,
            'unique_questions': len(set(e.question_id for e in self.errors)),
            'unique_models': len(set(e.model_name for e in self.errors)),
            'domains': dict(Counter(e.domain for e in self.errors)),

            'by_category': {
                cat.value: len([e for e in self.errors if e.error_category == cat])
                for cat in ErrorCategory
            },

            'avg_difficulty': np.mean([e.difficulty_score for e in self.errors]),

            'classification_coverage': len([e for e in self.errors
                                           if e.error_subtype is not None]) / total_errors,
        }

    def export_results(self, output_dir: str) -> None:
        """Export all analysis results to JSON files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export taxonomy tree
        with open(output_path / 'error_taxonomy_tree.json', 'w') as f:
            json.dump(self.generate_taxonomy_tree(), f, indent=2)

        # Export summary stats
        with open(output_path / 'error_summary.json', 'w') as f:
            json.dump(self.get_error_summary_stats(), f, indent=2)

        # Export model profiles
        profiles_data = {
            model: {
                'total_errors': profile.total_errors,
                'error_rate': profile.error_rate,
                'errors_by_category': {
                    cat.value: count
                    for cat, count in profile.errors_by_category.items()
                },
                'errors_by_domain': profile.errors_by_domain,
                'strongest_categories': [c.value for c in profile.strongest_categories],
                'weakest_categories': [c.value for c in profile.weakest_categories]
            }
            for model, profile in self.model_profiles.items()
        }

        with open(output_path / 'model_profiles.json', 'w') as f:
            json.dump(profiles_data, f, indent=2)

        print(f"Results exported to {output_path}")
