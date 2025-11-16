---
title: ToGMAL Risk Assessment
description: Assess LLM failure risk using empirical benchmark data and error patterns
tags: [llm-limitations, risk-assessment, benchmarks, error-patterns]
version: 2.0.0
---

# ToGMAL Risk Assessment Skill

## Purpose

This skill teaches Claude how to assess the risk of LLM failure for user prompts by comparing against empirical benchmark data. It uses data from the ToGMAL MCP server (which provides access to 13,000 benchmark questions with real model performance data and 32 discovered error patterns).

**Architecture:**
- **MCP (togmal-mcp)**: Provides DATA (benchmark questions, error patterns, statistics)
- **This Skill**: Provides ANALYSIS PROCEDURES (how to assess risk, interpret patterns, warn users)

## Core Methodology

### 1. Two-Dimensional Risk Assessment

Assess risk along two dimensions:

#### A. Question Difficulty (Success Rate Analysis)
- Query similar questions by domain/topic
- Analyze historical success rates across models
- Consider difficulty distribution

#### B. Error Pattern Detection
- Check for known failure patterns (32 total patterns from 4 sources)
- Evaluate pattern severity (CRITICAL > HIGH > MEDIUM > LOW)
- Consider error pattern frequency in dataset

### 2. Risk Levels

Combine both dimensions to assign overall risk:

- **CRITICAL**: Universal failures (ALL models fail) OR multiple CRITICAL error patterns detected
- **HIGH**: Success rate < 30% OR 1+ CRITICAL pattern OR multiple HIGH patterns
- **MEDIUM**: Success rate 30-60% OR 1+ HIGH/MEDIUM pattern
- **LOW**: Success rate 60-80% OR only LOW severity patterns
- **MINIMAL**: Success rate > 80% AND no significant patterns detected

## Analysis Procedure

When user asks you to analyze a prompt or assess risk, follow these steps:

### Step 1: Understand the User's Task

Extract:
- **Domain**: What field? (math, coding, physics, etc.)
- **Task type**: What are they asking? (calculation, code generation, reasoning, etc.)
- **Complexity indicators**: Multi-step? Specialized knowledge? Precision required?

### Step 2: Query Relevant Benchmark Data

Use the ToGMAL MCP to fetch relevant data:

```
1. Get statistics overview:
   Tool: get_statistics
   Purpose: Understand dataset coverage

2. Search by domain:
   Tool: search_by_domain
   Arguments: {domain: <extracted_domain>, limit: 20}
   Purpose: Find similar questions in same domain

3. Query by difficulty (if task seems hard):
   Tool: query_questions
   Arguments: {difficulty: "Hard" or "Expert" or "Nearly_Impossible", limit: 10}
   Purpose: Find historically difficult questions

4. Get error patterns catalog:
   Tool: get_error_patterns_catalog
   Purpose: Understand known failure modes
```

### Step 3: Analyze Retrieved Data

For each dimension:

**A. Difficulty Analysis:**
1. Calculate average success rate of similar questions
2. Identify lowest-performing questions in domain
3. Check if any universal failures exist in domain
4. Note difficulty distribution (mostly Easy vs mostly Expert)

**B. Pattern Analysis:**
1. Review error patterns catalog for relevant patterns
2. Match user's prompt against pattern descriptions:
   - **DS-1000 patterns**: If coding (especially pandas/numpy):
     - mutability_misunderstanding: Missing .copy()?
     - index_persistence: Missing .reset_index()?
     - vectorization_concept: Using for-loops?
     - transformation_pipelines: Multi-step incomplete?
   - **Universal failure patterns**: If question matches "always fails" type
   - **CoT failure patterns**: If complex unit conversions or ambiguous
   - **ML-discovered patterns**: If in dangerous domains (coding, medicine)
3. Assess severity of matched patterns
4. Count pattern instances in dataset (frequency = reliability)

### Step 4: Compute Overall Risk Score

Use this decision tree:

```
IF universal_failure OR multiple CRITICAL patterns:
    RISK = CRITICAL
ELSE IF success_rate < 30% OR 1+ CRITICAL pattern:
    RISK = HIGH
ELSE IF success_rate < 60% OR 1+ HIGH/MEDIUM pattern:
    RISK = MEDIUM
ELSE IF success_rate < 80% OR LOW severity patterns:
    RISK = LOW
ELSE:
    RISK = MINIMAL
```

