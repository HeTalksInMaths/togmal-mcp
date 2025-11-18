# Hierarchical Error Taxonomy for LLM Analysis

A comprehensive system for analyzing MMLU-Pro errors to understand **why** language models make mistakes and build a hierarchical taxonomy of conceptual errors.

## 🎯 Overview

This project implements a research-based framework for:
1. **Classifying** LLM errors into a hierarchical taxonomy
2. **Discovering** novel error patterns through clustering
3. **Analyzing** why models fail on specific question types
4. **Comparing** model error profiles to published baselines
5. **Recommending** targeted interventions for each error type

## 📊 Key Features

### 1. Hierarchical Error Taxonomy

Three-level taxonomy based on latest research:

**Level 1: Error Categories**
- Knowledge Deficits (35-58% of errors)
- Reasoning Failures (39% of errors)
- Execution Errors (12% of errors)
- Comprehension Errors
- Systematic Biases

**Level 2: Error Subtypes** (24 specific types)
- Factual gaps, domain blind spots, misconceptions
- Multi-step reasoning, counterfactual reasoning, quantitative reasoning
- Format errors, calculation errors
- Negation blindness, qualifier confusion
- Position bias, confidence miscalibration

**Level 3: Discovered Patterns**
- Automatically identified through clustering
- Domain-specific error signatures
- Cross-model systematic errors

### 2. Research-Based Analysis

Integrates findings from 2024 research papers:
- **MMLU-Pro Error Analysis** (Wang et al.) - 39% reasoning, 35% knowledge, 12% computational
- **"Are We Done with MMLU?"** (Koto et al.) - Dataset quality validation framework
- **Hierarchical Error Framework** (Li et al.) - Knowledge/reasoning/execution layers
- **Math Error Dataset** (Zhang et al.) - 304K real error examples
- **Bloom's Taxonomy** - Cognitive complexity classification

### 3. Advanced Analysis Tools

- **Dataset Quality Validation**: Detect ambiguous questions, bad options, mislabeled answers
- **Hierarchical Attribution**: Distinguish knowledge gaps from reasoning failures
- **Cognitive Complexity Scoring**: Classify by Bloom's taxonomy levels
- **Baseline Comparison**: Compare to GPT-4o performance on MMLU-Pro
- **Pattern Discovery**: Unsupervised clustering to find novel error types
- **Co-occurrence Analysis**: Find correlated errors across models/questions
- **Distractor Analysis**: Understand why wrong answers are attractive

### 4. Visualization & Reporting

- Interactive HTML dashboards
- Sunburst charts for taxonomy hierarchy
- Sankey diagrams for error flow
- Heatmaps for domain × error type distribution
- Model comparison charts
- Automated research reports

## 🏗️ Architecture

```
error_taxonomy.py              # Core taxonomy definitions and basic analysis
├── ErrorCategory, ErrorSubtype # Taxonomy enums
├── ErrorRecord                 # Individual error data structure
├── ErrorDetector              # Rule-based classification
├── ErrorAnalyzer              # Main analysis pipeline
└── ErrorCluster               # Pattern cluster representation

advanced_error_analysis.py     # Research-based enhancements
├── DatasetQualityValidator    # Validate question quality
├── HierarchicalErrorAnalyzer  # Multi-layer error attribution
├── CognitiveComplexityAnalyzer # Bloom's taxonomy classification
└── BaselineComparer           # Compare to published research

error_clustering.py            # Pattern discovery
├── ErrorPatternDiscovery      # Clustering algorithms
├── ErrorCooccurrenceAnalyzer  # Find correlated errors
├── DistractorAnalyzer         # Analyze wrong answer attraction
└── PatternExporter            # Export discovered patterns

error_visualization.py         # Visualization generation
├── ErrorTaxonomyVisualizer    # Generate chart data
└── generate_html_dashboard    # Interactive dashboards

demo_error_taxonomy.py         # Complete demonstration
```

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install numpy scikit-learn hdbscan sentence-transformers

# Optional: Install visualization dependencies
pip install plotly pandas
```

### Basic Usage

```python
from error_taxonomy import ErrorAnalyzer

# Load errors from MMLU-Pro benchmark data
analyzer = ErrorAnalyzer()
analyzer.load_errors_from_benchmark_data("data/benchmark_results/raw_benchmark_results.json")

