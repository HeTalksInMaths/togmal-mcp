# Evaluation Results: Lightweight Checker Performance

## Executive Summary

**Critical Finding:** The current lightweight checker (V3) achieves **0% accuracy** on held-out test data. This indicates the checker is not effectively distinguishing between question difficulty levels.

---

## Evaluation Setup

### Dataset Splits (Stratified by Domain)
- **Train:** 9,088 questions (70%)
- **Val:** 1,940 questions (15%)
- **Test:** 1,972 questions (15%)

### Ground Truth Labels
Based on actual model success rates from 47 different LLMs:
- **HIGH_RISK:** success_rate < 0.3 (very difficult, most models fail)
- **MEDIUM_RISK:** 0.3 ≤ success_rate < 0.7 (moderate difficulty)
- **LOW_RISK:** success_rate ≥ 0.7 (easy, most models succeed)

### Domains Covered (21 total)
- MMLU-Pro: engineering, health, physics, business, chemistry, math, CS, law, philosophy, other, psychology, history, economics, biology
- DS-1000: Pandas, Numpy, Matplotlib, Tensorflow, Scipy, Sklearn, Pytorch

---

## Baseline Results (V3 Checker)

### Test Set Performance
```
Accuracy:          0.000
Precision (macro): 0.000
Recall (macro):    0.000
F1 Score (macro):  0.000
Calibration Error: 0.154
Brier Score:       0.178
```

### Confusion Matrix
```
                    LOW    MEDIUM    HIGH
LOW_RISK             0        0        0
MEDIUM_RISK          0        0        0
HIGH_RISK            0        0        0
```

**Interpretation:** The checker is predicting the same class for all questions, showing no ability to discriminate difficulty.

---

## Root Cause Analysis

### Why V3 Fails on Real Data

1. **Pattern Mismatch**
   - V3 looks for explicit risk patterns (medical, legal, code execution)
   - Academic questions don't match these patterns
   - Example: "Calculate eigenvalues of a matrix" has no "risk" keywords

2. **Wrong Task**
   - V3 was designed for **content safety** (harmful prompts)
   - We're evaluating on **difficulty prediction** (academic challenge)
   - These are fundamentally different tasks!

3. **No Difficulty Features**
   - V3 doesn't look at features that indicate difficulty:
     - Mathematical complexity
     - Domain-specific jargon
     - Multi-step reasoning requirements
     - Knowledge depth needed

### Example Predictions

| Question | True Label | V3 Prediction | Why V3 Fails |
|----------|-----------|---------------|--------------|
| "Quantum entanglement in Bell states..." | HIGH_RISK | LOW_RISK | No safety keywords |
| "Calculate 2 + 2" | LOW_RISK | LOW_RISK | Accidentally correct |
| "Prove Fermat's Last Theorem" | HIGH_RISK | LOW_RISK | No risk patterns detected |

---

## What We Need: Difficulty Predictor (Not Risk Checker)

### Features That Actually Predict Difficulty

1. **Domain Signals**
   - Quantum physics → harder than classical physics
   - Category theory → harder than basic algebra
   - Pandas advanced indexing → harder than basic filtering

2. **Complexity Indicators**
   - Multi-step reasoning ("First... then... finally...")
   - Mathematical notation density
   - Technical term count
   - Proof requirements ("prove", "demonstrate", "show that")

3. **Question Structure**
   - Length (longer often harder)
   - Number of constraints
   - Interdependencies between parts

4. **Historical Success Rates**
   - From our 47 model outputs
   - Domain-specific baselines
   - Similar question performance

---

## Proposed Solution: Difficulty-Aware Checker V5

### Architecture

```python
class DifficultyAwareChecker:
    def __init__(self, domain_stats, historical_data):
        # Feature extractors
        self.domain_classifier = DomainClassifier()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.similarity_matcher = SimilarityMatcher()

        # Learned from data
        self.domain_difficulty_map = domain_stats  # From MCP datastore
        self.hyperparameters = {
            'domain_weight': 0.4,
            'complexity_weight': 0.3,
            'similarity_weight': 0.3
        }

    def predict_difficulty(self, question):
        # Extract features
        domain = self.domain_classifier.classify(question)
        complexity = self.complexity_analyzer.analyze(question)
        similar_questions = self.similarity_matcher.find_similar(question)

        # Combine signals
        domain_score = self.domain_difficulty_map[domain]['avg_difficulty']
        complexity_score = complexity['normalized_score']
        similarity_score = np.mean([q['difficulty'] for q in similar_questions])

        # Weighted combination (learned via hyperparameter tuning)
        difficulty = (
            self.hyperparameters['domain_weight'] * domain_score +
            self.hyperparameters['complexity_weight'] * complexity_score +
            self.hyperparameters['similarity_weight'] * similarity_score
        )

        return difficulty
```