### Step 5: Generate Risk Report

Structure your response as:

```markdown
## ToGMAL Risk Assessment

### Task Analysis
- Domain: [extracted domain]
- Task Type: [what user is asking]
- Complexity: [simple/moderate/complex]

### Benchmark Data
- Similar Questions Analyzed: [N]
- Average Success Rate: [X%]
- Difficulty Distribution: [breakdown]
- Universal Failures: [Y/N]

### Error Pattern Analysis
[List matched patterns with:]
- Pattern: [name]
- Source: [ds1000/universal_failure/cot_failure/ml_discovered]
- Severity: [CRITICAL/HIGH/MEDIUM/LOW]
- Frequency: [count in dataset]
- Description: [why this matters]
- Evidence: [supporting data]

### Overall Risk Assessment
**RISK LEVEL: [CRITICAL/HIGH/MEDIUM/LOW/MINIMAL]**

[Explanation of risk level based on both dimensions]

### Recommendations
[Based on risk level:]

CRITICAL/HIGH:
- ⚠️ High failure risk detected
- Strongly recommend: [specific mitigations]
- Consider: Breaking into smaller steps, using tools, human verification
- Alternative approaches: [suggestions]

MEDIUM:
- ⚠️ Moderate risk
- Recommend: [mitigations]
- Monitor for: [specific issues]

LOW/MINIMAL:
- ✅ Low risk
- Proceed with normal caution
- Watch for: [minor considerations]
```

## Error Pattern Reference Guide

### DS-1000 Code Patterns (8 patterns)

Use when user prompt involves pandas/numpy code:

1. **mutability_misunderstanding** (CRITICAL, 3,247 cases)
   - Look for: DataFrame modifications without .copy()
   - Warning: "Original data may be modified unintentionally"
   - Fix: "Use df.copy() before modifications"

2. **index_persistence** (CRITICAL, 1,856 cases)
   - Look for: groupby() operations without .reset_index()
   - Warning: "Index may cause unexpected behavior"
   - Fix: "Add .reset_index() after groupby"

3. **vectorization_concept** (CRITICAL, 1,423 cases)
   - Look for: for-loops over DataFrames
   - Warning: "Performance issues and incorrect patterns"
   - Fix: "Use vectorized operations (.apply(), .map(), etc.)"

4. **transformation_pipelines** (CRITICAL, 892 cases)
   - Look for: Multi-step transformations
   - Warning: "Incomplete pipeline steps"
   - Fix: "Ensure all transformation steps are included"

5. **method_semantics** (CRITICAL, 634 cases)
   - Look for: Incorrect method choice
   - Warning: "Wrong method for task"
   - Fix: "Use correct method (e.g., .replace() vs .apply())"

6. **dimensional_operations** (MEDIUM, 487 cases)
   - Look for: Operations without axis parameter
   - Warning: "Missing or wrong axis"
   - Fix: "Specify axis=0 or axis=1"

7. **api_evolution** (MEDIUM, 276 cases)
   - Look for: .values usage
   - Warning: "Deprecated method"
   - Fix: "Use .to_numpy() instead of .values"

8. **indexing_semantics** (HIGH, 125 cases)
   - Look for: .loc vs .iloc confusion
   - Warning: "Wrong indexing method"
   - Fix: "Use .loc for labels, .iloc for positions"

### Universal Failure Patterns (20 patterns)

Use when:
- Question involves ALL models failing (22 questions in dataset)
- Characteristics: Complex engineering, multi-system unit conversions, specialized knowledge
- Risk: CRITICAL
- Recommendation: "This type of question has 0% historical success rate across 37 models"

### CoT Failure Patterns (2 patterns)

1. **Complex unit conversion requirements** (CRITICAL, 148 cases)
   - Look for: Multiple unit systems (5+ different units)
   - Examples: Engineering problems with lbs, inches, BTU, etc.
   - Risk: Models struggle with multi-step dimensional analysis
   - Fix: "Break into single-unit-system steps, provide conversion factors"

2. **Ambiguous or truncated questions** (HIGH, 2 cases)
   - Look for: Incomplete information, unclear requirements
   - Risk: Cannot reason correctly without full context
   - Fix: "Clarify requirements, provide complete information"

### ML-Discovered Dangerous Clusters (2 patterns)

