# Failure Rate Prediction Improvement Plan
## Literature Review + Clever Experimental Designs

**Date:** 2025-11-19
**Goal:** Improve failure rate prediction accuracy from current MAE ~15-40% to <10%

---

## Executive Summary

**Current System Performance:**
- Validation MAE: ~15-40% (varies by question type)
- Lightweight Checker Recall: 32.9% (misses 67% of risky questions)
- Lightweight Checker Precision: 50.4%
- Uses: TF-IDF + LSA semantic similarity, top-k averaging

**Key Limitations Identified:**
1. ❌ Semantic similarity alone doesn't capture difficulty
2. ❌ No uncertainty quantification/calibration
3. ❌ Equal weighting of similar questions regardless of similarity score
4. ❌ No adaptive strategies based on confidence
5. ❌ Limited feature engineering beyond semantic similarity

---

## Literature Review: Key Findings (2024-2025)

### 🔬 1. Uncertainty Estimation & Calibration

**Key Papers:**
- "Revisiting Uncertainty Estimation and Calibration of Large Language Models" (2025)
- "A Survey of Uncertainty Estimation Methods on Large Language Models" (ACL 2025)
- "Bayesian Prompt Ensembles" (Amazon Science, 2024)

**Key Insights:**
- ✅ LLM confidence scores are generally **miscalibrated** without explicit calibration
- ✅ **Multi-generation consistency** improves uncertainty estimation
- ✅ **Bayesian ensemble methods** outperform single-model approaches
- ✅ **Conformal prediction** provides distribution-free uncertainty quantification

### 🔬 2. Test-Time Adaptive Compute

**Key Papers:**
- "Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters" (2024)
- "The LLM Already Knows: Estimating LLM-Perceived Question Difficulty" (2024)

**Key Insights:**
- ✅ Adaptive test-time compute allocation improves performance **4x** vs baseline
- ✅ Difficulty can be predicted from model-internal features
- ✅ Harder questions benefit from more sequential reasoning steps

### 🔬 3. Active Learning + Conformal Prediction

**Key Papers:**
- "CoPAL: Conformal Prediction in Active Learning" (COPA 2024)
- "CAP: Online Selective Conformal Prediction with FCR Control" (2024)

**Key Insights:**
- ✅ Conformal prediction + active learning reduces labeling by **60-70%**
- ✅ Uncertainty-based selection outperforms random sampling
- ✅ Calibration sets can be constructed adaptively

### 🔬 4. Meta-Learning & Curriculum Learning

**Key Papers:**
- "Meta-Learning Transformers to Improve In-Context Generalization" (2024)
- "Dual-Level Curriculum Meta-Learning for Noisy Few-Shot Learning" (AAAI 2024)

**Key Insights:**
- ✅ Support set size is a natural proxy for task difficulty
- ✅ Curriculum based on difficulty ordering improves generalization
- ✅ Transfer learning with similarity + difficulty balancing works well

### 🔬 5. Ensemble Methods

**Key Papers:**
- Survey on machine learning approaches for uncertainty quantification (2024)
- "Leveraging Bayesian deep learning and ensemble methods" (2024)

**Key Insights:**
- ✅ Deep ensembles improve both accuracy and calibration
- ✅ Ensemble diversity is critical for uncertainty quality
- ✅ Weighted ensembles outperform uniform averaging

---

## Proposed Experimental Designs

### 🧪 Experiment 1: Conformal Prediction with Adaptive Calibration Sets
**Hypothesis:** Conformal prediction will provide distribution-free uncertainty bounds

