# Scaling and Quality Assurance for Task-Oriented Taxonomy

## Overview

This document outlines strategies to:
1. **Scale up** the taxonomy to comprehensive coverage
2. **Ensure quality** and avoid "AI slop" through rigorous validation
3. **Integrate** with existing ToGMAL infrastructure

---

## 1. Growing the Taxonomy

### Current State
- 8 analyzed cases
- 4 task domains
- 8 capability categories
- Manual analysis by single reasoning agent

### Scaling Strategy

#### Phase 1: Complete MT-Bench Coverage (80 questions)
**Goal**: Analyze all 80 MT-Bench questions across both turns (160 total cases)

**Approach**:
```python
# Systematic analysis of all cases
for question in mt_bench_questions:
    for turn in [1, 2]:
        for model_pair in get_losing_winning_pairs(question, turn):
            analyze_case(question, turn, model_pair)
```

**Expected Output**:
- ~200-400 unique error patterns
- 15-20 task domains
- 25-35 capability categories
- Comprehensive coverage across 8 MT-Bench categories

**Effort**: ~1-2 hours of Claude Code analysis time

#### Phase 2: Multi-Benchmark Expansion

**Target Benchmarks**:
1. **MMLU** (Massive Multitask Language Understanding)
   - 57 subjects, 15,908 questions
   - Focus: Factual knowledge, domain expertise
   - New capabilities: Domain knowledge retrieval, fact verification

2. **HumanEval** (Code generation)
   - 164 programming problems
   - Focus: Code synthesis, algorithmic thinking
   - New capabilities: Algorithm selection, code structure planning

3. **MATH** (Mathematical reasoning)
   - 12,500 problems
   - Focus: Multi-step mathematical reasoning
   - New capabilities: Equation manipulation, proof construction

4. **Big-Bench** (Beyond the Imitation Game)
   - 204 diverse tasks
   - Focus: Novel task types, edge cases
   - New capabilities: Novel task adaptation, abstract reasoning

**Sample Strategy**: Don't analyze everything, sample representatively:
- Cluster questions by difficulty/domain
- Sample 5-10 representative cases per cluster
- Analyze ~500-1000 total cases across benchmarks

#### Phase 3: Longitudinal Analysis

**Track capability evolution**:
- Analyze same tasks across model generations (GPT-3 → GPT-4, LLaMA-1 → LLaMA-2)
- Identify which capabilities improve vs persist
- Build temporal taxonomy showing capability development

---

## 2. Quality Assurance & Grounding

### The "AI Slop" Problem

**Definition**: Analyses that are plausible-sounding but lack:
- Specific evidence from responses
- Grounding in established concepts
- Predictive validity
- Internal consistency

### Quality Assurance Framework

#### Level 1: Evidence Requirements

**Every analysis must include**:
```json
{
  "conceptual_error": "Cannot maintain rhyme scheme",
  "evidence": {
    "losing_response_quote": "Here is a comparison...",
    "specific_failure": "No rhyming words at line endings",
    "expected_behavior": "AABBA pattern: day/play, refined/designed, way",
    "actual_behavior": "Prose paragraph with no rhyme"
  }
}
```

**Validation**: Automated check that evidence fields are populated and specific

#### Level 2: Inter-Rater Reliability

**Multi-Agent Analysis**:
```python
# Same case analyzed by 3 independent reasoning passes
analyses = [
    analyze_case(case, temperature=0.3, seed=1),
    analyze_case(case, temperature=0.3, seed=2),
    analyze_case(case, temperature=0.3, seed=3)
]

# Compute agreement
agreement = compute_capability_agreement(analyses)

# Only accept if agreement > 0.7
if agreement > 0.7:
    consensus = merge_analyses(analyses)
else:
    flag_for_human_review(case)
```

**Metrics**:
- Capability category agreement: Must be >70%
- Error type agreement: Must be >60%
- Understanding vs execution agreement: Must be >80%

#### Level 3: Capability Grounding

**Validate against established frameworks**:

1. **Cognitive Science Grounding**
   - Map capabilities to known cognitive processes
   - Reference: Working memory, Theory of Mind, Executive function, etc.
   - Require citation to cognitive science literature

2. **Linguistics Grounding**
   - Prosodic reasoning → Phonology literature
   - Syntax tracking → Syntactic theory
   - Semantic preservation → Compositional semantics

