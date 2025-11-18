# Validation Framework: Ensuring Taxonomy is Grounded in Reality

## The Grounding Problem

**Risk**: We create categories that sound reasonable but don't actually:
1. Reliably distinguish between different failure modes
2. Predict model behavior on new questions
3. Guide effective interventions
4. Generalize across models/domains

**Solution**: Multi-faceted validation approach with measurable metrics.

---

## Validation Strategy

### Phase 1: Internal Consistency (Weeks 1-2)

#### 1.1 Inter-Rater Reliability

**Goal**: Multiple human annotators should agree on error classifications.

```python
def compute_inter_rater_reliability(annotations: List[List[ErrorSubtype]]) -> Dict:
    """
    Compute Cohen's Kappa or Fleiss' Kappa for multi-rater agreement.

    Target: Kappa > 0.7 (substantial agreement)
    If Kappa < 0.6: taxonomy definitions need refinement
    """
    from sklearn.metrics import cohen_kappa_score

    # Get 100 errors annotated by 3 human experts
    # Compare their classifications

    kappa_scores = []
    for i in range(len(annotations)):
        for j in range(i+1, len(annotations)):
            kappa = cohen_kappa_score(annotations[i], annotations[j])
            kappa_scores.append(kappa)

    return {
        'mean_kappa': np.mean(kappa_scores),
        'interpretation': 'substantial' if np.mean(kappa_scores) > 0.7 else 'needs_work',
        'problematic_categories': find_low_agreement_categories(annotations)
    }
```

**Action Items**:
- [ ] Recruit 3 domain experts (CS/AI researchers)
- [ ] Have each annotate 100 random errors
- [ ] Compute Kappa scores per category
- [ ] Refine categories with low agreement (<0.6)
- [ ] Iterate until Kappa > 0.7

**Grounding Evidence**: If experts can't agree, category isn't well-defined.

---

#### 1.2 LLM-Assisted Classification Validation

**Goal**: Use strong LLM (GPT-4, Claude) to classify errors, compare to rule-based.

```python
def validate_with_llm_classifier(errors: List[ErrorRecord]) -> Dict:
    """
    Use GPT-4/Claude to independently classify errors.
    Compare agreement with rule-based classifier.

    Target: Agreement > 75%
    Disagreements highlight edge cases or unclear categories
    """
    llm_classifications = []
    rule_based_classifications = []

    for error in errors:
        # Rule-based
        rule_class = ErrorDetector.classify_error(error)

        # LLM-based
        prompt = f"""
        Classify this LLM error:
        Question: {error.question_text}
        Correct: {error.correct_answer}
        Model chose: {error.model_answer}

        Which error type?
        {list_error_subtypes_with_descriptions()}
        """
        llm_class = await claude.classify(prompt)

        llm_classifications.append(llm_class)
        rule_based_classifications.append(rule_class)

    agreement = sum(l == r for l, r in zip(llm_classifications, rule_based_classifications))

    return {
        'agreement_rate': agreement / len(errors),
        'disagreements': find_disagreements(llm_classifications, rule_based_classifications),
        'llm_confidence': compute_confidence_scores(llm_classifications)
    }
```

**Action Items**:
- [ ] Classify 200 errors with both methods
- [ ] Analyze disagreements (where and why?)
- [ ] Use disagreements to improve rule-based detection
- [ ] Achieve >75% agreement

**Grounding Evidence**: If sophisticated LLM disagrees, our rules may be too simplistic.

---

#### 1.3 Within-Cluster Coherence

**Goal**: Errors within same cluster should be semantically similar.