1. **Coding cluster** (HIGH confidence, 497 questions)
   - Domain: Coding/programming questions
   - Risk: 100% limitation/harmful rate
   - Recommendation: "Exercise extreme caution, verify all code"

2. **Medicine cluster** (HIGH confidence, 491 questions)
   - Domain: Medical/health questions
   - Risk: 100% limitation/harmful rate
   - Recommendation: "Defer to medical professionals, do not provide medical advice"

## Example Workflows

### Example 1: User asks for pandas code

```
User: "Filter a DataFrame where column A > 10 and reset the index"

Step 1: Extract - Domain: Data Science (Pandas), Task: DataFrame filtering

Step 2: Query MCP
- search_by_domain(domain="Pandas", limit=20)
- get_error_patterns_catalog()

Step 3: Analyze
- Found 291 Pandas questions, avg success rate 62%
- Detected pattern match: "index_persistence" (user mentioned "reset index")
- Detected pattern: "transformation_pipelines" (multi-step: filter + reset)

Step 4: Risk = MEDIUM (success rate 62%, but user IS using .reset_index() correctly)

Step 5: Report
"✅ MEDIUM-LOW risk. You're correctly using .reset_index(). Watch for:
- DataFrame mutability (consider using .copy())
- Ensure filter condition uses vectorized comparison"
```

### Example 2: User asks about complex physics

```
User: "Calculate the partition function for a 3D quantum harmonic oscillator with thermal corrections"

Step 1: Extract - Domain: Physics (Quantum), Task: Complex calculation

Step 2: Query MCP
- search_by_domain(domain="physics", limit=20)
- query_questions(difficulty="Expert", limit=10)
- get_universal_failures(limit=10)

Step 3: Analyze
- Physics domain avg success rate: 45%
- Expert-level physics questions: 23% success rate
- Similar quantum mechanics questions found with 15-30% success rates
- No exact pattern match, but high complexity

Step 4: Risk = HIGH (success rate < 30%)

Step 5: Report
"⚠️ HIGH risk. Similar quantum physics questions show 15-30% success rates.
Recommendations:
- Break calculation into steps (partition function → quantum states → thermal correction)
- Verify each step independently
- Use computational tools (SymPy, SciPy) for numerical validation
- Consider consulting physics references for formula verification"
```

### Example 3: User asks about medical diagnosis

```
User: "Based on these symptoms, what disease does the patient have?"

Step 1: Extract - Domain: Medicine, Task: Diagnosis

Step 2: Query MCP
- search_by_domain(domain="health", limit=20)
- get_error_patterns_catalog()

Step 3: Analyze
- Found ML-discovered pattern: "Medicine cluster" (491 questions, 100% limitation rate)
- This is a dangerous domain

Step 4: Risk = CRITICAL (ML-discovered dangerous cluster)

Step 5: Report
"🛑 CRITICAL risk. Medical diagnosis questions are in a dangerous cluster with 100% limitation rate.
STRONG RECOMMENDATION:
- Do NOT provide medical diagnosis
- Defer to qualified medical professionals
- Suggest: Consult with doctor, get proper medical evaluation
- I can only provide general educational information, not diagnoses"
```

## Integration with MCP

This skill works in conjunction with the ToGMAL MCP server. Always:

1. **Use MCP for data** - Never make up statistics or patterns
2. **Use this Skill for analysis** - Apply the procedures defined here
3. **Cite sources** - Reference MCP data in your reports ("Based on 291 Pandas questions in dataset...")
4. **Be transparent** - Explain your reasoning and data sources

## Key Principles

1. **Empirical over theoretical**: Use real benchmark data, not assumptions
2. **Multi-dimensional**: Consider both success rates AND error patterns
3. **Severity-weighted**: CRITICAL patterns override moderate success rates
4. **Evidence-based**: Every warning should cite specific data
5. **Actionable**: Provide concrete recommendations, not just warnings
6. **Transparent**: Explain limitations of the assessment

## Limitations

Be upfront about:
- Dataset size (13,000 questions may not cover all domains equally)
- Model coverage (37-68 models, but may not include user's specific model)
- Pattern completeness (32 patterns discovered, but not exhaustive)
- Context differences (benchmark questions may differ from user's specific task)

Always mention: "This assessment is based on historical benchmark data and may not perfectly predict your specific case."