3. **AI Safety Grounding**
   - Align with existing capability taxonomies:
     - Anthropic's "Core Views on AI Safety"
     - OpenAI's model capabilities research
     - Academic papers on LLM capabilities

**Implementation**:
```python
capability_registry = {
    "Prosodic Reasoning": {
        "definition": "Ability to represent and manipulate sound patterns",
        "cognitive_basis": "Phonological working memory",
        "references": [
            "Baddeley, A. (2003). Working memory: Looking back and looking forward.",
            "Hayes, B. (2009). Introductory Phonology."
        ],
        "observable_tasks": ["rhyme generation", "meter tracking", "alliteration"],
        "failure_modes": ["ignores sound patterns", "violates phonotactic constraints"]
    }
}

def validate_capability(capability_name, analysis):
    if capability_name not in capability_registry:
        return ValidationResult(
            valid=False,
            reason="Capability not in registry - may be AI slop"
        )

    # Check if failure mode matches known patterns
    if analysis['observable_failure'] not in capability_registry[capability_name]['failure_modes']:
        return ValidationResult(
            valid=False,
            reason="Failure mode doesn't match expected patterns for this capability"
        )

    return ValidationResult(valid=True)
```

#### Level 4: Predictive Validation

**Test taxonomy's predictive power**:

```python
# Hold out 20% of cases
train_cases, test_cases = train_test_split(all_cases, test_size=0.2)

# Build taxonomy from train set
taxonomy = build_taxonomy(train_cases)

# Predict errors on test set
for test_case in test_cases:
    # Find similar train cases
    similar_cases = find_similar_by_task(test_case, train_cases)

    # Predict likely capability gaps
    predicted_capabilities = predict_missing_capabilities(similar_cases)

    # Analyze test case
    actual_analysis = analyze_case(test_case)

    # Compute prediction accuracy
    accuracy = compare(predicted_capabilities, actual_analysis['missing_capability'])
```

**Success Criteria**:
- Capability prediction accuracy >60% for similar tasks
- Error type prediction accuracy >50%

#### Level 5: Consistency Checks

**Automated validation**:

```python
def validate_taxonomy_consistency(taxonomy):
    issues = []

    # Check 1: Same capability should have consistent definition
    for capability in get_all_capabilities(taxonomy):
        definitions = get_all_definitions(capability)
        if len(set(definitions)) > 1:
            issues.append(f"Inconsistent definitions for {capability}")

    # Check 2: Similar tasks should require similar capabilities
    task_pairs = find_similar_task_pairs(taxonomy)
    for task_a, task_b in task_pairs:
        caps_a = get_required_capabilities(task_a)
        caps_b = get_required_capabilities(task_b)
        overlap = len(set(caps_a) & set(caps_b)) / len(set(caps_a) | set(caps_b))
        if overlap < 0.3:
            issues.append(f"Similar tasks have dissimilar capabilities: {task_a} vs {task_b}")

    # Check 3: Error chains should be causal
    for error in get_all_errors(taxonomy):
        chain = error['error_chain']
        if not is_causal_chain(chain):
            issues.append(f"Non-causal error chain: {chain}")

    return issues
```

#### Level 6: Human Expert Review

**Sample validation**:
- Randomly sample 10% of analyses
- Send to domain experts (linguists, cognitive scientists, AI researchers)
- Compare expert assessments to automated analyses
- Measure agreement and identify systematic biases

**Domains to validate**:
- Linguistics expert → Creative writing tasks
- Logician → Reasoning tasks
- Computer scientist → Coding tasks
- Cognitive scientist → Meta-cognitive tasks

---

## 3. Integration with ToGMAL

### Current ToGMAL Architecture

```
ToGMAL System:
├── benchmark_vector_db.py (difficulty assessment via similarity)
├── togmal_mcp.py (heuristic safety detection)
├── difficulty_based_clustering.py (question clustering by success rate)
└── research_pipeline.py (safety dataset integration)
```

### Integration Points

#### Integration 1: Enhanced Difficulty Assessment

**Current**: Difficulty = 1 - success_rate

**Enhanced**: Difficulty = f(success_rate, required_capabilities, model_capabilities)

