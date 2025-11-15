# AI/ML/Data Science Benchmarks for Error Analysis
## Available Datasets with Model Outputs

**Date**: November 15, 2025
**Goal**: Find benchmarks with actual model-generated code/reasoning to analyze WHY models fail on technical questions

---

## Current Dataset: MMLU-Pro

### What We Have

| Subject | Category | Questions | Avg Success | Type |
|---------|----------|-----------|-------------|------|
| machine_learning | CS | 90 | 56.8% | Multiple choice |
| college_computer_science | CS | 76 | 58.6% | Multiple choice |
| EECS | CS | 76 | 47.6% | Multiple choice |
| high_school_computer_science | CS | 62 | 71.6% | Multiple choice |
| ComputerScience | CS | 60 | 62.8% | Multiple choice |
| computer_security | CS | 46 | 55.0% | Multiple choice |

**Total AI/ML/CS questions**: ~410

### Limitation

❌ **Multiple-choice only** - We only have correct/incorrect, not actual code or reasoning traces
❌ **No failure modes** - Can't analyze WHAT errors models made
❌ **No generative output** - Can't study syntax errors, logic bugs, incorrect algorithms

---

## Available Benchmarks with Model Outputs

### 1. **HumanEval** (Code Generation) ⭐ RECOMMENDED

**What**: 164 Python programming problems
**Format**: Function signature + docstring → complete implementation
**Model Outputs Available**: Yes ✅

**GitHub Repositories**:
- **openai/human-eval** - Official evaluation harness
- **jamesmurdza/humaneval-results** - Community results collection with model outputs
- **CodeEval-Pro/CodeEval-Pro** - HumanEval Pro (ACL 2025)

**Example Problem**:
```python
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """Check if in given list of numbers, are any two numbers closer
    to each other than given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
```

**Model Output Example**:
```python
# GPT-4 Output:
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    for i in range(len(numbers)):
        for j in range(i+1, len(numbers)):
            if abs(numbers[i] - numbers[j]) < threshold:
                return True
    return False
# Result: PASS ✅

# Codex Output (buggy):
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    return any(abs(a-b) <= threshold for a in numbers for b in numbers)
# Result: FAIL ❌ (compares element with itself)
```

**Error Analysis Potential**:
- ✅ Syntax errors
- ✅ Logic bugs
- ✅ Off-by-one errors
- ✅ Edge case failures
- ✅ Algorithm correctness

**Size**: 164 problems
**Pass@1 Scores**: GPT-4 ~67%, Claude Sonnet 3.5 ~36.8% (HumanEval-V)

---

### 2. **DS-1000** (Data Science Code) ⭐⭐ HIGHLY RELEVANT

**What**: 1,000 data science problems across 7 libraries
**Libraries**: NumPy, Pandas, PyTorch, TensorFlow, Scikit-learn, SciPy, Matplotlib
**Model Outputs Available**: Yes ✅ (in `results/` folder)

**GitHub**: xlang-ai/DS-1000
**HuggingFace**: xlangai/DS-1000

**Example Problem**:
```python
# Problem: "How to get the sum of all values in a pandas DataFrame?"
# Expected: df.sum().sum()
# Common Errors:
#   - df.sum() only (forgets second .sum())
#   - df.values.sum() (works but inefficient)
#   - np.sum(df) (wrong library)
```

**Model Outputs**: Codex-002 results available as `data/codex002-answers.jsonl`

**Error Analysis Potential**:
- ✅ Library API misuse
- ✅ Pandas gotchas (multi-index, broadcasting)
- ✅ NumPy shape errors
- ✅ ML framework errors (PyTorch vs TensorFlow)
- ✅ Visualization mistakes

**Size**: 1,000 problems
**Pass@1 Scores**: Codex ~26%, GPT-4 ~40-50%

---

### 3. **BigCodeBench** (Complex Function Calls) - ICLR 2025

**What**: 1,140 tasks requiring multiple function calls from 139 libraries
**Domains**: 7 (data processing, ML, visualization, etc.)
**Model Outputs Available**: Via leaderboard ✅

**GitHub**: bigcode-project/bigcodebench
**Leaderboard**: https://bigcode-bench.github.io/

**Example Task**:
```python
# Task: "Read CSV, filter rows where column A > 5, group by column B,
#        calculate mean of column C, and plot as bar chart"
# Requires: pandas.read_csv + filter + groupby + mean + matplotlib
```

**Error Analysis Potential**:
- ✅ Multi-step reasoning failures
- ✅ API chaining errors
- ✅ Complex data transformations
- ✅ Integration across libraries

**Size**: 1,140 tasks (+ 148 BigCodeBench-Hard)
**Pass@1 Scores**: Up to 60% for best models (vs 97% human)

---

### 4. **ML-Bench** (Repository-Level ML Tasks)

**What**: Real ML research tasks in full repositories
**Format**: Given a repo, implement new ML features/experiments
**Model Outputs**: Via evaluation framework

**Key Feature**: Tests models on **realistic ML research** (not toy problems)

**Error Analysis Potential**:
- ✅ Understanding existing codebases
- ✅ Implementing new ML algorithms
- ✅ Debugging ML training pipelines
- ✅ Experiment design

**Size**: Repository-level (fewer problems, much more complex)

---

### 5. **MBPP** (Mostly Basic Python Programming)

**What**: 974 entry-level Python problems
**Format**: Similar to HumanEval but simpler
**Model Outputs Available**: Via evaluation harness

**Example**: "Write a function to find the sum of all even numbers in a list"

**Error Analysis Potential**:
- ✅ Basic Python mistakes
- ✅ Loop/iteration errors
- ✅ List comprehension bugs

**Size**: 974 problems
**Pass@1 Scores**: GPT-4 ~75%, Claude ~70%

