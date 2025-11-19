# Data Fetching Guide: Getting MMLU-Pro Dataset & Model Results

## Quick Start

### Option 1: Fetch Full 12K Dataset (Recommended)

```bash
# Install dependencies
pip install datasets

# Fetch all 12K questions from MMLU-Pro
python fetch_mmlu_pro_full.py
```

**What this does**:
- Downloads 12,031 questions from HuggingFace (TIGER-Lab/MMLU-Pro)
- Attempts to fetch model results from OpenLLM Leaderboard
- Saves to `data/mmlu_pro_full/mmlu_pro_12k.json`
- Generates fetch report

**Expected output**:
```
✓ Total questions: 12,031
  With model results: ??? (depends on leaderboard availability)
  Output: data/mmlu_pro_full/mmlu_pro_12k.json
```

### Option 2: Use Existing 500 Questions

```bash
# Use the data already in the repo
python fetch_real_benchmark_data.py
```

**What this does**:
- Uses existing `raw_benchmark_results.json` (500 questions)
- Populates `model_results` field from leaderboard
- Faster, smaller dataset for initial validation

## Understanding the Data Structure

### Input Format (from HuggingFace)

```json
{
  "question": "What is the capital of France?",
  "options": ["London", "Paris", "Berlin", "Madrid"],
  "answer": "B",
  "category": "geography",
  "cot_content": "Paris is the capital..."
}
```

### Our Output Format

```json
{
  "question_id": "mmlu_pro_test_0",
  "source_benchmark": "MMLU_Pro",
  "question_text": "What is the capital of France?",
  "choices": ["London", "Paris", "Berlin", "Madrid"],
  "correct_answer": "B",
  "domain": "geography",

  "model_results": {
    "meta-llama/Meta-Llama-3.1-70B-Instruct": {
      "is_correct": true,
      "answer": "B",
      "confidence": null
    },
    "Qwen/Qwen2.5-72B-Instruct": {
      "is_correct": false,
      "answer": "C",
      "confidence": null
    }
  },

  "success_rate": 0.5,  // 50% of models got it right
  "num_models": 2,
  "difficulty_tier": "medium",
  "difficulty_label": "Moderate"
}
```

## Where Model Results Come From

### Source 1: OpenLLM Leaderboard (Preferred)

**Pros**:
- Pre-computed results from top models
- Free, no API costs
- Includes many models

**Cons**:
- May not have MMLU-Pro results (leaderboard focuses on MMLU, not MMLU-Pro)
- Limited to models on leaderboard
- Only has correctness, not actual answers

**Access**:
```python
from datasets import load_dataset

# Try to load detailed results
dataset_name = "open-llm-leaderboard/details_meta-llama__Meta-Llama-3.1-70B-Instruct"
results = load_dataset(dataset_name, "harness_hendrycksTest_5")
```

**Status**: ⚠️ May not work for MMLU-Pro (MMLU-Pro is newer)

### Source 2: Direct API Calls (Fallback)

**Pros**:
- Get actual model answers
- Full control over prompting
- Can add chain-of-thought

**Cons**:
- Costs money (especially for 12K questions)
- Slower (rate limits)
- Requires API keys

**Implementation**:
```python
import anthropic

client = anthropic.Anthropic(api_key="...")

for question in questions:
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{
            "role": "user",
            "content": f"{question['question_text']}\n\n{format_choices(question['choices'])}"
        }]
    )

    model_answer = extract_answer(response.content)
```

**Cost estimate** (for 12K questions):
- Claude Sonnet: ~$15-30
- GPT-4: ~$50-100
- Llama via HF Inference: Free (rate limited)

### Source 3: Pre-computed Results from Papers

**Pros**:
- Free
- Already computed
- Includes baselines

**Cons**:
- Need to find and format
- May not have latest models
- Usually only has aggregate stats, not per-question

**Where to look**:
1. MMLU-Pro paper: https://github.com/TIGER-AI-Lab/MMLU-Pro
2. Model cards on HuggingFace
3. Published benchmarking papers

## Current Data Status

### What We Have

- ✅ 500 questions in `data/benchmark_results/raw_benchmark_results.json`
- ❌ `model_results` field is empty
- ✅ All question structure ready

### What We Need

**Minimum (for validation)**:
- Model results for 100+ questions
- At least 2 models
- Just correctness (not actual answers)

