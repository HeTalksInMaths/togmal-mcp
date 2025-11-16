#!/usr/bin/env python3
"""
Comprehensive Error Pattern Analysis
=====================================

This script analyzes ALL error analysis files in the project to create
a complete inventory of error patterns discovered across:
1. DS-1000 analysis (pandas/numpy code errors)
2. MMLU-Pro error taxonomy (11,726 failures)
3. Chain-of-Thought failure analysis (150 universal failures)
4. ML clustering patterns (3 clusters)
5. ML-discovered tools/patterns
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

def load_json(filepath: Path) -> Dict:
    """Load JSON file safely"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {}

def analyze_error_taxonomy(data: Dict) -> Dict[str, Any]:
    """Analyze error_taxonomy.json patterns"""
    print("\n" + "="*80)
    print("1. ERROR TAXONOMY ANALYSIS (MMLU-Pro)")
    print("="*80)

    metadata = data.get('metadata', {})
    print(f"\nMetadata:")
    print(f"  Total questions: {metadata.get('total_questions', 0)}")
    print(f"  Total failures: {metadata.get('total_failures', 0)}")
    print(f"  Failure rate: {metadata.get('failure_rate', 0):.1%}")
    print(f"  Models analyzed: {len(metadata.get('sota_models', []))}")

    # Universal failures
    universal = data.get('universal_failures', [])
    print(f"\nUniversal Failures: {len(universal)}")
    if universal:
        print(f"  Sample questions that ALL models fail:")
        for i, q in enumerate(universal[:3], 1):
            text = q.get('question', '')[:80] + "..." if len(q.get('question', '')) > 80 else q.get('question', '')
            print(f"    {i}. {text}")
            print(f"       Category: {q.get('category', 'unknown')}")
            print(f"       Success rate: {q.get('success_rate', 0):.1%}")

    # Common patterns
    patterns = data.get('common_patterns', [])
    print(f"\nCommon Patterns: {len(patterns)}")
    if patterns:
        for i, pattern in enumerate(patterns[:5], 1):
            print(f"  {i}. {pattern.get('pattern', 'Unknown')}")
            print(f"     Frequency: {pattern.get('frequency', 0)}")

    # Error types
    error_types = data.get('by_error_type', {})
    print(f"\nError Types: {len(error_types)}")
    if error_types:
        for error_type, info in list(error_types.items())[:5]:
            print(f"  - {error_type}: {info.get('count', 0)} occurrences")

    # Extract patterns
    extracted_patterns = []

    # From universal failures
    for q in universal:
        extracted_patterns.append({
            'source': 'universal_failure',
            'pattern': 'always_fails',
            'description': 'Question that all models fail',
            'category': q.get('category', 'unknown'),
            'frequency': len(metadata.get('sota_models', [])),  # All models
            'severity': 'CRITICAL'
        })

    # From common patterns
    for pattern in patterns:
        extracted_patterns.append({
            'source': 'common_pattern',
            'pattern': pattern.get('pattern', 'unknown'),
            'description': pattern.get('description', ''),
            'frequency': pattern.get('frequency', 0),
            'severity': 'HIGH' if pattern.get('frequency', 0) > 100 else 'MEDIUM'
        })

    return {
        'total_patterns': len(extracted_patterns),
        'patterns': extracted_patterns,
        'universal_failures': len(universal),
        'common_patterns': len(patterns),
        'error_types': len(error_types)
    }

