# Additional ML/DS Benchmarks: Availability and Analysis Potential

**Date**: November 15, 2025
**Benchmarks Surveyed**: ML-Bench, MLE-bench, DS-Bench, DataSciBench, RE-Bench
**Comparison with**: DS-1000 (already analyzed)

---

## Executive Summary

We identified **5 additional benchmarks** for ML/DS code generation. Here's the quick assessment for ToGMAL integration:

| Benchmark | Model Outputs Available? | Best For | Complexity vs DS-1000 | Recommendation |
|-----------|-------------------------|----------|----------------------|----------------|
| **ML-Bench** | ✅ YES (in repo) | Repository-level ML tasks | More complex | **HIGH PRIORITY** |
| **MLE-bench** | ✅ YES (agent runs) | Kaggle competitions | Much more complex | **HIGH PRIORITY** |
| **DataSciBench** | ✅ YES (evaluation results) | Multi-step data science | More complex | **MEDIUM PRIORITY** |
| **DS-Bench/DSCodeBench** | ❌ Framework only | Realistic DS tasks | More complex | Low priority (no outputs) |
| **RE-Bench** | ❌ Protected | AI R&D capabilities | Much more complex | Low priority (protected) |

**Top Recommendation**: **ML-Bench** - Has model outputs, repository-level tasks, similar scope to DS-1000 but more realistic.

---

## Detailed Benchmark Analysis

---

## 1. ML-Bench ⭐ HIGH PRIORITY

**Official Name**: ML-Bench: Evaluating Large Language Models and Agents for Machine Learning Tasks on Repository-Level Code

**Source**: Gerstein Lab (Yale University)
**Paper**: https://arxiv.org/abs/2311.09835
**GitHub**: https://github.com/gersteinlab/ML-Bench
**Data**: ✅ **Model outputs available in `output/` folder**

### Dataset Overview

**Size**: 9,641 examples across 169 distinct tasks
**Source**: 18 GitHub repositories
**Libraries**: Real-world ML repositories (TensorFlow, PyTorch, Scikit-learn, etc.)

**Task Types**:
- Code generation from user specifications
- Repository-level code understanding
- Documentation-aware implementation
- Argument handling and API usage

### Model Performance

| Model | Pass@5 (ML-LLM-Bench) | Success Rate (ML-Agent-Bench) |
|-------|----------------------|-------------------------------|
| GPT-4o | >50% | 76.47% |
| GPT-4 | 33.82% | - |
| CodeLlama-7b | Available | Available |

### What Makes It Different from DS-1000

**DS-1000**:
- Single-function problems
- Isolated library usage
- StackOverflow-style questions
- 1,000 problems

**ML-Bench**:
- Repository-level tasks (understand existing codebase)
- Multi-file context
- Real-world ML projects
- 9,641 examples (9.6x larger!)
- Requires documentation understanding

### Complexity Comparison

```
DS-1000:      ⭐⭐ (Basic - single function)
ML-Bench:     ⭐⭐⭐⭐ (Advanced - repository-level)
```

### Available for Analysis

✅ **YES** - Model outputs available in repository

**Output Format**: JSONL files with model-generated code
- `{{MODEL_NAME}}_{{TASK}}_results_{{TIMESTAMP}}.jsonl`
- Includes GPT-3.5-turbo-16k, GPT-4, CodeLlama-7b outputs

### Analysis Potential for ToGMAL

**High Value**:
1. **Repository-level errors**: New error types beyond single-function
2. **Context understanding**: Models must understand existing code
3. **Multi-file coordination**: Import errors, dependency issues
4. **Documentation adherence**: Using APIs according to docs
5. **Larger dataset**: 9.6x more examples than DS-1000

**Conceptual Errors We Could Discover**:
- `codebase_navigation` - Can't find relevant code in repository
- `import_resolution` - Wrong imports or missing dependencies
- `api_documentation_adherence` - Ignores documented constraints
- `multi_file_consistency` - Changes break other files
- `context_window_limits` - Misses critical code outside immediate context

**Recommendation**: **Download and analyze immediately** - this is the most direct upgrade from DS-1000.

---

## 2. MLE-bench ⭐ HIGH PRIORITY

**Official Name**: MLE-bench: Evaluating Machine Learning Agents on Machine Learning Engineering

**Source**: OpenAI
**Paper**: https://arxiv.org/pdf/2410.07095
**GitHub**: https://github.com/openai/mle-bench
**Data**: ✅ **Agent submissions and evaluation results available**

### Dataset Overview

