"""
MT-Bench LLM-Based Error Classifier

This module extends the basic error analyzer with LLM-based error classification.
Instead of using heuristics, it uses an LLM (Claude, GPT-4, etc.) to deeply analyze
conceptual errors made by weaker models.

This is the key innovation: leveraging AI to understand AI failures.
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import anthropic
from mt_bench_error_analyzer import MTBenchErrorAnalyzer, ErrorPattern, MTBenchQuestion


@dataclass
class DetailedErrorAnalysis:
    """Detailed error analysis with LLM reasoning"""
    error_pattern: ErrorPattern
    error_category: str
    error_subcategory: str
    detailed_explanation: str
    specific_mistake: str
    why_winning_response_better: str
    lesson_learned: str
    severity: str  # 'critical', 'major', 'minor'


class LLMErrorClassifier:
    """
    Uses an LLM to perform sophisticated error analysis on MT-Bench responses.

    This classifier can identify subtle conceptual errors that rule-based systems miss,
    such as:
    - Subtle logical fallacies
    - Implicit bias or inappropriate framing
    - Missing context or nuance
    - Factual errors that require domain knowledge
    - Creative failures in open-ended tasks
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the LLM-based classifier.

        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            model: Claude model to use for classification
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model

        # Enhanced error taxonomy with subcategories
        self.error_taxonomy = {
            'factual': {
                'hallucination': 'Made up information presented as fact',
                'outdated': 'Information that is outdated or no longer accurate',
                'incorrect': 'Verifiably wrong factual claim',
                'misleading': 'Technically true but misleading or lacking context',
            },
            'reasoning': {
                'logical_fallacy': 'Contains a logical fallacy (ad hominem, strawman, etc.)',
                'non_sequitur': 'Conclusion does not follow from premises',
                'circular_reasoning': 'Argument assumes what it is trying to prove',
                'false_dichotomy': 'Presents false either/or choice',
                'incomplete_analysis': 'Fails to consider important factors',
            },
            'instruction_following': {
                'missed_constraint': 'Did not follow a specific constraint',
                'partial_completion': 'Only completed part of the task',
                'wrong_format': 'Used wrong format or structure',
                'tone_mismatch': 'Wrong tone for the requested style',
            },
            'coherence': {
                'self_contradiction': 'Contradicts earlier statements',
                'inconsistent_logic': 'Logic inconsistent across turns',
                'topic_drift': 'Strays from the topic',
                'unclear': 'Response is confusing or ambiguous',
            },
            'creativity': {
                'generic': 'Response is generic and uninteresting',
                'low_effort': 'Minimal creativity or engagement',
                'inappropriate_style': 'Creative style does not match task',
                'missing_details': 'Lacks vivid details or examples',
            },
            'mathematical': {
                'calculation_error': 'Arithmetic or computational error',
                'wrong_formula': 'Used incorrect formula or method',
                'unit_error': 'Incorrect units or conversions',
                'conceptual_error': 'Misunderstood the mathematical concept',
            },
            'coding': {
                'syntax_error': 'Code has syntax errors',
                'logic_bug': 'Code has logical bugs',
                'inefficient': 'Code works but is inefficient',
                'poor_practices': 'Violates coding best practices',
                'incomplete': 'Code does not fully solve the problem',
            },
            'safety': {
                'harmful': 'Could cause harm if followed',
                'biased': 'Contains problematic bias',
                'inappropriate': 'Inappropriate for the context',
                'privacy': 'Privacy or security concerns',
            },
            'understanding': {
                'misunderstood_question': 'Misunderstood what was being asked',
                'missed_context': 'Missed important context from previous turn',
                'wrong_scope': 'Answered different scope than requested',
            },
        }

    def analyze_error_with_llm(
        self,
        question: MTBenchQuestion,
        error_pattern: ErrorPattern
    ) -> DetailedErrorAnalysis:
        """
        Use an LLM to deeply analyze a conceptual error.

        Args:
            question: The MT-Bench question
            error_pattern: The error pattern to analyze

        Returns:
            DetailedErrorAnalysis with LLM insights
        """
        # Construct the analysis prompt
        prompt = self._construct_analysis_prompt(question, error_pattern)

        # Call Claude for analysis
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for more analytical responses
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            analysis_text = message.content[0].text

            # Parse the LLM response
            detailed_analysis = self._parse_llm_response(analysis_text, error_pattern)

            return detailed_analysis

        except Exception as e:
            print(f"Error calling LLM API: {e}")
            # Return a fallback analysis
            return DetailedErrorAnalysis(
                error_pattern=error_pattern,
                error_category='unknown',
                error_subcategory='api_error',
                detailed_explanation=f"Error during LLM analysis: {str(e)}",
                specific_mistake="Could not analyze",
                why_winning_response_better="Could not analyze",
                lesson_learned="Could not analyze",
                severity='unknown'
            )

    def _construct_analysis_prompt(
        self,
        question: MTBenchQuestion,
        error_pattern: ErrorPattern
    ) -> str:
        """Construct the prompt for LLM error analysis"""
        question_text = question.turns[error_pattern.turn - 1]

        # Include previous turn context if this is turn 2
        context = ""
        if error_pattern.turn == 2:
            context = f"\nPrevious question (Turn 1): {question.turns[0]}\n"

        prompt = f"""You are an expert at analyzing language model failures. A human judge compared two AI responses and strongly preferred one over the other. Your task is to deeply analyze WHY the losing model failed and what conceptual error it made.

**Category**: {question.category}

**Question (Turn {error_pattern.turn})**: {question_text}
{context}
**Losing Model ({error_pattern.losing_model}) Response**:
{error_pattern.losing_response}

**Winning Model ({error_pattern.winning_model}) Response**:
{error_pattern.winning_response}

Please analyze the conceptual error made by the losing model and provide your analysis in the following JSON format:

{{
  "error_category": "one of: factual, reasoning, instruction_following, coherence, creativity, mathematical, coding, safety, understanding",
  "error_subcategory": "specific type of error within the category",
  "detailed_explanation": "A detailed explanation of what went wrong conceptually",
  "specific_mistake": "The specific mistake or flaw in the losing response",
  "why_winning_response_better": "Why the winning response succeeded where the losing one failed",
  "lesson_learned": "What this tells us about the losing model's weaknesses",
  "severity": "one of: critical, major, minor"
}}

Focus on conceptual and qualitative differences, not just length or style. What fundamental mistake did the losing model make?
"""

        return prompt

    def _parse_llm_response(self, response_text: str, error_pattern: ErrorPattern) -> DetailedErrorAnalysis:
        """Parse the LLM's JSON response into a DetailedErrorAnalysis object"""
        try:
            # Extract JSON from the response (it might have markdown code blocks)
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group())
            else:
                response_data = json.loads(response_text)

            return DetailedErrorAnalysis(
                error_pattern=error_pattern,
                error_category=response_data.get('error_category', 'unknown'),
                error_subcategory=response_data.get('error_subcategory', 'unknown'),
                detailed_explanation=response_data.get('detailed_explanation', ''),
                specific_mistake=response_data.get('specific_mistake', ''),
                why_winning_response_better=response_data.get('why_winning_response_better', ''),
                lesson_learned=response_data.get('lesson_learned', ''),
                severity=response_data.get('severity', 'unknown')
            )

        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response was: {response_text[:500]}")

            # Fallback to text parsing
            return DetailedErrorAnalysis(
                error_pattern=error_pattern,
                error_category='unknown',
                error_subcategory='parse_error',
                detailed_explanation=response_text[:1000],
                specific_mistake="Could not parse structured response",
                why_winning_response_better="",
                lesson_learned="",
                severity='unknown'
            )

    def batch_analyze_errors(
        self,
        analyzer: MTBenchErrorAnalyzer,
        limit: Optional[int] = None,
        filter_category: Optional[str] = None,
        filter_model: Optional[str] = None
    ) -> List[DetailedErrorAnalysis]:
        """
        Analyze multiple error patterns using the LLM.

        Args:
            analyzer: MTBenchErrorAnalyzer with loaded error patterns
            limit: Maximum number of errors to analyze
            filter_category: Only analyze errors in this category
            filter_model: Only analyze errors from this model

        Returns:
            List of DetailedErrorAnalysis objects
        """
        error_patterns = analyzer.error_patterns

        # Apply filters
        if filter_category:
            error_patterns = [ep for ep in error_patterns if ep.category == filter_category]

        if filter_model:
            error_patterns = [ep for ep in error_patterns if ep.losing_model == filter_model]

        # Apply limit
        if limit:
            error_patterns = error_patterns[:limit]

        detailed_analyses = []

        print(f"\nAnalyzing {len(error_patterns)} error patterns with LLM...")

        for i, error_pattern in enumerate(error_patterns, 1):
            print(f"  [{i}/{len(error_patterns)}] Analyzing Q{error_pattern.question_id} "
                  f"({error_pattern.category}, {error_pattern.losing_model})...")

            question = analyzer.questions[error_pattern.question_id]
            detailed_analysis = self.analyze_error_with_llm(question, error_pattern)
            detailed_analyses.append(detailed_analysis)

        return detailed_analyses

    def generate_insights_report(
        self,
        detailed_analyses: List[DetailedErrorAnalysis],
        output_file: str
    ) -> None:
        """
        Generate a comprehensive insights report from LLM error analyses.

        Args:
            detailed_analyses: List of detailed error analyses
            output_file: Path to save the report
        """
        # Aggregate insights
        from collections import Counter, defaultdict

        category_counts = Counter(da.error_category for da in detailed_analyses)
        subcategory_counts = Counter(da.error_subcategory for da in detailed_analyses)
        severity_counts = Counter(da.severity for da in detailed_analyses)

        # Model-specific insights
        model_insights = defaultdict(lambda: {
            'total_errors': 0,
            'categories': Counter(),
            'severities': Counter(),
            'examples': []
        })

        for da in detailed_analyses:
            model = da.error_pattern.losing_model
            model_insights[model]['total_errors'] += 1
            model_insights[model]['categories'][da.error_category] += 1
            model_insights[model]['severities'][da.severity] += 1

            if len(model_insights[model]['examples']) < 3:
                model_insights[model]['examples'].append({
                    'question_id': da.error_pattern.question_id,
                    'category': da.error_pattern.category,
                    'error_type': da.error_category,
                    'lesson': da.lesson_learned
                })

        # Build the report
        report = {
            'summary': {
                'total_errors_analyzed': len(detailed_analyses),
                'error_categories': dict(category_counts),
                'error_subcategories': dict(subcategory_counts),
                'severity_distribution': dict(severity_counts),
            },
            'model_insights': {
                model: {
                    'total_errors': data['total_errors'],
                    'top_error_categories': dict(data['categories'].most_common(5)),
                    'severity_distribution': dict(data['severities']),
                    'example_errors': data['examples']
                }
                for model, data in model_insights.items()
            },
            'detailed_analyses': [
                {
                    'question_id': da.error_pattern.question_id,
                    'category': da.error_pattern.category,
                    'turn': da.error_pattern.turn,
                    'losing_model': da.error_pattern.losing_model,
                    'winning_model': da.error_pattern.winning_model,
                    'error_category': da.error_category,
                    'error_subcategory': da.error_subcategory,
                    'specific_mistake': da.specific_mistake,
                    'lesson_learned': da.lesson_learned,
                    'severity': da.severity,
                    'detailed_explanation': da.detailed_explanation,
                }
                for da in detailed_analyses
            ]
        }

        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nInsights report saved to: {output_file}")

        # Print summary
        self._print_insights_summary(report)

    def _print_insights_summary(self, report: Dict) -> None:
        """Print a human-readable summary of the insights"""
        print("\n" + "="*80)
        print("LLM-BASED ERROR ANALYSIS INSIGHTS")
        print("="*80)

        summary = report['summary']
        print(f"\nTotal Errors Analyzed: {summary['total_errors_analyzed']}")

        print("\n--- Error Categories (LLM-Classified) ---")
        for category, count in sorted(summary['error_categories'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / summary['total_errors_analyzed']) * 100
            print(f"  {category:25s}: {count:4d} ({percentage:5.1f}%)")

        print("\n--- Severity Distribution ---")
        for severity, count in sorted(summary['severity_distribution'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / summary['total_errors_analyzed']) * 100
            print(f"  {severity:25s}: {count:4d} ({percentage:5.1f}%)")

        print("\n--- Top Error Subcategories ---")
        top_subcategories = sorted(summary['error_subcategories'].items(), key=lambda x: x[1], reverse=True)[:10]
        for subcategory, count in top_subcategories:
            percentage = (count / summary['total_errors_analyzed']) * 100
            print(f"  {subcategory:25s}: {count:4d} ({percentage:5.1f}%)")

        print("\n--- Model-Specific Insights ---")
        for model, insights in report['model_insights'].items():
            print(f"\n  {model}:")
            print(f"    Total errors: {insights['total_errors']}")
            print(f"    Top weaknesses:")
            for category, count in list(insights['top_error_categories'].items())[:3]:
                print(f"      - {category}: {count}")

            if insights['example_errors']:
                print(f"    Key lesson learned:")
                print(f"      \"{insights['example_errors'][0]['lesson']}\"")

        print("\n" + "="*80)


def main():
    """Demonstration of LLM-based error classification"""
    print("MT-Bench LLM-Based Error Classifier")
    print("=" * 80)

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nError: ANTHROPIC_API_KEY environment variable not set.")
        print("Please set your Anthropic API key:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\nOr use the basic analyzer instead: python mt_bench_error_analyzer.py")
        return

    # Load basic analyzer first
    print("\n1. Loading MT-Bench data...")
    analyzer = MTBenchErrorAnalyzer()
    analyzer.load_questions_from_github()

    try:
        analyzer.load_human_judgments_from_huggingface()
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Extract basic error patterns
    print("\n2. Extracting error patterns...")
    lopsided_cases = analyzer.identify_lopsided_preferences(min_preference_strength='strong')
    analyzer.extract_error_patterns(lopsided_cases)

    # Initialize LLM classifier
    print("\n3. Initializing LLM classifier...")
    classifier = LLMErrorClassifier()

    # Analyze a subset with LLM (to save API costs)
    print("\n4. Performing LLM-based deep analysis (analyzing first 10 errors)...")
    detailed_analyses = classifier.batch_analyze_errors(
        analyzer,
        limit=10  # Limit for demonstration
    )

    # Generate insights report
    print("\n5. Generating insights report...")
    classifier.generate_insights_report(
        detailed_analyses,
        "./data/mt_bench/llm_error_insights.json"
    )

    print("\n6. Example detailed analysis:")
    if detailed_analyses:
        da = detailed_analyses[0]
        print(f"\nQuestion ID: {da.error_pattern.question_id} ({da.error_pattern.category})")
        print(f"Models: {da.error_pattern.losing_model} vs {da.error_pattern.winning_model}")
        print(f"\nError: {da.error_category} / {da.error_subcategory} (Severity: {da.severity})")
        print(f"\nSpecific Mistake:\n  {da.specific_mistake}")
        print(f"\nLesson Learned:\n  {da.lesson_learned}")


if __name__ == "__main__":
    main()
