# ToGMAL Improvement Plan: Adaptive Scoring & Evaluation Framework

## Executive Summary

This plan addresses two critical gaps in togmal's current implementation:
1. **Naive weighted averaging fails when retrieved questions have low similarity** to the prompt
2. **Lack of rigorous evaluation methodology** to measure OOD detection performance

---

## Problem 1: Low-Similarity Scoring Issues

### Current Limitation
Your system uses a simple weighted average of difficulty scores from k-nearest neighbors, which produces unreliable risk assessments when:
- Maximum similarity < 0.6 (semantically distant matches)
- Retrieved questions span multiple unrelated domains
- Query is truly novel/out-of-distribution

**Example:** "Prove universe is 10,000 years old" matched to factual recall questions about Earth's age (similarity ~0.57), resulting in LOW risk despite being a "prove false premise" pattern.

### Solution: Adaptive Uncertainty-Aware Scoring

#### 1. Similarity-Based Confidence Adjustment

Implement a **confidence decay function** that increases risk when similarity is low:

```python
def compute_adaptive_risk(similarities, difficulties, k=5):
    """
    Adjust risk score based on retrieval confidence
    """
    # Base weighted score
    weights = np.array(similarities) / sum(similarities)
    base_score = np.dot(weights, difficulties)
    
    # Confidence metrics
    max_sim = max(similarities)
    avg_sim = np.mean(similarities)
    sim_variance = np.var(similarities)
    
    # Uncertainty penalty - increase risk when:
    # - Max similarity is low (< 0.7)
    # - High variance in similarities (diverse matches)
    # - Average similarity is low
    
    uncertainty_penalty = 0.0
    
    # Low maximum similarity threshold
    if max_sim < 0.7:
        uncertainty_penalty += (0.7 - max_sim) * 0.5
    
    # High variance (retrieved questions are dissimilar to each other)
    if sim_variance > 0.05:
        uncertainty_penalty += min(sim_variance * 2, 0.3)
    
    # Low average similarity
    if avg_sim < 0.5:
        uncertainty_penalty += (0.5 - avg_sim) * 0.4
    
    # Adjusted score (higher = more risky)
    adjusted_score = base_score + uncertainty_penalty
    
    # Map to risk levels
    if adjusted_score < 0.2:
        return "MINIMAL"
    elif adjusted_score < 0.4:
        return "LOW"  
    elif adjusted_score < 0.6:
        return "MODERATE"
    elif adjusted_score < 0.8:
        return "HIGH"
    else:
        return "CRITICAL"
```

**Key Insight:** Research shows that cosine similarity thresholds vary by domain and task. Values 0.7-0.8 are commonly recommended starting points for "relevant" matches. Below 0.6, matches become increasingly unreliable.

#### 2. Multi-Signal Fusion

Combine multiple indicators beyond just k-NN similarity:

```python
def compute_risk_with_fusion(prompt, knn_results, heuristics):
    """
    Fuse vector similarity with rule-based heuristics
    """
    # Vector-based score (from k-NN)
    vector_score = compute_adaptive_risk(
        knn_results['similarities'],
        knn_results['difficulties']
    )
    
    # Rule-based heuristics (existing togmal patterns)
    heuristic_score = heuristics.evaluate(prompt)
    
    # Domain classifier (is this math/physics/medical?)
    domain_confidence = classify_domain(prompt)
    
    # Combine scores with learned weights
    final_score = (
        0.4 * vector_score + 
        0.4 * heuristic_score +
        0.2 * domain_uncertainty(domain_confidence)
    )
    
    return final_score
```

#### 3. Threshold Calibration per Domain

Different domains need different thresholds. Implement **domain-specific calibration**:

```python
# Learned from validation data
DOMAIN_THRESHOLDS = {
    'math': {'low': 0.65, 'moderate': 0.75, 'high': 0.85},
    'physics': {'low': 0.60, 'moderate': 0.70, 'high': 0.80},
    'medical': {'low': 0.70, 'moderate': 0.80, 'high': 0.90},
    'general': {'low': 0.60, 'moderate': 0.70, 'high': 0.80}
}

def get_calibrated_threshold(domain, risk_level):
    return DOMAIN_THRESHOLDS.get(domain, DOMAIN_THRESHOLDS['general'])[risk_level]
```

---

## Problem 2: Evaluation & Generalization

### Proposed Evaluation Framework: Nested Cross-Validation (Gold Standard)

#### Why Nested CV > Simple Train/Val/Test Split

**Problem with simple splits:**
- Single validation set can be unrepresentative (lucky/unlucky split)
- Repeated "peeking" at validation during hyperparameter search causes leakage
- Test set provides only ONE estimate of generalization (high variance)

**Nested CV advantages:**
- **Outer loop**: K-fold CV for unbiased generalization estimate
- **Inner loop**: Hyperparameter search on each training fold
- **No leakage**: Test folds never seen during tuning
- **Multiple estimates**: Robust performance across K different test sets

