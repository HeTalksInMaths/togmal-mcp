# Comprehensive Data Expansion Plan

**Goal:** Expand from 82 → 1,000+ questions with performance data
**Expected Impact:** Correlation 0.13 → 0.60+, MAE 7.7% → 4-5%

---

## Current State

**What we have:**
- 82 MLE-bench competitions (real Kaggle tasks)
- 170 MMLU-Pro questions (academic Q&A)
- Total: 252 questions with performance data

**Limitations:**
- Small sample size → weak patterns
- Limited domain coverage
- Low confidence predictions (0.18)
- Weak correlation (+0.13)

---

## Expansion Strategy

### Tier 1: Most Similar to MLE-bench (PRIORITY)

#### 1.1 More Kaggle Competitions ⭐⭐⭐⭐⭐
**Target:** +200 competitions (82 → 282)

**Sources:**
- Kaggle API: 100,000+ public competitions
- Papers With Code: Published results
- Competition archives: Historical data

**How to get:**
```bash
# Install Kaggle API
pip install kaggle

# Get credentials from https://www.kaggle.com/account
# Download to ~/.kaggle/kaggle.json

# Fetch competitions
python expand_kaggle_competitions.py
```

**Data quality:**
- ✅ Real ML tasks (same as MLE-bench)
- ✅ Clear evaluation metrics
- ✅ Known difficulty (team counts, prizes)
- ❌ Need LLM evaluation results

**Estimated LLM performance:**
- Use heuristics: teams, prize, duration → difficulty
- Or: Run evaluations on subset (expensive)

**Impact:**
- Training data: 3x increase
- Correlation: +0.13 → +0.30 to +0.40
- Confidence: +0.18 → +0.35 to +0.45

---

#### 1.2 ML Competition Platforms ⭐⭐⭐⭐
**Target:** +100 competitions

**Sources:**
- **DrivenData**: Social good competitions
- **AIcrowd**: Academic research challenges
- **Zindi**: African data science competitions
- **CodaLab**: Academic benchmarks
- **TopCoder**: Algorithm competitions with ML

**How to get:**
- Scrape competition listings
- Extract problem statements
- Estimate difficulty from metadata

**Impact:**
- Training data: +40% more
- Better domain coverage (social impact, research)

---

### Tier 2: Similar Task Types (HIGH PRIORITY)

#### 2.1 Code Generation Benchmarks ⭐⭐⭐⭐
**Target:** +1,138 questions

**Benchmarks:**
1. **HumanEval** (164 problems) - Python code generation
2. **MBPP** (974 problems) - Basic Python programming
3. **BigCodeBench** - Complex coding tasks
4. **CodeContests** - Competitive programming

**How to get:**
```bash
from datasets import load_dataset

# HumanEval
humaneval = load_dataset("openai_humaneval")

# MBPP
mbpp = load_dataset("mbpp")
```

**LLM Performance:**
- Widely evaluated (GPT-4, Claude, etc.)
- Published results available
- Pass@k metrics standard

**Impact:**
- Strong domain: Code generation similar to ML engineering
- Well-studied: Lots of performance data
- Correlation improvement: +0.10 to +0.15

---

#### 2.2 Math & Reasoning Benchmarks ⭐⭐⭐
**Target:** +21,000 questions

**Benchmarks:**
1. **MATH** (12,500 problems) - Math word problems
2. **GSM8K** (8,500 problems) - Grade school math
3. **TheoremQA** - Scientific reasoning

**How to get:**
```bash
# MATH dataset
math = load_dataset("hendrycks/math")

# GSM8K
gsm8k = load_dataset("gsm8k")
```

**LLM Performance:**
- Extensively benchmarked
- Clear difficulty levels
- Pass/fail evaluation

**Impact:**
- Reasoning tasks relevant to ML
- Huge sample size
- Correlation: +0.05 to +0.10

---

### Tier 3: Academic Benchmarks (MODERATE PRIORITY)

#### 3.1 Domain-Specific Tasks ⭐⭐⭐
**Target:** +5,000 questions

**Domains:**
- **ScienceQA**: Scientific reasoning
- **MedQA**: Medical questions
- **LegalBench**: Legal reasoning
- **FinanceBench**: Financial analysis

**Impact:**
- Domain coverage
- Professional tasks (closer to real-world)

