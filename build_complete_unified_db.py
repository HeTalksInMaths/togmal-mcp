#!/usr/bin/env python3
"""
Build Complete Unified Vector Database
=======================================

This script builds the complete unified vector database integrating ALL error patterns:

1. MMLU-Pro (12K questions with taxonomy + CoT analysis)
2. DS-1000 (1K questions with code error patterns)
3. DataSciBench (future integration)

Error Pattern Integration:
- DS-1000: 8 code error patterns
- Universal Failures: 20 patterns (questions all models fail)
- CoT Failures: 2 reasoning patterns
- ML-Discovered: 2 dangerous cluster patterns

Total: 32 error patterns across 13K+ questions
"""

import json
import logging
from pathlib import Path
from unified_vector_db_builder import UnifiedVectorDBBuilder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("="*80)
    logger.info("Building Complete Unified Vector Database")
    logger.info("="*80)

    # Initialize builder
    builder = UnifiedVectorDBBuilder(data_dir=Path("./data"))

    # Build unified database
    logger.info("\nBuilding unified database from all sources...")
    all_questions = builder.build_unified_database(
        include_mmlu_pro=True,
        include_ds1000=False,  # Skip DS-1000 (not available)
        include_datasci=False  # Not implemented yet
    )

    # Statistics
    logger.info("\n" + "="*80)
    logger.info("Database Statistics")
    logger.info("="*80)

    total = len(all_questions)
    logger.info(f"\nTotal Questions: {total:,}")

    # By benchmark
    by_benchmark = {}
    for q in all_questions:
        by_benchmark[q.benchmark] = by_benchmark.get(q.benchmark, 0) + 1

    logger.info("\nBy Benchmark:")
    for bench, count in sorted(by_benchmark.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {bench}: {count:,} ({count/total*100:.1f}%)")

    # Error analysis coverage
    with_error_analysis = sum(1 for q in all_questions if q.has_error_analysis())
    universal_failures = sum(1 for q in all_questions if q.is_universal_failure)
    cot_failures = sum(1 for q in all_questions if q.cot_failure_mode is not None)

    logger.info("\nError Analysis Coverage:")
    logger.info(f"  Questions with error patterns: {with_error_analysis:,} ({with_error_analysis/total*100:.1f}%)")
    logger.info(f"  Universal failures (all models fail): {universal_failures:,}")
    logger.info(f"  CoT failures: {cot_failures:,}")

    # Error pattern statistics
    all_patterns = []
    for q in all_questions:
        all_patterns.extend(q.error_patterns)

    logger.info(f"\nTotal Error Pattern Instances: {len(all_patterns):,}")

    # By source
    by_source = {}
    for pattern in all_patterns:
        by_source[pattern.source] = by_source.get(pattern.source, 0) + 1

    logger.info("\nError Patterns by Source:")
    for source, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {source}: {count:,}")

    # By severity
    by_severity = {}
    for pattern in all_patterns:
        by_severity[pattern.severity] = by_severity.get(pattern.severity, 0) + 1

    logger.info("\nError Patterns by Severity:")
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = by_severity.get(severity, 0)
        if count > 0:
            logger.info(f"  {severity}: {count:,}")

    # Difficulty distribution
    by_difficulty = {}
    for q in all_questions:
        by_difficulty[q.difficulty_label] = by_difficulty.get(q.difficulty_label, 0) + 1

    logger.info("\nDifficulty Distribution:")
    for diff in ['Nearly_Impossible', 'Expert', 'Hard', 'Medium', 'Easy']:
        count = by_difficulty.get(diff, 0)
        if count > 0:
            logger.info(f"  {diff}: {count:,} ({count/total*100:.1f}%)")

    # Success rate statistics
    success_rates = [q.success_rate for q in all_questions]
    avg_success = sum(success_rates) / len(success_rates)

    logger.info(f"\nSuccess Rate Statistics:")
    logger.info(f"  Average: {avg_success:.1%}")
    logger.info(f"  Min: {min(success_rates):.1%}")
    logger.info(f"  Max: {max(success_rates):.1%}")

    # Domain coverage
    by_domain = {}
    for q in all_questions:
        by_domain[q.domain] = by_domain.get(q.domain, 0) + 1

    logger.info(f"\nDomain Coverage ({len(by_domain)} domains):")
    for domain, count in sorted(by_domain.items(), key=lambda x: x[1], reverse=True)[:15]:
        logger.info(f"  {domain}: {count:,}")

    # Save to JSON for inspection
    output_path = Path("./data/unified_database_complete.json")
    logger.info(f"\nSaving complete database to {output_path}...")

    output_data = {
        'metadata': {
            'total_questions': total,
            'benchmarks': by_benchmark,
            'error_analysis_coverage': {
                'with_patterns': with_error_analysis,
                'universal_failures': universal_failures,
                'cot_failures': cot_failures
            },
            'pattern_stats': {
                'total_instances': len(all_patterns),
                'by_source': by_source,
                'by_severity': by_severity
            },
            'difficulty_distribution': by_difficulty,
            'domain_coverage': len(by_domain)
        },
        'questions': [q.to_dict() for q in all_questions]
    }

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"✅ Saved {total:,} questions to {output_path}")
    logger.info(f"   File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Sample questions with error analysis
    logger.info("\n" + "="*80)
    logger.info("Sample Questions with Error Analysis")
    logger.info("="*80)

    # Universal failure
    universal = [q for q in all_questions if q.is_universal_failure]
    if universal:
        q = universal[0]
        logger.info(f"\n1. Universal Failure (ALL models fail):")
        logger.info(f"   Question: {q.question_text[:100]}...")
        logger.info(f"   Success Rate: {q.success_rate:.1%}")
        logger.info(f"   Patterns: {len(q.error_patterns)}")
        for p in q.error_patterns:
            logger.info(f"     - {p.pattern} ({p.source}, {p.severity})")

    # CoT failure
    cot = [q for q in all_questions if q.cot_failure_mode is not None]
    if cot:
        q = cot[0]
        logger.info(f"\n2. Chain-of-Thought Failure:")
        logger.info(f"   Question: {q.question_text[:100]}...")
        logger.info(f"   Failure Mode: {q.cot_failure_mode}")
        logger.info(f"   Success Rate: {q.success_rate:.1%}")
        logger.info(f"   Patterns: {len(q.error_patterns)}")

    # DS-1000 with errors
    ds_errors = [q for q in all_questions if q.benchmark == "DS-1000" and q.has_error_analysis()]
    if ds_errors:
        q = ds_errors[0]
        logger.info(f"\n3. DS-1000 Code Error:")
        logger.info(f"   Question: {q.question_text[:100]}...")
        logger.info(f"   Success Rate: {q.success_rate:.1%}")
        logger.info(f"   Patterns: {len(q.error_patterns)}")
        for p in q.error_patterns:
            logger.info(f"     - {p.pattern} ({p.source}, {p.severity})")

    logger.info("\n" + "="*80)
    logger.info("✅ Complete Unified Database Built Successfully!")
    logger.info("="*80)

    logger.info(f"\nNext Steps:")
    logger.info(f"  1. Build vector embeddings from unified database")
    logger.info(f"  2. Deploy ChromaDB with all {total:,} questions")
    logger.info(f"  3. Test MCP with comprehensive error patterns")
    logger.info(f"  4. Update README with statistics")

if __name__ == "__main__":
    main()