#### Implementation: Nested Cross-Validation

```python
from sklearn.model_selection import StratifiedKFold, GridSearchCV
import numpy as np
from typing import Dict, List, Any

class NestedCVEvaluator:
    """
    Nested cross-validation for ToGMAL hyperparameter tuning and evaluation.
    
    Outer CV: 5-fold stratified CV for generalization estimate
    Inner CV: 3-fold stratified CV for hyperparameter search
    
    This prevents data leakage from "peeking" at validation during tuning.
    """
    
    def __init__(
        self,
        benchmark_data,
        outer_folds: int = 5,
        inner_folds: int = 3,
        random_state: int = 42
    ):
        self.data = benchmark_data
        self.outer_folds = outer_folds
        self.inner_folds = inner_folds
        self.random_state = random_state
        
        # Stratify by (domain, difficulty) to ensure balanced folds
        self.stratify_labels = (
            benchmark_data['domain'].astype(str) + '_' + 
            benchmark_data['difficulty_label'].astype(str)
        )
    
    def run_nested_cv(
        self,
        param_grid: Dict[str, List[Any]],
        scoring_metric: str = 'roc_auc'
    ) -> Dict[str, Any]:
        """
        Run nested cross-validation.
        
        Args:
            param_grid: Hyperparameters to search (e.g., {'k': [3,5,7], 'threshold': [0.6,0.7]})
            scoring_metric: Metric for optimization (roc_auc, f1, etc.)
        
        Returns:
            Dictionary with:
            - outer_scores: Generalization performance on each outer fold
            - best_params_per_fold: Optimal hyperparameters found in each inner CV
            - mean_test_score: Average performance across outer folds
            - std_test_score: Standard deviation (uncertainty estimate)
        """
        
        # Outer CV: For generalization estimate
        outer_cv = StratifiedKFold(
            n_splits=self.outer_folds,
            shuffle=True,
            random_state=self.random_state
        )
        
        outer_scores = []
        best_params_per_fold = []
        
        print("Starting Nested Cross-Validation...")
        print(f"Outer CV: {self.outer_folds} folds")
        print(f"Inner CV: {self.inner_folds} folds")
        print(f"Param grid: {param_grid}")
        print("="*80)
        
        for fold_idx, (train_idx, test_idx) in enumerate(outer_cv.split(self.data, self.stratify_labels)):
            print(f"\nOuter Fold {fold_idx + 1}/{self.outer_folds}")
            
            # Split data for this outer fold
            train_data = self.data.iloc[train_idx]
            test_data = self.data.iloc[test_idx]
            
            # Inner CV: Hyperparameter search on training data ONLY
            inner_cv = StratifiedKFold(
                n_splits=self.inner_folds,
                shuffle=True,
                random_state=self.random_state
            )
            
            # Run grid search on inner folds
            best_params, best_inner_score = self._inner_grid_search(
                train_data,
                param_grid,
                inner_cv,
                scoring_metric
            )
            
            print(f"  Inner CV best params: {best_params}")
            print(f"  Inner CV best score: {best_inner_score:.4f}")
            
            # Build ToGMAL vector DB with ONLY training data
            vector_db = self._build_vector_db(train_data)
            
            # Evaluate on held-out test fold with best hyperparameters
            test_score = self._evaluate_on_test_fold(
                vector_db,
                test_data,
                best_params,
                scoring_metric
            )
            
            print(f"  Outer test score: {test_score:.4f}")
            
            outer_scores.append(test_score)
            best_params_per_fold.append(best_params)
        
        # Aggregate results
        mean_score = np.mean(outer_scores)
        std_score = np.std(outer_scores)
        
        print("\n" + "="*80)
        print("Nested CV Results:")
        print(f"  Outer scores: {[f'{s:.4f}' for s in outer_scores]}")
        print(f"  Mean ± Std: {mean_score:.4f} ± {std_score:.4f}")
        print("="*80)
        
        return {
            'outer_scores': outer_scores,
            'mean_test_score': mean_score,
            'std_test_score': std_score,
            'best_params_per_fold': best_params_per_fold,
            'most_common_params': self._find_most_common_params(best_params_per_fold)
        }
    
    def _inner_grid_search(
        self,
        train_data,
        param_grid: Dict[str, List[Any]],
        inner_cv,
        scoring_metric: str
    ) -> tuple:
        """
        Grid search over hyperparameters using inner CV folds.
        Returns (best_params, best_score)
        """
        stratify = (
            train_data['domain'].astype(str) + '_' + 
            train_data['difficulty_label'].astype(str)
        )
        
        best_score = -np.inf
        best_params = {}
        
        # Generate all parameter combinations
        from itertools import product
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        for param_combo in product(*param_values):
            params = dict(zip(param_names, param_combo))
            
            # Evaluate this parameter combination on inner folds
            fold_scores = []
            
            for inner_train_idx, inner_val_idx in inner_cv.split(train_data, stratify):
                inner_train = train_data.iloc[inner_train_idx]
                inner_val = train_data.iloc[inner_val_idx]
                
                # Build vector DB with inner training data
                inner_db = self._build_vector_db(inner_train)
                
                # Evaluate on inner validation
                score = self._evaluate_on_test_fold(
                    inner_db,
                    inner_val,
                    params,
                    scoring_metric
                )
                fold_scores.append(score)
            
            avg_score = np.mean(fold_scores)
            
            if avg_score > best_score:
                best_score = avg_score
                best_params = params
        
        return best_params, best_score
    
    def _build_vector_db(self, train_data):
        """Build vector database from training data."""
        from benchmark_vector_db import BenchmarkVectorDB, BenchmarkQuestion
        from pathlib import Path
        import tempfile
        
        # Create temporary DB for this fold
        temp_dir = tempfile.mkdtemp()
        db = BenchmarkVectorDB(
            db_path=Path(temp_dir) / "fold_db",
            embedding_model="all-MiniLM-L6-v2"
        )
        
        # Convert dataframe to BenchmarkQuestion objects
        questions = [
            BenchmarkQuestion(
                question_id=row['question_id'],
                source_benchmark=row['source_benchmark'],
                domain=row['domain'],
                question_text=row['question_text'],
                correct_answer=row['correct_answer'],
                success_rate=row['success_rate'],
                difficulty_score=row['difficulty_score'],
                difficulty_label=row['difficulty_label']
            )
            for _, row in train_data.iterrows()
        ]
        
        db.index_questions(questions)
        return db
    
    def _evaluate_on_test_fold(
        self,
        vector_db,
        test_data,
        params: Dict[str, Any],
        metric: str
    ) -> float:
        """
        Evaluate ToGMAL on test fold with given hyperparameters.
        
        Args:
            vector_db: Vector database built from training data
            test_data: Held-out test fold
            params: Hyperparameters (e.g., k, similarity_threshold, weights)
            metric: Scoring metric (roc_auc, f1, etc.)
        """
        from sklearn.metrics import roc_auc_score, f1_score
        
        predictions = []
        ground_truth = []
        
        for _, row in test_data.iterrows():
            # Query vector DB with test question
            result = vector_db.query_similar_questions(
                prompt=row['question_text'],
                k=params.get('k_neighbors', 5)
            )
            
            # Apply adaptive scoring with hyperparameters
            risk_score = self._compute_adaptive_risk(
                result,
                params
            )
            
            predictions.append(risk_score)
            
            # Ground truth: is this question hard? (success_rate < 0.5)
            ground_truth.append(1 if row['success_rate'] < 0.5 else 0)
        
        # Compute metric
        if metric == 'roc_auc':
            return roc_auc_score(ground_truth, predictions)
        elif metric == 'f1':
            # Binarize predictions at 0.5 threshold
            binary_preds = [1 if p > 0.5 else 0 for p in predictions]
            return f1_score(ground_truth, binary_preds)
        else:
            raise ValueError(f"Unknown metric: {metric}")
    
    def _compute_adaptive_risk(
        self,
        query_result: Dict[str, Any],
        params: Dict[str, Any]
    ) -> float:
        """
        Compute risk score with adaptive uncertainty penalties.
        Uses hyperparameters from inner CV search.
        """
        similarities = [q['similarity'] for q in query_result['similar_questions']]
        difficulties = [q['difficulty_score'] for q in query_result['similar_questions']]
        
        # Base weighted average
        weights = np.array(similarities) / sum(similarities)
        base_score = np.dot(weights, difficulties)
        
        # Adaptive uncertainty penalties
        max_sim = max(similarities)
        avg_sim = np.mean(similarities)
        sim_variance = np.var(similarities)
        
        uncertainty_penalty = 0.0
        
        # Low similarity threshold (configurable)
        sim_threshold = params.get('similarity_threshold', 0.7)
        if max_sim < sim_threshold:
            uncertainty_penalty += (sim_threshold - max_sim) * params.get('low_sim_penalty', 0.5)
        
        # High variance penalty
        if sim_variance > 0.05:
            uncertainty_penalty += min(sim_variance * params.get('variance_penalty', 2.0), 0.3)
        
        # Low average similarity
        if avg_sim < 0.5:
            uncertainty_penalty += (0.5 - avg_sim) * params.get('low_avg_penalty', 0.4)
        
        # Final score
        adjusted_score = base_score + uncertainty_penalty
        
        return np.clip(adjusted_score, 0.0, 1.0)
    
    def _find_most_common_params(self, params_list: List[Dict]) -> Dict:
        """Find the most frequently selected hyperparameters across folds."""
        from collections import Counter
        
        # For each parameter, find the most common value
        all_param_names = params_list[0].keys()
        most_common = {}
        
        for param_name in all_param_names:
            values = [p[param_name] for p in params_list]
            most_common[param_name] = Counter(values).most_common(1)[0][0]
        
        return most_common


# Example usage
if __name__ == "__main__":
    import pandas as pd
    from benchmark_vector_db import BenchmarkVectorDB
    
    # Load all benchmark questions
    db = BenchmarkVectorDB(db_path=Path("/Users/hetalksinmaths/togmal/data/benchmark_vector_db"))
    stats = db.get_statistics()
    
    # Get all questions as dataframe (you'll need to implement this)
    all_questions_df = db.get_all_questions_as_dataframe()
    
    # Define hyperparameter search grid
    param_grid = {
        'k_neighbors': [3, 5, 7, 10],
        'similarity_threshold': [0.6, 0.7, 0.8],
        'low_sim_penalty': [0.3, 0.5, 0.7],
        'variance_penalty': [1.0, 2.0, 3.0],
        'low_avg_penalty': [0.2, 0.4, 0.6]
    }
    
    # Run nested CV
    evaluator = NestedCVEvaluator(
        benchmark_data=all_questions_df,
        outer_folds=5,  # 5-fold outer CV
        inner_folds=3   # 3-fold inner CV for hyperparameter search
    )
    
    results = evaluator.run_nested_cv(
        param_grid=param_grid,
        scoring_metric='roc_auc'
    )
    
    print("\nFinal Results:")
    print(f"Generalization Performance: {results['mean_test_score']:.4f} ± {results['std_test_score']:.4f}")
    print(f"Most Common Best Params: {results['most_common_params']}")
```

