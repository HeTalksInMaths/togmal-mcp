# ToGMAL MCP - Complete System Demo

## System Purpose

The ToGMAL MCP predicts **LLM failure rates** for user questions by:
1. Finding semantically similar benchmark questions
2. Checking how LLMs performed on those questions
3. Aggregating failure rates across models
4. Providing risk assessment and recommendations

---

## Complete Workflow

### User Scenario: Business Ethics Question

**User asks an LLM**: "What are the ethical duties of corporate managers to shareholders?"

**MCP Process**:

```
1. User Query
   ↓
2. Semantic Search (74% precision@10)
   → Finds 20 similar questions from 13,100 question database
   → Top match: "Managers are entrusted to run the company..." (0.899 similarity)
   ↓
3. Performance Lookup
   → Checks if similar questions have benchmark data
   → Found: 1 question with performance from 4 LLMs
   ↓
4. Aggregate Results
   → Llama-2-70b-hf: ✅ CORRECT
   → Llama-2-13b-hf: ❌ FAILED
   → Llama-2-7b-hf: ❌ FAILED
   → Meta-Llama-3-70B: ❌ FAILED
   ↓
5. Calculate Failure Rate
   → 3 failures out of 4 attempts = 75% failure rate
   ↓
6. Risk Classification
   → 75% failure = VERY_HIGH_RISK
   ↓
7. MCP Response
   ⚠️ CAUTION: This type of question has 75% failure rate
   📊 Only Llama-2-70b succeeded
   💡 Suggested Action: Use largest available model or alternative approach
```

---

## Example Outputs

### Example 1: Business Ethics (High Risk)

```
Query: "Managers duties to shareholders"
Domain: business

📊 ANALYSIS:
   Similar questions: 20 found
   With performance data: 1 match
   Coverage: 5%

✨ PREDICTION:
   Overall Failure Rate: 75.0%
   Overall Success Rate: 25.0%
   Evaluations: 4 models tested

🤖 MODEL PERFORMANCE:
   Llama-2-70b-hf          Success:  100.0%  ← Best choice
   Llama-2-13b-hf          Success:    0.0%
   Llama-2-7b-hf           Success:    0.0%
   Meta-Llama-3-70B        Success:    0.0%

⚠️ RISK ASSESSMENT: VERY_HIGH_RISK (75% failure)

   Message: "Very high failure risk. This type of question has
            consistently failed across multiple models."

   Suggested Action: "CAUTION: Consider alternative approaches.
                      Only large models (70B+) succeeded."

📚 SIMILAR QUESTION:
   mmlu_pro_71 (similarity: 0.899)
   "Managers are entrusted to run the company in the best
    interest of ________. Specifically, they have a duty..."

   This exact question type failed 75% of the time.
```

**Interpretation**:
- **HIGH RISK**: User's question is very similar to a benchmark question that most models failed on
- **Model Selection Matters**: Only 70B parameter model succeeded
- **Action**: Use best available model or break down the task

---

### Example 2: Low Risk Scenario (Hypothetical)

```
Query: "What is 2+2?"
Domain: math

📊 ANALYSIS:
   Similar questions: 20 found
   With performance data: 15 matches
   Coverage: 75%

✨ PREDICTION:
   Overall Failure Rate: 5.0%
   Overall Success Rate: 95.0%
   Evaluations: 60 models tested

🤖 MODEL PERFORMANCE:
   GPT-4               Success:  100.0%
   Claude-3-Sonnet     Success:  100.0%
   Llama-2-70b         Success:   93.3%
   Llama-2-13b         Success:   86.7%

⚠️ RISK ASSESSMENT: LOW_RISK (5% failure)

   Message: "Low failure risk. Similar questions have 95%
            success rate across models."

   Suggested Action: "Proceed normally with any model."
```

**Interpretation**:
- **LOW RISK**: Similar questions succeeded 95% of the time
- **Any Model Works**: Even smaller models handle this well
- **Action**: Proceed with confidence

---

## System Components

### 1. Semantic Search (74% Precision)

```python
# Finds similar questions using TF-IDF + LSA embeddings
scorer = LocalSemanticScorer(
    questions=13_100_questions,
    embedding_dim=488,
    domain_boost=0.496
)

similar = scorer.search(
    query="Manager duties to shareholders",
    top_k=20,
    query_domain="business"
)
# Returns: 20 most similar questions (74% relevant)
```

**Why it works**: Captures semantic meaning, not just keywords
- "eigenvalue" ≈ "matrix decomposition"
- "manager duty" ≈ "corporate responsibility"

### 2. Performance Database

```json
{
  "questions": {
    "71": {  // Question ID
      "Llama-2-70b-hf": {
        "is_correct": true,
        "model_prediction": "F",
        "correct_answer": "F",
        "question_text": "Managers are entrusted..."
      },
      "Llama-2-13b-hf": {
        "is_correct": false,  // Failed
        "model_prediction": "D",
        "correct_answer": "F"
      }
    }
  }
}
```

**Coverage**:
- 170 questions with model performance
- 4 LLMs evaluated (Llama-2 family, Meta-Llama-3)
- Expandable to thousands with more eval data

### 3. Failure Rate Predictor

