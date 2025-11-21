#!/usr/bin/env python3
"""
Data Quality Analysis: Understanding the 13k Taxonomy vs 252 Known Rates
=========================================================================

Questions to answer:
1. What's in the 13k taxonomy? Do questions have any difficulty signals?
2. How representative are the 252 known questions?
3. Can we use taxonomy metadata to estimate failure rates?
4. What's the coverage of the 252 across domains?
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict


def main():
    print("="*80)
    print("DATA QUALITY ANALYSIS")
    print("="*80)

    # Load data
    with open('data/unified_database_with_real_mle.json') as f:
        unified_db = json.load(f)

    with open('data/model_performance_database.json') as f:
        perf_db = json.load(f)

    all_questions = unified_db['questions']
    print(f"\nTotal questions in taxonomy: {len(all_questions):,}")

    # Get known failure rates
    failure_rates = {}
    for qid, data in perf_db['questions'].items():
        if 'failure_rate' in data:
            failure_rates[str(qid)] = data['failure_rate']
        else:
            correct_count = sum(1 for m, r in data.items()
                              if isinstance(r, dict) and r.get('is_correct', False))
            total_count = sum(1 for m, r in data.items()
                            if isinstance(r, dict) and 'is_correct' in r)
            if total_count > 0:
                failure_rates[str(qid)] = 1.0 - (correct_count / total_count)

    print(f"Questions with known failure rates: {len(failure_rates)}")
    print(f"Coverage: {len(failure_rates) / len(all_questions) * 100:.2f}%")

    # Analyze taxonomy questions
    print("\n" + "="*80)
    print("TAXONOMY ANALYSIS (13k Questions)")
    print("="*80)

    # Check what metadata exists
    sample_q = all_questions[0]
    print(f"\nSample question fields: {list(sample_q.keys())}")

    # Analyze difficulty signals in taxonomy
    has_difficulty_score = sum(1 for q in all_questions if 'difficulty_score' in q)
    has_success_rate = sum(1 for q in all_questions if 'success_rate' in q)
    has_model_scores = sum(1 for q in all_questions if 'model_scores' in q and q['model_scores'])

    print(f"\nDifficulty signals in taxonomy:")
    print(f"  • Has difficulty_score: {has_difficulty_score:,} ({has_difficulty_score/len(all_questions)*100:.1f}%)")
    print(f"  • Has success_rate: {has_success_rate:,} ({has_success_rate/len(all_questions)*100:.1f}%)")
    print(f"  • Has model_scores: {has_model_scores:,} ({has_model_scores/len(all_questions)*100:.1f}%)")

    # Analyze sources
    print(f"\n" + "-"*80)
    print("Questions by source:")
    sources = defaultdict(int)
    for q in all_questions:
        source = q.get('source', 'unknown')
        sources[source] += 1

    for source, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  • {source}: {count:,} questions")

    # Domain distribution
    print(f"\n" + "-"*80)
    print("Top 10 domains:")
    domains = defaultdict(int)
    for q in all_questions:
        domain = q.get('domain', 'unknown')
        domains[domain] += 1

    for domain, count in sorted(domains.items(), key=lambda x: -x[1])[:10]:
        print(f"  • {domain}: {count:,} questions")

    # Analyze the 252 known questions
    print("\n" + "="*80)
    print("KNOWN FAILURE RATES ANALYSIS (252 Questions)")
    print("="*80)

    known_questions = [q for q in all_questions
                      if str(q['question_id']) in failure_rates]

    print(f"\nTotal with known rates: {len(known_questions)}")

    # Domain coverage of known questions
    known_domains = defaultdict(int)
    for q in known_questions:
        domain = q.get('domain', 'unknown')
        known_domains[domain] += 1

    print(f"\nDomain distribution in known questions:")
    for domain, count in sorted(known_domains.items(), key=lambda x: -x[1]):
        total_in_domain = domains[domain]
        coverage = count / total_in_domain * 100 if total_in_domain > 0 else 0
        print(f"  • {domain}: {count} known / {total_in_domain:,} total ({coverage:.1f}% coverage)")

    # Source breakdown of known questions
    known_sources = defaultdict(int)
    for q in known_questions:
        source = q.get('source', 'unknown')
        known_sources[source] += 1

    print(f"\nSource distribution in known questions:")
    for source, count in sorted(known_sources.items(), key=lambda x: -x[1]):
        print(f"  • {source}: {count} questions")

    # Failure rate statistics
    fr_values = list(failure_rates.values())
    print(f"\n" + "-"*80)
    print("Failure rate statistics:")
    print(f"  • Mean: {np.mean(fr_values):.3f}")
    print(f"  • Median: {np.median(fr_values):.3f}")
    print(f"  • Std: {np.std(fr_values):.3f}")
    print(f"  • Min: {np.min(fr_values):.3f}")
    print(f"  • Max: {np.max(fr_values):.3f}")

    # Distribution
    bins = [0, 0.25, 0.5, 0.75, 1.0]
    hist, _ = np.histogram(fr_values, bins=bins)
    print(f"\n  Distribution:")
    print(f"    • 0-25% (Easy): {hist[0]} questions")
    print(f"    • 25-50% (Medium): {hist[1]} questions")
    print(f"    • 50-75% (Hard): {hist[2]} questions")
    print(f"    • 75-100% (Very Hard): {hist[3]} questions")

    # Analyze if taxonomy metadata correlates with known failure rates
    print("\n" + "="*80)
    print("TAXONOMY METADATA vs ACTUAL FAILURE RATES")
    print("="*80)

    # For questions with both taxonomy difficulty and known failure rate
    matches = []
    for q in known_questions:
        qid = str(q['question_id'])
        if qid in failure_rates and 'difficulty_score' in q:
            taxonomy_diff = q['difficulty_score']
            actual_fr = failure_rates[qid]
            matches.append((taxonomy_diff, actual_fr))

    if matches:
        taxonomy_diffs, actual_frs = zip(*matches)
        correlation = np.corrcoef(taxonomy_diffs, actual_frs)[0, 1]

        print(f"\nQuestions with both taxonomy difficulty and actual failure rate: {len(matches)}")
        print(f"Correlation (taxonomy difficulty vs actual failure rate): {correlation:.3f}")

        if correlation > 0.5:
            print(f"  ✅ Strong correlation - taxonomy difficulty is reliable!")
        elif correlation > 0.3:
            print(f"  ⚠️  Moderate correlation - taxonomy difficulty somewhat useful")
        else:
            print(f"  ❌ Weak correlation - taxonomy difficulty not reliable")
    else:
        print("\n❌ No overlap between taxonomy difficulty scores and known failure rates")

    # Check success_rate field
    success_rate_matches = []
    for q in known_questions:
        qid = str(q['question_id'])
        if qid in failure_rates and 'success_rate' in q:
            taxonomy_success = q['success_rate']
            actual_fr = failure_rates[qid]
            actual_success = 1.0 - actual_fr
            success_rate_matches.append((taxonomy_success, actual_success))

    if success_rate_matches:
        taxonomy_successes, actual_successes = zip(*success_rate_matches)
        correlation = np.corrcoef(taxonomy_successes, actual_successes)[0, 1]

        print(f"\nQuestions with both taxonomy success_rate and actual success rate: {len(success_rate_matches)}")
        print(f"Correlation (taxonomy success_rate vs actual): {correlation:.3f}")

        if correlation > 0.8:
            print(f"  ✅ Very strong correlation - success_rate field is reliable!")
        elif correlation > 0.5:
            print(f"  ✅ Strong correlation - success_rate field is useful")
        else:
            print(f"  ⚠️  Correlation {correlation:.3f} - success_rate field may not be reliable")

    # Recommendation
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    print(f"""
Current state:
- Taxonomy: {len(all_questions):,} questions
- Known failure rates: {len(failure_rates)} questions ({len(failure_rates)/len(all_questions)*100:.2f}% coverage)
- Domain coverage: Varies by domain

