# ToGMAL Complete Architecture: 3-Tier System

## Overview

ToGMAL uses a **3-tier architecture** for intelligent risk assessment:

```
Tier 1: Lightweight Pre-Screening (MCP tool)
  ↓ (if risky)
Tier 2: Deep Analysis (ToGMAL Skill)
  ↓ (uses)
Tier 3: Data Fetching (MCP tools)
```

---

## Tier 1: Lightweight Pre-Screening ⚡

**Purpose:** Fast, automatic screening of EVERY prompt before deciding to invoke heavy analysis.

**Component:** `quick_risk_check` MCP tool (uses `lightweight_prompt_checker.py`)

**How it works:**
- Regex-based pattern matching
- No data loading required
- < 1ms response time
- Runs on EVERY user prompt automatically

**What it detects:**
- Code patterns (mutability, indexing, vectorization)
- Difficult domains (quantum, medical, physics)
- Multi-step complexity
- Unit conversions (CoT failure indicator)
- Dangerous domains (medical, legal)

**Returns:**
```json
{
  "should_analyze": true,     // Should invoke Skill?
  "risk_level": "MEDIUM",     // NONE, LOW, MEDIUM, HIGH, CRITICAL
  "triggers": ["code_pattern:mutability_risk"],
  "risk_score": 0.3,
  "confidence": 0.7,
  "recommended_action": "Invoke ToGMAL Skill..."
}
```

**Example:**
```python
Input: "df['new_col'] = df['old_col'] * 2"
Output: {
  "should_analyze": true,
  "risk_level": "MEDIUM",
  "triggers": ["code_pattern:mutability_risk"],
  "recommended_action": "Invoke ToGMAL Skill for pattern verification"
}
```

---

## Tier 2: Deep Analysis (ToGMAL Skill) 🎯

**Purpose:** Comprehensive, data-driven risk assessment using benchmark evidence.

**Component:** `skills/togmal-risk-assessment/SKILL.md`

**When activated:**
- User explicitly asks for analysis
- OR `quick_risk_check` returns `should_analyze: true`

**What it does:**
1. **Analyzes task context** (domain, complexity, requirements)
2. **Queries MCP for data** (calls Tier 3 tools)
3. **Applies error pattern matching** (32 patterns from 4 sources)
4. **Computes two-dimensional risk:**
   - Dimension 1: Historical difficulty (success rates)
   - Dimension 2: Error pattern severity
5. **Generates detailed report** with evidence and recommendations

**Data it uses (from MCP):**
- 13,000 benchmark questions
- Real success rates across 68 models
- 32 discovered error patterns
- 22 universal failures
- Domain-specific statistics

**Example workflow:**
```
1. Skill: "This is pandas code, let me check benchmark data"
2. Skill calls MCP: search_by_domain("Pandas", limit=20)
3. MCP returns: 20 Pandas questions, avg success 62%
4. Skill: "Code has mutability pattern, combining with 62% success = MEDIUM risk"
5. Skill generates: Comprehensive report with recommendations
```

---

## Tier 3: Data Fetching (MCP Tools) 📊

**Purpose:** Provide raw benchmark data - NO analysis, NO interpretation.

**Component:** `togmal_mcp_refactored.py`

**Tools provided:**
1. `quick_risk_check` - Tier 1 lightweight screening
2. `fetch_question` - Get specific question by ID
3. `query_questions` - Filter by benchmark/difficulty/domain
4. `get_universal_failures` - Questions all models failed
5. `get_error_patterns_catalog` - All 32 patterns
6. `get_statistics` - Dataset summary
7. `search_by_domain` - Domain-specific search

**Data sources:**
- `mcp_datastore/` - 116 MB of indexed JSON files
- `data/unified_database_complete.json` - 29 MB source data

**Example:**
```python
Tool: search_by_domain("Pandas", limit=5)

Returns (raw JSON):
{
  "domain": "Pandas",
  "count": 5,
  "questions": [
    {
      "question_id": "ds1000_pandas_42",
      "success_rate": 0.62,
      "error_patterns": [],
      ...
    },
    ...
  ]
}
```

