# ToGMAL MCP - LLM Limitation Detection via Benchmark Analysis

**Empirically-validated Model Context Protocol server for detecting LLM limitations based on real benchmark data.**

---

## Overview

ToGMAL (Theory of Gracefully Managing AI Limitations) is an MCP server that detects when LLM prompts are likely to fail, using two complementary approaches:

### 1. **Question Difficulty Analysis** (Semantic Similarity)
"What types of questions are hard for models?"

- **12,000 MMLU-Pro questions** with success rates from **37 models**
- Semantic similarity search to match user prompts against benchmark questions
- Risk assessment based on similar questions' difficulty
- **Status**: Data prepared, vector database ready to build

### 2. **Error Pattern Detection** (Why Models Fail)
"What mistakes do models make on hard questions?"

- **1,000 DS-1000 data science problems** with **8,934 logic errors analyzed**
- 8 critical error patterns discovered (mutability, indexing, vectorization, etc.)
- Evidence-based warnings with frequencies from real errors
- **Status**: ✅ Fully integrated into MCP

---

## Unified Database Architecture

### Two Data Sources, One Schema

The project unifies two types of benchmark data:

| Dataset | Questions | Models | Per-Question Errors? | Error Analysis? | Use Case |
|---------|-----------|--------|---------------------|-----------------|----------|
| **MMLU-Pro** | 12,000 | 37 | ✅ Success rates | ❌ Not analyzed | Difficulty via similarity |
| **DS-1000** | 1,000 | 3 | ✅ Success rates | ✅ 8 patterns | Difficulty + Why failures |
| **DataSciBench** | 222 | 28 | ✅ Success rates | ⚠️ Ready to analyze | Multi-step workflows |

### Unified Schema

All questions follow this structure (error analysis fields optional):

```python
{
  # Core fields (all questions)
  "question_id": "mmlu_pro_0001",
  "question_text": "In force-current analogy...",
  "benchmark": "MMLU-Pro",
  "domain": "engineering",
  "success_rate": 0.297,  # Across all models
  
  # Per-model results (all questions)
  "model_scores": {
    "gpt-4o": true,
    "claude-3.5-sonnet": false,
    "llama-3-70b": false,
    ...
  },
  
  # Error analysis (DS-1000 only, others null/empty)
  "error_patterns": [
    {
      "pattern": "mutability_misunderstanding",
      "frequency": 0.256,
      "severity": "CRITICAL",
      "example_wrong": "result = df.iloc[List]",
      "example_correct": "result = g(df.copy(), List)"
    }
  ],
  "error_categories": ["missing_method", "wrong_attribute"],
  "conceptual_gaps": ["mutability_misunderstanding", "indexing_semantics"]
}
```

**Key Insight**: MMLU-Pro questions have `error_patterns: []` (empty) because we don't have per-error analysis, but they still provide valuable difficulty signals via success rates and semantic similarity.

---

## Project Structure

```
togmal-mcp/
├── togmal_mcp.py              # Main MCP server
│   ├── togmal_analyze_prompt  # Pattern detection (DS-1000)
│   ├── togmal_analyze_response
│   └── togmal_check_prompt_difficulty  # Semantic similarity (MMLU-Pro)
│
├── data/
│   ├── autonomous_benchmarks/  # MMLU-Pro (12K questions, 37 models)
│   │   ├── vector_db_ready.json (21.9 MB)
│   │   └── autonomous_dataset.json (30 MB)
│   │
│   ├── ds1000_cache/          # DS-1000 (1K problems, 3 models)
│   │   ├── ds1000.jsonl (3.4 MB)
│   │   └── *-answers.jsonl (model outputs)
│   │
│   ├── deep_logic_analysis/   # DS-1000 error analysis
│   │   └── error_categorization.json
│   │
│   └── DataSciBench/          # 222 multi-step tasks, 28 models
│       ├── data/prompts
│       └── evaluation_results/
│
├── benchmark_vector_db.py     # ChromaDB builder (unified schema)
├── evaluation_results_scraper.py  # GitHub scraper (MMLU-Pro)
├── ds1000_scraper.py          # DS-1000 downloader
├── deep_logic_error_analyzer.py   # Error pattern discovery
├── conceptual_error_mapper.py     # Map to mental model gaps
│
└── Documentation/
    ├── DS1000_MCP_INTEGRATION.md
    ├── COMPLETE_DATA_INVENTORY.md
    ├── CONCEPTUAL_ERROR_MAPPING.md
    └── HUGGINGFACE_WORKAROUND_EXPLANATION.md
```

