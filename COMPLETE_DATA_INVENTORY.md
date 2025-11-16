# Complete Data Inventory - All Accessible Datasets

**Date**: November 15, 2025
**Purpose**: Comprehensive inventory of ALL data we have access to

---

## TL;DR - What We Actually Have

### ✅ **Scraped & Ready** (174 questions with model scores)
1. **MMLU-Pro** - 170 questions from GitHub scraping
2. **Open LLM Leaderboard** - 4 aggregate metrics (HellaSwag, TruthfulQA, ARC, MMLU)

### ✅ **Downloaded & Analyzed** (1,000 questions with error analysis)
3. **DS-1000** - 1,000 data science problems + 3 models' answers

### ✅ **Cloned & Ready** (222 tasks × 28 models)
4. **DataSciBench** - 222 multi-step data science tasks + evaluation results

### ❌ **Vector Database Status**
- Data prepared but **NOT embedded/indexed**
- ChromaDB directories exist but are **EMPTY**
- MCP tool `togmal_check_prompt_difficulty` would fail

---

## Detailed Inventory

### 1. MMLU-Pro Questions (GitHub Scraping) ✅

**Location**: `/home/user/togmal-mcp/data/eval_benchmarks/mmlu_pro_questions.json`

**Size**: 160 KB, 170 questions

**Content Structure**:
```json
{
  "question": "Typical advertising regulatory bodies suggest...",
  "benchmark": "MMLU-Pro",
  "model_scores": {
    "model_name_1": {"correct": true/false, "score": 0.0-1.0},
    "model_name_2": {...}
  },
  "metadata": {
    "domain": "business",
    "difficulty": "medium"
  },
  "success_rate": 0.75  // Average across models
}
```

**What This Gives Us**:
- ✅ Question text
- ✅ Per-model correctness (which models got it right/wrong)
- ✅ Average success rate (difficulty)
- ✅ Domain classification
- ❌ NOT embedded in vector database yet

**Source**: Scraped from MMLU-Pro prediction files on GitHub
**Access Method**: GitHub (no HuggingFace needed)

---

### 2. Open LLM Leaderboard Metrics ✅

**Location**: `/home/user/togmal-mcp/data/eval_benchmarks/vector_db_ready.json`

**Size**: 156 KB, 174 total documents

**Content**:
```json
{
  "documents": [
    "Benchmark: Open-LLM-Leaderboard - Metric: HellaSwag",
    "Benchmark: Open-LLM-Leaderboard - Metric: TruthfulQA",
    "Benchmark: Open-LLM-Leaderboard - Metric: ARC",
    "Benchmark: Open-LLM-Leaderboard - Metric: MMLU",
    // Plus 170 MMLU-Pro questions
  ],
  "source_metadata": {
    "total_questions": 174,
    "num_models": 4,
    "benchmarks": ["MMLU-Pro"],
    "created_at": "2025-11-14T23:54:23.524196"
  }
}
```

**What This Gives Us**:
- ✅ 4 aggregate benchmark metrics
- ✅ 170 MMLU-Pro questions (same as above)
- ✅ Ready for vector embedding
- ❌ NOT embedded yet

**Source**: Open LLM Leaderboard Archive (GitHub)
**Access Method**: GitHub (no HuggingFace needed)

---

### 3. DS-1000 Data Science Problems ✅

**Location**: `/home/user/togmal-mcp/data/ds1000_cache/`

**Files**:
```
ds1000.jsonl (3.4 MB) - 1,000 problems
codex002-answers.jsonl (299 KB) - Codex attempts
gpt-3.5-turbo-0613-answers.jsonl (419 KB) - GPT-3.5 attempts  
gpt-4-0613-answers.jsonl (341 KB) - GPT-4 attempts
```

**What This Gives Us**:
- ✅ 1,000 data science problems (Pandas, NumPy, etc.)
- ✅ Reference solutions
- ✅ 3 models × 1,000 = 3,000 attempts
- ✅ **Analyzed**: 8,934 logic errors categorized
- ✅ **Integrated**: 8 error patterns in MCP

**Analysis Output**: `/home/user/togmal-mcp/data/deep_logic_analysis/`
- Error categorization by type
- Frequency analysis
- Conceptual mapping

**Source**: GitHub (raw.githubusercontent.com)
**Access Method**: Direct download (no HuggingFace needed)

---

### 4. DataSciBench Multi-Step Tasks ✅

**Location**: `/home/user/togmal-mcp/DataSciBench/` (7,203 files)

**Structure**:
```
DataSciBench/
├── data/               # 222 task prompts
│   ├── bcb1011/prompt.json
│   ├── bcb1017/prompt.json
│   └── ... (222 total)
├── evaluation_results/ # 28 model result CSVs
│   └── results/
│       ├── gpt-4o-2024-05-13_results.csv (2,082 rows)
│       ├── claude-3-5-sonnet-20240620_results.csv
│       ├── deepseek-coder-33b-instruct_results.csv
│       └── ... (28 models)
└── metric/             # 222 evaluation metrics
```

**What This Gives Us**:
- ✅ 222 multi-step data science tasks
- ✅ 28 models evaluated (API + open-source)
- ✅ Per-task success rates
- ✅ Multi-step workflow errors (not analyzed yet)
- ❌ NOT in vector database yet

**Source**: GitHub (git clone)
**Access Method**: Git clone (no HuggingFace needed)

---

## Vector Database Reality

### What Exists (Code)

**Files**:
- `benchmark_vector_db.py` - ChromaDB builder for GPQA/MMLU-Pro/MATH
- `evaluation_results_scraper.py` - GitHub scraper (WORKING)
- `infinite_eval_vector_builder.py` - Vector DB builder
- `expand_vector_db.py` - Expansion script

