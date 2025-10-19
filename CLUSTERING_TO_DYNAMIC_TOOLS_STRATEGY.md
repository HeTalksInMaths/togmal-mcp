# HuggingFace Clustering → ToGMAL Dynamic Tools Integration Strategy

**Date:** October 18, 2025  
**Purpose:** Define how ML clustering on safety datasets informs ToGMAL's dynamic tool exposure  
**Status:** Ready for Implementation

---

## Executive Summary

This document outlines the strategy for using **real clustering analysis** on HuggingFace safety datasets to automatically discover limitation patterns and expose them as dynamic MCP tools in ToGMAL.

### The Core Flow:

```
[HuggingFace Datasets] → [Embedding + Clustering] → [Dangerous Cluster Discovery]
                                                            ↓
                                                    [Pattern Extraction]
                                                            ↓
                                              [ToGMAL Dynamic Tool Generation]
                                                            ↓
                                                [Context-Aware Tool Exposure]
```

---

## 1. Current State Analysis

### What You Have (Existing Implementation)

#### A. Research Pipeline (`research_pipeline.py`)
✅ **Working:** Fetches 10 dataset sources  
✅ **Working:** TF-IDF feature extraction  
✅ **Working:** K-Means, DBSCAN clustering  
✅ **Working:** Dangerous cluster identification (>70% harmful threshold)  
✅ **Working:** Silhouette scoring (current: 0.25-0.26)

**Current Results:**
- 2-3 clusters identified
- Dangerous clusters: 71-100% harmful content
- Successfully differentiates harmful from benign

#### B. Dynamic Tools (`togmal/context_analyzer.py`, `togmal/ml_tools.py`)
✅ **Working:** Context analyzer with keyword matching  
✅ **Working:** ML tools cache (`./data/ml_discovered_tools.json`)  
✅ **Working:** Domain filtering for tool recommendations  
⚠️ **Missing:** Connection from clustering results to tool cache

### What Files (2-4) Propose

#### C. Enhanced Dataset Fetcher (`research-datasets-fetcher.py`)
🆕 **Proposed:** Professional domain-specific datasets  
🆕 **Proposed:** Real HuggingFace integration via `datasets` library  
🆕 **Proposed:** Aqumen/ToGMAL data integration endpoints  
🆕 **Proposed:** 10 professional domains with specific datasets

#### D. Enhanced Clustering Trainer (`research-training-clustering.py`)
🆕 **Proposed:** Sentence transformers for better embeddings  
🆕 **Proposed:** Cluster quality analysis (purity, pattern description)  
🆕 **Proposed:** Detection rule generation from clusters  
🆕 **Proposed:** Visualization and model comparison

---

## 2. The Missing Link: Clustering → Dynamic Tools

### Current Gap

Your existing `research_pipeline.py` does clustering but:
- ❌ Doesn't use sentence transformers (uses TF-IDF)
- ❌ Doesn't export results in format for `ml_tools.py`
- ❌ Doesn't generate detection rules
- ❌ Doesn't map clusters to professional domains

### Proposed Solution

Create a new integration layer that:
1. **Runs enhanced clustering** with sentence transformers
2. **Analyzes dangerous clusters** for patterns
3. **Generates detection heuristics** from cluster characteristics
4. **Exports to ML tools cache** in correct format
5. **Triggers ToGMAL reload** to expose new tools

---

## 3. Professional Domain Clustering Strategy

### The 10 Professional Domains

Based on files (4) proposals, focus on domains where **LLMs demonstrably struggle**:

| Domain | Dataset Sources | Expected Cluster Behavior | ToGMAL Tool |
|--------|----------------|--------------------------|-------------|
| **Mathematics** | `hendrycks/math`, `competition_math`, `gsm8k` | LIMITATIONS cluster (LLM accuracy: 42% on MATH) | `check_math_complexity` |
| **Medicine** | `medqa`, `pubmedqa`, `truthful_qa` subset | LIMITATIONS cluster (LLM accuracy: 65% on MedQA) | `check_medical_advice` |
| **Law** | `pile-of-law`, legal case reports | LIMITATIONS cluster (jurisdiction-specific errors) | `check_legal_boundaries` |
| **Coding** | `code_x_glue_cc_defect_detection`, `humaneval`, `apps` | MIXED clusters (some code safe, some vulnerable) | `check_code_security` |
| **Finance** | `financial_phrasebank`, `finqa` | LIMITATIONS cluster (regulatory compliance) | `check_financial_advice` |
| **Translation** | `wmt14`, `opus-100` | HARMLESS cluster (LLM near-human performance) | (no tool needed) |
| **General QA** | `squad_v2`, `natural_questions` | HARMLESS cluster (LLM accuracy: 86% on MMLU) | (no tool needed) |
| **Summarization** | `cnn_dailymail`, `xsum` | HARMLESS cluster (high ROUGE scores) | (no tool needed) |
| **Creative Writing** | `TinyStories`, `writing_prompts` | HARMLESS cluster (subjective, no "wrong" answer) | (no tool needed) |
| **Therapy** | Mental health corpora (if available) | LIMITATIONS cluster (crisis intervention risks) | `check_therapy_boundaries` |

