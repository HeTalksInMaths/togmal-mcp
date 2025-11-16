# ToGMAL Architecture: Skills + MCP

## Overview

ToGMAL now follows the **Skills + MCP** architectural pattern recommended by Anthropic:

- **MCP Server** (`togmal_mcp_refactored.py`): Provides **DATA ACCESS** to benchmark questions
- **ToGMAL Skill** (`skills/togmal-risk-assessment/SKILL.md`): Provides **ANALYSIS PROCEDURES** for risk assessment

## Architecture Principles

### MCP: Data Provider

**What it does:**
- Connects Claude TO external data (13,000 benchmark questions)
- Provides simple data fetching operations
- Returns raw data without interpretation

**What it does NOT do:**
- ❌ Risk analysis
- ❌ Pattern detection logic
- ❌ User warnings
- ❌ Recommendations

**Tools Provided:**
1. `fetch_question` - Get specific question by ID
2. `query_questions` - Filter by benchmark/difficulty/domain
3. `get_universal_failures` - Get questions all models fail
4. `get_error_patterns_catalog` - Get all 32 error patterns
5. `get_statistics` - Get dataset statistics
6. `search_by_domain` - Search by domain

### Skill: Analysis Provider

**What it does:**
- Teaches Claude HOW to use benchmark data
- Provides step-by-step analysis procedures
- Defines risk assessment methodology
- Specifies when to warn users

**What it does NOT do:**
- ❌ Fetch data (delegates to MCP)
- ❌ Store data
- ❌ Implement data structures

**Procedures Provided:**
1. Two-dimensional risk assessment (difficulty + patterns)
2. Error pattern matching rules
3. Risk level computation (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL)
4. Report generation format
5. Domain-specific analysis workflows

## Data Flow

```
User Request
    ↓
Claude (with ToGMAL Skill loaded)
    ↓
[Skill: Analyze user intent, plan analysis]
    ↓
[MCP: query_questions(domain="physics")]
    ↓
[MCP: Returns raw question data]
    ↓
[Skill: Apply risk assessment procedure]
    ↓
[Skill: Generate risk report]
    ↓
User receives analysis
```

## Example Interaction

### User Prompt
```
"Help me filter a pandas DataFrame where column A > 10"
```

### Skill Activates
The ToGMAL Risk Assessment Skill recognizes this as a risk assessment task.

**Step 1: Extract task details**
- Domain: Data Science (Pandas)
- Task: DataFrame filtering
- Complexity: Simple operation

**Step 2: Query MCP for data**
```python
# Skill directs Claude to use MCP tools
search_by_domain(domain="Pandas", limit=20)
get_error_patterns_catalog()
```

**Step 3: MCP returns data**
```json
{
  "domain": "Pandas",
  "count": 20,
  "questions": [
    {
      "question_id": "ds1000_pandas_42",
      "success_rate": 0.62,
      "error_patterns": [...]
    },
    ...
  ]
}
```

**Step 4: Skill analyzes data**
- Average success rate for Pandas: 62%
- Relevant error patterns: vectorization_concept, index_persistence
- User code matches good practices
- Risk level: LOW-MEDIUM

**Step 5: Skill generates report**
```markdown
## ToGMAL Risk Assessment

### Task Analysis
- Domain: Data Science (Pandas)
- Task Type: DataFrame filtering
- Complexity: Simple

### Benchmark Data
- Similar Questions Analyzed: 20
- Average Success Rate: 62%
- Pandas domain has moderate success rates

### Error Pattern Analysis
No critical patterns detected. Code follows best practices.

### Overall Risk Assessment
**RISK LEVEL: LOW**

Your approach is sound. Minor considerations:
- Ensure vectorized comparison (A > 10 is correct)
- Consider .copy() if modifying result DataFrame

### Recommendations
✅ Low risk. Proceed with normal caution.
```

## Comparison: Old vs New Architecture

