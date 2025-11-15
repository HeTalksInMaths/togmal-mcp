# ML-Bench Data Access Investigation

**Date**: November 15, 2025
**Status**: ⚠️ Data Access Blocked - Model Outputs Not Available
**Repository**: https://github.com/gersteinlab/ML-Bench

---

## Summary

ML-Bench is a highly promising benchmark for repository-level code analysis with 9,641 examples across 18 real GitHub repositories. However, **model-generated outputs are not accessible** in the current environment due to network restrictions.

---

## What We Found

### ✅ Successfully Cloned
- Repository structure explored
- 18 GitHub repositories as submodules:
  - PyTorch-GAN
  - BERT (Google Research)
  - ESM (Facebook Research)
  - LAVIS (Salesforce)
  - DGL
  - Open CLIP
  - PyTorch Image Models
  - External-Attention-pytorch
  - Grounded-Segment-Anything
  - Time-Series-Library
  - Learning3D
  - Muzic (Microsoft)
  - Vid2Vid (NVIDIA)
  - IF (DeepFloyd)
  - And others

### ❌ Data Access Challenges

**Model Outputs Location**:
- README states: *"The `output/` folder includes the model-generated outputs we used for testing."*
- However: `output/` is in `.gitignore` - **not stored in GitHub repository**

**HuggingFace Dataset**:
- Dataset ID: `super-dainiu/ml-bench`
- Contains: 9,641 examples with ground truth
- Splits: `full` and `quarter`
- **Status**: Network restrictions prevent access
- Error: `LocalEntryNotFoundError: Couldn't find 'super-dainiu/ml-bench' on the Hugging Face Hub`

**arXiv Paper**:
- Paper: https://arxiv.org/abs/2311.09835
- **Status**: 403 Forbidden (network restrictions)
- Would contain: Methodology, evaluation results, supplementary materials

---

## Dataset Structure (from README)

When accessible, the dataset contains:

```python
{
    'github_id': str,          # Repository ID
    'github': str,             # Repository URL
    'repo_id': int,            # Sample ID within repo
    'id': int,                 # Unique sample ID
    'path': str,               # Path in LLM-Bench
    'arguments': str,          # User-specified arguments
    'instruction': str,        # User instructions
    'oracle': str,             # Relevant oracle contents
    'type': str,               # Expected output type
    'output': str,             # Ground truth output
    'prefix_code': str,        # Environment setup code
}
```

---

## Evaluation Framework

### ML-LLM-Bench
- Tests: Text-to-code conversion in predefined environment
- Models tested: GPT-4, GPT-3.5-turbo-16k, CodeLlama-7b

### ML-Agent-Bench
- Tests: Autonomous agents in Linux sandbox
- Best performance: GPT-4o with 76.47% success rate

### Output Files (when available)
- Format: `{{MODEL_NAME}}_{{TASK}}_results_{{TIMESTAMP}}.jsonl`
- Contains: Model-generated code for each task
- Evaluation results: `eval_result*.jsonl` and `eval_total*.jsonl`

---

## What Analysis Would Be Possible

If data were accessible, we could analyze:

### Repository-Level Errors

**1. Codebase Navigation**
- Can models find relevant code in large repositories?
- Do they import from correct files?
- How do they handle file structure?

**2. Import Resolution**
- Correct imports from existing modules?
- Handling of circular dependencies?
- Understanding of package structure?

**3. Documentation Comprehension**
- Do models follow README instructions?
- API usage according to documentation?
- Respecting documented constraints?

**4. Multi-File Coordination**
- Consistency across file changes?
- State management across modules?
- Avoiding breaking existing code?

**5. Context Window Limitations**
- What happens when critical code is distant?
- How do models synthesize information from multiple files?
- Strategies for handling large codebases?

### New Conceptual Errors

Would extend our DS-1000 taxonomy with:
- `codebase_navigation_failure`
- `context_window_limitation`
- `documentation_comprehension_gap`
- `multi_file_state_management_error`
- `import_resolution_confusion`
- `repository_structure_misunderstanding`

---

## Comparison with DS-1000

| Aspect | DS-1000 | ML-Bench |
|--------|---------|----------|
| **Size** | 1,000 | 9,641 (9.6x larger) |
| **Scope** | Single function | Repository-level |
| **Libraries** | 7 (Pandas, NumPy, etc.) | 18 real GitHub repos |
| **Context** | Isolated | Multi-file, imports, docs |
| **Task Type** | StackOverflow-style | Real ML repository tasks |
| **Complexity** | ⭐⭐ | ⭐⭐⭐⭐ |
| **Data Available** | ✅ YES | ❌ Blocked |

---

## Alternative Approaches

### Option 1: DataSciBench ⭐ RECOMMENDED
- Repository: https://github.com/THUDM/DataSciBench
- Contains: Evaluation results in repo
- Size: 222 prompts, 519 ground truths
- Focus: Multi-step workflows
- **Status**: Should be accessible

### Option 2: Deeper DS-1000 Analysis
- We have all the data
- Could do:
  - Error clustering
  - Prediction modeling
  - Correlation analysis
  - Interactive error explorer

### Option 3: Document and Wait
- Create detailed ML-Bench analysis plan
- Document exact data requirements
- Revisit when network access available

---

## Data Access Requirements

To proceed with ML-Bench analysis, would need:

### Direct Access
1. **HuggingFace Dataset**: `super-dainiu/ml-bench`
   - Unrestricted internet access to HuggingFace
   - ~2GB download (estimated)

2. **Model Outputs**:
   - Either from paper authors
   - Or from `output/` directory (if separately released)

3. **Paper/Supplementary**:
   - arXiv: https://arxiv.org/abs/2311.09835
   - Would provide: Evaluation methodology, baseline results

### OR: Alternative Data Sources
- OpenDevin evaluation results (mentioned in README)
- Contact paper authors for data release
- Wait for supplementary data publication

---

## Recommendations

### Immediate
✅ **Pivot to DataSciBench** - likely accessible, complements DS-1000 nicely

### Short-term
- Monitor ML-Bench for separate data releases
- Check if model outputs published elsewhere
- Document analysis plan for when data becomes available

### Long-term
- Consider ML-Bench when network restrictions lift
- Most valuable for repository-level conceptual error discovery
- Direct upgrade path from DS-1000 → ML-Bench

---

## Key Takeaway

**ML-Bench is the ideal next step for ToGMAL** (repository-level errors, 9.6x more data, real codebases), but **data access is currently blocked**.

**Pragmatic next step**: Analyze **DataSciBench** (multi-step workflows, accessible) while keeping ML-Bench as a future priority.

---

## Files in Local Clone

```
ML-Bench/
├── repos/               # 18 GitHub submodules
├── scripts/             # Evaluation scripts
│   ├── post_process/    # Data preparation
│   ├── api/             # API calling scripts
│   ├── openai/          # OpenAI evaluation
│   └── finetune/        # Model fine-tuning
├── evaluation/          # Evaluation framework
├── envs/               # Environment setup
├── utils/              # Utilities
└── README.md           # Documentation
```

**Note**: Local clone is in `/home/user/togmal-mcp/ML-Bench/` (gitignored, ~500MB)

---

**Status**: Investigation complete, pivot to alternative benchmark recommended

**Next Action**: Analyze DataSciBench or deepen DS-1000 analysis

**Future Opportunity**: Revisit ML-Bench when network access allows HuggingFace dataset download