---

## Complete Flow Example

### Scenario: User writes pandas code

```python
User: "result = df.groupby('category').sum()"
```

### Step-by-Step:

**1. Lightweight Pre-Screening (Automatic)**
```
Claude (or IDE) calls: quick_risk_check(prompt)
  ↓
MCP Tier 1 tool:
  - Detects: code_pattern:index_risk (missing .reset_index())
  - Returns: should_analyze=true, risk_level=MEDIUM
  ↓
Decision: Invoke ToGMAL Skill
```

**2. ToGMAL Skill Activates**
```
Claude loads: skills/togmal-risk-assessment/SKILL.md
  ↓
Skill procedure Step 1: Extract task details
  - Domain: Pandas
  - Task: DataFrame operation
  ↓
Skill procedure Step 2: Query MCP for data
  - Calls: search_by_domain("Pandas", limit=20)
  - Calls: get_error_patterns_catalog()
```

**3. MCP Data Fetching**
```
MCP Tier 3 tools:
  - search_by_domain returns: 20 Pandas questions
  - Average success rate: 62%
  - get_error_patterns_catalog returns: 32 patterns
```

**4. Skill Analysis**
```
Skill procedure Step 3: Analyze data
  - Historical difficulty: 62% success (MEDIUM)
  - Pattern match: index_persistence (CRITICAL)
  - Combined: MEDIUM-HIGH risk
  ↓
Skill procedure Step 4: Compute risk
  - Formula: 1 CRITICAL pattern + 62% success = MEDIUM-HIGH
  ↓
Skill procedure Step 5: Generate report
  - Evidence: 20 similar questions, avg 62% success
  - Pattern: Missing .reset_index() (1,856 cases in dataset)
  - Recommendation: Add .reset_index() after groupby
```

**5. User Receives Report**
```markdown
## ToGMAL Risk Assessment

### Task Analysis
- Domain: Pandas
- Code: `result = df.groupby('category').sum()`

### Benchmark Data (via MCP)
- Similar Questions: 20
- Average Success Rate: 62%
- Domain Difficulty: MEDIUM

### Error Pattern Analysis (via Skill)
**index_persistence** (CRITICAL)
- Description: Missing .reset_index() after groupby
- Evidence: 1,856 cases in DS-1000 dataset
- Recommendation: Add .reset_index()

### Overall Risk: MEDIUM-HIGH

⚠️ Recommendation:
`result = df.groupby('category').sum().reset_index()`
```

---

## Why 3 Tiers?

### Tier 1 (Lightweight) Benefits:
- **Fast**: < 1ms, can run on every prompt
- **No data needed**: Pure regex, works offline
- **Filters out safe prompts**: 70% of prompts skip deep analysis
- **Low cost**: No API calls, no data loading

### Tier 2 (Skill) Benefits:
- **Intelligent**: Claude reasons about risk
- **Transparent**: Shows evidence and reasoning
- **Adaptable**: Can handle novel situations
- **Maintainable**: Update procedures in markdown, not code

### Tier 3 (MCP) Benefits:
- **Factual**: Real benchmark data, not assumptions
- **Comprehensive**: 13,000 questions, 68 models
- **Reusable**: Same data for multiple analysis types
- **Extensible**: Easy to add more benchmarks

---

## Data Requirements

### For Tier 1 (Lightweight):
- ✅ **Nothing!** Pure code, no data files needed

### For Tier 2 (Skill):
- ✅ **Nothing!** Just markdown procedures

### For Tier 3 (MCP):
- ⚠️ **Required:** `mcp_datastore/` (116 MB, local only)
- ⚠️ **Required:** `data/unified_database_complete.json` (29 MB, local only)
- ✅ **Build once:** `python3 build_mcp_datastore.py`

### For Semantic Search (Optional):
- ❌ **Not working:** ChromaDB blocked (HuggingFace/AWS issues)
- ✅ **Alternative:** TF-IDF with `build_simple_vector_store.py`
- ⏳ **Future:** OpenAI embeddings (requires API key)

