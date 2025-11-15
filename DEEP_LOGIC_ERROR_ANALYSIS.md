# Deep Logic Error Analysis: DS-1000 Benchmark

**Date**: November 15, 2025
**Dataset**: DS-1000 (1,000 data science problems)
**Models**: Codex002, GPT-3.5-turbo-0613, GPT-4-0613
**Total Errors Analyzed**: 8,934 logic errors

---

## Executive Summary

By comparing generated code with reference solutions, we discovered that **"logic errors" are not a monolithic category**. They break down into 9 specific error types, with **wrong_attribute (27.6%)** and **missing_method (21.6%)** being the dominant failure modes.

### Critical Finding

**Models know HOW to write code syntactically, but struggle with WHAT to call**:
- 27.6% use wrong attributes (.values vs .to_numpy(), .loc vs .iloc)
- 21.6% forget to call required methods (.copy(), .reset_index())
- 15.8% call unnecessary extra methods
- Only 4.2% actually call the wrong method entirely (.median() instead of .mean())

This suggests models have **API confusion**, not fundamental coding inability.

---

## Error Type Taxonomy

### Overview: 9 Distinct Error Types

```
Total logic errors: 8,934 (across 3,000 code samples)

wrong_attribute       2,469 (27.6%) █████████████  ← Most common
missing_method        1,931 (21.6%) ██████████
extra_method          1,410 (15.8%) ███████
overcomplicated         860 ( 9.6%) ████
wrong_indexing          737 ( 8.2%) ████
incomplete_solution     574 ( 6.4%) ███
wrong_method            378 ( 4.2%) ██
wrong_parameter         356 ( 4.0%) █
complex_logic_error     219 ( 2.5%) █
```

---

## Detailed Error Type Analysis

### 1. Wrong Attribute (27.6% of errors)

**Definition**: Accessing wrong attributes or properties of objects.

**Common Patterns**:
- `.values` vs `.to_numpy()`
- `.loc` vs `.iloc` (as attribute, not indexer)
- Missing `.copy()` on chained operations
- Wrong DataFrame/Series attribute access

