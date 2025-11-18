#!/usr/bin/env python3
"""
Test MCP + Skill Integration
=============================

Simulates the complete workflow:
1. Lightweight checker pre-screens prompt
2. If risky, MCP tools fetch data
3. Skill procedures analyze data
4. Generate risk report

Tests WITHOUT running actual MCP server - just loads data directly.
"""

import json
from pathlib import Path
from lightweight_prompt_checker_improved import LightweightPromptChecker

# Load MCP data stores
DATASTORE_DIR = Path("./mcp_datastore")

def load_mcp_data():
    """Load all MCP datastores"""
    data = {}

    files_to_load = [
        'questions_by_id.json',
        'questions_by_domain.json',
        'questions_by_difficulty.json',
        'error_patterns_catalog.json',
        'statistics.json'
    ]

    for filename in files_to_load:
        path = DATASTORE_DIR / filename
        if path.exists():
            with open(path, 'r') as f:
                key = filename.replace('.json', '')
                data[key] = json.load(f)
                print(f"✅ Loaded {filename}")
        else:
            print(f"❌ Missing {filename}")

    return data

def simulate_mcp_tool(tool_name, args, mcp_data):
    """Simulate MCP tool call"""

    if tool_name == "get_statistics":
        return mcp_data['statistics']

    elif tool_name == "search_by_domain":
        domain = args.get('domain')
        limit = args.get('limit', 10)
        questions = mcp_data['questions_by_domain'].get(domain, [])
        return {
            'domain': domain,
            'count': len(questions),
            'questions': questions[:limit]
        }

    elif tool_name == "query_questions":
        difficulty = args.get('difficulty')
        limit = args.get('limit', 10)
        questions = mcp_data['questions_by_difficulty'].get(difficulty, [])
        return {
            'difficulty': difficulty,
            'count': len(questions),
            'questions': questions[:limit]
        }

    elif tool_name == "get_error_patterns_catalog":
        return mcp_data['error_patterns_catalog']

    elif tool_name == "fetch_question":
        question_id = args.get('question_id')
        return mcp_data['questions_by_id'].get(question_id, {})

    else:
        return {"error": f"Unknown tool: {tool_name}"}

def skill_analyze_prompt(prompt, mcp_data, lightweight_result):
    """
    Implement Skill's 5-step analysis procedure
    (Based on skills/togmal-risk-assessment/SKILL.md)
    """

    print("\n" + "="*80)
    print("SKILL ANALYSIS PROCEDURE (5 Steps)")
    print("="*80)

    # Step 1: Understand the user's task
    print("\n📋 Step 1: Understand the User's Task")
    print(f"Prompt: {prompt[:100]}...")

    # Extract domain from lightweight triggers
    domain = None
    if any('pandas' in t.lower() for t in lightweight_result.get('triggers', [])):
        domain = 'Pandas'
    elif any('quantum' in t.lower() for t in lightweight_result.get('triggers', [])):
        domain = 'physics'
    elif any('math' in t.lower() for t in lightweight_result.get('triggers', [])):
        domain = 'math'

    task_type = "calculation" if any(c.isdigit() for c in prompt) else "reasoning"

    print(f"  Domain: {domain or 'general'}")
    print(f"  Task Type: {task_type}")
    print(f"  Lightweight Risk: {lightweight_result['risk_level']}")

    # Step 2: Query relevant benchmark data
    print("\n🔍 Step 2: Query Relevant Benchmark Data")

    # Get statistics overview
    stats = simulate_mcp_tool("get_statistics", {}, mcp_data)
    print(f"  Dataset: {stats['total_questions']} questions")
    benchmarks = ', '.join(stats.get('by_benchmark', {}).keys())
    print(f"  Benchmarks: {benchmarks}")

    # Search by domain if identified
    domain_questions = []
    if domain:
        domain_result = simulate_mcp_tool("search_by_domain", {'domain': domain, 'limit': 20}, mcp_data)
        domain_questions = domain_result['questions']
        print(f"  Found {domain_result['count']} questions in domain '{domain}'")

    # Query by difficulty if prompt seems hard
    hard_questions = []
    if lightweight_result['risk_level'] in ['HIGH', 'CRITICAL']:
        hard_result = simulate_mcp_tool("query_questions", {'difficulty': 'Expert', 'limit': 10}, mcp_data)
        hard_questions = hard_result['questions']
        print(f"  Found {hard_result['count']} Expert-level questions")

    # Get error patterns catalog
    error_catalog = simulate_mcp_tool("get_error_patterns_catalog", {}, mcp_data)
    print(f"  Error patterns catalog: {error_catalog.get('total_patterns', 'N/A')} patterns")

    # Step 3: Analyze retrieved data
    print("\n📊 Step 3: Analyze Retrieved Data")

    # Difficulty analysis
    avg_success_rate = None
    if domain_questions:
        success_rates = [q['success_rate'] for q in domain_questions[:10] if 'success_rate' in q]
        if success_rates:
            avg_success_rate = sum(success_rates) / len(success_rates)
            print(f"  Average success rate in {domain}: {avg_success_rate:.1%}")

    # Pattern analysis
    matched_patterns = []
    for trigger in lightweight_result.get('triggers', []):
        if 'code_pattern' in trigger:
            pattern_name = trigger.split(':')[1]
            matched_patterns.append({
                'name': pattern_name,
                'severity': 'HIGH',
                'source': 'DS-1000'
            })

    if matched_patterns:
        print(f"  Matched error patterns: {len(matched_patterns)}")
        for p in matched_patterns:
            print(f"    - {p['name']} ({p['severity']})")

    # Step 4: Compute overall risk score
    print("\n🎯 Step 4: Compute Overall Risk Score")

    # Risk decision tree from skill
    final_risk = lightweight_result['risk_level']
    reasoning = []

    if avg_success_rate is not None and avg_success_rate < 0.3:
        final_risk = 'HIGH'
        reasoning.append(f"Success rate < 30% ({avg_success_rate:.1%})")

    if len(matched_patterns) >= 2:
        final_risk = 'HIGH'
        reasoning.append(f"{len(matched_patterns)} error patterns detected")

    if 'dangerous_domain_medical_or_legal' in lightweight_result.get('triggers', []):
        final_risk = 'CRITICAL'
        reasoning.append("Dangerous domain (medical/legal)")

    print(f"  Final Risk Level: {final_risk}")
    print(f"  Reasoning: {'; '.join(reasoning) if reasoning else 'Based on lightweight screening'}")

    # Step 5: Generate risk report
    print("\n📝 Step 5: Generate Risk Report")

    report = {
        'task_analysis': {
            'domain': domain or 'general',
            'task_type': task_type,
            'complexity': lightweight_result['risk_level']
        },
        'benchmark_data': {
            'similar_questions': len(domain_questions),
            'avg_success_rate': f"{avg_success_rate:.1%}" if avg_success_rate else "N/A",
            'expert_questions_found': len(hard_questions)
        },
        'pattern_analysis': matched_patterns,
        'overall_risk': final_risk,
        'recommendations': generate_recommendations(final_risk, matched_patterns)
    }

    return report

