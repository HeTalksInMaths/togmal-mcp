# How We Bypassed HuggingFace Token Requirements

**Date**: November 15, 2025
**Context**: Analyzing benchmarks without HuggingFace API access

---

## The Challenge

Many ML benchmarks are hosted on HuggingFace, which typically requires:
- HuggingFace API token
- Network access to `huggingface.co`
- Python `datasets` library configured

In our environment:
- ❌ HuggingFace API blocked (network restrictions)
- ❌ `load_dataset()` fails with `LocalEntryNotFoundError`
- ❌ Direct downloads from huggingface.co return 403 Forbidden

---

## The Solution: Direct GitHub Access

### For DS-1000 ✅ SUCCESS

Instead of using HuggingFace, we accessed the data **directly from GitHub**:

**Repository**: `xlang-ai/DS-1000`
**URL**: https://github.com/xlang-ai/DS-1000

**Key Files** (accessed via raw.githubusercontent.com):
```bash
# Main dataset
https://raw.githubusercontent.com/xlang-ai/DS-1000/main/data/ds1000.jsonl.gz

# Model answers
https://raw.githubusercontent.com/xlang-ai/DS-1000/main/data/codex002-answers.jsonl
https://raw.githubusercontent.com/xlang-ai/DS-1000/main/data/gpt-3.5-turbo-0613-answers.jsonl
https://raw.githubusercontent.com/xlang-ai/DS-1000/main/data/gpt-4-0613-answers.jsonl
```

**Download Method**:
```python
import requests
import gzip
import json

# Download and decompress
url = "https://raw.githubusercontent.com/xlang-ai/DS-1000/main/data/ds1000.jsonl.gz"
response = requests.get(url)
data = gzip.decompress(response.content).decode('utf-8')
problems = [json.loads(line) for line in data.strip().split('\n')]
```

**Why This Works**:
- GitHub hosts raw files at `raw.githubusercontent.com`
- No authentication required for public repositories
- Bypasses HuggingFace entirely

---

## For DataSciBench ✅ SUCCESS

**Repository**: `THUDM/DataSciBench`
**URL**: https://github.com/THUDM/DataSciBench

**Direct Git Clone**:
```bash
git clone https://github.com/THUDM/DataSciBench.git
```