```python
class EnhancedDifficultyAssessor:
    def __init__(self, vector_db, task_taxonomy):
        self.vector_db = vector_db
        self.taxonomy = task_taxonomy

    def assess_difficulty(self, prompt, model):
        # Step 1: Find similar benchmark questions
        similar = self.vector_db.query_similar(prompt, k=10)
        base_difficulty = compute_weighted_difficulty(similar)

        # Step 2: Identify required capabilities from taxonomy
        task_type = classify_task_type(prompt, self.taxonomy)
        required_caps = self.taxonomy.get_required_capabilities(task_type)

        # Step 3: Check model's capability gaps
        model_gaps = self.taxonomy.get_model_gaps(model)
        overlap = set(required_caps) & set(model_gaps)

        # Step 4: Adjust difficulty based on capability mismatch
        if overlap:
            capability_penalty = len(overlap) / len(required_caps)
            adjusted_difficulty = base_difficulty + (capability_penalty * 0.3)
        else:
            adjusted_difficulty = base_difficulty

        return {
            'base_difficulty': base_difficulty,
            'required_capabilities': required_caps,
            'model_gaps': list(overlap),
            'adjusted_difficulty': adjusted_difficulty,
            'warnings': [
                f"Model lacks {cap}" for cap in overlap
            ]
        }
```

#### Integration 2: Capability-Aware Risk Assessment

**Current**: Heuristic rules (math speculation, vibe coding, etc.)

**Enhanced**: Capability-based risk prediction

```python
class CapabilityRiskAssessor:
    def __init__(self, task_taxonomy, heuristic_detector):
        self.taxonomy = task_taxonomy
        self.heuristics = heuristic_detector

    def assess_risk(self, prompt, model, context):
        risks = []

        # Traditional heuristic detection
        heuristic_risks = self.heuristics.detect(prompt, context)
        risks.extend(heuristic_risks)

        # Taxonomy-based detection
        task_type = classify_task_type(prompt, self.taxonomy)

        # Check for systematic failures
        similar_errors = self.taxonomy.get_errors_for_task(task_type, model)

        for error in similar_errors:
            if error['is_systematic_error']:
                risks.append({
                    'type': 'capability_gap',
                    'severity': error['error_severity'],
                    'capability': error['missing_capability'],
                    'likelihood': error['occurrence_rate'],
                    'description': f"Model systematically fails at {error['conceptual_error']}",
                    'mitigation': suggest_mitigation(error)
                })

        return risks
```

#### Integration 3: Unified Taxonomy Structure

**Goal**: Merge difficulty, safety, and capability dimensions

```python
class UnifiedBenchmarkEntry:
    def __init__(self):
        # Existing ToGMAL fields
        self.question_id = None
        self.source_benchmark = None
        self.domain = None
        self.success_rate = None
        self.difficulty_score = None

        # NEW: Task-oriented fields
        self.task_domain = None  # e.g., "Creative Writing"
        self.specific_task = None  # e.g., "Limerick composition"
        self.required_capabilities = []  # e.g., ["Prosodic Reasoning", ...]

        # NEW: Known failure modes
        self.common_errors = []  # From taxonomy
        self.systematic_failures = {}  # {model: [capability_gaps]}

        # NEW: Capability requirements
        self.capability_requirements = {
            'cognitive': [],  # Working memory, Theory of Mind, etc.
            'linguistic': [],  # Prosodic, syntactic, semantic, etc.
            'computational': []  # Planning, search, constraint satisfaction, etc.
        }
```

**Storage**:
```json
{
  "question_id": "mtbench_83_t2",
  "source_benchmark": "MT-Bench",
  "domain": "writing",
  "success_rate": 0.35,
  "difficulty_score": 0.65,

  "task_domain": "Creative Writing",
  "specific_task": "Limerick composition with AABBA rhyme scheme",
  "required_capabilities": [
    "Prosodic Reasoning",
    "Constraint Satisfaction",
    "Semantic Compression"
  ],

  "common_errors": [
    {
      "error_type": "Phonetic Similarity Modeling",
      "description": "Cannot represent rhyme patterns",
      "frequency": 0.8,
      "affected_models": ["alpaca-13b", "llama-13b"]
    }
  ],

  "systematic_failures": {
    "alpaca-13b": ["Prosodic Reasoning", "Constraint Satisfaction"],
    "llama-13b": ["Prosodic Reasoning"]
  }
}
```

