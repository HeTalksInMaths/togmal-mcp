# Benchmark Expansion Plan for ToGMAL MCP

## Current State Analysis

### Coverage Gaps
- **DS/ML Questions**: Only 1,000 / 13,000 (7.7%)
- **Solutions**: 0% have stored solutions ⚠️
- **Difficulty**: All DS/ML marked as 1.0 (hard) - needs better distribution
- **Modern ML/AI**: Missing PyTorch, Transformers, MLOps, LLM fine-tuning

### Current DS/ML Breakdown
| Domain | Questions | Coverage |
|--------|-----------|----------|
| Pandas | 291 | Good |
| Numpy | 220 | Good |
| Matplotlib | 155 | Moderate |
| Sklearn | 115 | Moderate |
| Scipy | 106 | Moderate |
| **PyTorch** | 68 | **Too low** |
| **Tensorflow** | 45 | **Too low** |
| **Transformers** | 0 | **Missing** |
| **MLOps** | 0 | **Missing** |

---

## Top Priority Benchmarks to Add

### 1. **MLE-Bench** ⭐⭐⭐⭐⭐ HIGHEST PRIORITY

**What it is**: Machine Learning Engineering benchmark with 75 Kaggle competitions

**Why add it**:
- ✅ End-to-end ML project scenarios
- ✅ Real-world data science workflows
- ✅ Ground truth: Kaggle leaderboard scores
- ✅ Model answers: Winning solutions available
- ✅ Covers: EDA, feature engineering, model training, evaluation

**Data Available**:
- Competition descriptions
- Datasets (can reference, not store)
- Winning solutions (code + explanations)
- Performance metrics (AUC, F1, RMSE, etc.)
- Difficulty: Competition tier (Getting Started → Master)

**Integration**:
```python
{
    "question_id": "mle_bench_titanic",
    "question_text": "Predict survival on the Titanic...",
    "domain": "Machine Learning",
    "subdomain": "Binary Classification",
    "difficulty_score": 0.2,  # Getting Started competition
    "solution": {
        "winning_approach": "Ensemble of RF + XGBoost",
        "code": "...",
        "score": 0.82,  # Leaderboard accuracy
        "techniques": ["feature_engineering", "ensembling"]
    },
    "metrics": ["accuracy", "auc_roc"],
    "dataset_info": "891 passengers, 12 features"
}
```

**Expected Questions**: ~75-150 (could expand with different approaches per competition)

---

### 2. **SWE-Bench** ⭐⭐⭐⭐⭐ HIGHEST PRIORITY

**What it is**: 2,294 real GitHub issues from popular Python repos

**Why add it**:
- ✅ Real-world software engineering tasks
- ✅ Covers: bug fixes, features, refactoring
- ✅ Ground truth: Actual merged PRs
- ✅ Score rates: pass@k on test suites
- ✅ Repos: Django, Flask, Matplotlib, Scikit-learn, etc.

**Data Available**:
- Issue descriptions
- Repository context (files, dependencies)
- Gold patch (the actual fix)
- Test cases (pass/fail evaluation)
- Difficulty: Implicit from resolution time + PR complexity

**Integration**:
```python
{
    "question_id": "swe_bench_django_12345",
    "question_text": "Fix QuerySet.filter() not working with...",
    "domain": "Software Engineering",
    "subdomain": "Django",
    "difficulty_score": 0.75,  # Based on lines changed + resolution time
    "solution": {
        "patch": "diff --git a/django/db/models/query.py...",
        "files_changed": ["django/db/models/query.py"],
        "test_patch": "...",
        "explanation": "The issue was in..."
    },
    "repo": "django/django",
    "issue_number": 12345,
    "pass_at_1": 0.05,  # How often models solve it first try
    "pass_at_10": 0.23
}
```

**Expected Questions**: ~2,294

---

### 3. **BigCodeBench** ⭐⭐⭐⭐

**What it is**: 1,140 challenging, practical coding tasks

**Why add it**:
- ✅ Function-level tasks (like HumanEval but harder)
- ✅ Real-world libraries (not just stdlib)
- ✅ Test-based evaluation
- ✅ Covers: data processing, algorithms, API usage

**Expected Questions**: ~1,140

---

### 4. **MBPP (Mostly Basic Programming Problems)** ⭐⭐⭐

**What it is**: 974 entry-level to intermediate Python problems

**Why add it**:
- ✅ Better difficulty distribution (we need more easy/medium)
- ✅ Solutions + test cases included
- ✅ Good for learning fundamentals

**Expected Questions**: ~974

---

### 5. **HumanEval** ⭐⭐⭐

**What it is**: 164 hand-written Python function problems

**Why add it**:
- ✅ Clean, well-documented
- ✅ Standard benchmark for code generation
- ✅ Test cases for evaluation

**Expected Questions**: ~164

---

## Implementation Plan

### Phase 1: Add MLE-Bench + SWE-Bench (Highest Value)

**Week 1-2: Data Collection**
```bash
# Download benchmarks
git clone https://github.com/openai/mle-bench
git clone https://github.com/princeton-nlp/SWE-bench

# Extract question + solution pairs
python extract_mle_bench.py  # Parse Kaggle competitions
python extract_swe_bench.py  # Parse GitHub issues
```

**Week 2-3: Data Integration**
```python
# Unify schema
{
    "question_id": str,
    "question_text": str,
    "domain": str,
    "subdomain": str,
    "difficulty_score": float,  # Compute from metrics
    "solution": {
        "code": str,
        "explanation": str,
        "score": float,  # Performance metric
        "approach": str
    },
    "evaluation_metrics": list,
    "test_cases": list,
    "source_benchmark": str  # "mle_bench", "swe_bench", etc.
}
```

