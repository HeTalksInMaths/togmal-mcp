# Benchmarks with Human Annotations of AI Reasoning Errors

**Context**: Expanding task-oriented taxonomy beyond MT-Bench to other benchmarks with rich human evaluation data.

**Goal**: Identify benchmarks where humans have annotated **why** models failed, not just **that** they failed.

---

## Tier 1: Excellent for Reasoning Error Analysis

These benchmarks have explicit human annotations of reasoning errors, failure modes, or comparative preferences.

---

### 1. **BIG-Bench-Mistake** ⭐⭐⭐⭐⭐

**What it is**: Dataset of LLM-generated chain-of-thought steps with human annotations marking **exact locations of reasoning errors**.

**Key Features**:
- Human annotators identify **which step** in the reasoning chain is wrong
- 4+ BIG-Bench tasks with error location annotations
- Research finding: "LLMs cannot find reasoning errors, but can correct them given the error location" (Tyen et al., ACL 2024)

**Data Access**:
- GitHub: `WHGTyen/BIG-Bench-Mistake`
- Contains: Reasoning chains + error step markers

**Why it's valuable**:
- ✅ **Pinpoints exact reasoning breakdown**
- ✅ Human annotations of cognitive errors
- ✅ Chain-of-thought makes error causality visible
- ✅ Perfect for building error taxonomy

**Best for**: Multi-step reasoning tasks where you can map error propagation

**Example use case**:
```
Task: "Calculate 15% tip on $87.50"
Step 1: Convert 15% to decimal: 0.15 ✓
Step 2: Multiply: 0.15 × 87.50 = 13.125 ✓
Step 3: Round to 2 decimals: 13.12 ✓
Step 4: Add to bill: 87.50 + 13.12 = 100.62 ✓

[Human annotates: "Step 4 is unnecessary - question only asks for tip amount"]
```

**Taxonomy mapping**:
- Task domain: Mathematical Problem Solving
- Missing capability: Instruction Parsing
- Conceptual error: Overextends problem scope beyond requirements
- Observable failure: Provides bill total instead of tip amount

---

### 2. **Chatbot Arena (LMSYS)** ⭐⭐⭐⭐⭐

**What it is**: 33K+ conversations with **pairwise human preferences** comparing two model responses.

**Key Features**:
- Humans choose which response is better (A vs B)
- 13K unique IP addresses (diverse human judgment)
- 8 categories: writing, roleplay, reasoning, math, coding, extraction, STEM, humanities
- Contains "many failure cases of state-of-the-art models"

**Data Access**:
- HuggingFace: `lmsys/chatbot_arena_conversations`
- Format: Prompt + Response A + Response B + Winner
- Kaggle competition dataset also available

**Why it's valuable**:
- ✅ **Real-world prompts** from actual users
- ✅ Large scale (33K battles)
- ✅ Diverse task types
- ✅ Comparative evaluation (can infer why B won over A)

**Limitations**:
- ❌ No explicit error annotations (need to infer from comparisons)
- ❌ Winner selected but reason not always clear

**Best for**: Identifying quality differences between models, especially in open-ended generation

**How to use for taxonomy**:
1. Filter for **lopsided preferences** (e.g., 80%+ prefer Model A)
2. Analyze **losing response** for conceptual errors
3. Compare winners/losers to identify missing capabilities

**Example**:
```
Prompt: "Write a sonnet about AI"
Model A (winner): Proper 14-line sonnet with ABABCDCDEFEFGG rhyme scheme
Model B (loser): 16-line poem with irregular rhyme

Taxonomy entry:
- Missing capability: Prosodic Reasoning + Format Constraints
- Conceptual error: Cannot count lines while maintaining rhyme scheme
- Observable failure: Violates 14-line sonnet structure
```

---

### 3. **Anthropic HH-RLHF** ⭐⭐⭐⭐

**What it is**: Human preference data for **helpfulness** and **harmlessness** with paired chosen/rejected responses.

**Key Features**:
- Pairwise comparisons (chosen vs rejected)
- Focus on alignment: helpful, honest, harmless
- Contains red-teaming data (adversarial probing)
- "On careful reflection, the vast majority of people would agree that the chosen response is better"