**Good (for research)**:
- Model results for 1000+ questions
- 5+ models
- Actual model answers (not just correct/incorrect)

**Ideal (for publication)**:
- All 12K questions
- 10+ models
- Actual answers + confidence scores + chain-of-thought

## Step-by-Step: Getting Started

### Path 1: Quick Validation (Start Here)

**Goal**: Get enough data to run validation (1-2 hours)

```bash
# 1. Try to fetch 500 questions with results
python fetch_real_benchmark_data.py

# 2. Check if model results populated
python -c "
import json
with open('data/benchmark_results/raw_benchmark_results.json') as f:
    data = json.load(f)
    sample = list(data['questions'].values())[0]
    print('Model results:', sample.get('model_results', {}))
"

# 3. If results populated, run validation
python week1_2_validation.py
```

**Expected outcome**:
- If OpenLLM has MMLU data → 500 questions with 3-5 models ✅
- If not → Need to use fallback (see Path 2)

### Path 2: Full Dataset (1-2 days)

**Goal**: Get all 12K questions with comprehensive results

```bash
# 1. Fetch all questions
python fetch_mmlu_pro_full.py
# Output: data/mmlu_pro_full/mmlu_pro_12k.json (questions only)

# 2. Run models via API (choose one)

# Option A: Use HuggingFace Inference (free, slow)
pip install huggingface_hub
python run_hf_inference.py  # (need to create this)

# Option B: Use commercial APIs (fast, costs $)
python run_api_inference.py --provider anthropic --model claude-3-5-sonnet
python run_api_inference.py --provider openai --model gpt-4o

# 3. Validate results
python week1_2_validation.py --data data/mmlu_pro_full/mmlu_pro_12k.json
```

## What to Expect

### Scenario A: Leaderboard Has Data ✅

```
📊 Results:
  Total questions: 12,031
  With model results: 12,031 (100%)
  Models: 5 (Llama-70B, Qwen-72B, etc.)

✅ Ready for validation immediately
```

### Scenario B: Leaderboard Missing MMLU-Pro ⚠️

```
📊 Results:
  Total questions: 12,031
  With model results: 0 (0%)
  Models: 0

⚠️  OpenLLM Leaderboard doesn't have MMLU-Pro results
   Need to run models ourselves
```

**Solution**: Use API calls or find pre-computed results

### Scenario C: Partial Results 🔶

```
📊 Results:
  Total questions: 12,031
  With model results: 3,500 (29%)
  Models: 2

🔶 Some models available, but incomplete
   Can start validation, expand later
```

## Practical Recommendations

### For Immediate Progress (This Week)

**Focus on validation, not data scale**:

1. Get 100-500 questions with results (any source)
2. Run validation to verify taxonomy works
3. If validation passes → justify scaling
4. If validation fails → fix taxonomy first

**Why**: No point getting 12K questions if taxonomy doesn't work on 100

### For Research Paper (Month 2-3)

**Need comprehensive data**:

1. All 12K MMLU-Pro questions
2. 10+ models (mix of sizes/architectures)
3. Actual answers (for distractor analysis)
4. Chain-of-thought traces (for reasoning analysis)

**Estimated cost**: $50-200 depending on API choices

## Troubleshooting

### "datasets library not found"

```bash
pip install datasets
# or
pip install datasets huggingface_hub
```

### "Failed to fetch from leaderboard"

Leaderboard may not have MMLU-Pro results. Options:
1. Use MMLU (original) instead (has more leaderboard data)
2. Run models yourself
3. Find pre-computed results from papers

### "Out of memory loading dataset"

12K questions is large. Solutions:
1. Process in batches
2. Use streaming: `load_dataset(..., streaming=True)`
3. Sample subset: `load_dataset(...).shuffle().select(range(1000))`

### "API rate limits"

When running models:
1. Add delays: `time.sleep(1)` between calls
2. Use batch APIs when available
3. Parallelize across multiple API keys

## Summary

**Current Blocker**: Need model results data

**Fastest Path**: Run `fetch_mmlu_pro_full.py`, see if leaderboard has data

**If Leaderboard Works**: ✅ Instant 12K questions with results

**If Leaderboard Fails**: Run subset via API (~$10-20 for 1000 questions)

**Next Step After Data**: `python week1_2_validation.py` to verify taxonomy

**Goal**: Get 3/5 validation metrics passing, then scale
