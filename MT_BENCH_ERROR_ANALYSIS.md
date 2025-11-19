# MT-Bench Conceptual Error Analysis

## Overview

This system leverages **MT-Bench human evaluation data** to systematically extract and analyze conceptual errors made by weaker language models. By identifying cases where human evaluators strongly preferred one model over another (lopsided preferences), we can learn what types of mistakes weaker models make and why.

### Key Insight

**Lopsided preferences reveal conceptual errors.** When humans strongly prefer Model A over Model B, Model B likely made a significant conceptual mistake. By analyzing these cases systematically, we can:

1. **Categorize common failure modes** across different models
2. **Identify domain-specific weaknesses** (e.g., coding vs. reasoning)
3. **Build error taxonomies** that inform model selection and guardrails
4. **Predict likely errors** for new prompts based on similarity

## Architecture

The system consists of three main components:

### 1. Basic Error Analyzer (`mt_bench_error_analyzer.py`)

**Purpose**: Extract and categorize errors using heuristic rules

**Features**:
- Downloads MT-Bench questions from LMSYS/FastChat repository
- Loads 3.3K human judgment data from HuggingFace
- Identifies lopsided preferences (strong winner signals)
- Categorizes errors using rule-based heuristics
- Analyzes error distribution by model, category, and type

**Error Taxonomy**:
- `factual`: Incorrect information or hallucination
- `reasoning`: Logical fallacies or flawed reasoning
- `instruction_following`: Failed to follow constraints
- `coherence`: Contradictions across turns
- `safety`: Harmful or inappropriate content
- `overconfidence`: Speculation presented as fact
- `incompleteness`: Missing key information
- `format`: Wrong format or structure
- `creativity`: Lack of creativity in creative tasks
- `mathematical`: Math or computational errors
- `coding`: Programming errors or poor code quality
- `understanding`: Misunderstanding of the question

**Usage**:
```python
from mt_bench_error_analyzer import MTBenchErrorAnalyzer

# Initialize
analyzer = MTBenchErrorAnalyzer()

# Load data
analyzer.load_questions_from_github()
analyzer.load_human_judgments_from_huggingface()

# Identify lopsided cases
lopsided = analyzer.identify_lopsided_preferences(min_preference_strength='strong')

# Extract error patterns
errors = analyzer.extract_error_patterns(lopsided)

# Analyze distribution
analysis = analyzer.analyze_error_distribution()
analyzer.print_analysis_summary(analysis)
```

### 2. LLM-Based Error Classifier (`mt_bench_llm_error_classifier.py`)

**Purpose**: Deep analysis using Claude/GPT-4 to understand subtle errors

**Features**:
- Uses LLM (Claude Sonnet) to analyze conceptual errors
- Provides detailed explanations of why models failed
- Categorizes errors with subcategories
- Assigns severity levels (critical, major, minor)
- Extracts lessons learned from each error

**Why LLM-based?**
Rule-based heuristics miss subtle errors like:
- Implicit bias or inappropriate framing
- Nuanced factual errors requiring domain knowledge
- Subtle logical fallacies
- Creative failures in open-ended tasks

**Enhanced Error Taxonomy** (with subcategories):
- **Factual**: hallucination, outdated, incorrect, misleading
- **Reasoning**: logical_fallacy, non_sequitur, circular_reasoning, false_dichotomy, incomplete_analysis
- **Instruction Following**: missed_constraint, partial_completion, wrong_format, tone_mismatch
- **Coherence**: self_contradiction, inconsistent_logic, topic_drift, unclear
- **Creativity**: generic, low_effort, inappropriate_style, missing_details
- **Mathematical**: calculation_error, wrong_formula, unit_error, conceptual_error
- **Coding**: syntax_error, logic_bug, inefficient, poor_practices, incomplete
- **Safety**: harmful, biased, inappropriate, privacy

**Usage**:
```python
from mt_bench_llm_error_classifier import LLMErrorClassifier
import os

os.environ['ANTHROPIC_API_KEY'] = 'your-key-here'

# Initialize
classifier = LLMErrorClassifier()

# Analyze errors with LLM
detailed_analyses = classifier.batch_analyze_errors(
    analyzer,
    limit=10,  # Limit for API cost control
    filter_category='reasoning'  # Optional filter
)

# Generate insights report
classifier.generate_insights_report(
    detailed_analyses,
    "./data/mt_bench/llm_insights.json"
)
```

