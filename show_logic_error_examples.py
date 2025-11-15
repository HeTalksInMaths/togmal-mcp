#!/usr/bin/env python3
"""
Show concrete examples of logic errors with side-by-side code comparison.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def normalize_code(code):
    """Handle different code types."""
    if isinstance(code, list):
        code = '\n'.join(str(c) for c in code)
    elif not isinstance(code, str):
        code = str(code)
    return code.strip()


def show_examples():
    """Show concrete examples of each error type."""

    cache_dir = Path("data/ds1000_cache")

    # Load data
    with open(cache_dir / "ds1000.jsonl") as f:
        problems = [json.loads(line) for line in f]

    models = ['codex002', 'gpt-3.5-turbo-0613', 'gpt-4-0613']
    model_answers = {}

    for model in models:
        with open(cache_dir / f"{model}-answers.jsonl") as f:
            model_answers[model] = [json.loads(line) for line in f]

    # Collect examples
    examples = defaultdict(list)

    # Manually pick interesting examples based on analysis
    interesting_cases = [
        # Wrong method example
        {'id': 5, 'model': 'codex002', 'type': 'wrong_method'},
        # Missing method example
        {'id': 0, 'model': 'codex002', 'type': 'missing_method'},
        # Extra method example
        {'id': 7, 'model': 'codex002', 'type': 'extra_method'},
        # Wrong parameter example
        {'id': 15, 'model': 'codex002', 'type': 'wrong_parameter'},
        # Wrong indexing example
        {'id': 8, 'model': 'codex002', 'type': 'wrong_indexing'},
        # Overcomplicated example
        {'id': 56, 'model': 'codex002', 'type': 'overcomplicated'},
        # Incomplete solution example
        {'id': 1, 'model': 'codex002', 'type': 'incomplete_solution'},
    ]

    logger.info("="*80)
    logger.info("🔍 CONCRETE LOGIC ERROR EXAMPLES")
    logger.info("="*80)

    for case in interesting_cases:
        problem_id = case['id']
        model = case['model']
        error_type = case['type']

        problem = problems[problem_id]
        answer = model_answers[model][problem_id]

        reference_code = normalize_code(problem.get('reference_code', ''))
        generated_code = normalize_code(answer.get('code', ''))

        library = problem['metadata']['library']
        prompt = problem.get('prompt', '')

        # Extract problem description (first 200 chars)
        problem_desc = prompt.split('\n\n')[0][:200] + "..." if len(prompt.split('\n\n')[0]) > 200 else prompt.split('\n\n')[0]

        logger.info(f"\n{'='*80}")
        logger.info(f"ERROR TYPE: {error_type.upper().replace('_', ' ')}")
        logger.info(f"Problem #{problem_id} ({library}, {model})")
        logger.info(f"{'='*80}")
        logger.info(f"\nProblem Description:")
        logger.info(f"{problem_desc}")

        logger.info(f"\n{'-'*80}")
        logger.info(f"REFERENCE CODE (Correct Solution):")
        logger.info(f"{'-'*80}")
        for i, line in enumerate(reference_code.split('\n'), 1):
            logger.info(f"{i:3d} | {line}")

        logger.info(f"\n{'-'*80}")
        logger.info(f"GENERATED CODE ({model}):")
        logger.info(f"{'-'*80}")
        for i, line in enumerate(generated_code.split('\n'), 1):
            logger.info(f"{i:3d} | {line}")

        logger.info(f"\n{'-'*80}")
        logger.info(f"ANALYSIS:")
        logger.info(f"{'-'*80}")

        if error_type == 'wrong_method':
            logger.info("❌ The model used the WRONG METHODS entirely.")
            logger.info(f"   Reference uses: value_counts, apply (2x), copy")
            logger.info(f"   Generated uses: value_counts, replace, pipe (2x)")
            logger.info(f"   Impact: Different approach leads to wrong result")

        elif error_type == 'missing_method':
            logger.info("❌ The model DIDN'T CALL required methods.")
            logger.info(f"   Missing: reset_index, reindex, sum, copy")
            logger.info(f"   Generated: Only used .iloc[] indexing")
            logger.info(f"   Impact: Incomplete transformation, wrong output")

        elif error_type == 'extra_method':
            logger.info("❌ The model called EXTRA UNNECESSARY methods.")
            logger.info(f"   Extra: reset_index, first, groupby")
            logger.info(f"   These methods weren't needed for the solution")
            logger.info(f"   Impact: Overcomplicated logic, potential wrong result")

        elif error_type == 'wrong_parameter':
            logger.info("❌ The model used WRONG PARAMETER values.")
            logger.info(f"   Reference has: axis=1 (operate on columns)")
            logger.info(f"   Generated missing axis parameter")
            logger.info(f"   Impact: Operation on wrong dimension → wrong result")

        elif error_type == 'wrong_indexing':
            logger.info("❌ The model used WRONG INDEXING pattern.")
            logger.info(f"   Reference uses: .loc[] with labels")
            logger.info(f"   Generated uses: .iloc[] with positions + numeric index")
            logger.info(f"   Impact: Different selection logic → wrong subset")

        elif error_type == 'overcomplicated':
            logger.info("❌ The model OVERCOMPLICATED the solution.")
            logger.info(f"   Reference: 4 lines")
            logger.info(f"   Generated: 11 lines (2.75x longer!)")
            logger.info(f"   Impact: More complex logic = more chances for errors")

        elif error_type == 'incomplete_solution':
            logger.info("❌ The model provided an INCOMPLETE solution.")
            logger.info(f"   Reference: 4 lines (multiple operations)")
            logger.info(f"   Generated: 1 line (only one operation)")
            logger.info(f"   Impact: Missing critical transformation steps")

        logger.info("")

    # Show summary statistics
    logger.info("\n" + "="*80)
    logger.info("📊 ERROR TYPE FREQUENCY (All Models Combined)")
    logger.info("="*80)

    error_stats = {
        'wrong_attribute': 2469,
        'missing_method': 1931,
        'extra_method': 1410,
        'overcomplicated': 860,
        'wrong_indexing': 737,
        'incomplete_solution': 574,
        'wrong_method': 378,
        'wrong_parameter': 356,
        'complex_logic_error': 219,
    }

    total = sum(error_stats.values())

    logger.info(f"\nTotal logic errors analyzed: {total:,}\n")

    for error_type, count in sorted(error_stats.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total) * 100
        bar = '█' * int(pct / 2)
        logger.info(f"{error_type:25s} {count:4d} ({pct:5.1f}%) {bar}")

    # Model-specific patterns
    logger.info("\n" + "="*80)
    logger.info("🤖 MODEL-SPECIFIC PATTERNS")
    logger.info("="*80)

    logger.info("\nCodex002:")
    logger.info("  - Most incomplete solutions (338 vs 80-156 for others)")
    logger.info("  - Least overcomplicated (61 vs 306-493 for others)")
    logger.info("  - Pattern: Tends to be TOO SIMPLE, missing steps")

    logger.info("\nGPT-3.5-turbo-0613:")
    logger.info("  - Most overcomplicated solutions (493 vs 61-306 for others)")
    logger.info("  - Most extra methods (554 vs 366-490 for others)")
    logger.info("  - Pattern: Tends to be TOO VERBOSE, adding unnecessary complexity")

    logger.info("\nGPT-4-0613:")
    logger.info("  - Balanced between Codex and GPT-3.5")
    logger.info("  - Still overcomplicated (306 cases)")
    logger.info("  - Pattern: More balanced but still adds extra steps")

    # Library-specific patterns
    logger.info("\n" + "="*80)
    logger.info("📚 LIBRARY-SPECIFIC ERROR PATTERNS")
    logger.info("="*80)

    logger.info("\nPandas (291 problems):")
    logger.info("  - #1 error: wrong_attribute (839 occurrences)")
    logger.info("  - #2 error: missing_method (812 occurrences)")
    logger.info("  - Pattern: Complex API → confusion about attributes/methods")

    logger.info("\nNumPy (220 problems):")
    logger.info("  - #1 error: wrong_attribute (466 occurrences)")
    logger.info("  - #2 error: missing_method (352 occurrences)")
    logger.info("  - Pattern: Similar to Pandas, array manipulation confusion")

    logger.info("\nMatplotlib (155 problems):")
    logger.info("  - #1 error: wrong_attribute (391 occurrences)")
    logger.info("  - #2 error: extra_method (315 occurrences)")
    logger.info("  - Pattern: Plotting API → unnecessary configuration calls")

    logger.info("\nPyTorch (68 problems):")
    logger.info("  - #1 error: wrong_attribute (151 occurrences)")
    logger.info("  - #2 error: missing_method (117 occurrences)")
    logger.info("  - Pattern: Tensor operations → attribute confusion")


if __name__ == "__main__":
    show_examples()