**Size**: 75 Kaggle competitions
**Complexity**: 22 Low (30%), 38 Medium (50%), 15 High (20%)
**Task**: Complete end-to-end ML pipeline for competition

**Real-World Grading**: Submissions compared against actual Kaggle leaderboards

### Model Performance

| Agent | Medal Rate (Bronze+) | Notes |
|-------|---------------------|-------|
| o1-preview + AIDE | 16.9% | Best performing (purpose-built scaffolding) |
| Thesis (gpt-5-codex) | Available | On leaderboard |
| FM Agent (Gemini-2.5-Pro) | Available | On leaderboard |
| R&D-Agent variants | Available | Multiple configurations tested |

### What Makes It Different

**DS-1000**: Single-function, isolated problems
**MLE-bench**: Complete ML pipeline (data loading → preprocessing → modeling → submission)

**Task Scope**:
- Data exploration and cleaning
- Feature engineering
- Model selection and tuning
- Cross-validation strategies
- Submission formatting
- End-to-end pipeline

### Complexity Comparison

```
DS-1000:      ⭐⭐ (Basic - single function)
ML-Bench:     ⭐⭐⭐⭐ (Advanced - repository-level)
MLE-bench:    ⭐⭐⭐⭐⭐ (Expert - complete competition)
```

### Available for Analysis

✅ **YES** - Agent runs and evaluation results

**Data Structure**:
- `runs/` directory with agent submissions
- `experiments/` with performance analysis
- Leaderboard with comparative metrics
- Grading scripts for evaluation

### Analysis Potential for ToGMAL

**Very High Value**:
1. **Pipeline errors**: Multi-stage failures (data → model → submission)
2. **Strategy errors**: Wrong approach to problem
3. **Integration errors**: Components don't work together
4. **Validation errors**: Overfitting, data leakage
5. **Real-world applicability**: Actual competition performance

**Conceptual Errors We Could Discover**:
- `pipeline_composition` - Steps in wrong order or missing
- `data_leakage` - Using test data in training
- `validation_strategy` - Wrong CV approach for problem type
- `feature_engineering_relevance` - Creating irrelevant features
- `model_selection_mismatch` - Wrong model for data type
- `hyperparameter_tuning_inefficiency` - Poor search strategy
- `submission_format_errors` - Wrong output format

**Challenges**:
- Much more complex than DS-1000 (harder to attribute errors)
- Multi-file, multi-step solutions
- Longer timescales (agent may iterate for hours)

**Recommendation**: **High value but requires more sophisticated analysis** - consider after ML-Bench.

---

## 3. DataSciBench ⭐ MEDIUM PRIORITY

**Official Name**: DataSciBench: An LLM Agent Benchmark for Data Science

**Source**: THUDM (Tsinghua University)
**Paper**: https://arxiv.org/abs/2502.13897
**GitHub**: https://github.com/THUDM/DataSciBench
**Data**: ✅ **Evaluation results and model outputs available**

### Dataset Overview

**Size**: 222 comprehensive prompts with 519 ground truths
**Framework**: Task-Function-Code (TFC) evaluation
**Focus**: Multi-step data science workflows

**Models Tested**:
- 6 API-based models (GPT-4o, etc.)
- 8 open-source general models
- 9 open-source code generation models

### Model Performance

| Model | Best Performer |
|-------|---------------|
| GPT-4o | Highest across all metrics |
| Deepseek-Coder-33B-Instruct | Best open-source model |

### What Makes It Different

**DS-1000**: Single function, single library
**DataSciBench**: Multi-task workflows, requires task decomposition

**Task Examples**:
- Verify data file existence
- Explore dataset structure
- Generate PDF reports
- Multi-step analysis pipelines

### Complexity Comparison

```
DS-1000:        ⭐⭐ (Basic - single function)
DataSciBench:   ⭐⭐⭐ (Intermediate - multi-task workflows)
```

### Available for Analysis

✅ **YES** - Evaluation results available

**Data Structure**:
- `evaluation_results/` directory
- JSON output samples with:
  - Generated code per task
  - Execution success/failure
  - Time costs and token usage
  - Performance metrics (accuracy, precision, recall, F1)

### Analysis Potential for ToGMAL

**Medium-High Value**:
1. **Task decomposition**: How models break down complex requests
2. **Multi-step reasoning**: Logic across multiple functions
3. **Workflow coherence**: Do steps work together?
4. **Error propagation**: How errors cascade through pipeline