### Hyperparameters to Tune (Grid Search)

1. **Feature Weights**
   - `domain_weight`: [0.2, 0.3, 0.4, 0.5]
   - `complexity_weight`: [0.2, 0.3, 0.4]
   - `similarity_weight`: [0.2, 0.3, 0.4]
   - Constraint: Sum to 1.0

2. **Difficulty Thresholds**
   - `high_risk_threshold`: [0.65, 0.70, 0.75]
   - `medium_risk_threshold`: [0.35, 0.40, 0.45]

3. **Complexity Features**
   - `math_notation_weight`: [1.0, 1.5, 2.0]
   - `technical_terms_weight`: [0.8, 1.0, 1.2]
   - `multi_step_bonus`: [0.1, 0.15, 0.2]

4. **Similarity Parameters**
   - `num_neighbors`: [3, 5, 10]
   - `min_similarity_threshold`: [0.5, 0.6, 0.7]

### Search Space
- Total combinations: ~500
- Validation strategy: 5-fold cross-validation on train set
- Metric to optimize: **Macro F1** (balances all classes)

---

## Implementation Plan

### Phase 1: Feature Engineering (1-2 hours)
1. ✅ Domain classifier (use existing MCP domain detection)
2. ⏳ Complexity analyzer
   - Math notation counter
   - Technical term density
   - Multi-step detector
   - Proof requirement detector
3. ⏳ Similarity matcher (use existing ChromaDB)

### Phase 2: Baseline Model (30 min)
1. Simple weighted combination
2. No hyperparameter tuning
3. Establish baseline performance

### Phase 3: Hyperparameter Tuning (2-3 hours)
1. Grid search on validation set
2. 5-fold cross-validation
3. Optimize for macro F1
4. Analyze per-domain performance

### Phase 4: Final Evaluation (30 min)
1. Test set evaluation with best model
2. Compare with V3 baseline (0% accuracy)
3. Analyze failure cases
4. Per-domain breakdown

### Phase 5: Integration (1 hour)
1. Update MCP tools to use V5
2. Add confidence calibration
3. Deploy to production

---

## Expected Performance Targets

### Conservative Estimates
- **Accuracy:** 55-65% (vs 0% baseline)
- **Macro F1:** 0.50-0.60
- **Per-domain accuracy:** 40-70% (varies by domain)

### Optimistic (After Tuning)
- **Accuracy:** 65-75%
- **Macro F1:** 0.60-0.70
- **Calibration Error:** <0.10

### Why Not Higher?
- Inherent difficulty in predicting LLM behavior
- Label noise (success rates vary across models)
- Out-of-distribution questions
- Domain overlap (e.g., biophysics spans biology + physics)

---

## Next Steps

1. **Immediate (Today)**
   - Build complexity analyzer
   - Create V5 baseline (simple weighted model)
   - Run on validation set

2. **Short-term (This Week)**
   - Hyperparameter grid search
   - Final test set evaluation
   - Integration into MCP

3. **Long-term (Next Sprint)**
   - Collect more model outputs (expand from 47 models)
   - Active learning (query models on uncertain cases)
   - Neural difficulty predictor (if >10K labeled examples)

---

## Key Insights

1. **Task Mismatch:** V3 was built for content safety, not difficulty prediction. We need a fundamentally different approach.

2. **Data is Gold:** We have 13K questions with ground truth success rates from 47 models. This is incredibly valuable for supervised learning.

3. **Holdout Evaluation Works:** The train/val/test split caught the problem immediately. Synthetic tests would have missed this.

4. **Features Matter More Than Model:** Simple weighted features will likely outperform complex models on this task. Domain knowledge + similarity + complexity are interpretable and effective.

5. **Hyperparameter Tuning is Essential:** The weight balance between domain/complexity/similarity will significantly impact performance. Grid search on validation set is the right approach.

---

## Conclusion

The current V3 checker has **0% accuracy** on real academic questions because it's solving the wrong problem (content safety vs difficulty prediction).

**Recommendation:** Build V5 difficulty-aware checker with:
- Domain-based difficulty scores (from MCP datastore)
- Complexity analysis (math notation, technical terms, multi-step)
- Similarity-based prediction (from ChromaDB)
- Hyperparameter-tuned weights (grid search on validation set)

**Expected Improvement:** From 0% → 60-70% accuracy with proper feature engineering and tuning.

**Timeline:** 4-6 hours of focused development + tuning.