**Key Advantages:**
- **No leakage**: Each outer test fold is never seen during hyperparameter tuning
- **Robust estimates**: 5 different generalization scores (not just 1)
- **Automatic tuning**: Inner CV finds best hyperparameters for each fold
- **Confidence intervals**: Standard deviation tells you uncertainty in performance

#### Phase 2: Define Evaluation Metrics

Use standard **OOD detection metrics** + **calibration metrics**:

1. **AUROC** (Area Under ROC Curve)
   - Threshold-independent
   - Measures overall discriminative ability
   - Gold standard for OOD detection
   - Interpretation: Probability that a random risky prompt is ranked higher than a random safe prompt

2. **FPR@TPR95** (False Positive Rate at 95% True Positive Rate)
   - How many safe prompts are incorrectly flagged when catching 95% of risky ones
   - Common in safety-critical applications
   - Lower is better (want to minimize false alarms)

3. **AUPR** (Area Under Precision-Recall Curve)
   - Better for imbalanced datasets
   - Useful when risky prompts are rare
   - Focuses on positive class (risky prompts)

4. **Expected Calibration Error (ECE)**
   - Are your risk probabilities accurate?
   - If you say 70% risky, is it actually 70% risky?
   - Measures gap between predicted probabilities and observed frequencies

5. **Brier Score**
   - Measures accuracy of probabilistic predictions
   - Lower is better
   - Combines discrimination and calibration

