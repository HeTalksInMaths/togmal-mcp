# Hierarchical Error Taxonomy System for LLM Analysis

## Overview
A systematic approach to analyzing MMLU-Pro errors to understand **why** LLMs make mistakes, building a multi-level taxonomy of conceptual errors.

## Error Taxonomy Hierarchy

### Level 1: High-Level Error Categories
1. **Knowledge Deficits** - Missing or incorrect factual knowledge
2. **Reasoning Failures** - Logical/inferential errors despite having knowledge
3. **Comprehension Errors** - Misunderstanding question or context
4. **Format/Parsing Errors** - Technical failures in output generation
5. **Systematic Biases** - Consistent patterns across question types

### Level 2: Error Subtypes

#### 1. Knowledge Deficits
- **1.1 Factual Gaps**: Missing specific facts (dates, names, formulas)
- **1.2 Domain Blind Spots**: Weak in entire subject areas
- **1.3 Outdated Information**: Training data cutoff issues
- **1.4 Misconceptions**: Active incorrect beliefs

#### 2. Reasoning Failures
- **2.1 Multi-Step Reasoning**: Breaks down in chains of logic
- **2.2 Counterfactual Reasoning**: Struggles with hypotheticals
- **2.3 Quantitative Reasoning**: Math/calculation errors
- **2.4 Causal Reasoning**: Confuses correlation/causation
- **2.5 Analogical Reasoning**: Poor transfer across domains

#### 3. Comprehension Errors
- **3.1 Negation Blindness**: Misses "not", "except", "least"
- **3.2 Qualifier Confusion**: Ignores "always", "sometimes", "never"
- **3.3 Context Neglect**: Misses critical contextual clues
- **3.4 Ambiguity Mishandling**: Wrong interpretation of ambiguous text

#### 4. Format/Parsing Errors
- **4.1 Output Format**: Generates invalid response format
- **4.2 Choice Extraction**: Picks option not in choices
- **4.3 Refusal Errors**: Inappropriately refuses to answer

#### 5. Systematic Biases
- **5.1 Position Bias**: Prefers certain answer positions (A/B/C/D)
- **5.2 Length Bias**: Prefers longer/shorter options
- **5.3 Confidence Miscalibration**: Overconfident on wrong answers
- **5.4 Domain Transfer Failure**: Applies wrong domain knowledge

### Level 3: Fine-Grained Error Patterns

For each Level 2 subtype, identify specific patterns through clustering:
- Question semantic similarity (vector embeddings)
- Error co-occurrence across models
- Domain-specific error signatures

## Implementation Strategy

### Phase 1: Data Collection & Enrichment
```python
class ErrorRecord:
    question_id: str
    model_name: str
    correct_answer: str
    model_answer: str
    is_correct: bool

    # Metadata for analysis
    domain: str
    difficulty_score: float
    question_embedding: np.ndarray

    # Error analysis fields (to be filled)
    error_category: str  # Level 1
    error_subtype: str   # Level 2
    error_patterns: List[str]  # Level 3
    confidence_score: float
```

### Phase 2: Automated Error Classification

#### A. Rule-Based Detection (High Precision)
```python
def detect_negation_blindness(question_text: str, error: ErrorRecord) -> bool:
    """Detect if model missed 'not', 'except', 'least' etc."""
    negation_keywords = ['not', 'except', 'least', 'never', 'cannot']
    return any(kw in question_text.lower() for kw in negation_keywords)

def detect_position_bias(model_errors: List[ErrorRecord]) -> Dict:
    """Analyze if model systematically prefers certain answer positions."""
    position_freq = Counter([err.model_answer for err in model_errors])
    return chi_square_test(position_freq)  # Check for non-uniform distribution
```

#### B. LLM-Assisted Classification (High Coverage)
```python
async def classify_error_with_llm(error: ErrorRecord) -> ErrorClassification:
    """
    Use Claude to analyze why the model made this error.

    Prompt structure:
    - Show question + all choices
    - Show correct answer vs model answer
    - Ask: What type of error is this? (provide taxonomy)
    - Ask: What specific knowledge/reasoning failed?
    - Ask: Would other models likely make the same error?
    """
    prompt = f"""
    Analyze this LLM error:

    Question: {error.question_text}
    Choices: {error.choices}
    Correct Answer: {error.correct_answer}
    Model Answer: {error.model_answer}

    Classify the error using this taxonomy:
    [Include taxonomy tree]

    Provide:
    1. Primary error category (Level 1)
    2. Specific error subtype (Level 2)
    3. Root cause explanation
    4. Likelihood other models make same error (High/Medium/Low)
    """

    return await claude_api.classify(prompt)
```

