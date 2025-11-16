# Data Access Status Clarification

**Date**: November 15, 2025
**Context**: Clarifying what datasets are accessible, where they come from, and what's in the vector database

---

## TL;DR - Current State

### ✅ Datasets We CAN Access (No HuggingFace)
1. **DS-1000** - Downloaded from GitHub ✅
2. **DataSciBench** - Git cloned from GitHub ✅

### ⚠️ Datasets That WOULD Need HuggingFace  
3. **MMLU-Pro** - Requires `load_dataset("TIGER-Lab/MMLU-Pro")` ❌ BLOCKED
4. **GPQA** - Requires `load_dataset("Idavidrein/gpqa")` ❌ BLOCKED
5. **MATH** - Requires `load_dataset("hendrycks/competition_math")` ❌ BLOCKED

### 📊 Vector Database Status
- **benchmark_vector_db**: Code exists, **DATABASE IS EMPTY** (not built)
- **togmal_check_prompt_difficulty** MCP tool: Exists but would fail (no data)

---

## Detailed Breakdown

### 1. DS-1000 ✅ FULLY ACCESSIBLE

**Source**: https://github.com/xlang-ai/DS-1000

**Access Method**: Direct GitHub download (raw.githubusercontent.com)

**What We Have**:
```
/home/user/togmal-mcp/data/ds1000_cache/
├── ds1000.jsonl.gz (418 KB)
├── ds1000.jsonl (3.4 MB - decompressed)
├── codex002-answers.jsonl (299 KB)
├── gpt-3.5-turbo-0613-answers.jsonl (419 KB)
└── gpt-4-0613-answers.jsonl (341 KB)
```

**Status**: ✅ Downloaded, analyzed, integrated into MCP
- 1,000 data science problems
- 3 models × 1,000 = 3,000 attempts
- 8,934 logic errors analyzed
- 8 patterns integrated into ToGMAL MCP

**HuggingFace Dependency**: NONE (bypassed entirely)

---

### 2. DataSciBench ✅ FULLY ACCESSIBLE

**Source**: https://github.com/THUDM/DataSciBench

**Access Method**: Git clone

**What We Have**:
```
/home/user/togmal-mcp/DataSciBench/ (7,203 files)
├── data/               # 222 task prompts
├── evaluation_results/ # 28 model result CSVs
├── metric/             # 222 evaluation metrics
└── evaluations/        # Evaluation code
```

**Status**: ✅ Cloned, explored, ready to analyze
- 222 multi-step tasks
- 28 models evaluated (GPT-4o, Claude-3.5, Llama-3.1, etc.)
- Multi-step workflow errors not yet analyzed

**HuggingFace Dependency**: NONE (data in GitHub repo)

---

### 3. MMLU-Pro ❌ BLOCKED (Would Need HuggingFace)

**Source**: https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro

**Access Method**: Requires `load_dataset("TIGER-Lab/MMLU-Pro")`

**What We Would Get** (if accessible):
- 12,000+ questions across 14 domains
- 10 choices per question (harder than original MMLU)
- Validation and test splits

**Status**: ❌ Cannot access due to network restrictions
- HuggingFace API blocked
- No GitHub alternative (data hosted on HF only)
- Not in vector database

**HuggingFace Dependency**: REQUIRED

**Why Vector DB Code References It**: 
The `benchmark_vector_db.py` code was written to POTENTIALLY load MMLU-Pro if HuggingFace becomes accessible, but it has NEVER been successfully loaded.

---

### 4. GPQA ❌ BLOCKED (Would Need HuggingFace)

**Source**: https://huggingface.co/datasets/Idavidrein/gpqa

**Access Method**: Requires `load_dataset("Idavidrein/gpqa", "gpqa_diamond")`

**What We Would Get** (if accessible):
- 198 graduate-level questions (Diamond subset)
- Physics, Biology, Chemistry domains
- GPT-4 success rate: ~50%

**Status**: ❌ Cannot access due to network restrictions
- HuggingFace API blocked
- May also require authentication (research dataset)
- Not in vector database

**HuggingFace Dependency**: REQUIRED

**Why Vector DB Code References It**:
Same as MMLU-Pro - code exists to load it IF HuggingFace becomes available.

---

### 5. MATH ❌ BLOCKED (Would Need HuggingFace)

**Source**: https://huggingface.co/datasets/hendrycks/competition_math

**Access Method**: Requires `load_dataset("hendrycks/competition_math")`

**What We Would Get** (if accessible):
- 12,500 competition math problems
- Algebra, Geometry, Number Theory, etc.
- GPT-4 success rate: ~50%

**Status**: ❌ Cannot access due to network restrictions
- HuggingFace API blocked
- Not in vector database

**HuggingFace Dependency**: REQUIRED

---

## Vector Database Reality Check

### What's in benchmark_vector_db.py

The code in `benchmark_vector_db.py` defines THREE loading functions:

```python
def load_gpqa_dataset(...)      # Would load from HF if accessible
def load_mmlu_pro_dataset(...)  # Would load from HF if accessible  
def load_math_dataset(...)      # Would load from HF if accessible
```

