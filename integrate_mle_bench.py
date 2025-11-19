#!/usr/bin/env python3
"""
Integrate MLE-Bench into Unified Database
==========================================

Adds MLE-Bench (synthetic) competitions to the unified question database.
Preserves solutions and evaluation metrics for enhanced MCP capabilities.
"""

import json
from pathlib import Path
from datetime import datetime


def load_databases():
    """Load existing unified database and MLE-Bench data"""

    # Load unified database
    unified_path = Path("./data/unified_database_complete.json")
    with open(unified_path, 'r') as f:
        unified_db = json.load(f)

    # Load MLE-Bench
    mle_path = Path("./data/synthetic_mle_bench.json")
    with open(mle_path, 'r') as f:
        mle_data = json.load(f)

    return unified_db, mle_data


def convert_mle_to_unified_format(competition):
    """Convert MLE-Bench competition to unified question format"""

    # Extract solution details if available
    solution_text = None
    if 'solution' in competition:
        sol = competition['solution']
        solution_parts = []

        if 'winning_approach' in sol:
            solution_parts.append(f"**Winning Approach**: {sol['winning_approach']}")

        if 'key_techniques' in sol:
            techniques = ", ".join(sol['key_techniques'])
            solution_parts.append(f"**Key Techniques**: {techniques}")

        if 'features_engineered' in sol:
            features = "\n  - ".join(sol['features_engineered'])
            solution_parts.append(f"**Feature Engineering**:\n  - {features}")

        if 'code_snippet' in sol:
            solution_parts.append(f"**Code**:\n```python{sol['code_snippet']}\n```")

        if 'performance' in sol and 'leaderboard_score' in sol['performance']:
            perf = sol['performance']
            solution_parts.append(f"**Performance**: {perf['leaderboard_score']} (Top {100-perf.get('rank_percentile', 50)}%)")

        if 'lessons_learned' in sol:
            lessons = "\n  - ".join(sol['lessons_learned'])
            solution_parts.append(f"**Lessons Learned**:\n  - {lessons}")

        solution_text = "\n\n".join(solution_parts)

    # Create unified format question
    unified_question = {
        "question_id": competition['question_id'],
        "question_text": competition['question_text'],
        "domain": competition['domain'],
        "difficulty_score": competition['difficulty_score'],
        "source": competition.get('source_benchmark', 'MLE-Bench'),

        # Additional MLE-Bench specific fields
        "subdomain": competition.get('subdomain'),
        "competition_tier": competition.get('competition_tier'),
        "evaluation_metrics": competition.get('evaluation_metrics', []),

        # Solution (if available)
        "has_solution": solution_text is not None,
        "solution": solution_text,

        # For solution evaluation
        "solution_metadata": competition.get('solution', {}),
        "dataset_info": competition.get('dataset_info', {})
    }

    return unified_question


def integrate_mle_bench():
    """Integrate MLE-Bench into unified database"""

    print("="*80)
    print("INTEGRATING MLE-BENCH INTO UNIFIED DATABASE")
    print("="*80)

    # Load data
    print("\nLoading databases...")
    unified_db, mle_data = load_databases()

    original_count = len(unified_db['questions'])
    print(f"  Unified DB: {original_count:,} questions")
    print(f"  MLE-Bench: {len(mle_data['competitions'])} competitions")

    # Convert and add MLE-Bench questions
    print("\nConverting MLE-Bench to unified format...")
    added_questions = []

    for comp in mle_data['competitions']:
        unified_q = convert_mle_to_unified_format(comp)
        added_questions.append(unified_q)
        print(f"  ✅ {comp['question_id']}: {comp['subdomain']}")

    # Add to unified database
    unified_db['questions'].extend(added_questions)

    # Update metadata
    if 'metadata' not in unified_db:
        unified_db['metadata'] = {}

    unified_db['metadata']['last_updated'] = datetime.now().isoformat()
    unified_db['metadata']['total_questions'] = len(unified_db['questions'])
    unified_db['metadata']['mle_bench_count'] = len(added_questions)
    unified_db['metadata']['sources'] = unified_db['metadata'].get('sources', [])
    if 'MLE-Bench (Synthetic)' not in unified_db['metadata']['sources']:
        unified_db['metadata']['sources'].append('MLE-Bench (Synthetic)')

    # Save updated database
    output_path = Path("./data/unified_database_with_mle.json")
    print(f"\nSaving updated database to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(unified_db, f, indent=2)

    print(f"\n✅ Integration complete!")
    print(f"   Original: {original_count:,} questions")
    print(f"   Added: {len(added_questions)} MLE-Bench questions")
    print(f"   Total: {len(unified_db['questions']):,} questions")

    # Statistics
    print("\n" + "="*80)
    print("DATABASE STATISTICS")
    print("="*80)

    # Count by domain
    domains = {}
    with_solutions = 0
    difficulties = []

    for q in unified_db['questions']:
        domain = q['domain']
        domains[domain] = domains.get(domain, 0) + 1
        if q.get('has_solution') or q.get('solution'):
            with_solutions += 1
        difficulties.append(q['difficulty_score'])

    print(f"\nTotal questions: {len(unified_db['questions']):,}")
    print(f"Questions with solutions: {with_solutions} ({with_solutions/len(unified_db['questions'])*100:.1f}%)")

    print(f"\nNew domains added:")
    new_domains = set()
    for q in added_questions:
        if q['domain'] not in domains or domains[q['domain']] == 1:
            new_domains.add(q['domain'])

    for domain in sorted(new_domains):
        count = sum(1 for q in added_questions if q['domain'] == domain)
        print(f"  • {domain}: {count} questions")

    import numpy as np
    print(f"\nDifficulty distribution:")
    print(f"  Easy (0.0-0.3):   {sum(1 for d in difficulties if d <= 0.3)} ({sum(1 for d in difficulties if d <= 0.3)/len(difficulties)*100:.1f}%)")
    print(f"  Medium (0.3-0.7): {sum(1 for d in difficulties if 0.3 < d <= 0.7)} ({sum(1 for d in difficulties if 0.3 < d <= 0.7)/len(difficulties)*100:.1f}%)")
    print(f"  Hard (0.7-1.0):   {sum(1 for d in difficulties if d > 0.7)} ({sum(1 for d in difficulties if d > 0.7)/len(difficulties)*100:.1f}%)")

    return output_path


if __name__ == "__main__":
    integrate_mle_bench()