```python
def measure_cluster_coherence(clusters: List[ErrorCluster]) -> Dict:
    """
    Measure if clusters are internally coherent.

    Metrics:
    - Silhouette score: How well-separated are clusters?
    - Intra-cluster similarity: Are items within cluster similar?
    - Inter-cluster distance: Are clusters distinct?

    Target: Silhouette > 0.4, Intra-similarity > 0.6
    """
    from sklearn.metrics import silhouette_score

    embeddings = np.array([e.question_embedding for e in all_errors])
    labels = np.array([e.cluster_id for e in all_errors])

    silhouette = silhouette_score(embeddings, labels)

    # Compute intra-cluster similarity
    coherence_scores = []
    for cluster in clusters:
        cluster_embeddings = [e.question_embedding for e in cluster.error_records]
        # Average pairwise cosine similarity
        similarities = compute_pairwise_cosine(cluster_embeddings)
        coherence_scores.append(np.mean(similarities))

    return {
        'silhouette_score': silhouette,
        'avg_intra_cluster_similarity': np.mean(coherence_scores),
        'interpretation': 'good' if silhouette > 0.4 else 'needs_refinement'
    }
```

**Action Items**:
- [ ] Measure cluster coherence metrics
- [ ] If silhouette < 0.3: clusters are arbitrary, refine algorithm
- [ ] Inspect low-coherence clusters manually
- [ ] Adjust min_cluster_size or similarity threshold

**Grounding Evidence**: If cluster members aren't similar, they're not a real pattern.

---

### Phase 2: Predictive Validity (Weeks 3-4)

#### 2.1 Error Prediction Accuracy

**Goal**: Taxonomy should predict which questions models will fail.

```python
def test_predictive_power(train_errors: List[ErrorRecord],
                         test_questions: List[Question]) -> Dict:
    """
    Train: Use known errors to build profiles
    Test: Predict which test questions will cause errors

    Approach:
    1. For each error type, get average embedding
    2. For test question, find K nearest error embeddings
    3. If avg similarity > threshold, predict error

    Target: AUROC > 0.65 (better than random)
    """
    from sklearn.metrics import roc_auc_score, precision_recall_curve

    # Build error type centroids
    error_centroids = {}
    for subtype in ErrorSubtype:
        subtype_errors = [e for e in train_errors if e.error_subtype == subtype]
        if len(subtype_errors) > 0:
            embeddings = np.array([e.question_embedding for e in subtype_errors])
            error_centroids[subtype] = np.mean(embeddings, axis=0)

    # Predict on test questions
    predictions = []
    ground_truth = []  # Whether model actually failed

    for question in test_questions:
        q_embedding = embed(question.text)

        # Distance to nearest error centroid
        min_distance = min(
            cosine_distance(q_embedding, centroid)
            for centroid in error_centroids.values()
        )

        # Convert distance to probability
        prob_error = 1 / (1 + np.exp(5 * (min_distance - 0.7)))

        predictions.append(prob_error)
        ground_truth.append(question.model_failed)

    auroc = roc_auc_score(ground_truth, predictions)

    return {
        'auroc': auroc,
        'interpretation': (
            'strong' if auroc > 0.75 else
            'moderate' if auroc > 0.65 else
            'weak'
        ),
        'baseline_random': 0.5
    }
```

**Action Items**:
- [ ] Hold out 20% of questions as test set
- [ ] Build error profiles from 80% training set
- [ ] Predict errors on test set
- [ ] Target: AUROC > 0.65 (significantly better than random)
- [ ] If AUROC < 0.55: taxonomy doesn't capture real patterns

**Grounding Evidence**: If we can't predict future errors, taxonomy is just post-hoc labeling.

---

#### 2.2 Cross-Model Transfer

**Goal**: Error patterns learned from Model A should transfer to Model B.