Issues:
1. Low coverage: Only {len(failure_rates)/len(all_questions)*100:.1f}% of taxonomy has known failure rates
2. Most taxonomy questions don't have validated performance data
3. Risk: Using taxonomy for similarity without knowing if those questions are truly similar in difficulty

Options:

A. USE TAXONOMY AS-IS (Current approach):
   - Pro: Rich semantic space (13k questions)
   - Con: Low coverage means predictions based on few neighbors
   - Current result: Avg 5.6 neighbors found with known rates

B. ESTIMATE TAXONOMY FAILURE RATES:
   - Use existing metadata (success_rate, difficulty_score) to estimate
   - Check correlation with known rates first (analysis above)
   - Pro: Can use full 13k for predictions
   - Con: Estimates may not be accurate out-of-distribution

C. EXPAND KNOWN FAILURE RATES:
   - Add more benchmarks (HumanEval, MBPP, Kaggle)
   - Goal: Get to 1,000+ questions with known rates
   - Pro: More confident predictions
   - Con: Takes time to add data

D. HYBRID APPROACH (Recommended):
   - Use 252 known rates for high-confidence predictions
   - Use taxonomy metadata for fallback when no similar known questions
   - Weight by confidence based on data source
   - Pro: Best of both worlds
   - Con: More complex

Recommended: Start with D (Hybrid), then pursue C (Expand known rates)
""")

    # Save analysis
    analysis = {
        'taxonomy_size': len(all_questions),
        'known_failure_rates': len(failure_rates),
        'coverage_pct': len(failure_rates) / len(all_questions) * 100,
        'sources': dict(sources),
        'domains': dict(domains),
        'known_domain_coverage': {k: {'known': v, 'total': domains[k]}
                                  for k, v in known_domains.items()},
        'failure_rate_stats': {
            'mean': float(np.mean(fr_values)),
            'median': float(np.median(fr_values)),
            'std': float(np.std(fr_values)),
            'min': float(np.min(fr_values)),
            'max': float(np.max(fr_values))
        },
        'has_difficulty_score_pct': has_difficulty_score / len(all_questions) * 100,
        'has_success_rate_pct': has_success_rate / len(all_questions) * 100,
    }

    if matches:
        analysis['taxonomy_difficulty_correlation'] = float(correlation)

    if success_rate_matches:
        analysis['taxonomy_success_rate_correlation'] = float(correlation)

    with open('data/data_quality_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)

    print("\n💾 Analysis saved to: data/data_quality_analysis.json")


if __name__ == "__main__":
    main()
