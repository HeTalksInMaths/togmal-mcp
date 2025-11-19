"""
Task-Oriented Error Analyzer using Reasoning Agents

This system uses reasoning agents (LLMs) to deeply analyze MT-Bench data and build
a task-oriented taxonomy that maps:

    Human Task → Conceptual Error → Observable Failure

Instead of surface-level categories like "instruction_following", this identifies
what cognitive capabilities models lack and how that manifests in task failures.

Example:
    Task: "Write a limerick"
    Conceptual Error: Lacks prosodic reasoning (rhyme scheme tracking)
    Observable Failure: Produces paragraph instead of AABBA structure
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, Counter
import anthropic

from mt_bench_error_analyzer import MTBenchErrorAnalyzer, ErrorPattern, MTBenchQuestion


@dataclass
class TaskLevelError:
    """Rich analysis of an error at the task level"""
    # Basic info
    question_id: int
    turn: int
    category: str
    losing_model: str
    winning_model: str

    # Task analysis
    task_domain: str  # e.g., "Creative Writing", "Logical Reasoning"
    specific_task: str  # e.g., "Limerick composition with rhyme constraints"
    task_complexity: str  # simple, moderate, complex, expert

    # Capability analysis
    required_capabilities: List[str]  # What the task requires
    missing_capability: str  # What the model lacks
    capability_category: str  # e.g., "Prosodic Reasoning", "State Tracking"

    # Error analysis
    conceptual_error: str  # Why it failed conceptually
    observable_failure: str  # How it manifested
    error_chain: List[str]  # Causal chain from concept to failure

    # Meta-analysis
    error_severity: str  # critical, major, minor
    is_understanding_failure: bool  # Didn't understand vs couldn't execute
    is_systematic_error: bool  # Happens consistently vs edge case

    # Evidence
    losing_response_snippet: str
    winning_response_snippet: str
    explanation: str


class TaskOrientedErrorAnalyzer:
    """
    Uses reasoning agents to build task-oriented error taxonomy from MT-Bench data.

    This system goes beyond surface-level classification to understand:
    1. What human tasks are being requested
    2. What cognitive capabilities those tasks require
    3. What conceptual gaps cause failures
    4. How those gaps manifest as observable errors
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        output_dir: str = "./data/mt_bench/task_analysis"
    ):
        """
        Initialize the task-oriented analyzer.

        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY)
            model: Claude model for reasoning
            output_dir: Directory for analysis outputs
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Store analyzed errors
        self.task_errors: List[TaskLevelError] = []

        # Cache for incremental analysis
        self.cache_file = self.output_dir / "analysis_cache.jsonl"

    def analyze_error_with_reasoning(
        self,
        question: MTBenchQuestion,
        error_pattern: ErrorPattern,
        context: Optional[Dict] = None
    ) -> TaskLevelError:
        """
        Use a reasoning agent to deeply analyze an error at the task level.

        Args:
            question: The MT-Bench question
            error_pattern: The error pattern to analyze
            context: Optional context (e.g., previous turn for turn 2)

        Returns:
            TaskLevelError with deep analysis
        """
        prompt = self._construct_task_analysis_prompt(question, error_pattern, context)

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.2,  # Lower for analytical consistency
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            task_error = self._parse_task_analysis(response_text, question, error_pattern)

            return task_error

        except Exception as e:
            print(f"Error analyzing Q{error_pattern.question_id}: {e}")
            return self._create_fallback_analysis(question, error_pattern, str(e))

    def _construct_task_analysis_prompt(
        self,
        question: MTBenchQuestion,
        error_pattern: ErrorPattern,
        context: Optional[Dict]
    ) -> str:
        """Construct the reasoning prompt for task-level analysis"""

        question_text = question.turns[error_pattern.turn - 1]

        # Add context for turn 2
        context_section = ""
        if error_pattern.turn == 2:
            context_section = f"""
**Context from Turn 1:**
Question: {question.turns[0]}
(This is a multi-turn conversation - Turn 2 builds on Turn 1)
"""

        prompt = f"""You are an expert at analyzing language model capabilities and failures. Your task is to deeply analyze WHY a model failed at a specific human task, identifying the conceptual gap that caused the failure.

**DO NOT just describe what went wrong. Identify the COGNITIVE CAPABILITY the model lacks and HOW that manifests.**

## The Case

**Category**: {question.category}
**Turn**: {error_pattern.turn} of {len(question.turns)}
{context_section}
**Question**: {question_text}

**Losing Model ({error_pattern.losing_model}) Response:**
{error_pattern.losing_response}

