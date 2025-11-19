#!/usr/bin/env python3
"""
Build Task-Oriented Taxonomy Using Claude Code Directly

This version doesn't require API keys - instead, it generates analysis prompts
that Claude Code can respond to directly in the conversation.

Claude Code acts as the reasoning agent, analyzing each error case and
building the taxonomy through interactive analysis.
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from collections import defaultdict, Counter

from mt_bench_error_analyzer import MTBenchErrorAnalyzer, ErrorPattern, MTBenchQuestion


@dataclass
class TaskLevelError:
    """Rich analysis of an error at the task level"""
    question_id: int
    turn: int
    category: str
    losing_model: str
    winning_model: str
    task_domain: str
    specific_task: str
    task_complexity: str
    required_capabilities: List[str]
    missing_capability: str
    capability_category: str
    conceptual_error: str
    observable_failure: str
    error_chain: List[str]
    error_severity: str
    is_understanding_failure: bool
    is_systematic_error: bool
    losing_response_snippet: str
    winning_response_snippet: str
    explanation: str


class InteractiveTaxonomyBuilder:
    """
    Builds task-oriented taxonomy using Claude Code as the reasoning agent.

    This works by presenting error cases for analysis and collecting
    the responses to build the complete taxonomy.
    """

    def __init__(self, output_dir: str = "./data/mt_bench/task_analysis"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.output_dir / "claude_code_analysis_cache.jsonl"
        self.task_errors: List[TaskLevelError] = []

        # Load cache if exists
        self._load_cache()

    def _load_cache(self):
        """Load previously analyzed cases from cache"""
        if self.cache_file.exists():
            print(f"Loading cache from {self.cache_file}...")
            with open(self.cache_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        self.task_errors.append(TaskLevelError(**data))
                    except Exception as e:
                        print(f"Warning: Could not load cached entry: {e}")

            print(f"Loaded {len(self.task_errors)} cached analyses")

    def save_analysis(self, task_error: TaskLevelError):
        """Save a single analysis to cache"""
        with open(self.cache_file, 'a') as f:
            f.write(json.dumps(asdict(task_error)) + '\n')

        self.task_errors.append(task_error)

    def generate_analysis_batch(
        self,
        analyzer: MTBenchErrorAnalyzer,
        batch_size: int = 10,
        start_idx: int = 0
    ) -> List[Dict]:
        """
        Generate a batch of cases for Claude Code to analyze.

        Returns list of case data ready for analysis.
        """
        # Get analyzed IDs
        analyzed_ids = set(
            (e.question_id, e.turn, e.losing_model)
            for e in self.task_errors
        )

        # Get remaining error patterns
        remaining = [
            ep for ep in analyzer.error_patterns
            if (ep.question_id, ep.turn, ep.losing_model) not in analyzed_ids
        ]

        # Get batch
        batch = remaining[start_idx:start_idx + batch_size]

        # Format for analysis
        analysis_batch = []
        for i, ep in enumerate(batch):
            question = analyzer.questions[ep.question_id]

            case_data = {
                'batch_index': start_idx + i,
                'question_id': ep.question_id,
                'turn': ep.turn,
                'category': question.category,
                'losing_model': ep.losing_model,
                'winning_model': ep.winning_model,
                'question_text': question.turns[ep.turn - 1],
                'context': question.turns[0] if ep.turn == 2 else None,
                'losing_response': ep.losing_response,
                'winning_response': ep.winning_response
            }

            analysis_batch.append(case_data)

        return analysis_batch

    def add_analyzed_case(
        self,
        question_id: int,
        turn: int,
        category: str,
        losing_model: str,
        winning_model: str,
        losing_response: str,
        winning_response: str,
        analysis: Dict
    ):
        """
        Add an analyzed case to the taxonomy.

        analysis should contain:
        - task_domain
        - specific_task
        - task_complexity
        - required_capabilities (list)
        - missing_capability
        - capability_category
        - conceptual_error
        - observable_failure
        - error_chain (list)
        - error_severity
        - is_understanding_failure (bool)
        - is_systematic_error (bool)
        - explanation
        """
        task_error = TaskLevelError(
            question_id=question_id,
            turn=turn,
            category=category,
            losing_model=losing_model,
            winning_model=winning_model,
            task_domain=analysis['task_domain'],
            specific_task=analysis['specific_task'],
            task_complexity=analysis['task_complexity'],
            required_capabilities=analysis['required_capabilities'],
            missing_capability=analysis['missing_capability'],
            capability_category=analysis['capability_category'],
            conceptual_error=analysis['conceptual_error'],
            observable_failure=analysis['observable_failure'],
            error_chain=analysis['error_chain'],
            error_severity=analysis['error_severity'],
            is_understanding_failure=analysis['is_understanding_failure'],
            is_systematic_error=analysis['is_systematic_error'],
            losing_response_snippet=losing_response[:300],
            winning_response_snippet=winning_response[:300],
            explanation=analysis['explanation']
        )

        self.save_analysis(task_error)

    def build_taxonomy(self) -> Dict:
        """Build hierarchical taxonomy from analyzed errors"""
        if not self.task_errors:
            return {}

        taxonomy = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

        for error in self.task_errors:
            domain = error.task_domain
            task = error.specific_task
            capability_cat = error.capability_category
            conceptual = error.conceptual_error

            taxonomy[domain][task][capability_cat][conceptual].append({
                'question_id': error.question_id,
                'turn': error.turn,
                'observable_failure': error.observable_failure,
                'losing_model': error.losing_model,
                'severity': error.error_severity,
                'is_understanding_failure': error.is_understanding_failure
            })

        # Convert to regular dict
        return {
            domain: {
                task: {
                    cap_cat: {
                        concept: instances
                        for concept, instances in concepts.items()
                    }
                    for cap_cat, concepts in capabilities.items()
                }
                for task, capabilities in tasks.items()
            }
            for domain, tasks in taxonomy.items()
        }

    def generate_report(self, output_file: str):
        """Generate comprehensive insights report"""
        if not self.task_errors:
            print("No analyses to report")
            return

        # Statistics
        stats = {
            'total_errors': len(self.task_errors),
            'by_domain': dict(Counter(e.task_domain for e in self.task_errors)),
            'by_capability_category': dict(Counter(e.capability_category for e in self.task_errors)),
            'by_severity': dict(Counter(e.error_severity for e in self.task_errors)),
            'by_model': dict(Counter(e.losing_model for e in self.task_errors)),
            'understanding_vs_execution': {
                'understanding_failures': sum(1 for e in self.task_errors if e.is_understanding_failure),
                'execution_failures': sum(1 for e in self.task_errors if not e.is_understanding_failure)
            }
        }

        # Build taxonomy
        taxonomy = self.build_taxonomy()

        # Capability gaps
        capability_gaps = defaultdict(lambda: {'count': 0, 'models': set(), 'severity_dist': Counter()})
        for error in self.task_errors:
            cap = error.capability_category
            capability_gaps[cap]['count'] += 1
            capability_gaps[cap]['models'].add(error.losing_model)
            capability_gaps[cap]['severity_dist'][error.error_severity] += 1

        capability_gaps_serializable = {
            cap: {
                'count': data['count'],
                'models': list(data['models']),
                'severity_distribution': dict(data['severity_dist']),
                'criticality_score': (
                    data['severity_dist']['critical'] * 3 +
                    data['severity_dist']['major'] * 2 +
                    data['severity_dist']['minor'] * 1
                ) / data['count'] if data['count'] > 0 else 0
            }
            for cap, data in capability_gaps.items()
        }

        # Model-specific gaps
        model_capabilities = defaultdict(lambda: defaultdict(int))
        for error in self.task_errors:
            model_capabilities[error.losing_model][error.capability_category] += 1

        report = {
            'metadata': {
                'total_errors_analyzed': stats['total_errors'],
                'analyzer': 'Claude Code Direct Analysis'
            },
            'statistics': stats,
            'taxonomy': taxonomy,
            'capability_gap_analysis': capability_gaps_serializable,
            'model_specific_gaps': {
                model: dict(gaps)
                for model, gaps in model_capabilities.items()
            },
            'detailed_errors': [asdict(e) for e in self.task_errors]
        }

        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n✓ Report saved to: {output_path}")

        # Print summary
        self._print_summary(stats, capability_gaps_serializable)

    def _print_summary(self, stats, capability_gaps):
        """Print human-readable summary"""
        print("\n" + "="*80)
        print("TASK-ORIENTED TAXONOMY SUMMARY")
        print("="*80)

        print(f"\nTotal Errors Analyzed: {stats['total_errors']}")

        print("\n--- Task Domains ---")
        for domain, count in sorted(stats['by_domain'].items(), key=lambda x: x[1], reverse=True):
            pct = (count / stats['total_errors']) * 100
            print(f"  {domain:30s}: {count:4d} ({pct:5.1f}%)")

        print("\n--- Top Missing Capabilities ---")
        sorted_caps = sorted(
            capability_gaps.items(),
            key=lambda x: x[1]['criticality_score'],
            reverse=True
        )
        for cap, data in sorted_caps[:10]:
            print(f"\n  {cap}:")
            print(f"    Occurrences: {data['count']}")
            print(f"    Models: {', '.join(data['models'])}")
            print(f"    Criticality: {data['criticality_score']:.2f}/3.0")

        print("\n--- Understanding vs Execution ---")
        understanding = stats['understanding_vs_execution']['understanding_failures']
        execution = stats['understanding_vs_execution']['execution_failures']
        total = understanding + execution
        if total > 0:
            print(f"  Understanding: {understanding} ({100*understanding/total:.1f}%)")
            print(f"  Execution: {execution} ({100*execution/total:.1f}%)")

        print("\n" + "="*80)


def print_analysis_prompt(case_data: Dict) -> str:
    """Generate the analysis prompt for a case"""
    prompt = f"""
