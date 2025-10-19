# ToGMAL Enhanced Clustering - Execution Log

**Date:** October 18, 2025  
**Status:** In Progress  
**Goal:** Upgrade from TF-IDF to Sentence Transformers for better cluster separation

---

## Setup Complete ✅

### Dependencies Installed
```bash
✓ sentence-transformers==5.1.1
✓ datasets==4.2.0
✓ scikit-learn (already installed)
✓ matplotlib==3.10.7
✓ seaborn==0.13.2
✓ torch==2.2.2
✓ transformers==4.57.1
✓ numpy==1.26.4 (downgraded from 2.x for compatibility)
```

---

## Step 1: Dataset Fetching ✅

**Script:** `enhanced_dataset_fetcher.py`

### Datasets Fetched

#### GOOD Cluster (LLMs Excel - >80% accuracy)
| Dataset | Source | Samples | Domain | Performance |
|---------|--------|---------|--------|-------------|
| squad_general_qa | rajpurkar/squad_v2 | 500 | general_qa | 86% |
| hellaswag_commonsense | Rowan/hellaswag | 500 | commonsense | 95% |
| **TOTAL** | | **1000** | | |

#### LIMITATIONS Cluster (LLMs Struggle - <70% accuracy)
| Dataset | Source | Samples | Domain | Performance |
|---------|--------|---------|--------|-------------|
| medical_qa | GBaker/MedQA-USMLE-4-options | 500 | medicine | 65% |
| code_defects | code_x_glue_cc_defect_detection | 500 | coding | ~60% |
| **TOTAL** | | **1000** | | |

#### HARMFUL Cluster (Safety Benchmarks)
| Dataset | Source | Samples | Status |
|---------|--------|---------|--------|
| toxic_chat | lmsys/toxic-chat | 0 | ⚠️ Config error (need to specify 'toxicchat0124') |

**Note:** Math dataset (hendrycks/competition_math) failed to load - will add alternative later

### Cache Location
```
/Users/hetalksinmaths/togmal/data/datasets/
├── squad_general_qa.json (500 entries)
├── hellaswag_commonsense.json (500 entries)
├── medical_qa.json (500 entries)
├── code_defects.json (500 entries)
└── combined_dataset.json (2000 entries total)
```

---

## Step 2: Enhanced Clustering (In Progress) 🔄

**Script:** `enhanced_clustering_trainer.py`

### Configuration
- **Embedding Model:** all-MiniLM-L6-v2 (sentence transformers)
- **Clustering Method:** K-Means
- **Number of Clusters:** 3 (targeting: good, limitations, harmful)
- **Total Samples:** 2000
- **Batch Size:** 32

### Progress
```
[1/4] Generating embeddings... (in progress)
├─ Model downloaded: all-MiniLM-L6-v2 (90.9MB)
├─ Progress: ~29% (18/63 batches)
└─ Estimated time: 1-2 minutes remaining

[2/4] Standardizing embeddings... (pending)
[3/4] K-Means clustering... (pending)
[4/4] Cluster analysis... (pending)
```

### Expected Output
1. **Clustering Results:**
   - Silhouette score (target: >0.4, vs current TF-IDF 0.25)
   - Davies-Bouldin score (lower is better)
   - Cluster assignments for each sample

2. **Cluster Analysis:**
   - Category distribution per cluster
   - Domain distribution per cluster
   - Purity scores (% of primary category)
   - Dangerous cluster identification (>70% limitations/harmful)

3. **Pattern Extraction:**
   - Keywords per cluster
   - Detection heuristics
   - Representative examples

4. **Export to ToGMAL:**
   - `./data/ml_discovered_tools.json` (for dynamic tools)
   - `./models/clustering/kmeans_model.pkl` (trained model)
   - `./models/clustering/embeddings.npy` (cached embeddings)

---

## Expected Results

### Hypothesis
With sentence transformers, we expect:

**Cluster 0: GOOD** (general QA + commonsense)
- Primary categories: 100% "good"
- Domains: general_qa, commonsense
- Keywords: question, answer, what, context
- Purity: >90%
- Dangerous: NO