**Winning Model ({error_pattern.winning_model}) Response:**
{error_pattern.winning_response}

---

## Your Analysis Task

Analyze this failure at the TASK LEVEL. Identify:

1. **What human task is being requested?** (Be specific - not just "writing", but "limerick composition with rhyme scheme constraints")

2. **What cognitive capabilities does this task require?** (e.g., prosodic reasoning, state tracking, constraint propagation)

3. **Which capability is the losing model missing?** (The conceptual gap)

4. **How does this conceptual gap cause the observable failure?** (Causal chain)

5. **Is this an understanding failure or execution failure?** (Didn't get it vs got it but couldn't do it)

---

## Output Format (JSON)

Return ONLY a valid JSON object with this structure:

{{
  "task_domain": "High-level domain (e.g., Creative Writing, Logical Reasoning, Mathematical Problem Solving)",
  "specific_task": "Precise description of what's being asked (e.g., 'Generate limerick with AABBA rhyme scheme while maintaining semantic content')",
  "task_complexity": "simple|moderate|complex|expert",

  "required_capabilities": [
    "Capability 1 (e.g., Prosodic reasoning for rhyme scheme)",
    "Capability 2 (e.g., Constraint tracking across lines)",
    "Capability 3 (e.g., Semantic preservation under restructuring)"
  ],

  "missing_capability": "The specific capability the model lacks",
  "capability_category": "High-level category (e.g., Prosodic Reasoning, State Tracking, Constraint Satisfaction, Causal Reasoning)",

  "conceptual_error": "WHY it failed conceptually (e.g., 'Cannot represent rhyme scheme constraints', not just 'failed to rhyme')",
  "observable_failure": "WHAT we see as a result (e.g., 'Produced paragraph instead of AABBA limerick')",

  "error_chain": [
    "Step 1: Conceptual gap (e.g., No rhyme scheme representation)",
    "Step 2: Intermediate failure (e.g., Cannot plan line endings)",
    "Step 3: Observable result (e.g., Defaults to prose generation)"
  ],

  "error_severity": "critical|major|minor",
  "is_understanding_failure": true|false,
  "is_systematic_error": true|false,
  "explanation": "2-3 sentence explanation of the core insight"
}}

**CRITICAL**: Focus on CONCEPTUAL gaps, not surface errors. We want to understand what cognitive capability is missing, not just what went wrong.

Examples:
- Good: "Lacks constraint propagation - cannot maintain rhyme while preserving meaning"
- Bad: "Didn't follow instructions"

- Good: "Missing state tracking across reasoning steps - loses intermediate conclusions"
- Bad: "Made a logic error"