def analyze_enhanced_taxonomy(data: Dict) -> Dict[str, Any]:
    """Analyze enhanced_taxonomy.json patterns"""
    print("\n" + "="*80)
    print("2. ENHANCED TAXONOMY ANALYSIS (Domain-Specific)")
    print("="*80)

    categories = data.get('categories', {})
    print(f"\nDomains analyzed: {len(categories)}")

    extracted_patterns = []
    domain_stats = {}

    for domain, domain_data in categories.items():
        stats = domain_data.get('statistics', {})
        failures = domain_data.get('high_failure_questions', [])
        patterns = domain_data.get('common_failure_patterns', [])

        domain_stats[domain] = {
            'total_questions': stats.get('total_questions', 0),
            'avg_success_rate': stats.get('average_success_rate', 0),
            'failure_patterns': len(patterns)
        }

        print(f"\n  {domain}:")
        print(f"    Questions: {stats.get('total_questions', 0)}")
        print(f"    Avg success: {stats.get('average_success_rate', 0):.1%}")
        print(f"    Patterns: {len(patterns)}")

        # Extract patterns for this domain
        for pattern in patterns:
            extracted_patterns.append({
                'source': 'domain_specific',
                'domain': domain,
                'pattern': pattern.get('pattern', 'unknown'),
                'description': pattern.get('description', ''),
                'frequency': pattern.get('frequency', 0),
                'severity': 'HIGH' if pattern.get('frequency', 0) > 10 else 'MEDIUM'
            })

    # Global insights
    global_insights = data.get('global_insights', {})
    universal_failures = global_insights.get('universal_failures', [])
    top_knowledge = global_insights.get('top_required_knowledge', [])

    print(f"\nGlobal Insights:")
    print(f"  Universal failures: {len(universal_failures)}")

    # Handle different formats for top_knowledge
    if isinstance(top_knowledge, list):
        print(f"  Top required knowledge areas: {len(top_knowledge)}")
        if top_knowledge:
            print(f"  Most required knowledge:")
            for i, knowledge in enumerate(top_knowledge[:5], 1):
                if isinstance(knowledge, dict):
                    print(f"    {i}. {knowledge.get('knowledge', 'unknown')}: {knowledge.get('count', 0)} questions")
                else:
                    print(f"    {i}. {knowledge}")
    elif isinstance(top_knowledge, dict):
        print(f"  Top required knowledge areas: {len(top_knowledge)}")
        if top_knowledge:
            print(f"  Most required knowledge:")
            for i, (knowledge, count) in enumerate(list(top_knowledge.items())[:5], 1):
                print(f"    {i}. {knowledge}: {count}")

    return {
        'total_patterns': len(extracted_patterns),
        'patterns': extracted_patterns,
        'domains': len(categories),
        'domain_stats': domain_stats,
        'universal_failures': len(universal_failures)
    }