---

#### 3.2 Multilingual Benchmarks ⭐⭐
**Target:** +3,000 questions

**Benchmarks:**
- **MGSM**: Math in multiple languages
- **XLSum**: Multilingual summarization
- **XNLI**: Cross-lingual NLI

**Impact:**
- Language diversity
- Difficulty variation

---

## Implementation Phases

### Phase 1: Quick Wins (1-2 weeks) ⭐⭐⭐⭐⭐

**Add code generation benchmarks:**
```bash
# Already available, no scraping needed
python expand_code_benchmarks.py  # HumanEval + MBPP

# Expected result:
# - Training data: 252 → 1,390 (+450%)
# - Correlation: 0.13 → 0.35-0.45
# - MAE: 7.7% → 5.5-6.5%
```

**Effort:** 4-6 hours
**Impact:** Very high (4-5x more data)

---

### Phase 2: Kaggle Expansion (2-4 weeks) ⭐⭐⭐⭐

**Add 200+ Kaggle competitions:**
```bash
# Requires Kaggle API setup
pip install kaggle
python expand_kaggle_competitions.py

# Manual curation of high-quality competitions
python curate_competitions.py

# Expected result:
# - Training data: 1,390 → 1,590
# - Better MLE-bench coverage
# - Correlation: 0.35 → 0.45-0.55
```

**Effort:** 20-30 hours (API + curation)
**Impact:** High (more real ML tasks)

---

### Phase 3: Math Benchmarks (1 week) ⭐⭐⭐

**Add MATH + GSM8K:**
```bash
python expand_math_benchmarks.py

# Expected result:
# - Training data: 1,590 → 23,000+
# - Massive sample size
# - Correlation: 0.45 → 0.50-0.60
```

**Effort:** 8-12 hours
**Impact:** Moderate per-question but huge volume

---

## Expected Impact by Phase

| Phase | Questions | Correlation | MAE | Confidence |
|-------|-----------|-------------|-----|------------|
| **Current** | 252 | +0.13 | 7.7% | 0.18 |
| **Phase 1** | 1,390 | +0.35-0.45 | 5.5-6.5% | 0.40-0.50 |
| **Phase 2** | 1,590 | +0.45-0.55 | 5.0-6.0% | 0.50-0.60 |
| **Phase 3** | 23,000+ | +0.55-0.65 | 4.0-5.0% | 0.60-0.70 |

---

## Better Confidence Through Validation

### Problem: How do we know it's working?

Current approach:
- Single train/test split
- Test on 16 questions (too small!)
- No confidence intervals

### Solution 1: K-Fold Cross-Validation ⭐⭐⭐⭐⭐

```python
from sklearn.model_selection import KFold

# 5-fold cross-validation
kfold = KFold(n_splits=5, shuffle=True, random_state=42)

correlations = []
maes = []

for train_idx, test_idx in kfold.split(questions):
    train = [questions[i] for i in train_idx]
    test = [questions[i] for i in test_idx]

    predictor = train_predictor(train)
    metrics = evaluate(predictor, test)

    correlations.append(metrics['correlation'])
    maes.append(metrics['mae'])

# Report with confidence intervals
print(f"Correlation: {np.mean(correlations):.3f} ± {np.std(correlations):.3f}")
print(f"MAE: {np.mean(maes):.2f}% ± {np.std(maes):.2f}%")

# Example output:
# Correlation: 0.425 ± 0.082 (95% CI: [0.343, 0.507])
# MAE: 5.8% ± 1.2% (95% CI: [4.6%, 7.0%])
```

**Impact:**
- ✅ Confidence intervals on all metrics
- ✅ Know if improvements are real or noise
- ✅ Detect overfitting
- ✅ More reliable evaluation (5x more test samples)

---

### Solution 2: Stratified Evaluation ⭐⭐⭐⭐

Break down by domain/difficulty:

```python
# Evaluate by domain
for domain in ['CV', 'NLP', 'Tabular', 'Code']:
    domain_questions = [q for q in test if q['domain'] == domain]
    metrics = evaluate(predictor, domain_questions)
    print(f"{domain}: Correlation = {metrics['correlation']:.3f}")

# Example output:
# CV: Correlation = 0.512 ± 0.091 (strong!)
# NLP: Correlation = 0.387 ± 0.124 (moderate)
# Tabular: Correlation = 0.441 ± 0.106 (moderate)
# Code: Correlation = 0.623 ± 0.078 (very strong!)
```