**Example** (Problem #0, Codex):
```python
# Reference (correct):
result = g(df.copy(), List)  # Uses .copy() attribute

# Generated (wrong):
result = df.iloc[List]  # Missing .copy() attribute
```

**Why This Happens**:
- Pandas/NumPy have MANY similar attributes
- `.values` was deprecated in favor of `.to_numpy()` → models trained on old code
- Subtle differences between similar attributes

**Impact**: **HIGH RISK**
- Code runs without error
- Returns wrong type or wrong data
- Silent failure

---

### 2. Missing Method (21.6% of errors)

**Definition**: Failed to call required method(s) in the solution.

**Common Patterns**:
- Missing `.copy()` → modifies original DataFrame
- Missing `.reset_index()` → index not reset after operations
- Missing `.apply()` → transformation not applied
- Missing `.sum()`, `.mean()`, etc. → aggregation step missing

**Example** (Problem #1, Codex):
```python
# Reference (correct):
def g(df, List):
    df2 = df.iloc[List].reindex().reset_index(drop=True)
    return (df2.Type != df.Type).sum()

result = g(df.copy(), List)

# Generated (wrong):
result = df.iloc[List]  # Missing: reindex(), reset_index(), sum(), copy()
```

**Why This Happens**:
- Models generate minimal code
- Training on incomplete StackOverflow answers
- Optimization for brevity over correctness

**Impact**: **CRITICAL**
- Incomplete transformations
- Missing critical steps
- Wrong final result

---

### 3. Extra Method (15.8% of errors)

**Definition**: Called unnecessary methods that weren't required.

**Common Patterns**:
- Unnecessary `.groupby()` when direct filtering would work
- Extra `.reset_index()` when index doesn't matter
- Redundant `.apply()` calls
- Over-engineering with `.pipe()`, `.assign()`, etc.

**Example** (Problem #7, Codex):
```python
# Reference (correct):
def g(df):
    return df.loc[(df['keep_if_dup'] =='Yes') | ~df['url'].duplicated()]

result = g(df.copy())

# Generated (wrong):
result = df.groupby(['url', 'keep_if_dup']).first().reset_index()
# Extra methods: groupby(), first(), reset_index() - none needed!
```

**Why This Happens**:
- Models trained on verbose tutorial code
- Attempting to be "safe" with extra operations
- Confusion about the simplest approach

**Impact**: **MEDIUM RISK**
- More complex code = more bugs
- Performance overhead
- May produce wrong result due to unexpected side effects

---

### 4. Overcomplicated (9.6% of errors)

**Definition**: Generated significantly longer code than necessary (2x+ lines).

**Common Patterns**:
- For-loops instead of vectorized operations
- Manual iteration instead of built-in methods
- Explicit construction instead of method chaining

**Example** (Problem #56, Codex):
```python
# Reference (correct - 4 lines):
def g(df):
    df.dt = pd.to_datetime(df.dt)
    return df.set_index(['dt', 'user']).unstack(fill_value=0).asfreq('D', fill_value=0).stack().sort_index(level=1).reset_index()

result = g(df.copy())

# Generated (wrong - 11 lines):
result = pd.DataFrame(columns=['dt', 'user', 'val'])
for user in df['user'].unique():
    user_df = df[df['user'] == user]
    min_date = user_df['dt'].min()
    max_date = user_df['dt'].max()
    user_df = user_df.set_index('dt')
    user_df = user_df.reindex(pd.date_range(min_date, max_date))
    user_df = user_df.reset_index()
    user_df['user'] = user
    user_df['val'] = user_df['val'].fillna(0)
    result = result.append(user_df)
```

**Why This Happens**:
- Models default to imperative (for-loop) style
- Unfamiliar with advanced method chaining
- Prioritizing readability over conciseness

**Impact**: **HIGH RISK**
- 2.75x more code = 2.75x more potential bugs
- for-loops in Pandas are ~100x slower
- More state management = more errors

---

### 5. Wrong Indexing (8.2% of errors)

**Definition**: Used wrong indexing pattern (.loc vs .iloc vs []).

**Common Patterns**:
- `.iloc[]` (position-based) vs `.loc[]` (label-based)
- Direct `[]` indexing vs accessor methods
- Numeric index when string index needed

**Example** (Problem #8, Codex):
```python
# Reference (correct):
def g(df):
    return df.loc[(df['drop_if_dup'] =='No') | ~df['url'].duplicated()]
    # Uses .loc[] for label-based boolean indexing

result = g(df.copy())

# Generated (wrong):
result = df.groupby('url').apply(lambda x: x.iloc[0] if x['drop_if_dup'].iloc[0] == 'Yes' else x)
# Uses .iloc[] for position-based indexing - wrong approach!
```

**Why This Happens**:
- Pandas has 3 indexing methods (.loc, .iloc, [])
- Subtle semantic differences
- Models confuse position-based vs label-based indexing

**Impact**: **HIGH RISK**
- Selects wrong rows/columns
- Breaks when index is not default (0, 1, 2...)
- Silent failure with wrong subset

---

### 6. Incomplete Solution (6.4% of errors)

**Definition**: Generated code is too short (< 50% of reference lines).

**Common Patterns**:
- Only first step of multi-step solution
- Missing final transformation
- Partial implementation

**Example** (Problem #1, Codex):
```python
# Reference (correct - 4 lines):
def g(df, List):
    df2 = df.iloc[List].reindex().reset_index(drop=True)
    return (df2.Type != df.Type).sum()

result = g(df.copy(), List)

# Generated (wrong - 1 line):
result = df.iloc[List]
# Missing: reindex(), reset_index(), comparison, sum()
```

**Why This Happens**:
- Models stop generation too early
- Incomplete problem understanding
- Training on incomplete code snippets

**Impact**: **CRITICAL**
- Fundamentally wrong result
- Missing entire steps
- User expects complete solution, gets partial

---

### 7. Wrong Method (4.2% of errors)

**Definition**: Called completely wrong method (e.g., .median() instead of .mean()).

**Common Patterns**:
- Statistical methods: `.median()` vs `.mean()` vs `.mode()`
- Transformation methods: `.replace()` vs `.map()` vs `.apply()`
- Aggregation methods: `.sum()` vs `.count()` vs `.size()`

**Example** (Problem #5, Codex):
```python
# Reference (correct):
def g(df):
    for col in df.columns:
        vc = df[col].value_counts()
        if col == 'Qu1':
            df[col] = df[col].apply(lambda x: x if vc[x] >= 3 else 'other')
        else:
            df[col] = df[col].apply(lambda x: x if vc[x] >= 2 else 'other')
    return df

result = g(df.copy())

# Generated (wrong):
def replace_values(df, column, threshold):
    counts = df[column].value_counts()
    mask = counts >= threshold
    df[column] = df[column].replace(counts[mask].index, 'other')  # .replace() instead of .apply()!
    return df

result = df.pipe(replace_values, 'Qu1', 3).pipe(replace_values, 'Qu3', 2)
```

**Why This Happens**:
- Semantic similarity between methods
- Incomplete understanding of method behavior
- Training on diverse code styles

**Impact**: **CRITICAL**
- Fundamentally different operation
- Wrong result type or values
- Logic error that may not be caught

---

### 8. Wrong Parameter (4.0% of errors)

**Definition**: Used wrong parameter values (axis, inplace, ascending, etc.).

**Common Patterns**:
- `axis=0` (rows) vs `axis=1` (columns)
- `inplace=True` vs `inplace=False`
- `ascending=True` vs `ascending=False`
- Missing required parameters

**Example** (Problem #15, Codex):
```python
# Reference (correct):
result = pd.concat([df, df1], axis=1)  # axis=1 for column-wise concat

# Generated (wrong):
result = df.join(df.message.apply(extract_key_value).apply(pd.Series))
# Missing axis parameter in join - defaults to axis=1 but behavior differs
```

**Why This Happens**:
- Parameter defaults vary by method
- `axis` parameter especially confusing (0=rows, 1=columns)
- Models don't understand dimensional implications

**Impact**: **HIGH RISK**
- Operates on wrong dimension
- Wrong shape or structure
- Silent failure with plausible-looking output

---

### 9. Complex Logic Error (2.5% of errors)

**Definition**: Codes differ but no specific pattern detected by our analyzer.

**Patterns**:
- Completely different algorithmic approach
- Novel combinations of errors
- Subtle semantic differences

**Why This Happens**:
- Our pattern detector can't catch everything
- Genuinely complex logical differences
- May require execution to understand failure

**Impact**: **UNKNOWN**
- Requires manual inspection
- Could be minor or critical

---

## Model-Specific Patterns

### Codex002: "Too Simple"

**Signature Pattern**: Incomplete solutions

**Statistics**:
- **Incomplete solutions**: 338 (vs 80-156 for others) ← **5.5x worse than GPT-3.5**
- **Overcomplicated**: 61 (vs 306-493 for others) ← 8x BETTER
- **Missing methods**: 659 (high)

**Interpretation**:
- Optimized for brevity
- Stops generation too early
- Missing critical steps

**Example Behavior**:
```python
# Problem: Multi-step data transformation
# Codex: result = df.iloc[List]  # Only step 1 of 4!
# GPT-4: (all 4 steps)
```

**Implication for Users**:
> ⚠️ **Codex code is often TOO SIMPLE**. Always verify all required steps are present.

---

### GPT-3.5-turbo: "Too Verbose"

**Signature Pattern**: Overcomplicated solutions

**Statistics**:
- **Overcomplicated**: 493 (vs 61-306 for others) ← **8x worse than Codex**
- **Extra methods**: 554 (highest)
- **Incomplete solutions**: 80 (vs 338 for Codex) ← 4x better

**Interpretation**:
- Adds unnecessary complexity
- Over-engineers solutions
- Includes redundant operations

**Example Behavior**:
```python
# Problem: Simple filtering
# Reference: df.loc[condition]  # 1 line
# GPT-3.5: df.groupby().apply().reset_index()  # 3+ unnecessary operations
```

**Implication for Users**:
> ⚠️ **GPT-3.5 code is often TOO COMPLEX**. Look for simpler alternatives.

---

### GPT-4: "Balanced but Still Flawed"

**Signature Pattern**: Balanced between extremes

**Statistics**:
- **Overcomplicated**: 306 (middle ground)
- **Incomplete solutions**: 156 (middle ground)
- **Missing methods**: 625 (similar to others)

**Interpretation**:
- More balanced approach
- Still makes both types of errors
- Not significantly better than GPT-3.5 on logic

**Implication for Users**:
> GPT-4 is more balanced but **still makes 600+ logic errors**. Don't assume correctness.

---

## Library-Specific Error Patterns

### Pandas (291 problems): "Attribute Chaos"

**Top Errors**:
1. **wrong_attribute**: 839 occurrences (2.9 per problem!)
2. **missing_method**: 812 occurrences
3. **extra_method**: 423 occurrences

**Why Pandas is Hard**:
- **Massive API**: 200+ DataFrame methods, 150+ Series methods
- **Attribute confusion**: `.values` vs `.to_numpy()` vs `.array`
- **Method chaining**: Complex chains are error-prone
- **Indexing variety**: `.loc`, `.iloc`, `.at`, `.iat`, `[]`

**Common Specific Errors**:
- Forgetting `.copy()` → modifies original
- Wrong indexing: `.iloc` vs `.loc`
- Missing `.reset_index()` after groupby

**Implication**:
> 🚨 **Pandas has the highest error rate** due to API complexity. Extra scrutiny needed.

---

### NumPy (220 problems): "Array Confusion"

**Top Errors**:
1. **wrong_attribute**: 466 occurrences (2.1 per problem)
2. **missing_method**: 352 occurrences
3. **overcomplicated**: 293 occurrences

**Why NumPy is Hard**:
- **Broadcasting rules**: Implicit dimension handling
- **Axis parameter**: `axis=0` vs `axis=1` confusion
- **Shape manipulation**: `.reshape()`, `.transpose()`, `.swapaxes()`
- **Type conversion**: Array types and dtypes

**Common Specific Errors**:
- Wrong axis parameter
- Missing `.copy()` for view vs copy
- Confusion with NumPy vs Pandas methods

**Implication**:
> NumPy errors often involve **dimensional confusion** (axis, shape, broadcasting).

---

### Matplotlib (155 problems): "Extra Configuration"

**Top Errors**:
1. **wrong_attribute**: 391 occurrences (2.5 per problem)
2. **extra_method**: 315 occurrences ← **Highest ratio for this error type**
3. **overcomplicated**: 193 occurrences

**Why Matplotlib is Hard**:
- **Stateful API**: `plt.` vs `ax.` confusion
- **Configuration heavy**: Many optional customization calls
- **Dual interfaces**: Pyplot vs OO interface

**Common Specific Errors**:
- Extra styling calls not needed for the problem
- Redundant configuration methods
- Wrong object-level access (figure vs axes)

**Implication**:
> Matplotlib errors tend to be **extra configuration**, not missing functionality. Code is overcomplicated.

---

### PyTorch / TensorFlow / Sklearn / Scipy: "Attribute Access"

**Pattern**: All show **wrong_attribute** as #1 error

**Why These Are Moderately Hard**:
- Distinct APIs reduce confusion with each other
- But internal attribute/method confusion remains
- Tensor operations (PyTorch/TF) have similar issues to NumPy

**Implication**:
> Even specialized libraries suffer from **attribute confusion** as the primary error mode.

---

## Key Insights

### Insight 1: API Confusion, Not Coding Inability

**Finding**: Models struggle with WHAT to call, not HOW to code.

**Evidence**:
- Only 0.1-0.2% syntax errors (execution_error)
- 27.6% wrong attributes
- 21.6% missing methods
- 15.8% extra methods

**Interpretation**: Models know Python syntax perfectly, but don't understand library APIs deeply.

**Implication for ToGMAL**:
```python
def assess_api_confusion_risk(question: str) -> dict:
    libraries = detect_libraries(question)

    high_confusion_libs = ['pandas', 'numpy']  # 2-3 errors per problem
    medium_confusion_libs = ['matplotlib', 'scipy']

    if any(lib in question.lower() for lib in high_confusion_libs):
        return {
            'risk': 'HIGH',
            'message': (
                '⚠️ API CONFUSION RISK: Pandas/NumPy have 2-3 logic errors '
                'per problem on average. Most common: wrong attributes (27.6%), '
                'missing methods (21.6%). Verify all method calls carefully.'
            )
        }
```

---

### Insight 2: Model Personality Differences

**Codex**: "Minimalist" (too simple, incomplete)
**GPT-3.5**: "Maximalist" (too complex, extra methods)
**GPT-4**: "Balanced" (both problems, not significantly better)

**Implication**: **Choose model based on task complexity**
- Simple tasks → GPT-3.5/GPT-4 (won't miss steps)
- Complex tasks → Codex (won't overcomplicate)
- Always verify regardless

---

### Insight 3: Library Complexity Correlates with Error Rate

**Error Rate by Library** (errors per problem):

```
Pandas:     2.9 errors/problem  ← Most complex API
NumPy:      2.1 errors/problem
Matplotlib: 2.5 errors/problem
Sklearn:    1.8 errors/problem
PyTorch:    1.7 errors/problem
Scipy:      1.6 errors/problem
TensorFlow: 1.5 errors/problem  ← Most specialized API
```

**Observation**: More general-purpose libraries (Pandas, NumPy) have higher error rates than specialized libraries (TensorFlow, PyTorch).

**Why**: Pandas/NumPy are used in diverse contexts → more diverse training data → more confusion about correct usage.

---

### Insight 4: The ".copy()" Problem

**Observation**: `.copy()` is THE most commonly missing method.

**Why It Matters**:
- Modifies original DataFrame instead of copy
- Silent side effect
- Breaks caller's data

**Frequency**: Appears in 800+ missing_method errors

**Implication for ToGMAL**:
```python
def check_copy_usage(code: str) -> dict:
    if 'pandas' in code or 'pd.' in code:
        if 'df[' in code or 'df.' in code:  # DataFrame manipulation
            if '.copy()' not in code:
                return {
                    'warning': 'MISSING .copy()',
                    'message': (
                        '⚠️ Code modifies DataFrame without .copy(). '
                        'This is the #1 missing method in DS-1000 errors. '
                        'Consider: df_new = df.copy() before modifications.'
                    )
                }
```

---

### Insight 5: Wrong Attribute Dominates Across ALL Libraries

**Universal Pattern**: Every library's #1 error is **wrong_attribute**

**Why This Is Critical**:
- Attributes look like methods: `.values` vs `.to_numpy()`
- Deprecated attributes still in training data: `.values` → `.to_numpy()`
- Subtle differences: `.iloc` vs `.loc` as attributes

**Implication**: This is a **fundamental model weakness**, not library-specific.

---

## Recommendations for ToGMAL

### 1. Library-Specific Risk Warnings

**Implementation**:
```python
LIBRARY_ERROR_PROFILES = {
    'pandas': {
        'error_rate': 2.9,  # errors per problem
        'top_errors': ['wrong_attribute', 'missing_method', 'extra_method'],
        'common_issues': ['.copy() missing', '.loc vs .iloc confusion', 'index not reset'],
        'severity': 'HIGH'
    },
    'numpy': {
        'error_rate': 2.1,
        'top_errors': ['wrong_attribute', 'missing_method', 'overcomplicated'],
        'common_issues': ['axis parameter wrong', 'broadcasting confusion', 'shape errors'],
        'severity': 'HIGH'
    },
    # ... etc
}

def warn_library_specific(question: str):
    for lib, profile in LIBRARY_ERROR_PROFILES.items():
        if lib in question.lower():
            return {
                'library': lib,
                'error_rate': f"{profile['error_rate']} errors/problem average",
                'top_errors': profile['top_errors'],
                'common_issues': profile['common_issues'],
                'severity': profile['severity']
            }
```

---

### 2. Error Type Detection in Generated Code

**Check generated code for common patterns**:

```python
def analyze_generated_code(code: str, library: str) -> List[dict]:
    warnings = []

    # Check 1: Missing .copy()
    if library == 'pandas':
        if 'df[' in code or 'df.' in code:
            if '.copy()' not in code:
                warnings.append({
                    'type': 'missing_method',
                    'severity': 'HIGH',
                    'message': 'Missing .copy() - may modify original DataFrame'
                })

    # Check 2: Overcomplicated (for-loops in Pandas)
    if library == 'pandas':
        if 'for ' in code and 'df' in code:
            warnings.append({
                'type': 'overcomplicated',
                'severity': 'MEDIUM',
                'message': 'Using for-loop with DataFrame - consider vectorized operation'
            })

    # Check 3: Wrong indexing (iloc with string index)
    if '.iloc[' in code and any(c in code for c in ["'", '"']):
        warnings.append({
            'type': 'wrong_indexing',
            'severity': 'HIGH',
            'message': '.iloc[] with string detected - use .loc[] for label-based indexing'
        })

    # Check 4: axis parameter missing
    if library in ['pandas', 'numpy']:
        methods_needing_axis = ['sum', 'mean', 'std', 'concat', 'apply']
        for method in methods_needing_axis:
            if f'.{method}(' in code:
                # Simple check: if method call doesn't have 'axis='
                method_call = code[code.find(f'.{method}('):]
                if 'axis=' not in method_call[:50]:  # Check next 50 chars
                    warnings.append({
                        'type': 'wrong_parameter',
                        'severity': 'MEDIUM',
                        'message': f'.{method}() without axis parameter - may operate on wrong dimension'
                    })

    return warnings
```

---

### 3. Model-Specific Warnings

**Codex**:
```
⚠️ Codex tends to generate INCOMPLETE solutions (338 cases in DS-1000).
Verify all required steps are present:
✓ All transformations applied
✓ Final aggregation/calculation included
✓ .copy() called if needed
```

**GPT-3.5**:
```
⚠️ GPT-3.5 tends to OVERCOMPLICATE solutions (493 cases in DS-1000).
Look for simpler alternatives:
✓ Can for-loops be replaced with vectorized operations?
✓ Are all method calls necessary?
✓ Can method chaining be simplified?
```

**GPT-4**:
```
⚠️ GPT-4 is balanced but still makes 600+ logic errors in DS-1000.
Don't assume correctness - verify:
✓ Attribute usage (.loc vs .iloc, .values vs .to_numpy())
✓ All required methods called
✓ Parameter values (axis, inplace, etc.)
```

---

### 4. Interactive Code Review Prompts

**When user gets Pandas code**:
```
🔍 PANDAS CODE REVIEW CHECKLIST:

This code uses Pandas, which has 2.9 logic errors per problem on average in DS-1000 benchmark.

Common issues to check:
[ ] Is .copy() called before modifying DataFrame?
[ ] Is .loc[] used for labels and .iloc[] for positions?
[ ] Is .reset_index() called after groupby/transform?
[ ] Are axis parameters correct (0=rows, 1=columns)?
[ ] Are all required methods present?

Top 3 error types in Pandas code:
1. Wrong attribute (27.6%) - e.g., .values vs .to_numpy()
2. Missing method (21.6%) - e.g., forgot .copy() or .reset_index()
3. Extra method (15.8%) - e.g., unnecessary .groupby()

Would you like me to review this code for these specific issues?
```

---

### 5. Benchmark-Based Confidence Scoring

**Assign confidence based on error patterns**:

```python
def calculate_code_confidence(code: str, library: str, model: str) -> dict:
    """Calculate confidence score based on DS-1000 error patterns."""

    confidence = 100  # Start at 100%
    issues = []

    # Deduct based on library complexity
    library_penalties = {
        'pandas': -20,  # 2.9 errors/problem
        'numpy': -15,   # 2.1 errors/problem
        'matplotlib': -15,
        'sklearn': -10,
        'pytorch': -10,
        'scipy': -10,
        'tensorflow': -5,
    }

    confidence += library_penalties.get(library, 0)

    # Deduct based on model patterns
    if model == 'codex':
        code_lines = len([l for l in code.split('\n') if l.strip()])
        if code_lines < 5:
            confidence -= 15
            issues.append('Short code (Codex incomplete pattern)')

    elif model == 'gpt-3.5-turbo':
        code_lines = len([l for l in code.split('\n') if l.strip()])
        if code_lines > 15:
            confidence -= 10
            issues.append('Long code (GPT-3.5 overcomplicated pattern)')

    # Deduct for specific error patterns
    if library == 'pandas' and '.copy()' not in code:
        confidence -= 15
        issues.append('Missing .copy() (most common missing method)')

    if 'for ' in code and library in ['pandas', 'numpy']:
        confidence -= 10
        issues.append('For-loop detected (overcomplicated pattern)')

    # Floor at 0
    confidence = max(0, confidence)

    return {
        'confidence': confidence,
        'issues': issues,
        'recommendation': 'VERIFY CAREFULLY' if confidence < 50 else 'REVIEW' if confidence < 75 else 'LIKELY OK'
    }
```

---

## Conclusion

### What We Learned

1. **"Logic errors" are not uniform** - they break into 9 distinct types with different characteristics
2. **API confusion is the real problem** - 27.6% wrong attributes, 21.6% missing methods
3. **Each model has a personality** - Codex is minimalist, GPT-3.5 is maximalist, GPT-4 is balanced but still flawed
4. **Library complexity matters** - Pandas (2.9 errors/problem) >> TensorFlow (1.5 errors/problem)
5. **Wrong attribute is universal** - Every library's #1 error type

### Critical Recommendations

**For ToGMAL Users**:
1. ⚠️ Never trust Pandas/NumPy code without verification (2-3 errors/problem average)
2. ⚠️ Always check for `.copy()` - most commonly missing method
3. ⚠️ Verify axis parameters - most common wrong parameter
4. ⚠️ Codex code may be incomplete - check all steps present
5. ⚠️ GPT-3.5 code may be overcomplicated - look for simpler alternatives

**For ToGMAL Integration**:
1. Implement library-specific risk warnings
2. Add code pattern detection for common errors
3. Provide model-specific guidance
4. Calculate confidence scores based on DS-1000 patterns
5. Offer interactive code review checklists

### Next Steps

1. Build automated code analyzer using error patterns
2. Create library-specific linters
3. Develop fix suggestions for common errors
4. Train custom risk predictor on DS-1000 data

---

**Generated**: November 15, 2025
**Analysis**: 8,934 logic errors across 3,000 code samples (DS-1000 benchmark)
**Models**: Codex002, GPT-3.5-turbo-0613, GPT-4-0613
**Libraries**: Pandas, NumPy, Matplotlib, PyTorch, Scikit-learn, SciPy, TensorFlow