**Design:**
```python
class ConformalFailurePredictor:
    """
    Conformal prediction wrapper for failure rate estimation

    Key Innovation: Adaptive calibration set construction based on
    query similarity to avoid distribution shift
    """

    def __init__(self, base_predictor, calibration_data):
        self.base_predictor = base_predictor
        self.calibration_data = calibration_data

    def predict_with_interval(self, query, alpha=0.1):
        """
        Returns: (point_prediction, lower_bound, upper_bound)

        Method:
        1. Find k most similar calibration questions to query
        2. Compute prediction errors on calibration set
        3. Use quantile of errors to construct prediction interval
        4. Adjust interval width based on local difficulty variance
        """

        # Find similar calibration questions
        similar_cal = self._find_similar_calibration(query, k=50)

        # Get base prediction
        point_pred = self.base_predictor.predict(query)

        # Compute calibration errors
        errors = []
        for cal_q in similar_cal:
            pred = self.base_predictor.predict(cal_q['text'])
            actual = cal_q['actual_failure_rate']
            errors.append(abs(pred - actual))

        # Conformal interval
        quantile = np.quantile(errors, 1 - alpha)

        # INNOVATION: Adjust interval based on local variance
        local_variance = np.var([q['actual_failure_rate']
                                for q in similar_cal])
        adjustment = np.sqrt(local_variance)

        lower = max(0, point_pred - quantile - adjustment)
        upper = min(100, point_pred + quantile + adjustment)

        return point_pred, lower, upper, quantile
```

**Expected Improvement:**
- Valid coverage guarantees (90% intervals will contain true value 90% of time)
- Better calibration than current point estimates
- Adaptive to local difficulty distribution

**Evaluation Metrics:**
- Coverage rate (should match 1-alpha)
- Interval width (narrower is better, given valid coverage)
- Conditional coverage by domain/difficulty

---

### 🧪 Experiment 2: Weighted Ensemble with Uncertainty Decomposition
**Hypothesis:** Decomposing uncertainty into aleatoric (irreducible) and epistemic (model) components will improve predictions

**Design:**
```python
class UncertaintyDecomposedEnsemble:
    """
    Ensemble of failure predictors with uncertainty decomposition

    Key Innovation: Separate aleatoric (data noise) from epistemic
    (model uncertainty) to know when to gather more data vs improve model
    """

    def __init__(self, base_models, similarity_scorer):
        self.models = base_models  # List of different predictors
        self.scorer = similarity_scorer

    def predict_with_uncertainty(self, query, top_k=20):
        """
        Returns failure rate + aleatoric + epistemic uncertainty
        """

        # Get predictions from each model
        predictions = []
        for model in self.models:
            pred = model.predict_failure_rate(query, top_k=top_k)
            predictions.append(pred['aggregated_prediction']['overall_failure_rate'])

        # Ensemble mean (point prediction)
        mean_pred = np.mean(predictions)

        # EPISTEMIC UNCERTAINTY: Variance across models
        # (reducible by improving models or getting more data)
        epistemic = np.var(predictions)

        # ALEATORIC UNCERTAINTY: Average variance within each model
        # (irreducible data noise)
        aleatoric_estimates = []
        for model in self.models:
            similar_qs = self.scorer.search(query, top_k=top_k)
            # Variance in ground truth for similar questions
            failure_rates = [self._get_actual_failure_rate(q)
                           for q in similar_qs]
            aleatoric_estimates.append(np.var(failure_rates))

        aleatoric = np.mean(aleatoric_estimates)

        # Total uncertainty
        total_uncertainty = epistemic + aleatoric

        return {
            'prediction': mean_pred,
            'epistemic_uncertainty': epistemic,
            'aleatoric_uncertainty': aleatoric,
            'total_uncertainty': total_uncertainty,
            'confidence': 1.0 / (1.0 + total_uncertainty),
            'recommendation': self._uncertainty_recommendation(
                epistemic, aleatoric
            )
        }

    def _uncertainty_recommendation(self, epistemic, aleatoric):
        """
        Actionable recommendations based on uncertainty type
        """
        if epistemic > aleatoric * 2:
            return "HIGH_MODEL_UNCERTAINTY: Models disagree. Consider gathering more benchmark data in this domain."
        elif aleatoric > epistemic * 2:
            return "HIGH_DATA_NOISE: Similar questions have variable outcomes. This is inherently difficult - use caution."
        else:
            return "BALANCED_UNCERTAINTY: Standard prediction confidence applies."
```

**Ensemble Diversity Strategies:**
1. **Different similarity metrics:** BM25, TF-IDF+LSA, future sentence-transformers
2. **Different aggregation methods:** Mean, weighted by similarity, kernel-weighted
3. **Different top-k values:** k=5, k=10, k=20, k=50
4. **Different domain boosts:** 0.0, 0.2, 0.5