**Benefits:**
- Know which domains work well
- Identify weak areas
- Domain-specific improvements

---

### Solution 3: Bootstrap Confidence Intervals ⭐⭐⭐

```python
# Bootstrap 1000 times
n_bootstrap = 1000
bootstrap_correlations = []

for _ in range(n_bootstrap):
    # Resample test set with replacement
    sample_indices = np.random.choice(len(test), len(test), replace=True)
    sample = [test[i] for i in sample_indices]

    metrics = evaluate(predictor, sample)
    bootstrap_correlations.append(metrics['correlation'])

# 95% confidence interval
ci_lower = np.percentile(bootstrap_correlations, 2.5)
ci_upper = np.percentile(bootstrap_correlations, 97.5)

print(f"Correlation: {np.mean(bootstrap_correlations):.3f}")
print(f"95% CI: [{ci_lower:.3f}, {ci_upper:.3f}]")

# Example:
# Correlation: 0.425
# 95% CI: [0.338, 0.512]
```

---

### Solution 4: Hold-Out Test Set (Never Touch!) ⭐⭐⭐⭐⭐

```python
# Split data ONCE at the beginning
train_val, holdout = train_test_split(questions, test_size=0.15, random_state=42)

# Use train_val for development (k-fold CV, hyperparameter tuning, etc.)
# NEVER look at holdout until the very end

# Final evaluation (once!)
final_metrics = evaluate(final_predictor, holdout)
print(f"Final Test Correlation: {final_metrics['correlation']:.3f}")
```

**Why this matters:**
- Prevents overfitting to test set
- True generalization performance
- Standard ML practice

---

## Meta-Features for Better Predictions

### Current: Only text similarity

**Problem:** TF-IDF only uses question text
- Misses structural information
- No domain knowledge
- Ignores task metadata

### Solution: Extract Rich Features ⭐⭐⭐⭐

```python
def extract_meta_features(question):
    """Extract difficulty-relevant features"""

    features = {}

    # Text features (current)
    features['text_embedding'] = tfidf_vectorizer.transform([question['text']])

    # NEW: Structural features
    features['text_length'] = len(question['text'])
    features['has_code'] = '```' in question['text']
    features['has_math'] = any(c in question['text'] for c in ['$', '\\frac', '\\int'])
    features['has_image'] = 'image' in question['text'].lower()

    # NEW: Domain features
    features['domain'] = question['domain']  # One-hot encode
    features['subdomain'] = question['subdomain']

    # NEW: Complexity indicators
    features['dataset_size'] = extract_dataset_size(question['text'])  # "10GB" → 10
    features['num_classes'] = extract_num_classes(question['text'])  # "10 classes" → 10
    features['metric_type'] = extract_metric(question['text'])  # "log-loss", "RMSE", etc.

    # NEW: Competition metadata (if available)
    features['num_teams'] = question.get('teams', 0)
    features['prize_amount'] = question.get('prize', 0)
    features['competition_duration'] = question.get('duration_days', 0)

    return features
```

**Combine with Gradient Boosting:**

```python
from sklearn.ensemble import GradientBoostingRegressor

# Train meta-predictor
X_train = [extract_meta_features(q) for q in train]
y_train = [failure_rates[q['id']] for q in train]

meta_model = GradientBoostingRegressor(n_estimators=100)
meta_model.fit(X_train, y_train)

# Predict
X_test = [extract_meta_features(q) for q in test]
predictions = meta_model.predict(X_test)
```

**Expected Impact:**
- Correlation: +0.10 to +0.20 improvement
- Captures non-textual signals
- Better confidence (uses multiple signal types)

---

## Ensemble Methods

### Combine Multiple Predictors ⭐⭐⭐⭐

```python
class EnsemblePredictor:
    """Combine TF-IDF + meta-features + domain-specific models"""

    def __init__(self):
        self.tfidf_predictor = TfidfFailureRatePredictor()
        self.meta_predictor = GradientBoostingRegressor()
        self.domain_predictors = {
            'CV': DomainSpecificPredictor('CV'),
            'NLP': DomainSpecificPredictor('NLP'),
            # ...
        }

    def predict(self, question):
        # Get predictions from each model
        tfidf_pred = self.tfidf_predictor.predict(question)
        meta_pred = self.meta_predictor.predict(extract_features(question))
        domain_pred = self.domain_predictors[question['domain']].predict(question)

        # Weighted combination
        weights = [0.4, 0.3, 0.3]  # Learned from validation
        ensemble_pred = (
            weights[0] * tfidf_pred +
            weights[1] * meta_pred +
            weights[2] * domain_pred
        )

        # Ensemble uncertainty (disagreement = high uncertainty)
        predictions = [tfidf_pred, meta_pred, domain_pred]
        uncertainty = np.std(predictions)

        return ensemble_pred, uncertainty