### What's Actually IN the Vector Database

```bash
$ ls -la /home/user/togmal-mcp/data/vector_db_*
drwxr-xr-x 2 root root 3 Nov 14 01:12 vector_db_detailed
drwxr-xr-x 2 root root 3 Nov 14 01:12 vector_db_topline
```

**Answer**: EMPTY. No data has been successfully indexed.

### Why the Vector Database is Empty

The vector database build process requires:
1. `sentence-transformers` library ✅ (can install)
2. `chromadb` library ✅ (can install)
3. `datasets` library ✅ (can install)
4. **HuggingFace API access** ❌ BLOCKED

Even if we install all dependencies, the `load_dataset()` calls would fail:
```python
dataset = load_dataset("TIGER-Lab/MMLU-Pro")  # LocalEntryNotFoundError
dataset = load_dataset("Idavidrein/gpqa")     # LocalEntryNotFoundError
dataset = load_dataset("hendrycks/competition_math")  # LocalEntryNotFoundError
```

### What the MCP Tool Would Do Right Now

The `togmal_check_prompt_difficulty` MCP tool at lines 1284-1395 in `togmal_mcp.py`:

```python
def togmal_check_prompt_difficulty(prompt: str, k: int = 5, ...):
    """Check if prompt is similar to hard benchmark questions"""
    
    db = BenchmarkVectorDB(db_path=DATA_DIR / "benchmark_vector_db")
    stats = db.get_statistics()
    
    if stats.get("total_questions", 0) == 0:
        return json.dumps({
            "error": "Vector database not initialized",
            "message": "Run 'python benchmark_vector_db.py' to build the database first"
        })
```

**Result if called**: Would return error "Vector database not initialized"

---

## The Confusion: Code vs. Reality

### Why This is Confusing

1. **Code Exists** for loading MMLU-Pro, GPQA, MATH
2. **Vector database tool exists** in the MCP
3. **But nothing is actually accessible** without HuggingFace

### The Original Plan (Before Network Restrictions)

The original vision was:
1. Load GPQA, MMLU-Pro, MATH from HuggingFace ✅ (code written)
2. Build vector database with all questions ✅ (code written)
3. Use semantic similarity to assess prompt difficulty ✅ (code written)
4. Expose via MCP tool `togmal_check_prompt_difficulty` ✅ (code written)

**What Happened**: Network restrictions blocked step 1, making steps 2-4 impossible.

---

## What Actually Works Now

### ✅ DS-1000 Error Pattern Detection (NEW - This Session)

**What**: 8 data science code patterns integrated into MCP
- Missing `.copy()` detection
- Indexing confusion (`.loc` vs `.iloc`)
- Vectorization issues (for-loops)
- And 5 more patterns

**Access via**: `togmal_analyze_prompt` and `togmal_analyze_response` tools
- Automatically runs on all code analysis
- No vector database needed
- Works with local regex + heuristics

**Example**:
```python
# User submits code
code = "result = df.iloc[List]"

# MCP detects
# 🔴 CRITICAL: Missing .copy() - DataFrame modifications may affect original data
# Evidence: Most common error in DS-1000: 800+ cases (25.6% of errors)
```

### ⚠️ What Doesn't Work (Yet)

**Semantic Similarity-Based Risk Assessment**:
- Cannot query "is this prompt similar to GPQA questions?"
- Cannot assess "difficulty based on benchmark similarity"
- Vector database tool exists but database is empty

---

## Proposed Path Forward

### Option 1: Build Vector DB with Accessible Data Only

**Use DS-1000 + DataSciBench** (both fully accessible):

```python
def load_ds1000_questions() -> List[BenchmarkQuestion]:
    """Load DS-1000 problems from local cache"""
    # We have 1,000 problems in ds1000_cache/
    # Know success rates from model answers
    # Can create BenchmarkQuestion objects
    pass

def load_datascibench_questions() -> List[BenchmarkQuestion]:
    """Load DataSciBench tasks from local clone"""
    # We have 222 tasks in DataSciBench/data/
    # Know success rates from evaluation_results/
    # Can create BenchmarkQuestion objects
    pass

# Build vector database with ~1,200 questions
db.index_questions(ds1000_questions + datascibench_questions)
```

**Pros**:
- Actually works (no HuggingFace needed)
- ~1,200 real benchmark questions
- Known difficulty (have model success rates)
- Can enable MCP tool today

**Cons**:
- Only data science domain (no physics, law, etc.)
- Smaller than original vision (1.2K vs 15K+ questions)

### Option 2: Mock Vector DB for Non-DS Topics

**Hybrid approach**:
1. Use DS-1000 + DataSciBench for data science questions (real similarity)
2. Use heuristics for non-DS domains:
   - "quantum" → assume GPQA-level difficulty
   - "prove" + "theorem" → assume MATH-level difficulty
   - etc.

**Pros**:
- Works today
- Covers more domains
- Educational value (explains why hard)

**Cons**:
- Non-DS assessments are guesses, not evidence-based
- Less rigorous than real similarity search