#### Integration 4: MCP Server Enhancement

**Extend `togmal_mcp.py` with capability awareness**:

```python
# In togmal_mcp.py

class ToGMALServer:
    def __init__(self):
        self.vector_db = BenchmarkVectorDB()
        self.task_taxonomy = load_task_taxonomy()
        self.capability_assessor = CapabilityRiskAssessor(self.task_taxonomy, self)

    @server.tool()
    async def assess_prompt_with_capabilities(
        self,
        prompt: str,
        model: str = "default",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enhanced prompt assessment with capability analysis.

        Returns difficulty, safety risks, AND capability-based predictions.
        """
        # Existing difficulty assessment
        difficulty = self.vector_db.assess_difficulty(prompt)

        # Existing heuristic safety
        safety_risks = self.detect_risks(prompt, context)

        # NEW: Capability-based assessment
        capability_assessment = self.capability_assessor.assess_risk(
            prompt, model, context
        )

        # NEW: Mitigation suggestions
        mitigations = []
        for risk in capability_assessment:
            if risk['type'] == 'capability_gap':
                mitigations.append({
                    'risk': risk['description'],
                    'suggestions': [
                        f"Consider using a model strong in {risk['capability']}",
                        f"Break task into simpler sub-tasks",
                        f"Provide examples of {risk['capability']} in prompt"
                    ]
                })

        return {
            'difficulty': difficulty,
            'safety_risks': safety_risks,
            'capability_risks': capability_assessment,
            'mitigations': mitigations,
            'overall_risk': compute_overall_risk(
                difficulty, safety_risks, capability_assessment
            )
        }
```

---

## 4. Implementation Roadmap

### Week 1: Quality Infrastructure
- [ ] Implement evidence requirement validation
- [ ] Build inter-rater reliability system
- [ ] Create capability registry with definitions
- [ ] Set up consistency checks

### Week 2: Scale to Full MT-Bench
- [ ] Analyze all 80 questions systematically
- [ ] Run quality validation on all analyses
- [ ] Build comprehensive MT-Bench taxonomy
- [ ] Validate predictive accuracy

### Week 3: Multi-Benchmark Expansion
- [ ] Sample MMLU, HumanEval, MATH questions
- [ ] Analyze 500 representative cases
- [ ] Expand capability categories
- [ ] Cross-validate across benchmarks

### Week 4: ToGMAL Integration
- [ ] Extend BenchmarkVectorDB schema
- [ ] Implement capability-aware risk assessment
- [ ] Update MCP server with new tools
- [ ] Create unified query interface

### Week 5: Validation & Refinement
- [ ] Run predictive validation experiments
- [ ] Conduct human expert review
- [ ] Refine capability definitions
- [ ] Document final taxonomy

---

## 5. Success Metrics

### Coverage Metrics
- ✅ 80 MT-Bench questions analyzed
- ✅ 500+ cases across multiple benchmarks
- ✅ 20+ task domains identified
- ✅ 40+ capability categories defined

### Quality Metrics
- ✅ Inter-rater agreement >70%
- ✅ Predictive accuracy >60%
- ✅ Human expert agreement >75%
- ✅ Zero AI slop (all analyses have evidence)

### Integration Metrics
- ✅ ToGMAL MCP server using taxonomy
- ✅ Capability-based risk assessment live
- ✅ Unified benchmark database operational
- ✅ 5+ mitigation strategies per capability gap

### Impact Metrics
- ✅ Reduced false positives in risk detection
- ✅ Better model selection recommendations
- ✅ More actionable prompt improvement suggestions
- ✅ Faster identification of novel capability gaps

---

## 6. Anti-Slop Checklist

Before accepting any analysis:

- [ ] **Evidence**: Specific quotes from both responses
- [ ] **Specificity**: Capability name in established registry
- [ ] **Causality**: Error chain shows logical progression
- [ ] **Consistency**: Agrees with similar cases >70%
- [ ] **Predictive**: Can predict on held-out data
- [ ] **Grounded**: References cognitive science/linguistics literature
- [ ] **Testable**: Failure mode can be empirically validated

If any check fails → Flag for review or re-analysis.

---

This framework ensures the taxonomy grows systematically, maintains high quality, and integrates seamlessly with ToGMAL!