def generate_recommendations(risk_level, patterns):
    """Generate recommendations based on risk level"""

    if risk_level == 'CRITICAL':
        return [
            "⚠️ HIGH FAILURE RISK DETECTED",
            "Strongly recommend: Break into smaller steps",
            "Consider: Human verification required",
            "Alternative: Use specialized tools or expert consultation"
        ]
    elif risk_level == 'HIGH':
        return [
            "⚠️ Moderate to high risk",
            "Recommend: Careful validation of results",
            "Monitor for: Known error patterns",
            "Consider: Step-by-step approach"
        ]
    elif risk_level == 'MEDIUM':
        return [
            "⚠️ Some risk detected",
            "Recommend: Double-check outputs",
            "Watch for: " + (patterns[0]['name'] if patterns else "potential issues")
        ]
    else:
        return [
            "✅ Low risk",
            "Proceed with normal caution"
        ]

def test_complete_workflow():
    """Test complete MCP + Skill workflow"""

    print("="*80)
    print("MCP + SKILL INTEGRATION TEST")
    print("="*80)

    # Load data
    print("\n📦 Loading MCP Datastores...")
    mcp_data = load_mcp_data()

    # Initialize lightweight checker
    checker = LightweightPromptChecker()

    # Test cases
    test_prompts = [
        "df['result'] = df.groupby('category').sum()",
        "Calculate the partition function for a quantum harmonic oscillator at temperature T",
        "Based on these symptoms, what disease does the patient have?",
        "What is the capital of France?",
        "Convert 27000 lbs to kg and calculate stress in MPa given yield strength in psi"
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print("\n" + "="*80)
        print(f"TEST CASE #{i}")
        print("="*80)

        # Step 0: Lightweight pre-screening
        print("\n🚦 Step 0: Lightweight Pre-Screening")
        lightweight_result = checker.quick_check(prompt)

        print(f"  Prompt: '{prompt[:60]}...'")
        print(f"  Risk Level: {lightweight_result['risk_level']}")
        print(f"  Should Analyze: {lightweight_result['should_analyze']}")
        print(f"  Triggers: {', '.join(lightweight_result['triggers']) if lightweight_result['triggers'] else 'none'}")

        # If risky, run full skill analysis
        if lightweight_result['should_analyze']:
            report = skill_analyze_prompt(prompt, mcp_data, lightweight_result)

            # Print final report
            print("\n" + "="*80)
            print("FINAL RISK REPORT")
            print("="*80)
            print(f"\n**Overall Risk: {report['overall_risk']}**")
            print(f"\nBenchmark Data:")
            print(f"  - Similar questions analyzed: {report['benchmark_data']['similar_questions']}")
            print(f"  - Average success rate: {report['benchmark_data']['avg_success_rate']}")

            if report['pattern_analysis']:
                print(f"\nError Patterns Detected:")
                for p in report['pattern_analysis']:
                    print(f"  - {p['name']} ({p['severity']} severity, source: {p['source']})")

            print(f"\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  {rec}")
        else:
            print("\n✅ Low risk - no deep analysis needed")

        print("\n" + "-"*80)

if __name__ == "__main__":
    test_complete_workflow()