**Week 3-4: Re-tune Semantic Scorer**
- Re-index: 13K → ~15K-16K questions
- Re-run Bayesian optimization (should improve with more ML/AI coverage)
- Expected new Precision@10: **75-80%** (more domain coherence in ML)

### Phase 2: Add Coding Benchmarks (BigCodeBench, MBPP, HumanEval)

**Week 5-6**:
- Add 1,140 + 974 + 164 = 2,278 more questions
- Total: ~17K-18K questions
- Re-tune semantic scorer

### Phase 3: Enhanced Evaluation

**New Capabilities**:
```python
# MCP tool: evaluate_solution
evaluate_solution(
    question_id="mle_bench_titanic",
    solution_code="...",
    metrics=["accuracy", "auc_roc"]
)
# Returns: {"accuracy": 0.78, "auc_roc": 0.82, "baseline_score": 0.82}

# MCP tool: compare_with_winning_solution
compare_with_winning_solution(
    question_id="swe_bench_django_12345",
    user_solution="..."
)
# Returns: {
#   "passes_tests": True,
#   "similarity_to_gold": 0.65,
#   "approach_matches": ["refactoring", "edge_case_handling"]
# }
```

---

## Expected Impact

### Quantitative Improvements

| Metric | Current | After Phase 1 | After Phase 2 |
|--------|---------|---------------|---------------|
| **Total Questions** | 13,000 | ~15,500 | ~18,000 |
| **DS/ML Coverage** | 7.7% | **25%** | **30%** |
| **With Solutions** | 0% | **15%** | **20%** |
| **Semantic P@10** | 74% | **76-78%** | **78-80%** |
| **Modern ML (PyTorch/TF)** | 113 | **500+** | **800+** |

### Qualitative Improvements

**Current**:
- ❌ Can't evaluate user solutions
- ❌ No real-world ML engineering tasks
- ❌ Limited to basic DS (Pandas/Numpy)
- ❌ No software engineering coverage

**After**:
- ✅ Can evaluate solutions against test cases
- ✅ 75 full Kaggle competition scenarios
- ✅ 2,294 real GitHub issues (SWE tasks)
- ✅ Winning solutions as reference
- ✅ Performance metrics (pass@k, leaderboard scores)
- ✅ Better difficulty distribution (easy → master)

---

## New MCP Capabilities

### 1. Solution Evaluation
```python
# User submits code for Titanic competition
result = mcp.evaluate_solution(
    question_id="mle_bench_titanic",
    code=user_code,
    test_data=test_df
)
# Returns: {"accuracy": 0.78, "rank_percentile": 65, "passes": True}
```

### 2. Progressive Difficulty
```python
# Get Kaggle competitions by difficulty
competitions = mcp.find_similar_questions(
    query="classification with tabular data",
    domain="Machine Learning",
    difficulty_range=(0.0, 0.3),  # Getting Started competitions
    top_k=5
)
```

### 3. Compare Solutions
```python
# Compare user's approach to winning solutions
comparison = mcp.compare_solutions(
    question_id="mle_bench_house_prices",
    user_code=user_code
)
# Returns: {
#   "techniques_used": ["xgboost", "feature_engineering"],
#   "missing_techniques": ["ensembling", "stacking"],
#   "performance_gap": 0.05,  # RMSE difference
#   "suggestions": ["Try ensemble methods", "Feature interaction terms"]
# }
```

### 4. Real-World Engineering Tasks
```python
# Find similar bugs to one user encountered
issues = mcp.find_similar_questions(
    query="Django ORM QuerySet filter not working",
    domain="Software Engineering",
    subdomain="Django"
)
# Returns actual GitHub issues with solutions
```

---

## Implementation Priorities

### MUST HAVE (Phase 1)
1. ✅ **MLE-Bench** - 75 Kaggle competitions with solutions
2. ✅ **SWE-Bench** - 2,294 real GitHub issues
3. ✅ Extract solutions + metrics
4. ✅ Re-tune semantic scorer

### SHOULD HAVE (Phase 2)
5. BigCodeBench - 1,140 practical tasks
6. MBPP - 974 basic Python problems
7. HumanEval - 164 function problems
8. Solution evaluation tools

### NICE TO HAVE (Phase 3)
9. LiveCodeBench - competitive programming
10. Fine-tune sentence transformers on our data
11. Hybrid semantic + code similarity scoring
12. Interactive evaluation environment

---

## Technical Considerations

### Storage
- Current: ~100MB (13K questions)
- After Phase 1: ~150-200MB (15.5K questions + solutions)
- After Phase 2: ~250-300MB (18K questions)
- Solutions (code) add ~50-100MB

### Re-indexing
- Semantic scorer needs re-training: ~30-60 minutes
- Bayesian optimization: ~20 evaluations × 30s = 10 minutes
- Total: **1-2 hours per re-index**

### Evaluation Infrastructure
- Need test case execution environment
- Sandboxing for untrusted code
- Metrics computation (accuracy, RMSE, pass@k)

---

## Recommendation

**START WITH**:
1. **MLE-Bench** (75 competitions) - Immediate value for ML engineers
2. **SWE-Bench** (2,294 issues) - Real-world software engineering

**Total additions**: ~2,400 high-quality questions with solutions

**Expected outcomes**:
- DS/ML coverage: 7.7% → 25%
- Questions with solutions: 0% → 15%
- Semantic P@10: 74% → 76-78%
- **New capability**: Solution evaluation with metrics

**Timeline**: 3-4 weeks for Phase 1

Would you like me to start implementing the MLE-Bench + SWE-Bench integration?