**Cluster 1: LIMITATIONS - Medicine** (medical QA)
- Primary categories: ~100% "limitations"
- Domains: medicine
- Keywords: diagnosis, patient, treatment, symptom
- Purity: >85%
- Dangerous: YES → Will generate `check_medical_advice` tool

**Cluster 2: LIMITATIONS - Coding** (code defects)
- Primary categories: ~100% "limitations"
- Domains: coding
- Keywords: function, code, bug, vulnerability
- Purity: >85%
- Dangerous: YES → Will generate `check_code_security` tool

### Comparison to Baseline

| Metric | TF-IDF (Baseline) | Sentence Transformers (Target) |
|--------|------------------|--------------------------------|
| Silhouette Score | 0.25-0.26 | >0.4 (54-60% improvement) |
| Cluster Purity | ~71-100% | >85% (more consistent) |
| Cluster Separation | Moderate | High (semantic understanding) |
| Dangerous Clusters Identified | 2-3 | 2 (cleaner boundaries) |

---

## Next Steps (After Clustering Completes)

1. **✅ Verify Results**
   - Check silhouette score improvement
   - Review cluster assignments
   - Validate dangerous cluster identification

2. **✅ Export to Dynamic Tools**
   - Confirm `./data/ml_discovered_tools.json` generated
   - Verify format matches `ml_tools.py` expectations

3. **✅ Test Integration**
   ```bash
   # Test ML tools loading
   python -c "from togmal.ml_tools import get_ml_discovered_tools; import asyncio; print(asyncio.run(get_ml_discovered_tools()))"
   ```

4. **✅ Visualization**
   - Generate 2D PCA projection of clusters
   - Compare with TF-IDF clustering visually

5. **📝 Update Documentation**
   - Add results to CLUSTERING_TO_DYNAMIC_TOOLS_STRATEGY.md
   - Update requirements.txt with new dependencies

---

## Issues Encountered

### 1. NumPy Version Incompatibility ✅ FIXED
**Error:** PyTorch compiled with NumPy 1.x, but NumPy 2.x installed  
**Solution:** Downgraded to `numpy<2` (1.26.4)

### 2. HuggingFace Dataset Loading
**Issue:** Some datasets require specific configs
- `lmsys/toxic-chat` needs config: 'toxicchat0124' or 'toxicchat1123'
- `hendrycks/competition_math` not accessible (may be private)

**Workaround:** 
- Using 2000 samples (1000 good, 1000 limitations) is sufficient for proof-of-concept
- Can add more datasets later (see CLUSTERING_TO_DYNAMIC_TOOLS_STRATEGY.md for alternatives)

---

## File Artifacts Created

```
/Users/hetalksinmaths/togmal/
├── enhanced_dataset_fetcher.py (354 lines) ✅
├── enhanced_clustering_trainer.py (476 lines) ✅
├── CLUSTERING_TO_DYNAMIC_TOOLS_STRATEGY.md (628 lines) ✅
├── CLUSTERING_EXECUTION_LOG.md (THIS FILE)
│
├── data/
│   ├── datasets/
│   │   ├── combined_dataset.json ✅
│   │   └── *.json (individual dataset caches) ✅
│   │
│   ├── ml_discovered_tools.json (TO BE GENERATED)
│   └── training_results.json (TO BE GENERATED)
│
└── models/
    └── clustering/
        ├── kmeans_model.pkl (TO BE GENERATED)
        └── embeddings.npy (TO BE GENERATED)
```

---

## Timeline

- **15:00-15:15:** Dependencies installation
- **15:15-15:25:** Dataset fetching (completed)
- **15:25-15:35:** Embedding generation (in progress)
- **15:35-15:40:** Clustering & analysis (pending)
- **15:40-15:45:** Export to ML tools (pending)

**Estimated completion:** 15:40-15:45 SGT

---

## Success Criteria

- [x] Datasets fetched (2000 samples minimum)
- [ ] Sentence transformers embeddings generated
- [ ] Silhouette score >0.4 (vs 0.25 baseline)
- [ ] 2+ dangerous clusters identified
- [ ] ML tools cache exported
- [ ] Integration with existing `togmal_list_tools_dynamic` verified

**Status:** 60% complete