```

**Benefits:**
- More robust (multiple signals)
- Better confidence estimates (disagreement = uncertainty)
- Handles different task types better

**Expected Impact:**
- Correlation: +0.05 to +0.10
- Better confidence estimates
- More stable predictions

---

## Recommended Action Plan

### Immediate (This Week) - Quick Wins

1. **K-Fold Cross-Validation** ⭐⭐⭐⭐⭐
   ```bash
   python train_tfidf_predictor.py --cv-folds 5
   ```
   - Get confidence intervals
   - 4-6 hours work
   - High confidence in results

2. **Add HumanEval + MBPP** ⭐⭐⭐⭐⭐
   ```bash
   python expand_code_benchmarks.py
   ```
   - 1,138 more questions (+450%)
   - 4-6 hours work
   - Huge impact

**Expected after 1 week:**
- Training data: 252 → 1,390 (5x more!)
- Correlation: 0.13 → 0.35-0.45 (with CI!)
- Confidence: 0.18 → 0.40-0.50
- **We'll KNOW if it's working (CI's!)**

---

### Short-term (2-4 Weeks)

3. **Meta-Features** ⭐⭐⭐⭐
   - Extract structural features
   - Train gradient boosting
   - Correlation: +0.10 to +0.15

4. **Kaggle Expansion** ⭐⭐⭐⭐
   - Add 200+ competitions
   - Better ML task coverage
   - Correlation: +0.05 to +0.10

**Expected after 1 month:**
- Training data: 1,500+
- Correlation: 0.50-0.60 (with CI!)
- MAE: 5.0-6.0%
- Confidence: 0.50-0.60

---

### Medium-term (1-2 Months)

5. **Ensemble Methods** ⭐⭐⭐
   - Combine multiple predictors
   - Better uncertainty estimates

6. **MATH + GSM8K** ⭐⭐⭐
   - 21,000 more questions
   - Huge sample size

**Expected after 2 months:**
- Training data: 20,000+
- Correlation: 0.60-0.70 (strong!)
- MAE: 4.0-5.0%
- Confidence: 0.60-0.70
- **Production-grade system**

---

## Success Metrics

### How will we know it's working?

**Tier 1: Statistical Confidence** ✅
- Correlation > 0.60 (strong positive)
- 95% CI width < 0.10 (tight bounds)
- MAE < 5% (accurate predictions)
- ECE < 0.05 (well-calibrated)

**Tier 2: Domain Performance** ✅
- All domains: Correlation > 0.50
- High-confidence predictions: MAE < 3%
- Low-uncertainty cases: 80%+ of predictions

**Tier 3: Real-World Validation** ✅
- Predictions match user experience
- Helps users choose models
- Reduces wasted compute on wrong models

---

## Summary

**Current State:**
- 252 questions
- Correlation: +0.13 (weak positive)
- Low confidence

**After Phase 1 (1 week):**
- 1,390 questions
- Correlation: +0.35-0.45 (moderate)
- With confidence intervals!

**After Phase 2 (1 month):**
- 1,500+ questions
- Correlation: +0.50-0.60 (strong)
- Multiple features

**After Phase 3 (2 months):**
- 20,000+ questions
- Correlation: +0.60-0.70 (very strong)
- Production-ready

**Priority Order:**
1. K-fold CV (confidence intervals) - **DO THIS FIRST**
2. Add HumanEval + MBPP (5x more data) - **HUGE IMPACT**
3. Meta-features (better predictions)
4. Kaggle expansion (more ML tasks)
5. Ensemble methods (robustness)