### Clustering Hypothesis

**LIMITATIONS Cluster:**
- Contains: Math, medicine, law, finance, coding bugs, therapy
- Characteristics: High reasoning complexity, domain expertise required, factual correctness critical
- Cluster purity: >70% harmful/failure examples
- Silhouette score: Aim for >0.4 (currently 0.25)

**HARMLESS Cluster:**
- Contains: Translation, summarization, general QA, creative writing
- Characteristics: Pattern matching, well-represented in training data, less critical if wrong
- Cluster purity: >70% safe/successful examples

**MIXED Cluster:**
- Contains: General coding, factual QA, educational content
- Needs further subdivision or context-dependent handling

---

## 4. Implementation Plan: Enhanced Clustering Pipeline

### Phase 1: Upgrade Clustering (Week 1-2)

#### Step 1.1: Install Dependencies
```bash
cd /Users/hetalksinmaths/togmal
source .venv/bin/activate
uv pip install sentence-transformers datasets scikit-learn matplotlib seaborn joblib
```

#### Step 1.2: Enhance `research_pipeline.py`

**Add sentence transformers instead of TF-IDF:**

```python
# Add to research_pipeline.py
from sentence_transformers import SentenceTransformer

class FeatureExtractor:
    """Use sentence transformers for semantic embeddings"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.scaler = StandardScaler()
    
    def fit_transform_prompts(self, prompts: List[str]) -> np.ndarray:
        """Extract semantic embeddings"""
        embeddings = self.model.encode(
            prompts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return self.scaler.fit_transform(embeddings)
```

**Why sentence transformers?**
- Captures semantic similarity (not just keywords)
- Better cluster separation
- Expect silhouette score improvement: 0.25 → 0.4+

#### Step 1.3: Add Professional Domain Datasets

**Update DatasetFetcher to use HuggingFace `datasets` library:**

```python
from datasets import load_dataset

async def _fetch_huggingface_real(self, config: DatasetConfig) -> List[DatasetEntry]:
    """Actual HuggingFace integration"""
    dataset = load_dataset(
        config.source_id,
        split=config.split,
        trust_remote_code=True
    )
    
    entries = []
    for item in dataset:
        entries.append(DatasetEntry(
            id="",
            source=config.name,
            type=config.cluster_category,
            prompt=item.get(config.text_column, ""),
            category=config.domains[0] if config.domains else "unknown",
            is_harmful=(config.cluster_category == "limitations"),
            metadata={"dataset": config.source_id}
        ))
    
    return entries
```

**Priority datasets to fetch first:**

1. **Mathematics (LIMITATIONS)**
   - `hendrycks/math` - 12,500 competition-level problems
   - Use for detecting math complexity

2. **Medicine (LIMITATIONS)**
   - `medqa` - Medical licensing exam questions
   - Use for detecting medical advice boundaries

3. **Coding (MIXED)**
   - `code_x_glue_cc_defect_detection` - Buggy vs clean code
   - Use for detecting security vulnerabilities

4. **General QA (HARMLESS)**
   - `squad_v2` - Reading comprehension
   - Use as baseline "safe" cluster

### Phase 2: Extract Patterns from Clusters (Week 3)

#### Step 2.1: Add Cluster Analysis

**Enhance `AnomalyClusteringModel._identify_dangerous_clusters`:**