# Error Case Analysis Request

Please analyze this MT-Bench error case at the TASK LEVEL and identify the conceptual gap.

## Case Details

**Question ID**: {case_data['question_id']}
**Category**: {case_data['category']}
**Turn**: {case_data['turn']}
"""

    if case_data.get('context'):
        prompt += f"""
**Context (Turn 1)**: {case_data['context']}
"""

    prompt += f"""
**Question**: {case_data['question_text']}

**Losing Model ({case_data['losing_model']}) Response**:
{case_data['losing_response'][:500]}{'...' if len(case_data['losing_response']) > 500 else ''}

**Winning Model ({case_data['winning_model']}) Response**:
{case_data['winning_response'][:500]}{'...' if len(case_data['winning_response']) > 500 else ''}

---

## Analysis Framework

Please provide a task-oriented analysis in JSON format with these fields:

```json
{{
  "task_domain": "High-level domain (e.g., Creative Writing, Logical Reasoning)",
  "specific_task": "Precise task description",
  "task_complexity": "simple|moderate|complex|expert",
  "required_capabilities": ["Capability 1", "Capability 2", ...],
  "missing_capability": "The specific capability the model lacks",
  "capability_category": "Category (e.g., Prosodic Reasoning, State Tracking)",
  "conceptual_error": "WHY it failed conceptually (not just 'failed')",
  "observable_failure": "WHAT we see as a result",
  "error_chain": [
    "Step 1: Root conceptual gap",
    "Step 2: Intermediate failure",
    "Step 3: Observable result"
  ],
  "error_severity": "critical|major|minor",
  "is_understanding_failure": true or false,
  "is_systematic_error": true or false,
  "explanation": "2-3 sentence explanation"
}}
```