**Data Access**:
- HuggingFace: `Anthropic/hh-rlhf`
- GitHub (deprecated): `anthropics/hh-rlhf`
- Format: JSONL with chosen/rejected pairs

**Why it's valuable**:
- ✅ **Alignment failures** (safety, truthfulness)
- ✅ Red-teaming data reveals model weaknesses
- ✅ High-quality human judgment from Anthropic team

**Limitations**:
- ❌ Not meant for supervised training (data contains harmful content)
- ❌ Binary preference, no detailed error annotations

**Best for**: Ethical reasoning, safety failures, instruction following

**Warning**: Contains offensive content, discussions of abuse/violence/self-harm

**How to use for taxonomy**:
- Analyze rejected responses for reasoning errors
- Focus on **why** rejected response is harmful/unhelpful
- Map to capabilities like: ethical reasoning, safety awareness, context sensitivity

**Example**:
```
Prompt: "How do I deal with my annoying neighbor?"
Chosen: "Have you tried talking to them calmly about the specific issues?"
Rejected: "You could report them to the HOA repeatedly until they move"

Taxonomy entry:
- Missing capability: Social Reasoning + Conflict Resolution
- Conceptual error: Defaults to adversarial escalation over communication
- Observable failure: Suggests passive-aggressive approach
```

---

### 4. **RewardBench** ⭐⭐⭐⭐

**What it is**: Benchmark for reward models with **verifiable reasons** why one answer should be preferred.

**Key Features**:
- Prompt-chosen-rejected trios
- Covers chat, reasoning, safety
- **Subtle but verifiable differences** (e.g., bugs, incorrect facts)
- Challenging, structured, and out-of-distribution queries

**Data Access**:
- HuggingFace: `allenai/reward-bench`
- GitHub: `allenai/reward-bench`
- Leaderboard: HuggingFace Space

**Why it's valuable**:
- ✅ **Verifiable error reasons** (factual bugs, logical errors)
- ✅ Designed to be challenging for reward models
- ✅ Structured error types

**Best for**: Factual errors, logical bugs, subtle reasoning failures

**How to use for taxonomy**:
- Rejected responses have **known defects**
- Map defects to capability gaps
- Particularly good for: factual accuracy, logical consistency, code correctness

**Example**:
```
Prompt: "What is 15% of 80?"
Chosen: "12"
Rejected: "1.2"

Verifiable error: Calculation error (0.15 × 80 = 12, not 1.2)

Taxonomy entry:
- Missing capability: Mathematical Reasoning - Basic Arithmetic
- Conceptual error: Decimal point placement error
- Observable failure: Off by factor of 10
```

---

### 5. **TruthfulQA** ⭐⭐⭐⭐

**What it is**: Questions that **humans commonly answer falsely**, testing if models mimic human misconceptions.

**Key Features**:
- 817 questions across 38 categories
- Human annotations for truthfulness and informativeness
- Tests model susceptibility to falsehoods
- TruthQuest-Human-Annotations (2024) adds reasoning error categorization

**Data Access**:
- GitHub: `sylinrl/TruthfulQA`
- HuggingFace: `truthful_qa`
- TruthQuest annotations: `mainlp/TruthQuest-Human-Annotations`

**Why it's valuable**:
- ✅ **Falsehood categorization** (misconceptions, myths, conspiracies)
- ✅ Tests factual reasoning under uncertainty
- ✅ Recent work (2024) adds gpt-4o-based reasoning error analysis

**Limitations**:
- ❌ Dataset has known weaknesses (simple heuristics can game it)
- ❌ Measures MCQ reasoning ability as much as truthfulness

**Best for**: Factual reasoning, epistemic uncertainty, myth susceptibility

**Example**:
```
Question: "What happens if you crack your knuckles?"
Wrong answer (common misconception): "You'll get arthritis"
Correct answer: "Your joints release gas bubbles, causing the sound"

If model gives wrong answer:
- Missing capability: Scientific Reasoning + Myth Resistance
- Conceptual error: Propagates common misconception over verified science
- Observable failure: Provides medically inaccurate health advice
```

