# Autonomous Benchmark Dataset Growth Guide

## Overview

The autonomous growth system intelligently selects and grows your benchmark dataset by choosing top-performing models across different size categories. No manual curation needed - the system discovers, ranks, and selects the best models automatically.

## Selection Strategy

### Intelligent Model Selection

The system uses a **multi-criteria selection approach**:

1. **Top 5 SOTA Models** - Best overall performers regardless of size
2. **Top 1 Medium (~10-40B)** - Best mid-size model
3. **Top 1 Small (≤10B)** - Best small/efficient model

This ensures diversity in:
- **Performance levels**: From cutting-edge SOTA to efficient small models
- **Model sizes**: Coverage across deployment scenarios
- **Use cases**: Production (large), edge deployment (small), balanced (medium)

### Current Selection (MMLU-Pro Benchmark)

**Top 5 SOTA Models** (76-83% accuracy):
- arx_0314 (83.0%)
- iask_pro (81.2%)
- arx_3 (78.2%)
- Claude 3.5 Sonnet (77.6%)
- Gemini 2.0 Flash (76.2%)

**Top Medium Model** (34B):
- Yi-34B (42.1%)

**Top Small Model** (8B):
- Meta-Llama-3.1-8B-Instruct (44.2%)

**Total: 7 models** providing comprehensive performance data

## Dataset Format

Each question includes scores from all 7 selected models:

```json
{
  "question": "What will be the number of lamps, each having 300 lumens...",
  "benchmark": "MMLU-Pro",
  "model_scores": {
    "arx_0314_5shots.json": true,
    "iask_pro_5shots.json": true,
    "arx_3_5shots": true,
    "claude-3-5-sonnet-20241022_5shots.json": false,
    "gemini-2.0-flash-exp_5shots.json": true,
    "Yi-34B_5shots": false,
    "Meta-Llama-3_1-8B-Instruct_5shots": false
  },
  "success_rate": 0.57,  // 4/7 models got it right
  "metadata": {
    "category": "engineering",
    "subject": "electrical_engineering",
    "options": ["...", "...", "..."]
  }
}
```

## Usage

### One-Time Build

Build dataset once with default settings (5,000 questions):

```bash
python autonomous_benchmark_grower.py
```

Build with specific question count:

```bash
python autonomous_benchmark_grower.py 10000  # 10k questions
```

### Continuous/Scheduled Growth

**Run once and exit**:
```bash
python run_continuous_growth.py --once
```

**Run every 6 hours**:
```bash
python run_continuous_growth.py --interval 6
```

**Run 5 cycles, hourly, with 10k questions each**:
```bash
python run_continuous_growth.py --interval 1 --iterations 5 --questions 10000
```

**Continuous mode (default 24 hours)**:
```bash
python run_continuous_growth.py
```

### Background Daemon

Run in background:

```bash
nohup python run_continuous_growth.py --interval 12 > growth.out 2>&1 &
```

Monitor progress:

```bash
tail -f continuous_growth.log
```

### Cron Job

Add to crontab for daily updates at 2 AM:

```bash
# Edit crontab
crontab -e

# Add this line:
0 2 * * * cd /path/to/togmal-mcp && python run_continuous_growth.py --once >> growth.out 2>&1
```

## Output Files

### State and Configuration

**`data/autonomous_state.json`** - Tracks growth state:
```json
{
  "total_questions": 1000,
  "selected_models": ["arx_0314_5shots.json", ...],
  "model_metadata": {...},
  "selection_criteria": {
    "top_sota": 5,
    "top_medium": 1,
    "top_small": 1
  },
  "last_check": "2025-11-15T02:02:00"
}
```

### Dataset Files

**`data/autonomous_benchmarks/autonomous_dataset.json`** - Full dataset with metadata

**`data/autonomous_benchmarks/vector_db_ready.json`** - ChromaDB-compatible format:
```json
{
  "documents": ["question text", ...],
  "metadatas": [{"success_rate": 0.57, ...}, ...],
  "ids": ["q_0", "q_1", ...],
  "source_metadata": {...}
}
```

### Logs

**`autonomous_growth.log`** - Detailed growth logs
**`continuous_growth.log`** - Continuous runner logs

## Performance Data

### Current Coverage

- **1,000 questions** with 7 model evaluations each
- **7,000 total model predictions** (1000 × 7)
- **Dataset size**: 1.2 MB (full), 0.7 MB (vector-ready)

### Scalability

Can scale to:
- **Up to 12,000 questions** per model (full MMLU-Pro benchmark)
- **Up to 48 models** available in MMLU-Pro
- **Potential: 576,000 model predictions** (12k × 48)

Current focused approach (7 carefully selected models) provides better quality vs quantity trade-off.

## Size Categories

### Small (≤10B parameters)
- **Use case**: Edge deployment, mobile, cost-efficient
- **Examples**: Llama-3.1-8B, Mistral-7B, Gemma-7B
- **Performance**: 18-44% accuracy on MMLU-Pro

### Medium (10-40B parameters)
- **Use case**: Balanced performance/cost, on-prem deployment
- **Examples**: Yi-34B, Qwen-14B
- **Performance**: 33-42% accuracy on MMLU-Pro

### Large (>40B parameters)
- **Use case**: Maximum performance, cloud deployment
- **Examples**: Llama-3.1-70B, Qwen-110B
- **Performance**: 36-63% accuracy on MMLU-Pro