```python
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc, brier_score_loss
import numpy as np

def compute_fpr_at_tpr(y_true, y_pred_proba, tpr_threshold=0.95):
    """Compute FPR when TPR is at specified threshold."""
    from sklearn.metrics import roc_curve
    
    fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)
    
    # Find index where TPR >= threshold
    idx = np.argmax(tpr >= tpr_threshold)
    
    return fpr[idx]

def expected_calibration_error(y_true, y_pred_proba, n_bins=10):
    """
    Compute Expected Calibration Error (ECE).
    
    Bins predictions into n_bins buckets and measures the gap between
    predicted probability and observed frequency in each bin.
    """
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]
    
    ece = 0.0
    
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        # Find predictions in this bin
        in_bin = (y_pred_proba > bin_lower) & (y_pred_proba <= bin_upper)
        prop_in_bin = in_bin.mean()
        
        if prop_in_bin > 0:
            # Observed frequency in this bin
            accuracy_in_bin = y_true[in_bin].mean()
            # Average predicted probability in this bin
            avg_confidence_in_bin = y_pred_proba[in_bin].mean()
            
            # Contribution to ECE
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
    
    return ece

def evaluate_togmal(predictions, ground_truth):
    """
    Comprehensive evaluation of ToGMAL performance.
    
    Args:
        predictions: Dict with 'risk_score' (continuous 0-1) and 'risk_level' (categorical)
        ground_truth: Array of difficulty scores or binary labels (0=easy, 1=hard)
    
    Returns:
        Dictionary with all evaluation metrics
    """
    # Convert ground truth to binary if needed (HIGH/CRITICAL = 1, else = 0)
    if hasattr(ground_truth, 'success_rate'):
        y_true = (ground_truth['success_rate'] < 0.5).astype(int)
    else:
        y_true = ground_truth
    
    y_pred_proba = predictions['risk_score']  # Continuous 0-1
    y_pred_binary = (y_pred_proba > 0.5).astype(int)  # Binarized
    
    # AUROC
    auroc = roc_auc_score(y_true, y_pred_proba)
    
    # FPR@TPR95
    fpr_at_95_tpr = compute_fpr_at_tpr(y_true, y_pred_proba, tpr_threshold=0.95)
    
    # AUPR
    precision, recall, _ = precision_recall_curve(y_true, y_pred_proba)
    aupr = auc(recall, precision)
    
    # Calibration error
    ece = expected_calibration_error(y_true, y_pred_proba, n_bins=10)
    
    # Brier score (lower is better)
    brier = brier_score_loss(y_true, y_pred_proba)
    
    # Standard classification metrics (for reference)
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
    
    accuracy = accuracy_score(y_true, y_pred_binary)
    f1 = f1_score(y_true, y_pred_binary)
    precision = precision_score(y_true, y_pred_binary)
    recall = recall_score(y_true, y_pred_binary)
    
    return {
        # Primary OOD detection metrics
        'AUROC': auroc,
        'FPR@TPR95': fpr_at_95_tpr,
        'AUPR': aupr,
        
        # Calibration metrics
        'ECE': ece,
        'Brier_Score': brier,
        
        # Standard classification (for reference)
        'Accuracy': accuracy,
        'F1': f1,
        'Precision': precision,
        'Recall': recall
    }

def print_evaluation_report(metrics: dict):
    """Pretty print evaluation metrics."""
    print("\n" + "="*80)
    print("ToGMAL Evaluation Report")
    print("="*80)
    
    print("\nOOD Detection Performance:")
    print(f"  AUROC:          {metrics['AUROC']:.4f}  (higher is better, 0.5=random, 1.0=perfect)")
    print(f"  FPR@TPR95:      {metrics['FPR@TPR95']:.4f}  (lower is better, false alarm rate)")
    print(f"  AUPR:           {metrics['AUPR']:.4f}  (higher is better)")
    
    print("\nCalibration:")
    print(f"  ECE:            {metrics['ECE']:.4f}  (lower is better, 0=perfect calibration)")
    print(f"  Brier Score:    {metrics['Brier_Score']:.4f}  (lower is better)")
    
    print("\nClassification Metrics (for reference):")
    print(f"  Accuracy:       {metrics['Accuracy']:.4f}")
    print(f"  F1 Score:       {metrics['F1']:.4f}")
    print(f"  Precision:      {metrics['Precision']:.4f}")
    print(f"  Recall:         {metrics['Recall']:.4f}")
    
    print("\n" + "="*80)
```