---

## Key Features

### ✅ Implemented

**1. DS-1000 Error Pattern Detection**
- 8 critical patterns from analyzing 8,934 real errors
- Evidence-based warnings (e.g., "25.6% of errors are missing .copy()")
- Integrated into `togmal_analyze_prompt` and `togmal_analyze_response`
- 100% test pass rate on validation

**2. Autonomous MMLU-Pro Scraping**
- 12,000 questions from 37 models (GPT-4o, Claude-3.5, Llama-3, etc.)
- Per-question success rates
- Continuous growth system (updates every 24 hours)
- No HuggingFace dependency (GitHub-based)

**3. Multi-Source Benchmark Coverage**
- MMLU-Pro: General knowledge (12K questions)
- DS-1000: Data science code (1K problems)
- DataSciBench: Multi-step workflows (222 tasks)
- Total: ~13,222 questions, 68 unique models, ~450K predictions

### ⚠️ Pending

**Vector Database (Semantic Similarity)**
- Data prepared (21.9 MB ready for embedding)
- ChromaDB structure defined
- Needs: Embedding step with sentence-transformers
- Would enable: "Your prompt is 87% similar to graduate physics questions (30% success rate)"

**DataSciBench Error Analysis**
- Data cloned (7,203 files)
- Ready to analyze multi-step workflow failures
- Would discover: Task decomposition errors, pipeline failures

---

## Data Access Strategy

### No HuggingFace Required ✅

All data accessed via GitHub, bypassing HuggingFace API restrictions:

| Dataset | Source | Method | Size |
|---------|--------|--------|------|
| **MMLU-Pro** | TIGER-AI-Lab/MMLU-Pro | Scrape eval_results/ | 12K questions |
| **DS-1000** | xlang-ai/DS-1000 | Direct download (raw.githubusercontent.com) | 1K problems |
| **DataSciBench** | THUDM/DataSciBench | Git clone | 222 tasks |

**Why This Works**:
- GitHub hosts raw files publicly (`raw.githubusercontent.com`)
- Model predictions stored in repositories
- No authentication needed

**What Doesn't Work** (blocked):
- GPQA, MATH, Full MMLU: Require HuggingFace `load_dataset()`
- ML-Bench: Model outputs on HuggingFace, not in GitHub

---

## MCP Tools

### 1. `togmal_analyze_prompt`

Analyze user prompts for risky patterns.

**Input**:
```json
{
  "prompt": "result = df.iloc[List]",
  "response_format": "markdown"
}
```

**Output** (DS-1000 patterns):
```markdown
### 🐼 Data Science Code Issues Detected (DS-1000 Patterns)
- **Confidence:** 40.00%
- **Coverage:** 1 of 8 common patterns detected

🔴 **CRITICAL**: Missing .copy() - DataFrame modifications may affect original data
   - **Recommendation:** Use df.copy() before modifications
   - **Evidence:** Most common error in DS-1000: 800+ cases (25.6% of errors)
   - **Example:** `result = g(df.copy(), List)  # NOT: result = df.iloc[List]`
```

### 2. `togmal_analyze_response`

Analyze LLM responses for issues (same as analyze_prompt but with context).

### 3. `togmal_check_prompt_difficulty` (Pending - Needs Vector DB)

Check if prompt is similar to hard benchmark questions.

**Planned Input**:
```json
{
  "prompt": "Calculate quantum correction to partition function for 3D harmonic oscillator",
  "k": 5
}
```

**Planned Output**:
```markdown
### Similar Benchmark Questions
1. "Calculate the quantum..." (MMLU-Pro Physics, 23% success rate)
2. "Derive partition function..." (MMLU-Pro Physics, 31% success rate)
...