---

## Usage Patterns

### Pattern 1: Automatic Screening
```
User types code → IDE calls quick_risk_check
  ↓
If risky → Show inline warning
If very risky → Suggest full ToGMAL analysis
```

### Pattern 2: Explicit Analysis
```
User: "Analyze this code for risk"
  ↓
Claude activates ToGMAL Skill
  ↓
Skill calls MCP tools for data
  ↓
Comprehensive report generated
```

### Pattern 3: Learning Mode
```
User: "Why is this risky?"
  ↓
Claude uses quick_risk_check to identify patterns
  ↓
Explains pattern without full analysis
  ↓
Offers: "Want full benchmark comparison?"
```

---

## File Structure

```
togmal-mcp/
├── # Tier 1: Lightweight Screening
│   ├── lightweight_prompt_checker.py    # Regex-based risk detection
│   └── togmal_mcp_refactored.py         # Includes quick_risk_check tool
│
├── # Tier 2: Deep Analysis
│   └── skills/togmal-risk-assessment/
│       └── SKILL.md                     # Analysis procedures (13 KB)
│
├── # Tier 3: Data Fetching
│   ├── togmal_mcp_refactored.py         # MCP server (6 data tools)
│   └── mcp_datastore/                   # Indexed data (116 MB, gitignored)
│       ├── questions_by_id.json
│       ├── questions_by_domain.json
│       ├── error_patterns_catalog.json
│       └── ... (8 files total)
│
├── # Data Building
│   ├── build_mcp_datastore.py           # Build Tier 3 data
│   ├── build_complete_unified_db.py     # Build source data
│   └── build_simple_vector_store.py     # TF-IDF search (offline)
│
├── # Testing
│   ├── test_mcp_skill_flow.py           # Full flow demo
│   └── lightweight_prompt_checker.py    # Tests included
│
└── # Documentation
    ├── ARCHITECTURE.md                  # Skills + MCP overview
    ├── ARCHITECTURE_V2.md              # This file (3-tier detail)
    └── README.md                        # Project overview
```

---

## Key Differences from Original Vision

### Original (Monolithic MCP):
```
User prompt → MCP analyzes everything → Returns result
```
- Hard to update
- Not transparent
- Can't handle novel situations

### Current (3-Tier):
```
Tier 1: Quick check (fast, automatic)
  ↓ (if needed)
Tier 2: Skill analysis (smart, transparent)
  ↓ (uses)
Tier 3: MCP data (factual, comprehensive)
```
- Fast for safe prompts
- Intelligent for risky prompts
- Data-driven for evidence
- Easy to update (edit SKILL.md)
- Transparent reasoning

---

## Next Steps

1. **Test Tier 1:** Run `python3 lightweight_prompt_checker.py`
2. **Build Tier 3 data:** Run `python3 build_mcp_datastore.py`
3. **Test full flow:** Run `python3 test_mcp_skill_flow.py`
4. **Deploy MCP:** `python3 togmal_mcp_refactored.py`
5. **Use with Claude Code:** Skills auto-discovered from `skills/`

---

## FAQ

**Q: Where are the embeddings?**
A: Blocked by HuggingFace/AWS. Use TF-IDF alternative (`build_simple_vector_store.py`) or wait for fix.

**Q: Where is the large database?**
A: Local only, in `mcp_datastore/` (116 MB, gitignored). Rebuild with `build_mcp_datastore.py`.

**Q: Should Tier 1 be in MCP or separate?**
A: In MCP! It's a tool for data fetching (risk indicators), just very lightweight.

**Q: Can Tier 1 run without Tier 3?**
A: Yes! Pure regex, no data needed. Perfect for offline/fast screening.

**Q: When does Tier 2 (Skill) activate?**
A: When Tier 1 says `should_analyze: true` OR user explicitly asks.

**Q: Can I use this without the Skill?**
A: Yes, but you only get quick checks + raw data. Skill provides intelligence.