```python
def test_cross_model_transfer(model_a_errors: List[ErrorRecord],
                               model_b_errors: List[ErrorRecord]) -> Dict:
    """
    Learn error patterns from Model A.
    Predict Model B's errors on same questions.

    If patterns transfer: they're about question difficulty, not model quirks
    If no transfer: patterns are model-specific

    Target: Transfer accuracy > 60%
    """
    # Find questions both models attempted
    shared_questions = set(e.question_id for e in model_a_errors) & \
                      set(e.question_id for e in model_b_errors)

    # Build Model A error profile
    model_a_error_types = {
        e.question_id: e.error_subtype
        for e in model_a_errors
    }

    # Predict Model B errors based on Model A patterns
    correct_predictions = 0
    total = 0

    for qid in shared_questions:
        # If Model A failed with error type X on this question
        # Predict Model B will also fail with similar error type

        predicted_type = model_a_error_types.get(qid)
        actual_b_error = next(e for e in model_b_errors if e.question_id == qid)

        if predicted_type == actual_b_error.error_subtype:
            correct_predictions += 1
        total += 1

    return {
        'transfer_accuracy': correct_predictions / total,
        'shared_questions': len(shared_questions),
        'interpretation': (
            'strong_transfer' if correct_predictions / total > 0.6 else
            'weak_transfer'
        )
    }
```

**Action Items**:
- [ ] Test transfer between Llama-70B and Qwen-72B
- [ ] Test transfer between GPT-4 and Claude
- [ ] If transfer accuracy > 60%: patterns are universal
- [ ] If accuracy < 40%: patterns are model-specific (refine taxonomy)

**Grounding Evidence**: Universal patterns are more fundamental than model-specific quirks.

---

#### 2.3 Difficulty Calibration

**Goal**: Error-prone questions should actually be harder (validated by human experts).

```python
def validate_difficulty_calibration(errors: List[ErrorRecord],
                                    human_ratings: Dict[str, float]) -> Dict:
    """
    Correlate model errors with human-rated difficulty.

    Get 50 domain experts to rate subset of questions:
    - Easy (answer immediately)
    - Medium (need to think)
    - Hard (need to look up / calculate)
    - Expert (requires specialized knowledge)

    Target: Spearman correlation > 0.5
    """
    from scipy.stats import spearmanr

    # For each question, get:
    # - Number of models that failed (proxy for difficulty)
    # - Human expert rating

    question_error_rates = {}
    for error in errors:
        qid = error.question_id
        question_error_rates[qid] = question_error_rates.get(qid, 0) + 1

    model_difficulty = []
    human_difficulty = []

    for qid in human_ratings.keys():
        if qid in question_error_rates:
            model_difficulty.append(question_error_rates[qid])
            human_difficulty.append(human_ratings[qid])

    correlation, p_value = spearmanr(model_difficulty, human_difficulty)

    return {
        'correlation': correlation,
        'p_value': p_value,
        'interpretation': (
            'strong' if correlation > 0.6 else
            'moderate' if correlation > 0.4 else
            'weak'
        )
    }
```

**Action Items**:
- [ ] Get 50 experts to rate 100 random questions
- [ ] Compute correlation with model error rates
- [ ] Target: Spearman r > 0.5, p < 0.01
- [ ] If correlation < 0.3: models failing on "easy" questions (investigate)

**Grounding Evidence**: If humans and models disagree on difficulty, something's wrong.

---

### Phase 3: Intervention Validity (Weeks 5-8)

#### 3.1 A/B Testing Interventions

**Goal**: Recommended interventions should actually improve performance.

```python
def test_intervention_efficacy(error_type: ErrorSubtype,
                               intervention: str,
                               test_set: List[Question]) -> Dict:
    """
    For a specific error type, test if intervention works.

    Example:
    Error: Multi-step reasoning failures
    Intervention: Chain-of-thought prompting

    Test: Run with/without CoT, measure improvement

    Target: >15% error reduction for recommended interventions
    """
    # Identify questions that cause this error type
    error_prone_questions = [
        q for q in test_set
        if historical_error_type(q.id) == error_type
    ]

    # Run without intervention (baseline)
    baseline_errors = 0
    for q in error_prone_questions:
        response = model.generate(q.text, prompt_type='standard')
        if response != q.correct_answer:
            baseline_errors += 1

    # Run with intervention
    intervention_errors = 0
    for q in error_prone_questions:
        if intervention == 'chain_of_thought':
            response = model.generate(
                q.text,
                prompt_type='cot',
                instruction="Let's solve this step by step"
            )
        elif intervention == 'rag':
            context = retrieve_context(q.text)
            response = model.generate(f"Context: {context}\n\nQuestion: {q.text}")

        if response != q.correct_answer:
            intervention_errors += 1

    improvement = (baseline_errors - intervention_errors) / baseline_errors

    return {
        'baseline_error_rate': baseline_errors / len(error_prone_questions),
        'intervention_error_rate': intervention_errors / len(error_prone_questions),
        'relative_improvement': improvement,
        'is_effective': improvement > 0.15,  # 15% error reduction
        'statistical_significance': compute_p_value(baseline_errors, intervention_errors)
    }
```

