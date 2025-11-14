# Alternative Approach: GitHub-Based Evaluation Results

## Overview

This is an alternative implementation for building the ToGMAL vector database that works without HuggingFace access. It scrapes benchmark evaluation results from public GitHub repositories and leaderboards.

## Problem Solved

The original HuggingFace-based approach (`infinite_benchmark_builder.py`, `massive_vector_db_builder.py`) was blocked by network restrictions preventing access to:
- HuggingFace API and datasets
- Open LLM Leaderboard evaluation results
- Model performance details per question

This alternative approach gets the same data from alternative public sources.

## Architecture

### 1. **Evaluation Results Scraper** (`evaluation_results_scraper.py`)

Fetches benchmark evaluation data from multiple sources:

**Current Sources:**
- **Open LLM Leaderboard Archive** (CSV)
  - Repository: `dsdanielpark/open-llm-leaderboard-report`
  - Data: 109 models × 4 benchmarks (ARC, HellaSwag, MMLU, TruthfulQA)
  - Format: Aggregate scores per model

- **MMLU-Pro Predictions** (ZIP archives)
  - Repository: `TIGER-AI-Lab/MMLU-Pro`
  - Data: 48 models with per-question predictions
  - Format: ~12,000 questions per model with correct/incorrect labels

**Features:**
- Automatic caching to avoid re-downloading
- Rate limit handling
- Multiple data format support (CSV, ZIP, JSON)
- Per-question prediction extraction
- Accuracy calculation from predictions

### 2. **Infinite Vector DB Builder** (`infinite_eval_vector_builder.py`)

Combines data from multiple sources into ToGMAL-compatible format:

**Output Format:**
```json
{
  "question": "What is the capital of France?",
  "benchmark": "MMLU-Pro",
  "model_scores": {
    "llama-2-7b": false,
    "llama-2-70b": true,
    "llama-3-70b": true
  },
  "success_rate": 0.67,
  "metadata": {
    "category": "geography",
    "options": ["Paris", "London", "Berlin"]
  }
}
```

**Capabilities:**
- Aggregate scores → synthetic questions (one per benchmark metric)
- Per-question predictions → real questions with model scores
- Export to vector database format (ChromaDB compatible)
- State persistence for incremental builds
- Caching for efficiency

## Current Dataset

As of last run:
- **174 total questions** with model evaluation scores
- **4 models tracked**: Llama-2 (7B, 13B, 70B), Llama-3-70B-Instruct
- **1 benchmark**: MMLU-Pro
- **170 real questions** from MMLU-Pro
- **4 synthetic questions** from aggregate scores

## Usage

### Quick Test (Aggregate Scores Only)
```bash
python infinite_eval_vector_builder.py
```

### Full Build (With Per-Question Data)
```bash
python infinite_eval_vector_builder.py full 5000
```

This fetches up to 5,000 per-question predictions from MMLU-Pro.

### View Scraper Sources
```bash
python evaluation_results_scraper.py
```

## Comparison with Original Approach

| Feature | HuggingFace Approach | GitHub Approach |
|---------|---------------------|-----------------|
| Data Source | Open LLM Leaderboard | Public GitHub repos |
| Network Requirement | HuggingFace access | General internet |
| Models Covered | All leaderboard models | Sample of models |
| Questions | 10+ benchmarks | Currently MMLU-Pro |
| Per-Question Data | ✅ Yes | ✅ Yes |
| Real Model Scores | ✅ Yes | ✅ Yes |
| Auto-Discovery | ✅ Yes | 🔄 Planned |
| Works in Restricted Networks | ❌ No | ✅ Yes |

## Extending the System

### Adding More Sources

Edit `evaluation_results_scraper.py`:

```python
GITHUB_SOURCES = [
    # ... existing sources ...
    {
        'name': 'new-benchmark',
        'repo': 'username/repo-name',
        'data_url': 'https://raw.githubusercontent.com/...',
        'format': 'csv',  # or 'zip', 'json'
        'benchmarks': ['BenchmarkName']
    }
]
```

### Future Enhancements

1. **Web Scraping**: Scrape live leaderboards (Artificial Analysis, LLM-Stats, etc.)
2. **More Benchmarks**: Add HumanEval, GSM8K, ARC-Challenge, etc.
3. **Continuous Updates**: Schedule periodic re-scraping for new data
4. **Model Coverage**: Expand from 5 to all 48 available MMLU-Pro models
5. **Papers With Code Integration**: Fetch benchmark results from academic papers

## Files

- `evaluation_results_scraper.py` - Core scraping logic
- `infinite_eval_vector_builder.py` - Vector database builder
- `data/eval_cache/` - Cached raw data from sources
- `data/eval_benchmarks/` - Processed datasets
  - `complete_evaluation_dataset.json` - Full dataset
  - `vector_db_ready.json` - ChromaDB-compatible format
  - `mmlu_pro_questions.json` - Cached MMLU-Pro questions
- `data/eval_builder_state.json` - Builder state for incremental builds
- `eval_vector_build.log` - Build logs

## Integration with ToGMAL

The `vector_db_ready.json` file is ready for ChromaDB ingestion:

```python
import chromadb
import json

# Load vector-ready data
with open('data/eval_benchmarks/vector_db_ready.json') as f:
    data = json.load(f)

# Create ChromaDB collection
client = chromadb.Client()
collection = client.create_collection("togmal_benchmarks")

# Add to database
collection.add(
    documents=data['documents'],
    metadatas=data['metadatas'],
    ids=data['ids']
)
```

Then use for similarity search:
```python
# Find similar questions
results = collection.query(
    query_texts=["What is photosynthesis?"],
    n_results=5
)

# Extract success rates for risk assessment
for metadata in results['metadatas'][0]:
    print(f"Similar question success rate: {metadata['success_rate']}")
```

## Advantages

✅ **Works in restricted networks** - No HuggingFace required
✅ **Real evaluation data** - Actual model predictions, not synthetic
✅ **Transparent sources** - All data from public GitHub repos
✅ **Extensible** - Easy to add new sources
✅ **Cacheable** - Avoids re-downloading data
✅ **Production-ready** - Handles rate limits, errors, edge cases

## Limitations

⚠️ **Limited model coverage** - Only 4-5 models vs all leaderboard models
⚠️ **Manual source addition** - Need to find and configure new sources
⚠️ **Data staleness** - Repos may become archived (like open-llm-leaderboard-report)
⚠️ **No auto-discovery yet** - Unlike GitHub benchmark discovery for training data

## Recommendations

1. **If HuggingFace is available**: Use original `infinite_benchmark_builder.py` - it's more comprehensive
2. **If HuggingFace is blocked**: Use this GitHub-based approach
3. **For production**: Run locally where HuggingFace isn't blocked, then deploy the vector database
4. **For development**: This approach works well for testing and prototyping

## Next Steps

1. ✅ Scrape evaluation results from GitHub repos
2. ✅ Build vector database with real model scores
3. 🔄 Add more benchmark sources (HumanEval, GSM8K, etc.)
4. 🔄 Implement web scraping for live leaderboards
5. 🔄 Expand model coverage to all 48 MMLU-Pro models
6. 🔄 Add automatic discovery of new evaluation repos
7. 🔄 Integrate with ChromaDB in the MCP server
