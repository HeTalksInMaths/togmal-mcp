# Lightweight Checker: Measured Results & Database Durability

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

- ~48% of hard MMLU-Pro questions still slip through: prose-only conceptual
  questions (law, philosophy, history) carry no lexical difficulty signal a
  regex can see. Closing that gap needs the Tier-2 semantic-similarity lookup
  (TF-IDF / vector DB), not more regexes — that is by design.

---

## Database Durability (the rebuild problem, solved)

**What happened:** this workspace was reset between sessions and every
gitignored artifact vanished — `data/unified_database_complete.json`,
`mcp_datastore/`, and all the scraped source data. Worse, the documented
rebuild path was broken: `autonomous_benchmark_grower.py` lists MMLU-Pro
eval results via `api.github.com`, which returns **403** when unauthenticated.

**Two fixes are now in the repo:**

### 1. Committed snapshot (fast path — no scraping ever again)

`snapshots/unified_database_complete.json.gz` (2 MB) is the full 13,000-question
database, committed to git. Restore on any machine:

```bash
mkdir -p data
gunzip -c snapshots/unified_database_complete.json.gz > data/unified_database_complete.json
python3 build_mcp_datastore.py   # regenerates mcp_datastore/ (~116 MB) in ~1 min
```

This also answers "where can I download the data": clone the repo, run the two
commands above. Only the 2 MB source snapshot is versioned; the 116 MB of
derived indexes are regenerated locally.

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

**Note:** the CoT-failure and error-taxonomy enrichments
(`cot_failure_analysis.json`, `error_taxonomy.json`,
`comprehensive_error_patterns.json`) were also lost in the reset and are not
yet regenerated — the snapshot contains success rates and DS-1000 error data
but not the 176 MMLU-Pro error-pattern annotations. Re-run the analyzer
scripts (`cot_failure_analyzer.py`, `error_taxonomy_analyzer.py`,
`analyze_all_error_patterns.py`) before `build_complete_unified_db.py` to
restore those, then refresh the snapshot.