# Classify errors
analyzer.classify_errors()

# Get summary statistics
stats = analyzer.get_error_summary_stats()
print(f"Total errors: {stats['total_errors']}")
print(f"By category: {stats['by_category']}")

# Build model profiles
for model_name in analyzer.get_models():
    profile = analyzer.build_model_profile(model_name)
    print(f"{model_name}: {profile.error_rate*100:.1f}% error rate")

# Generate taxonomy tree
tree = analyzer.generate_taxonomy_tree()

# Export results
analyzer.export_results("output/")
```

### Advanced Analysis

```python
from advanced_error_analysis import AdvancedErrorAnalyzer

advanced = AdvancedErrorAnalyzer()

# Comprehensive error analysis
for error in analyzer.errors[:10]:
    analysis = advanced.analyze_error_comprehensive(error)

    # Check dataset quality
    quality = analysis['dataset_quality']
    print(f"Question quality: {quality.issue_type.value}")

    # Hierarchical attribution
    hierarchical = analysis['hierarchical_analysis']
    print(f"Error layer: {hierarchical.primary_layer.value}")
    print(f"Interventions: {hierarchical.recommended_interventions}")

    # Cognitive complexity
    cognitive = analysis['cognitive_complexity']
    print(f"Cognitive level: {cognitive.cognitive_level.name}")

# Generate research report
report = advanced.generate_research_report(analyzer.errors, "model_name")
print(f"Comparison to GPT-4o: {report['comparison_to_gpt4o']}")
```

### Pattern Discovery

```python
from error_clustering import ErrorPatternDiscovery, ErrorCooccurrenceAnalyzer

discovery = ErrorPatternDiscovery()

# Cluster errors to find patterns
clusters = discovery.cluster_errors_hdbscan(analyzer.errors, min_cluster_size=5)

for cluster in clusters:
    print(f"{cluster.cluster_name}: {cluster.size} errors")
    print(f"  {cluster.cluster_description}")
    print(f"  Keywords: {[kw for kw, _ in cluster.common_keywords[:5]]}")

# Find correlated errors
cooccurrence = ErrorCooccurrenceAnalyzer()

# Questions that models fail together
correlated_questions = cooccurrence.find_correlated_questions(analyzer.errors)

# Models with similar error patterns
similar_models = cooccurrence.find_correlated_errors_across_models(analyzer.errors)
```

### Generate Visualizations

```python
from error_visualization import generate_all_visualizations

# Generate all visualizations
generate_all_visualizations(
    errors=analyzer.errors,
    clusters=clusters,
    model_profiles=analyzer.model_profiles,
    output_dir="visualizations/"
)

