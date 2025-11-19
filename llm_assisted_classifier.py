"""
LLM-Assisted Error Classification

Uses Claude/GPT-4 to provide deep analysis of LLM errors that goes beyond
rule-based detection.
"""

import json
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from error_taxonomy import ErrorRecord, ErrorSubtype, ErrorCategory


@dataclass
class EnhancedErrorAnalysis:
    """
    Deep error analysis from LLM.

    Combines rule-based detection with LLM understanding.
    """
    error_record: ErrorRecord

    # LLM's classification
    llm_error_category: Optional[ErrorCategory] = None
    llm_error_subtype: Optional[ErrorSubtype] = None
    llm_confidence: float = 0.0

    # Deep analysis
    root_cause: str = ""
    distractor_analysis: str = ""
    generalization_assessment: str = ""  # Is this error universal or model-specific?

    # Recommendations
    recommended_interventions: List[str] = field(default_factory=list)
    estimated_intervention_effectiveness: Dict[str, float] = field(default_factory=dict)

    # Additional insights
    similar_error_patterns: List[str] = field(default_factory=list)
    cognitive_complexity_level: str = ""

    # Agreement with rule-based
    agrees_with_rule_based: bool = False
    disagreement_explanation: str = ""


class LLMAssistedClassifier:
    """
    Use LLM to deeply understand error patterns.

    This complements rule-based detection by:
    1. Catching subtle patterns rules miss
    2. Providing natural language explanations
    3. Suggesting interventions
    4. Identifying generalization patterns
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize LLM classifier.

        Args:
            api_key: Anthropic API key (if None, will try environment)
            model: Model to use for classification
        """
        self.model = model
        self.api_key = api_key

        # Try to import anthropic
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            self.available = True
        except ImportError:
            print("Warning: anthropic package not installed. LLM classification unavailable.")
            print("Install with: pip install anthropic")
            self.available = False

    def _build_taxonomy_description(self) -> str:
        """Build human-readable taxonomy for LLM"""
        taxonomy = """
## Error Type Taxonomy

### Level 1: Error Categories

1. **Knowledge Deficits** - Missing or incorrect factual knowledge
   - Factual Gap: Missing specific facts (dates, names, formulas)
   - Domain Blind Spot: Weak in entire subject areas
   - Outdated Information: Training data cutoff issues
   - Misconception: Active incorrect beliefs

2. **Reasoning Failures** - Logical/inferential errors despite having knowledge
   - Multi-Step Reasoning: Breaks down in chains of logic
   - Counterfactual Reasoning: Struggles with hypotheticals
   - Quantitative Reasoning: Math/calculation errors
   - Causal Reasoning: Confuses correlation/causation
   - Analogical Reasoning: Poor transfer across domains

3. **Comprehension Errors** - Misunderstanding question or context
   - Negation Blindness: Misses "not", "except", "least"
   - Qualifier Confusion: Ignores "always", "sometimes", "never"
   - Context Neglect: Misses critical contextual clues
   - Ambiguity Mishandling: Wrong interpretation of ambiguous text

4. **Execution Errors** - Technical failures in output generation
   - Output Format: Generates invalid response format
   - Choice Extraction: Picks option not in choices
   - Computational Error: Pure calculation mistakes

5. **Systematic Biases** - Consistent patterns across question types
   - Position Bias: Prefers certain answer positions (A/B/C/D)
   - Length Bias: Prefers longer/shorter options
   - Confidence Miscalibration: Overconfident on wrong answers
   - Domain Transfer Failure: Applies wrong domain knowledge
"""
        return taxonomy

    async def classify_error_async(
        self,
        error: ErrorRecord,
        include_rule_based: bool = True
    ) -> EnhancedErrorAnalysis:
        """
        Classify error using LLM (async version).

        Args:
            error: Error to analyze
            include_rule_based: Include rule-based classification for comparison
        """
        if not self.available:
            return EnhancedErrorAnalysis(
                error_record=error,
                root_cause="LLM classification unavailable - anthropic package not installed"
            )

        # Build prompt
        prompt = self._build_analysis_prompt(error, include_rule_based)

        try:
            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3  # Lower temperature for consistent classification
            )

            # Parse response
            analysis_text = response.content[0].text

            # Try to parse as JSON
            try:
                analysis_dict = json.loads(analysis_text)
            except json.JSONDecodeError:
                # If not JSON, extract manually
                analysis_dict = self._parse_text_response(analysis_text)

            # Build enhanced analysis
            enhanced = self._build_enhanced_analysis(error, analysis_dict, include_rule_based)

            return enhanced

        except Exception as e:
            print(f"Error during LLM classification: {e}")
            return EnhancedErrorAnalysis(
                error_record=error,
                root_cause=f"LLM classification failed: {str(e)}"
            )

    def classify_error(
        self,
        error: ErrorRecord,
        include_rule_based: bool = True
    ) -> EnhancedErrorAnalysis:
        """
        Classify error using LLM (sync version).

        Wrapper around async method for convenience.
        """
        return asyncio.run(self.classify_error_async(error, include_rule_based))

    def _build_analysis_prompt(
        self,
        error: ErrorRecord,
        include_rule_based: bool
    ) -> str:
        """Build prompt for LLM analysis"""

        prompt = f"""Analyze this LLM error in detail.

## Error Context

**Domain**: {error.domain}
**Difficulty Score**: {error.difficulty_score:.2f}

**Question**:
{error.question_text}

**Answer Choices**:
"""
        for i, choice in enumerate(error.choices):
            letter = chr(65 + i)  # A, B, C, ...
            marker = "✓ CORRECT" if letter == error.correct_answer else ""
            marker = f"{marker} ← Model chose this" if letter == error.model_answer else marker
            prompt += f"{letter}. {choice} {marker}\n"

        prompt += f"\n**Correct Answer**: {error.correct_answer}\n"
        prompt += f"**Model Chose**: {error.model_answer}\n"

        if include_rule_based and error.error_subtype:
            prompt += f"\n**Rule-Based Classification**: {error.error_subtype.value}\n"
            if error.error_patterns:
                prompt += f"**Detected Patterns**: {', '.join(error.error_patterns)}\n"

        prompt += "\n" + self._build_taxonomy_description()

        prompt += """

## Analysis Tasks

Please provide a detailed analysis in JSON format with the following fields:

{
  "error_classification": {
    "category": "knowledge_deficit|reasoning_failure|comprehension_error|execution_error|systematic_bias",
    "subtype": "specific_subtype_from_taxonomy",
    "confidence": 0.0-1.0
  },

  "root_cause": "Detailed explanation of WHY this error occurred. What specific knowledge was missing or what reasoning step failed?",

  "distractor_analysis": "Why was the wrong answer attractive? What makes it seem plausible?",

  "generalization": {
    "is_universal": true|false,
    "explanation": "Would most LLMs make this error, or is it model/architecture specific?"
  },

  "interventions": [
    {
      "name": "chain_of_thought|rag|tool_use|rephrasing|etc",
      "description": "How this would help",
      "estimated_effectiveness": 0.0-1.0
    }
  ],

  "cognitive_complexity": "remember|understand|apply|analyze|evaluate|create (Bloom's taxonomy)",

  "similar_patterns": ["List of similar error patterns this resembles"],

  "rule_based_agreement": {
    "agrees": true|false,
    "explanation": "If disagrees with rule-based classification, explain why"
  }
}

Provide thorough, specific analysis based on the question content and domain.
"""

        return prompt

    def _parse_text_response(self, text: str) -> Dict:
        """Parse non-JSON text response (fallback)"""
        # Basic parsing if JSON fails
        return {
            "error_classification": {
                "category": "unknown",
                "subtype": "unknown",
                "confidence": 0.5
            },
            "root_cause": text[:500],  # First 500 chars
            "distractor_analysis": "",
            "generalization": {
                "is_universal": False,
                "explanation": ""
            },
            "interventions": [],
            "cognitive_complexity": "understand",
            "similar_patterns": [],
            "rule_based_agreement": {
                "agrees": True,
                "explanation": ""
            }
        }

    def _build_enhanced_analysis(
        self,
        error: ErrorRecord,
        analysis_dict: Dict,
        include_rule_based: bool
    ) -> EnhancedErrorAnalysis:
        """Build EnhancedErrorAnalysis from LLM response"""

        # Parse error classification
        classification = analysis_dict.get("error_classification", {})

        llm_category = None
        llm_subtype = None

        try:
            category_str = classification.get("category", "")
            for cat in ErrorCategory:
                if cat.value == category_str:
                    llm_category = cat
                    break

            subtype_str = classification.get("subtype", "")
            for sub in ErrorSubtype:
                if sub.value == subtype_str:
                    llm_subtype = sub
                    break
        except:
            pass

        # Parse interventions
        interventions = []
        intervention_effectiveness = {}

        for interv in analysis_dict.get("interventions", []):
            name = interv.get("name", "")
            effectiveness = interv.get("estimated_effectiveness", 0.5)

            interventions.append(f"{name}: {interv.get('description', '')}")
            intervention_effectiveness[name] = effectiveness

        # Check agreement with rule-based
        agreement = analysis_dict.get("rule_based_agreement", {})
        agrees = agreement.get("agrees", True)
        disagreement_explanation = agreement.get("explanation", "")

        return EnhancedErrorAnalysis(
            error_record=error,
            llm_error_category=llm_category,
            llm_error_subtype=llm_subtype,
            llm_confidence=classification.get("confidence", 0.0),
            root_cause=analysis_dict.get("root_cause", ""),
            distractor_analysis=analysis_dict.get("distractor_analysis", ""),
            generalization_assessment=analysis_dict.get("generalization", {}).get("explanation", ""),
            recommended_interventions=interventions,
            estimated_intervention_effectiveness=intervention_effectiveness,
            similar_error_patterns=analysis_dict.get("similar_patterns", []),
            cognitive_complexity_level=analysis_dict.get("cognitive_complexity", ""),
            agrees_with_rule_based=agrees,
            disagreement_explanation=disagreement_explanation
        )

    async def classify_batch_async(
        self,
        errors: List[ErrorRecord],
        max_concurrent: int = 5
    ) -> List[EnhancedErrorAnalysis]:
        """
        Classify multiple errors concurrently.

        Args:
            errors: List of errors to classify
            max_concurrent: Maximum concurrent API calls
        """
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def classify_with_semaphore(error):
            async with semaphore:
                return await self.classify_error_async(error)

        # Run classifications concurrently
        tasks = [classify_with_semaphore(error) for error in errors]
        results = await asyncio.gather(*tasks)

        return results

    def classify_batch(
        self,
        errors: List[ErrorRecord],
        max_concurrent: int = 5
    ) -> List[EnhancedErrorAnalysis]:
        """
        Classify multiple errors (sync version).
        """
        return asyncio.run(self.classify_batch_async(errors, max_concurrent))

    def compare_with_rule_based(
        self,
        enhanced_analyses: List[EnhancedErrorAnalysis]
    ) -> Dict:
        """
        Compare LLM classifications with rule-based.

        Returns agreement statistics and interesting disagreements.
        """
        total = len(enhanced_analyses)
        agrees = sum(1 for a in enhanced_analyses if a.agrees_with_rule_based)

        agreement_rate = agrees / total if total > 0 else 0

        # Find interesting disagreements
        disagreements = [
            {
                'question_id': a.error_record.question_id,
                'rule_based': a.error_record.error_subtype.value if a.error_record.error_subtype else None,
                'llm_classification': a.llm_error_subtype.value if a.llm_error_subtype else None,
                'explanation': a.disagreement_explanation,
                'llm_confidence': a.llm_confidence
            }
            for a in enhanced_analyses
            if not a.agrees_with_rule_based
        ]

        return {
            'agreement_rate': agreement_rate,
            'total_analyzed': total,
            'agreements': agrees,
            'disagreements_count': total - agrees,
            'interesting_disagreements': disagreements[:10],  # Top 10
            'interpretation': (
                'excellent' if agreement_rate > 0.85 else
                'good' if agreement_rate > 0.75 else
                'moderate' if agreement_rate > 0.6 else
                'poor'
            )
        }

    def export_enhanced_analyses(
        self,
        analyses: List[EnhancedErrorAnalysis],
        output_path: str
    ) -> None:
        """Export enhanced analyses to JSON"""
        data = []

        for analysis in analyses:
            data.append({
                'question_id': analysis.error_record.question_id,
                'domain': analysis.error_record.domain,
                'rule_based_classification': analysis.error_record.error_subtype.value if analysis.error_record.error_subtype else None,
                'llm_classification': {
                    'category': analysis.llm_error_category.value if analysis.llm_error_category else None,
                    'subtype': analysis.llm_error_subtype.value if analysis.llm_error_subtype else None,
                    'confidence': analysis.llm_confidence
                },
                'root_cause': analysis.root_cause,
                'distractor_analysis': analysis.distractor_analysis,
                'interventions': analysis.recommended_interventions,
                'cognitive_complexity': analysis.cognitive_complexity_level,
                'agrees_with_rule_based': analysis.agrees_with_rule_based
            })

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Enhanced analyses exported to {output_path}")