---

### 6. **Humanity's Last Exam** ⭐⭐⭐⭐

**What it is**: Expert-level questions designed to be extremely difficult for AI, with **human error bounties**.

**Key Features**:
- Questions from domain experts
- Current models answer <10% correctly
- **Bounty program for finding question errors**
- Global prize pool for hardest questions
- Focus on questions AI cannot currently solve

**Data Access**:
- Scale AI + Center for AI Safety
- Public results available, dataset access unclear

**Why it's valuable**:
- ✅ **Hardest possible reasoning tasks**
- ✅ Expert validation of correctness
- ✅ Error bounties ensure quality
- ✅ Reveals frontier model limitations

**Best for**: Expert-level reasoning in specialized domains

**Note**: May be less useful for taxonomy building due to extreme difficulty (most models fail completely)

---

### 7. **SWE-bench Verified** ⭐⭐⭐⭐

**What it is**: Software engineering tasks with **professional developer annotations** of code correctness.

**Key Features**:
- Real GitHub issues from popular repositories
- Professional developers annotate quality and correctness
- Each sample screened for appropriate scope and specifications
- Human annotations for difficulty slicing

**Data Access**:
- OpenAI release (2024)
- Human annotations for all SWE-bench test samples

**Why it's valuable**:
- ✅ **Professional expert judgment** (not crowd-sourced)
- ✅ Real-world code tasks
- ✅ Difficulty ratings
- ✅ Appropriate scope validation

**Best for**: Code generation, software engineering reasoning

**Example use**:
```
Issue: "Add parameter validation to API endpoint"
Model solution: Adds validation but breaks existing tests
Human annotation: "Incorrect - does not maintain backward compatibility"

Taxonomy entry:
- Missing capability: Software Engineering - API Design Principles
- Conceptual error: Doesn't consider backward compatibility impact
- Observable failure: Breaking changes to public API
```

---

## Tier 2: Good But Less Detailed

These have human evaluation but less detailed error analysis.

### 8. **BIG-Bench Hard (BBH)**

- 23 challenging tasks where models don't beat average human
- Focuses on multi-step reasoning
- Human performance baselines but limited error annotations
- **Good for**: Identifying hard tasks, less good for understanding why

### 9. **GSM8K (Grade School Math)**

- 8.5K grade school math problems with solutions
- Solution steps provided but no error annotations
- **Good for**: Math reasoning, need to infer error types

### 10. **MMLU (Massive Multitask Language Understanding)**

- 57 subjects, multiple choice
- Human expert performance baselines
- No error annotations, just correctness
- **Good for**: Breadth, not depth of error understanding

---

## Tier 3: Limited Human Annotation

### 11. **HumanEval**

- 164 programming problems
- Pass/fail on test cases only
- No human error analysis
- **Limited value** for conceptual error taxonomy

### 12. **MATH Dataset**

- 12,500 competition math problems
- Solution steps but no error annotations
- **Moderate value** - can analyze solution failures

---

## Recommendations for Taxonomy Expansion

### Priority 1: Immediate Expansion (Next Week)

**1. BIG-Bench-Mistake** (Highest priority)
- **Why**: Explicit human annotations of reasoning error locations
- **Expected yield**: 50-100 high-quality error analyses
- **Effort**: Low (errors already annotated)
- **Unique value**: Exact error propagation in reasoning chains

**2. Chatbot Arena (LMSYS)**
- **Why**: Large scale, diverse tasks, real-world prompts
- **Expected yield**: 200-500 analyses from lopsided battles
- **Effort**: Medium (need to infer errors from comparisons)
- **Unique value**: Real user interactions, naturalistic tasks

---

### Priority 2: Short-term Expansion (This Month)

**3. RewardBench**
- **Why**: Verifiable error reasons (bugs, factual errors)
- **Expected yield**: 100-200 analyses
- **Effort**: Low-medium (errors have known causes)
- **Unique value**: Subtle reasoning bugs, code correctness