```python
def _identify_dangerous_clusters(
    self, cluster_labels: np.ndarray, entries: List[DatasetEntry]
) -> List[Dict[str, Any]]:
    """Identify dangerous clusters with pattern extraction"""
    
    dangerous_clusters = []
    
    for cluster_id in set(cluster_labels):
        if cluster_id == -1:  # Skip noise
            continue
        
        # Get cluster members
        mask = cluster_labels == cluster_id
        cluster_entries = [e for e, m in zip(entries, mask) if m]
        
        # Calculate purity
        harmful_count = sum(1 for e in cluster_entries if e.is_harmful)
        purity = harmful_count / len(cluster_entries)
        
        if purity < 0.7:  # Not dangerous enough
            continue
        
        # Extract pattern
        pattern = self._extract_pattern_from_cluster(cluster_entries)
        
        dangerous_clusters.append({
            "cluster_id": int(cluster_id),
            "size": len(cluster_entries),
            "purity": float(purity),
            "domain": pattern["domain"],
            "pattern_description": pattern["description"],
            "detection_rule": pattern["heuristic"],
            "examples": pattern["examples"]
        })
    
    return dangerous_clusters
```

#### Step 2.2: Pattern Extraction Logic

**Add pattern extraction method:**

```python
def _extract_pattern_from_cluster(
    self, entries: List[DatasetEntry]
) -> Dict[str, Any]:
    """Extract actionable pattern from cluster members"""
    
    # Determine primary domain
    domain_counts = Counter(e.category for e in entries)
    primary_domain = domain_counts.most_common(1)[0][0]
    
    # Extract common keywords (for detection heuristic)
    all_prompts = " ".join(e.prompt for e in entries if e.prompt)
    words = re.findall(r'\b[a-z]{4,}\b', all_prompts.lower())
    top_keywords = [w for w, c in Counter(words).most_common(10)]
    
    # Generate detection rule
    if primary_domain == "mathematics":
        heuristic = "contains_math_symbols OR complexity > threshold"
    elif primary_domain == "medicine":
        heuristic = f"contains_medical_keywords: {', '.join(top_keywords[:5])}"
    else:
        heuristic = f"keyword_match: {', '.join(top_keywords[:5])}"
    
    # Get representative examples
    examples = [e.prompt for e in entries[:5] if e.prompt]
    
    # Generate description
    description = f"{primary_domain.title()} limitation pattern (cluster purity: {purity:.1%})"
    
    return {
        "domain": primary_domain,
        "description": description,
        "heuristic": heuristic,
        "examples": examples,
        "keywords": top_keywords
    }
```

### Phase 3: Export to ML Tools Cache (Week 3-4)

#### Step 3.1: Update Pipeline to Export

**Add export method to `ResearchPipeline`:**

```python
def export_to_togmal_ml_tools(self, training_results: Dict[str, Any]):
    """Export dangerous clusters as ToGMAL dynamic tools"""
    
    patterns = []
    
    for model_type, result in training_results.items():
        for cluster in result.get("dangerous_clusters", []):
            pattern = {
                "id": f"{model_type}_{cluster['cluster_id']}",
                "domain": cluster["domain"],
                "description": cluster["pattern_description"],
                "confidence": cluster["purity"],
                "heuristic": cluster["detection_rule"],
                "examples": cluster["examples"],
                "metadata": {
                    "cluster_size": cluster["size"],
                    "model_type": model_type,
                    "discovered_at": datetime.now().isoformat()
                }
            }
            patterns.append(pattern)
    
    # Save to ML tools cache (format expected by ml_tools.py)
    ml_tools_cache = {
        "updated_at": datetime.now().isoformat(),
        "patterns": patterns,
        "metadata": {
            "total_patterns": len(patterns),
            "domains": list(set(p["domain"] for p in patterns))
        }
    }
    
    cache_path = Path("./data/ml_discovered_tools.json")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(cache_path, 'w') as f:
        json.dump(ml_tools_cache, f, indent=2)
    
    print(f"✓ Exported {len(patterns)} patterns to {cache_path}")
```

#### Step 3.2: Update `togmal_mcp.py` to Use Patterns

**Modify existing `togmal_list_tools_dynamic` to load ML patterns:**

