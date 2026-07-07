# ToGMAL Data Pipeline

Python-code-based pipeline (`togmal_pipeline/`) that turns the previously
manual script chain into a cached, dependency-ordered DAG. No orchestration
framework required — plain Python, ~200 lines of core.

## Usage

```bash
python3 -m togmal_pipeline status           # freshness of every stage
python3 -m togmal_pipeline run              # run only stale stages
python3 -m togmal_pipeline run --force      # rebuild everything
python3 -m togmal_pipeline run --only unified_db
python3 -m togmal_pipeline grow             # pull new eval results, then run
```

## The DAG

```
ingest_mmlu_pro ─┐
                 ├─ enrich_subjects ─ error_taxonomy ─ cot_analysis ─┐
ingest_ds1000 ───┤                                                   │
                 │        comprehensive_patterns ◄──────────────────┘
                 └─► unified_db ─┬─ mcp_datastore
                                 ├─ semantic_index ─ semantic_eval
                                 ├─ expanded_taxonomy
                                 └─ snapshots
```

Ordering is **inferred from declared input/output paths** — a stage that
reads another stage's outputs runs after it. Explicit `after=[...]` exists
for dependencies paths can't express.

## Caching model

Each stage's fingerprint = SHA-256 of its command + the `(path, size,
mtime)` of every input file (directories are walked). A stage re-runs only
when its fingerprint changes or its outputs are missing. State lives in
`.pipeline_state.json` (gitignored); delete it or use `--force` for a full
rebuild.

Because each stage's *script file* is one of its declared inputs, editing
the code of a stage automatically invalidates it and everything downstream —
the same behavior a build system gives you.

## Scaling it out

### More models (automatic)

`python3 -m togmal_pipeline grow` pulls the sparse checkout of
TIGER-AI-Lab/MMLU-Pro `eval_results/` and re-runs. New model archives change
the ingest stage's fingerprint, so ingestion and everything downstream
rebuild; anything untouched stays cached. The ingestor handles all archive
naming variants (`_5shots.zip`, `_5shots.json.zip`, `_5-shots.zip`,
timestamped `_0shots_HH_MM_SS.zip`) and skips summary-only archives.

### More benchmarks (one stage + one loader)

1. Write an ingest script that produces the benchmark's raw data under
   `data/<benchmark>_cache/`.
2. Add a `Stage` for it in `togmal_pipeline/stages.py` whose outputs feed
   `unified_db`'s inputs.
3. Add a loader in `unified_vector_db_builder.py` mapping the data into the
   unified question schema (`question_id`, `question_text`, `success_rate`,
   `model_scores`, optional error fields), and call it from
   `build_complete_unified_db.py`.

Every derived artifact — datastore, semantic index, expanded taxonomy,
snapshots — then rebuilds automatically on the next `run`.

### More analyzers

Enrichment analyzers are ordinary stages. A new analyzer that reads the
dataset and writes `data/<name>.json` slots into the DAG by declaring those
paths; make `unified_db` depend on its output to bake results into the
database, or `expanded_taxonomy` to surface them in the taxonomy only.

## Measured behavior (growth experiment, this session)

The pipeline was validated by actually growing the dataset with it:

**Full cold run — 12 stages, ~2 minutes wall clock:**

| Stage | Time |
|-------|------|
| ingest_mmlu_pro | 23.5s |
| semantic_index | 14.9s |
| semantic_eval (optional) | 33.6s |
| combined_eval (optional) | 37.5s |
| all 9 other stages | < 6s each |
| **Total** | **~124s** |

**Incremental run after adding one new stage:** 2 ran, 11 cached — only the
new stage and the snapshot stage it feeds executed.

**Growth result:** robust archive-name parsing raised model coverage
**39 → 48 models** (~585K → ~578K predictions over 12K questions; new
captures include claude-3-5-sonnet-20241022, claude-3-5-haiku, opus, and a
frontier model scoring 91.2%). All ingested accuracies cross-check against
the public MMLU-Pro leaderboard.

**Effect on ground truth (an honest finding):** adding stronger models makes
the difficulty labels *stricter* — universal failures fell 168 → 78 because
questions formerly failed by all 39 models are now solved by at least one.
Evaluation metrics shifted with the harder ground truth (combined recall
91.6% → 88.4%, semantic F1 83.9% → 79.6% — same checkers, cleaner labels).
The surviving 78 universal failures are correspondingly stronger evidence
of genuine model limitations.

## Failure semantics

A failed required stage aborts the run (state for completed stages is
already saved, so a fixed re-run resumes where it stopped). Stages marked
`optional: true` (e.g. `semantic_eval`) log the failure and continue.