**Expected Improvement:**
- Epistemic uncertainty tells us when to gather more data
- Aleatoric uncertainty tells us when questions are inherently variable
- Better risk communication to users

**Evaluation:**
- Correlation between uncertainty and prediction error
- Stratify MAE by uncertainty level (high uncertainty should have higher MAE)
- Decision-making improvements (reject high-uncertainty predictions)

---

### 🧪 Experiment 3: Meta-Learned Difficulty Features
**Hypothesis:** Combining semantic similarity with learned difficulty features will outperform semantic alone

**Design:**
```python
class MetaLearnedDifficultyPredictor:
    """
    Two-stage predictor:
    1. Learn difficulty features from similar questions
    2. Use features + similarity for weighted aggregation

    Key Innovation: Automatically discover which question features
    correlate with difficulty beyond just semantic content
    """

    def __init__(self, questions_db, performance_db):
        self.questions_db = questions_db
        self.performance_db = performance_db

        # Extract meta-features from questions
        self.feature_extractor = DifficultyFeatureExtractor()

        # Train meta-learner
        self.meta_model = self._train_meta_learner()

    def _extract_features(self, question):
        """
        Extract difficulty-predictive features

        Features inspired by literature + domain knowledge:
        """
        features = {}

        # Length-based features
        features['question_length'] = len(question['question_text'].split())
        features['avg_word_length'] = np.mean([len(w) for w in
                                               question['question_text'].split()])

        # Complexity features
        features['num_numbers'] = len(re.findall(r'\d+', question['question_text']))
        features['num_equations'] = len(re.findall(r'[=<>]', question['question_text']))
        features['has_proof_words'] = int(any(w in question['question_text'].lower()
                                             for w in ['prove', 'show that', 'demonstrate']))

        # Syntactic features
        features['num_clauses'] = question['question_text'].count(',') + question['question_text'].count(';')
        features['num_questions'] = question['question_text'].count('?')

        # Semantic features (from literature)
        features['abstractness'] = self._compute_abstractness(question['question_text'])
        features['technical_density'] = self._count_technical_terms(question['question_text'])

        # Domain-specific
        features[f'domain_{question["domain"]}'] = 1  # One-hot encoding

        # Answer choice complexity (if available)
        if 'options' in question:
            features['avg_option_length'] = np.mean([len(opt) for opt in question['options']])
            features['num_options'] = len(question['options'])

        return features

    def _train_meta_learner(self):
        """
        Train a meta-model to predict failure rate from features

        Training approach: Curriculum learning (easy to hard)
        """
        from sklearn.ensemble import GradientBoostingRegressor

        # Extract features and labels
        X, y = [], []
        for qid, perf in self.performance_db.items():
            question = self._get_question(qid)
            features = self._extract_features(question)

            # Label: actual failure rate
            failure_rate = self._compute_actual_failure_rate(perf)

            X.append(list(features.values()))
            y.append(failure_rate)

        X = np.array(X)
        y = np.array(y)

        # CURRICULUM LEARNING: Train on easy examples first
        difficulties = y.copy()
        sorted_indices = np.argsort(difficulties)  # Easy to hard

        model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8
        )

        # Progressive training
        for split in [0.3, 0.6, 1.0]:
            n_samples = int(len(sorted_indices) * split)
            indices = sorted_indices[:n_samples]
            model.fit(X[indices], y[indices])

        return model

    def predict_failure_rate(self, query, top_k=20):
        """
        Hybrid prediction: meta-features + semantic similarity
        """
        # Extract query features
        query_features = self._extract_features({'question_text': query})

        # Meta-model prediction (feature-based)
        meta_pred = self.meta_model.predict([list(query_features.values())])[0]

        # Semantic similarity prediction (current approach)
        similar_qs = self.scorer.search(query, top_k=top_k)

        # WEIGHTED AGGREGATION based on feature similarity
        weighted_sum = 0
        weight_sum = 0

        for sim_q in similar_qs:
            # Semantic weight
            semantic_weight = sim_q['score']

            # Feature similarity weight
            sim_features = self._extract_features(sim_q['question'])
            feature_distance = self._feature_distance(query_features, sim_features)
            feature_weight = np.exp(-feature_distance)

            # Combined weight
            combined_weight = semantic_weight * feature_weight

            # Actual failure rate
            actual_fr = self._get_actual_failure_rate(sim_q['question_id'])

            weighted_sum += combined_weight * actual_fr
            weight_sum += combined_weight

        semantic_pred = weighted_sum / weight_sum if weight_sum > 0 else meta_pred

        # ENSEMBLE: Combine meta-model and semantic predictions
        # Weight by confidence in each approach
        meta_confidence = self._estimate_meta_confidence(query_features)
        semantic_confidence = weight_sum / top_k  # Coverage as confidence

        final_pred = (meta_confidence * meta_pred +
                     semantic_confidence * semantic_pred) / (meta_confidence + semantic_confidence)

        return {
            'prediction': final_pred,
            'meta_prediction': meta_pred,
            'semantic_prediction': semantic_pred,
            'meta_confidence': meta_confidence,
            'semantic_confidence': semantic_confidence,
            'feature_importance': self.meta_model.feature_importances_
        }
```