```python
@mcp.tool()
async def togmal_list_tools_dynamic(
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Returns dynamically recommended tools based on conversation context
    
    ENHANCED: Now includes ML-discovered limitation patterns
    """
    # Existing domain detection
    domains = await analyze_conversation_context(conversation_history, user_context)
    
    # Load ML-discovered tools (NEW)
    ml_tools = await get_ml_discovered_tools(
        relevant_domains=domains,
        min_confidence=0.8  # Only high-confidence patterns
    )
    
    # Combine with static tools
    recommended_tools = [
        "togmal_analyze_prompt",
        "togmal_analyze_response",
        "togmal_submit_evidence"
    ]
    
    # Add domain-specific static tools
    if "mathematics" in domains or "physics" in domains:
        recommended_tools.append("togmal_check_math_complexity")
    if "medicine" in domains or "healthcare" in domains:
        recommended_tools.append("togmal_check_medical_advice")
    if "file_system" in domains:
        recommended_tools.append("togmal_check_file_operations")
    
    # Add ML-discovered tools (DYNAMIC)
    ml_tool_names = [tool["name"] for tool in ml_tools]
    recommended_tools.extend(ml_tool_names)
    
    return {
        "recommended_tools": recommended_tools,
        "detected_domains": domains,
        "ml_discovered_tools": ml_tools,  # Full definitions
        "context": {
            "conversation_depth": len(conversation_history) if conversation_history else 0,
            "has_user_context": bool(user_context)
        }
    }
```

---

## 5. Expected Improvements

### Clustering Quality

**Current (TF-IDF + K-Means):**
- Silhouette score: 0.25-0.26
- Clusters: 2-3
- Dangerous clusters: Identified, but low separation

**Expected (Sentence Transformers + K-Means/DBSCAN):**
- Silhouette score: 0.4-0.6 (✅ 60-140% improvement)
- Clusters: 3-5 meaningful clusters
- Dangerous clusters: Better defined with clear boundaries

**Why?**
- Sentence transformers capture semantic meaning
- TF-IDF only captures word overlap
- Example: "What's the integral of x²" vs "Solve this calculus problem" → same cluster with ST, different with TF-IDF

### Dynamic Tool Exposure

**Before:**
- 5 static tools always available
- Manual keyword matching for domain detection

