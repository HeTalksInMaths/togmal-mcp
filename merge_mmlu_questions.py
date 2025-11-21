#!/usr/bin/env python3
"""
Merge MMLU-Pro Questions from Performance DB into Unified DB
=============================================================

The performance database has 170 MMLU-Pro questions (IDs 70-239)
that are not in the unified database. This script adds them.
"""

import json
from pathlib import Path
from datetime import datetime


def main():
    print("Merging MMLU-Pro questions from performance DB into unified DB...")

    # Load databases
    unified_path = Path('data/unified_database_with_real_mle.json')
    perf_path = Path('data/model_performance_database.json')

    with open(unified_path) as f:
        unified_db = json.load(f)

    with open(perf_path) as f:
        perf_db = json.load(f)

    # Get existing question IDs
    existing_ids = set(str(q['question_id']) for q in unified_db['questions'])

    print(f"  Existing questions in unified DB: {len(existing_ids)}")

    # Find MMLU-Pro questions in performance DB that are not in unified DB
    new_questions = []

    for qid, model_results in perf_db['questions'].items():
        if str(qid) not in existing_ids:
            # This is a new question - extract info from first model result
            if isinstance(model_results, dict):
                # Get first model's result for question metadata
                first_model = list(model_results.keys())[0]
                if isinstance(model_results[first_model], dict) and 'question_text' in model_results[first_model]:
                    result = model_results[first_model]

                    # Compute failure rate
                    correct_count = sum(1 for m in model_results.values()
                                      if isinstance(m, dict) and m.get('is_correct', False))
                    total_count = sum(1 for m in model_results.values()
                                    if isinstance(m, dict) and 'is_correct' in m)
                    failure_rate = 1.0 - (correct_count / total_count) if total_count > 0 else 0.5

                    # Create unified question format
                    question = {
                        'question_id': str(qid),
                        'question_text': result['question_text'],
                        'benchmark': 'MMLU-Pro',
                        'domain': result.get('domain', result.get('category', 'unknown')),
                        'category': result.get('category', result.get('domain', 'unknown')),
                        'subject': result.get('domain', result.get('category', '')),
                        'success_rate': 1.0 - failure_rate,
                        'difficulty_score': failure_rate,
                        'model_scores': {
                            model_name: model_data.get('is_correct', False)
                            for model_name, model_data in model_results.items()
                            if isinstance(model_data, dict) and 'is_correct' in model_data
                        },
                        'num_models_tested': total_count,
                        'error_patterns': [],
                        'error_categories': [],
                        'conceptual_gaps': [],
                        'difficulty_label': 'Hard' if failure_rate > 0.7 else 'Medium' if failure_rate > 0.3 else 'Easy',
                        'is_universal_failure': failure_rate >= 0.9,
                        'cot_failure_mode': None,
                        'ml_cluster_id': None,
                        'source': 'MMLU-Pro (from performance DB)'
                    }

                    new_questions.append(question)

    print(f"  Found {len(new_questions)} new MMLU-Pro questions to add")

    # Add new questions to unified DB
    unified_db['questions'].extend(new_questions)

    # Update metadata
    unified_db['metadata']['total_questions'] = len(unified_db['questions'])
    unified_db['metadata']['last_updated'] = datetime.now().isoformat()

    # Add source tracking
    if 'MMLU-Pro (from performance DB)' not in unified_db['metadata']['sources']:
        unified_db['metadata']['sources'].append('MMLU-Pro (from performance DB)')
    unified_db['metadata']['mmlu_pro_count'] = len(new_questions)

    # Save updated database
    backup_path = unified_path.parent / f"{unified_path.stem}_backup.json"
    print(f"  Creating backup at {backup_path}")
    with open(backup_path, 'w') as f:
        json.dump(unified_db, f, indent=2)

    print(f"  Saving updated unified DB to {unified_path}")
    with open(unified_path, 'w') as f:
        json.dump(unified_db, f, indent=2)

    print(f"\n✅ Successfully merged {len(new_questions)} MMLU-Pro questions")
    print(f"  Total questions now: {len(unified_db['questions'])}")
    print(f"  Questions with performance data: {len(new_questions) + 82} (170 MMLU-Pro + 82 MLE-bench)")

    # Verify the merge
    print("\nVerifying merge...")
    with open(unified_path) as f:
        verified_db = json.load(f)

    # Count questions by source
    sources = {}
    for q in verified_db['questions']:
        source = q.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1

    print("  Questions by source:")
    for source, count in sorted(sources.items()):
        print(f"    {source}: {count}")

    print("\n✅ Merge complete!")


if __name__ == '__main__':
    main()
