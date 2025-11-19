"""
MT-Bench Integration with ToGMAL Benchmark Infrastructure

This module integrates MT-Bench error analysis with the existing ToGMAL
benchmark vector database, enabling unified difficulty and error analysis.

Key Features:
- Add MT-Bench questions to the vector database
- Cross-reference error patterns with similar benchmark questions
- Identify which types of prompts cause specific error patterns
- Enhanced risk assessment combining difficulty + known error patterns
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict, Counter

from mt_bench_error_analyzer import MTBenchErrorAnalyzer, ErrorPattern, MTBenchQuestion


class MTBenchIntegration:
    """
    Integrates MT-Bench error analysis with ToGMAL's benchmark infrastructure.

    This allows us to:
    1. Add MT-Bench questions to the vector DB for similarity search
    2. Map error patterns to question types
    3. Predict likely errors for incoming prompts based on similarity
    4. Enhance risk assessment with error-pattern awareness
    """

    def __init__(
        self,
        mt_bench_analyzer: MTBenchErrorAnalyzer,
        data_dir: str = "./data/mt_bench"
    ):
        """
        Initialize the integration.

        Args:
            mt_bench_analyzer: Configured MTBenchErrorAnalyzer with loaded data
            data_dir: Directory for integration data
        """
        self.analyzer = mt_bench_analyzer
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Map question IDs to error patterns for quick lookup
        self.question_errors: Dict[int, List[ErrorPattern]] = defaultdict(list)
        self._build_question_error_map()

    def _build_question_error_map(self):
        """Build a map from question IDs to their associated error patterns"""
        for error_pattern in self.analyzer.error_patterns:
            self.question_errors[error_pattern.question_id].append(error_pattern)

    def export_for_vector_db(self, output_file: str) -> None:
        """
        Export MT-Bench questions in a format compatible with BenchmarkVectorDB.

        This creates a JSON file that can be loaded into the vector database
        alongside MMLU-Pro, GPQA, etc.

        Args:
            output_file: Path to save the exported data
        """
        exported_questions = []

        for question_id, question in self.analyzer.questions.items():
            # Get error patterns for this question
            errors = self.question_errors.get(question_id, [])

            # Calculate "failure rate" based on how often models failed
            # (this is approximate since we only have pairwise comparisons)
            model_failures = Counter(ep.losing_model for ep in errors)
            total_comparisons = len(errors)

            # Estimate difficulty based on error frequency
            # More errors = higher difficulty
            if total_comparisons > 0:
                # Normalize by number of unique models
                unique_models = len(set(ep.losing_model for ep in errors))
                difficulty_score = min(1.0, total_comparisons / (unique_models * 3))
            else:
                difficulty_score = 0.5  # Unknown difficulty

            # For each turn, create a separate entry
            for turn_idx, turn_question in enumerate(question.turns, start=1):
                # Get errors specific to this turn
                turn_errors = [ep for ep in errors if ep.turn == turn_idx]

                question_entry = {
                    "question_id": f"mtbench_{question_id}_t{turn_idx}",
                    "source_benchmark": "MT-Bench",
                    "domain": question.category,
                    "question_text": turn_question,
                    "correct_answer": "",  # MT-Bench doesn't have single correct answers
                    "choices": None,
                    "success_rate": 1.0 - difficulty_score,  # Estimated
                    "difficulty_score": difficulty_score,
                    "difficulty_label": self._get_difficulty_label(difficulty_score),
                    "num_models_tested": len(set(ep.losing_model for ep in errors)) if errors else 0,
                    "turn": turn_idx,
                    "total_turns": len(question.turns),
                    "error_patterns": [
                        {
                            "error_type": ep.error_type,
                            "losing_model": ep.losing_model,
                            "winning_model": ep.winning_model,
                        }
                        for ep in turn_errors
                    ],
                    "common_errors": self._get_common_errors(turn_errors),
                }

                exported_questions.append(question_entry)

        # Save to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(exported_questions, f, indent=2)

        print(f"\nExported {len(exported_questions)} MT-Bench questions to {output_path}")
        print(f"Categories: {len(set(q['domain'] for q in exported_questions))}")
        print(f"Total error patterns: {sum(len(q['error_patterns']) for q in exported_questions)}")

    def _get_difficulty_label(self, difficulty_score: float) -> str:
        """Convert difficulty score to label"""
        if difficulty_score < 0.25:
            return "Easy"
        elif difficulty_score < 0.5:
            return "Medium"
        elif difficulty_score < 0.75:
            return "Hard"
        else:
            return "Expert"

    def _get_common_errors(self, error_patterns: List[ErrorPattern]) -> List[str]:
        """Get most common error types for this question"""
        if not error_patterns:
            return []

        error_counts = Counter(ep.error_type for ep in error_patterns)
        return [error_type for error_type, _ in error_counts.most_common(3)]

    def create_error_pattern_lookup(self, output_file: str) -> None:
        """
        Create a lookup table mapping (category, error_type) to example questions.

        This enables quick lookup of "which MT-Bench questions test reasoning errors?"

        Args:
            output_file: Path to save the lookup table
        """
        lookup = defaultdict(lambda: defaultdict(list))

        for error_pattern in self.analyzer.error_patterns:
            category = error_pattern.category
            error_type = error_pattern.error_type
            question_id = error_pattern.question_id

            question = self.analyzer.questions[question_id]
            turn_text = question.turns[error_pattern.turn - 1]

            entry = {
                "question_id": question_id,
                "turn": error_pattern.turn,
                "question_text": turn_text[:200],  # Truncate
                "losing_model": error_pattern.losing_model,
                "winning_model": error_pattern.winning_model,
            }

            lookup[category][error_type].append(entry)

        # Convert to regular dict for JSON serialization
        lookup_dict = {
            category: {
                error_type: questions
                for error_type, questions in errors.items()
            }
            for category, errors in lookup.items()
        }

        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(lookup_dict, f, indent=2)

        print(f"\nCreated error pattern lookup table at {output_path}")
        print(f"Categories covered: {list(lookup_dict.keys())}")

    def generate_risk_assessment_guide(self, output_file: str) -> None:
        """
        Generate a guide mapping error patterns to risk levels.

        This can be used by ToGMAL's heuristic detection to flag risky prompts.

        Args:
            output_file: Path to save the guide
        """
        # Analyze which error types are most severe
        error_severity = defaultdict(lambda: {
            'count': 0,
            'categories': set(),
            'models_affected': set(),
            'severity_score': 0.0
        })

        for error_pattern in self.analyzer.error_patterns:
            error_type = error_pattern.error_type
            error_severity[error_type]['count'] += 1
            error_severity[error_type]['categories'].add(error_pattern.category)
            error_severity[error_type]['models_affected'].add(error_pattern.losing_model)

        # Compute severity scores
        # More categories + more models affected = higher severity
        for error_type, data in error_severity.items():
            category_diversity = len(data['categories']) / 8.0  # 8 MT-Bench categories
            model_diversity = len(data['models_affected']) / 6.0  # 6 models in dataset
            frequency = min(1.0, data['count'] / 100.0)

            data['severity_score'] = (category_diversity + model_diversity + frequency) / 3.0

        # Create risk guide
        risk_guide = {
            'error_types': {},
            'category_risks': {},
            'heuristic_rules': []
        }

        # Error type details
        for error_type, data in error_severity.items():
            risk_guide['error_types'][error_type] = {
                'severity_score': data['severity_score'],
                'occurrence_count': data['count'],
                'affected_categories': list(data['categories']),
                'models_affected': list(data['models_affected']),
                'risk_level': self._get_risk_level(data['severity_score']),
                'description': self.analyzer.error_taxonomy.get(error_type, 'Unknown')
            }

        # Category-specific risks
        category_errors = defaultdict(Counter)
        for ep in self.analyzer.error_patterns:
            category_errors[ep.category][ep.error_type] += 1

        for category, errors in category_errors.items():
            risk_guide['category_risks'][category] = {
                'total_errors': sum(errors.values()),
                'top_error_types': [
                    {'type': error_type, 'count': count}
                    for error_type, count in errors.most_common(5)
                ],
                'primary_risk': errors.most_common(1)[0][0] if errors else 'unknown'
            }

        # Generate heuristic rules
        # These can be integrated into togmal_mcp.py
        risk_guide['heuristic_rules'] = self._generate_heuristic_rules(category_errors)

        # Save guide
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(risk_guide, f, indent=2)

        print(f"\nGenerated risk assessment guide at {output_path}")
        print("\nTop 5 High-Risk Error Types:")
        sorted_errors = sorted(
            risk_guide['error_types'].items(),
            key=lambda x: x[1]['severity_score'],
            reverse=True
        )[:5]

        for error_type, data in sorted_errors:
            print(f"  - {error_type}: {data['risk_level']} (score: {data['severity_score']:.2f})")

    def _get_risk_level(self, severity_score: float) -> str:
        """Convert severity score to risk level"""
        if severity_score < 0.25:
            return "LOW"
        elif severity_score < 0.5:
            return "MEDIUM"
        elif severity_score < 0.75:
            return "HIGH"
        else:
            return "CRITICAL"

    def _generate_heuristic_rules(self, category_errors: Dict) -> List[Dict]:
        """
        Generate heuristic rules based on error patterns.

        These can be integrated into ToGMAL's existing heuristic detection.
        """
        rules = []

        # Rule 1: Multi-turn conversation warnings
        rules.append({
            'rule_id': 'mt_bench_multiturn',
            'description': 'Warn on multi-turn conversations with constraints',
            'pattern': 'Questions with "rewrite", "rephrase", "start every sentence"',
            'risk_type': 'instruction_following',
            'severity': 'MEDIUM',
            'rationale': 'Models often fail to follow constraints in second turn'
        })

        # Rule 2: Coding task warnings
        if 'coding' in category_errors:
            top_coding_error = category_errors['coding'].most_common(1)[0][0]
            rules.append({
                'rule_id': 'mt_bench_coding',
                'description': 'Warn on complex coding tasks',
                'pattern': 'Programming questions requiring algorithmic thinking',
                'risk_type': top_coding_error,
                'severity': 'HIGH',
                'rationale': f'Most common coding error: {top_coding_error}'
            })

        # Rule 3: Math reasoning warnings
        if 'math' in category_errors or 'reasoning' in category_errors:
            rules.append({
                'rule_id': 'mt_bench_reasoning',
                'description': 'Warn on multi-step reasoning',
                'pattern': 'Logic puzzles, mathematical reasoning',
                'risk_type': 'reasoning',
                'severity': 'HIGH',
                'rationale': 'Complex reasoning often leads to logical errors'
            })

        # Rule 4: Creative constraint warnings
        if 'writing' in category_errors:
            rules.append({
                'rule_id': 'mt_bench_creative_constraints',
                'description': 'Warn on creative tasks with specific constraints',
                'pattern': 'Writing with stylistic constraints (limerick, alliteration, etc.)',
                'risk_type': 'format',
                'severity': 'MEDIUM',
                'rationale': 'Models struggle to balance creativity with strict constraints'
            })

        return rules


def main():
    """Demonstration of MT-Bench integration with ToGMAL"""
    print("MT-Bench Integration with ToGMAL Benchmark Infrastructure")
    print("=" * 80)

    # Load MT-Bench analyzer
    print("\n1. Loading MT-Bench error analyzer...")
    analyzer = MTBenchErrorAnalyzer()
    analyzer.load_questions_from_github()

    try:
        analyzer.load_human_judgments_from_huggingface()
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Extract error patterns
    print("\n2. Extracting error patterns...")
    lopsided_cases = analyzer.identify_lopsided_preferences()
    analyzer.extract_error_patterns(lopsided_cases)

    # Create integration
    print("\n3. Creating integration...")
    integration = MTBenchIntegration(analyzer)

    # Export for vector DB
    print("\n4. Exporting for vector database integration...")
    integration.export_for_vector_db("./data/mt_bench/mt_bench_for_vectordb.json")

    # Create error lookup
    print("\n5. Creating error pattern lookup table...")
    integration.create_error_pattern_lookup("./data/mt_bench/error_pattern_lookup.json")

    # Generate risk assessment guide
    print("\n6. Generating risk assessment guide...")
    integration.generate_risk_assessment_guide("./data/mt_bench/risk_assessment_guide.json")

    print("\n✓ Integration complete!")
    print("\nGenerated files:")
    print("  - ./data/mt_bench/mt_bench_for_vectordb.json")
    print("  - ./data/mt_bench/error_pattern_lookup.json")
    print("  - ./data/mt_bench/risk_assessment_guide.json")
    print("\nNext steps:")
    print("  1. Add MT-Bench questions to BenchmarkVectorDB")
    print("  2. Integrate heuristic rules into togmal_mcp.py")
    print("  3. Use error patterns for enhanced risk assessment")


if __name__ == "__main__":
    main()