**Expected Improvement:**
- Capture difficulty patterns beyond semantic similarity
- Reduce MAE by 30-50% (based on similar meta-learning papers)
- Interpretable feature importance

**Evaluation:**
- MAE on held-out test set
- Ablation study: semantic only vs features only vs hybrid
- Feature importance analysis

---

### 🧪 Experiment 4: Active Learning for Strategic Data Collection
**Hypothesis:** Strategically selecting which questions to evaluate next will improve prediction faster than random evaluation

**Design:**
```python
class ActiveLearningFailurePredictor:
    """
    Actively select which questions to evaluate next based on:
    1. High uncertainty regions
    2. High impact regions (frequently queried)
    3. Diverse coverage

    Key Innovation: Maximize information gain per evaluation
    """

    def __init__(self, predictor, question_pool, budget=100):
        self.predictor = predictor
        self.question_pool = question_pool
        self.budget = budget
        self.evaluated = []
        self.unevaluated = list(question_pool)

    def select_next_batch(self, batch_size=10):
        """
        Select next batch of questions to evaluate

        Selection criteria (from literature):
        1. Uncertainty sampling (conformal interval width)
        2. Query density (how often similar questions are asked)
        3. Diversity (maximize coverage of feature space)
        """

        scores = []
        for q in self.unevaluated:
            # 1. Uncertainty score
            pred, lower, upper, _ = self.predictor.predict_with_interval(q['text'])
            uncertainty_score = upper - lower

            # 2. Query density (how "important" is this region)
            density_score = self._estimate_query_density(q)

            # 3. Diversity score (distance to evaluated questions)
            diversity_score = self._compute_diversity(q, self.evaluated)

            # Combined acquisition function
            total_score = (0.5 * uncertainty_score +
                          0.3 * density_score +
                          0.2 * diversity_score)

            scores.append((q, total_score))

        # Select top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        selected = [q for q, score in scores[:batch_size]]

        return selected

    def _estimate_query_density(self, question):
        """
        Estimate how often similar questions are queried

        Can use:
        - Historical query logs
        - Domain popularity
        - Benchmark coverage
        """
        # Placeholder: Use domain frequency as proxy
        domain_counts = {}
        for q in self.question_pool:
            domain_counts[q['domain']] = domain_counts.get(q['domain'], 0) + 1

        return domain_counts.get(question['domain'], 0) / len(self.question_pool)

    def _compute_diversity(self, question, evaluated_set):
        """
        How different is this question from already evaluated ones?
        """
        if not evaluated_set:
            return 1.0

        # Compute minimum distance to evaluated questions
        distances = []
        for eval_q in evaluated_set:
            # Feature-space distance
            dist = self._feature_distance(
                self._extract_features(question),
                self._extract_features(eval_q)
            )
            distances.append(dist)

        return min(distances)  # Most similar to closest evaluated question
```