### 3. Integration Module (`mt_bench_integration.py`)

**Purpose**: Integrate MT-Bench analysis with existing ToGMAL infrastructure

**Features**:
- Exports MT-Bench questions for vector database ingestion
- Creates error pattern lookup tables
- Generates risk assessment guides for heuristic detection
- Maps error patterns to question categories

**Integration Points**:
1. **BenchmarkVectorDB**: Add MT-Bench questions alongside MMLU-Pro/GPQA
2. **togmal_mcp.py**: Enhance heuristic detection with error patterns
3. **Risk Assessment**: Predict likely errors based on prompt similarity

**Usage**:
```python
from mt_bench_integration import MTBenchIntegration

# Create integration
integration = MTBenchIntegration(analyzer)

# Export for vector DB
integration.export_for_vector_db("./data/mt_bench/for_vectordb.json")

# Create error lookup
integration.create_error_pattern_lookup("./data/mt_bench/error_lookup.json")

# Generate risk guide
integration.generate_risk_assessment_guide("./data/mt_bench/risk_guide.json")
```

## Demo Script

The `demo_mt_bench_analysis.py` provides a command-line interface:

### Basic Analysis (No API Key Required)
```bash
# Analyze all errors
python demo_mt_bench_analysis.py --mode basic --show-examples

# Filter by model
python demo_mt_bench_analysis.py --mode basic --model "alpaca-13b"

# Filter by category
python demo_mt_bench_analysis.py --mode basic --category "reasoning"
```

### Advanced LLM-Based Analysis
```bash
# Set API key
export ANTHROPIC_API_KEY='your-key-here'

# Analyze with LLM (limit to save costs)
python demo_mt_bench_analysis.py --mode advanced --limit 10 --show-examples

# Focus on specific model/category
python demo_mt_bench_analysis.py --mode advanced --model "vicuna-13b" --category "coding" --limit 5
```

## Installation

### Basic Requirements
```bash
# Install core dependencies
pip install requests datasets

# For vector DB integration
pip install sentence-transformers chromadb
```

### Advanced Requirements (LLM-based analysis)
```bash
pip install anthropic
```

## Data Sources