---

## Recommended Implementation Priority

### **Option 1: HumanEval** (IMMEDIATE - Fast to implement)

**Why**:
- ✅ Small (164 problems)
- ✅ Model outputs available on GitHub (jamesmurdza/humaneval-results)
- ✅ Standard benchmark everyone uses
- ✅ Can scrape in ~5 minutes

**Error Types to Analyze**:
1. **Syntax errors** - Malformed code
2. **Logic bugs** - Wrong algorithm
3. **Edge cases** - Off-by-one, empty lists, None handling
4. **Inefficiency** - O(n²) instead of O(n)

**Implementation**:
```python
# Scrape from jamesmurdza/humaneval-results
# Each model has folder with:
#   - problem_N.md (problem + model output + test results)
# Extract:
#   - Problem description
#   - Model-generated code
#   - Pass/fail status
#   - Specific test cases failed
```

---

### **Option 2: DS-1000** (HIGH VALUE - Data science specific)

**Why**:
- ✅ Most relevant for ML/DS practitioners
- ✅ Real-world library usage
- ✅ Model outputs in repo (`results/codex002-answers.jsonl`)
- ✅ 1,000 problems = good statistical power

**Error Types to Analyze**:
1. **API misuse** - Wrong pandas/numpy methods
2. **Broadcasting errors** - Shape mismatches
3. **Type errors** - DataFrame vs Series confusion
4. **Performance** - Inefficient operations

**Implementation**:
```python
# Clone xlang-ai/DS-1000
# Load results/codex002-answers.jsonl
# Parse:
#   - Problem (with library context)
#   - Model-generated code
#   - Execution result (pass/fail)
#   - Error messages if failed
```

---

### **Option 3: BigCodeBench** (COMPREHENSIVE - Best for research)

**Why**:
- ✅ Most comprehensive (1,140 tasks)
- ✅ Complex multi-step problems
- ✅ ICLR 2025 acceptance = cutting-edge
- ✅ Leaderboard with many models

**Error Types to Analyze**:
1. **Function call errors** - Wrong library, wrong API
2. **Chaining failures** - Breaking multi-step pipelines
3. **Integration issues** - Combining multiple libraries
4. **Complex reasoning** - Multi-hop logic

---

## Error Analysis Approach

### Phase 1: Extract Model Outputs (Scraping)

```python
class CodeBenchmarkScraper:
    def scrape_humaneval_results():
        # From jamesmurdza/humaneval-results
        # Returns: [(problem_id, problem_text, model_code, passed, failed_tests)]

    def scrape_ds1000_results():
        # From xlang-ai/DS-1000/results/
        # Returns: [(problem_id, library, problem_text, model_code, error_msg)]
```

### Phase 2: Error Classification (Traditional NLP)

```python
def classify_errors(model_code, error_msg, test_results):
    categories = {
        'syntax_error': has_syntax_error(model_code),
        'runtime_error': 'Error' in error_msg,
        'logic_bug': passed_some_failed_some(test_results),
        'edge_case': failed_only_edge_cases(test_results),
        'api_misuse': wrong_library_used(model_code),
        'type_error': 'TypeError' in error_msg,
        'shape_error': 'shape' in error_msg.lower()
    }
    return categories
```

### Phase 3: Pattern Analysis (Fast Analysis from Earlier)

```python
# Extract features
features = {
    'problem_length': len(problem_text),
    'problem_complexity': count_steps(problem_text),
    'libraries_required': count_imports(reference_code),
    'has_edge_cases': has_special_cases(test_cases),
    'function_calls_needed': count_api_calls(reference_code)
}

# Cluster similar failures
kmeans.fit(features)  # Find natural groups

# Correlate with error types
correlation = features.corr(error_types)
```

### Phase 4: LLM Deep Dive (Selective)

```python
# For top 10 failure patterns:
llm_prompt = f"""
Analyze why models fail on this problem:

Problem: {problem_text}
Failed on: {failed_test_case}
Model output: {model_code}
Error: {error_msg}

What conceptual misunderstanding caused this failure?
"""
```

---

## Implementation Plan

### Quick Start (30 minutes)

```bash
# 1. Clone HumanEval results
git clone https://github.com/jamesmurdza/humaneval-results

# 2. Parse model outputs
python parse_humaneval.py

# 3. Run fast analysis
python fast_offline_analysis.py --dataset humaneval

# 4. Generate report
python error_analysis.py --input humaneval_outputs.json
```

### Expected Output

```
HumanEval Error Analysis Results:
=================================

Total problems: 164
Total model attempts: 3 models × 164 = 492

Error Types:
- Syntax errors: 12 (2.4%)
- Logic bugs: 89 (18.1%)
- Edge case failures: 156 (31.7%)
- Timeout/inefficient: 23 (4.7%)

Top Failure Patterns:
1. Off-by-one errors (42 occurrences)
2. None/empty list handling (38 occurrences)
3. Incorrect loop bounds (31 occurrences)
4. Wrong base case in recursion (18 occurrences)
5. Type confusion (list vs set) (15 occurrences)

Highest Risk Problem Types:
- Recursive algorithms: 45% failure rate
- String manipulation: 38% failure rate
- List operations: 32% failure rate
```

---

## Next Steps

**What would you like me to do?**

1. **Scrape HumanEval** → Fast, 164 problems, good for code error analysis
2. **Scrape DS-1000** → High value, 1,000 problems, best for ML/DS errors
3. **Implement both** → Comprehensive analysis across problem types
4. **Just analyze what we have** → Focus on MMLU-Pro machine_learning (90 questions)

Let me know and I'll build the scraper + error analysis pipeline!

---

**Generated**: November 15, 2025
**By**: ToGMAL Benchmark Research System