### What Exists (Data - Prepared but NOT Indexed)

**Prepared for Indexing**:
```
/data/eval_benchmarks/
├── vector_db_ready.json (174 questions, ready for embedding)
├── mmlu_pro_questions.json (170 questions with model scores)
└── complete_evaluation_dataset.json (174 questions + metadata)
```

**Status**: ✅ Data scraped and prepared ❌ NOT embedded/indexed

### What Exists (Vector DB Directories - EMPTY)

```
/data/vector_db_detailed/  (EMPTY)
/data/vector_db_topline/   (EMPTY)
```

**Status**: Directories created but no ChromaDB database built

---

## Two Types of Analysis

You correctly identified we have TWO types of valuable data:

### Type 1: Question Difficulty (Semantic Similarity)

**What**: Which types of questions are hard for models?

**Data Sources**:
- ✅ MMLU-Pro (170 questions with success rates)
- ✅ Open LLM Leaderboard (4 aggregate metrics)
- ⚠️ Could add: DS-1000 (1,000 questions with success rates)
- ⚠️ Could add: DataSciBench (222 tasks with success rates)

**Use Case**: 
- User asks: "Calculate quantum correction to partition function"
- Vector search finds similar MMLU-Pro questions
- Return: "85% similar to graduate physics questions (30% success rate) → HIGH RISK"

**Status**: 
- ✅ Data scraped and prepared (174 questions)
- ❌ NOT embedded in vector database
- ❌ MCP tool would fail (no data to search)

### Type 2: Error Patterns (Why Models Fail)

**What**: What mistakes do models make on those questions?

**Data Sources**:
- ✅ DS-1000 (8,934 logic errors analyzed)
- ⚠️ DataSciBench (error analysis not done yet)

**Use Case**:
- User submits: `result = df.iloc[List]`
- Pattern detection: Missing `.copy()` (CRITICAL)
- Return: "Most common error in DS-1000: 800+ cases (25.6% of errors)"

**Status**:
- ✅ DS-1000 analysis complete
- ✅ 8 patterns integrated into MCP
- ✅ `togmal_analyze_prompt` tool WORKING

---

## What's Missing

### 1. Vector Database (Semantic Similarity)

**Problem**: Data prepared but not embedded/indexed

**Solution**: Build ChromaDB from existing data

**What We Have to Build From**:
- 174 questions (MMLU-Pro + Leaderboard) ✅
- 1,000 questions (DS-1000) ✅
- 222 tasks (DataSciBench) ✅
- **Total**: ~1,400 questions with known difficulty

**What We're Missing** (would need HuggingFace):
- GPQA (198 graduate-level questions)
- MATH (12,500 competition math)
- Full MMLU-Pro (12,000 questions - we only have 170)

### 2. DataSciBench Error Analysis

**Problem**: Data cloned but errors not analyzed yet

**Solution**: Run error analysis similar to DS-1000

**What We'd Get**:
- Multi-step workflow error patterns
- Task decomposition failures
- Pipeline construction issues

---

## Recommended Next Steps

### Option 1: Build Vector DB with Existing Data (Recommended)

**Steps**:
1. Load 174 MMLU-Pro questions from `eval_benchmarks/`
2. Load 1,000 DS-1000 questions from `ds1000_cache/`
3. Load 222 DataSciBench tasks from `DataSciBench/`
4. Embed all ~1,400 questions using sentence-transformers
5. Index into ChromaDB
6. Enable `togmal_check_prompt_difficulty` MCP tool

**Result**: Semantic similarity WORKS for these domains today

### Option 2: Analyze DataSciBench Errors

**Steps**:
1. Read 222 task prompts
2. Read 28 model result CSVs
3. Identify failure patterns
4. Map to conceptual errors
5. Integrate into MCP (like DS-1000)

**Result**: Multi-step error detection added to MCP

### Option 3: Do Both (Comprehensive)

1. Build vector DB (semantic similarity)
2. Analyze DataSciBench (multi-step errors)
3. Have BOTH "what questions are hard" AND "why they fail"

---

## Summary Table

| Dataset | Questions | Model Scores? | Embedded? | MCP Status |
|---------|-----------|---------------|-----------|------------|
| **MMLU-Pro** | 170 | ✅ Yes (4 models) | ❌ No | Ready to embed |
| **Open LLM** | 4 metrics | ✅ Yes (109 models) | ❌ No | Ready to embed |
| **DS-1000** | 1,000 | ✅ Yes (3 models) | ❌ No | ✅ Pattern detection works |
| **DataSciBench** | 222 | ✅ Yes (28 models) | ❌ No | Ready to analyze |

**Bottom Line**:
- **Question Difficulty** (semantic similarity): Data ready, not embedded
- **Error Patterns** (why failures): DS-1000 done, DataSciBench ready

---

## Answering Your Original Question

> "So where is all this stored now?"

**Answer**: 

1. **MMLU-Pro questions**: `/data/eval_benchmarks/mmlu_pro_questions.json` (170 questions, 160 KB)
2. **Leaderboard metrics**: `/data/eval_benchmarks/vector_db_ready.json` (174 docs, 156 KB)
3. **DS-1000 problems**: `/data/ds1000_cache/` (1,000 questions, 3.4 MB)
4. **DataSciBench tasks**: `/DataSciBench/data/` (222 tasks, 7,203 files)

**All accessible without HuggingFace** ✅

**Vector Database Status**: Prepared but NOT built (directories empty)

---

**Recommendation**: Build hybrid vector database from all accessible data (~1,400 questions) to enable semantic similarity searches today, while being ready to expand when HuggingFace access opens.