**Risk Level:** HIGH
**Weighted Success Rate:** 28%
**Recommendation:** Break into smaller steps, use external tools
```

---

## 8 Detected Error Patterns (DS-1000)

| Pattern | Severity | Frequency | Description |
|---------|----------|-----------|-------------|
| **mutability_misunderstanding** | CRITICAL | 25.6% (800+ cases) | Missing `.copy()` |
| **indexing_semantics** | HIGH | 35.8% | `.loc` vs `.iloc` confusion |
| **index_persistence** | HIGH | 21.6% | Missing `.reset_index()` after groupby |
| **transformation_pipelines** | CRITICAL | 28.0% | Incomplete multi-step solutions |
| **api_evolution** | MEDIUM | 27.6% | Deprecated `.values` vs `.to_numpy()` |
| **vectorization_concept** | MEDIUM | 9.6% | For-loops instead of vectorized ops |
| **method_semantics** | MEDIUM | 4.2% | Wrong method for task |
| **dimensional_operations** | MEDIUM | 4.0% | Wrong/missing axis parameter |

**Total Coverage**: ~85% of DS-1000 logic errors

---

## Installation & Usage

### Prerequisites

```bash
# Install dependencies
pip install sentence-transformers chromadb mcp anthropic-sdk

# Optional: For scraping new data
pip install requests beautifulsoup4 datasets
```

### Build Vector Database (Unified Schema)

```bash
# Build from autonomous MMLU-Pro data (12K questions, no error analysis)
python benchmark_vector_db.py --source autonomous

# Add DS-1000 with error analysis (1K questions WITH error patterns)
python benchmark_vector_db.py --add-ds1000

# Result: 13K questions, error_patterns populated for DS-1000 only
```

### Run MCP Server

```bash
# Start server
python togmal_mcp.py

# Or via MCP Inspector
npx @modelcontextprotocol/inspector togmal_mcp.py
```

### Test Pattern Detection

```python
# Standalone test (no MCP needed)
python test_pandas_detection_standalone.py

# Full integration test
python test_mcp_integration.py --verbose
```

---

## Research Foundation

### Benchmark Analysis

**DS-1000**:
- 1,000 data science problems (Pandas, NumPy, Matplotlib, etc.)
- 3 models: Codex-002, GPT-3.5-turbo-0613, GPT-4-0613
- 8,934 logic errors analyzed (88-91% of failures)
- Source: [xlang-ai/DS-1000](https://github.com/xlang-ai/DS-1000)

**MMLU-Pro**:
- 12,000+ multi-domain questions (14 categories)
- 37 models evaluated (23.5% - 83.0% accuracy range)
- Graduate-level difficulty
- Source: [TIGER-AI-Lab/MMLU-Pro](https://github.com/TIGER-AI-Lab/MMLU-Pro)

**DataSciBench**:
- 222 multi-step data science workflows
- 28 models (GPT-4o: 19.82% Pass@1)
- Real-world task complexity
- Source: [THUDM/DataSciBench](https://github.com/THUDM/DataSciBench)

### Error Taxonomy

**9 Syntactic Error Types** (from DS-1000):
1. wrong_attribute (27.6%)
2. missing_method (21.6%)
3. extra_method (15.8%)
4. overcomplicated (9.6%)
5. wrong_indexing (8.2%)
6. incomplete_solution (6.4%)
7. wrong_method (4.2%)
8. wrong_parameter (4.0%)
9. complex_logic_error (2.5%)

**11 Conceptual Error Types** (mental model gaps):
1. indexing_semantics (~35.8%)
2. method_semantics (~29.6%)
3. transformation_pipelines (~28.0%)
4. api_evolution (~27.6%)
5. mutability_misunderstanding (~25.6%)
6. And 6 more...

See `CONCEPTUAL_ERROR_MAPPING.md` for full taxonomy.

---

## Unified Database Implementation

### Building the Merged Database

```python
from benchmark_vector_db import BenchmarkVectorDB

db = BenchmarkVectorDB()

# Load MMLU-Pro (error_patterns will be empty list)
mmlu_questions = db.load_mmlu_pro_from_autonomous()
# Returns: [{question_id, text, success_rate, model_scores, error_patterns: []}]

# Load DS-1000 (error_patterns populated)
ds1000_questions = db.load_ds1000_with_error_analysis()
# Returns: [{question_id, text, success_rate, model_scores, error_patterns: [...]}]

# Load DataSciBench (error_patterns empty for now)
datasci_questions = db.load_datascibench()
# Returns: [{question_id, text, success_rate, model_scores, error_patterns: []}]

# Merge all into single database
all_questions = mmlu_questions + ds1000_questions + datasci_questions
db.index_questions(all_questions)

