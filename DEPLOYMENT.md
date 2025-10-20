# Deployment Guide for Hugging Face Spaces

## Problem Solved

**Issue**: Hugging Face Spaces rejects files larger than 10 MiB without Git LFS.

**Previous setup**: 
- ❌ Committed 94 MB of vector database files to git
- ❌ Committed 12 MB of MMLU results JSON

**New setup**:
- ✅ Build vector database on first app launch
- ✅ Only commit code files (~50 KB)
- ✅ Database builds in ~3-5 minutes on first launch

## How It Works

1. **First Launch**: App detects empty database and builds it from HuggingFace datasets
2. **Subsequent Launches**: App loads existing database from Hugging Face persistent storage

## Files Excluded from Git

Added to `.gitignore`:
```
data/benchmark_vector_db/          # ChromaDB vector database (builds automatically)
data/benchmark_results/mmlu_real_results.json  # Large benchmark file (not needed)
```

## Deployment Steps

### 1. Clean Git History (Remove Large Files)

```bash
cd Togmal-demo

# Remove large files from git tracking
git rm -r --cached data/benchmark_vector_db/
git rm --cached data/benchmark_results/mmlu_real_results.json

# Commit the removal
git add .gitignore app.py
git commit -m "Remove large files - build database on startup instead"
```

### 2. Clean Git History (Optional - for smaller repo)

If files were already committed to history:

```bash
# Install git-filter-repo if needed
brew install git-filter-repo  # macOS
# or: pip install git-filter-repo

# Remove files from entire history
git filter-repo --path data/benchmark_vector_db --invert-paths
git filter-repo --path data/benchmark_results/mmlu_real_results.json --invert-paths

# Force push (be careful!)
git push origin main --force
```

### 3. Push to Hugging Face

```bash
# Push to Hugging Face Spaces
git remote add hf https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo
git push hf main
```

## First Launch Behavior

When deployed to Hugging Face Spaces:

1. ⏱️ App starts - database is empty
2. 📥 Downloads benchmark datasets from HuggingFace:
   - GPQA Diamond (~200 questions)
   - MMLU-Pro (1000 questions sampled)
   - MATH (500 questions sampled)
3. 🧠 Generates embeddings using `all-MiniLM-L6-v2`
4. 💾 Stores in ChromaDB (persistent across restarts)
5. ✅ Ready to use!

**Time**: 3-5 minutes on Hugging Face hardware

## Persistent Storage

Hugging Face Spaces provides persistent storage for:
- `/data` directory (survives app restarts)
- Our database is stored in `./data/benchmark_vector_db/`

## Why This is Better

| Metric | Before | After |
|--------|--------|-------|
| Git repo size | ~100 MB | ~50 KB |
| Files in git | 94 MB binaries | Code only |
| First launch | Instant | 3-5 min build |
| Subsequent | Instant | Instant |
| Maintainability | Hard to update DB | Rebuild anytime |

## Updating the Database

To rebuild with new data:

```python
# In app.py, add force rebuild option:
FORCE_REBUILD = os.getenv("FORCE_REBUILD", "false").lower() == "true"

if db.collection.count() == 0 or FORCE_REBUILD:
    db.build_database(...)
```

Then set environment variable in Hugging Face Space settings:
```
FORCE_REBUILD=true
```

## Troubleshooting

### "Database build failed"
- Check HuggingFace dataset access (may need authentication)
- Check space has enough memory (upgrade to larger instance)

### "Out of memory during build"
- Reduce `max_samples_per_dataset` in `app.py`
- Use smaller embedding model (e.g., `all-MiniLM-L6-v2`)

### "Database not persisting"
- Ensure database path is `./data/` (Hugging Face persistent dir)
- Check space hasn't been reset

## Local Development

For local testing:

```bash
# Install dependencies
pip install -r requirements.txt

# Run app (builds database on first launch)
python app.py
```

Database will be built once, then reused on subsequent runs.