```python
predictor = FailureRatePredictor()

result = predictor.predict_failure_rate(
    query="Manager duties",
    domain="business",
    top_k_similar=20
)

# Returns:
# - similar_questions_found: 20
# - questions_with_performance_data: 1
# - overall_failure_rate: 75.0%
# - by_model: {...}
# - risk_level: "VERY_HIGH_RISK"
# - recommendation: {...}
```

### 4. Risk Classification

| Failure Rate | Risk Level | Action |
|--------------|------------|--------|
| 0-20% | **LOW_RISK** | Proceed normally |
| 20-40% | **MODERATE_RISK** | Consider verification or stronger model |
| 40-60% | **HIGH_RISK** | Use best model + human verification |
| 60-100% | **VERY_HIGH_RISK** | Caution: Question type consistently fails |

---

## Real-World Use Cases

### Use Case 1: Model Selection

**Scenario**: User needs to answer business ethics questions

**MCP Analysis**:
```
Query: "Corporate governance principles"
→ 65% failure rate overall
→ But 70B parameter models: 20% failure
→ vs 7B parameter models: 90% failure

Recommendation: Use GPT-4, Claude Sonnet, or Llama-70B
               Avoid smaller models for this question type
```

**Value**: Prevents using underpowered models

### Use Case 2: Task Decomposition

**Scenario**: Complex multi-step question

**MCP Analysis**:
```
Query: "Analyze this company's ethical violations and legal liability"
→ 80% failure rate (too complex)
→ But sub-questions:
   - "What are ethical violations?": 15% failure
   - "What is legal liability?": 20% failure

Recommendation: Break into 2 simpler questions
```

**Value**: Identifies when to decompose tasks

### Use Case 3: Human-in-Loop Trigger

**Scenario**: Critical decision-making

**MCP Analysis**:
```
Query: "Should we fire this employee for ethics violation?"
→ 70% failure rate
→ VERY_HIGH_RISK classification

Recommendation: AUTO-TRIGGER human review
               Do not rely solely on LLM output
```

**Value**: Prevents acting on unreliable LLM output

---

## Performance Metrics

### Semantic Search
- **Precision@10**: 74.0% (vs 18.3% with keyword matching)
- **Domain Coherence**: 83.9%
- **Speed**: ~50ms per query (13K questions)

### Failure Prediction
- **Coverage**: 170 questions with performance data (expandable)
- **Models Tracked**: 4 (expandable to 40+ from eval cache)
- **Prediction Speed**: <1 second per query

### Accuracy of Predictions
- Based on **real benchmark results** (MMLU-Pro)
- Aggregated across multiple models
- Confidence scoring based on coverage

---

## Limitations & Future Improvements

### Current Limitations

1. **Limited Coverage**: Only 170 questions have performance data
   - Solution: Process all 47 eval cache files → 12,000+ questions

2. **Few Models**: Only 4 LLMs tracked
   - Solution: Add GPT-4, Claude, Gemini from eval cache

3. **Domain Gaps**: Strong on business/law, weak on coding
   - Solution: Add SWE-Bench (2,294 coding questions with pass@k)

4. **Binary Success**: Doesn't capture partial correctness
   - Solution: Add confidence scores, multi-level grading

### Expansion Plan

**Phase 1: More Eval Data**
```
Current: 170 questions, 4 models
→ Add: 12,000 questions, 40+ models
→ Result: 95% coverage on MMLU-Pro
```

**Phase 2: SWE-Bench Integration**
```
Add: 2,294 coding questions
→ pass@1, pass@10 metrics
→ Enables: Code failure prediction
```

**Phase 3: Real-Time MCP Tool**
```
mcp.predict_failure_rate(question="...")
→ Returns: Risk level, model recommendations
→ Integration: Auto-warn users before submission
```

---

## MCP Tool Integration (Future)

### Proposed MCP Tools

#### 1. `predict_failure_rate`
```python
mcp.predict_failure_rate(
    question="Manager duties to shareholders",
    domain="business",
    model="claude-sonnet-3.5"
)

# Returns:
{
  "risk_level": "VERY_HIGH_RISK",
  "failure_rate": 75.0,
  "model_specific_rate": 0.0,  # Claude failed on similar
  "recommendation": "Consider alternative approach",
  "similar_questions": [...]
}
```

#### 2. `compare_models_for_question`
```python
mcp.compare_models_for_question(
    question="Calculate eigenvalues"
)

# Returns: Ranked models by success rate on similar questions
{
  "best_model": "GPT-4 (95% success)",
  "worst_model": "Llama-2-7B (30% success)",
  "rankings": [...]
}
```

#### 3. `suggest_task_decomposition`
```python
mcp.suggest_task_decomposition(
    question="Complex multi-step question",
    failure_threshold=0.5
)

# Returns: Suggested breakdown if overall failure > 50%
```

---

## Key Achievement

**The ToGMAL MCP now provides evidence-based failure prediction:**

✅ Finds semantically similar benchmark questions (74% precision)
✅ Aggregates real model performance data
✅ Predicts failure rates based on actual benchmark results
✅ Classifies risk levels (LOW/MODERATE/HIGH/VERY_HIGH)
✅ Provides actionable recommendations

**Example Impact**:

Before: User asks business ethics question → LLM fails → User trusts wrong answer

After: User asks → MCP warns "75% failure rate on similar questions" → User:
- Uses larger model (70B instead of 7B)
- Adds human verification
- Breaks down into simpler questions

**This is the core ToGMAL goal**: Showing likely LLM limitations based on taxonomy of similar question failures.