#### Phase 3: Out-of-Distribution Testing

**Critical:** Test on data that's truly OOD from your training benchmarks.

**OOD Test Sets to Create:**

1. **Temporal OOD**: New benchmark questions released after your training data cutoff
2. **Domain Shift**: Categories not in MMLU (e.g., creative writing prompts, coding challenges)
3. **Adversarial**: Hand-crafted examples designed to fool the system
   - "Prove [false scientific claim]"
   - Jailbreak attempts disguised as innocent questions
   - Edge cases from your taxonomy submissions

```python
ood_test_sets = {
    'adversarial_false_premises': load_false_premise_examples(),
    'jailbreaks': load_jailbreak_attempts(),
    'creative_writing': load_writing_prompts(),
    'recent_benchmarks': load_benchmarks_after('2024-01'),
    'user_submissions': load_taxonomy_entries()
}

# Evaluate on each OOD set
for name, test_data in ood_test_sets.items():
    metrics = evaluate_togmal(model.predict(test_data), test_data.labels)
    print(f"{name}: AUROC={metrics['AUROC']:.3f}, FPR@95={metrics['FPR@TPR95']:.3f}")
```

#### Phase 4: Hyperparameter Tuning Protocol

**Use validation set ONLY** - never touch test set until final evaluation.

```python
from sklearn.model_selection import GridSearchCV

# Parameters to tune
param_grid = {
    'similarity_threshold': [0.5, 0.6, 0.7, 0.8],
    'k_neighbors': [3, 5, 7, 10],
    'uncertainty_penalty_weight': [0.2, 0.4, 0.6],
    'heuristic_weight': [0.3, 0.4, 0.5],
    'vector_weight': [0.3, 0.4, 0.5]
}

# Cross-validation on validation set
best_params = grid_search_cv(
    togmal_model,
    param_grid,
    val_set,
    metric='AUROC',
    cv=5  # 5-fold CV within validation set
)

# Train final model with best params on train + val
final_model = train_togmal(
    train_set + val_set,
    params=best_params
)

# Evaluate ONCE on test set
final_metrics = evaluate_togmal(
    final_model.predict(test_set),
    test_set.labels
)
```

---

## Implementation Roadmap

### Phase 1: Adaptive Scoring Implementation (Week 1-2)
- [x] ✓ Implement basic vector database with 32K questions
- [ ] Add adaptive uncertainty-aware scoring function
  - [ ] Similarity threshold penalties
  - [ ] Variance penalties for diverse matches
  - [ ] Low average similarity penalties