**What We Get**:
- ✅ **7,203 files** cloned successfully
- ✅ **evaluation_results/** directory with model outputs:
  - `gpt-4o-2024-05-13_results.csv` (2,082 rows)
  - `claude-3-5-sonnet-20240620_results.csv`
  - `deepseek-coder-33b-instruct_results.csv`
  - And 20+ other models
- ✅ **data/** directory with 222 prompts (each in `prompt.json`)
- ✅ **metric/** directory with evaluation metrics
- ✅ **evaluations/** directory with evaluation code

**Why This Works**:
- Complete dataset stored in GitHub repository
- Model outputs included in repo (not separate)
- No HuggingFace dependency at all

---

## For ML-Bench ❌ FAILED

**Repository**: `gersteinlab/ML-Bench`
**URL**: https://github.com/gersteinlab/ML-Bench

**What We Get**:
- ✅ Repository cloned successfully
- ✅ Evaluation framework and scripts
- ❌ **Model outputs NOT in repository**
  - `output/` folder is gitignored
  - Authors state: "The output/ folder includes the model-generated outputs we used for testing"
  - But these outputs aren't stored in GitHub

**Why This Fails**:
- Authors published code but not data
- Model outputs presumably:
  - Generated during evaluation OR
  - Stored separately (possibly on HuggingFace)
- HuggingFace dataset `super-dainiu/ml-bench` blocked

**Potential Workaround** (not tested):
- Run the evaluation scripts ourselves
- Generate outputs from our own API keys
- But this requires:
  - API access to GPT-4, CodeLlama, etc.
  - Significant compute time
  - Not feasible for large-scale analysis

---

## Key Lessons

### ✅ Datasets That Work Without HuggingFace

**Pattern**: Repository contains **both code AND data**
- DS-1000: ✅ Data in GitHub (`.jsonl.gz` files)
- DataSciBench: ✅ Data in GitHub (prompts + results)
- RE-Bench: ❌ Data password-protected (intentional)

### ❌ Datasets That Don't Work

**Pattern**: Repository contains **code only, data elsewhere**
- ML-Bench: Data on HuggingFace (`super-dainiu/ml-bench`)
- DS-Bench: Framework only, no outputs yet
- MLE-bench: Outputs may be generated, not stored

### 🔍 How to Check Before Starting

**1. Check `.gitignore`**
```bash
grep "output\|data\|results" .gitignore
```
If these are ignored → data not in repo

**2. Check for data files**
```bash
find . -name "*.jsonl" -o -name "*.csv" -o -name "*.json" | head -20
```
If empty → data elsewhere

**3. Check README**
Look for:
- "Download from HuggingFace..." → Need HF access
- "Load dataset using..." → Need HF library
- "Data in `/data` directory" → Should work!

---

## DataSciBench Specific Success

### What Makes DataSciBench Accessible

**1. Self-Contained Repository**
```
DataSciBench/
├── data/               # 222 task prompts
│   ├── bcb1011/prompt.json
│   ├── bcb1017/prompt.json
│   └── ... (222 total)
├── evaluation_results/ # Model outputs
│   └── results/
│       ├── gpt-4o-2024-05-13_results.csv
│       ├── claude-3-5-sonnet-20240620_results.csv
│       ├── deepseek-coder-33b-instruct_results.csv
│       └── ... (28 models)
├── metric/             # Evaluation metrics (222 dirs)
└── evaluations/        # Evaluation code
```

**2. Models Analyzed** (28 total):
- API Models (6):
  - gpt-4o-2024-05-13
  - gpt-4-turbo
  - gpt-4o-mini
  - claude-3-5-sonnet-20240620
  - glm-4-flash
  - o1-mini

- Open-Source General (8):
  - Meta-Llama-3.1-8B-Instruct
  - Qwen2.5-7B-Instruct
  - glm-4-9b-chat
  - gemma-2-9b-it
  - Yi-1.5-9B-Chat-16K
  - And others

- Open-Source Code Models (14):
  - deepseek-coder-33b-instruct
  - CodeLlama-34b-Instruct-hf
  - Qwen2.5-Coder-7B-Instruct
  - starcoder2-15b
  - And others

**3. Rich Evaluation Data**

Each result CSV contains:
- `model_name`: Model identifier
- `run_id`: Execution ID
- `data_name`: Task identifier (e.g., "human_8")
- `task_name`: Task description
- `metric_name`: Metric being measured
- `function_name`: Specific function evaluated
- `result_value`: Result (True/False/Error/numeric)
- `result_cr`: Numeric score
- `result_type`: Type of task

**4. Multi-Step Tasks**

Each prompt.json defines complex tasks like:
- Read CSV → Group by column → Calculate mean → Create bar plot
- Requires multiple pandas/matplotlib operations
- Tests task decomposition and pipeline construction

---

## Comparison: Data Access Methods

| Benchmark | Access Method | Data Location | Status |
|-----------|---------------|---------------|--------|
| **DS-1000** | Direct GitHub | Raw files in repo | ✅ Works |
| **DataSciBench** | Git clone | Data IN repo | ✅ Works |
| **ML-Bench** | HuggingFace | `super-dainiu/ml-bench` | ❌ Blocked |
| **MLE-bench** | Git clone | Generated during eval | ⚠️ Needs eval |
| **RE-Bench** | Protected | Password-protected | ❌ Intentional |

---

## Best Practices for Future Benchmarks

### Before Starting Analysis

**1. Verify Data Availability**
```bash
# Clone repo
git clone https://github.com/org/benchmark.git
cd benchmark

# Check for data files
find . -name "*.jsonl" -o -name "*.csv" | wc -l

# If count > 0 → data in repo ✅
# If count = 0 → check HuggingFace or elsewhere ❌
```

**2. Test HuggingFace Alternative**
```bash
# Look for raw data URLs in GitHub
grep -r "raw.githubusercontent.com" README.md
grep -r "github.com/.*/data/" README.md
```

**3. Check Paper Supplementary**
- Look for "Data Availability" section
- Check for Zenodo, Dropbox, Google Drive links
- Some papers publish data separately from code

---

## Why This Matters for ToGMAL

**Key Insight**: We can analyze many benchmarks **without** HuggingFace access by:
1. Using GitHub-hosted datasets (DS-1000, DataSciBench)
2. Cloning repositories with embedded data
3. Accessing raw files via `raw.githubusercontent.com`

**Impact**:
- ✅ Successfully analyzed DS-1000 (1,000 problems × 3 models)
- ✅ Can now analyze DataSciBench (222 prompts × 28 models)
- ❌ ML-Bench blocked (need HF access)
- ✅ Total accessible: ~7,000 model outputs for analysis

**Next Steps**:
- Analyze DataSciBench multi-step errors
- Identify task decomposition patterns
- Map to new conceptual errors (pipeline-related)
- Extend ToGMAL risk framework

---

**Bottom Line**: **GitHub direct access > HuggingFace API** for benchmark analysis in restricted environments. Many benchmarks store data in GitHub, bypassing HuggingFace entirely.
