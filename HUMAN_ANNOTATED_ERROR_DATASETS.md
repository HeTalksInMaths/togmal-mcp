# Human-Annotated LLM Error Datasets for ToGMAL

**Status**: Available datasets with human annotations of model failures

---

## Summary

| Dataset | Size | Annotation Type | Domains | Access |
|---------|------|----------------|---------|--------|
| **BIG-Bench Mistake** | 2,186 examples (1,708 annotated) | Error location (which step is first mistake) | 5 reasoning tasks | ✅ GitHub (open) |
| **ReaLMistake** | 900 examples | Error label + category + natural language explanation | 3 NLP tasks | ⚠️ HuggingFace (requires auth) |
| **EIC-Math** | 1,800 cases | Error type + error step | Math reasoning | 🔍 Need to locate |
| **JudgeBench** | 620 pairs | Human preference (A>B or B>A) | Multi-domain SOTA failures | ✅ Downloaded |

---

## Dataset 1: BIG-Bench Mistake ⭐ RECOMMENDED

### Overview
- **Paper**: "LLMs cannot find reasoning errors, but can correct them given the error location" (ACL 2024)
- **Repository**: https://github.com/WHGTyen/BIG-Bench-Mistake
- **Size**: 2,186 examples (1,708 with mistake annotations)
- **Model**: PaLM 2-L (Unicorn)
- **Status**: ✅ Downloaded to `/tmp/BIG-Bench-Mistake/`

### Human Annotation
**What humans annotated**: The index of the **first logical mistake** in the chain-of-thought

Each example has:
```json
{
  "input": "question text",
  "steps": ["step 1", "step 2", "step 3", ...],
  "mistake_index": 2,  // ← Human annotated: first mistake at step 2
  "target": "correct answer",
  "answer": "model's answer"
}
```

### Tasks Covered
1. **Logical Deduction** (300 examples, 294 annotated)
   - 5 objects with ordering constraints
   - Multi-step logical inference

2. **Tracking Shuffled Objects** (300 examples, 260 annotated)
   - Track object positions through swaps
   - Working memory + state tracking

3. **Word Sorting** (300 examples, 266 annotated)
   - Alphabetically sort lists of words
   - Sequential comparison operations

4. **Multistep Arithmetic** (300 examples, 238 annotated)
   - Multi-operation arithmetic problems
   - Iterative calculation chains

5. **Dyck Languages** (986 examples, 650 annotated)
   - Bracket matching / context-free grammar
   - Hierarchical structure tracking

### Mistake Distribution
- **Step 1-3**: 817 mistakes (47.8%) - Early errors
- **Step 4-10**: 525 mistakes (30.7%) - Middle errors
- **Step 10+**: 366 mistakes (21.4%) - Late errors
- **Average mistake step**: 6.3

### Why This Is Valuable for ToGMAL
✅ **Human annotated error location** - pinpoints exactly where reasoning breaks
✅ **Chain-of-thought traces** - full reasoning path, not just final answer
✅ **Covers key reasoning types** - logic, arithmetic, tracking, structure
✅ **Immediately usable** - clean format, no authentication required
✅ **1,708 annotated examples** - substantial coverage

### Limitations
❌ **Only 5 tasks** - narrow domain coverage (no code, science, etc.)
❌ **Location only** - doesn't explain WHY the mistake happened
❌ **Single model** - only PaLM 2-L, not GPT-4/Claude
❌ **No error taxonomy** - doesn't categorize error types

### How to Use for ToGMAL
1. **Add domain-specific why**: For each task, characterize what type of conceptual error causes mistakes at that step
2. **Pattern mapping**: Map to your 7 patterns (arithmetic errors, variable confusion, etc.)
3. **Step-level risk**: Predict which reasoning step is most likely to fail for similar queries
4. **Combine with JudgeBench**: Use JudgeBench for breadth, BIG-Bench for depth

---

## Dataset 2: ReaLMistake ⭐ BEST FOR "WHY"

### Overview
- **Paper**: "Evaluating LLMs at Detecting Errors in LLM Responses" (2024)
- **Repository**: https://github.com/psunlpgroup/ReaLMistake
- **HuggingFace**: ryokamoi/realmistake
- **Size**: 900 examples
- **Models**: GPT-4-0613, Llama 2 70B

### Human Annotation
**What humans annotated**:
1. **Binary error label**: "error" or "no_error"
2. **Error categories**:
   - Reasoning Correctness
   - Instruction-Following
   - Context-Faithfulness
   - Parameterized Knowledge
3. **Natural text explanations**: Human-written explanation of WHY it's wrong

### Example Format
```json
{
  "input": "question/instruction",
  "response": "model's response",
  "error_label": "error",
  "error_categories": ["Reasoning Correctness"],
  "explanation": "The model incorrectly calculated... because...",
  "model": "gpt-4-0613"
}
```

### Tasks Covered
1. **Math Word Problem Generation** (300 examples)
2. **Fine-grained Fact Verification** (300 examples)
3. **Answerability Classification** (300 examples)

### Why This Is Valuable for ToGMAL
✅ **Natural language explanations** - humans explain WHY in text
✅ **Error taxonomy** - categorizes types of errors
✅ **SOTA models** - GPT-4 and Llama 2 70B
✅ **Binary + category + explanation** - rich annotations

### Limitations
❌ **Only 900 examples** - smaller than BIG-Bench
❌ **Only 3 tasks** - narrow coverage
❌ **Requires authentication** - HuggingFace agreement needed
❌ **No step-by-step** - single response, no CoT breakdown

---

## Dataset 3: JudgeBench (Already Downloaded)