**Action Items**:
- [ ] For each error subtype, test top 2 recommended interventions
- [ ] Measure on 50 test questions per subtype
- [ ] Target: >15% error reduction, p < 0.05
- [ ] If intervention doesn't work: revise recommendations

**Grounding Evidence**: If recommended fixes don't work, taxonomy isn't actionable.

---

#### 3.2 Causal Analysis

**Goal**: Verify error types are causes, not just correlations.

```python
def test_causal_attribution(error_subtype: ErrorSubtype,
                            suspected_cause: str) -> Dict:
    """
    Use counterfactual testing to verify causation.

    Example:
    Suspected cause: "Negation blindness" - model misses "not"
    Test:
    1. Find questions with negations where model fails
    2. Remove negation (reverse logic)
    3. Check if model now succeeds

    If yes: negation was the cause
    If no: something else caused the error
    """
    # Find errors classified as this type
    errors_of_type = [e for e in all_errors if e.error_subtype == error_subtype]

    causal_count = 0
    non_causal_count = 0

    for error in errors_of_type[:50]:  # Sample
        # Create counterfactual version
        if error_subtype == ErrorSubtype.NEGATION_BLINDNESS:
            # Remove negation
            original = error.question_text
            counterfactual = remove_negation(original)

            # Re-run model
            new_response = model.generate(counterfactual)

            # Check if model now succeeds
            # (accounting for flipped logic)
            if is_logically_consistent(original, new_response, counterfactual):
                causal_count += 1
            else:
                non_causal_count += 1

    causal_ratio = causal_count / (causal_count + non_causal_count)

    return {
        'causal_ratio': causal_ratio,
        'interpretation': (
            'strong_causation' if causal_ratio > 0.7 else
            'weak_causation' if causal_ratio < 0.4 else
            'moderate_causation'
        )
    }
```

**Action Items**:
- [ ] Design counterfactual tests for top 5 error types
- [ ] Run on 50 examples each
- [ ] Target: Causal ratio > 60%
- [ ] If ratio < 40%: error type is mis-attributed

**Grounding Evidence**: True error types should show causal relationship.

---

### Phase 4: Longitudinal Validation (Months 2-6)

#### 4.1 Temporal Stability

**Goal**: Taxonomy should be stable across model versions.

```python
def test_temporal_stability(gpt3_errors, gpt4_errors, gpt4o_errors) -> Dict:
    """
    Track error type prevalence across model generations.

    Expectation:
    - Knowledge errors should decrease (better training data)
    - Reasoning errors should persist (fundamental limitation)
    - New error types may emerge

    Test if taxonomy captures evolution patterns
    """
    error_distribution_over_time = []

    for model_errors, model_name in [
        (gpt3_errors, 'GPT-3.5'),
        (gpt4_errors, 'GPT-4'),
        (gpt4o_errors, 'GPT-4o')
    ]:
        distribution = Counter(e.error_subtype for e in model_errors)
        error_distribution_over_time.append({
            'model': model_name,
            'distribution': distribution
        })

    # Analyze trends
    knowledge_errors_trend = [
        d['distribution'][ErrorSubtype.FACTUAL_GAP]
        for d in error_distribution_over_time
    ]

    reasoning_errors_trend = [
        d['distribution'][ErrorSubtype.MULTI_STEP_REASONING]
        for d in error_distribution_over_time
    ]

    return {
        'knowledge_errors_declining': is_declining(knowledge_errors_trend),
        'reasoning_errors_stable': is_stable(reasoning_errors_trend),
        'interpretation': 'taxonomy_captures_evolution'
    }
```

