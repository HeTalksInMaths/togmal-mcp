# ToGMAL Measured Results: Tiers 1–2, Taxonomy & Data Durability

**Current system (all figures measured, not projected):**

| Layer | Latency | Recall | Precision | F1 |
|-------|---------|--------|-----------|-----|
| Tier 1 — lightweight regex (improved) | 0.14 ms | 56.1% | 86.9% | 68.2% |
| Tier 2 — semantic TF-IDF kNN | 21 ms | 91.2% | 77.7% | 83.9% |
| **Combined (T1 OR T2)** | ≤ 21 ms | **91.6%** | 77.3% | 83.8% |

Tier decomposition on a 2,000-question sample: Tier-2 uniquely catches 506
risky prompts Tier-1 misses (prose-only conceptual difficulty); Tier-1
uniquely catches 56 (code patterns) at 150× lower latency. The tiers are
complementary, as designed.

**Update (48-model dataset):** the pipeline growth experiment (see
`PIPELINE.md`) raised model coverage 39 → 48, which makes ground truth
stricter — with stronger models added, fewer questions count as risky and
universal failures fell 168 → 78. Against that harder ground truth the same
checkers measure: semantic F1 79.6% (recall 86.3%), combined recall 88.4%
(F1 79.4%). Numbers in this document from the 39-model run are kept for
methodology; `data/combined_tier_evaluation.json` and
`data/semantic_evaluation_results.json` always hold the current measurement.

The whole data layer now rebuilds via a cached, dependency-ordered pipeline:
`python3 -m togmal_pipeline run` (see `PIPELINE.md`).

---

## Measured Effectiveness (full 13,000-question ground truth)

Both checker versions were evaluated against the rebuilt unified database
(12,000 MMLU-Pro questions with success rates from 39 models + 1,000 DS-1000).
"Risky" ground truth = success rate < 60% or known error patterns. The metric
compares the checker's actual gating decision (`should_analyze`) against that
ground truth.

| Metric | Original | Improved | Change |
|--------|----------|----------|--------|
| **Recall** | 7.3% | **56.1%** | 7.7× |
| **Precision** | 78.3% | **86.9%** | +8.6 pts |
| **F1** | 13.3% | **68.2%** | 5.1× |
| **FPR** | 4.8% | 20.1% | +15.3 pts |
| **Accuracy** | 33.3% | 63.2% | +29.9 pts |

Per-benchmark (improved version):

| Benchmark | Precision | Recall |
|-----------|-----------|--------|
| DS-1000 (code) | 100.0% | 90.5% |
| MMLU-Pro (knowledge) | 84.5% | 51.9% |

**Measured latency:** 0.137 ms/prompt average over 2,000 real benchmark
questions (the "< 1 ms" design goal holds).

**Interpretation of the FPR trade-off:** 20% of genuinely-safe prompts now
trigger deep analysis. That is intentional — the lightweight tier is a
pre-screener, and a Tier-2 pass on a safe prompt costs ~100 ms, while a missed
risky prompt defeats the system's purpose. Precision *rose* alongside recall,
so the extra flags are mostly warranted.

### What was changed in the improved checker

Measured trigger accuracy on the full run (share of firings that landed on
genuinely risky questions):

| Trigger | Accuracy | Status |
|---------|----------|--------|
| `dangerous_domain_medical_advice_direct` | 97.6% | new (first-person advice-seeking) |
| `numerical:equation_with_vars` | 93.3% | new |
| `unit_conversion_2_units` | 100.0% | new (graded threshold) |
| `numerical:multi_unit` | 89.7% | new (word-boundary fixed) |
| `numerical:multiple_numbers` | 88.1% | new (findall count, not regex repetition) |
| `numerical:latex_notation` | — | new (catches `$2.00 \mathrm{~mJ}$`-style questions) |
| code patterns (DS-1000) | ~100% | unchanged |

Changes vs the original:

1. `should_analyze` threshold lowered 0.3 → 0.15.
2. Numerical-complexity triggers added (numbers, units, sci-notation, LaTeX,
   subscripted equations) — these do the heavy lifting on MMLU-Pro recall.