**Experimental Protocol:**
1. Start with 100 randomly evaluated questions (current state)
2. Use active learning to select next 100 questions to evaluate
3. Compare:
   - **Random selection:** Randomly pick 100 more questions
   - **Active learning:** Use uncertainty + density + diversity
4. Measure: MAE reduction per evaluation

**Expected Improvement:**
- 2-3x faster MAE reduction compared to random evaluation
- Better coverage of high-uncertainty regions
- More efficient use of evaluation budget

**Evaluation Metrics:**
- Learning curve: MAE vs number of evaluations
- Coverage: % of feature space covered
- ROI: MAE reduction per evaluation

---

### 🧪 Experiment 5: Adaptive Test-Time Strategies
**Hypothesis:** Different prediction strategies should be used based on query characteristics

**Design:**
```python
class AdaptiveFailurePredictor:
    """
    Route queries to different prediction strategies based on characteristics

    Inspired by: "Scaling LLM Test-Time Compute Optimally" (2024)

    Key Innovation: Allocate computational budget adaptively
    """

    def __init__(self, predictors_suite):
        # Suite of predictors with different speed/accuracy tradeoffs
        self.fast_predictor = predictors_suite['fast']      # Lightweight checker
        self.medium_predictor = predictors_suite['medium']  # Semantic similarity
        self.slow_predictor = predictors_suite['slow']      # Meta-learned + ensemble

        # Router: Decide which predictor to use
        self.router = self._train_router()

    def _train_router(self):
        """
        Train a routing model to decide which predictor to use

        Training data: (query_features, optimal_predictor)
        where optimal_predictor minimizes error for that query type
        """
        from sklearn.tree import DecisionTreeClassifier

        X, y = [], []
        for q in self.training_questions:
            features = self._extract_router_features(q)

            # Which predictor was most accurate for this question?
            fast_error = abs(self.fast_predictor.predict(q) - q['actual'])
            medium_error = abs(self.medium_predictor.predict(q) - q['actual'])
            slow_error = abs(self.slow_predictor.predict(q) - q['actual'])

            optimal = np.argmin([fast_error, medium_error, slow_error])

            X.append(features)
            y.append(optimal)

        router = DecisionTreeClassifier(max_depth=5)
        router.fit(X, y)

        return router

    def _extract_router_features(self, query):
        """
        Fast features to decide routing (must be cheap to compute)
        """
        return [
            len(query.split()),  # Length
            query.count('?'),    # Number of questions
            int('prove' in query.lower() or 'show that' in query.lower()),
            sum(c.isdigit() for c in query),  # Number of digits
            # ... more fast features
        ]

    def predict(self, query):
        """
        Adaptively route to appropriate predictor
        """
        router_features = self._extract_router_features(query)
        predictor_choice = self.router.predict([router_features])[0]

        if predictor_choice == 0:
            # Fast path
            result = self.fast_predictor.predict(query)
            result['strategy'] = 'fast_lightweight'
            result['compute_cost'] = 'low'

        elif predictor_choice == 1:
            # Medium path
            result = self.medium_predictor.predict(query)
            result['strategy'] = 'semantic_similarity'
            result['compute_cost'] = 'medium'

        else:
            # Slow but accurate path
            result = self.slow_predictor.predict(query)
            result['strategy'] = 'meta_learned_ensemble'
            result['compute_cost'] = 'high'

        return result
```

**Expected Improvement:**
- Average latency reduction of 40-60% (use fast predictor when sufficient)
- Maintain or improve accuracy (use slow predictor when needed)
- Better resource utilization

**Evaluation:**
- Accuracy vs compute budget tradeoff curve
- Routing accuracy (how often does router choose optimal predictor?)
- Latency distribution

---

### 🧪 Experiment 6: Temperature-Scaled Calibration
**Hypothesis:** Post-hoc calibration can improve confidence estimates without retraining