**Action Items**:
- [ ] Analyze 3+ model generations
- [ ] Track error type prevalence over time
- [ ] Verify expected patterns (knowledge ↓, reasoning stable)
- [ ] Update taxonomy if new error types emerge

**Grounding Evidence**: Valid taxonomy should show meaningful evolution patterns.

---

#### 4.2 Domain Expert Validation

**Goal**: Domain experts confirm error classifications make sense.

```python
def get_expert_feedback(sample_errors: List[ErrorRecord]) -> Dict:
    """
    Show 20 classified errors to domain experts (physics, law, etc.)

    Ask:
    1. Does this classification make sense?
    2. What would you add to the explanation?
    3. Are there patterns we're missing?

    Iterate taxonomy based on qualitative feedback
    """
    feedback = []

    for error in sample_errors:
        expert_review = {
            'question_id': error.question_id,
            'our_classification': error.error_subtype,
            'expert_agrees': None,  # Fill from survey
            'expert_alternative': None,
            'expert_reasoning': None
        }
        feedback.append(expert_review)

    agreement_rate = sum(f['expert_agrees'] for f in feedback) / len(feedback)

    return {
        'agreement_rate': agreement_rate,
        'new_insights': [f['expert_reasoning'] for f in feedback],
        'suggested_refinements': aggregate_expert_suggestions(feedback)
    }
```

**Action Items**:
- [ ] Interview 10 domain experts (2 per major domain)
- [ ] Show 20 classified errors each
- [ ] Target: >70% agreement
- [ ] Incorporate qualitative insights

**Grounding Evidence**: If experts disagree, we're missing nuance.

---

## Summary: Validation Checklist

### Must-Have Validations (Months 1-2)
- [ ] **Inter-rater reliability**: Kappa > 0.7
- [ ] **LLM agreement**: >75% with GPT-4/Claude
- [ ] **Cluster coherence**: Silhouette > 0.4
- [ ] **Predictive power**: AUROC > 0.65 on held-out questions
- [ ] **Cross-model transfer**: >60% accuracy
- [ ] **Difficulty calibration**: Spearman r > 0.5 with human ratings

### Should-Have Validations (Months 2-4)
- [ ] **Intervention efficacy**: >15% error reduction for recommended fixes
- [ ] **Causal attribution**: >60% causal ratio on counterfactuals
- [ ] **Domain expert agreement**: >70% on classifications

### Nice-to-Have Validations (Months 4-6)
- [ ] **Temporal stability**: Meaningful evolution patterns across generations
- [ ] **Generalization**: Works on GPQA, MATH benchmarks
- [ ] **Publication acceptance**: Peer review validates approach

---

## Red Flags: When to Revise Taxonomy

**Weak Evidence**:
- Kappa < 0.5 → Categories not well-defined
- AUROC < 0.55 → No predictive power (just post-hoc labeling)
- Silhouette < 0.2 → Clusters are arbitrary
- No intervention works → Taxonomy isn't actionable
- Expert agreement < 50% → Missing key insights

**Action**: Iterate on taxonomy definitions, merge/split categories, refine detection rules.

---

## Gold Standard: What "Grounded" Looks Like

A well-grounded taxonomy should:

1. ✅ **Reliable**: Multiple annotators agree (Kappa > 0.7)
2. ✅ **Predictive**: Forecasts future errors (AUROC > 0.65)
3. ✅ **Universal**: Transfers across models (>60% accuracy)
4. ✅ **Calibrated**: Aligns with human difficulty ratings (r > 0.5)
5. ✅ **Actionable**: Interventions reduce errors (>15% improvement)
6. ✅ **Causal**: Counterfactuals verify attribution (>60% causal)
7. ✅ **Validated**: Domain experts agree (>70% consensus)
8. ✅ **Stable**: Shows meaningful evolution patterns over time

This multi-faceted validation ensures taxonomy reflects **real patterns in LLM cognition**, not just convenient categories.