- [ ] Implement domain-specific threshold calibration
- [ ] Add multi-signal fusion (vector + heuristics)
- [ ] Integrate into `benchmark_vector_db.py::query_similar_questions()`

### Phase 2: Data Export & Preparation (Week 2)
- [ ] Export all 32K questions from ChromaDB to pandas DataFrame
  - [ ] Add `BenchmarkVectorDB.get_all_questions_as_dataframe()` method
  - [ ] Include all metadata (domain, difficulty, success_rate, etc.)
- [ ] Verify stratification labels (domain × difficulty)
- [ ] Create initial train/val/test split (simple 70/15/15) for baseline
- [ ] Document dataset statistics per split

### Phase 3: Nested CV Framework (Week 3)
- [ ] Implement `NestedCVEvaluator` class
  - [ ] Outer CV loop (5-fold stratified)
  - [ ] Inner CV loop (3-fold grid search)
  - [ ] Temporary vector DB creation per fold
- [ ] Define hyperparameter search grid
  - `k_neighbors`: [3, 5, 7, 10]
  - `similarity_threshold`: [0.6, 0.7, 0.8]
  - `low_sim_penalty`: [0.3, 0.5, 0.7]
  - `variance_penalty`: [1.0, 2.0, 3.0]
  - `low_avg_penalty`: [0.2, 0.4, 0.6]
- [ ] Implement evaluation metrics (AUROC, FPR@TPR95, ECE)

### Phase 4: Baseline Evaluation (Week 3-4)
- [ ] Run current ToGMAL (naive weighted average) on simple split
- [ ] Compute baseline metrics:
  - [ ] AUROC on test set
  - [ ] FPR@TPR95
  - [ ] Expected Calibration Error
  - [ ] Brier Score
- [ ] Analyze failure modes:
  - [ ] Low similarity cases (max_sim < 0.6)
  - [ ] High variance matches
  - [ ] Cross-domain queries
- [ ] Document baseline performance for comparison

### Phase 5: Nested CV Hyperparameter Tuning (Week 4-5)
- [ ] Run full nested CV (5 outer × 3 inner = 15 train-test runs)
- [ ] Track computational cost (time per fold)
- [ ] Collect best hyperparameters per outer fold
- [ ] Identify most common optimal parameters
- [ ] Compute mean ± std generalization performance

### Phase 6: Final Model Training (Week 5)
- [ ] Train final model on ALL 32K questions with best hyperparameters
- [ ] Re-index full vector database
- [ ] Update `togmal_mcp.py` to use adaptive scoring
- [ ] Deploy to MCP server and HTTP facade

### Phase 7: OOD Testing (Week 6)
- [ ] Create OOD test sets:
  - [ ] **Adversarial**: Hand-crafted edge cases
    - "Prove [false scientific claim]"
    - Jailbreak attempts disguised as questions
    - Taxonomy submissions from users
  - [ ] **Domain Shift**: Categories not in MMLU
    - Creative writing prompts
    - Code generation tasks
    - Real-world user queries
  - [ ] **Temporal OOD**: New benchmarks (2024+)
    - SimpleQA (if available)
    - Latest MMLU updates
- [ ] Evaluate on each OOD set
- [ ] Analyze degradation vs. in-distribution performance

### Phase 8: Iteration & Documentation (Week 7)
- [ ] Analyze failures on OOD sets
- [ ] Add new heuristics for missed patterns
- [ ] Re-run nested CV with updated features
- [ ] Generate calibration plots (reliability diagrams)
- [ ] Write technical report:
  - [ ] Methodology (nested CV protocol)
  - [ ] Results (baseline vs. adaptive)
  - [ ] Ablation studies (each penalty component)
  - [ ] OOD generalization analysis
  - [ ] Failure mode documentation

---

## Expected Improvements

Based on OOD detection literature and nested CV best practices:

1. **Adaptive scoring** should improve AUROC by 5-15% on low-similarity cases
   - Baseline: ~0.75 AUROC (naive weighted average)
   - Target: ~0.85+ AUROC (adaptive with uncertainty)

2. **Nested CV** will give honest performance estimates
   - Simple train/test: Single point estimate (could be lucky/unlucky)
   - Nested CV: Mean ± std across 5 folds (robust estimate)

3. **Domain calibration** should reduce false positives by 10-20%
   - Expected: FPR@TPR95 drops from ~0.25 to ~0.15

4. **Multi-signal fusion** should catch edge cases like "prove false premise"
   - Combine vector similarity + rule-based heuristics
   - Expected: Improved recall on adversarial examples

5. **Calibration improvements**
   - Expected Calibration Error (ECE) < 0.05
   - Better alignment between predicted risk and actual difficulty

---

## Validation Checklist