#### C. Clustering-Based Discovery (Pattern Finding)
```python
def discover_error_patterns(errors: List[ErrorRecord]) -> List[ErrorCluster]:
    """
    Use vector embeddings + clustering to find novel error patterns.
    """
    # 1. Embed all error questions
    embeddings = [err.question_embedding for err in errors]

    # 2. Cluster using HDBSCAN (handles varying densities)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=5)
    labels = clusterer.fit_predict(embeddings)

    # 3. For each cluster, analyze common characteristics
    clusters = []
    for label in set(labels):
        if label == -1:  # Noise
            continue

        cluster_errors = [e for e, l in zip(errors, labels) if l == label]

        # Analyze what makes this cluster unique
        pattern = {
            'cluster_id': label,
            'size': len(cluster_errors),
            'common_domains': Counter([e.domain for e in cluster_errors]),
            'avg_difficulty': np.mean([e.difficulty_score for e in cluster_errors]),
            'affected_models': set([e.model_name for e in cluster_errors]),
            'sample_questions': cluster_errors[:5],

            # Extract linguistic patterns
            'common_keywords': extract_tfidf_keywords(cluster_errors),
            'question_structure': analyze_syntactic_patterns(cluster_errors),
        }

        clusters.append(pattern)

    return clusters
```

### Phase 3: Comparative Analysis Across Models

```python
def compare_model_error_profiles(models: List[str]) -> pd.DataFrame:
    """
    Build error profile matrix: models × error types
    """
    matrix = []

    for model in models:
        model_errors = get_errors_for_model(model)

        profile = {
            'model': model,
            'total_errors': len(model_errors),
            'error_rate': len(model_errors) / total_questions,
        }

        # Count each error type
        for category in ERROR_TAXONOMY:
            profile[category] = count_errors_by_type(model_errors, category)

        matrix.append(profile)

    df = pd.DataFrame(matrix)

    # Identify model strengths/weaknesses
    df['strongest_area'] = df.drop(['model', 'total_errors'], axis=1).idxmin(axis=1)
    df['weakest_area'] = df.drop(['model', 'total_errors'], axis=1).idxmax(axis=1)

    return df
```

### Phase 4: Cross-Model Error Agreement Analysis

```python
def analyze_error_consensus(question_id: str) -> ErrorConsensusAnalysis:
    """
    For questions where multiple models err, understand if they make
    the SAME error (systematic) or DIFFERENT errors (ambiguous question).
    """
    errors = get_errors_for_question(question_id)

    if len(errors) < 2:
        return None  # Only one model failed

    # Check if models made the same wrong choice
    wrong_answers = [e.model_answer for e in errors]
    consensus_score = max(Counter(wrong_answers).values()) / len(wrong_answers)

    analysis = {
        'question_id': question_id,
        'num_models_failed': len(errors),
        'models': [e.model_name for e in errors],
        'consensus_score': consensus_score,  # 1.0 = all chose same wrong answer
        'wrong_answer_distribution': Counter(wrong_answers),

        'interpretation': (
            'systematic_error' if consensus_score > 0.7
            else 'ambiguous_question' if consensus_score < 0.4
            else 'mixed_errors'
        )
    }

    # If systematic, dig deeper
    if analysis['interpretation'] == 'systematic_error':
        analysis['likely_cause'] = diagnose_systematic_error(errors)
        analysis['distractor_strength'] = analyze_distractor(
            question_id,
            most_common_wrong_answer
        )

    return analysis
```

### Phase 5: Hierarchical Visualization