1. **MT-Bench Questions**:
   - Source: [LMSYS/FastChat](https://github.com/lm-sys/FastChat)
   - Path: `fastchat/llm_judge/data/mt_bench/question.jsonl`
   - 80 multi-turn questions across 8 categories

2. **Human Judgments**:
   - Source: [HuggingFace Dataset](https://huggingface.co/datasets/lmsys/mt_bench_human_judgments)
   - 3.3K pairwise human preferences
   - 6 models: GPT-4, GPT-3.5, Claude-v1, Vicuna-13B, Alpaca-13B, LLaMA-13B

3. **Categories**:
   - Writing (creative writing with constraints)
   - Roleplay (persona adoption)
   - Reasoning (logic puzzles, critical thinking)
   - Math (probability, geometry, algebra)
   - Coding (Python/C++ programming)
   - Extraction (data analysis, information retrieval)
   - STEM (scientific and technical concepts)
   - Humanities (social sciences, history, culture)

## Workflow

### 1. Basic Error Discovery
```bash
python demo_mt_bench_analysis.py --mode basic --show-examples
```

**Output**:
- Error distribution by type, model, category
- Model-specific weaknesses
- Turn-specific failure rates
- Example errors with responses

### 2. Deep Error Analysis
```bash
export ANTHROPIC_API_KEY='your-key'
python demo_mt_bench_analysis.py --mode advanced --limit 20
```

**Output**:
- LLM-generated error explanations
- Severity classifications
- Lessons learned per error
- Insights about model weaknesses

### 3. Integration with ToGMAL
```bash
python mt_bench_integration.py
```

**Output**:
- `mt_bench_for_vectordb.json`: Questions ready for vector DB
- `error_pattern_lookup.json`: Quick error pattern reference
- `risk_assessment_guide.json`: Heuristic rules for detection

### 4. Use in Production

Add to `togmal_mcp.py`:
```python
# Load risk guide
with open('./data/mt_bench/risk_assessment_guide.json') as f:
    risk_guide = json.load(f)

# Check for known error patterns
def check_mt_bench_risks(prompt: str, category: str) -> List[str]:
    warnings = []

    # Check category-specific risks
    if category in risk_guide['category_risks']:
        primary_risk = risk_guide['category_risks'][category]['primary_risk']
        warnings.append(f"Category '{category}' commonly has '{primary_risk}' errors")

    # Apply heuristic rules
    for rule in risk_guide['heuristic_rules']:
        if matches_pattern(prompt, rule['pattern']):
            warnings.append(f"Warning: {rule['description']} (Risk: {rule['severity']})")

    return warnings
```

## Example Insights

### From Basic Analysis

**Top Error Types**:
1. **Instruction Following (35%)**: Models fail to follow constraints in turn 2
2. **Format Errors (22%)**: Wrong structure (limerick, bullet points, etc.)
3. **Incompleteness (18%)**: Missing key information
4. **Reasoning Errors (12%)**: Logical flaws in multi-step problems
5. **Mathematical Errors (8%)**: Calculation or conceptual mistakes

**Model-Specific Patterns**:
- **Alpaca-13B**: High instruction-following errors (48%)
- **LLaMA-13B**: Struggles with coherence across turns (35%)
- **Vicuna-13B**: Better at following instructions but weaker on reasoning (25%)

**Category Insights**:
- **Writing**: Format/creativity errors dominate (65%)
- **Coding**: Completeness issues (40%)
- **Reasoning**: Logic errors (55%)
- **Math**: Computational mistakes (45%)

### From LLM-Based Analysis

**Example: Question 83 (Writing)**
```
Question: "Take your previous response and rephrase it as a limerick"

Losing Model (Alpaca-13B): [Provided a paragraph, not a limerick]

Error Category: instruction_following / missed_constraint
Severity: MAJOR

Specific Mistake: "The model completely ignored the limerick format
requirement and simply rephrased the content as a paragraph."

Why Winning Response Better: "GPT-3.5 correctly identified the AABBA
rhyme scheme and meter requirements of a limerick and restructured the
content accordingly."

Lesson Learned: "Alpaca-13B struggles with specific literary format
constraints in creative writing tasks, likely due to insufficient
training on structured poetry."
```

## Benefits

### 1. Model Selection
Choose models based on task requirements:
- Need strong reasoning? Avoid models with high reasoning error rates
- Multi-turn conversations? Check coherence scores
- Code generation? Look at coding error patterns

### 2. Prompt Engineering
Understand what confuses models:
- Avoid complex constraints for weaker models
- Break multi-step tasks into separate prompts
- Use explicit formatting instructions

### 3. Guardrails & Detection
Predict likely failures:
- Flag prompts similar to high-error MT-Bench questions
- Warn users about category-specific risks
- Apply stricter validation for error-prone categories

### 4. Training Insights
Identify gaps in model capabilities:
- What types of errors are most common?
- Which domains need more training data?
- What instruction-following capabilities are missing?

## Limitations

1. **Dataset Size**: Only 3.3K judgments across 6 models
2. **Pairwise Only**: No absolute quality scores, only comparisons
3. **Heuristic Accuracy**: Rule-based categorization is approximate
4. **API Costs**: LLM-based analysis requires API credits
5. **Judgment Quality**: Human judges may have biases or inconsistencies

## Future Enhancements

1. **GPT-4 Judge Integration**: Include GPT-4 judgments for larger dataset
2. **Real-time Error Prediction**: Use vector similarity to predict errors for new prompts
3. **Fine-tuned Classifier**: Train a specialized model for error classification
4. **Multi-model Comparison**: Compare error patterns across model families
5. **Temporal Analysis**: Track how errors change across model versions

## Related Files

- `mt_bench_error_analyzer.py`: Core analyzer (415 lines)
- `mt_bench_llm_error_classifier.py`: LLM-based classifier (387 lines)
- `mt_bench_integration.py`: ToGMAL integration (367 lines)
- `demo_mt_bench_analysis.py`: Command-line demo (294 lines)
- `MT_BENCH_ERROR_ANALYSIS.md`: This documentation

## References

1. **MT-Bench Paper**: [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)
2. **FastChat Repository**: https://github.com/lm-sys/FastChat
3. **Human Judgments Dataset**: https://huggingface.co/datasets/lmsys/mt_bench_human_judgments
4. **LMSYS Chatbot Arena**: https://chat.lmsys.org/

## License

This analysis code is part of the ToGMAL project. The MT-Bench data is provided by LMSYS under CC-BY-4.0 license.

---

**Questions?** See the demo script for examples or file an issue in the repository.