**Design:**
```python
class TemperatureScaledPredictor:
    """
    Apply temperature scaling to calibrate predictions

    From: "On Calibration of Modern Neural Networks" (Guo et al.)

    Key Innovation: Single parameter (temperature T) rescales predictions
    to match empirical accuracy
    """

    def __init__(self, base_predictor, calibration_set):
        self.base_predictor = base_predictor
        self.temperature = self._learn_temperature(calibration_set)

    def _learn_temperature(self, cal_set):
        """
        Learn optimal temperature to minimize calibration error

        Calibration error: How well do predicted probabilities match
        actual frequencies?
        """
        from scipy.optimize import minimize

        def calibration_error(T):
            # Get predictions on calibration set
            preds = []
            actuals = []

            for q in cal_set:
                pred = self.base_predictor.predict(q['text'])

                # Convert failure rate to "probability of failure"
                prob_failure = pred / 100.0

                # Apply temperature scaling
                # (for regression, we bin predictions)
                calibrated_prob = self._apply_temperature(prob_failure, T)

                preds.append(calibrated_prob)
                actuals.append(q['actual_failure_rate'] / 100.0)

            # Compute Expected Calibration Error (ECE)
            ece = self._compute_ece(preds, actuals, n_bins=10)
            return ece

        # Optimize temperature
        result = minimize(calibration_error, x0=1.0, bounds=[(0.1, 10.0)])
        return result.x[0]

    def _compute_ece(self, predictions, actuals, n_bins=10):
        """
        Expected Calibration Error:

        For each bin of predictions, compute:
        |average_prediction - average_actual|

        Weight by bin frequency
        """
        predictions = np.array(predictions)
        actuals = np.array(actuals)

        # Bin predictions
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]

        ece = 0.0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            # Find predictions in this bin
            in_bin = (predictions >= bin_lower) & (predictions < bin_upper)

            if np.sum(in_bin) > 0:
                # Average predicted confidence in bin
                avg_pred = np.mean(predictions[in_bin])

                # Average actual failure rate in bin
                avg_actual = np.mean(actuals[in_bin])

                # Bin weight
                bin_weight = np.sum(in_bin) / len(predictions)

                # Add to ECE
                ece += bin_weight * abs(avg_pred - avg_actual)

        return ece

    def predict_calibrated(self, query):
        """
        Return temperature-scaled prediction
        """
        pred = self.base_predictor.predict(query)

        # Apply temperature scaling
        failure_rate = pred['aggregated_prediction']['overall_failure_rate']
        prob_failure = failure_rate / 100.0

        calibrated_prob = self._apply_temperature(prob_failure, self.temperature)
        calibrated_failure_rate = calibrated_prob * 100.0

        pred['calibrated_failure_rate'] = calibrated_failure_rate
        pred['temperature'] = self.temperature
        pred['calibration_info'] = {
            'uncalibrated': failure_rate,
            'calibrated': calibrated_failure_rate,
            'temperature': self.temperature
        }

        return pred
```

**Expected Improvement:**
- Better calibration (ECE reduction of 30-50%)
- No retraining required
- Predictions match empirical frequencies

**Evaluation:**
- Expected Calibration Error (ECE)
- Reliability diagrams (predicted vs actual failure rates)
- Brier score

---

## Recommended Implementation Roadmap

### Phase 1: Quick Wins (1-2 weeks)
1. ✅ **Temperature-Scaled Calibration** (Experiment 6)
   - Minimal code changes
   - Immediate calibration improvement
   - Baseline for other experiments

2. ✅ **Weighted Semantic Similarity** (part of Experiment 3)
   - Weight similar questions by similarity score (not equal weight)
   - Add feature-based similarity
   - Expected: 15-25% MAE reduction

### Phase 2: Medium-Term Improvements (2-4 weeks)
3. ✅ **Meta-Learned Difficulty Features** (Experiment 3)
   - Extract features, train meta-learner
   - Hybrid semantic + feature prediction
   - Expected: 30-50% MAE reduction

4. ✅ **Uncertainty Decomposition** (Experiment 2)
   - Build ensemble
   - Decompose uncertainty
   - Better user guidance

### Phase 3: Advanced Techniques (4-8 weeks)
5. ✅ **Conformal Prediction** (Experiment 1)
   - Implement adaptive calibration sets
   - Provide prediction intervals
   - Valid coverage guarantees

6. ✅ **Active Learning** (Experiment 4)
   - Strategic evaluation selection
   - Maximize learning efficiency
   - Reduce evaluation costs

