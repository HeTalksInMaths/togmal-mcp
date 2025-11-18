# Research Findings on LLM Error Taxonomies

## Summary of Existing Research (2024)

### 1. MMLU-Pro Error Analysis (ArXiv 2406.01574)

**Key Finding**: Analysis of 120 errors from GPT-4o revealed:
- **39% Reasoning Process Flaws** - Logical errors despite having correct knowledge
- **35% Domain Expertise Gaps** - Missing specialized knowledge (esp. Engineering, Law)
- **12% Computational Errors** - Math/calculation mistakes
- **14% Other** - Format errors, ambiguity, etc.

**Insight**: Chain-of-thought (CoT) boosts GPT-4o performance by 19% on MMLU-Pro, indicating that reasoning support is critical for harder questions.

**Citation**: Wang et al., "MMLU-Pro: A More Robust and Challenging Multi-Task Language Understanding Benchmark"

---

### 2. "Are We Done with MMLU?" (ArXiv 2406.04127)

**Key Finding**: Systematic analysis found:
- **9%+ error rate** in MMLU dataset ground truth labels
- **57% errors** in Virology subset
- Created **MMLU-Redux**: 3,000 manually re-annotated questions

**Error Taxonomy for Dataset Quality**:
1. **Bad Question Clarity** - Ambiguous or poorly written
2. **Bad Options** - Implausible or duplicate options
3. **No Correct Option** - All answers are wrong
4. **Multiple Correct Options** - More than one valid answer

**Insight**: Dataset quality issues can mask true model capabilities. Need to validate ground truth before analyzing model errors.

**Citation**: Koto et al., "Are We Done with MMLU?"

---

### 3. Math Word Problem Error Dataset (MWPES-300K) (ArXiv 2501.15581)

**Key Finding**: Created dataset of 304,865 erroneous solutions from real LLM outputs across 4 MWP datasets.

**Error Classification Framework**:
- **Conceptual Errors** (high-level) - Less amenable to algorithmic correction
- **Procedural Errors** (low-level) - Can be caught with symbolic verification
- **Dynamic Adaptive Framework** - Adjusts error detection based on error type

**Insight**: High-level conceptual errors require different intervention strategies than procedural errors. Simple post-processing can't fix conceptual mistakes.

**Citation**: Zhang et al., "Error Classification of Large Language Models on Math Word Problems"

---

### 4. Hierarchical Error Framework (HEC) for Communication Research (ArXiv 2509.24841)

**Key Finding**: Analysis of 1,469 baseline errors revealed three-layer structure:
- **Knowledge-layer (58.4%)** - Domain terminology gaps, specialty boundary confusion
- **Reasoning-layer** - Logical inference failures
- **Complexity-layer** - Struggles with complex, multi-faceted content

**Theoretical Foundation**: Based on Reason's error hierarchy:
- **Skill-based errors** - Execution failures (slips, lapses)
- **Rule-based errors** - Wrong rule application
- **Knowledge-based errors** - Missing knowledge, wrong mental model

**Insight**: Different error layers require different mitigation strategies. Knowledge errors need better training data; reasoning errors need better prompting.

**Citation**: Li et al., "A Hierarchical Error Framework for Reliable Automated Coding"

---

### 5. Evaluating LLMs at Detecting Errors (ArXiv 2404.03602)

**Four Evaluation Criteria**:
1. **Reasoning Correctness** - Logical soundness of inference chains
2. **Instruction-Following** - Adherence to user requirements
3. **Context-Faithfulness** - Consistency with provided context
4. **Parameterized Knowledge** - Correctness of factual information

**Insight**: These criteria are objectively evaluable by humans and cover diverse error types in LLM responses.

**Citation**: Cohen et al., "Evaluating LLMs at Detecting Errors in LLM Responses"

---

### 6. TaxoGlimpse Benchmark (ArXiv 2406.11131)

**Key Finding**: Evaluated LLMs on taxonomy discovery tasks:
- Best-performing LLMs show **unsatisfactory performance** on specialized taxonomies
- Performance **degrades significantly** for entities near leaf levels of hierarchy
- Generalist models struggle with **fine-grained domain knowledge**

**Insight**: Hierarchical knowledge structures reveal blind spots in LLM knowledge. Surface-level performance doesn't guarantee deep understanding.

**Citation**: Zhang et al., "Are Large Language Models a Good Replacement of Taxonomies?"

---

### 7. Cognitive Complexity Framework (ArXiv 2509.19347)

**Application of Bloom's Taxonomy to LLMs**:
- **Remember** (recall facts) → **Create** (generate novel solutions)
- Knowledge Graph tasks mapped to cognitive levels
- Higher-order reasoning (analyze, evaluate, create) shows steeper error curves

