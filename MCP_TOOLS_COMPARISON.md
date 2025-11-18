# ToGMAL MCP Tools & Architecture Comparison

## Current Branch Status: ❌ NO MCP SERVER

**Branch:** `claude/improve-checker-recall-01LWYCMoZrc4vC8SWpFgyBzH`

**What's here:**
- ✅ Data files (13K questions, 104 MB)
- ✅ JSON datastore (56 MB)
- ✅ Build scripts
- ✅ Lightweight checker (improved 4x)
- ❌ **NO MCP server**
- ❌ **NO skill files**
- ❌ **NO MCP tools**

---

## Previous Branch: ✅ FULL MCP + SKILL ARCHITECTURE

**Branch:** `claude/infinite-vector-db-builder-01Kwz7B7QeCmK5QDGguvUgzp`

**What was there:**
- ✅ Full MCP server implementation
- ✅ Claude skill for risk assessment reasoning
- ✅ Two architectural approaches (original + refactored)

---

# MCP Tools Architecture Evolution

## Version 1: Original MCP (Analysis-Heavy)

**File:** `togmal_mcp.py`

**Philosophy:** MCP does both DATA + ANALYSIS

### Tools (7 total):

1. **togmal_analyze_prompt**
   - **Purpose:** Analyze user prompts for potential LLM limitations
   - **Features:**
     - Heuristic anomaly detection
     - Pattern matching for problematic scenarios
     - ML-enhanced detection (clustering)
     - Context-aware analysis
   - **Returns:** Risk level + interventions + recommendations

2. **togmal_analyze_response**
   - **Purpose:** Analyze LLM responses for issues
   - **Features:**
     - Detect hedging language
     - Check for hallucination indicators
     - Validate reasoning quality
   - **Returns:** Response quality assessment

3. **togmal_submit_evidence**
   - **Purpose:** Submit evidence of LLM failures to build taxonomy
   - **Features:**
     - Record prompt-response pairs
     - Store error patterns
     - Privacy-preserving hashing
   - **Returns:** Confirmation + evidence ID

4. **togmal_get_taxonomy**
   - **Purpose:** Retrieve stored taxonomy entries
   - **Features:**
     - Filter by category, severity, domain
     - Search evidence database
   - **Returns:** Matching taxonomy entries

5. **togmal_get_statistics**
   - **Purpose:** Get taxonomy statistics
   - **Returns:** Summary of collected evidence

6. **togmal_get_recommended_checks**
   - **Purpose:** Get recommended checks based on conversation context
   - **Features:**
     - Context-aware recommendations
     - Conversation history analysis
   - **Returns:** Suggested checks for current conversation

7. **togmal_list_tools_dynamic**
   - **Purpose:** Dynamically list available tools based on ML clustering
   - **Features:**
     - ML-discovered dangerous clusters
     - Confidence-based tool availability
   - **Returns:** Contextual tool list

**Key Features:**
- ✅ ML-enhanced detection (clustering, pattern discovery)
- ✅ Context-aware recommendations
- ✅ Evidence submission system
- ✅ Dynamic tool availability
- ❌ Heavy logic in MCP (analysis + data mixed)
- ❌ Harder to customize reasoning

---

## Version 2: Refactored MCP (Data-Only) + Skill (Analysis)

**Files:**
- `togmal_mcp_refactored.py` (MCP server)
- `skills/togmal-risk-assessment/SKILL.md` (Claude skill)

**Philosophy:** Separation of concerns
- **MCP:** Pure data provider
- **Skill:** Analysis procedures and reasoning

### MCP Tools (7 total) - Data Only:

1. **quick_risk_check**
   - **Purpose:** LIGHTWEIGHT pre-screening (lightweight checker)
   - **Features:**
     - Fast regex pattern matching
     - No data loading needed
     - Runs on every prompt
   - **Returns:** Risk level + whether to invoke full analysis
   - **Performance:** 32.9% recall (4x better than original)

2. **fetch_question**
   - **Purpose:** Get a specific benchmark question by ID
   - **Input:** `question_id` (e.g., "mmlu_pro_math_001")
   - **Returns:**
     - Question text
     - Difficulty & success rate
     - Model scores (7 top models)
     - Error patterns (if available)

3. **query_questions**
   - **Purpose:** Query questions by filters
   - **Filters:**
     - `benchmark`: MMLU-Pro or DS-1000
     - `difficulty`: Easy/Medium/Hard/Expert/Nearly_Impossible
     - `domain`: math, physics, Pandas, etc.
     - `with_errors`: Only questions with error patterns
     - `limit`: Max results (default 10)
   - **Returns:** Matching questions