### Overview
- **Repository**: https://github.com/ScalerLab/JudgeBench
- **Size**: 620 response pairs
- **Models**: GPT-4o (May 2024), Claude-3.5-Sonnet (June 2024)
- **Status**: ✅ Downloaded to `data/judgebench/`

### Human Annotation
**What humans annotated**: Preference judgment (A>B or B>A)

### Sources (17 domains)
- livebench-reasoning (149 cases)
- livebench-math (90 cases)
- livecodebench (73 cases)
- mmlu-pro-* (17 categories, 22 each): law, biology, CS, health, history, psychology, philosophy, economics, math, chemistry, physics, engineering, business, other

### Why This Is Valuable for ToGMAL
✅ **Breadth**: 17 domains vs 3-5 in other datasets
✅ **Latest SOTA**: GPT-4o and Claude-3.5 from 2024
✅ **Real failures**: Actual SOTA model mistakes on hard tasks
✅ **Already analyzed**: 9 cases deep-dived with domain-specific why

### Limitations
❌ **Binary preference only**: Shows which is better, not why
❌ **Need to infer errors**: Not pre-annotated with reasons
❌ **You're doing this manually**: Current approach - 9 done, 611 to go

---

## Recommendation for Scaling ToGMAL

### Option 1: Hybrid Approach ⭐ RECOMMENDED

**Combine multiple datasets for complementary coverage**:

1. **JudgeBench** (620 cases) → **Breadth** across 17 domains
   - Continue deep-dive on stratified sample
   - Target: 50-100 annotated cases
   - Covers science, law, business, engineering (missing from others)

2. **BIG-Bench Mistake** (1,708 cases) → **Depth** on reasoning + already annotated
   - Already has human error locations
   - Add domain-specific "why" layer
   - Target: 200 cases annotated with conceptual errors
   - Focuses on logic, arithmetic, tracking

3. **ReaLMistake** (900 cases) → **Human explanations** (if accessible)
   - Use their natural language explanations directly
   - Map their categories to your 7 patterns
   - Validate your annotation approach

**Total: ~350 cases across 20+ domains with human-grounded annotations**

### Option 2: Focus on BIG-Bench Mistake

**Process**:
1. Load 1,708 annotated examples
2. For each, look at the mistake step + surrounding context
3. Classify conceptual error type
4. Write domain-specific why (5 min per case)

**Advantages**:
- 1,708 already annotated (error location)
- Clean format, immediately usable
- Faster than reading full responses

**Limitations**:
- Only 5 task types
- Missing: code, science, law, business, engineering

**Time**: 200 cases × 5 min = ~17 hours

### Option 3: Scale JudgeBench Analysis

**Process**:
1. Stratified sample: 100 cases across 17 sources
2. Read both responses for each
3. Identify specific error
4. Write domain-specific why (15 min per case)

**Advantages**:
- 17 domains covered
- SOTA models (GPT-4o, Claude-3.5)
- Consistent with your 9 existing annotations

**Limitations**:
- Time-intensive (full response reading)
- Only 100 cases

**Time**: 100 cases × 15 min = ~25 hours

---

## Recommended Hybrid Workflow

### Phase 1: Quick Coverage (Week 1)
1. **BIG-Bench Mistake** - Annotate 200 cases
   - Sample 40 per task
   - Add domain-specific why layer
   - Map to 7 patterns
   - **Output**: 200 annotated reasoning cases

### Phase 2: Domain Breadth (Week 2)
2. **JudgeBench** - Annotate 50 more cases
   - Stratified: 3 per source (17 sources)
   - Focus on missing domains (science, law, business)
   - Deep dive like current 9
   - **Output**: 50 + 9 = 59 diverse domain cases

### Phase 3: Quality Check (Week 3)
3. **ReaLMistake** - Access and integrate
   - If accessible, use 900 human explanations
   - Map to your taxonomy
   - Cross-validate against your annotations
   - **Output**: Validation + potential 900 more cases

### Result
- **Total annotated**: 259 minimum, up to 1,159 if ReaLMistake accessible
- **Domain coverage**: 17+ domains from JudgeBench + 5 reasoning from BIG-Bench
- **Human grounding**: All based on human annotations (error location or preference)
- **Time estimate**: ~42 hours (doable in 3 weeks)

---

## Summary Table

| Metric | BIG-Bench Mistake | ReaLMistake | JudgeBench |
|--------|------------------|-------------|------------|
| Size | 1,708 annotated | 900 | 620 |
| Access | ✅ Downloaded | ⚠️ Need auth | ✅ Downloaded |
| Annotation | Error location | Label + explanation | Preference |
| Models | PaLM 2 | GPT-4, Llama 2 | GPT-4o, Claude-3.5 |
| Domains | 5 reasoning tasks | 3 NLP tasks | 17 domains |
| Has WHY | ❌ Need to add | ✅ Human written | ❌ Need to add |
| Has WHERE | ✅ Step-level | ❌ | ❌ |
| Ready to use | ✅ Yes | ⚠️ If accessible | ✅ Yes |
| Best for | Fast coverage (reasoning) | Understanding WHY | Domain breadth |
| Effort to annotate | 5 min/case | 0 min (already done) | 15 min/case |

---

## Next Action

**What do you want to do?**

**A.** Start annotating BIG-Bench Mistake (fast coverage - 200 cases in ~17 hours)
**B.** Continue JudgeBench deep dives (high quality - 50 more cases in ~12 hours)
**C.** Try to access ReaLMistake first (potentially 900 cases with human explanations)
**D.** Hybrid approach: BIG-Bench (200) + JudgeBench (50) = 250 total

I can start immediately on any of these.