**Conceptual Errors We Could Discover**:
- `task_decomposition` - Breaking problem into wrong subtasks
- `step_ordering` - Tasks in illogical sequence
- `state_management` - Lost track of data transformations
- `error_recovery` - Can't handle failed intermediate steps
- `output_chaining` - Output of one step doesn't match input of next

**Recommendation**: **Good complement to DS-1000** - adds multi-step complexity without overwhelming repository-level context.

---

## 4. DS-Bench / DSCodeBench

**Official Name**: DS-Bench: A Realistic Benchmark for Data Science Code Generation

**Paper**: https://arxiv.org/abs/2505.15621
**Note**: Different from DSBench (by LiqiangJing) which is an agent benchmark

### Dataset Overview

**Size**: 1,000 problems
**Libraries**: NumPy, Pandas, SciPy, Scikit-learn, TensorFlow, PyTorch, Matplotlib, Seaborn, Keras, LightGBM
**Source**: Real problems from GitHub

### Model Performance

| Model | Pass@1 | Pass@3 |
|-------|--------|--------|
| GPT-4o | 0.202 | 0.239 |
| DeepSeek-Coder-33B | 0.155 | - |

**Comparison**: GPT-4o achieves 45.1% pass@1 on DS-1000 but only 20.2% on DS-Bench (2.2x harder!)

### Complexity Comparison

```
DS-1000:        ⭐⭐ (Basic)
DS-Bench:       ⭐⭐⭐⭐ (Significantly harder - 2.2x lower pass rate)
```

### Available for Analysis

❌ **NO** - Repository structure not found/documented

**Status**: Paper published May 2025, but public repository with model outputs not located

### Analysis Potential

**Would Be High Value** if outputs available:
- More realistic problems than DS-1000
- 2.2x harder (more error-prone)
- Same library coverage

**Conceptual Errors**:
- Similar to DS-1000 but more complex variants
- Edge cases and corner conditions
- More realistic constraints

**Recommendation**: **Monitor for data release** - would be valuable if model outputs become available.

---

## 5. RE-Bench (Research Engineering Benchmark)

**Official Name**: RE-Bench: Evaluating Frontier AI R&D Capabilities

**Source**: METR (Model Evaluation and Threat Research)
**Paper**: https://arxiv.org/abs/2411.15114
**GitHub**: https://github.com/METR/RE-Bench
**Data**: ❌ **Protected (password-protected solutions)**

### Dataset Overview

**Size**: 7 open-ended ML research engineering environments
**Human Baseline**: 71 attempts (8 hours each) by 61 expert researchers
**Focus**: AI research and development capabilities

### Model vs Human Performance

**2-hour budget**: AI agents 4x better than humans
**8-hour budget**: Humans slightly exceed AI
**32-hour budget**: Humans achieve 2x AI score

### What Makes It Different

**All Other Benchmarks**: Coding tasks
**RE-Bench**: Research engineering (novel ML research implementation)

**Example Tasks**:
- Custom Triton kernel optimization
- Novel algorithm implementation
- Research paper replication
- ML system improvements

### Complexity Comparison

```
DS-1000:        ⭐⭐ (Basic - library usage)
ML-Bench:       ⭐⭐⭐⭐ (Advanced - repository code)
MLE-bench:      ⭐⭐⭐⭐⭐ (Expert - complete pipeline)
RE-Bench:       ⭐⭐⭐⭐⭐⭐ (Frontier - novel research)
```

### Available for Analysis

❌ **NO** - Data intentionally protected

**Reason**: Tasks password-protected to prevent solution leakage into training data
**Access**: Direct collaboration with METR required

### Analysis Potential

**Would Be Extremely High Value** if accessible:
- Research-level problem solving
- Novel algorithm development
- Creative solutions beyond training data
- Human baseline comparison

**Conceptual Errors**:
- `research_novelty` - Can't go beyond training distribution
- `creative_problem_solving` - Rigid template application
- `experimental_design` - Poor hypothesis testing
- `optimization_strategy` - Local vs global optimization confusion

**Recommendation**: **Not accessible** - data intentionally protected from public analysis.

---

## Comparison Matrix

### Dataset Characteristics

| Benchmark | Size | Complexity | Libraries | Outputs Available |
|-----------|------|------------|-----------|-------------------|
| **DS-1000** (baseline) | 1,000 | ⭐⭐ | 7 libraries | ✅ YES |
| **ML-Bench** | 9,641 | ⭐⭐⭐⭐ | Real repos | ✅ YES |
| **MLE-bench** | 75 | ⭐⭐⭐⭐⭐ | Full pipeline | ✅ YES |
| **DataSciBench** | 222 | ⭐⭐⭐ | Multi-task | ✅ YES |
| **DS-Bench** | 1,000 | ⭐⭐⭐⭐ | 10 libraries | ❌ NO |
| **RE-Bench** | 7 | ⭐⭐⭐⭐⭐⭐ | Research | ❌ Protected |