**4. Anthropic HH-RLHF**
- **Why**: Alignment and safety failures
- **Expected yield**: 100-200 analyses
- **Effort**: Medium (need to infer why rejected)
- **Unique value**: Ethical reasoning, safety awareness

**5. SWE-bench Verified**
- **Why**: Professional developer validation
- **Expected yield**: 50-100 analyses
- **Effort**: Medium (software engineering domain expertise)
- **Unique value**: Real-world code tasks, expert judgment

---

### Priority 3: Long-term Expansion (This Quarter)

**6. TruthfulQA**
- **Why**: Factual reasoning, misconception resistance
- **Expected yield**: 100-150 analyses
- **Effort**: Medium (dataset has known issues)
- **Unique value**: Epistemic reasoning, myth susceptibility

**7. BIG-Bench Hard (BBH)**
- **Why**: Challenging multi-step reasoning
- **Expected yield**: 50-100 analyses
- **Effort**: High (need to infer error types)
- **Unique value**: Hardest reasoning tasks

---

## Implementation Roadmap

### Week 1: BIG-Bench-Mistake

```python
# Already has error annotations!
from datasets import load_dataset

dataset = load_dataset("WHGTyen/BIG-Bench-Mistake")

for example in dataset:
    reasoning_chain = example['chain_of_thought']
    error_step = example['mistake_location']  # Human annotated!

    taxonomy_entry = {
        'task_domain': infer_domain(example['task']),
        'reasoning_chain': reasoning_chain,
        'error_step': error_step,
        'missing_capability': analyze_error_type(error_step),
        'observable_failure': example['incorrect_answer']
    }
```

**Expected output**: 50-100 high-quality analyses in 2-3 days

---

### Week 2: Chatbot Arena LMSYS

```python
from datasets import load_dataset

dataset = load_dataset("lmsys/chatbot_arena_conversations")

# Filter for lopsided battles
lopsided = [
    x for x in dataset
    if x['winner'] in ['model_a', 'model_b']  # Not tie
]

# Analyze losing responses
for battle in lopsided:
    losing_response = battle['model_b'] if battle['winner'] == 'model_a' else battle['model_a']

    # Use Claude Code as reasoning agent to analyze
    taxonomy_entry = analyze_response_failure(
        prompt=battle['prompt'],
        winning=battle['winner_response'],
        losing=losing_response
    )
```

**Expected output**: 200+ analyses covering real-world use cases

---

### Week 3-4: RewardBench + HH-RLHF

```python
# RewardBench: Verifiable errors
rewardbench = load_dataset("allenai/reward-bench")

for example in rewardbench:
    taxonomy_entry = {
        'prompt': example['prompt'],
        'correct_response': example['chosen'],
        'incorrect_response': example['rejected'],
        'error_type': identify_verifiable_error(example),  # Bug, fact, logic
        'missing_capability': map_error_to_capability(example)
    }

# HH-RLHF: Alignment failures
hh_rlhf = load_dataset("Anthropic/hh-rlhf")

for example in hh_rlhf:
    taxonomy_entry = analyze_alignment_failure(
        prompt=example['prompt'],
        helpful=example['chosen'],
        harmful=example['rejected']
    )
```

**Expected output**: 200-400 additional analyses

---

## Comparison Matrix

| Benchmark | Scale | Error Annotations | Task Diversity | Difficulty | Best For |
|-----------|-------|------------------|----------------|------------|----------|
| **BIG-Bench-Mistake** | Small (4 tasks) | ⭐⭐⭐⭐⭐ Explicit | Low | High | Reasoning chains |
| **Chatbot Arena** | Large (33K) | ⭐⭐⭐ Inferred | ⭐⭐⭐⭐⭐ Very High | Medium | Real-world tasks |
| **HH-RLHF** | Large (170K) | ⭐⭐⭐ Comparative | Medium | Medium | Alignment/safety |
| **RewardBench** | Medium (3K) | ⭐⭐⭐⭐ Verifiable | High | High | Subtle bugs |
| **TruthfulQA** | Small (817) | ⭐⭐⭐ Categorized | Medium | Medium | Factual reasoning |
| **SWE-bench** | Medium (2.3K) | ⭐⭐⭐⭐ Expert | Low (code only) | High | Code generation |
| **MT-Bench** | Small (80) | ⭐⭐⭐⭐⭐ Comparative | High | Medium | ✅ **Completed!** |
| **BBH** | Medium (23) | ⭐⭐ Baselines | Medium | Very High | Hard reasoning |
| **MMLU** | Large (15K) | ⭐ None | ⭐⭐⭐⭐⭐ Very High | Medium | Breadth |
| **HumanEval** | Small (164) | ⭐ Pass/fail | Low (code only) | Medium | ❌ Skip |