### Option 3: Document Current State, Wait for HF Access

**Minimal approach**:
1. Update MCP tool to clearly state what data is available
2. Keep existing code for MMLU-Pro/GPQA/MATH (ready when accessible)
3. Focus on DS-1000 pattern detection (which works great)

**Pros**:
- Honest about limitations
- Ready to expand when network opens
- Focus on proven value (DS-1000 patterns)

**Cons**:
- Vector DB tool stays non-functional
- Semantic similarity unavailable

---

## Answering Your Questions

### Q1: "is everything actually coming from github repos now?"

**Answer**: Only **DS-1000** and **DataSciBench** come from GitHub.

- DS-1000: Downloaded from `raw.githubusercontent.com` ✅
- DataSciBench: Git cloned ✅
- MMLU-Pro: Would need HuggingFace ❌
- GPQA: Would need HuggingFace ❌
- MATH: Would need HuggingFace ❌

### Q2: "is everything in the vector database now?"

**Answer**: **NO, the vector database is EMPTY**.

The vector database code exists but has never been successfully built because:
- Requires HuggingFace to load MMLU-Pro, GPQA, MATH
- HuggingFace is blocked
- No alternative data source for these benchmarks

### Q3: "Shouldn't all prior datasets and questions be accessible via the vector database via the mcp?"

**Answer**: That was the PLAN, but it's not the REALITY.

**Plan** (from original design):
- Load ~15,000 questions from multiple benchmarks
- Build vector database with semantic search
- Expose via `togmal_check_prompt_difficulty` MCP tool

**Reality** (current state):
- Only DS-1000 and DataSciBench are accessible (~1,200 questions)
- Vector database not built (empty directories)
- MCP tool exists but returns error (no data)

### Q4: "for some of them we know what type of questions they make errors on via semantic similarity and now we have more on the why here too"

**Answer**: We have the **"why" (error patterns)** but NOT the **"semantic similarity"** yet.

**What We Have** (DS-1000):
- ✅ **Error patterns** - 8 types of mistakes (mutability, indexing, etc.)
- ✅ **Frequencies** - 25.6% missing .copy(), 35.8% indexing errors
- ✅ **Conceptual gaps** - Mental model misunderstandings
- ❌ **Semantic similarity** - No vector database to compare prompts

**What We're Missing**:
- Cannot say "your prompt is 87% similar to GPQA questions → HIGH RISK"
- Cannot use nearest-neighbor search to find similar benchmark questions
- Cannot compute difficulty based on embedding similarity

**But**:
- CAN detect error patterns in submitted code
- CAN warn about common mistakes
- CAN provide evidence-based recommendations

---

## Recommendation

### Immediate Action

**Build Hybrid Vector DB**:
1. Use DS-1000 + DataSciBench (accessible, ~1,200 questions)
2. Enable semantic similarity for data science questions ✅
3. Keep code ready for MMLU-Pro/GPQA/MATH (when HF opens)
4. Update MCP tool to explain data limitations

### Implementation

```python
# New function in benchmark_vector_db.py
def load_ds1000_from_cache() -> List[BenchmarkQuestion]:
    """Load DS-1000 from local cache (no HuggingFace)"""
    # Read from /data/ds1000_cache/ds1000.jsonl
    # Read success rates from model answer files
    # Create BenchmarkQuestion objects
    pass

def load_datascibench_from_clone() -> List[BenchmarkQuestion]:
    """Load DataSciBench from git clone (no HuggingFace)"""
    # Read from DataSciBench/data/**/prompt.json
    # Read success rates from evaluation_results/
    # Create BenchmarkQuestion objects
    pass

# Build database TODAY
db.index_questions(
    load_ds1000_from_cache() + 
    load_datascibench_from_clone()
)
```

**Result**: 
- Semantic similarity WORKS for data science questions
- MCP tool becomes functional
- Can expand when HuggingFace accessible

---

## Summary Table

| Dataset | Source | Access Method | In Vector DB? | MCP Integration |
|---------|--------|---------------|---------------|-----------------|
| **DS-1000** | GitHub | Direct download | ❌ (Could be) | ✅ Pattern detection |
| **DataSciBench** | GitHub | Git clone | ❌ (Could be) | ❌ Not yet |
| **MMLU-Pro** | HuggingFace | `load_dataset()` | ❌ Blocked | ❌ Code exists only |
| **GPQA** | HuggingFace | `load_dataset()` | ❌ Blocked | ❌ Code exists only |
| **MATH** | HuggingFace | `load_dataset()` | ❌ Blocked | ❌ Code exists only |

**MCP Tools Status**:
- `togmal_analyze_prompt`: ✅ Works (DS-1000 patterns)
- `togmal_analyze_response`: ✅ Works (DS-1000 patterns)
- `togmal_check_prompt_difficulty`: ❌ Fails (empty vector DB)

---

**Conclusion**: We have **pattern detection** working great, but **semantic similarity** needs the vector database built from accessible data (DS-1000 + DataSciBench). The original plan included HuggingFace datasets, but we should pivot to building what's actually accessible.