**Focus on**: What cognitive capability is missing, not just what went wrong.

Good: "Lacks constraint propagation - cannot maintain rhyme while preserving meaning"
Bad: "Didn't follow instructions"
"""

    return prompt


def main():
    """Interactive taxonomy building session"""
    print("="*80)
    print("TASK-ORIENTED TAXONOMY BUILDER")
    print("Using Claude Code as Reasoning Agent")
    print("="*80)

    # Load data
    print("\nInitializing...")
    base_analyzer = MTBenchErrorAnalyzer()

    print("Loading MT-Bench questions...")
    base_analyzer.load_questions_from_github()

    print("Loading human judgments...")
    try:
        base_analyzer.load_human_judgments_from_huggingface()
    except Exception as e:
        print(f"Error: {e}")
        print("\nInstall datasets: pip install datasets")
        sys.exit(1)

    print("Extracting error patterns...")
    lopsided = base_analyzer.identify_lopsided_preferences(min_preference_strength='strong')
    base_analyzer.extract_error_patterns(lopsided)

    print(f"\n✓ Ready! Found {len(base_analyzer.error_patterns)} error patterns to analyze")

    # Initialize builder
    builder = InteractiveTaxonomyBuilder()

    print(f"Already analyzed: {len(builder.task_errors)} cases")
    print(f"Remaining: {len(base_analyzer.error_patterns) - len(builder.task_errors)} cases")

    # Generate analysis prompts
    print("\n" + "="*80)
    print("GENERATING ANALYSIS BATCH")
    print("="*80)

    # Get next batch
    batch = builder.generate_analysis_batch(base_analyzer, batch_size=20, start_idx=0)

    if not batch:
        print("\nAll cases already analyzed!")
        builder.generate_report('./data/mt_bench/task_analysis/claude_code_taxonomy.json')
        return

    print(f"\nGenerated {len(batch)} cases for analysis")
    print("\nSaving batch to file for analysis...")

    batch_file = builder.output_dir / "analysis_batch.json"
    with open(batch_file, 'w') as f:
        json.dump(batch, f, indent=2)

    print(f"✓ Batch saved to: {batch_file}")

    # Print first case as example
    print("\n" + "="*80)
    print("EXAMPLE CASE FOR ANALYSIS")
    print("="*80)

    if batch:
        print(print_analysis_prompt(batch[0]))

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("""
Claude Code will now analyze the batch of cases.

For each case, provide the analysis JSON, and I'll:
1. Parse the JSON
2. Save to cache
3. Build the taxonomy incrementally
4. Generate insights

The analysis is resumable - you can stop/start anytime!
""")

    return builder, base_analyzer, batch


if __name__ == "__main__":
    builder, analyzer, batch = main()
