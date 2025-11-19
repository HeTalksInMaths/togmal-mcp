#!/usr/bin/env python3
"""
ToGMAL Capability Integration

Extends ToGMAL's existing infrastructure with task-oriented capability awareness.

Integration Points:
1. Enhanced difficulty assessment (difficulty + capabilities)
2. Capability-based risk prediction
3. Unified benchmark schema
4. MCP server tools for capability queries

This module bridges the gap between:
- benchmark_vector_db.py (difficulty via similarity)
- task taxonomy (capabilities via error analysis)
- togmal_mcp.py (heuristic risk detection)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter


@dataclass
class CapabilityRequirement:
    """Represents a capability required for a task"""
    name: str
    category: str  # cognitive, linguistic, computational
    importance: float  # 0-1, how critical is this capability
    failure_rate: float  # 0-1, how often do models fail without it


@dataclass
class UnifiedBenchmarkEntry:
    """
    Unified benchmark entry combining ToGMAL fields with capability taxonomy.

    This extends the existing BenchmarkQuestion structure from benchmark_vector_db.py
    """
    # Original ToGMAL fields
    question_id: str
    source_benchmark: str
    domain: str
    question_text: str
    correct_answer: str
    success_rate: float
    difficulty_score: float

    # NEW: Task-oriented fields
    task_domain: str = None  # From taxonomy
    specific_task: str = None
    required_capabilities: List[CapabilityRequirement] = None

    # NEW: Known error patterns
    common_errors: List[Dict] = None
    systematic_failures: Dict[str, List[str]] = None  # model -> capability_gaps

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert CapabilityRequirement objects to dicts
        if self.required_capabilities:
            data['required_capabilities'] = [
                asdict(cap) for cap in self.required_capabilities
            ]
        return data


class CapabilityAwareDifficultyAssessor:
    """
    Enhanced difficulty assessment that considers both:
    1. Statistical difficulty (success rates from vector DB)
    2. Capability requirements (from task taxonomy)

    This answers: "How hard is this for THIS specific model?"
    """

    def __init__(self, task_taxonomy_file: str):
        """
        Initialize with task taxonomy.

        Args:
            task_taxonomy_file: Path to task_oriented_taxonomy.json
        """
        with open(task_taxonomy_file, 'r') as f:
            self.taxonomy_data = json.load(f)

        self.taxonomy = self.taxonomy_data.get('taxonomy', {})
        self.model_gaps = self.taxonomy_data.get('model_specific_gaps', {})

    def assess_difficulty_with_capabilities(
        self,
        prompt: str,
        model: str,
        base_difficulty: float,
        similar_questions: List[Dict]
    ) -> Dict:
        """
        Assess difficulty considering model-specific capability gaps.

        Args:
            prompt: The user's prompt
            model: Model being used
            base_difficulty: Base difficulty from vector similarity
            similar_questions: Similar benchmark questions from vector DB

        Returns:
            Enhanced difficulty assessment with capability analysis
        """
        # Step 1: Classify task type from prompt
        task_classification = self._classify_task(prompt)

        # Step 2: Identify required capabilities
        required_caps = self._get_required_capabilities(task_classification)

        # Step 3: Check model's capability gaps
        model_capability_gaps = self.model_gaps.get(model, {})

        # Step 4: Compute capability mismatch
        missing_capabilities = []
        for cap in required_caps:
            if cap.name in model_capability_gaps:
                gap_count = model_capability_gaps[cap.name]
                missing_capabilities.append({
                    'capability': cap.name,
                    'category': cap.category,
                    'importance': cap.importance,
                    'model_failure_count': gap_count
                })

        # Step 5: Adjust difficulty based on capability mismatch
        if missing_capabilities:
            # Weight by importance
            capability_penalty = sum(
                cap['importance'] for cap in missing_capabilities
            ) / len(required_caps)

            adjusted_difficulty = min(1.0, base_difficulty + (capability_penalty * 0.3))
        else:
            adjusted_difficulty = base_difficulty

        # Step 6: Identify likely error patterns
        likely_errors = self._predict_errors(task_classification, model, missing_capabilities)

        return {
            'base_difficulty': base_difficulty,
            'adjusted_difficulty': adjusted_difficulty,
            'task_classification': task_classification,
            'required_capabilities': [asdict(c) for c in required_caps],
            'missing_capabilities': missing_capabilities,
            'capability_penalty': capability_penalty if missing_capabilities else 0.0,
            'likely_errors': likely_errors,
            'risk_level': self._compute_risk_level(adjusted_difficulty, missing_capabilities)
        }

    def _classify_task(self, prompt: str) -> Dict:
        """Classify the task type from prompt text"""
        prompt_lower = prompt.lower()

        # Simple keyword-based classification
        # In production, use vector similarity to MT-Bench questions
        classifications = {
            'Creative Writing': [
                'write', 'compose', 'create', 'story', 'poem', 'limerick',
                'blog', 'email', 'letter', 'describe'
            ],
            'Logical Reasoning': [
                'reason', 'logic', 'puzzle', 'deduce', 'infer', 'conclude',
                'if', 'therefore', 'because'
            ],
            'Coding': [
                'code', 'program', 'function', 'algorithm', 'implement',
                'debug', 'python', 'javascript'
            ],
            'Mathematical': [
                'calculate', 'compute', 'solve', 'equation', 'math',
                'probability', 'statistics'
            ],
            'Roleplay': [
                'pretend', 'imagine', 'act as', 'role', 'persona', 'character'
            ]
        }

        scores = {}
        for domain, keywords in classifications.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            scores[domain] = score

        # Get highest scoring domain
        if scores:
            task_domain = max(scores.items(), key=lambda x: x[1])[0]
            confidence = scores[task_domain] / max(sum(scores.values()), 1)
        else:
            task_domain = "General"
            confidence = 0.0

        return {
            'task_domain': task_domain,
            'confidence': confidence,
            'prompt_length': len(prompt),
            'complexity_indicators': self._detect_complexity(prompt)
        }

    def _detect_complexity(self, prompt: str) -> List[str]:
        """Detect complexity indicators in prompt"""
        indicators = []

        # Multi-step task
        if any(word in prompt.lower() for word in ['first', 'then', 'next', 'finally', 'step']):
            indicators.append('multi-step')

        # Constraints
        if any(word in prompt.lower() for word in ['without', 'only', 'exactly', 'must', 'constraint']):
            indicators.append('constrained')

        # Creativity
        if any(word in prompt.lower() for word in ['creative', 'unique', 'original', 'vivid']):
            indicators.append('creative')

        # Meta-cognitive
        if any(word in prompt.lower() for word in ['explain', 'analyze', 'evaluate', 'critique']):
            indicators.append('meta-cognitive')

        return indicators

    def _get_required_capabilities(self, task_classification: Dict) -> List[CapabilityRequirement]:
        """Get capabilities required for this task type"""
        task_domain = task_classification['task_domain']
        complexity = task_classification['complexity_indicators']

        # Map task domains to typical capabilities
        capability_map = {
            'Creative Writing': [
                CapabilityRequirement('Semantic Compression', 'linguistic', 0.7, 0.3),
                CapabilityRequirement('Stylistic Control', 'linguistic', 0.6, 0.4)
            ],
            'Logical Reasoning': [
                CapabilityRequirement('Multi-Step State Tracking', 'cognitive', 0.9, 0.5),
                CapabilityRequirement('Constraint Satisfaction', 'computational', 0.8, 0.6)
            ],
            'Coding': [
                CapabilityRequirement('Algorithm Selection', 'computational', 0.9, 0.5),
                CapabilityRequirement('Syntax Knowledge', 'linguistic', 0.8, 0.3)
            ],
            'Mathematical': [
                CapabilityRequirement('Equation Manipulation', 'computational', 0.9, 0.6),
                CapabilityRequirement('Numerical Reasoning', 'cognitive', 0.8, 0.5)
            ],
            'Roleplay': [
                CapabilityRequirement('Persona Consistency', 'cognitive', 0.8, 0.4),
                CapabilityRequirement('Character Knowledge', 'cognitive', 0.7, 0.5)
            ]
        }

        base_caps = capability_map.get(task_domain, [])

        # Add complexity-based capabilities
        if 'constrained' in complexity:
            base_caps.append(
                CapabilityRequirement('Constraint Satisfaction', 'computational', 0.9, 0.7)
            )

        if 'multi-step' in complexity:
            base_caps.append(
                CapabilityRequirement('Multi-Step State Tracking', 'cognitive', 0.8, 0.6)
            )

        if 'meta-cognitive' in complexity:
            base_caps.append(
                CapabilityRequirement('Meta-Cognitive Reasoning', 'cognitive', 0.7, 0.5)
            )

        # Remove duplicates
        seen = set()
        unique_caps = []
        for cap in base_caps:
            if cap.name not in seen:
                seen.add(cap.name)
                unique_caps.append(cap)

        return unique_caps

    def _predict_errors(
        self,
        task_classification: Dict,
        model: str,
        missing_capabilities: List[Dict]
    ) -> List[Dict]:
        """Predict likely error patterns based on capability gaps"""
        likely_errors = []

        # Look up known errors from taxonomy for this task domain + model
        task_domain = task_classification['task_domain']

        if task_domain in self.taxonomy:
            for specific_task, capabilities in self.taxonomy[task_domain].items():
                for cap_category, errors in capabilities.items():
                    # Check if this capability is missing
                    if any(mc['capability'] == cap_category for mc in missing_capabilities):
                        for conceptual_error, instances in errors.items():
                            # Filter to this model
                            model_instances = [
                                inst for inst in instances
                                if inst['losing_model'] == model
                            ]

                            if model_instances:
                                likely_errors.append({
                                    'error_type': cap_category,
                                    'conceptual_error': conceptual_error,
                                    'observed_count': len(model_instances),
                                    'severity': Counter(inst['severity'] for inst in model_instances).most_common(1)[0][0],
                                    'example_failure': model_instances[0]['observable_failure']
                                })

        return likely_errors

    def _compute_risk_level(self, difficulty: float, missing_caps: List[Dict]) -> str:
        """Compute overall risk level"""
        if difficulty > 0.8 or len(missing_caps) >= 3:
            return 'HIGH'
        elif difficulty > 0.6 or len(missing_caps) >= 2:
            return 'MEDIUM'
        elif difficulty > 0.4 or len(missing_caps) >= 1:
            return 'LOW'
        else:
            return 'MINIMAL'


class CapabilityRiskAssessor:
    """
    Risk assessment based on capability requirements.

    Complements existing heuristic detection in togmal_mcp.py
    """

    def __init__(self, taxonomy_file: str):
        with open(taxonomy_file, 'r') as f:
            self.taxonomy_data = json.load(f)

    def assess_risks(
        self,
        prompt: str,
        model: str,
        difficulty_assessment: Dict
    ) -> List[Dict]:
        """
        Assess capability-based risks.

        Args:
            prompt: User's prompt
            model: Model being used
            difficulty_assessment: Output from CapabilityAwareDifficultyAssessor

        Returns:
            List of risk warnings with mitigations
        """
        risks = []

        missing_caps = difficulty_assessment.get('missing_capabilities', [])
        likely_errors = difficulty_assessment.get('likely_errors', [])

        # Risk 1: Critical capability gaps
        critical_caps = [
            cap for cap in missing_caps
            if cap['importance'] > 0.8
        ]

        for cap in critical_caps:
            risks.append({
                'type': 'critical_capability_gap',
                'severity': 'HIGH',
                'capability': cap['capability'],
                'description': f"Model lacks {cap['capability']} which is critical for this task",
                'likelihood': cap['model_failure_count'] / 10.0,  # Normalize
                'mitigation': [
                    f"Use a model stronger in {cap['capability']} (e.g., GPT-4, Claude)",
                    f"Break task into subtasks that don't require {cap['capability']}",
                    f"Provide examples demonstrating {cap['capability']}"
                ]
            })

        # Risk 2: Known systematic failures
        systematic_errors = [
            err for err in likely_errors
            if err['observed_count'] >= 2  # Happened multiple times
        ]

        for error in systematic_errors:
            risks.append({
                'type': 'systematic_failure',
                'severity': error['severity'].upper(),
                'error_pattern': error['conceptual_error'],
                'description': f"Model systematically fails: {error['example_failure']}",
                'likelihood': min(1.0, error['observed_count'] / 5.0),
                'mitigation': [
                    f"Avoid tasks requiring {error['error_type']}",
                    "Use explicit step-by-step instructions",
                    "Request output in structured format for validation"
                ]
            })

        # Risk 3: High difficulty + capability gaps = likely failure
        if difficulty_assessment['risk_level'] == 'HIGH':
            risks.append({
                'type': 'high_difficulty_with_gaps',
                'severity': 'HIGH',
                'description': f"High difficulty ({difficulty_assessment['adjusted_difficulty']:.2f}) combined with {len(missing_caps)} capability gaps",
                'likelihood': difficulty_assessment['adjusted_difficulty'],
                'mitigation': [
                    "Consider using a more capable model",
                    "Simplify the task requirements",
                    "Break into smaller, simpler subtasks",
                    "Use chain-of-thought prompting"
                ]
            })

        return risks


def integrate_with_vector_db(
    vector_db_path: Path,
    taxonomy_file: str,
    output_path: Path
):
    """
    Augment existing vector DB entries with capability information.

    Reads BenchmarkVectorDB data and enriches it with taxonomy insights.

    Args:
        vector_db_path: Path to existing benchmark data
        taxonomy_file: Path to task taxonomy JSON
        output_path: Where to save enriched data
    """
    print(f"Loading taxonomy from {taxonomy_file}...")
    with open(taxonomy_file, 'r') as f:
        taxonomy_data = json.load(f)

    taxonomy = taxonomy_data.get('taxonomy', {})

    print(f"Loading vector DB data from {vector_db_path}...")
    # Load existing benchmark questions
    # (In practice, this would interface with BenchmarkVectorDB)

    enriched_entries = []

    # For each benchmark entry, add capability information
    # This is a placeholder - actual implementation would query chromadb

    print(f"Enriching entries with capability data...")

    # Save enriched data
    print(f"Saving enriched data to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump({
            'metadata': {
                'source': str(vector_db_path),
                'taxonomy': str(taxonomy_file),
                'total_entries': len(enriched_entries)
            },
            'entries': enriched_entries
        }, f, indent=2)

    print(f"✓ Enriched {len(enriched_entries)} entries")


def main():
    """Demonstration of capability-aware assessment"""
    import sys

    taxonomy_file = './data/mt_bench/task_analysis/demo_taxonomy.json'

    if not Path(taxonomy_file).exists():
        print(f"Error: Taxonomy file not found: {taxonomy_file}")
        print("Run demo_task_analysis.py first.")
        sys.exit(1)

    print("="*80)
    print("CAPABILITY-AWARE DIFFICULTY ASSESSMENT DEMO")
    print("="*80)

    # Initialize assessor
    assessor = CapabilityAwareDifficultyAssessor(taxonomy_file)

    # Example prompts
    test_prompts = [
        ("Write a limerick about programming", "alpaca-13b"),
        ("Solve this logic puzzle: If A>B and B>C, what is the relationship between A and C?", "llama-13b"),
        ("Explain the theory of relativity in simple terms", "gpt-3.5"),
    ]

    for prompt, model in test_prompts:
        print(f"\n--- Prompt: \"{prompt[:50]}...\" ---")
        print(f"Model: {model}")

        # Simulate base difficulty
        base_difficulty = 0.5

        # Assess with capabilities
        assessment = assessor.assess_difficulty_with_capabilities(
            prompt=prompt,
            model=model,
            base_difficulty=base_difficulty,
            similar_questions=[]
        )

        print(f"\nBase difficulty: {assessment['base_difficulty']:.2f}")
        print(f"Adjusted difficulty: {assessment['adjusted_difficulty']:.2f}")
        print(f"Risk level: {assessment['risk_level']}")

        print(f"\nRequired capabilities:")
        for cap in assessment['required_capabilities']:
            print(f"  - {cap['name']} ({cap['category']}): importance={cap['importance']:.1f}")

        if assessment['missing_capabilities']:
            print(f"\nMissing capabilities:")
            for cap in assessment['missing_capabilities']:
                print(f"  ⚠️  {cap['capability']} (failures: {cap['model_failure_count']})")

        if assessment['likely_errors']:
            print(f"\nLikely errors:")
            for error in assessment['likely_errors'][:2]:
                print(f"  - {error['conceptual_error']}")
                print(f"    Example: {error['example_failure']}")

    print("\n" + "="*80)
    print("✓ Demo complete!")


if __name__ == "__main__":
    main()