7. ✅ **Adaptive Routing** (Experiment 5)
   - Route queries to appropriate predictors
   - Optimize speed/accuracy tradeoff
   - Better resource utilization

---

## Expected Overall Improvement

**Conservative Estimates:**
| Metric | Current | Phase 1 | Phase 2 | Phase 3 | Improvement |
|--------|---------|---------|---------|---------|-------------|
| MAE | 20-30% | 15-25% | 10-15% | 8-12% | **60-70% reduction** |
| Recall | 32.9% | 45-50% | 55-65% | 65-75% | **2-2.3x improvement** |
| Calibration (ECE) | ~0.15 | ~0.08 | ~0.05 | ~0.03 | **80% reduction** |

**Optimistic Estimates (if all experiments succeed):**
- MAE: **5-8%** (vs current 20-30%)
- Recall: **75-85%** (vs current 32.9%)
- Calibration: **ECE < 0.02**

---

## Key Metrics to Track

### Prediction Accuracy
- ✅ Mean Absolute Error (MAE)
- ✅ Root Mean Squared Error (RMSE)
- ✅ R² correlation
- ✅ Stratified MAE (by domain, difficulty)

### Calibration
- ✅ Expected Calibration Error (ECE)
- ✅ Reliability diagrams
- ✅ Brier score
- ✅ Coverage of prediction intervals

### Detection Performance
- ✅ Recall (% of risky questions caught)
- ✅ Precision (% of flagged questions actually risky)
- ✅ F1 score
- ✅ AUROC, AUPRC

### Efficiency
- ✅ Average prediction latency
- ✅ Compute cost per prediction
- ✅ Learning curve (accuracy vs evaluations)

---

## Literature-Inspired Best Practices

### 1. Cross-Domain Validation
**From:** Meta-learning literature

**Practice:** Test on held-out *domains*, not just held-out questions
- Train on: Math, Physics, Chemistry
- Test on: Biology, Engineering (entirely new domains)
- Measures: True generalization, not just memorization

### 2. Stratified Evaluation
**From:** Fairness in ML

**Practice:** Report metrics separately for:
- Each domain
- Each difficulty level
- Each question type
- Ensure no systematic biases

### 3. Ablation Studies
**From:** Deep learning best practices

**Practice:** For each improvement, measure:
- Full model performance
- Performance without that component
- Shows: Actual contribution of each part

### 4. Human-in-the-Loop Validation
**From:** Medical ML

**Practice:** For high-stakes predictions:
- Flag disagreement between ensemble members
- Request human review when uncertainty is high
- Learn from human corrections

---

## Open Research Questions

1. **Can we predict *why* a question fails?**
   - Current: Predict failure *rate*
   - Better: Predict failure *mode* (reasoning error? knowledge gap? calculation error?)

2. **Can we use LLM-internal features for prediction?**
   - Token logits, attention patterns, hidden states
   - May reveal difficulty better than text features

3. **Can we do zero-shot difficulty prediction?**
   - For questions with no similar benchmarks
   - Use LLM to generate synthetic similar questions?

4. **Can we learn from LLM mistakes?**
   - Analyze *incorrect* LLM answers to find patterns
   - Build taxonomy of failure modes

---

## Conclusion

The current failure rate prediction system is solid but has significant room for improvement. By incorporating:

1. ✅ **Uncertainty quantification** (conformal prediction, ensembles)
2. ✅ **Meta-learned features** (beyond semantic similarity)
3. ✅ **Active learning** (strategic data collection)
4. ✅ **Adaptive strategies** (route based on query characteristics)
5. ✅ **Calibration** (temperature scaling, reliability)

We can improve prediction accuracy by **60-70%** (MAE 20-30% → 8-12%) while also providing:
- Valid uncertainty bounds
- Interpretable failure predictions
- Efficient resource utilization
- Better user guidance

The roadmap is structured to deliver quick wins first (Phase 1) while building toward more advanced techniques (Phases 2-3).

**Next Step:** Implement Phase 1 (Temperature Scaling + Weighted Similarity) to establish baseline improvements before tackling more complex techniques.