4. **get_universal_failures**
   - **Purpose:** Get questions that ALL models failed (0% success rate)
   - **Input:** `limit` (default 10)
   - **Returns:**
     - 22 universally difficult questions
     - From 37 top models (GPT-4, Claude 3.5, Gemini, etc.)

5. **get_error_patterns_catalog**
   - **Purpose:** Get catalog of all discovered error patterns
   - **Returns:** 32 patterns from 4 sources:
     - **8 DS-1000 patterns** (pandas/numpy code issues)
     - **20 universal failure patterns** (complex engineering)
     - **2 CoT failure patterns** (unit conversion, ambiguity)
     - **2 ML-discovered clusters** (coding, medicine - 100% risk)

6. **get_statistics**
   - **Purpose:** Get dataset summary statistics
   - **Returns:**
     - Total questions: 13,000
     - Benchmarks: MMLU-Pro (12K), DS-1000 (1K)
     - Difficulty distribution
     - Error pattern coverage
     - Model coverage (7-68 models)

7. **search_by_domain**
   - **Purpose:** Search all questions in a specific domain
   - **Input:** `domain` (e.g., "math", "Pandas", "physics")
   - **Returns:** All questions in that domain (with limit)

### Claude Skill - Analysis Procedures

**File:** `skills/togmal-risk-assessment/SKILL.md`

**Purpose:** Teach Claude HOW to assess risk using MCP data

**Key Components:**

1. **Two-Dimensional Risk Assessment**
   - **Dimension A:** Question Difficulty (success rates)
   - **Dimension B:** Error Pattern Detection (32 patterns)

2. **Analysis Procedure (5 steps)**
   ```
   Step 1: Understand user's task
   Step 2: Query relevant benchmark data (MCP tools)
   Step 3: Analyze retrieved data
   Step 4: Compute overall risk score
   Step 5: Generate risk report
   ```

3. **Risk Levels**
   - **CRITICAL:** Universal failures OR multiple CRITICAL patterns
   - **HIGH:** Success rate < 30% OR 1+ CRITICAL pattern
   - **MEDIUM:** Success rate 30-60% OR HIGH/MEDIUM patterns
   - **LOW:** Success rate 60-80% OR LOW severity patterns
   - **MINIMAL:** Success rate > 80% AND no patterns

4. **Error Pattern Reference Guide**
   - DS-1000 patterns: mutability, indexing, vectorization, etc.
   - Universal failures: Complex engineering, unit conversions
   - CoT failures: Ambiguous questions
   - ML-discovered: Coding (100% risk), Medicine (100% risk)

5. **Example Workflows**
   - Pandas code analysis
   - Complex physics calculations
   - Medical diagnosis (dangerous cluster)

**Advantages of Skill Approach:**
- ✅ Reasoning is transparent and editable
- ✅ User can customize assessment logic
- ✅ Claude can adapt procedures
- ✅ MCP stays simple and focused
- ✅ Clear separation of data vs analysis

---

# What's Missing in Current Branch

## Data Files: ✅ ALL PRESENT
- 13K questions (MMLU-Pro + DS-1000)
- JSON datastore (56 MB, 8 files)
- Error patterns catalog (32 patterns)
- Statistics and metadata

## MCP Server: ❌ NOT PRESENT
- No `togmal_mcp.py` or `togmal_mcp_refactored.py`
- Need to copy from previous branch

## Claude Skill: ❌ NOT PRESENT
- No `skills/togmal-risk-assessment/SKILL.md`
- Need to copy from previous branch

## Test Files: ❌ NOT PRESENT
- No MCP integration tests
- No skill flow tests

---

# Recommended Next Steps

## Option 1: Copy Refactored MCP + Skill (Recommended)

**Why:** Clean architecture, data-heavy MCP, reasoning in skill

**What to copy:**
1. `togmal_mcp_refactored.py` → MCP server
2. `skills/togmal-risk-assessment/SKILL.md` → Claude skill
3. `test_mcp_skill_flow.py` → Test integration

**Benefits:**
- ✅ Data-heavy MCP (pure data provider)
- ✅ Reasoning in skill (editable, transparent)
- ✅ Already works with current datastore
- ✅ Uses improved lightweight checker

## Option 2: Copy Original MCP (Analysis-Heavy)

**Why:** Self-contained, no skill needed

**What to copy:**
1. `togmal_mcp.py` → MCP server with built-in analysis

**Benefits:**
- ✅ Works standalone
- ✅ ML-enhanced detection built-in

**Drawbacks:**
- ❌ Analysis logic hidden in code
- ❌ Harder to customize reasoning

## Option 3: Create New Enhanced Version

**Combine best of both:**