```python
def build_error_taxonomy_tree(errors: List[ErrorRecord]) -> Dict:
    """
    Build interactive hierarchical tree of errors.
    """
    tree = {
        'name': 'All Errors',
        'value': len(errors),
        'children': []
    }

    # Level 1: High-level categories
    for category in ERROR_CATEGORIES:
        cat_errors = [e for e in errors if e.error_category == category]

        category_node = {
            'name': category,
            'value': len(cat_errors),
            'percentage': len(cat_errors) / len(errors) * 100,
            'children': []
        }

        # Level 2: Subtypes
        for subtype in get_subtypes(category):
            sub_errors = [e for e in cat_errors if e.error_subtype == subtype]

            subtype_node = {
                'name': subtype,
                'value': len(sub_errors),
                'percentage': len(sub_errors) / len(cat_errors) * 100,
                'examples': [e.question_id for e in sub_errors[:3]]
            }

            category_node['children'].append(subtype_node)

        tree['children'].append(category_node)

    return tree

# Export to D3.js, Plotly, or other viz libraries
```

## Analysis Workflows

### Workflow 1: Model Debugging
"Why does Model X struggle with quantum physics?"

1. Filter errors: Model X + domain="physics" + subdomain="quantum"
2. Cluster error questions by semantic similarity
3. Classify errors using taxonomy
4. Compare to other models' performance on same questions
5. Generate report: "Model X has 2.3× higher error rate on quantum superposition questions, primarily due to **Multi-Step Reasoning failures** (Category 2.1)"

### Workflow 2: Dataset Quality Analysis
"Are there ambiguous/mislabeled questions?"

1. Find questions where ALL models fail or disagree
2. Analyze error consensus (do they choose same wrong answer?)
3. If high disagreement: flag for human review
4. Use LLM to explain correct answer and why wrong answers seem plausible

### Workflow 3: Intervention Design
"How can we improve reasoning on legal questions?"

1. Identify top error subtypes for domain="law"
2. For each subtype, extract representative examples
3. Design targeted prompting strategies or fine-tuning data
4. A/B test interventions on held-out questions from same error cluster

### Workflow 4: Novel Error Discovery
"What unexpected error patterns exist?"

1. Run clustering on all errors (unsupervised)
2. For each cluster, use LLM to generate hypotheses about common failure mode
3. Validate hypothesis on more examples
4. If consistent: add new node to taxonomy

## Implementation Roadmap

### Week 1: Data Foundation
- [ ] Populate model results for all 500 questions (5+ models)
- [ ] Expand to full MMLU-Pro dataset (12K questions)
- [ ] Build ErrorRecord database schema
- [ ] Implement extraction of actual model answers (not just correct/incorrect)

### Week 2: Classification Pipeline
- [ ] Implement rule-based error detectors
- [ ] Build LLM-assisted classification system
- [ ] Create error embedding pipeline
- [ ] Test on subset (100 errors) for validation

### Week 3: Pattern Discovery
- [ ] Implement clustering algorithms
- [ ] Build cross-model comparison tools
- [ ] Create error consensus analyzer
- [ ] Generate first-pass taxonomy from data

### Week 4: Visualization & Reporting
- [ ] Build hierarchical tree visualizations
- [ ] Create model error profile dashboards
- [ ] Implement interactive exploration tools
- [ ] Generate automated analysis reports

## Key Research Questions

1. **Universality**: Are certain error types universal across models, or do different architectures have different failure modes?

2. **Difficulty Correlation**: Do harder questions produce different error types than easier ones?

3. **Domain Specificity**: Are errors in law fundamentally different from errors in physics?

4. **Transfer Learning**: Can we predict errors on unseen questions based on error patterns on similar questions?

5. **Intervention Efficacy**: If we provide chain-of-thought, does it address some error categories better than others?

6. **Evolution**: How do error profiles change across model generations (GPT-3.5 → GPT-4 → GPT-4.5)?

## Success Metrics

- **Coverage**: % of errors successfully classified into taxonomy
- **Coherence**: Intra-cluster similarity > inter-cluster similarity
- **Actionability**: Can we design interventions targeting specific error types?
- **Predictive Power**: Can error taxonomy predict model performance on new questions?
- **Discovery**: Do we find novel error patterns not covered by initial taxonomy?

## Output Artifacts

1. **Error Database**: SQLite DB with all errors + classifications
2. **Taxonomy Tree**: JSON/YAML defining hierarchy
3. **Model Profiles**: Per-model error distribution reports
4. **Pattern Library**: Catalog of discovered error patterns with examples
5. **Visualization Dashboard**: Interactive exploration tool
6. **Research Paper**: Findings on LLM conceptual error patterns
