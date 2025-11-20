#!/usr/bin/env python3
"""
Unified Multi-Benchmark Taxonomy

Merges analyses from multiple benchmarks into a single comprehensive taxonomy:
- MT-Bench (168 analyses)
- BIG-Bench-Mistake (5 analyses)
- Chatbot Arena (5 analyses)
- RewardBench (3 analyses)
- HH-RLHF (3 analyses)
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List


def load_taxonomy(filepath: str) -> Dict:
    """Load a taxonomy JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)


def merge_taxonomies():
    """Merge all benchmark taxonomies into unified structure"""
    print("=" * 80)
    print("UNIFIED MULTI-BENCHMARK TAXONOMY")
    print("=" * 80)

    # Load all taxonomies
    taxonomies = {}

    taxonomy_files = [
        ("MT-Bench", "data/mt_bench/task_analysis/complete_mt_bench_taxonomy.json"),
        ("BIG-Bench-Mistake", "bigbench_mistake_taxonomy.json"),
        ("Chatbot Arena", "chatbot_arena_taxonomy.json"),
        ("RewardBench", "rewardbench_taxonomy.json"),
        ("HH-RLHF", "hh_rlhf_taxonomy.json")
    ]

    print("\nLoading taxonomies...")
    for name, filepath in taxonomy_files:
        if Path(filepath).exists():
            tax = load_taxonomy(filepath)
            taxonomies[name] = tax
            error_count = tax.get('statistics', {}).get('total_errors', 0) or len(tax.get('detailed_errors', []))
            print(f"  ✓ {name}: {error_count} analyses")
        else:
            print(f"  ✗ {name}: File not found at {filepath}")

    # Merge detailed errors
    all_errors = []
    benchmark_stats = {}

    for benchmark_name, tax in taxonomies.items():
        errors = tax.get('detailed_errors', [])

        for error in errors:
            # Add benchmark source
            error['benchmark_source'] = benchmark_name
            all_errors.append(error)

        benchmark_stats[benchmark_name] = len(errors)

    print(f"\n✓ Merged {len(all_errors)} total error analyses across {len(taxonomies)} benchmarks")

    # Generate unified statistics
    unified_stats = generate_unified_statistics(all_errors, benchmark_stats)

    # Create unified taxonomy structure
    unified_taxonomy = {
        'metadata': {
            'total_analyses': len(all_errors),
            'total_benchmarks': len(taxonomies),
            'benchmarks': list(taxonomies.keys()),
            'generated_by': 'Claude Code reasoning agent',
            'version': '1.0'
        },
        'benchmark_breakdown': benchmark_stats,
        'detailed_errors': all_errors,
        'unified_statistics': unified_stats,
        'capability_gap_analysis': generate_capability_analysis(all_errors),
        'cross_benchmark_insights': generate_cross_benchmark_insights(all_errors, taxonomies.keys())
    }

    # Save unified taxonomy
    output_path = "data/unified_multi_benchmark_taxonomy.json"
    Path("data").mkdir(exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(unified_taxonomy, f, indent=2)

    print(f"\n✓ Unified taxonomy saved to: {output_path}")

    # Print summary
    print_summary(unified_taxonomy)

    return unified_taxonomy


def generate_unified_statistics(all_errors: List[Dict], benchmark_stats: Dict) -> Dict:
    """Generate comprehensive statistics across all benchmarks"""

    # Task domains
    domain_counter = Counter(e.get('task_domain', 'Unknown') for e in all_errors)

    # Capabilities
    capability_counter = Counter(e.get('missing_capability', 'Unknown') for e in all_errors)

    # Severity
    severity_counter = Counter(e.get('error_severity', 'unknown') for e in all_errors)

    # Understanding vs Execution
    understanding_count = sum(1 for e in all_errors if e.get('is_understanding_failure', False))
    execution_count = len(all_errors) - understanding_count

    return {
        'total_errors': len(all_errors),
        'by_benchmark': benchmark_stats,
        'by_domain': dict(domain_counter),
        'by_capability': dict(capability_counter.most_common(20)),
        'by_severity': dict(severity_counter),
        'understanding_vs_execution': {
            'understanding_failures': understanding_count,
            'execution_failures': execution_count,
            'understanding_percentage': round(100 * understanding_count / len(all_errors), 1),
            'execution_percentage': round(100 * execution_count / len(all_errors), 1)
        }
    }


def generate_capability_analysis(all_errors: List[Dict]) -> Dict:
    """Analyze capability gaps across all benchmarks"""
    capability_data = defaultdict(lambda: {
        'count': 0,
        'benchmarks': set(),
        'models': set(),
        'severity_dist': defaultdict(int)
    })

    for error in all_errors:
        cap = error.get('capability_category', 'Unknown')
        capability_data[cap]['count'] += 1
        capability_data[cap]['benchmarks'].add(error.get('benchmark_source', 'Unknown'))
        capability_data[cap]['models'].add(error.get('losing_model', 'Unknown'))
        capability_data[cap]['severity_dist'][error.get('error_severity', 'unknown')] += 1

    # Convert sets to lists for JSON serialization
    result = {}
    for cap, data in capability_data.items():
        result[cap] = {
            'count': data['count'],
            'benchmarks': sorted(list(data['benchmarks'])),
            'models': sorted(list(data['models'])),
            'severity_distribution': dict(data['severity_dist'])
        }

    return result


def generate_cross_benchmark_insights(all_errors: List[Dict], benchmarks: List[str]) -> Dict:
    """Generate insights by comparing patterns across benchmarks"""

    insights = {
        'common_capabilities_across_benchmarks': [],
        'benchmark_specific_patterns': {},
        'universal_vs_domain_specific': {}
    }

    # Find capabilities that appear in multiple benchmarks
    cap_to_benchmarks = defaultdict(set)
    for error in all_errors:
        cap = error.get('capability_category', 'Unknown')
        bench = error.get('benchmark_source', 'Unknown')
        cap_to_benchmarks[cap].add(bench)

    # Capabilities appearing in 3+ benchmarks are "universal"
    universal = []
    domain_specific = []

    for cap, benches in cap_to_benchmarks.items():
        if len(benches) >= 3:
            universal.append({
                'capability': cap,
                'appears_in': len(benches),
                'benchmarks': sorted(list(benches))
            })
        else:
            domain_specific.append({
                'capability': cap,
                'appears_in': len(benches),
                'benchmarks': sorted(list(benches))
            })

    insights['universal_capabilities'] = sorted(universal, key=lambda x: x['appears_in'], reverse=True)
    insights['domain_specific_capabilities'] = sorted(domain_specific, key=lambda x: x['appears_in'], reverse=True)

    # Benchmark-specific error patterns
    for benchmark in benchmarks:
        bench_errors = [e for e in all_errors if e.get('benchmark_source') == benchmark]
        if bench_errors:
            domain_dist = Counter(e.get('task_domain', 'Unknown') for e in bench_errors)
            insights['benchmark_specific_patterns'][benchmark] = {
                'total_analyses': len(bench_errors),
                'top_domains': dict(domain_dist.most_common(3)),
                'understanding_failure_rate': round(100 * sum(1 for e in bench_errors if e.get('is_understanding_failure', False)) / len(bench_errors), 1)
            }

    return insights


def print_summary(taxonomy: Dict):
    """Print summary statistics"""
    print("\n" + "=" * 80)
    print("UNIFIED TAXONOMY SUMMARY")
    print("=" * 80)

    stats = taxonomy['unified_statistics']

    print(f"\nTotal Analyses: {stats['total_errors']}")

    print("\n--- By Benchmark ---")
    for bench, count in sorted(stats['by_benchmark'].items(), key=lambda x: x[1], reverse=True):
        pct = round(100 * count / stats['total_errors'], 1)
        print(f"  {bench:25s}: {count:3d} ({pct:5.1f}%)")

    print("\n--- Top Task Domains ---")
    for domain, count in sorted(stats['by_domain'].items(), key=lambda x: x[1], reverse=True)[:10]:
        pct = round(100 * count / stats['total_errors'], 1)
        print(f"  {domain:30s}: {count:3d} ({pct:5.1f}%)")

    print("\n--- Top Missing Capabilities ---")
    for cap, count in list(stats['by_capability'].items())[:10]:
        pct = round(100 * count / stats['total_errors'], 1)
        print(f"  {cap:50s}: {count:3d} ({pct:5.1f}%)")

    ue = stats['understanding_vs_execution']
    print(f"\n--- Understanding vs Execution ---")
    print(f"  Understanding Failures: {ue['understanding_failures']:3d} ({ue['understanding_percentage']:5.1f}%)")
    print(f"  Execution Failures:     {ue['execution_failures']:3d} ({ue['execution_percentage']:5.1f}%)")

    insights = taxonomy['cross_benchmark_insights']
    print(f"\n--- Cross-Benchmark Insights ---")
    print(f"  Universal capabilities (3+ benchmarks): {len(insights['universal_capabilities'])}")
    print(f"  Domain-specific capabilities: {len(insights['domain_specific_capabilities'])}")

    if insights['universal_capabilities']:
        print("\n  Top Universal Capabilities:")
        for cap_info in insights['universal_capabilities'][:5]:
            print(f"    {cap_info['capability']}: appears in {cap_info['appears_in']} benchmarks")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    merge_taxonomies()
