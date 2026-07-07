"""
ToGMAL pipeline stage definitions.

The DAG (ordering is inferred from input/output paths):

    ingest_mmlu_pro ─┐
                     ├─ enrich_subjects ─ error_taxonomy ─ cot_analysis ─┐
    ingest_ds1000 ───┤                                                   │
                     │        comprehensive_patterns ◄──────────────────┘
                     └─► unified_db ─┬─ mcp_datastore
                                     ├─ semantic_index
                                     ├─ semantic_eval        (optional)
                                     ├─ expanded_taxonomy
                                     └─ snapshots

Adding a benchmark = add one ingest stage whose outputs feed unified_db
(and teach unified_vector_db_builder.py to load it).
"""

import sys
from pathlib import Path

from .core import Stage

PY = sys.executable

# Local sparse checkout of TIGER-AI-Lab/MMLU-Pro (eval_results only).
# Override with TOGMAL_MMLU_EVAL_DIR if yours lives elsewhere.
import os
MMLU_EVAL_DIR = os.environ.get(
    "TOGMAL_MMLU_EVAL_DIR",
    "/tmp/claude-0/-home-user-togmal-mcp/aff2cb02-7ce0-5f7d-8ea1-aae1d6221433/"
    "scratchpad/MMLU-Pro/eval_results",
)


def build_stages():
    return [
        # ---------------------------------------------------------- ingest
        Stage(
            name="ingest_mmlu_pro",
            command=[PY, "rebuild_mmlu_pro_from_local.py", MMLU_EVAL_DIR, "12000"],
            inputs=[MMLU_EVAL_DIR, "rebuild_mmlu_pro_from_local.py"],
            outputs=["data/autonomous_benchmarks/autonomous_dataset.json",
                     "data/autonomous_benchmarks/vector_db_ready.json"],
        ),
        Stage(
            name="ingest_ds1000",
            command=[PY, "ds1000_scraper.py"],
            inputs=["ds1000_scraper.py"],
            outputs=["data/ds1000_cache/ds1000.jsonl",
                     "data/ds1000_cache/gpt-4-0613-answers.jsonl"],
        ),
        # ------------------------------------------------------ enrichment
        Stage(
            name="enrich_subjects",
            command=[PY, "enrich_with_subjects.py"],
            inputs=["data/autonomous_benchmarks/autonomous_dataset.json",
                    "enrich_with_subjects.py"],
            outputs=["data/autonomous_benchmarks/autonomous_dataset_enriched.json"],
        ),
        Stage(
            name="error_taxonomy",
            command=[PY, "error_taxonomy_analyzer.py"],
            inputs=["data/autonomous_benchmarks/autonomous_dataset.json",
                    "error_taxonomy_analyzer.py"],
            outputs=["data/error_taxonomy.json"],
        ),
        Stage(
            name="cot_analysis",
            command=[PY, "cot_failure_analyzer.py"],
            inputs=["data/error_taxonomy.json",
                    "data/autonomous_benchmarks/autonomous_dataset_enriched.json",
                    "cot_failure_analyzer.py"],
            outputs=["data/cot_failure_analysis.json"],
        ),
        Stage(
            name="comprehensive_patterns",
            command=[PY, "analyze_all_error_patterns.py"],
            inputs=["data/error_taxonomy.json",
                    "data/cot_failure_analysis.json",
                    "analyze_all_error_patterns.py"],
            outputs=["data/comprehensive_error_patterns.json"],
        ),
        # --------------------------------------------------------- unified
        Stage(
            name="unified_db",
            command=[PY, "build_complete_unified_db.py"],
            inputs=["data/autonomous_benchmarks/vector_db_ready.json",
                    "data/ds1000_cache/ds1000.jsonl",
                    "data/error_taxonomy.json",
                    "data/cot_failure_analysis.json",
                    "data/comprehensive_error_patterns.json",
                    "unified_vector_db_builder.py",
                    "build_complete_unified_db.py"],
            outputs=["data/unified_database_complete.json"],
        ),
        # --------------------------------------------------------- derived
        Stage(
            name="mcp_datastore",
            command=[PY, "build_mcp_datastore.py"],
            inputs=["data/unified_database_complete.json",
                    "build_mcp_datastore.py"],
            outputs=["mcp_datastore/questions_by_id.json",
                     "mcp_datastore/statistics.json"],
        ),
        Stage(
            name="semantic_index",
            command=[PY, "semantic_difficulty_checker.py", "build"],
            inputs=["data/unified_database_complete.json",
                    "semantic_difficulty_checker.py"],
            outputs=["data/semantic_index.pkl"],
        ),
        Stage(
            name="semantic_eval",
            command=[PY, "semantic_difficulty_checker.py", "evaluate"],
            inputs=["data/semantic_index.pkl"],
            outputs=["data/semantic_evaluation_results.json"],
            optional=True,
        ),
        Stage(
            name="combined_eval",
            command=[PY, "evaluate_combined_tiers.py", "2000"],
            inputs=["data/semantic_index.pkl",
                    "lightweight_prompt_checker_improved.py",
                    "evaluate_combined_tiers.py"],
            outputs=["data/combined_tier_evaluation.json"],
            optional=True,
        ),
        Stage(
            name="expanded_taxonomy",
            command=[PY, "build_expanded_taxonomy.py"],
            inputs=["data/unified_database_complete.json",
                    "data/autonomous_benchmarks/autonomous_dataset.json",
                    "data/cot_failure_analysis.json",
                    "data/comprehensive_error_patterns.json",
                    "build_expanded_taxonomy.py"],
            outputs=["data/expanded_taxonomy.json", "EXPANDED_TAXONOMY.md"],
        ),
        Stage(
            name="snapshots",
            command=[PY, "-c", (
                "import gzip, shutil, pathlib\n"
                "src_names = ['unified_database_complete', 'error_taxonomy', "
                "'cot_failure_analysis', 'comprehensive_error_patterns', "
                "'expanded_taxonomy', 'semantic_evaluation_results', "
                "'combined_tier_evaluation']\n"
                "out = pathlib.Path('snapshots'); out.mkdir(exist_ok=True)\n"
                "for n in src_names:\n"
                "    src = pathlib.Path(f'data/{n}.json')\n"
                "    if not src.exists(): continue\n"
                "    with open(src, 'rb') as fi, gzip.open(out / f'{n}.json.gz', 'wb', 9) as fo:\n"
                "        shutil.copyfileobj(fi, fo)\n"
                "    print(f'snapshotted {n}')\n"
            )],
            inputs=["data/unified_database_complete.json",
                    "data/expanded_taxonomy.json",
                    "data/combined_tier_evaluation.json"],
            outputs=["snapshots/unified_database_complete.json.gz",
                     "snapshots/expanded_taxonomy.json.gz"],
        ),
    ]
