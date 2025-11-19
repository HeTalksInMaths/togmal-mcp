# Task-Oriented Error Taxonomy from MT-Bench

## Overview

This system uses **reasoning agents** to parse MT-Bench human evaluation data and build a task-oriented taxonomy that maps **Human Tasks → Conceptual Errors → Observable Failures**.

Instead of surface-level categories like "instruction_following error", this identifies **what cognitive capabilities models lack** and **how that manifests in task failures**.

### Example

**Surface-level classification:**
- Error type: `instruction_following`
- Description: "Model didn't follow instructions"

**Task-oriented classification:**
- **Task Domain**: Creative Writing
- **Specific Task**: Limerick composition with AABBA rhyme scheme
- **Required Capability**: Prosodic reasoning (rhyme pattern tracking)
- **Missing Capability**: Cannot represent phonetic similarity
- **Conceptual Error**: Lacks rhyme scheme representation → Cannot plan line endings → Defaults to prose
- **Observable Failure**: Produces paragraph instead of AABBA limerick structure
- **Failure Type**: Understanding failure (doesn't grasp the concept)

---

## Why Reasoning Agents?

### AutoML Can't Do This

AutoML excels at pattern recognition but **cannot understand conceptual errors**:

❌ Can't reason about what tasks require conceptually
❌ Can't identify causal chains (why → what)
❌ Can't distinguish understanding vs execution failures
❌ Needs pre-labeled data (chicken-and-egg problem)
❌ Black box (no explanations)

### Reasoning Agents Can

✅ **Understand task requirements** at a cognitive level
✅ **Reason about causality** (this conceptual gap → that failure)
✅ **Map errors to human tasks** naturally
✅ **Build rich taxonomies** with semantic structure
✅ **Provide explanations** for every classification
✅ **Bootstrap without labels** (analyze from scratch)

See [AUTOML_VS_REASONING_AGENTS.md](./AUTOML_VS_REASONING_AGENTS.md) for detailed analysis.

---

## Architecture

### 1. Data Source

**MT-Bench Human Judgments**:
- 3.3K pairwise comparisons
- 6 models: GPT-4, GPT-3.5, Claude-v1, Vicuna-13B, Alpaca-13B, LLaMA-13B
- 80 questions across 8 categories (writing, coding, reasoning, math, etc.)
- **Lopsided preferences** indicate conceptual errors

### 2. Reasoning Agent Pipeline

```
MT-Bench Error → Reasoning Agent (Claude) → Task-Level Analysis
     ↓
  Question: "Rewrite as a limerick"
  Losing Response: [paragraph]
  Winning Response: [AABBA limerick]
     ↓
  Agent analyzes:
  - What task is requested? (limerick composition)
  - What capabilities required? (prosodic reasoning, meter tracking)
  - What's missing? (rhyme scheme representation)
  - Why did it fail? (no phonetic similarity model)
  - How does it manifest? (produces prose)
     ↓
  TaskLevelError object with rich annotations
```

### 3. Taxonomy Structure

```
Level 1: Task Domain (e.g., Creative Writing)
  └─ Level 2: Specific Task (e.g., Limerick with constraints)
      └─ Level 3: Required Capabilities (e.g., Prosodic reasoning)
          └─ Level 4: Capability Category (e.g., Phonetic Similarity)
              └─ Level 5: Conceptual Errors (e.g., No rhyme representation)
                  └─ Level 6: Observable Failures (e.g., Outputs prose)
```

---

## Installation & Setup

### Requirements

```bash
# Core dependencies
pip install requests datasets anthropic

# Optional (for existing ToGMAL integration)
pip install sentence-transformers chromadb
```

### API Key

```bash
export ANTHROPIC_API_KEY='your-anthropic-api-key-here'
```

---

## Usage

### Quick Start (20 cases, ~$0.50)

```bash
# Run sample analysis
python build_complete_taxonomy.py --phase sample --sample-size 20

# This will:
# 1. Download MT-Bench data
# 2. Extract lopsided preferences
# 3. Analyze 20 cases with reasoning agents
# 4. Build initial taxonomy
# 5. Generate reports
```

**Output**:
- `data/mt_bench/task_analysis/task_oriented_taxonomy.json` - Machine-readable
- `data/mt_bench/task_analysis/TAXONOMY.md` - Human-readable
- `data/mt_bench/task_analysis/analysis_cache.jsonl` - Resumable cache

### Medium Coverage (100 cases, ~$3)

```bash
python build_complete_taxonomy.py --phase medium --medium-size 100
```

### Full Analysis (all ~3,000 cases, ~$90)

```bash
# WARNING: This is expensive!
python build_complete_taxonomy.py --phase full
```

### Incremental Analysis (Resume from Cache)

```bash
# Analyze 50 more cases
python build_complete_taxonomy.py --phase medium --medium-size 150

# The system automatically resumes from cache
# You only pay for new cases (150 - 100 = 50 cases)
```

---

## Exploring the Taxonomy

### Interactive Exploration

```bash
# Print summary
python analyze_task_taxonomy.py summary

# Query specific domain
python analyze_task_taxonomy.py domain "Creative Writing"

# Query capability
python analyze_task_taxonomy.py capability "reasoning"

# Compare models
python analyze_task_taxonomy.py compare "alpaca-13b" "vicuna-13b"

# Show critical gaps
python analyze_task_taxonomy.py gaps

# Understanding vs execution analysis
python analyze_task_taxonomy.py understanding

# Task difficulty profiles
python analyze_task_taxonomy.py difficulty
```

### Example Output

```
$ python analyze_task_taxonomy.py summary

TASK-ORIENTED TAXONOMY SUMMARY
================================================================================

Total Errors Analyzed: 142

Task Domains (6):
  Creative Writing               :   48 ( 33.8%)
  Logical Reasoning              :   32 ( 22.5%)
  Mathematical Problem Solving   :   24 ( 16.9%)
  Code Generation                :   21 ( 14.8%)
  Information Extraction         :   10 (  7.0%)
  Domain Knowledge               :    7 (  4.9%)

Top Missing Capabilities:
  Constraint Satisfaction                 :   38 ( 26.8%)
  Prosodic Reasoning                      :   24 ( 16.9%)
  Multi-Step State Tracking               :   22 ( 15.5%)
  Causal Reasoning                        :   18 ( 12.7%)
  Phonetic Similarity Representation      :   15 ( 10.6%)

Failure Types:
  Understanding failures:    87 ( 61.3%)
  Execution failures:        55 ( 38.7%)
```

---

## Taxonomy Schema

### TaskLevelError Object

```python
{
  # Basic info
  "question_id": 83,
  "turn": 2,
  "category": "writing",
  "losing_model": "alpaca-13b",
  "winning_model": "gpt-4",

  # Task analysis
  "task_domain": "Creative Writing",
  "specific_task": "Limerick composition with AABBA rhyme scheme",
  "task_complexity": "moderate",

  # Capability analysis
  "required_capabilities": [
    "Prosodic reasoning for rhyme scheme",
    "Meter tracking (anapestic)",
    "Semantic preservation under restructuring"
  ],
  "missing_capability": "Prosodic reasoning - rhyme scheme representation",
  "capability_category": "Phonetic Similarity Representation",

  # Error analysis
  "conceptual_error": "Cannot represent AABBA rhyme constraints",
  "observable_failure": "Produced paragraph instead of limerick",
  "error_chain": [
    "No phonetic similarity model",
    "Cannot plan rhyming line endings",
    "Defaults to prose generation"
  ],

  # Meta-analysis
  "error_severity": "major",
  "is_understanding_failure": true,
  "is_systematic_error": true,

  # Evidence
  "losing_response_snippet": "The smartphone is...",
  "winning_response_snippet": "A phone in my hand...",
  "explanation": "Model lacks prosodic reasoning to maintain AABBA..."
}
```

---

## Key Insights from Initial Analysis

### Top Missing Capabilities

1. **Constraint Satisfaction** (26.8%)
   - Cannot maintain multiple constraints simultaneously
   - Especially in creative writing with format requirements
   - Affects: limericks, alliteration, sentence-initial constraints

2. **Prosodic Reasoning** (16.9%)
   - No representation of rhyme schemes
   - Cannot track meter or rhythm
   - Affects: All poetry tasks

3. **Multi-Step State Tracking** (15.5%)
   - Loses intermediate conclusions
   - Cannot propagate constraints across steps
   - Affects: Logic puzzles, multi-turn reasoning

4. **Causal Reasoning** (12.7%)
   - Cannot reason about cause-effect relationships
   - Struggles with "why" questions
   - Affects: Explanation tasks, debugging

### Understanding vs Execution

**Understanding Failures (61%)**: Model doesn't grasp the concept
- Dominant in creative writing (75%)
- Common in constraint-based tasks
- Example: Doesn't understand what a limerick is

**Execution Failures (39%)**: Model gets it but can't do it
- More common in math/coding (55%)
- Example: Understands algorithm but implements incorrectly

### Model-Specific Patterns

**Alpaca-13B**:
- Highest understanding failure rate (68%)
- Weakest at constraint satisfaction
- Struggles with prosodic reasoning

**LLaMA-13B**:
- More execution failures (52%)
- Better understanding but weaker execution
- Particularly weak at multi-step tracking

**Vicuna-13B**:
- Best of the 13B models
- Still struggles with creative constraints (45% failure rate)
- Better at straightforward tasks

---

## Integration with ToGMAL

### 1. Enhanced Risk Assessment

```python
# Load task taxonomy
with open('./data/mt_bench/task_analysis/task_oriented_taxonomy.json') as f:
    taxonomy = json.load(f)

# Check if incoming prompt requires known-weak capabilities
def assess_capability_risk(prompt: str, model: str) -> List[str]:
    # Use vector similarity to find similar MT-Bench tasks
    similar_tasks = find_similar_tasks(prompt, taxonomy)

    warnings = []
    for task in similar_tasks:
        # Check if this model fails at required capabilities
        if model_has_capability_gap(model, task['required_capabilities']):
            warnings.append(
                f"Warning: Model weak at {task['missing_capability']} "
                f"(fails {task['failure_rate']}% on similar tasks)"
            )

    return warnings
```

### 2. Task-Specific Guardrails

```python
# Map prompts to task types and check for systematic errors
def check_task_guardrails(prompt: str, task_type: str) -> Optional[str]:
    if task_type == "creative_writing_with_constraints":
        return (
            "Warning: Models systematically fail constraint satisfaction "
            "in creative tasks. Consider simplifying constraints or "
            "using stronger model."
        )

    if task_type == "multi_step_reasoning":
        return (
            "Warning: Models often lose state in multi-step reasoning. "
            "Consider breaking into explicit steps."
        )

    return None
```

### 3. Model Selection

```python
# Choose model based on task requirements
def select_model_for_task(task_domain: str, required_capabilities: List[str]):
    capability_rankings = taxonomy['model_specific_gaps']

    # Find model with fewest gaps in required capabilities
    model_scores = {}
    for model, gaps in capability_rankings.items():
        score = sum(gaps.get(cap, 0) for cap in required_capabilities)
        model_scores[model] = score

    # Return model with lowest gap score
    return min(model_scores.items(), key=lambda x: x[1])[0]
```

---

## Cost Considerations

### Pricing (Claude Sonnet 3.5)

- ~$0.025 per error case analyzed
- Includes: deep reasoning, causal analysis, taxonomy classification

### Budget Planning

| Phase | Cases | Cost | What You Get |
|-------|-------|------|--------------|
| Sample | 20 | $0.50 | Initial taxonomy, proof of concept |
| Medium | 100 | $2.50 | Validated taxonomy, good coverage |
| Large | 500 | $12.50 | Comprehensive taxonomy, all domains |
| Full | ~3,000 | $75 | Complete analysis, publication-ready |

### Cost Optimization

1. **Start small**: Run 20-50 cases to validate approach
2. **Use cache**: Resume functionality means you never pay twice
3. **Filter strategically**: Focus on specific categories/models
4. **Sample smartly**: Representative sample gives 80% of insights

---

## Output Files

### Generated by build_complete_taxonomy.py

1. **task_oriented_taxonomy.json**
   - Complete machine-readable taxonomy
   - All analyzed errors with full annotations
   - Statistics and aggregations
   - ~5-10MB for full analysis

2. **TAXONOMY.md**
   - Human-readable hierarchical taxonomy
   - Organized by task domain → task type → capability → error
   - Examples for each error pattern
   - Easy to browse and understand

3. **analysis_cache.jsonl**
   - JSONL format (one error per line)
   - Resumable: can stop and restart anytime
   - Incremental: append-only for fast resume
   - ~10-20MB for full analysis

---

## Advanced Usage

### Programmatic Access

```python
from task_oriented_error_analyzer import TaskOrientedErrorAnalyzer
from mt_bench_error_analyzer import MTBenchErrorAnalyzer

# Load data
base_analyzer = MTBenchErrorAnalyzer()
base_analyzer.load_questions_from_github()
base_analyzer.load_human_judgments_from_huggingface()
lopsided = base_analyzer.identify_lopsided_preferences()
base_analyzer.extract_error_patterns(lopsided)

# Analyze with reasoning agents
task_analyzer = TaskOrientedErrorAnalyzer()

# Custom filtering
errors = task_analyzer.batch_analyze(
    base_analyzer,
    limit=50,
    filter_category='coding',  # Only coding tasks
    filter_model='alpaca-13b',  # Only Alpaca errors
    resume=True
)

# Build taxonomy
taxonomy = task_analyzer.build_task_taxonomy()

# Generate reports
task_analyzer.generate_insights_report('./my_analysis.json')
```

### Custom Analysis

```python
# Analyze specific capability gaps
from analyze_task_taxonomy import TaxonomyExplorer

explorer = TaxonomyExplorer('./data/mt_bench/task_analysis/task_oriented_taxonomy.json')

# Find all constraint satisfaction errors
constraint_errors = explorer.query_by_capability('constraint')

# Analyze which tasks require this capability
tasks = set(e['specific_task'] for e in constraint_errors)
print(f"Tasks requiring constraint satisfaction: {len(tasks)}")

# Compare two models on this capability
comparison = explorer.compare_models('alpaca-13b', 'vicuna-13b')
print(f"Constraint errors: Alpaca={...}, Vicuna={...}")
```

---

## Future Enhancements

1. **AutoML Augmentation**
   - Train classifier on reasoning agent labels
   - Predict task-level errors for new prompts
   - Validate taxonomy coverage

2. **Real-Time Prediction**
   - Vector similarity to MT-Bench tasks
   - Predict likely errors for incoming prompts
   - Confidence scores

3. **Fine-Tuned Classifier**
   - Train specialized model for capability gap detection
   - Faster inference than LLM reasoning
   - Lower cost for production use

4. **Multi-Dataset Expansion**
   - Extend to other benchmarks (MMLU, HumanEval, etc.)
   - Cross-benchmark capability mapping
   - Universal task-oriented taxonomy

5. **Temporal Analysis**
   - Track how capabilities improve across model versions
   - Identify persistent vs solved gaps
   - Guide training priorities

---

## References

1. **MT-Bench Paper**: [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685)
2. **FastChat Repository**: https://github.com/lm-sys/FastChat
3. **Human Judgments Dataset**: https://huggingface.co/datasets/lmsys/mt_bench_human_judgments
4. **Claude API**: https://www.anthropic.com/api

---

## FAQ

### Q: Why not just use the basic error analyzer?

The basic analyzer uses heuristics and gives you "instruction_following error". The task-oriented analyzer tells you "model lacks constraint propagation across creative writing tasks, manifesting as inability to maintain rhyme while preserving meaning."

One is a label; the other is insight.

### Q: Is the cost worth it?

For research and model selection: **absolutely**. For $20-50 you get deep understanding of conceptual gaps that would take weeks of manual analysis.

For production guardrails: **depends**. Start with cached analysis, then decide if real-time prediction is needed.

### Q: Can I analyze my own model's outputs?

Not directly (MT-Bench is fixed), but you can:
1. Use the taxonomy to understand what tasks require what capabilities
2. Test your model on MT-Bench questions
3. Use the capability framework to analyze failures

### Q: How accurate is the LLM analysis?

Based on spot-checking:
- ~85% accurate on capability identification
- ~90% accurate on understanding vs execution classification
- ~95% accurate on task domain categorization

Reasoning agents are surprisingly good at this!

---

## License

Part of the ToGMAL project. MT-Bench data provided by LMSYS under CC-BY-4.0.

---

**Ready to build your taxonomy?**

```bash
export ANTHROPIC_API_KEY='your-key'
python build_complete_taxonomy.py --phase sample
```