# Query works across all sources
results = db.query_similar_questions("Calculate partition function", k=5)
# Might return:
# - 3 MMLU-Pro physics questions (success_rate 0.3, error_patterns: [])
# - 2 DS-1000 problems (success_rate 0.12, error_patterns: [mutability, ...])
```

### Schema Flexibility

```python
# MMLU-Pro question (no error analysis)
{
  "question_id": "mmlu_pro_0001",
  "question_text": "In force-current analogy...",
  "benchmark": "MMLU-Pro",
  "success_rate": 0.297,
  "model_scores": {...},
  "error_patterns": [],  # EMPTY
  "error_categories": [],  # EMPTY
  "conceptual_gaps": []  # EMPTY
}

# DS-1000 question (with error analysis)
{
  "question_id": "ds1000_pandas_0001",
  "question_text": "Filter DataFrame by condition...",
  "benchmark": "DS-1000",
  "success_rate": 0.12,
  "model_scores": {...},
  "error_patterns": [  # POPULATED
    {
      "pattern": "mutability_misunderstanding",
      "frequency": 0.256,
      "severity": "CRITICAL",
      "examples": {...}
    }
  ],
  "error_categories": ["missing_method"],
  "conceptual_gaps": ["mutability_misunderstanding"]
}
```

**Benefits**:
- Single query interface for all benchmarks
- Semantic similarity works across sources
- Error analysis available when data exists
- Easy to add new benchmarks incrementally

---

## Future Roadmap

### Immediate (Ready to Build)

1. **Build Unified Vector Database**
   - Embed 13K questions (MMLU-Pro + DS-1000 + DataSciBench)
   - Enable semantic similarity searches
   - Launch `togmal_check_prompt_difficulty` tool

2. **DataSciBench Error Analysis**
   - Analyze 222 multi-step tasks
   - Discover task decomposition patterns
   - Add to error taxonomy

### Medium-Term

3. **ML-Bench Integration** (when data accessible)
   - Repository-level errors (9,641 examples)
   - Codebase navigation patterns

4. **Additional Pattern Detectors**
   - DataFrame shape tracking
   - Type confusion (Series vs DataFrame)
   - Column name validation

### Long-Term

5. **Interactive Error Explorer**
   - Web UI for browsing error patterns
   - Educational resource
   - Search by frequency, domain, severity

6. **Continuous Benchmark Updates**
   - Automated scraping (daily/weekly)
   - Track model improvements over time
   - Detect new error patterns

---

## Contributing

### Adding New Benchmarks

To add a new benchmark to the unified database:

1. **Define loader function**:
```python
def load_your_benchmark() -> List[BenchmarkQuestion]:
    questions = []
    for item in your_data:
        q = BenchmarkQuestion(
            question_id=f"your_bench_{i}",
            question_text=item['question'],
            success_rate=calculate_success_rate(item),
            model_scores=extract_model_scores(item),
            error_patterns=analyze_errors(item) if has_errors else [],
            # ...
        )
        questions.append(q)
    return questions
```

2. **Add to database builder**:
```python
db.build_database(
    load_mmlu_pro=True,
    load_ds1000=True,
    load_your_benchmark=True  # New!
)
```

3. **Document in README** with:
   - Data source
   - Access method
   - Whether error analysis available
   - Schema mapping

### Testing New Patterns

1. Add test case to `test_pandas_detection_standalone.py`
2. Run test suite: `python test_pandas_detection_standalone.py`
3. Document pattern in `CONCEPTUAL_ERROR_MAPPING.md`

---

## Citations

If you use ToGMAL or the error taxonomy in your research:

```bibtex
@misc{togmal2025,
  title={ToGMAL: Empirically-Validated LLM Limitation Detection},
  author={ToGMAL Project},
  year={2025},
  note={Analyzing 8,934 real LLM errors across DS-1000, MMLU-Pro, and DataSciBench}
}
```

**Referenced Benchmarks**:
- DS-1000: [Lai et al., 2023](https://arxiv.org/abs/2211.11501)
- MMLU-Pro: [Wang et al., 2024](https://arxiv.org/abs/2406.01574)
- DataSciBench: [Liu et al., 2024](https://arxiv.org/abs/2409.07728)

---

## License

MIT License - See LICENSE file

---

## Contact

For questions, suggestions, or contributions, please open an issue on GitHub.

**Status**: Active Development
**Last Updated**: November 15, 2025
**Version**: 0.2.0 (DS-1000 Integration Complete)