### Error Type Coverage

| Error Category | DS-1000 | ML-Bench | MLE-bench | DataSciBench |
|----------------|---------|----------|-----------|--------------|
| API confusion | ✅ Excellent | ✅ Excellent | ✅ Good | ✅ Good |
| Single-function logic | ✅ Excellent | ⚠️ Limited | ⚠️ Limited | ⚠️ Limited |
| Repository navigation | ❌ None | ✅ Excellent | ✅ Good | ❌ None |
| Multi-step pipelines | ❌ None | ⚠️ Some | ✅ Excellent | ✅ Excellent |
| Context understanding | ❌ None | ✅ Excellent | ✅ Excellent | ⚠️ Some |
| Integration errors | ❌ None | ✅ Good | ✅ Excellent | ⚠️ Some |

---

## Recommendations for ToGMAL Integration

### Priority 1: ML-Bench (Immediate Action)

**Why**:
- ✅ Model outputs readily available
- ✅ 9.6x larger dataset than DS-1000
- ✅ Repository-level tasks (new error types)
- ✅ Similar analysis approach to DS-1000

**Action Items**:
1. Clone https://github.com/gersteinlab/ML-Bench
2. Extract model outputs from `output/` folder
3. Adapt DS-1000 analysis scripts
4. Compare single-function vs repository-level errors

**Expected New Insights**:
- How models handle multi-file context
- Import and dependency resolution errors
- Documentation reading comprehension
- Code navigation strategies

**Estimated Effort**: 2-3 days (leverage existing DS-1000 analysis)

---

### Priority 2: DataSciBench (Short-term)

**Why**:
- ✅ Evaluation results available
- ✅ Multi-step workflow focus
- ✅ Moderate complexity (not overwhelming)
- ✅ Complements DS-1000 nicely

**Action Items**:
1. Clone https://github.com/THUDM/DataSciBench
2. Extract evaluation results
3. Analyze task decomposition patterns
4. Map multi-step errors to conceptual gaps

**Expected New Insights**:
- Task decomposition strategies
- Step ordering logic
- Error propagation through pipelines
- State management across functions

**Estimated Effort**: 3-4 days

---

### Priority 3: MLE-bench (Medium-term)

**Why**:
- ✅ Agent submissions available
- ✅ Real-world Kaggle performance
- ⚠️ Very complex (harder to analyze)
- ✅ High-value insights

**Action Items**:
1. Clone https://github.com/openai/mle-bench
2. Study agent run structure
3. Develop pipeline-level error taxonomy
4. Compare agent strategies

**Expected New Insights**:
- ML pipeline composition errors
- Data leakage patterns
- Validation strategy mistakes
- Feature engineering effectiveness

**Estimated Effort**: 1-2 weeks (requires new analysis framework)

---

### Not Recommended: DS-Bench, RE-Bench

**DS-Bench**: No model outputs available (framework only)
**RE-Bench**: Intentionally protected data

**Action**: Monitor for future data releases

---

## Analysis Strategy Comparison

### DS-1000 Approach (What We Did)

1. Compare generated code vs reference solutions
2. Extract syntactic errors (wrong_method, missing_method, etc.)
3. Map to conceptual errors (mutability, indexing, etc.)
4. Generate ToGMAL warnings

**Works well for**: Single-function, isolated library usage

---

### ML-Bench Approach (Recommended)

**Same Foundation**:
- Compare generated vs reference
- Extract syntactic errors
- Map to conceptual errors

**New Dimensions**:
1. **Repository Context Analysis**
   - Did model find relevant code?
   - Correct imports from existing files?
   - Maintained consistency with codebase style?

2. **Multi-File Coordination**
   - Cross-file dependencies handled?
   - Import errors?
   - Namespace conflicts?

3. **Documentation Adherence**
   - Used APIs according to docs?
   - Respected parameter constraints?
   - Followed documented patterns?

**New Conceptual Errors**:
- `codebase_navigation_failure` - Can't find relevant code
- `context_window_limitation` - Misses critical distant code
- `documentation_comprehension` - Ignores documented constraints
- `multi_file_state_management` - Lost track of cross-file state
- `import_resolution_confusion` - Wrong or circular imports