# Open visualizations/dashboard.html in browser
```

### Run Full Demo

```bash
python demo_error_taxonomy.py
```

This will run all analysis pipelines and generate comprehensive reports.

## 📈 Example Outputs

### Taxonomy Tree (JSON)

```json
{
  "name": "All LLM Errors",
  "value": 500,
  "children": [
    {
      "name": "Knowledge Deficit",
      "value": 175,
      "percentage": 35.0,
      "children": [
        {
          "name": "Factual Gap",
          "value": 82,
          "percentage": 46.8,
          "examples": [...]
        },
        {
          "name": "Domain Blind Spot",
          "value": 65,
          "percentage": 37.1
        }
      ]
    },
    {
      "name": "Reasoning Failure",
      "value": 195,
      "percentage": 39.0,
      "children": [...]
    }
  ]
}
```

### Error Cluster

```json
{
  "cluster_id": 3,
  "name": "Physics - Multi-step Reasoning",
  "description": "42 errors primarily in physics showing multi-step reasoning",
  "size": 42,
  "avg_difficulty": 0.73,
  "common_domains": {"physics": 35, "math": 7},
  "keywords": [
    ["velocity", 0.85],
    ["acceleration", 0.78],
    ["calculate", 0.72]
  ],
  "dominant_error_type": "multi_step_reasoning"
}
```

### Model Profile Comparison

```json
{
  "model": "meta-llama/Llama-3.1-70B",
  "error_rate": 0.42,
  "comparison_to_gpt4o": {
    "similar": false,
    "deviations": {
      "knowledge": +8.3,  // 8.3% more knowledge errors than GPT-4o
      "reasoning": -12.1, // 12.1% fewer reasoning errors
      "execution": +2.1
    }
  },
  "weakest_areas": ["quantum_physics", "legal_reasoning"],
  "strongest_areas": ["basic_math", "history"]
}
```

## 📚 Documentation

- **[ERROR_TAXONOMY_DESIGN.md](ERROR_TAXONOMY_DESIGN.md)** - Complete design document with implementation strategy
- **[RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md)** - Synthesis of 2024 research papers on LLM errors
- Code documentation in each module

## 🔬 Research Applications

### 1. Model Debugging
"Why does Model X struggle with quantum physics?"
→ Filter errors by model + domain → Cluster → Classify → Generate report

### 2. Dataset Quality Analysis
"Are there ambiguous/mislabeled questions?"
→ Find questions where all models fail → Analyze consensus → Flag for review

### 3. Intervention Design
"How can we improve reasoning on legal questions?"
→ Identify top error subtypes → Extract examples → Design targeted prompts

### 4. Novel Pattern Discovery
"What unexpected error patterns exist?"
→ Unsupervised clustering → Analyze clusters → Generate hypotheses → Validate

### 5. Comparative Analysis
"How do different model families compare?"
→ Build error profiles → Compare to baselines → Identify architecture-specific patterns

## 🎯 Key Research Questions

This framework enables investigation of:

1. **Universality**: Are certain error types universal across models, or architecture-specific?
2. **Difficulty Correlation**: Do harder questions produce different error types?
3. **Domain Specificity**: Are errors in law fundamentally different from errors in physics?
4. **Transfer Learning**: Can we predict errors on unseen questions based on similarity?
5. **Intervention Efficacy**: Do different interventions (CoT, RAG, tools) address specific error types?
6. **Evolution**: How do error profiles change across model generations?

## 📊 Comparison to Published Baselines

**GPT-4o on MMLU-Pro (Published Baseline)**:
- 39% Reasoning process flaws
- 35% Domain expertise gaps
- 12% Computational errors
- 14% Other

Our system automatically compares any model's error distribution to this baseline and identifies deviations.

## 🛠️ Next Steps

### Immediate (Week 1)
- [ ] Populate actual model answers (not just correct/incorrect flags)
- [ ] Expand to full MMLU-Pro dataset (12,000 questions vs. current 500)
- [ ] Run analysis on 5+ models (Llama, Qwen, Mixtral, GPT-4, Claude)

### Short-term (Week 2-4)
- [ ] Implement LLM-assisted classification for deeper error understanding
- [ ] Add chain-of-thought analysis (where did reasoning break down?)
- [ ] Create interactive exploration dashboard
- [ ] Validate findings with human expert review

### Long-term (Month 2-3)
- [ ] Cross-benchmark analysis (MMLU-Pro + GPQA + MATH)
- [ ] Temporal analysis across model generations
- [ ] Build error prediction system (predict which questions will fail)
- [ ] Design and test interventions targeting specific error types
- [ ] Write research paper on findings

## 🤝 Contributing

This is a research prototype. Contributions welcome:
- Additional error detection rules
- New clustering algorithms
- Visualization improvements
- Integration with other benchmarks
- Validation studies

## 📄 Citation

If you use this framework in your research:

```bibtex
@misc{llm-error-taxonomy-2024,
  title={Hierarchical Error Taxonomy for Large Language Models},
  author={[Your Name]},
  year={2024},
  note={Research framework for analyzing MMLU-Pro errors}
}
```

## 🔗 Related Research

Based on and extends:
- Wang et al. (2024) - MMLU-Pro: A More Robust and Challenging Multi-Task Language Understanding Benchmark
- Koto et al. (2024) - Are We Done with MMLU?
- Li et al. (2024) - A Hierarchical Error Framework for Reliable Automated Coding
- Zhang et al. (2024) - Error Classification of Large Language Models on Math Word Problems

See [RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md) for detailed analysis.

## 📧 Contact

For questions or collaboration: [Your Contact Info]

---

**Status**: Research prototype - Active development

**License**: MIT (or your chosen license)

**Last Updated**: 2024