Before deploying to production:
- ✓ Nested CV completed with no data leakage
- ✓ Hyperparameters tuned on inner CV folds only
- ✓ Generalization performance estimated on outer CV folds
- ✓ OOD sets tested (adversarial, domain-shift, temporal)
- ✓ Calibration error measured and within acceptable range (ECE < 0.1)
- ✓ Failure modes documented with specific examples
- ✓ Ablation studies show each component contributes positively
- ✓ Performance comparison: adaptive > baseline on all metrics
- ✓ Real-world testing with user queries from taxonomy submissions

---

## Key References

1. **Similarity Thresholds**: Cosine similarity 0.7-0.8 recommended as starting point for "relevant" matches; lower values increasingly unreliable
2. **OOD Metrics**: AUROC, FPR@TPR95 are standard; conformal prediction provides probabilistic guarantees
3. **Adaptive Methods**: Uncertainty-aware thresholds outperform fixed thresholds in retrieval tasks
4. **Holdout Validation**: 60-20-20 or 70-15-15 splits common; stratification by domain/difficulty essential
5. **Calibration**: Expected Calibration Error (ECE) measures if predicted probabilities match observed frequencies
6. **Nested CV**: Gold standard for hyperparameter tuning; prevents leakage from repeated validation peeking
7. **Stratified K-Fold**: Maintains class distribution across folds; essential for imbalanced datasets

---

## Quick Start: Immediate Implementation

### Step 1: Add Adaptive Scoring to `benchmark_vector_db.py` (Today)

Replace the naive weighted average in `query_similar_questions()` with adaptive uncertainty-aware scoring:

```python
def query_similar_questions(
    self,
    prompt: str,
    k: int = 5,
    domain_filter: Optional[str] = None,
    # NEW: Adaptive scoring parameters
    similarity_threshold: float = 0.7,
    low_sim_penalty: float = 0.5,
    variance_penalty: float = 2.0,
    low_avg_penalty: float = 0.4
) -> Dict[str, Any]:
    """Find k most similar benchmark questions with adaptive uncertainty penalties."""
    
    # ... existing code to query ChromaDB ...
    
    # Extract similarities and difficulty scores
    similarities = []
    difficulty_scores = []
    success_rates = []
    
    for i in range(len(results['ids'][0])):
        metadata = results['metadatas'][0][i]
        distance = results['distances'][0][i]
        
        # Convert L2 distance to cosine similarity
        similarity = max(0, 1 - (distance ** 2) / 2)
        
        similarities.append(similarity)
        difficulty_scores.append(metadata['difficulty_score'])
        success_rates.append(metadata['success_rate'])
    
    # IMPROVED: Adaptive uncertainty-aware scoring
    weighted_difficulty = self._compute_adaptive_difficulty(
        similarities=similarities,
        difficulty_scores=difficulty_scores,
        similarity_threshold=similarity_threshold,
        low_sim_penalty=low_sim_penalty,
        variance_penalty=variance_penalty,
        low_avg_penalty=low_avg_penalty
    )
    
    # ... rest of existing code ...

def _compute_adaptive_difficulty(
    self,
    similarities: List[float],
    difficulty_scores: List[float],
    similarity_threshold: float = 0.7,
    low_sim_penalty: float = 0.5,
    variance_penalty: float = 2.0,
    low_avg_penalty: float = 0.4
) -> float:
    """
    Compute difficulty score with adaptive uncertainty penalties.
    
    Key insight: When retrieved questions have low similarity to the prompt,
    we should INCREASE the risk estimate because we're extrapolating.
    
    Args:
        similarities: Cosine similarities of k-NN results
        difficulty_scores: Difficulty scores (1 - success_rate) of k-NN results
        similarity_threshold: Below this, apply low similarity penalty (default: 0.7)
        low_sim_penalty: Weight for low similarity penalty (default: 0.5)
        variance_penalty: Weight for high variance penalty (default: 2.0)
        low_avg_penalty: Weight for low average similarity penalty (default: 0.4)
    
    Returns:
        Adjusted difficulty score (0.0 to 1.0, higher = more risky)
    """
    import numpy as np
    
    # Base weighted average (original approach)
    weights = np.array(similarities) / sum(similarities)
    base_score = np.dot(weights, difficulty_scores)
    
    # Compute uncertainty indicators
    max_sim = max(similarities)
    avg_sim = np.mean(similarities)
    sim_variance = np.var(similarities)
    
    # Initialize uncertainty penalty
    uncertainty_penalty = 0.0
    
    # Penalty 1: Low maximum similarity
    # If best match is weak, we're likely OOD
    if max_sim < similarity_threshold:
        penalty = (similarity_threshold - max_sim) * low_sim_penalty
        uncertainty_penalty += penalty
        logger.debug(f"Low max similarity penalty: {penalty:.3f} (max_sim={max_sim:.3f})")
    
    # Penalty 2: High variance in similarities
    # If k-NN results are very dissimilar to each other, matches are unreliable
    variance_threshold = 0.05
    if sim_variance > variance_threshold:
        penalty = min(sim_variance * variance_penalty, 0.3)  # Cap at 0.3
        uncertainty_penalty += penalty
        logger.debug(f"High variance penalty: {penalty:.3f} (variance={sim_variance:.3f})")
    
    # Penalty 3: Low average similarity
    # If ALL matches are weak, we're definitely OOD
    avg_threshold = 0.5
    if avg_sim < avg_threshold:
        penalty = (avg_threshold - avg_sim) * low_avg_penalty
        uncertainty_penalty += penalty
        logger.debug(f"Low avg similarity penalty: {penalty:.3f} (avg_sim={avg_sim:.3f})")
    
    # Final adjusted score
    adjusted_score = base_score + uncertainty_penalty
    
    # Clip to [0, 1] range
    adjusted_score = np.clip(adjusted_score, 0.0, 1.0)
    
    logger.info(
        f"Adaptive scoring: base={base_score:.3f}, penalty={uncertainty_penalty:.3f}, "
        f"adjusted={adjusted_score:.3f}"
    )
    
    return adjusted_score
```

