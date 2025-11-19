#!/usr/bin/env python3
"""
Task Taxonomy Analysis and Visualization

Tools for exploring and visualizing the task-oriented error taxonomy
built from MT-Bench data.

This script provides:
- Interactive queries about specific tasks/capabilities
- Model comparison across task types
- Capability gap identification
- Error pattern exploration
"""

import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional


class TaxonomyExplorer:
    """Interactive explorer for task-oriented error taxonomy"""

    def __init__(self, taxonomy_file: str):
        """
        Load taxonomy from JSON file.

        Args:
            taxonomy_file: Path to task_oriented_taxonomy.json
        """
        self.taxonomy_file = Path(taxonomy_file)

        if not self.taxonomy_file.exists():
            raise FileNotFoundError(
                f"Taxonomy file not found: {taxonomy_file}\n"
                "Run build_complete_taxonomy.py first to generate it."
            )

        with open(self.taxonomy_file, 'r') as f:
            self.data = json.load(f)

        self.errors = self.data.get('detailed_errors', [])
        self.taxonomy = self.data.get('taxonomy', {})
        self.stats = self.data.get('statistics', {})

    def query_by_task_domain(self, domain: str) -> List[Dict]:
        """Get all errors for a specific task domain"""
        return [e for e in self.errors if e['task_domain'] == domain]

    def query_by_capability(self, capability: str) -> List[Dict]:
        """Get all errors related to a specific capability"""
        return [e for e in self.errors if capability.lower() in e['capability_category'].lower()]

    def query_by_model(self, model: str) -> List[Dict]:
        """Get all errors made by a specific model"""
        return [e for e in self.errors if e['losing_model'] == model]

    def compare_models(self, model_a: str, model_b: str) -> Dict:
        """Compare two models across task types"""
        errors_a = self.query_by_model(model_a)
        errors_b = self.query_by_model(model_b)

        comparison = {
            'model_a': model_a,
            'model_b': model_b,
            'total_errors': {
                model_a: len(errors_a),
                model_b: len(errors_b)
            },
            'by_domain': {},
            'by_capability': {},
            'unique_to_a': [],
            'unique_to_b': [],
            'shared': []
        }

        # Compare by domain
        domains_a = Counter(e['task_domain'] for e in errors_a)
        domains_b = Counter(e['task_domain'] for e in errors_b)

        all_domains = set(domains_a.keys()) | set(domains_b.keys())
        for domain in all_domains:
            comparison['by_domain'][domain] = {
                model_a: domains_a.get(domain, 0),
                model_b: domains_b.get(domain, 0)
            }

        # Compare by capability
        caps_a = Counter(e['capability_category'] for e in errors_a)
        caps_b = Counter(e['capability_category'] for e in errors_b)

        all_caps = set(caps_a.keys()) | set(caps_b.keys())
        for cap in all_caps:
            comparison['by_capability'][cap] = {
                model_a: caps_a.get(cap, 0),
                model_b: caps_b.get(cap, 0)
            }

        # Find unique vs shared conceptual errors
        concepts_a = set(e['conceptual_error'] for e in errors_a)
        concepts_b = set(e['conceptual_error'] for e in errors_b)

        comparison['unique_to_a'] = list(concepts_a - concepts_b)
        comparison['unique_to_b'] = list(concepts_b - concepts_a)
        comparison['shared'] = list(concepts_a & concepts_b)

        return comparison

    def find_critical_gaps(self) -> List[Dict]:
        """Identify critical capability gaps across all models"""
        critical_errors = [e for e in self.errors if e['error_severity'] == 'critical']

        gaps = defaultdict(lambda: {
            'count': 0,
            'models': set(),
            'examples': []
        })

        for error in critical_errors:
            cap = error['capability_category']
            gaps[cap]['count'] += 1
            gaps[cap]['models'].add(error['losing_model'])

            if len(gaps[cap]['examples']) < 3:
                gaps[cap]['examples'].append({
                    'task': error['specific_task'],
                    'error': error['conceptual_error'],
                    'failure': error['observable_failure']
                })

        # Convert to list and sort by count
        gap_list = [
            {
                'capability': cap,
                'critical_failures': data['count'],
                'models_affected': list(data['models']),
                'examples': data['examples']
            }
            for cap, data in gaps.items()
        ]

        return sorted(gap_list, key=lambda x: x['critical_failures'], reverse=True)

    def analyze_understanding_vs_execution(self) -> Dict:
        """Analyze understanding failures vs execution failures"""
        understanding = [e for e in self.errors if e['is_understanding_failure']]
        execution = [e for e in self.errors if not e['is_understanding_failure']]

        analysis = {
            'understanding_failures': {
                'count': len(understanding),
                'by_domain': dict(Counter(e['task_domain'] for e in understanding).most_common()),
                'by_capability': dict(Counter(e['capability_category'] for e in understanding).most_common(10)),
                'examples': [
                    {
                        'task': e['specific_task'],
                        'error': e['conceptual_error'],
                        'explanation': e['explanation']
                    }
                    for e in understanding[:5]
                ]
            },
            'execution_failures': {
                'count': len(execution),
                'by_domain': dict(Counter(e['task_domain'] for e in execution).most_common()),
                'by_capability': dict(Counter(e['capability_category'] for e in execution).most_common(10)),
                'examples': [
                    {
                        'task': e['specific_task'],
                        'error': e['conceptual_error'],
                        'explanation': e['explanation']
                    }
                    for e in execution[:5]
                ]
            }
        }

        return analysis

    def get_task_difficulty_profile(self) -> Dict:
        """Analyze which tasks are hardest for models"""
        by_task = defaultdict(lambda: {
            'total_failures': 0,
            'models': set(),
            'avg_severity': [],
            'capability_gaps': set()
        })

        severity_scores = {'critical': 3, 'major': 2, 'minor': 1, 'unknown': 0}

        for error in self.errors:
            task = error['specific_task']
            by_task[task]['total_failures'] += 1
            by_task[task]['models'].add(error['losing_model'])
            by_task[task]['avg_severity'].append(severity_scores.get(error['error_severity'], 0))
            by_task[task]['capability_gaps'].add(error['capability_category'])

        # Compute difficulty score
        task_profiles = []
        for task, data in by_task.items():
            avg_severity = sum(data['avg_severity']) / len(data['avg_severity']) if data['avg_severity'] else 0

            difficulty_score = (
                data['total_failures'] * 0.4 +
                len(data['models']) * 0.3 +
                avg_severity * 0.3
            )

            task_profiles.append({
                'task': task,
                'difficulty_score': difficulty_score,
                'total_failures': data['total_failures'],
                'models_failing': len(data['models']),
                'avg_severity': avg_severity,
                'capability_gaps_count': len(data['capability_gaps'])
            })

        return sorted(task_profiles, key=lambda x: x['difficulty_score'], reverse=True)

    def print_summary(self):
        """Print high-level summary of taxonomy"""
        print("="*80)
        print("TASK-ORIENTED TAXONOMY SUMMARY")
        print("="*80)

        print(f"\nTotal Errors Analyzed: {len(self.errors)}")

        # Domains
        domains = Counter(e['task_domain'] for e in self.errors)
        print(f"\nTask Domains ({len(domains)}):")
        for domain, count in domains.most_common():
            pct = 100 * count / len(self.errors)
            print(f"  {domain:30s}: {count:4d} ({pct:5.1f}%)")

        # Capabilities
        capabilities = Counter(e['capability_category'] for e in self.errors)
        print(f"\nTop Missing Capabilities:")
        for cap, count in capabilities.most_common(10):
            pct = 100 * count / len(self.errors)
            print(f"  {cap:40s}: {count:4d} ({pct:5.1f}%)")

        # Models
        models = Counter(e['losing_model'] for e in self.errors)
        print(f"\nErrors by Model:")
        for model, count in models.most_common():
            pct = 100 * count / len(self.errors)
            print(f"  {model:20s}: {count:4d} ({pct:5.1f}%)")

        # Understanding vs Execution
        understanding = sum(1 for e in self.errors if e['is_understanding_failure'])
        execution = len(self.errors) - understanding
        print(f"\nFailure Types:")
        print(f"  Understanding failures: {understanding:4d} ({100*understanding/len(self.errors):5.1f}%)")
        print(f"  Execution failures:     {execution:4d} ({100*execution/len(self.errors):5.1f}%)")

        print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(description="Explore task-oriented error taxonomy")

    parser.add_argument(
        '--taxonomy-file',
        default='./data/mt_bench/task_analysis/task_oriented_taxonomy.json',
        help='Path to taxonomy JSON file'
    )

    subparsers = parser.add_subparsers(dest='command', help='Analysis command')

    # Summary command
    subparsers.add_parser('summary', help='Print high-level summary')

    # Query by domain
    domain_parser = subparsers.add_parser('domain', help='Query by task domain')
    domain_parser.add_argument('domain', help='Domain name')

    # Query by capability
    cap_parser = subparsers.add_parser('capability', help='Query by capability')
    cap_parser.add_argument('capability', help='Capability name or keyword')

    # Compare models
    compare_parser = subparsers.add_parser('compare', help='Compare two models')
    compare_parser.add_argument('model_a', help='First model')
    compare_parser.add_argument('model_b', help='Second model')

    # Critical gaps
    subparsers.add_parser('gaps', help='Show critical capability gaps')

    # Understanding vs execution
    subparsers.add_parser('understanding', help='Analyze understanding vs execution failures')

    # Task difficulty
    subparsers.add_parser('difficulty', help='Show task difficulty profiles')

    args = parser.parse_args()

    # Load taxonomy
    try:
        explorer = TaxonomyExplorer(args.taxonomy_file)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # Execute command
    if args.command == 'summary' or not args.command:
        explorer.print_summary()

    elif args.command == 'domain':
        errors = explorer.query_by_task_domain(args.domain)
        print(f"\nErrors in domain '{args.domain}': {len(errors)}")

        if errors:
            capabilities = Counter(e['capability_category'] for e in errors)
            print("\nMissing Capabilities:")
            for cap, count in capabilities.most_common():
                print(f"  - {cap}: {count}")

            print("\nExample errors:")
            for error in errors[:3]:
                print(f"\n  Task: {error['specific_task']}")
                print(f"  Error: {error['conceptual_error']}")
                print(f"  Failure: {error['observable_failure']}")

    elif args.command == 'capability':
        errors = explorer.query_by_capability(args.capability)
        print(f"\nErrors related to '{args.capability}': {len(errors)}")

        if errors:
            tasks = Counter(e['specific_task'] for e in errors)
            print("\nTasks affected:")
            for task, count in tasks.most_common(5):
                print(f"  - {task}: {count}")

    elif args.command == 'compare':
        comparison = explorer.compare_models(args.model_a, args.model_b)

        print(f"\nModel Comparison: {args.model_a} vs {args.model_b}")
        print("="*80)

        print(f"\nTotal Errors:")
        print(f"  {args.model_a}: {comparison['total_errors'][args.model_a]}")
        print(f"  {args.model_b}: {comparison['total_errors'][args.model_b]}")

        print(f"\nBy Task Domain:")
        for domain, counts in comparison['by_domain'].items():
            print(f"  {domain}:")
            print(f"    {args.model_a}: {counts[args.model_a]}")
            print(f"    {args.model_b}: {counts[args.model_b]}")

        print(f"\nTop Capability Gaps:")
        sorted_caps = sorted(
            comparison['by_capability'].items(),
            key=lambda x: max(x[1].values()),
            reverse=True
        )
        for cap, counts in sorted_caps[:5]:
            print(f"  {cap}:")
            print(f"    {args.model_a}: {counts[args.model_a]}")
            print(f"    {args.model_b}: {counts[args.model_b]}")

        print(f"\nUnique conceptual errors:")
        print(f"  Only {args.model_a}: {len(comparison['unique_to_a'])}")
        print(f"  Only {args.model_b}: {len(comparison['unique_to_b'])}")
        print(f"  Shared: {len(comparison['shared'])}")

    elif args.command == 'gaps':
        gaps = explorer.find_critical_gaps()

        print("\nCritical Capability Gaps")
        print("="*80)

        for i, gap in enumerate(gaps[:10], 1):
            print(f"\n{i}. {gap['capability']}")
            print(f"   Critical failures: {gap['critical_failures']}")
            print(f"   Models affected: {', '.join(gap['models_affected'])}")

            if gap['examples']:
                print(f"   Example:")
                ex = gap['examples'][0]
                print(f"     Task: {ex['task']}")
                print(f"     Error: {ex['error']}")
                print(f"     Failure: {ex['failure']}")

    elif args.command == 'understanding':
        analysis = explorer.analyze_understanding_vs_execution()

        print("\nUnderstanding vs Execution Failures")
        print("="*80)

        print(f"\nUnderstanding Failures: {analysis['understanding_failures']['count']}")
        print("  (Model didn't understand what was being asked)")
        print("\n  Top domains:")
        for domain, count in list(analysis['understanding_failures']['by_domain'].items())[:5]:
            print(f"    - {domain}: {count}")

        print(f"\nExecution Failures: {analysis['execution_failures']['count']}")
        print("  (Model understood but couldn't execute)")
        print("\n  Top domains:")
        for domain, count in list(analysis['execution_failures']['by_domain'].items())[:5]:
            print(f"    - {domain}: {count}")

    elif args.command == 'difficulty':
        profiles = explorer.get_task_difficulty_profile()

        print("\nTask Difficulty Profiles")
        print("="*80)
        print("\nHardest Tasks (ranked by difficulty score):\n")

        for i, profile in enumerate(profiles[:15], 1):
            print(f"{i}. {profile['task'][:70]}")
            print(f"   Difficulty: {profile['difficulty_score']:.2f}")
            print(f"   Failures: {profile['total_failures']} | "
                  f"Models: {profile['models_failing']} | "
                  f"Avg severity: {profile['avg_severity']:.2f}")
            print()


if __name__ == "__main__":
    main()