- Good: "No phonetic similarity representation - cannot identify rhyming words"
- Bad: "Didn't rhyme"
"""

        return prompt

    def _parse_task_analysis(
        self,
        response_text: str,
        question: MTBenchQuestion,
        error_pattern: ErrorPattern
    ) -> TaskLevelError:
        """Parse the LLM's analysis into a TaskLevelError"""
        try:
            import re
            # Extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response_text)

            task_error = TaskLevelError(
                question_id=error_pattern.question_id,
                turn=error_pattern.turn,
                category=question.category,
                losing_model=error_pattern.losing_model,
                winning_model=error_pattern.winning_model,

                task_domain=data.get('task_domain', 'Unknown'),
                specific_task=data.get('specific_task', 'Unknown'),
                task_complexity=data.get('task_complexity', 'unknown'),

                required_capabilities=data.get('required_capabilities', []),
                missing_capability=data.get('missing_capability', 'Unknown'),
                capability_category=data.get('capability_category', 'Unknown'),

                conceptual_error=data.get('conceptual_error', 'Unknown'),
                observable_failure=data.get('observable_failure', 'Unknown'),
                error_chain=data.get('error_chain', []),

                error_severity=data.get('error_severity', 'unknown'),
                is_understanding_failure=data.get('is_understanding_failure', False),
                is_systematic_error=data.get('is_systematic_error', True),

                losing_response_snippet=error_pattern.losing_response[:300],
                winning_response_snippet=error_pattern.winning_response[:300],
                explanation=data.get('explanation', '')
            )

            return task_error

        except Exception as e:
            print(f"Parse error for Q{error_pattern.question_id}: {e}")
            print(f"Response: {response_text[:200]}...")
            return self._create_fallback_analysis(question, error_pattern, response_text[:500])

    def _create_fallback_analysis(
        self,
        question: MTBenchQuestion,
        error_pattern: ErrorPattern,
        error_msg: str
    ) -> TaskLevelError:
        """Create a fallback analysis when LLM fails"""
        return TaskLevelError(
            question_id=error_pattern.question_id,
            turn=error_pattern.turn,
            category=question.category,
            losing_model=error_pattern.losing_model,
            winning_model=error_pattern.winning_model,
            task_domain="Parse Error",
            specific_task="Could not analyze",
            task_complexity="unknown",
            required_capabilities=[],
            missing_capability="Unknown",
            capability_category="Unknown",
            conceptual_error=f"Analysis failed: {error_msg}",
            observable_failure="Could not analyze",
            error_chain=[],
            error_severity="unknown",
            is_understanding_failure=False,
            is_systematic_error=False,
            losing_response_snippet=error_pattern.losing_response[:300],
            winning_response_snippet=error_pattern.winning_response[:300],
            explanation="LLM analysis failed"
        )

    def batch_analyze(
        self,
        analyzer: MTBenchErrorAnalyzer,
        limit: Optional[int] = None,
        filter_category: Optional[str] = None,
        filter_model: Optional[str] = None,
        resume: bool = True
    ) -> List[TaskLevelError]:
        """
        Analyze multiple errors in batch.

        Args:
            analyzer: MTBenchErrorAnalyzer with loaded error patterns
            limit: Maximum number to analyze
            filter_category: Only analyze this category
            filter_model: Only analyze this model
            resume: Resume from cache if available

        Returns:
            List of TaskLevelError objects
        """
        error_patterns = analyzer.error_patterns

        # Apply filters
        if filter_category:
            error_patterns = [ep for ep in error_patterns if ep.category == filter_category]
        if filter_model:
            error_patterns = [ep for ep in error_patterns if ep.losing_model == filter_model]

        # Load cache if resuming
        analyzed_ids = set()
        if resume and self.cache_file.exists():
            print(f"Loading cache from {self.cache_file}...")
            with open(self.cache_file, 'r') as f:
                for line in f:
                    cached = json.loads(line)
                    analyzed_ids.add((cached['question_id'], cached['turn'], cached['losing_model']))
                    # Reconstruct TaskLevelError
                    self.task_errors.append(TaskLevelError(**cached))

            print(f"Loaded {len(self.task_errors)} cached analyses")

        # Filter out already analyzed
        remaining = [
            ep for ep in error_patterns
            if (ep.question_id, ep.turn, ep.losing_model) not in analyzed_ids
        ]

        # Apply limit to remaining
        if limit:
            remaining = remaining[:limit]

        if not remaining:
            print("No new cases to analyze!")
            return self.task_errors

        print(f"\nAnalyzing {len(remaining)} error patterns...")
        print(f"(Already cached: {len(self.task_errors)})")

        for i, error_pattern in enumerate(remaining, 1):
            print(f"[{i}/{len(remaining)}] Q{error_pattern.question_id} T{error_pattern.turn} "
                  f"({error_pattern.category}, {error_pattern.losing_model})...")

            question = analyzer.questions[error_pattern.question_id]
            task_error = self.analyze_error_with_reasoning(question, error_pattern)

            self.task_errors.append(task_error)

            # Save to cache incrementally
            with open(self.cache_file, 'a') as f:
                f.write(json.dumps(asdict(task_error)) + '\n')

            # Progress update every 10
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(remaining)} complete")

        print(f"\n✓ Analysis complete! Total: {len(self.task_errors)} errors analyzed")
        return self.task_errors

    def build_task_taxonomy(self) -> Dict:
        """
        Build hierarchical taxonomy from analyzed errors.

        Structure:
            Task Domain
              └─ Specific Task Type
                  └─ Required Capabilities
                      └─ Capability Category
                          └─ Conceptual Errors
                              └─ Observable Failures
        """
        if not self.task_errors:
            print("No errors analyzed yet. Run batch_analyze() first.")
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

        # Convert to regular dict for JSON serialization
        taxonomy_dict = {
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

        return taxonomy_dict

    def generate_insights_report(self, output_file: str) -> None:
        """Generate comprehensive insights report"""
        if not self.task_errors:
            print("No errors to report. Run batch_analyze() first.")
            return

        # Aggregate statistics
        stats = {
            'total_errors': len(self.task_errors),
            'by_domain': Counter(e.task_domain for e in self.task_errors),
            'by_capability_category': Counter(e.capability_category for e in self.task_errors),
            'by_severity': Counter(e.error_severity for e in self.task_errors),
            'by_model': Counter(e.losing_model for e in self.task_errors),
            'understanding_vs_execution': {
                'understanding_failures': sum(1 for e in self.task_errors if e.is_understanding_failure),
                'execution_failures': sum(1 for e in self.task_errors if not e.is_understanding_failure)
            },
            'systematic_vs_edge_case': {
                'systematic': sum(1 for e in self.task_errors if e.is_systematic_error),
                'edge_case': sum(1 for e in self.task_errors if not e.is_systematic_error)
            }
        }

        # Build taxonomy
        taxonomy = self.build_task_taxonomy()

        # Capability gap analysis
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

        # Model-specific capability gaps
        model_capabilities = defaultdict(lambda: defaultdict(int))
        for error in self.task_errors:
            model_capabilities[error.losing_model][error.capability_category] += 1

        report = {
            'metadata': {
                'total_errors_analyzed': stats['total_errors'],
                'analysis_timestamp': str(Path(self.cache_file).stat().st_mtime) if self.cache_file.exists() else 'unknown'
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

        print(f"\n✓ Insights report saved to: {output_path}")

        # Print summary
        self._print_task_taxonomy_summary(stats, capability_gaps_serializable, model_capabilities)

    def _print_task_taxonomy_summary(self, stats, capability_gaps, model_capabilities):
        """Print human-readable summary"""
        print("\n" + "="*80)
        print("TASK-ORIENTED ERROR ANALYSIS")
        print("="*80)

        print(f"\nTotal Errors Analyzed: {stats['total_errors']}")

        print("\n--- Task Domains ---")
        for domain, count in stats['by_domain'].most_common():
            pct = (count / stats['total_errors']) * 100
            print(f"  {domain:30s}: {count:4d} ({pct:5.1f}%)")

        print("\n--- Missing Capabilities (Ranked by Criticality) ---")
        sorted_caps = sorted(
            capability_gaps.items(),
            key=lambda x: x[1]['criticality_score'],
            reverse=True
        )
        for cap, data in sorted_caps[:10]:
            print(f"\n  {cap}:")
            print(f"    Occurrences: {data['count']}")
            print(f"    Models affected: {', '.join(data['models'])}")
            print(f"    Criticality: {data['criticality_score']:.2f}/3.0")
            print(f"    Severity: {dict(data['severity_distribution'])}")

        print("\n--- Understanding vs Execution Failures ---")
        understanding = stats['understanding_vs_execution']['understanding_failures']
        execution = stats['understanding_vs_execution']['execution_failures']
        total = understanding + execution
        print(f"  Understanding failures: {understanding} ({100*understanding/total:.1f}%)")
        print(f"  Execution failures: {execution} ({100*execution/total:.1f}%)")

        print("\n--- Model-Specific Capability Gaps (Top 3 per model) ---")
        for model, gaps in model_capabilities.items():
            print(f"\n  {model}:")
            for cap, count in Counter(gaps).most_common(3):
                print(f"    - {cap}: {count}")

        print("\n" + "="*80)


def main():
    """Demo of task-oriented error analysis"""
    import sys

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY required")
        print("Set with: export ANTHROPIC_API_KEY='your-key'")
        sys.exit(1)

    print("Task-Oriented Error Analyzer")
    print("="*80)

    # Load base analyzer
    print("\n1. Loading MT-Bench data...")
    from mt_bench_error_analyzer import MTBenchErrorAnalyzer
    base_analyzer = MTBenchErrorAnalyzer()
    base_analyzer.load_questions_from_github()
    base_analyzer.load_human_judgments_from_huggingface()

    # Extract basic patterns
    print("\n2. Extracting error patterns...")
    lopsided = base_analyzer.identify_lopsided_preferences()
    base_analyzer.extract_error_patterns(lopsided)

    # Initialize task analyzer
    print("\n3. Initializing task-oriented analyzer...")
    task_analyzer = TaskOrientedErrorAnalyzer()

    # Analyze with reasoning agents
    print("\n4. Deep task-level analysis with reasoning agents...")
    print("(Starting with 20 cases - this will cost ~$0.50)")

    task_errors = task_analyzer.batch_analyze(
        base_analyzer,
        limit=20,  # Start small
        resume=True  # Resume from cache
    )

    # Generate report
    print("\n5. Generating taxonomy and insights...")
    task_analyzer.generate_insights_report(
        "./data/mt_bench/task_analysis/task_oriented_taxonomy.json"
    )

    print("\n✓ Analysis complete!")
    print("\nTo continue analyzing more cases:")
    print("  task_analyzer.batch_analyze(base_analyzer, limit=50, resume=True)")


if __name__ == "__main__":
    main()