def analyze_cot_failures(data: Dict) -> Dict[str, Any]:
    """Analyze cot_failure_analysis.json patterns"""
    print("\n" + "="*80)
    print("3. CHAIN-OF-THOUGHT FAILURE ANALYSIS")
    print("="*80)

    metadata = data.get('metadata', {})
    analyses = data.get('analyses', [])

    print(f"\nMetadata:")
    print(f"  Total analyzed: {metadata.get('total_analyzed', 0)}")
    print(f"  Method: {metadata.get('analysis_method', 'unknown')}")

    print(f"\nAnalyses: {len(analyses)}")

    # Aggregate failure modes
    failure_modes = defaultdict(int)
    contributing_factors = defaultdict(int)
    required_knowledge = defaultdict(int)
    difficulty_levels = defaultdict(int)

    extracted_patterns = []

    for analysis in analyses:
        # Count failure modes
        primary_mode = analysis.get('primary_failure_mode', 'unknown')
        failure_modes[primary_mode] += 1

        # Count contributing factors
        for factor in analysis.get('contributing_factors', []):
            contributing_factors[factor] += 1

        # Count required knowledge
        for knowledge in analysis.get('required_knowledge', []):
            required_knowledge[knowledge] += 1

        # Count difficulty
        difficulty = analysis.get('difficulty_estimate', 'unknown')
        difficulty_levels[difficulty] += 1

    print(f"\nPrimary Failure Modes:")
    for mode, count in sorted(failure_modes.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {mode}: {count}")
        extracted_patterns.append({
            'source': 'cot_failure',
            'pattern': mode,
            'description': f'Chain-of-thought failure mode',
            'frequency': count,
            'severity': 'CRITICAL' if count > 20 else 'HIGH'
        })

    print(f"\nTop Contributing Factors:")
    for factor, count in sorted(contributing_factors.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {factor}: {count}")

    print(f"\nMost Required Knowledge:")
    for knowledge, count in sorted(required_knowledge.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {knowledge}: {count}")

    print(f"\nDifficulty Distribution:")
    for diff, count in sorted(difficulty_levels.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {diff}: {count}")

    # Sample detailed analysis
    if analyses:
        print(f"\nSample Detailed Analysis:")
        sample = analyses[0]
        print(f"  Question: {sample.get('question', '')[:100]}...")
        print(f"  Category: {sample.get('category', 'unknown')}")
        print(f"  Primary failure: {sample.get('primary_failure_mode', 'unknown')}")
        print(f"  Reasoning steps: {len(sample.get('reasoning_steps', []))}")

    return {
        'total_patterns': len(extracted_patterns),
        'patterns': extracted_patterns,
        'failure_modes': dict(failure_modes),
        'contributing_factors': dict(contributing_factors),
        'required_knowledge': dict(required_knowledge),
        'difficulty_levels': dict(difficulty_levels)
    }

def analyze_ml_discovered_tools(data: Dict) -> Dict[str, Any]:
    """Analyze ml_discovered_tools.json patterns"""
    print("\n" + "="*80)
    print("4. ML-DISCOVERED TOOLS/PATTERNS")
    print("="*80)

    patterns = data.get('patterns', [])
    metadata = data.get('metadata', {})

    print(f"\nPatterns discovered: {len(patterns)}")
    print(f"Updated: {data.get('updated_at', 'unknown')}")

    extracted_patterns = []

    for i, pattern in enumerate(patterns, 1):
        print(f"\nPattern {i}:")
        print(f"  Type: {pattern.get('type', 'unknown')}")
        print(f"  Name: {pattern.get('name', 'unknown')}")
        print(f"  Description: {pattern.get('description', '')[:100]}...")
        print(f"  Confidence: {pattern.get('confidence', 0):.1%}")

        extracted_patterns.append({
            'source': 'ml_discovered',
            'pattern': pattern.get('name', 'unknown'),
            'description': pattern.get('description', ''),
            'confidence': pattern.get('confidence', 0),
            'severity': 'HIGH' if pattern.get('confidence', 0) > 0.7 else 'MEDIUM'
        })

    return {
        'total_patterns': len(extracted_patterns),
        'patterns': extracted_patterns,
        'metadata': metadata
    }

def analyze_training_results(data: Dict) -> Dict[str, Any]:
    """Analyze training_results.json patterns"""
    print("\n" + "="*80)
    print("5. ML CLUSTERING RESULTS (KMeans)")
    print("="*80)

    print(f"\nModel: {data.get('model_type', 'unknown')}")
    print(f"Clusters: {data.get('n_clusters', 0)}")
    print(f"Silhouette score: {data.get('silhouette_score', 0):.3f}")

    clusters = data.get('clusters', {})
    dangerous = data.get('dangerous_clusters', [])

    print(f"\nDangerous clusters: {dangerous}")

    extracted_patterns = []

    # Handle both dict and list formats
    if isinstance(clusters, dict):
        cluster_items = clusters.items()
    elif isinstance(clusters, list):
        cluster_items = enumerate(clusters)
    else:
        cluster_items = []

    for cluster_id, cluster_data in cluster_items:
        print(f"\nCluster {cluster_id}:")

        if isinstance(cluster_data, dict):
            print(f"  Size: {cluster_data.get('size', 0)}")
            print(f"  Avg success rate: {cluster_data.get('avg_success_rate', 0):.1%}")
            print(f"  Top categories: {cluster_data.get('top_categories', [])[:3]}")

            # Extract pattern for dangerous clusters
            if str(cluster_id) in [str(d) for d in dangerous]:
                extracted_patterns.append({
                    'source': 'ml_clustering',
                    'pattern': f'dangerous_cluster_{cluster_id}',
                    'description': f'High-risk question cluster with low success rate',
                    'cluster_size': cluster_data.get('size', 0),
                    'avg_success_rate': cluster_data.get('avg_success_rate', 0),
                    'severity': 'CRITICAL'
                })

    return {
        'total_patterns': len(extracted_patterns),
        'patterns': extracted_patterns,
        'n_clusters': data.get('n_clusters', 0),
        'dangerous_clusters': len(dangerous)
    }

def analyze_ds1000_patterns() -> Dict[str, Any]:
    """Document DS-1000 patterns from togmal_mcp.py"""
    print("\n" + "="*80)
    print("6. DS-1000 ERROR PATTERNS (Pandas/NumPy Code)")
    print("="*80)

    # These are hardcoded from the MCP implementation
    ds1000_patterns = [
        {
            'source': 'ds1000',
            'pattern': 'mutability_misunderstanding',
            'description': 'Missing .copy() or in-place modification issues',
            'frequency': 3247,  # From DS-1000 analysis
            'severity': 'CRITICAL'
        },
        {
            'source': 'ds1000',
            'pattern': 'index_persistence',
            'description': 'Missing .reset_index() after groupby/operations',
            'frequency': 1856,
            'severity': 'CRITICAL'
        },
        {
            'source': 'ds1000',
            'pattern': 'vectorization_concept',
            'description': 'Using for-loops instead of vectorized operations',
            'frequency': 1423,
            'severity': 'CRITICAL'
        },
        {
            'source': 'ds1000',
            'pattern': 'transformation_pipelines',
            'description': 'Incomplete transformation pipeline (missing steps)',
            'frequency': 892,
            'severity': 'CRITICAL'
        },
        {
            'source': 'ds1000',
            'pattern': 'method_semantics',
            'description': 'Wrong method choice (e.g., .replace vs .apply)',
            'frequency': 634,
            'severity': 'CRITICAL'
        },
        {
            'source': 'ds1000',
            'pattern': 'dimensional_operations',
            'description': 'Missing or wrong axis parameter',
            'frequency': 487,
            'severity': 'MEDIUM'
        },
        {
            'source': 'ds1000',
            'pattern': 'api_evolution',
            'description': 'Using deprecated methods (e.g., .values instead of .to_numpy())',
            'frequency': 276,
            'severity': 'MEDIUM'
        },
        {
            'source': 'ds1000',
            'pattern': 'indexing_semantics',
            'description': 'Confusion between .loc and .iloc',
            'frequency': 125,
            'severity': 'HIGH'
        }
    ]

    print(f"\nTotal DS-1000 patterns: {len(ds1000_patterns)}")
    print(f"Total failures analyzed: 8,934")

    for pattern in ds1000_patterns:
        print(f"\n  {pattern['pattern']}:")
        print(f"    Description: {pattern['description']}")
        print(f"    Frequency: {pattern['frequency']}")
        print(f"    Severity: {pattern['severity']}")

    return {
        'total_patterns': len(ds1000_patterns),
        'patterns': ds1000_patterns,
        'total_failures': 8934
    }

def main():
    print("="*80)
    print("COMPREHENSIVE ERROR PATTERN ANALYSIS")
    print("="*80)
    print("\nAnalyzing all error analysis files in the project...")

    data_dir = Path("/home/user/togmal-mcp/data")

    # Load all data files
    error_taxonomy = load_json(data_dir / "error_taxonomy.json")
    enhanced_taxonomy = load_json(data_dir / "enhanced_taxonomy.json")
    cot_failures = load_json(data_dir / "cot_failure_analysis.json")
    ml_tools = load_json(data_dir / "ml_discovered_tools.json")
    training = load_json(data_dir / "training_results.json")

    # Analyze each source
    results = {}

    results['error_taxonomy'] = analyze_error_taxonomy(error_taxonomy)
    results['enhanced_taxonomy'] = analyze_enhanced_taxonomy(enhanced_taxonomy)
    results['cot_failures'] = analyze_cot_failures(cot_failures)
    results['ml_tools'] = analyze_ml_discovered_tools(ml_tools)
    results['training'] = analyze_training_results(training)
    results['ds1000'] = analyze_ds1000_patterns()

    # Combine all patterns
    print("\n" + "="*80)
    print("COMPREHENSIVE PATTERN SUMMARY")
    print("="*80)

    all_patterns = []
    for source, data in results.items():
        all_patterns.extend(data.get('patterns', []))

    print(f"\nTotal patterns across all sources: {len(all_patterns)}")

    # Group by source
    by_source = defaultdict(list)
    for pattern in all_patterns:
        by_source[pattern['source']].append(pattern)

    print(f"\nPatterns by source:")
    for source, patterns in sorted(by_source.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {source}: {len(patterns)} patterns")

    # Group by severity
    by_severity = defaultdict(list)
    for pattern in all_patterns:
        severity = pattern.get('severity', 'UNKNOWN')
        by_severity[severity].append(pattern)

    print(f"\nPatterns by severity:")
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']:
        count = len(by_severity[severity])
        if count > 0:
            print(f"  {severity}: {count} patterns")

    # Save comprehensive results
    output_file = data_dir / "comprehensive_error_patterns.json"
    output = {
        'metadata': {
            'total_patterns': len(all_patterns),
            'sources': {
                'ds1000': 'Pandas/NumPy code error patterns from DS-1000 benchmark',
                'error_taxonomy': 'MMLU-Pro failure taxonomy (11,726 failures)',
                'enhanced_taxonomy': 'Domain-specific error patterns',
                'cot_failures': 'Chain-of-thought reasoning failures (150 questions)',
                'ml_tools': 'ML-discovered patterns',
                'ml_clustering': 'KMeans clustering patterns (3 clusters)'
            },
            'pattern_counts': {source: len(patterns) for source, patterns in by_source.items()},
            'severity_counts': {severity: len(patterns) for severity, patterns in by_severity.items()}
        },
        'patterns_by_source': dict(by_source),
        'patterns_by_severity': dict(by_severity),
        'all_patterns': all_patterns,
        'source_summaries': results
    }

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Saved comprehensive analysis to: {output_file}")

    # Create markdown summary
    create_markdown_summary(output, data_dir / "COMPREHENSIVE_ERROR_PATTERNS.md")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

def create_markdown_summary(data: Dict, output_path: Path):
    """Create a markdown summary of all error patterns"""

    md = """# Comprehensive Error Pattern Analysis

**Generated**: Auto-generated from all error analysis files
**Total Patterns**: {total_patterns}

---

## Overview

This document catalogs ALL error patterns discovered across the ToGMAL project, combining:

1. **DS-1000 Analysis**: Pandas/NumPy code error patterns (8,934 failures)
2. **MMLU-Pro Error Taxonomy**: General knowledge failures (11,726 failures)
3. **Enhanced Domain Taxonomy**: Domain-specific error patterns
4. **Chain-of-Thought Failures**: Reasoning failure modes (150 questions)
5. **ML-Discovered Patterns**: Machine learning pattern discovery
6. **Clustering Analysis**: KMeans clustering of dangerous question types

---

## Pattern Summary by Source

""".format(total_patterns=data['metadata']['total_patterns'])

    # Add source summaries
    for source, count in sorted(data['metadata']['pattern_counts'].items(), key=lambda x: x[1], reverse=True):
        md += f"- **{source}**: {count} patterns\n"

    md += "\n---\n\n## Pattern Summary by Severity\n\n"

    # Add severity breakdown
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = data['metadata']['severity_counts'].get(severity, 0)
        if count > 0:
            bar = '█' * min(count // 5, 50)
            md += f"- **{severity}**: {count} patterns {bar}\n"

    md += "\n---\n\n## Detailed Patterns\n\n"

    # Add detailed patterns by source
    for source, patterns in sorted(data['patterns_by_source'].items()):
        md += f"### {source.upper().replace('_', ' ')} ({len(patterns)} patterns)\n\n"

        # Group by severity within source
        by_sev = defaultdict(list)
        for p in patterns:
            by_sev[p.get('severity', 'UNKNOWN')].append(p)

        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if severity in by_sev:
                md += f"#### {severity}\n\n"
                for pattern in by_sev[severity]:
                    md += f"**{pattern.get('pattern', 'unknown')}**\n\n"
                    md += f"- Description: {pattern.get('description', 'No description')}\n"

                    if 'frequency' in pattern:
                        md += f"- Frequency: {pattern['frequency']}\n"
                    if 'confidence' in pattern:
                        md += f"- Confidence: {pattern['confidence']:.1%}\n"
                    if 'domain' in pattern:
                        md += f"- Domain: {pattern['domain']}\n"
                    if 'cluster_size' in pattern:
                        md += f"- Cluster size: {pattern['cluster_size']}\n"
                    if 'avg_success_rate' in pattern:
                        md += f"- Avg success rate: {pattern['avg_success_rate']:.1%}\n"

                    md += "\n"

        md += "---\n\n"

    md += """
## How to Use These Patterns

### For Vector Database Integration

All patterns should be integrated into the unified vector database schema:

```python
@dataclass
class UnifiedBenchmarkQuestion:
    # Core fields
    question_id: str
    question_text: str
    benchmark: str
    success_rate: float

    # Error analysis (populated based on source)
    error_patterns: List[ErrorPattern]  # All patterns from all sources
    error_categories: List[str]  # Categories from taxonomy
    conceptual_gaps: List[str]  # From CoT analysis
    ml_cluster_id: Optional[int]  # From clustering
    cot_failure_mode: Optional[str]  # From CoT analysis
```

### For MCP Tool Detection

DS-1000 patterns are already integrated into `togmal_mcp.py`. Other patterns can be added:

- **MMLU-Pro patterns**: Add domain-specific detection
- **CoT failure modes**: Add reasoning pattern detection
- **ML clusters**: Add cluster-based risk assessment

### For Risk Assessment

Use pattern severity and frequency to calculate risk:

- **CRITICAL**: Immediate intervention required
- **HIGH**: Strong warning recommended
- **MEDIUM**: Cautionary notice
- **LOW**: Informational only

---

## Next Steps

1. ✅ Extract all patterns (COMPLETE)
2. ⏳ Integrate MMLU-Pro patterns into vector DB
3. ⏳ Integrate CoT failure modes into vector DB
4. ⏳ Add ML cluster patterns to risk assessment
5. ⏳ Update MCP tools to detect all pattern types
6. ⏳ Build complete unified vector database
"""

    with open(output_path, 'w') as f:
        f.write(md)

    print(f"✅ Saved markdown summary to: {output_path}")

if __name__ == "__main__":
    main()