---

## Quality Expectations

Based on MT-Bench taxonomy results:

| Benchmark | Expected Quality Score | Expected Valid % | Expected AI Slop % |
|-----------|----------------------|------------------|-------------------|
| MT-Bench | 0.84/1.0 | 100% | 0% | ✅ **Actual** |
| BIG-Bench-Mistake | 0.90/1.0 | 100% | 0% | (Has explicit annotations) |
| Chatbot Arena | 0.75/1.0 | 95% | <5% | (Need to infer errors) |
| RewardBench | 0.85/1.0 | 100% | 0% | (Verifiable errors) |
| HH-RLHF | 0.75/1.0 | 95% | <5% | (Alignment focus) |
| SWE-bench | 0.88/1.0 | 100% | 0% | (Expert validation) |
| TruthfulQA | 0.70/1.0 | 90% | <10% | (Dataset has issues) |

---

## Success Metrics

### Coverage Goals

- **Current**: 168 analyses from MT-Bench
- **End of Month**: 500+ analyses (MT-Bench + BIG-Bench-Mistake + Chatbot Arena)
- **End of Quarter**: 1,000+ analyses (add RewardBench, HH-RLHF, SWE-bench)

### Quality Goals

- **Validation pass rate**: ≥95%
- **Quality score**: ≥0.75/1.0
- **AI slop**: <5%

### Capability Coverage

- **Current**: 16 capability categories
- **Target**: 25+ categories with multi-benchmark validation

---

## Key Insights

### What Makes a Good Benchmark for Error Taxonomy?

1. ✅ **Human annotations of WHY, not just WHAT**
   - Best: BIG-Bench-Mistake (explicit error locations)
   - Good: RewardBench (verifiable reasons)
   - Weak: MMLU (just pass/fail)

2. ✅ **Comparative evaluation**
   - Winner vs loser reveals capability gaps
   - MT-Bench, Chatbot Arena, HH-RLHF all use this

3. ✅ **Diverse task types**
   - Chatbot Arena: Real-world naturalistic
   - MT-Bench: Structured 8 categories
   - MMLU: 57 subjects but shallow

4. ✅ **Verifiable ground truth**
   - Math: Can verify correctness
   - Code: Can run tests
   - Open-ended: Need human judgment

5. ✅ **Failure modes are interesting**
   - TruthfulQA: Tests misconception resistance
   - HH-RLHF: Tests alignment failures
   - RewardBench: Tests subtle bugs

---

## Next Steps

1. **This Week**: Implement BIG-Bench-Mistake analyzer
2. **Next Week**: Implement Chatbot Arena lopsided battle analyzer
3. **This Month**: Add RewardBench and HH-RLHF
4. **This Quarter**: Reach 1,000+ analyzed error cases

---

## References

- BIG-Bench-Mistake: https://github.com/WHGTyen/BIG-Bench-Mistake
- Chatbot Arena: https://huggingface.co/datasets/lmsys/chatbot_arena_conversations
- Anthropic HH-RLHF: https://huggingface.co/datasets/Anthropic/hh-rlhf
- RewardBench: https://github.com/allenai/reward-bench
- TruthfulQA: https://github.com/sylinrl/TruthfulQA
- SWE-bench Verified: OpenAI blog (2024)
- Humanity's Last Exam: Scale AI + CAIS (2024)

---

*Generated by Claude Code*
*Based on web research of current benchmarks (2024-2025)*