**Why this helps:**
- **"Prove universe is 10,000 years old" example**: max_sim=0.57 triggers low similarity penalty → risk increases from MODERATE to HIGH
- **Unrelated k-NN matches**: High variance → additional penalty → correctly flags as uncertain
- **Novel domains**: Low average similarity across all matches → strong penalty → CRITICAL risk

### Step 2: Export Database for Evaluation (This Week)

Add method to export all questions as DataFrame for nested CV:

```python
def get_all_questions_as_dataframe(self) -> 'pd.DataFrame':
    """
    Export all questions from ChromaDB as a pandas DataFrame.
    Used for train/val/test splitting and nested CV.
    
    Returns:
        DataFrame with columns:
        - question_id, source_benchmark, domain, question_text,
        - correct_answer, success_rate, difficulty_score, difficulty_label
    """
    import pandas as pd
    
    count = self.collection.count()
    logger.info(f"Exporting {count} questions from vector database...")
    
    # Get all questions from ChromaDB
    all_data = self.collection.get(
        limit=count,
        include=["metadatas", "documents"]
    )
    
    # Convert to DataFrame
    rows = []
    for i, qid in enumerate(all_data['ids']):
        metadata = all_data['metadatas'][i]
        rows.append({
            'question_id': qid,
            'question_text': all_data['documents'][i],
            'source_benchmark': metadata['source'],
            'domain': metadata['domain'],
            'success_rate': metadata['success_rate'],
            'difficulty_score': metadata['difficulty_score'],
            'difficulty_label': metadata['difficulty_label'],
            'num_models_tested': metadata.get('num_models', 0)
        })
    
    df = pd.DataFrame(rows)
    
    logger.info(f"Exported {len(df)} questions to DataFrame")
    logger.info(f"  Domains: {df['domain'].nunique()}")
    logger.info(f"  Sources: {df['source_benchmark'].nunique()}")
    
    return df
```

### Step 3: Test Adaptive Scoring Immediately

Create a test script to compare baseline vs. adaptive:

```python
#!/usr/bin/env python3
"""Test adaptive scoring improvements."""

from benchmark_vector_db import BenchmarkVectorDB
from pathlib import Path

# Initialize database
db = BenchmarkVectorDB(
    db_path=Path("/Users/hetalksinmaths/togmal/data/benchmark_vector_db")
)

# Test cases that should trigger uncertainty penalties
test_cases = [
    # Low similarity - should get penalty
    "Prove that the universe is exactly 10,000 years old using thermodynamics",
    
    # Novel domain - should get penalty
    "Write a haiku about quantum entanglement in 17th century Japanese",
    
    # Should match well - no penalty
    "What is the capital of France?",
    
    # Should match GPQA physics - no penalty
    "Calculate the quantum correction to the partition function for a 3D harmonic oscillator"
]

print("="*80)
print("Adaptive Scoring Test")
print("="*80)

for prompt in test_cases:
    print(f"\nPrompt: {prompt[:100]}...")
    
    result = db.query_similar_questions(prompt, k=5)
    
    print(f"  Max Similarity: {max(q['similarity'] for q in result['similar_questions']):.3f}")
    print(f"  Avg Similarity: {result['avg_similarity']:.3f}")
    print(f"  Weighted Difficulty: {result['weighted_difficulty_score']:.3f}")
    print(f"  Risk Level: {result['risk_level']}")
    print(f"  Top Match: {result['similar_questions'][0]['domain']} - {result['similar_questions'][0]['source']}")
```

---

## Next Steps

1. **Immediate**: Implement train/val/test split of benchmark data
2. **This week**: Add similarity-based uncertainty penalties
3. **Next week**: Run validation experiments with different thresholds
4. **End of month**: Complete evaluation on test set + OOD sets
5. **Ongoing**: Build adversarial test set from user submissions