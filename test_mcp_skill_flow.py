#!/usr/bin/env python3
"""
Test MCP + Skill Flow (Without MCP Server)
===========================================

Simulates how the MCP + Skill architecture works by:
1. Querying data (what MCP would do)
2. Following Skill procedures (what Claude would do)
3. Generating risk report (what Skill teaches)
"""

import json
from pathlib import Path

DATASTORE = Path("./mcp_datastore")

# ============================================================================
# MCP Functions (Data Fetching Only)
# ============================================================================

def mcp_search_by_domain(domain: str, limit: int = 10):
    """MCP tool: search_by_domain"""
    with open(DATASTORE / "questions_by_domain.json") as f:
        questions_by_domain = json.load(f)

    questions = questions_by_domain.get(domain, [])[:limit]
    return {
        "domain": domain,
        "count": len(questions),
        "questions": questions
    }

def mcp_get_statistics():
    """MCP tool: get_statistics"""
    with open(DATASTORE / "statistics.json") as f:
        return json.load(f)

def mcp_get_error_patterns_catalog():
    """MCP tool: get_error_patterns_catalog"""
    with open(DATASTORE / "error_patterns_catalog.json") as f:
        return json.load(f)

def mcp_get_universal_failures(limit: int = 10):
    """MCP tool: get_universal_failures"""
    with open(DATASTORE / "universal_failures.json") as f:
        failures = json.load(f)
    return {
        "count": len(failures[:limit]),
        "total_universal_failures": len(failures),
        "questions": failures[:limit]
    }

# ============================================================================
# Skill Procedures (Analysis Logic)
# ============================================================================

def skill_assess_pandas_code_risk(code: str):
    """
    ToGMAL Skill Procedure: Assess pandas code risk

    Following the procedure from skills/togmal-risk-assessment/SKILL.md:
    1. Extract task details
    2. Query MCP for data
    3. Analyze retrieved data
    4. Compute risk score
    5. Generate report
    """

    print("="*80)
    print("ToGMAL Risk Assessment (Following Skill Procedures)")
    print("="*80)

    # Step 1: Extract task details (from Skill)
    print("\n📋 Step 1: Extract Task Details")
    task = {
        "domain": "Pandas",
        "task_type": "DataFrame operation",
        "code": code
    }
    print(f"  Domain: {task['domain']}")
    print(f"  Task: {task['task_type']}")
    print(f"  Code: {task['code']}")

    # Step 2: Query MCP for data (MCP provides data)
    print("\n📊 Step 2: Query MCP for Data")
    print("  Calling: mcp_search_by_domain('Pandas', limit=20)")
    pandas_data = mcp_search_by_domain("Pandas", limit=20)
    print(f"  ✅ Retrieved {pandas_data['count']} Pandas questions")

    print("  Calling: mcp_get_error_patterns_catalog()")
    patterns_catalog = mcp_get_error_patterns_catalog()
    print(f"  ✅ Retrieved {patterns_catalog['unique_patterns']} error patterns")

    # Step 3: Analyze data (Skill teaches how)
    print("\n🔍 Step 3: Analyze Retrieved Data")

    # A. Difficulty analysis
    success_rates = [q['success_rate'] for q in pandas_data['questions']]
    avg_success = sum(success_rates) / len(success_rates) if success_rates else 0.5
    print(f"  A. Difficulty Analysis:")
    print(f"     Average success rate: {avg_success:.1%}")
    print(f"     Domain difficulty: {'HIGH' if avg_success < 0.5 else 'MEDIUM'}")

    # B. Pattern matching (from Skill's pattern guide)
    print(f"\n  B. Pattern Matching (following Skill procedures):")
    detected_patterns = []

    # Check for missing .copy() (mutability pattern)
    if 'copy()' not in code and ('=' in code or 'df[' in code):
        print(f"     ⚠️  Potential mutability issue (no .copy() detected)")
        detected_patterns.append({
            "pattern": "mutability_misunderstanding",
            "severity": "CRITICAL",
            "description": "Missing .copy() - DataFrame modifications may affect original",
            "recommendation": "Use df.copy() before modifications"
        })

    # Check for missing .reset_index() after groupby
    if 'groupby' in code and 'reset_index' not in code:
        print(f"     ⚠️  Missing .reset_index() after groupby")
        detected_patterns.append({
            "pattern": "index_persistence",
            "severity": "CRITICAL",
            "description": "Index may cause unexpected behavior after groupby",
            "recommendation": "Add .reset_index() after groupby operations"
        })

    # Check for for-loops (vectorization pattern)
    if 'for ' in code and ('df[' in code or 'DataFrame' in code):
        print(f"     ⚠️  For-loop detected over DataFrame")
        detected_patterns.append({
            "pattern": "vectorization_concept",
            "severity": "CRITICAL",
            "description": "Using for-loops instead of vectorized operations",
            "recommendation": "Use vectorized operations (.apply(), .map(), etc.)"
        })

    if not detected_patterns:
        print(f"     ✅ No critical patterns detected")

    # Step 4: Compute risk score (Skill's decision tree)
    print("\n⚖️  Step 4: Compute Risk Score (using Skill's decision tree)")

    critical_patterns = [p for p in detected_patterns if p['severity'] == 'CRITICAL']

    if len(critical_patterns) >= 2:
        risk_level = "HIGH"
        print(f"  Multiple CRITICAL patterns → RISK: HIGH")
    elif len(critical_patterns) == 1:
        risk_level = "MEDIUM-HIGH"
        print(f"  1 CRITICAL pattern → RISK: MEDIUM-HIGH")
    elif avg_success < 0.5:
        risk_level = "MEDIUM"
        print(f"  Success rate < 50% → RISK: MEDIUM")
    elif avg_success < 0.7:
        risk_level = "LOW-MEDIUM"
        print(f"  Success rate < 70% → RISK: LOW-MEDIUM")
    else:
        risk_level = "LOW"
        print(f"  Success rate ≥ 70% → RISK: LOW")

    # Step 5: Generate report (Skill's template)
    print("\n" + "="*80)
    print("📄 Step 5: Generate Risk Report (following Skill template)")
    print("="*80)

    report = f"""
## ToGMAL Risk Assessment

### Task Analysis
- Domain: {task['domain']}
- Task Type: {task['task_type']}
- Code Analyzed: `{task['code']}`

### Benchmark Data (via MCP)
- Similar Questions Analyzed: {pandas_data['count']}
- Average Success Rate: {avg_success:.1%}
- Domain Difficulty: {'HIGH' if avg_success < 0.5 else 'MEDIUM'}
- Data Source: MCP datastore (DS-1000 benchmark)

### Error Pattern Analysis (via Skill procedures)
"""

    if detected_patterns:
        report += f"Detected {len(detected_patterns)} pattern(s):\n\n"
        for pattern in detected_patterns:
            report += f"**{pattern['pattern']}** ({pattern['severity']})\n"
            report += f"- Description: {pattern['description']}\n"
            report += f"- Recommendation: {pattern['recommendation']}\n\n"
    else:
        report += "✅ No critical patterns detected. Code follows best practices.\n\n"

    report += f"""
### Overall Risk Assessment
**RISK LEVEL: {risk_level}**

"""

    if risk_level in ["HIGH", "MEDIUM-HIGH"]:
        report += "⚠️ **Moderate to High Risk Detected**\n\n"
        report += "**Recommendations:**\n"
        for pattern in detected_patterns:
            report += f"- {pattern['recommendation']}\n"
    else:
        report += "✅ **Low Risk**\n\n"
        report += "Your approach is sound. Continue with normal caution.\n"

    print(report)

    return {
        "risk_level": risk_level,
        "avg_success_rate": avg_success,
        "patterns_detected": len(detected_patterns),
        "patterns": detected_patterns
    }