**Insight**: Cognitive science frameworks can systematically categorize task complexity and predict failure modes.

**Citation**: Wang et al., "Characterizing Knowledge Graph Tasks in LLM Benchmarks"

---

## Synthesis: Proposed Unified Taxonomy

Combining insights from all papers, here's a comprehensive error taxonomy:

### Level 0: Error Source (HEC-inspired)
1. **Dataset Errors** - Ground truth issues (from "Are We Done with MMLU?")
2. **Model Errors** - True LLM failures

### Level 1: Error Category (Reason's hierarchy + MMLU-Pro analysis)
1. **Knowledge-Layer (35-58%)**
   - Factual gaps
   - Domain blind spots
   - Outdated information
   - Misconceptions

2. **Reasoning-Layer (39%)**
   - Multi-step reasoning failures
   - Logical inference errors
   - Causal confusion
   - Analogical reasoning failures

3. **Execution-Layer (12%)**
   - Computational errors
   - Format/parsing errors
   - Output generation issues

4. **Comprehension-Layer**
   - Context neglect
   - Instruction misunderstanding
   - Ambiguity mishandling
   - Negation blindness

5. **Systematic Biases**
   - Position bias
   - Length bias
   - Confidence miscalibration

### Level 2: Fine-Grained Subtypes
(As defined in ERROR_TAXONOMY_DESIGN.md)

### Level 3: Discovered Patterns
(From clustering and LLM-assisted analysis)

---

## Implications for Our Implementation

### 1. Dataset Validation First
Before analyzing model errors, validate MMLU-Pro ground truth:
- Check for "Bad Question Clarity"
- Verify "No Correct Option" cases
- Flag "Multiple Correct Options" scenarios

**Action**: Implement dataset quality checker based on "Are We Done with MMLU?" framework

### 2. Multi-Level Error Attribution
Don't just classify errors - attribute them to layers:
- Is this a knowledge gap or reasoning failure?
- Is the question itself flawed?
- Would CoT help, or is it a fundamental knowledge gap?

**Action**: Implement hierarchical classification (knowledge → reasoning → execution)

### 3. Error Clustering by Cognitive Complexity
Use Bloom's taxonomy levels to group questions:
- **Remember/Understand** (low complexity) - Factual recall
- **Apply/Analyze** (medium) - Domain application
- **Evaluate/Create** (high) - Multi-step reasoning

**Action**: Add cognitive complexity scoring to questions

### 4. Comparative Analysis with Known Benchmarks
Compare our findings to MMLU-Pro paper results:
- Do we see similar 39% reasoning / 35% knowledge split?
- Which models match GPT-4o's error profile?
- Are there novel error patterns not in published research?

**Action**: Implement comparison metrics against published baselines

### 5. Intervention-Specific Analysis
Different errors need different fixes:
- **Knowledge errors** → Better training data, RAG
- **Reasoning errors** → CoT, step-by-step prompting
- **Computational errors** → Tool use, symbolic verification
- **Comprehension errors** → Prompt engineering, examples

**Action**: For each error type, recommend specific interventions

---

## Research Gaps We Can Fill

### 1. Cross-Model Systematic Error Patterns
**Question**: Do different model families (Llama, Qwen, Mixtral) make systematically different errors on same questions?

**Novel Contribution**: Multi-model consensus analysis + architecture-specific error profiles

### 2. Temporal Evolution of Error Types
**Question**: As models improve (GPT-3.5 → GPT-4 → GPT-4o), do error types shift from knowledge → reasoning → edge cases?

**Novel Contribution**: Track error type evolution across model generations

### 3. Domain-Specific Error Hierarchies
**Question**: Does the error taxonomy look different for Physics vs. Law vs. History?

**Novel Contribution**: Domain-specific error taxonomies with specialized subtypes

### 4. Predictive Error Modeling
**Question**: Can we predict which questions will cause errors based on semantic similarity to known errors?

**Novel Contribution**: Vector-based error prediction system (already partially built!)

### 5. Ensemble Error Analysis
**Question**: When do multiple models agree on wrong answers (systematic) vs. disagree (ambiguous question)?

**Novel Contribution**: Consensus scoring + distractor strength analysis

---

## Next Steps

1. ✅ Review existing research (DONE)
2. Update implementation to incorporate:
   - Dataset quality validation
   - Hierarchical error attribution (knowledge → reasoning → execution)
   - Cognitive complexity scoring
   - Comparison to published baselines
3. Run analysis on our 500 MMLU-Pro questions
4. Generate comparison report: Our findings vs. MMLU-Pro paper
5. Identify novel patterns not covered in existing research
6. Write up findings for potential publication