### Old Architecture (Monolithic MCP)
```python
@server.call_tool()
async def togmal_analyze_prompt(prompt):
    # MCP does EVERYTHING:
    # 1. Load data
    # 2. Detect patterns (hardcoded logic)
    # 3. Compute risk (hardcoded thresholds)
    # 4. Format warnings (hardcoded templates)
    # 5. Return formatted result

    # Problems:
    # - Logic buried in MCP code
    # - Hard to customize analysis
    # - Claude can't reason about it
    # - Not adaptable to new patterns
```

### New Architecture (Skills + MCP)
```python
# MCP: Pure data fetching
@server.call_tool()
async def search_by_domain(domain):
    questions = load_from_datastore(domain)
    return questions  # Raw data only

# Skill: Analysis procedure (in SKILL.md)
"""
When analyzing pandas code:
1. Query MCP: search_by_domain("Pandas")
2. Check success rates
3. Match against these patterns:
   - mutability_misunderstanding
   - index_persistence
   - vectorization_concept
4. Compute risk using formula: ...
5. Generate report with format: ...
"""

# Benefits:
# + Claude can reason about analysis
# + Easy to update procedures (just edit SKILL.md)
# + Transparent decision-making
# + Adaptable to new contexts
```

## Why This Is Better

### 1. **Separation of Concerns**
- **MCP**: "Here's the data you requested"
- **Skill**: "Here's how to analyze that data"

### 2. **Flexibility**
- Update analysis procedures without touching MCP code
- Claude can adapt procedures to specific contexts
- New patterns can be added to dataset without code changes

### 3. **Transparency**
- Analysis logic visible to Claude
- Claude explains reasoning in reports
- User can see decision-making process

### 4. **Context-Awareness**
- Skills can consider user's specific situation
- Not limited to hardcoded templates
- Can combine multiple data sources

### 5. **Maintainability**
- Procedures documented in markdown
- No complex Python logic for analysis
- Easy to version control and review

## File Structure

```
togmal-mcp/
├── togmal_mcp_refactored.py       # MCP server (data fetching only)
├── mcp_datastore/                 # Data files (JSON)
│   ├── questions_by_id.json       # 13K questions indexed
│   ├── questions_by_benchmark.json
│   ├── questions_by_difficulty.json
│   ├── questions_by_domain.json
│   ├── questions_with_errors.json # 176 questions with patterns
│   ├── universal_failures.json    # 22 universal failures
│   ├── error_patterns_catalog.json # 32 patterns cataloged
│   └── statistics.json            # Summary stats
├── skills/
│   └── togmal-risk-assessment/
│       └── SKILL.md               # Analysis procedures
└── data/
    └── unified_database_complete.json # Source data (28.9 MB)
```

## Usage

### 1. Build Data Store
```bash
python3 build_mcp_datastore.py
```

### 2. Run MCP Server
```bash
python3 togmal_mcp_refactored.py
```

### 3. Load Skill (in Claude Code)
The skill is automatically discovered from `skills/` directory.

### 4. Use Combined System
```
User: "Analyze this pandas code for risk"

Claude (with Skill loaded):
1. Recognizes request matches ToGMAL Skill
2. Follows Skill's analysis procedure
3. Uses MCP tools to fetch data
4. Applies Skill's risk assessment logic
5. Generates report per Skill's template
```

## Benefits Over Previous Approach

1. **No Hardcoded Logic**: Analysis procedures in plain language, not Python code
2. **Claude's Intelligence**: Leverages Claude's reasoning, not just pattern matching
3. **Context-Sensitive**: Can adapt to specific user situations
4. **Transparent**: User can see why risk was assessed
5. **Maintainable**: Update SKILL.md, not complex Python logic
6. **Extensible**: Easy to add new procedures without touching MCP
7. **Portable**: Skill works across Claude.ai, API, and Claude Code

## Next Steps

1. Test MCP + Skill integration
2. Refine analysis procedures based on usage
3. Add more specialized sub-skills (e.g., "Pandas Code Review Skill")
4. Extend MCP with additional data sources (DataSciBench, etc.)
5. Build semantic similarity search (when ChromaDB works)