# ============================================================================
# Mock Classifier (for testing without API)
# ============================================================================

class MockLLMClassifier(LLMAssistedClassifier):
    """
    Mock classifier for testing without API access.

    Uses heuristics to simulate LLM analysis.
    """

    def __init__(self):
        self.available = True

    async def classify_error_async(
        self,
        error: ErrorRecord,
        include_rule_based: bool = True
    ) -> EnhancedErrorAnalysis:
        """Mock classification"""

        # Use rule-based as baseline
        llm_category = error.error_category
        llm_subtype = error.error_subtype

        # Generate mock analysis
        root_cause = f"Mock analysis: {error.error_subtype.value if error.error_subtype else 'unknown'} error in {error.domain} domain"

        interventions = []
        effectiveness = {}

        if error.error_subtype:
            if "reasoning" in error.error_subtype.value:
                interventions.append("chain_of_thought: Break down reasoning steps")
                effectiveness["chain_of_thought"] = 0.7
            elif "knowledge" in error.error_category.value:
                interventions.append("rag: Retrieve relevant information")
                effectiveness["rag"] = 0.8

        return EnhancedErrorAnalysis(
            error_record=error,
            llm_error_category=llm_category,
            llm_error_subtype=llm_subtype,
            llm_confidence=0.7,
            root_cause=root_cause,
            distractor_analysis=f"Mock: Distractor {error.model_answer} appears plausible",
            generalization_assessment="Mock: Likely affects most models",
            recommended_interventions=interventions,
            estimated_intervention_effectiveness=effectiveness,
            cognitive_complexity_level="apply",
            agrees_with_rule_based=True
        )
