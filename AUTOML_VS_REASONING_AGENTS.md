# AutoML vs Reasoning Agents for Task-Level Error Taxonomy

## The Question

Should we use **AutoML** or **Reasoning Agents** to parse MT-Bench data and build a task-oriented taxonomy of conceptual errors?

## Analysis

### What We're Trying to Achieve

**Goal**: Build a taxonomy that maps:
```
Human Task → Conceptual Error → Observable Failure
```

**Example**:
```
Task: "Write a limerick about smartphones"
Conceptual Error: Lack of prosodic reasoning (can't track meter/rhyme)
Observable Failure: Produces paragraph instead of AABBA rhyme scheme
```

This is fundamentally different from surface classification like "instruction_following error."

---

## AutoML Approach

### What AutoML Would Do

1. **Feature Extraction**:
   - Bag-of-words from questions
   - Response length, format features
   - Surface patterns (punctuation, structure)

2. **Pattern Recognition**:
   - Cluster similar failures
   - Predict error categories from features
   - Find correlations

3. **Classification**:
   - Train classifier: (question, response) → error_type
   - Use ensemble methods (XGBoost, Random Forest)
   - Optimize for accuracy on labeled data

### Strengths
✅ Scales to large datasets efficiently
✅ Finds statistical patterns humans might miss
✅ Fast inference once trained
✅ Good for prediction tasks

