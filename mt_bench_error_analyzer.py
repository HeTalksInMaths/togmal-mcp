"""
MT-Bench Conceptual Error Analyzer

This module analyzes MT-Bench human evaluation data to extract conceptual errors
from weaker models based on lopsided preference judgments.

The core insight: When humans strongly prefer one model over another, the losing model
likely made significant conceptual errors that can be categorized and learned from.
"""

import json
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
from pathlib import Path
import re


@dataclass
class ErrorPattern:
    """Represents a conceptual error pattern found in model responses"""
    error_type: str
    description: str
    question_id: int
    category: str
    losing_model: str
    winning_model: str
    turn: int
    losing_response: str
    winning_response: str
    preference_strength: str  # 'strong', 'moderate', 'weak'


@dataclass
class MTBenchQuestion:
    """Represents an MT-Bench question"""
    question_id: int
    category: str
    turns: List[str]
    reference_answer: Optional[List[str]] = None


class MTBenchErrorAnalyzer:
    """
    Analyzes MT-Bench evaluation data to extract conceptual errors from lopsided preferences.

    This class loads MT-Bench questions and human judgment data, identifies cases where
    one model is strongly preferred over another, and extracts patterns of conceptual
    errors made by the weaker model.
    """

    def __init__(self, data_dir: str = "./data/mt_bench"):
        """
        Initialize the analyzer.

        Args:
            data_dir: Directory to store/load MT-Bench data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.questions: Dict[int, MTBenchQuestion] = {}
        self.human_judgments: List[Dict] = []
        self.error_patterns: List[ErrorPattern] = []

        # Error taxonomy based on common LLM failure modes
        self.error_taxonomy = {
            'factual': 'Incorrect factual information or hallucination',
            'reasoning': 'Logical fallacy or flawed reasoning',
            'instruction_following': 'Failed to follow instructions or constraints',
            'coherence': 'Contradictions or inconsistency across turns',
            'safety': 'Harmful, biased, or inappropriate content',
            'overconfidence': 'Speculation presented as fact',
            'incompleteness': 'Missing key information or partial answer',
            'format': 'Wrong format or structure in response',
            'creativity': 'Lack of creativity or engagement in creative tasks',
            'mathematical': 'Mathematical or computational errors',
            'coding': 'Programming errors or poor code quality',
            'understanding': 'Misunderstanding of the question',
        }

    def load_questions_from_github(self) -> None:
        """Load MT-Bench questions from the FastChat GitHub repository"""
        url = "https://raw.githubusercontent.com/lm-sys/FastChat/main/fastchat/llm_judge/data/mt_bench/question.jsonl"

        print("Downloading MT-Bench questions from GitHub...")
        response = requests.get(url)
        response.raise_for_status()

        questions_file = self.data_dir / "questions.jsonl"
        questions_file.write_text(response.text)

        # Parse questions
        for line in response.text.strip().split('\n'):
            if line.strip():
                q_data = json.loads(line)
                question = MTBenchQuestion(
                    question_id=q_data['question_id'],
                    category=q_data['category'],
                    turns=q_data['turns'],
                    reference_answer=q_data.get('reference')
                )
                self.questions[question.question_id] = question

        print(f"Loaded {len(self.questions)} MT-Bench questions across {len(set(q.category for q in self.questions.values()))} categories")

    def load_human_judgments_from_huggingface(self) -> None:
        """
        Load human judgment data from HuggingFace datasets.

        Note: This requires the 'datasets' library. If not available, users should
        download the data manually from:
        https://huggingface.co/datasets/lmsys/mt_bench_human_judgments
        """
        try:
            from datasets import load_dataset

            print("Downloading human judgments from HuggingFace...")
            dataset = load_dataset("lmsys/mt_bench_human_judgments", split="human")

            self.human_judgments = [dict(example) for example in dataset]

            # Save locally for future use
            judgments_file = self.data_dir / "human_judgments.jsonl"
            with open(judgments_file, 'w') as f:
                for judgment in self.human_judgments:
                    f.write(json.dumps(judgment) + '\n')

            print(f"Loaded {len(self.human_judgments)} human judgments")

        except ImportError:
            print("Warning: 'datasets' library not installed.")
            print("Please install with: pip install datasets")
            print("Or download data manually from: https://huggingface.co/datasets/lmsys/mt_bench_human_judgments")

            # Try to load from local file if it exists
            judgments_file = self.data_dir / "human_judgments.jsonl"
            if judgments_file.exists():
                print(f"Loading from local file: {judgments_file}")
                with open(judgments_file, 'r') as f:
                    self.human_judgments = [json.loads(line) for line in f]
                print(f"Loaded {len(self.human_judgments)} human judgments from local cache")
            else:
                raise FileNotFoundError(
                    f"No local data found at {judgments_file}. "
                    "Please install 'datasets' library or download data manually."
                )

    def identify_lopsided_preferences(self, min_preference_strength: str = 'strong') -> List[Dict]:
        """
        Identify cases where human judges strongly preferred one model over another.

        Args:
            min_preference_strength: Minimum preference strength ('strong', 'moderate', 'weak')

        Returns:
            List of judgment dictionaries with lopsided preferences
        """
        lopsided_cases = []

        strength_thresholds = {
            'strong': lambda w: w in ['model_a', 'model_b'],  # Clear winner
            'moderate': lambda w: w in ['model_a', 'model_b', 'tie_a', 'tie_b'],
            'weak': lambda w: True  # All cases
        }

        threshold_fn = strength_thresholds.get(min_preference_strength, strength_thresholds['strong'])

        for judgment in self.human_judgments:
            winner = judgment.get('winner', '')

            # Identify lopsided preferences (not ties)
            if threshold_fn(winner) and winner != 'tie':
                lopsided_cases.append(judgment)

        print(f"Found {len(lopsided_cases)} lopsided preference cases (strength: {min_preference_strength})")
        return lopsided_cases

    def extract_error_patterns(self, lopsided_cases: List[Dict]) -> List[ErrorPattern]:
        """
        Extract conceptual error patterns from lopsided preference cases.

        Args:
            lopsided_cases: List of judgments with clear preferences

        Returns:
            List of ErrorPattern objects
        """
        error_patterns = []

        for judgment in lopsided_cases:
            question_id = judgment['question_id']
            turn = judgment.get('turn', 1)
            winner = judgment['winner']

            # Determine winning and losing models
            if winner == 'model_a':
                winning_model = judgment['model_a']
                losing_model = judgment['model_b']
                winning_conv = judgment.get('conversation_a', [])
                losing_conv = judgment.get('conversation_b', [])
            elif winner == 'model_b':
                winning_model = judgment['model_b']
                losing_model = judgment['model_a']
                winning_conv = judgment.get('conversation_b', [])
                losing_conv = judgment.get('conversation_a', [])
            else:
                continue  # Skip ties

            # Get question details
            question = self.questions.get(question_id)
            if not question:
                continue

            # Extract responses for the specific turn
            # Conversations have format: [user, assistant, user, assistant, ...]
            # Turn 1 = first assistant response (index 1)
            # Turn 2 = second assistant response (index 3)
            response_idx = (turn - 1) * 2 + 1

            losing_response = ""
            winning_response = ""

            if len(losing_conv) > response_idx:
                losing_response = losing_conv[response_idx].get('content', '')
            if len(winning_conv) > response_idx:
                winning_response = winning_conv[response_idx].get('content', '')

            # Analyze the losing response to categorize the error
            error_type = self._categorize_error(
                question=question,
                losing_response=losing_response,
                winning_response=winning_response,
                turn=turn
            )

            # Determine preference strength
            preference_strength = 'strong' if winner in ['model_a', 'model_b'] else 'moderate'

            error_pattern = ErrorPattern(
                error_type=error_type,
                description=self.error_taxonomy.get(error_type, 'Unknown error type'),
                question_id=question_id,
                category=question.category,
                losing_model=losing_model,
                winning_model=winning_model,
                turn=turn,
                losing_response=losing_response,
                winning_response=winning_response,
                preference_strength=preference_strength
            )

            error_patterns.append(error_pattern)

        self.error_patterns = error_patterns
        print(f"Extracted {len(error_patterns)} error patterns")
        return error_patterns

    def _categorize_error(
        self,
        question: MTBenchQuestion,
        losing_response: str,
        winning_response: str,
        turn: int
    ) -> str:
        """
        Categorize the type of error based on heuristic analysis.

        This uses rule-based heuristics. For production use, you would want to
        use an LLM to perform more sophisticated error classification.

        Args:
            question: The MT-Bench question
            losing_response: The losing model's response
            winning_response: The winning model's response
            turn: Which turn (1 or 2)

        Returns:
            Error type from the taxonomy
        """
        category = question.category
        question_text = question.turns[turn - 1].lower()
        losing_lower = losing_response.lower()
        winning_lower = winning_response.lower()

        # Category-specific error detection
        if category == 'math':
            # Check for mathematical errors
            if any(word in losing_lower for word in ['calculate', 'compute', 'answer is']):
                # If the response attempts calculation but is wrong
                return 'mathematical'

        elif category == 'coding':
            # Check for coding errors
            if 'error' in losing_lower or 'exception' in losing_lower or 'bug' in losing_lower:
                return 'coding'
            if len(losing_response) < len(winning_response) * 0.3:
                return 'incompleteness'

        elif category == 'reasoning':
            # Check for logical errors
            if 'therefore' in losing_lower or 'thus' in losing_lower or 'so' in losing_lower:
                # Contains reasoning but may be flawed
                return 'reasoning'

        # Instruction following checks (works across categories)
        if turn == 2:
            # Second turn often has special constraints
            constraints = [
                ('start every sentence with', 'format'),
                ('rewrite', 'instruction_following'),
                ('rephrase', 'instruction_following'),
                ('fewer than', 'instruction_following'),
                ('without', 'instruction_following'),
                ('only use', 'instruction_following'),
                ('limerick', 'format'),
                ('bullet points', 'format'),
                ('four-word sentences', 'format'),
            ]

            for constraint, error_type in constraints:
                if constraint in question_text:
                    # Check if losing response attempted to follow constraint
                    if turn == 2 and len(losing_response) > 0:
                        return error_type

        # Coherence checks for multi-turn
        if turn == 2:
            # Check if response is too short (might indicate confusion)
            if len(losing_response) < 50:
                return 'incompleteness'

        # Length-based heuristics
        if len(losing_response) < len(winning_response) * 0.5:
            return 'incompleteness'

        # Overconfidence detection
        confidence_words = ['definitely', 'certainly', 'absolutely', 'must be', 'obviously']
        if any(word in losing_lower for word in confidence_words):
            return 'overconfidence'

        # Default based on category
        category_defaults = {
            'writing': 'creativity',
            'roleplay': 'understanding',
            'reasoning': 'reasoning',
            'math': 'mathematical',
            'coding': 'coding',
            'extraction': 'understanding',
            'stem': 'factual',
            'humanities': 'factual',
        }

        return category_defaults.get(category, 'understanding')

    def analyze_error_distribution(self) -> Dict[str, any]:
        """
        Analyze the distribution of errors across models, categories, and error types.

        Returns:
            Dictionary containing various statistics and insights
        """
        if not self.error_patterns:
            print("No error patterns loaded. Run extract_error_patterns() first.")
            return {}

        # Count errors by type
        errors_by_type = Counter(ep.error_type for ep in self.error_patterns)

        # Count errors by model
        errors_by_model = Counter(ep.losing_model for ep in self.error_patterns)

        # Count errors by category
        errors_by_category = Counter(ep.category for ep in self.error_patterns)

        # Model-specific error patterns
        model_error_patterns = defaultdict(lambda: defaultdict(int))
        for ep in self.error_patterns:
            model_error_patterns[ep.losing_model][ep.error_type] += 1

        # Category-specific error patterns
        category_error_patterns = defaultdict(lambda: defaultdict(int))
        for ep in self.error_patterns:
            category_error_patterns[ep.category][ep.error_type] += 1

        # Turn-specific analysis
        errors_by_turn = Counter(ep.turn for ep in self.error_patterns)

        analysis = {
            'total_errors': len(self.error_patterns),
            'errors_by_type': dict(errors_by_type),
            'errors_by_model': dict(errors_by_model),
            'errors_by_category': dict(errors_by_category),
            'errors_by_turn': dict(errors_by_turn),
            'model_error_patterns': {k: dict(v) for k, v in model_error_patterns.items()},
            'category_error_patterns': {k: dict(v) for k, v in category_error_patterns.items()},
        }

        return analysis

    def print_analysis_summary(self, analysis: Dict) -> None:
        """Print a human-readable summary of the error analysis"""
        print("\n" + "="*80)
        print("MT-BENCH CONCEPTUAL ERROR ANALYSIS")
        print("="*80)

        print(f"\nTotal Error Patterns Identified: {analysis['total_errors']}")

        print("\n--- Errors by Type ---")
        for error_type, count in sorted(analysis['errors_by_type'].items(), key=lambda x: x[1], reverse=True):
            description = self.error_taxonomy.get(error_type, 'Unknown')
            percentage = (count / analysis['total_errors']) * 100
            print(f"  {error_type:20s}: {count:4d} ({percentage:5.1f}%) - {description}")

        print("\n--- Errors by Model ---")
        for model, count in sorted(analysis['errors_by_model'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / analysis['total_errors']) * 100
            print(f"  {model:20s}: {count:4d} ({percentage:5.1f}%)")

        print("\n--- Errors by Category ---")
        for category, count in sorted(analysis['errors_by_category'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / analysis['total_errors']) * 100
            print(f"  {category:20s}: {count:4d} ({percentage:5.1f}%)")

        print("\n--- Errors by Turn ---")
        for turn, count in sorted(analysis['errors_by_turn'].items()):
            percentage = (count / analysis['total_errors']) * 100
            print(f"  Turn {turn}: {count:4d} ({percentage:5.1f}%)")

        print("\n--- Model-Specific Error Patterns ---")
        for model, error_counts in analysis['model_error_patterns'].items():
            print(f"\n  {model}:")
            total_model_errors = sum(error_counts.values())
            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                percentage = (count / total_model_errors) * 100
                print(f"    - {error_type:20s}: {count:3d} ({percentage:5.1f}%)")

        print("\n" + "="*80)

    def get_examples_for_error_type(self, error_type: str, limit: int = 5) -> List[ErrorPattern]:
        """
        Get example error patterns for a specific error type.

        Args:
            error_type: The type of error to get examples for
            limit: Maximum number of examples to return

        Returns:
            List of ErrorPattern objects
        """
        examples = [ep for ep in self.error_patterns if ep.error_type == error_type]
        return examples[:limit]

    def export_analysis(self, output_file: str) -> None:
        """
        Export the complete error analysis to a JSON file.

        Args:
            output_file: Path to the output JSON file
        """
        analysis = self.analyze_error_distribution()

        # Add example errors for each type
        analysis['example_errors'] = {}
        for error_type in analysis['errors_by_type'].keys():
            examples = self.get_examples_for_error_type(error_type, limit=3)
            analysis['example_errors'][error_type] = [
                {
                    'question_id': ep.question_id,
                    'category': ep.category,
                    'losing_model': ep.losing_model,
                    'winning_model': ep.winning_model,
                    'turn': ep.turn,
                    'losing_response': ep.losing_response[:500],  # Truncate for readability
                    'winning_response': ep.winning_response[:500],
                }
                for ep in examples
            ]

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dumps(analysis, f, indent=2)

        print(f"\nAnalysis exported to: {output_path}")


def main():
    """Main function demonstrating the error analyzer"""
    print("MT-Bench Conceptual Error Analyzer")
    print("=" * 80)

    # Initialize analyzer
    analyzer = MTBenchErrorAnalyzer()

    # Load data
    print("\n1. Loading MT-Bench questions...")
    analyzer.load_questions_from_github()

    print("\n2. Loading human judgment data...")
    try:
        analyzer.load_human_judgments_from_huggingface()
    except Exception as e:
        print(f"\nError loading human judgments: {e}")
        print("\nTo use this tool, you need to either:")
        print("  1. Install the datasets library: pip install datasets")
        print("  2. Or manually download data from: https://huggingface.co/datasets/lmsys/mt_bench_human_judgments")
        return

    # Identify lopsided preferences
    print("\n3. Identifying lopsided preferences...")
    lopsided_cases = analyzer.identify_lopsided_preferences(min_preference_strength='strong')

    # Extract error patterns
    print("\n4. Extracting conceptual error patterns...")
    error_patterns = analyzer.extract_error_patterns(lopsided_cases)

    # Analyze error distribution
    print("\n5. Analyzing error distribution...")
    analysis = analyzer.analyze_error_distribution()

    # Print summary
    analyzer.print_analysis_summary(analysis)

    # Export results
    print("\n6. Exporting results...")
    analyzer.export_analysis("./data/mt_bench/error_analysis.json")

    # Show some examples
    print("\n--- Example Error: Instruction Following ---")
    examples = analyzer.get_examples_for_error_type('instruction_following', limit=1)
    if examples:
        ex = examples[0]
        question = analyzer.questions[ex.question_id]
        print(f"\nQuestion ID: {ex.question_id} ({ex.category})")
        print(f"Turn {ex.turn}: {question.turns[ex.turn-1]}")
        print(f"\nLosing Model ({ex.losing_model}):")
        print(f"  {ex.losing_response[:300]}...")
        print(f"\nWinning Model ({ex.winning_model}):")
        print(f"  {ex.winning_response[:300]}...")


if __name__ == "__main__":
    main()