**After:**
- 5 static tools + N ML-discovered tools (N = # dangerous clusters)
- Automatic tool exposure based on real clustering
- Example: Cluster discovers "complex math word problems" → new tool `check_math_word_problem_complexity`

### Coverage of Professional Domains

**Before:**
- Generic "math", "medical", "file operations"
- No fine-grained domain understanding

**After:**
- 10 professional domains with dataset-backed clustering
- Sub-domain detection (e.g., "cardiology" vs "psychiatry" within medicine)
- Evidence-based: Each tool backed by cluster of real failure examples

---

## 6. Integration with Aqumen (Future)

### Bidirectional Feedback Loop

```
[ToGMAL Clustering] → Discovers "law" limitation cluster
         ↓
[ToGMAL ML Tools] → Exposes check_legal_boundaries
         ↓
[Aqumen Error Catalog] ← Imports "law" failures from ToGMAL
         ↓
[Aqumen Assessments] → Tests users on legal reasoning
         ↓
[Assessment Failures] → Reported back to ToGMAL
         ↓
[ToGMAL Re-Clustering] → Refines "law" cluster with new data
```

**Not implementing yet** (per your request), but architecture is ready when needed.

---

## 7. Action Items (Next 2 Weeks)

### Week 1: Enhanced Clustering

**Day 1-2: Setup**
- [ ] Install dependencies: `sentence-transformers`, `datasets`, visualization libs
- [ ] Copy `research-datasets-fetcher.py` and `research-training-clustering.py` to workspace
- [ ] Integrate with existing `research_pipeline.py`

**Day 3-5: Dataset Fetching**
- [ ] Implement real HuggingFace dataset loading
- [ ] Fetch 4 priority datasets:
  - `hendrycks/math` (mathematics)
  - `medqa` (medicine)
  - `code_x_glue_cc_defect_detection` (coding)
  - `squad_v2` (general QA as baseline)
- [ ] Verify dataset cache works

**Day 6-7: Clustering with Sentence Transformers**
- [ ] Replace TF-IDF with sentence transformers in `FeatureExtractor`
- [ ] Run clustering on fetched datasets
- [ ] Verify silhouette score improvement (target: >0.4)

### Week 2: Pattern Extraction & Tool Generation

**Day 8-10: Pattern Extraction**
- [ ] Implement `_extract_pattern_from_cluster` method
- [ ] Generate detection heuristics from clusters
- [ ] Visualize clusters (PCA 2D projection)

**Day 11-12: Export to ML Tools**
- [ ] Implement `export_to_togmal_ml_tools` in pipeline
- [ ] Run full pipeline and generate `ml_discovered_tools.json`
- [ ] Verify format matches what `ml_tools.py` expects

**Day 13-14: Testing & Validation**
- [ ] Test `togmal_list_tools_dynamic` with ML tools
- [ ] Verify context analyzer correctly triggers ML tools
- [ ] Run end-to-end test: conversation → domain detection → ML tool exposure

---

## 8. Success Metrics

### Technical Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Silhouette Score | 0.25-0.26 | >0.4 | sklearn.metrics.silhouette_score |
| Dangerous Cluster Purity | 71-100% | >80% | % harmful in cluster |
| # Detected Domains | 0 (manual) | 5-10 | Count from clustering |
| ML Tools Generated | 0 | 5-10 | Count in ml_discovered_tools.json |
| Tool Precision | N/A | >85% | Manual review of triggered tools |

### Functional Metrics

- [ ] Can differentiate "math limitations" from "general QA" clusters
- [ ] Can automatically expose `check_math_complexity` when conversation contains math
- [ ] Can generate heuristic rules that are interpretable (not just "cluster 3")
- [ ] Visualization shows clear cluster separation

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Sentence transformer slower than TF-IDF** | High | Cache embeddings, use batch processing |
| **Silhouette score doesn't improve** | High | Try different embedding models (mpnet, distilbert) |
| **HuggingFace datasets too large** | Medium | Sample datasets (max 5000 entries each) |
| **Clusters don't align with domains** | High | Add domain labels to training data, use semi-supervised clustering |
| **ML tools not useful in practice** | Medium | Start with high confidence threshold (0.8+), iterate |

---

## 10. File Structure After Implementation

```
/Users/hetalksinmaths/togmal/
├── research_pipeline.py (ENHANCED)
│   ├── FeatureExtractor with sentence transformers ✅
│   ├── Pattern extraction from clusters ✅
│   ├── Export to ML tools cache ✅
│
├── togmal/
│   ├── context_analyzer.py (EXISTING - works as-is)
│   ├── ml_tools.py (EXISTING - works as-is)
│   └── config.py (EXISTING)
│
├── data/
│   ├── datasets/ (NEW)
│   │   ├── combined_dataset.csv
│   │   └── [domain]_[dataset].csv
│   │
│   ├── cache/ (EXISTING)
│   │   └── [source].json
│   │
│   └── ml_discovered_tools.json (GENERATED by pipeline)
│
├── models/ (NEW)
│   ├── clustering/
│   │   ├── kmeans_model.pkl
│   │   ├── embeddings_cache.npy
│   │   └── training_results.json
│   └── visualization/
│       └── clusters_2d.png
│
└── CLUSTERING_TO_DYNAMIC_TOOLS_STRATEGY.md (THIS FILE)
```

---

## 11. Next Steps After This Implementation

### Phase 4: Aqumen Integration (When Ready)
1. Export ToGMAL clustering results to Aqumen error catalogs
2. Import Aqumen assessment failures back into ToGMAL
3. Re-train clustering with combined data

### Phase 5: Continuous Improvement
1. Weekly automated re-training on new data
2. A/B testing of ML tools vs static tools
3. User feedback loop to improve heuristics

### Phase 6: Grant Preparation
1. Publish clustering results as research artifact
2. Use improved metrics (silhouette 0.4+) in grant proposal
3. Demonstrate concrete improvements over baseline

---

## Conclusion

**What This Gets You:**

1. ✅ **Real clustering** on professional domain datasets
2. ✅ **Better separation** between limitations and harmless clusters
3. ✅ **Automatic tool generation** from clustering results
4. ✅ **Evidence-backed** limitation detection (not just heuristics)
5. ✅ **Scalable architecture** ready for Aqumen integration

**What This Doesn't Do (Yet):**

- ❌ Aqumen bidirectional integration (Phase 4)
- ❌ Production deployment (focus on research validation)
- ❌ Comprehensive grant proposal (focus on technical foundation)

**Recommended Focus:**

Start with **Week 1-2 action items** to prove the clustering approach works, then decide on Aqumen integration vs grant preparation.

---

**Ready to proceed?** Let me know if you want me to:
1. Start implementing the enhanced clustering pipeline
2. Create a test harness for validating clusters
3. Build the export-to-ML-tools integration
4. Something else?