**MCP Tools (data + semantic search):**
1. `quick_risk_check` (lightweight pre-screen)
2. `fetch_question` (by ID)
3. `query_questions` (by filters)
4. `search_similar_questions` (NEW - semantic search with ChromaDB)
5. `get_universal_failures`
6. `get_error_patterns_catalog`
7. `get_statistics`
8. `search_by_domain`

**New feature:** Add semantic similarity search using ChromaDB (when built locally)

**Claude Skill:** Enhanced procedures with semantic search examples

---

# Architecture Comparison Summary

| Feature | Original MCP | Refactored MCP + Skill | Current Branch |
|---------|--------------|------------------------|----------------|
| **Data files** | ✅ 13K questions | ✅ 13K questions | ✅ 13K questions |
| **JSON datastore** | ✅ Yes | ✅ Yes | ✅ Yes |
| **MCP server** | ✅ Analysis-heavy | ✅ Data-only | ❌ None |
| **Claude skill** | ❌ No | ✅ Yes | ❌ None |
| **Lightweight checker** | ✅ Basic | ✅ Improved | ✅ Improved (4x) |
| **Error patterns** | ✅ 32 patterns | ✅ 32 patterns | ✅ 32 patterns |
| **ML clustering** | ✅ Built-in | ✅ In catalog | ✅ In catalog |
| **Semantic search** | ❌ No | ❌ No | ❌ No (but ChromaDB ready) |
| **Analysis logic** | In MCP code | In Skill MD | ❌ None |
| **Reasoning transparency** | ❌ Hidden | ✅ Editable | N/A |
| **Evidence submission** | ✅ Yes | ❌ No | ❌ No |
| **Context-aware** | ✅ Yes | ✅ Via skill | N/A |

---

# Key Design Decisions

## Original Architecture: Monolithic

```
User Prompt → MCP analyze_prompt → Returns analysis
                  ↓
              (MCP does everything)
                  ↓
         1. Load data
         2. Run heuristics
         3. ML detection
         4. Compute risk
         5. Generate recommendations
                  ↓
            Risk Report
```

**Pros:**
- Self-contained
- No external dependencies
- Fast (everything in one call)

**Cons:**
- Hard to customize reasoning
- Logic hidden in code
- Can't see how decisions are made

## Refactored Architecture: Separation of Concerns

```
User Prompt → Skill (Analysis Procedures)
                  ↓
         Step 1: Extract domain/task
         Step 2: Query MCP (data only)
                  ↓
              MCP Tools
                  ↓
         fetch_question, query_questions,
         get_error_patterns, etc.
                  ↓
              Return DATA
                  ↓
         Step 3: Analyze data (in skill)
         Step 4: Compute risk (in skill)
         Step 5: Generate report (in skill)
                  ↓
            Risk Report
```

**Pros:**
- Transparent reasoning (user can read skill)
- Customizable (edit skill procedures)
- MCP stays simple and focused
- Claude can adapt analysis based on context

**Cons:**
- Requires skill file
- More verbose (multiple MCP calls)

---

# Recommendation for Current Branch

## Bring over the Refactored MCP + Skill

**Reasoning:**
1. ✅ **Data-heavy MCP philosophy** matches user's request
2. ✅ **Skill for reasoning** provides transparency
3. ✅ **Already built improved lightweight checker** (4x better)
4. ✅ **JSON datastore ready** (works perfectly with refactored MCP)
5. ✅ **Can add semantic search later** when ChromaDB is built

**Next Actions:**
1. Copy `togmal_mcp_refactored.py` to this branch
2. Copy `skills/togmal-risk-assessment/SKILL.md` to this branch
3. Test with current datastore
4. Optional: Enhance with semantic search tool (when ChromaDB ready)

**Enhanced Version (Future):**
Add semantic search tool:
```python
@server.call_tool()
async def search_similar_questions(query_text: str, n_results: int = 5):
    """Find semantically similar questions using ChromaDB"""
    # Requires ChromaDB built locally
    collection = client.get_collection("togmal_benchmarks")
    results = collection.query(query_texts=[query_text], n_results=n_results)
    return results
```

---

# Files to Copy

From `origin/claude/infinite-vector-db-builder-01Kwz7B7QeCmK5QDGguvUgzp`:

**Essential:**
- `togmal_mcp_refactored.py` (MCP server)
- `skills/togmal-risk-assessment/SKILL.md` (analysis procedures)

**Optional:**
- `test_mcp_skill_flow.py` (integration tests)
- `test_mcp_integration.py` (MCP tests)
- `benchmark-data-integration-skill.skill` (if useful)

**Already have (don't copy):**
- `build_mcp_datastore.py` (already in current branch)
- `lightweight_prompt_checker.py` (current branch has improved version)
- Data files (current branch has all 13K questions)