### Weaknesses
❌ **Cannot understand conceptual errors** (just surface patterns)
❌ **Requires pre-labeled data** (chicken-and-egg problem)
❌ **No causal reasoning** (correlation ≠ causation)
❌ **Cannot map to human tasks conceptually**
❌ **Black box** (can't explain *why* an error occurred)
❌ **Misses nuance** (e.g., can't distinguish "didn't understand rhyme scheme" from "understood but failed execution")

### Verdict for This Task
**❌ Not suitable** - AutoML can't answer "WHY conceptually did this model fail at this human task?"

---

## Reasoning Agents Approach

### What Reasoning Agents Would Do

1. **Deep Analysis**:
   - Read the task instructions
   - Understand what cognitive capabilities are required
   - Analyze winning vs losing responses
   - Identify conceptual gaps (not just surface errors)

2. **Task Decomposition**:
   - Break down "write a limerick" into:
     - Understand AABBA rhyme scheme
     - Maintain meter (anapestic)
     - Preserve semantic content while restructuring
     - Track constraints across lines

3. **Causal Reasoning**:
   - "The model failed because it lacks X capability"
   - "This failure manifests as Y in task type Z"
   - Build causal chains: conceptual gap → intermediate failure → observable error

4. **Taxonomy Construction**:
   - Group tasks by required capabilities
   - Map conceptual errors to task types
   - Create hierarchical structure

### Strengths
✅ **Understands conceptual errors** at a deep level
✅ **Can reason about causality** (why, not just what)
✅ **No pre-labeled data needed** (can bootstrap)
✅ **Maps to human task structure** naturally
✅ **Explainable** (provides reasoning for classifications)
✅ **Captures nuance** (distinguishes understanding vs execution failures)
✅ **Builds rich taxonomies** with causal relationships

### Weaknesses
❌ More expensive (API costs for LLM calls)
❌ Slower than AutoML (sequential reasoning)
❌ Requires careful prompt engineering
❌ Quality depends on LLM capabilities

### Verdict for This Task
**✅ Ideal** - Reasoning agents can build the conceptual task-oriented taxonomy you want.

---

## Recommendation: Hybrid Approach

### Phase 1: Reasoning Agents (Build Taxonomy)
**Use reasoning agents to:**
1. Deeply analyze 100-200 representative error cases
2. Identify task types and required capabilities
3. Build initial task-oriented taxonomy
4. Create labeled dataset with conceptual annotations

**Output**:
- Rich taxonomy: Task → Required Capabilities → Conceptual Errors
- Labeled dataset with explanations

### Phase 2: AutoML (Scale & Validate)
**Use AutoML to:**
1. Train classifier on labeled data from Phase 1
2. Predict error categories for remaining cases
3. Find patterns and clusters
4. Validate taxonomy coverage

**Output**:
- Scaled classification across full dataset
- Pattern validation
- Confidence scores

### Phase 3: Iterative Refinement
**Use reasoning agents to:**
1. Analyze AutoML's low-confidence predictions
2. Discover new error patterns
3. Refine taxonomy
4. Update AutoML classifier

---

## Task-Oriented Taxonomy Structure

### Hierarchical Design

```
Level 1: Human Task Domain
  └─ Level 2: Specific Task Type
      └─ Level 3: Required Capabilities
          └─ Level 4: Conceptual Error Types
              └─ Level 5: Observable Failures
```

### Example Hierarchy

```
CREATIVE WRITING
├─ Poetry Generation
│   ├─ Rhyme Scheme Tasks (limerick, sonnet)
│   │   ├─ Required: Prosodic reasoning
│   │   │   └─ Error: Cannot track rhyme patterns
│   │   │       └─ Failure: Produces prose instead of poetry
│   │   ├─ Required: Meter awareness
│   │   │   └─ Error: No rhythmic understanding
│   │   │       └─ Failure: Inconsistent syllable counts
│   │   └─ Required: Constraint satisfaction
│   │       └─ Error: Cannot maintain multiple constraints
│   │           └─ Failure: Breaks rhyme when maintaining meter
│   └─ Stylistic Constraint Writing
│       ├─ Required: Alliteration tracking
│       ├─ Required: Per-sentence constraint tracking
│       └─ Error: Loses constraint after first few sentences
│
LOGICAL REASONING
├─ Multi-Step Deduction
│   ├─ Chain of Reasoning Tasks
│   │   ├─ Required: State tracking
│   │   │   └─ Error: Loses intermediate conclusions
│   │   ├─ Required: Logical inference
│   │   │   └─ Error: Makes non-sequitur leaps
│   │   └─ Required: Consistency checking
│   │       └─ Error: Self-contradicts in step 3
│   └─ Constraint Satisfaction Problems
│       ├─ Required: Constraint propagation
│       └─ Error: Satisfies constraint A but breaks constraint B
```

---

## Implementation Plan

### Reasoning Agent System

```python
class TaskOrientedErrorAnalyzer:
    """Uses reasoning agents to build task-oriented error taxonomy"""

    def analyze_case(self, question, losing_response, winning_response):
        """
        Use LLM to deeply analyze a single case

        Returns:
        {
          'task_domain': 'Creative Writing',
          'specific_task': 'Limerick composition with constraints',
          'required_capabilities': [
              'Prosodic reasoning (AABBA rhyme)',
              'Meter tracking (anapestic)',
              'Semantic preservation under restructuring'
          ],
          'conceptual_error': 'Cannot maintain rhyme scheme',
          'why_conceptual': 'Model lacks phonetic similarity reasoning',
          'observable_failure': 'Output is paragraph, not limerick',
          'error_chain': [
              'No rhyme scheme representation',
              '-> Cannot plan line endings',
              '-> Defaults to prose generation'
          ]
        }
        """
```

### AutoML Augmentation (Phase 2)

```python
class ErrorPatternClassifier:
    """AutoML classifier trained on reasoning agent labels"""

    def train(self, labeled_data):
        """Train on reasoning agent output"""

    def predict(self, unlabeled_cases):
        """Predict task-level errors for new cases"""

    def find_clusters(self):
        """Discover new error patterns"""
```

---

## Cost-Benefit Analysis

### Reasoning Agents
- **Cost**: ~$0.01-0.03 per case analysis (Claude)
- **For 3,355 cases**: ~$30-100 total
- **Value**: Deep conceptual understanding, rich taxonomy

### AutoML
- **Cost**: ~$0 (open source tools)
- **Requirements**: Need labeled data first (from reasoning agents)
- **Value**: Fast scaling, pattern validation

### Conclusion
**Start with reasoning agents** for 100-200 cases (~$3-6) to build taxonomy, then decide if AutoML scaling is needed.

---

## Answer: Use Reasoning Agents

For your specific goal of building a **task-oriented taxonomy of conceptual errors**, you need **reasoning agents**.

AutoML can augment later, but only reasoning agents can:
1. Understand what human tasks require conceptually
2. Identify why models fail (causal reasoning)
3. Map conceptual errors to task failures
4. Build the rich taxonomy you're describing

Let's build it! 🚀