# ============================================================================
# Test Examples
# ============================================================================

def test_example_1():
    """Example 1: Code with missing .copy()"""
    print("\n" + "🧪 "*20)
    print("TEST 1: Pandas code with potential mutability issue")
    print("🧪 "*20)

    code = "result = df.groupby('category').sum()"
    skill_assess_pandas_code_risk(code)

def test_example_2():
    """Example 2: Good code"""
    print("\n\n" + "🧪 "*20)
    print("TEST 2: Pandas code with good practices")
    print("🧪 "*20)

    code = "result = df.copy().groupby('category').sum().reset_index()"
    skill_assess_pandas_code_risk(code)

def test_mcp_tools():
    """Test MCP tools directly"""
    print("\n" + "🔧 "*20)
    print("TESTING MCP TOOLS (Data Fetching)")
    print("🔧 "*20)

    print("\n1. Get Statistics")
    stats = mcp_get_statistics()
    print(f"   Total questions: {stats['total_questions']:,}")
    print(f"   Benchmarks: {list(stats['by_benchmark'].keys())}")

    print("\n2. Search by Domain (Physics)")
    physics = mcp_search_by_domain("physics", limit=5)
    print(f"   Found {physics['count']} physics questions")
    print(f"   Sample question: {physics['questions'][0]['question_text'][:100]}...")

    print("\n3. Get Universal Failures")
    failures = mcp_get_universal_failures(limit=3)
    print(f"   Total universal failures: {failures['total_universal_failures']}")
    print(f"   First failure: {failures['questions'][0]['question_text'][:100]}...")

    print("\n4. Get Error Patterns Catalog")
    catalog = mcp_get_error_patterns_catalog()
    print(f"   Unique patterns: {catalog['unique_patterns']}")
    print(f"   Total instances: {catalog['total_pattern_instances']}")

if __name__ == "__main__":
    # Test MCP tools
    test_mcp_tools()

    # Test Skill procedures
    test_example_1()
    test_example_2()

    print("\n" + "="*80)
    print("✅ TESTS COMPLETE")
    print("="*80)
    print("\nThis demonstrates:")
    print("1. MCP provides RAW DATA (no analysis)")
    print("2. Skill provides ANALYSIS PROCEDURES (how to interpret data)")
    print("3. Claude follows Skill to generate context-aware reports")
    print("\nIn real usage:")
    print("- MCP runs as server, Claude calls tools via protocol")
    print("- Skill loaded by Claude Code, teaches analysis workflow")
    print("- Claude combines both to assess risk intelligently")