3. Medical/legal check made context-aware: first-person advice-seeking
   ("I have…", "should I take…") scores 0.7 (CRITICAL alone); bare medical
   keywords score 0.5 only when the prompt isn't phrased as a knowledge
   question (interrogative opening, "caused by", "referred to as", …).
4. Unit-conversion trigger graded: 2 unit classes → +0.15, 3+ → +0.3.
5. Multi-step complexity requires both a step indicator and > 30 words.
6. Over-broad domains removed (generic medicine/engineering keywords).

### How to reproduce

```bash
python3 test_lightweight_effectiveness.py                  # original, 1K sample
python3 test_lightweight_effectiveness.py --improved       # improved, 1K sample
python3 test_lightweight_effectiveness.py --improved --full  # improved, all 13K
```

Results are saved to `data/lightweight_effectiveness_<version>_<size>.json`.

### Deploying the improved checker

`togmal_mcp_refactored.py` imports `lightweight_prompt_checker`. To switch:

```bash
cp lightweight_prompt_checker.py lightweight_prompt_checker_original.py
cp lightweight_prompt_checker_improved.py lightweight_prompt_checker.py
```

### Remaining known gaps (from false-negative analysis)

- ~48% of hard MMLU-Pro questions still slip through Tier-1: prose-only
  conceptual questions (law, philosophy, history) carry no lexical difficulty
  signal a regex can see. **Tier-2 (below) closes this gap** — combined
  recall is 91.6%.

---

## Tier 2: Semantic Difficulty Checker (measured)

`semantic_difficulty_checker.py` — TF-IDF (word + char n-grams, 40K features)
over all 13,000 questions; predicts a prompt's success rate as the
similarity-weighted mean of its k=10 nearest benchmark questions. Fully
offline (HuggingFace is blocked in this environment, so neural embeddings
are not an option; TF-IDF rebuilds in ~30 s from the committed snapshot).

Held-out evaluation on 2,000 questions, **excluding near-duplicate neighbors
(cosine ≥ 0.95)** so MMLU-Pro's repeated questions can't leak ground truth:

- MAE of predicted success rate: **0.184**
- Correlation predicted-vs-actual: **0.49**
- Risky-classification: **recall 91.2%, precision 77.7%, F1 83.9%**
- 98% of prompts get a confident prediction (mean top-k similarity ≥ 0.18);
  the rest return risk level `UNKNOWN` instead of guessing
- Latency: ~21 ms/prompt

```bash
python3 semantic_difficulty_checker.py build      # ~30 s, writes data/semantic_index.pkl
python3 semantic_difficulty_checker.py query "your prompt here"
python3 semantic_difficulty_checker.py evaluate   # reproduces the numbers above
```

Exposed in the MCP server (`togmal_mcp_refactored.py`) as
`semantic_difficulty_check`, alongside `get_taxonomy_section` for the
expanded taxonomy. All 9 tools smoke-tested end-to-end.

---

## Data-Quality Bug Found & Fixed: DS-1000 success rates

While building the taxonomy, every DS-1000 question showed
`success_rate = 0.0` with all-False model scores — in the original build
too, not just the rebuild. Root cause: the answer JSONLs contain model
*generations* only (`{id, code, metadata}`); the builder looked for a
`result == 'passed'` field that doesn't exist, so every answer counted as
a failure. This had inflated `Nearly_Impossible` counts (1,939 → 1,213 after
the fix) and made "universal failures" meaningless for DS-1000.

Per-question grading would require executing 3,000 generated snippets against
version-pinned test suites — not feasible here. The fix
(`unified_vector_db_builder.py`) uses the **official per-library and
per-perturbation pass rates** from xlang-ai/DS-1000 `results/*.txt` as
per-question estimates (avg 0.428, matching the published ~0.43 overall),
and leaves `model_scores` empty so downstream code never mistakes estimates
for measurements. Caveat: DS-1000 evaluation metrics reflect these
library-level estimates, not per-question ground truth.

---

## Expanded Taxonomy (data-driven, committed)

`build_expanded_taxonomy.py` generates `data/expanded_taxonomy.json` (272 KB)
and the human-readable `EXPANDED_TAXONOMY.md` from measured model behavior —
9 sections:

1. **Domain risk profiles** (21 domains): engineering is the hardest domain
   (32.6% avg success, 35% of questions nearly impossible); biology the
   safest (64.3%). Includes SOTA-lift-over-field per domain.
2. **Subject risk index** (100+ subjects): MachineDesign (22.6%),
   TransportPhenomena (22.8%), PhysicalChemistry (26.1%) lead the risk list.
3. **Universal failures**: 168 questions that all ~39 models fail
   (min 37 models per question — DS-1000's 3-model rows are excluded).
4. **Near-universal failures**: 405 questions with success < 5%.
5. **Deceptive questions**: 50 questions where SOTA models underperform the
   field by ≥ 20 points — likely traps or misleading phrasing.
6. **CoT failure modes**: complex unit conversion dominates (166 of 168
   analyzed CoT failures).
7. **Code error patterns**: the DS-1000 pattern catalog.
8. **Semantic danger clusters**: 30 ML-discovered topic clusters of hard
   questions (TF-IDF → TruncatedSVD → KMeans), e.g. state/federal statute
   law (14.5% success), moral philosophy (14.6%), heat-transfer engineering
   (15.5%), electrical circuits (16.9%), gas-law chemistry (18.1%).
9. **Risk keywords**: log-odds terms separating risky from safe questions,
   computed separately for prose and code — candidate future Tier-1 triggers.

Fetchable at runtime via the `get_taxonomy_section` MCP tool.

---

## Database Durability (the rebuild problem, solved)

**What happened:** this workspace was reset between sessions and every
gitignored artifact vanished — `data/unified_database_complete.json`,
`mcp_datastore/`, and all the scraped source data. Worse, the documented
rebuild path was broken: `autonomous_benchmark_grower.py` lists MMLU-Pro
eval results via `api.github.com`, which returns **403** when unauthenticated.

**Two fixes are now in the repo:**

### 1. Committed snapshots (fast path — no scraping ever again)

`snapshots/` (2.1 MB total, committed to git) holds the full data layer:

| Snapshot | Contents |
|----------|----------|
| `unified_database_complete.json.gz` | 13,000 questions, enrichments baked in |
| `error_taxonomy.json.gz` | SOTA-failure taxonomy |
| `cot_failure_analysis.json.gz` | 168 CoT failure analyses |
| `comprehensive_error_patterns.json.gz` | 32-pattern catalog |
| `expanded_taxonomy.json.gz` | 9-section expanded taxonomy |
| `semantic_evaluation_results.json.gz` | Tier-2 eval results |
| `combined_tier_evaluation.json.gz` | combined-system eval results |

Restore everything on any machine with one command:

```bash
python3 restore_from_snapshots.py            # data/*.json
python3 restore_from_snapshots.py --rebuild  # + mcp_datastore/ + semantic index (~2 min)
```

This also answers "where can I download the data": clone the repo and run the
restore script. Only 2.1 MB of compressed sources are versioned; the ~160 MB
of derived indexes (datastore, TF-IDF pickle) regenerate locally.

### 2. Offline rebuild from origin (when you want fresh data)

`rebuild_mmlu_pro_from_local.py` replaces the API-dependent scraper step with
a sparse git clone (no API, no rate limit):

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/TIGER-AI-Lab/MMLU-Pro.git /tmp/MMLU-Pro
cd /tmp/MMLU-Pro && git sparse-checkout set eval_results && cd -

python3 rebuild_mmlu_pro_from_local.py /tmp/MMLU-Pro/eval_results  # ~1 min
python3 ds1000_scraper.py                                          # ~1 min
python3 build_complete_unified_db.py                               # ~1 min
python3 build_mcp_datastore.py                                     # ~1 min
```

Measured end-to-end (this session): the sparse clone downloads ~200 MB of
eval zips; every subsequent step is under a minute. The rebuilt database now
covers **39 models** (up from 37).

The enrichment chain was re-run in full and its outputs are snapshotted:
`enrich_with_subjects.py` → `error_taxonomy_analyzer.py` →
`cot_failure_analyzer.py` → `analyze_all_error_patterns.py` →
`build_complete_unified_db.py`. The rebuilt database carries **215 questions
with error patterns** (up from 176 — the 39-model rebuild found more
universal/CoT failures than the original 37-model build).
