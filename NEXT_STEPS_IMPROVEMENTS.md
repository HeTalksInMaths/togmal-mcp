# ToGMAL Next Steps: Adaptive Scoring & Nested CV

## Updated: 2025-10-21

This document outlines the immediate next steps to improve ToGMAL's difficulty assessment accuracy and establish a rigorous evaluation framework.

---

## 🎯 Immediate Goals (This Week)

### 1. **Implement Adaptive Uncertainty-Aware Scoring**
   - **Problem**: Current naive weighted average fails on low-similarity matches
   - **Example Failure**: "Prove universe is 10,000 years old" → matched to factual recall (similarity ~0.57) → incorrectly rated LOW risk
   - **Solution**: Add uncertainty penalties when:
     - Max similarity < 0.7 (weak best match)
     - High variance in k-NN similarities (diverse, unreliable matches)
     - Low average similarity (all matches are weak)
   - **File to modify**: `benchmark_vector_db.py::query_similar_questions()`
   - **Expected improvement**: 5-15% AUROC gain on low-similarity cases

### 2. **Export Database for Evaluation**
   - Add `get_all_questions_as_dataframe()` method to export 32K questions
   - Prepare for train/val/test splitting and nested CV
   - **File to modify**: `benchmark_vector_db.py`

### 3. **Test Adaptive Scoring**
   - Create test script with edge cases
   - Compare baseline vs. adaptive on known failure modes
   - **New file**: `test_adaptive_scoring.py`

---

## 📊 Evaluation Framework (Next 2-3 Weeks)

### Why Nested Cross-Validation?

**Problem with simple train/val/test split:**
- Single validation set can be lucky/unlucky (unrepresentative)
- Repeated "peeking" at validation during hyperparameter search causes data leakage
- Test set gives only ONE performance estimate (high variance)

**Nested CV advantages:**
- **Outer loop**: 5-fold CV for unbiased generalization estimate
- **Inner loop**: 3-fold grid search for hyperparameter tuning
- **No leakage**: Test folds never seen during tuning
- **Robust**: Multiple performance estimates across 5 different test sets

### Hyperparameters to Tune

```python
param_grid = {
    'k_neighbors': [3, 5, 7, 10],
    'similarity_threshold': [0.6, 0.7, 0.8],
    'low_sim_penalty': [0.3, 0.5, 0.7],
    'variance_penalty': [1.0, 2.0, 3.0],
    'low_avg_penalty': [0.2, 0.4, 0.6]
}
```

### Evaluation Metrics

1. **AUROC** (primary): Discriminative ability (0.5=random, 1.0=perfect)
2. **FPR@TPR95**: False positive rate when catching 95% of risky prompts
3. **AUPR**: Area under precision-recall curve (good for imbalanced data)
4. **Expected Calibration Error (ECE)**: Are predicted probabilities accurate?
5. **Brier Score**: Overall probabilistic prediction accuracy

---

## 🗂️ Implementation Phases

### Phase 1: Adaptive Scoring (This Week)
- [x] ✓ 32K vector database with 20 domains, 7 benchmark sources
- [ ] Add `_compute_adaptive_difficulty()` method
- [ ] Integrate uncertainty penalties into scoring
- [ ] Test on known failure cases
- [ ] Update `togmal_mcp.py` to use adaptive scoring

### Phase 2: Data Export & Baseline (Week 2)
- [ ] Add `get_all_questions_as_dataframe()` export method
- [ ] Create simple 70/15/15 train/val/test split
- [ ] Run current ToGMAL (baseline) on test set
- [ ] Compute baseline metrics:
  - AUROC
  - FPR@TPR95
  - Expected Calibration Error
  - Brier Score
- [ ] Document failure modes (low similarity, cross-domain, etc.)

### Phase 3: Nested CV Implementation (Week 3)
- [ ] Implement `NestedCVEvaluator` class
- [ ] Outer CV: 5-fold stratified by (domain × difficulty)
- [ ] Inner CV: 3-fold grid search over hyperparameters
- [ ] Temporary vector DB creation per fold
- [ ] Metrics computation on each outer fold

### Phase 4: Hyperparameter Tuning (Week 4)
- [ ] Run full nested CV (5 outer × 3 inner = 15 train-test runs)
- [ ] Collect best hyperparameters per fold
- [ ] Identify most common optimal parameters
- [ ] Compute mean ± std generalization performance
- [ ] Compare to baseline

### Phase 5: Final Model & Deployment (Week 5)
- [ ] Train final model on ALL 32K questions with best hyperparameters
- [ ] Re-index full vector database
- [ ] Deploy to MCP server and HTTP facade
- [ ] Test with Claude Desktop

### Phase 6: OOD Testing (Week 6)
- [ ] Create OOD test sets:
  - **Adversarial**: "Prove false premises", jailbreaks
  - **Domain Shift**: Creative writing, coding, real user queries
  - **Temporal**: New benchmarks (2024+)
- [ ] Evaluate on each OOD set
- [ ] Analyze performance degradation vs. in-distribution

### Phase 7: Iteration & Documentation (Week 7)
- [ ] Analyze failures on OOD sets
- [ ] Add new heuristics for missed patterns
- [ ] Re-run nested CV with updated features
- [ ] Generate calibration plots (reliability diagrams)
- [ ] Write technical report

---

## 📈 Expected Improvements

Based on OOD detection literature and nested CV best practices:

1. **Adaptive scoring**: +5-15% AUROC on low-similarity cases
   - Baseline: ~0.75 AUROC (naive weighted average)
   - Target: ~0.85+ AUROC (adaptive with uncertainty)

2. **Nested CV**: Honest, robust performance estimates
   - Simple split: Single point estimate (could be lucky/unlucky)
   - Nested CV: Mean ± std across 5 folds

3. **Domain calibration**: -10-20% false positives
   - Expected: FPR@TPR95 drops from ~0.25 to ~0.15

4. **Multi-signal fusion**: Better edge case detection
   - Combine vector similarity + rule-based heuristics
   - Improved recall on adversarial examples

5. **Calibration**: ECE < 0.05
   - Better alignment between predicted risk and actual difficulty

---

## ✅ Validation Checklist (Before Production Deploy)

- [ ] Nested CV completed with no data leakage
- [ ] Hyperparameters tuned on inner CV folds only
- [ ] Generalization performance estimated on outer CV folds
- [ ] OOD sets tested (adversarial, domain-shift, temporal)
- [ ] Calibration error within acceptable range (ECE < 0.1)
- [ ] Failure modes documented with specific examples
- [ ] Ablation studies show each component contributes
- [ ] Performance: adaptive > baseline on all metrics
- [ ] Real-world testing with user queries

---

## 🚀 Quick Start Command

See `togmal_improvement_plan.md` for full implementation details including:
- Complete code for `NestedCVEvaluator` class
- Adaptive scoring implementation
- All evaluation metrics with examples
- Detailed roadmap with weekly milestones

**Next Action**: Implement adaptive scoring in `benchmark_vector_db.py` and test with edge cases.