### Unknown (Proprietary/API models)
- **Examples**: Claude 3.5, GPT-4o, Gemini
- **Performance**: 52-83% accuracy on MMLU-Pro

## Why This Approach Works

### 1. Performance Diversity
- SOTA models show what's possible
- Small models show practical limits
- Medium models show balanced trade-offs

### 2. Risk Assessment
ToGMAL can now provide nuanced risk warnings:
- "Even SOTA models struggle with this (20% success)" → High risk
- "Small models handle this well (80% success)" → Low risk
- "Only large models succeed (SOTA: 90%, small: 30%)" → Complexity warning

### 3. Resource-Aware Recommendations
- If only small models available: "This task may be too complex"
- If medium models sufficient: "No need for expensive SOTA"
- If SOTA required: "Consider using top-tier model"

### 4. Automated Discovery
- No manual curation of models
- Automatically adapts to new benchmarks
- Rankings update as new models added

## Customizing Selection Criteria

Edit `data/autonomous_state.json`:

```json
{
  "selection_criteria": {
    "top_sota": 10,    // Top 10 instead of 5
    "top_medium": 2,   // Top 2 medium models
    "top_small": 3     // Top 3 small models
  }
}
```

Then run growth cycle again to rebuild with new criteria.

## Integration with ToGMAL MCP

### Load into ChromaDB

```python
import chromadb
import json

# Load vector-ready data
with open('data/autonomous_benchmarks/vector_db_ready.json') as f:
    data = json.load(f)

# Create collection
client = chromadb.Client()
collection = client.create_collection(
    name="togmal_benchmarks",
    metadata={"description": "Autonomous benchmark dataset"}
)

# Add to database
collection.add(
    documents=data['documents'],
    metadatas=data['metadatas'],
    ids=data['ids']
)
```

### Query for Similar Questions

```python
# Find similar questions
results = collection.query(
    query_texts=["Calculate the current in a circuit"],
    n_results=5
)

# Extract risk indicators
for metadata in results['metadatas'][0]:
    success_rate = metadata['success_rate']

    if success_rate < 0.3:
        print("🔴 HIGH RISK: Most models fail on similar questions")
    elif success_rate < 0.6:
        print("🟡 MEDIUM RISK: Mixed success on similar questions")
    else:
        print("🟢 LOW RISK: Most models succeed on similar questions")

    # Check model scores for complexity analysis
    model_scores = json.loads(metadata['model_scores'])
    # Analyze which size categories succeed...
```

## Monitoring Growth

### Check Current Status

```bash
cat data/autonomous_state.json | jq '{
  total_questions,
  num_models: (.selected_models | length),
  last_check
}'
```

### View Model Selection

```bash
cat data/autonomous_state.json | jq '.model_metadata[] | {
  name,
  size_params,
  size_category,
  accuracy
}' | head -20
```

### Dataset Statistics

```bash
cat data/autonomous_benchmarks/autonomous_dataset.json | jq '.metadata'
```

## Advantages Over Manual Curation

✅ **Automated ranking** - No need to manually track model performance
✅ **Size diversity** - Automatically ensures coverage across sizes
✅ **Performance stratification** - Gets both SOTA and practical models
✅ **Easy updates** - Re-run to pick up new top models
✅ **Reproducible** - Selection criteria documented in state
✅ **Efficient** - Only downloads what's needed

## Future Enhancements

### Planned

1. **Multi-benchmark support** - Extend beyond MMLU-Pro
2. **Per-category selection** - Top models per subject area
3. **Temporal tracking** - Monitor model improvements over time
4. **Adaptive criteria** - Adjust selection based on use case
5. **Cost optimization** - Factor in API costs for proprietary models

### Possible Additions

- HumanEval (code generation)
- GSM8K (mathematical reasoning)
- ARC-Challenge (commonsense reasoning)
- HellaSwag (commonsense NLI)
- BigBench (diverse capabilities)

## Troubleshooting

### Issue: Rate limit errors

**Solution**: Increase delays in `autonomous_benchmark_grower.py`:
```python
time.sleep(2)  # Increase to 3-5 seconds
```

### Issue: Out of disk space

**Solution**: The system caches model predictions. Clear cache:
```bash
rm -rf data/eval_cache/mmlu_pro_*.json
```

### Issue: Stale model rankings

**Solution**: Clear cache to force re-ranking:
```bash
rm -rf data/eval_cache/
python autonomous_benchmark_grower.py
```

### Issue: Want different models

**Solution**: Modify selection criteria in state file and re-run.

## Best Practices

1. **Start small**: Run with 1,000 questions first to test
2. **Check logs**: Monitor `autonomous_growth.log` for errors
3. **Backup state**: Keep backups of `autonomous_state.json`
4. **Schedule wisely**: Daily updates are usually sufficient
5. **Monitor storage**: Each 1k questions ≈ 1-2 MB

## Summary

The autonomous growth system provides:

- **Smart selection**: Top performers across size categories
- **Automatic updates**: Continuous improvement without manual work
- **Quality data**: Real model evaluations for risk assessment
- **Scalable**: From 1k to 100k+ questions
- **Integrated**: Ready for ChromaDB and ToGMAL MCP

No manual curation. No hardcoded model lists. Just intelligent, autonomous growth. 🚀