---

### MLE-bench Approach (Advanced)

**Pipeline-Level Analysis**:
1. **Stage Identification**
   - Data loading
   - EDA
   - Feature engineering
   - Model training
   - Validation
   - Submission

2. **Stage-Specific Errors**
   - Data leakage (using test in train)
   - Wrong validation strategy
   - Inefficient feature engineering
   - Model-data mismatch

3. **Integration Errors**
   - Pipeline stages don't connect
   - Data format mismatches
   - Missing error handling

**New Conceptual Errors**:
- `data_leakage_unawareness` - Test data in training
- `validation_strategy_mismatch` - Wrong CV for problem
- `pipeline_composition_error` - Steps in wrong order
- `feature_target_leakage` - Features use future information
- `model_architecture_mismatch` - Wrong model for data type

---

## Implementation Roadmap

### Phase 1: ML-Bench Analysis (Week 1-2)

**Week 1**:
- Clone ML-Bench repository
- Extract model outputs (GPT-4, GPT-3.5, CodeLlama)
- Adapt DS-1000 analysis scripts
- Run initial syntactic error detection

**Week 2**:
- Develop repository-level error detectors
- Map new error types to conceptual gaps
- Generate preliminary report
- Create ToGMAL integration prototypes

**Deliverables**:
- ML-Bench error analysis report
- Repository-level conceptual error taxonomy
- Updated ToGMAL risk detection

---

### Phase 2: DataSciBench Analysis (Week 3)

**Week 3**:
- Extract DataSciBench evaluation results
- Analyze multi-step workflows
- Identify task decomposition patterns
- Map pipeline errors to concepts

**Deliverables**:
- DataSciBench multi-step error analysis
- Task decomposition error patterns
- Pipeline coherence metrics

---

### Phase 3: Unified Framework (Week 4)

**Week 4**:
- Combine insights from DS-1000, ML-Bench, DataSciBench
- Build unified conceptual error taxonomy
- Develop comprehensive ToGMAL risk framework
- Create educational materials

**Deliverables**:
- Unified conceptual error taxonomy (single-function → repository-level)
- Comprehensive ToGMAL integration guide
- Learning path recommendations by complexity

---

## Expected Insights by Benchmark

### DS-1000 (Completed)
✅ API confusion patterns
✅ Single-function logic errors
✅ Library-specific error rates
✅ Model personality differences
✅ 11 conceptual error types

### ML-Bench (Next)
🔄 Repository navigation strategies
🔄 Multi-file coordination errors
🔄 Documentation comprehension gaps
🔄 Context window limitations
🔄 Import resolution patterns
🔄 Codebase consistency failures

### DataSciBench (Then)
🔄 Task decomposition approaches
🔄 Multi-step pipeline errors
🔄 Error propagation patterns
🔄 State management across functions
🔄 Workflow coherence metrics

### Combined (Final)
🔄 Complexity vs error rate relationship
🔄 Error type transitions (simple → complex tasks)
🔄 Universal conceptual gaps across all complexity levels
🔄 Learning path by user skill level
🔄 Risk scoring by task complexity

---

## Conclusion

### Available and Valuable

✅ **ML-Bench**: 9,641 examples, repository-level, outputs available → **START HERE**
✅ **DataSciBench**: 222 prompts, multi-step, outputs available → **COMPLEMENT DS-1000**
✅ **MLE-bench**: 75 competitions, full pipelines, outputs available → **ADVANCED ANALYSIS**

### Not Accessible Now

❌ **DS-Bench**: Framework only, no outputs yet
❌ **RE-Bench**: Intentionally protected

### Recommendation

**Immediate action**: Begin ML-Bench analysis to extend our DS-1000 insights to repository-level code.

**Approach**:
1. Download ML-Bench model outputs
2. Adapt our DS-1000 analysis scripts
3. Identify new error types unique to repository-level tasks
4. Extend conceptual error taxonomy
5. Update ToGMAL risk framework

**Timeline**: 2-3 days for initial ML-Bench analysis (leverage existing work)

**Expected ROI**:
- 9.6x more data than DS-1000
- New error categories (navigation, imports, documentation)
- Repository-level risk assessment for ToGMAL
- Clearer guidance for real-world codebases (not just isolated functions)

---

**Generated**: November 15, 2025
**Benchmarks Surveyed**: ML-Bench, MLE-bench, DataSciBench, DS-Bench, RE-Bench
**Recommendation**: **Start with ML-Bench** - model outputs available, direct upgrade from DS-1000
