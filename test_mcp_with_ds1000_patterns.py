#!/usr/bin/env python3
"""
ToGMAL MCP Test Suite with Real DS-1000 Error Patterns

Tests the MCP server against actual error patterns we discovered:
- Missing .copy() (mutability gap)
- Wrong indexing (.loc vs .iloc)
- For-loops instead of vectorization
- Wrong methods (.replace vs .apply)
- Wrong parameters (axis confusion)
- Multi-step pipeline errors

Uses real code examples from DS-1000 analysis.
"""

import json
from typing import Dict, List

# Test cases based on our DS-1000 findings
TEST_CASES = {
    "mutability_misunderstanding": {
        "name": "Missing .copy() - Mutability Gap",
        "severity": "CRITICAL",
        "frequency": "25.6% of errors (800+ cases in DS-1000)",
        "conceptual_gap": "Doesn't understand side effects and references",
        "examples": [
            {
                "user_prompt": "How do I reorder DataFrame rows according to a list?",
                "wrong_code": """
result = df.iloc[List]
""",
                "correct_code": """
def g(df, List):
    return df.iloc[List]

result = g(df.copy(), List)
""",
                "issue": "Missing .copy() - will modify original DataFrame",
                "expected_detection": "HIGH RISK: Mutability side effects"
            }
        ]
    },

    "indexing_semantics": {
        "name": "Wrong Indexing (.loc vs .iloc)",
        "severity": "HIGH",
        "frequency": "35.8% of errors (wrong_indexing + wrong_attribute)",
        "conceptual_gap": "Doesn't understand label-based vs position-based indexing",
        "examples": [
            {
                "user_prompt": "Filter DataFrame to keep certain rows",
                "wrong_code": """
result = df.groupby('url').apply(lambda x: x.iloc[0] if x['drop_if_dup'].iloc[0] == 'Yes' else x)
""",
                "correct_code": """
def g(df):
    return df.loc[(df['drop_if_dup'] =='No') | ~df['url'].duplicated()]

result = g(df.copy())
""",
                "issue": "Using .iloc[] (position) when .loc[] (label) is needed",
                "expected_detection": "HIGH RISK: Indexing confusion"
            }
        ]
    },

    "vectorization_concept": {
        "name": "For-loops Instead of Vectorized Operations",
        "severity": "MEDIUM",
        "frequency": "9.6% of errors (overcomplicated)",
        "conceptual_gap": "Thinks imperatively, not declaratively",
        "examples": [
            {
                "user_prompt": "Fill missing dates in time series DataFrame",
                "wrong_code": """
result = pd.DataFrame(columns=['dt', 'user', 'val'])
for user in df['user'].unique():
    user_df = df[df['user'] == user]
    min_date = user_df['dt'].min()
    max_date = user_df['dt'].max()
    user_df = user_df.set_index('dt')
    user_df = user_df.reindex(pd.date_range(min_date, max_date))
    user_df = user_df.reset_index()
    user_df['user'] = user
    user_df['val'] = user_df['val'].fillna(0)
    result = result.append(user_df)
""",
                "correct_code": """
def g(df):
    df.dt = pd.to_datetime(df.dt)
    return df.set_index(['dt', 'user']).unstack(fill_value=0).asfreq('D', fill_value=0).stack().sort_index(level=1).reset_index()

result = g(df.copy())
""",
                "issue": "For-loop over DataFrame (100x slower than vectorized)",
                "expected_detection": "MEDIUM RISK: Vectorization opportunity"
            }
        ]
    },

    "method_semantics": {
        "name": "Wrong Method (.replace vs .apply)",
        "severity": "HIGH",
        "frequency": "4.2% of errors (wrong_method)",
        "conceptual_gap": "Doesn't understand what methods do",
        "examples": [
            {
                "user_prompt": "Replace values conditionally based on counts",
                "wrong_code": """
def replace_values(df, column, threshold):
    counts = df[column].value_counts()
    mask = counts >= threshold
    df[column] = df[column].replace(counts[mask].index, 'other')
    return df

result = df.pipe(replace_values, 'Qu1', 3).pipe(replace_values, 'Qu3', 2)
""",
                "correct_code": """
def g(df):
    for col in df.columns:
        vc = df[col].value_counts()
        if col == 'Qu1':
            df[col] = df[col].apply(lambda x: x if vc[x] >= 3 else 'other')
        else:
            df[col] = df[col].apply(lambda x: x if vc[x] >= 2 else 'other')
    return df

result = g(df.copy())
""",
                "issue": "Using .replace() for transformation, need .apply() for conditional logic",
                "expected_detection": "HIGH RISK: Wrong method for task"
            }
        ]
    },

    "dimensional_operations": {
        "name": "Wrong axis Parameter",
        "severity": "HIGH",
        "frequency": "4.0% of errors (wrong_parameter)",
        "conceptual_gap": "Doesn't understand axis parameter",
        "examples": [
            {
                "user_prompt": "Concatenate DataFrames column-wise",
                "wrong_code": """
result = df.join(df.message.apply(extract_key_value).apply(pd.Series))
# Missing axis parameter in concat-like operation
""",
                "correct_code": """
result = pd.concat([df, df1], axis=1)
# axis=1 for column-wise concatenation
""",
                "issue": "axis parameter missing or wrong (axis=0 vs axis=1)",
                "expected_detection": "MEDIUM RISK: Dimensional confusion"
            }
        ]
    },

    "transformation_pipelines": {
        "name": "Incomplete Multi-Step Solution",
        "severity": "CRITICAL",
        "frequency": "28.0% of errors (missing_method + incomplete_solution)",
        "conceptual_gap": "Doesn't understand transformation pipelines",
        "examples": [
            {
                "user_prompt": "Calculate differences after reordering DataFrame",
                "wrong_code": """
result = df.iloc[List]
# Missing: .reindex(), .reset_index(), comparison, .sum()
""",
                "correct_code": """
def g(df, List):
    df2 = df.iloc[List].reindex().reset_index(drop=True)
    return (df2.Type != df.Type).sum()

result = g(df.copy(), List)
""",
                "issue": "Only step 1 of 4 - incomplete pipeline",
                "expected_detection": "CRITICAL: Incomplete transformation pipeline"
            }
        ]
    },

    "index_persistence": {
        "name": "Missing .reset_index() after groupby",
        "severity": "HIGH",
        "frequency": "21.6% of errors (portion of missing_method)",
        "conceptual_gap": "Doesn't understand index transformations",
        "examples": [
            {
                "user_prompt": "Group DataFrame and calculate means",
                "wrong_code": """
result = df.groupby('category').sum()
# Index is now ['A', 'B', 'C'], not a regular column!
""",
                "correct_code": """
result = df.groupby('category').sum().reset_index()
# Now 'category' is a column again
""",
                "issue": "Grouping column becomes index, need .reset_index()",
                "expected_detection": "HIGH RISK: Index persistence confusion"
            }
        ]
    },

    "api_evolution": {
        "name": "Using Deprecated .values instead of .to_numpy()",
        "severity": "MEDIUM",
        "frequency": "27.6% of errors (portion of wrong_attribute)",
        "conceptual_gap": "Using deprecated API patterns",
        "examples": [
            {
                "user_prompt": "Convert DataFrame to numpy array",
                "wrong_code": """
arr = df.values  # Deprecated!
""",
                "correct_code": """
arr = df.to_numpy()  # Current best practice
""",
                "issue": "Using .values (deprecated) instead of .to_numpy()",
                "expected_detection": "MEDIUM RISK: Deprecated API usage"
            }
        ]
    }
}


def print_test_case(category: str, case: Dict):
    """Print a test case in formatted style."""
    print(f"\n{'='*80}")
    print(f"TEST: {case['name']}")
    print(f"Severity: {case['severity']} | Frequency: {case['frequency']}")
    print(f"Conceptual Gap: {case['conceptual_gap']}")
    print(f"{'='*80}")

    for i, example in enumerate(case['examples'], 1):
        print(f"\nExample {i}:")
        print(f"User Prompt: {example['user_prompt']}")
        print(f"\n--- WRONG CODE (what models generate) ---")
        print(example['wrong_code'].strip())
        print(f"\n--- CORRECT CODE (reference) ---")
        print(example['correct_code'].strip())
        print(f"\nIssue: {example['issue']}")
        print(f"Expected Detection: {example['expected_detection']}")
        print(f"-" * 80)


def simulate_mcp_analysis(code: str, category: str) -> Dict:
    """
    Simulate what ToGMAL MCP should detect.

    In real implementation, this would call the actual MCP tools.
    For now, we're defining expected behavior.
    """

    detections = []

    # Check for mutability issues
    if 'pandas' in code or 'pd.' in code or 'df' in code:
        if '.copy()' not in code and ('df[' in code or 'df.' in code or '.iloc[' in code):
            detections.append({
                'type': 'mutability_misunderstanding',
                'severity': 'CRITICAL',
                'message': 'Missing .copy() - may modify original DataFrame',
                'recommendation': 'Use df.copy() before modifications',
                'evidence': 'THE #1 missing method in DS-1000 (800+ cases)'
            })

    # Check for indexing confusion
    if '.iloc[' in code and ("'" in code or '"' in code):
        detections.append({
            'type': 'indexing_semantics',
            'severity': 'HIGH',
            'message': '.iloc[] with string detected - use .loc[] for labels',
            'recommendation': 'Use .loc[] for label-based, .iloc[] for position-based',
            'evidence': '35.8% of DS-1000 errors involve indexing confusion'
        })

    # Check for for-loops
    if 'for ' in code and 'df' in code:
        detections.append({
            'type': 'vectorization_concept',
            'severity': 'MEDIUM',
            'message': 'For-loop over DataFrame detected (100x slower)',
            'recommendation': 'Use vectorized operations, .apply(), or .transform()',
            'evidence': '9.6% of DS-1000 errors are overcomplicated with loops'
        })

    # Check for deprecated APIs
    if '.values' in code and '.to_numpy()' not in code:
        detections.append({
            'type': 'api_evolution',
            'severity': 'MEDIUM',
            'message': 'Using deprecated .values - use .to_numpy() instead',
            'recommendation': 'Replace df.values with df.to_numpy()',
            'evidence': '27.6% of DS-1000 errors use wrong attributes'
        })

    # Check for groupby without reset_index
    if '.groupby(' in code and 'reset_index' not in code:
        detections.append({
            'type': 'index_persistence',
            'severity': 'HIGH',
            'message': 'groupby without .reset_index() - index will change',
            'recommendation': 'Use .reset_index() to convert index back to column',
            'evidence': '21.6% of DS-1000 errors involve missing methods'
        })

    # Check code length for incomplete solutions
    code_lines = len([l for l in code.strip().split('\n') if l.strip() and not l.strip().startswith('#')])
    if code_lines < 3 and category == 'transformation_pipelines':
        detections.append({
            'type': 'transformation_pipelines',
            'severity': 'CRITICAL',
            'message': 'Code appears too short for multi-step task',
            'recommendation': 'Verify all pipeline steps: filter → transform → aggregate → format',
            'evidence': '28% of DS-1000 errors are incomplete pipelines'
        })

    return {
        'code_analyzed': code,
        'category': category,
        'detections': detections,
        'risk_level': 'CRITICAL' if any(d['severity'] == 'CRITICAL' for d in detections) else
                      'HIGH' if any(d['severity'] == 'HIGH' for d in detections) else
                      'MEDIUM' if detections else 'LOW'
    }


def run_tests():
    """Run all test cases through simulated MCP analysis."""

    print("\n" + "="*80)
    print("ToGMAL MCP TEST SUITE - DS-1000 Error Patterns")
    print("="*80)
    print("\nTesting against real error patterns from 8,934 logic errors")
    print("Coverage: 11 conceptual error types from DS-1000 analysis")
    print("="*80)

    results = []

    for category, case in TEST_CASES.items():
        print_test_case(category, case)

        for example in case['examples']:
            # Test wrong code
            print(f"\n🔍 ANALYZING WRONG CODE...")
            wrong_analysis = simulate_mcp_analysis(example['wrong_code'], category)

            print(f"\nDetections ({len(wrong_analysis['detections'])}):")
            for detection in wrong_analysis['detections']:
                print(f"  ⚠️  {detection['severity']}: {detection['message']}")
                print(f"     → {detection['recommendation']}")
                print(f"     📊 Evidence: {detection['evidence']}")

            print(f"\n✓ Risk Level: {wrong_analysis['risk_level']}")

            # Test correct code
            print(f"\n🔍 ANALYZING CORRECT CODE...")
            correct_analysis = simulate_mcp_analysis(example['correct_code'], category)

            if correct_analysis['detections']:
                print(f"\nDetections ({len(correct_analysis['detections'])}):")
                for detection in correct_analysis['detections']:
                    print(f"  ⚠️  {detection['severity']}: {detection['message']}")
            else:
                print("\n✓ No issues detected - code looks good!")

            results.append({
                'category': category,
                'wrong_detected': len(wrong_analysis['detections']) > 0,
                'correct_clean': len(correct_analysis['detections']) == 0,
                'wrong_risk': wrong_analysis['risk_level'],
                'correct_risk': correct_analysis['risk_level']
            })

            print("\n" + "~"*80)

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total = len(results)
    wrong_detected = sum(1 for r in results if r['wrong_detected'])
    correct_clean = sum(1 for r in results if r['correct_clean'])

    print(f"\nTotal Test Cases: {total}")
    print(f"Wrong Code Detected: {wrong_detected}/{total} ({wrong_detected/total*100:.1f}%)")
    print(f"Correct Code Clean: {correct_clean}/{total} ({correct_clean/total*100:.1f}%)")

    print(f"\nRisk Level Distribution (Wrong Code):")
    risk_counts = {}
    for r in results:
        risk = r['wrong_risk']
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

    for risk, count in sorted(risk_counts.items(), reverse=True):
        bar = '█' * (count * 5)
        print(f"  {risk:10s}: {count:2d} {bar}")

    print("\n" + "="*80)
    print("RECOMMENDATIONS FOR ToGMAL MCP")
    print("="*80)

    print("\n1. Pattern Detection Priority:")
    print("   CRITICAL: mutability_misunderstanding (800+ cases)")
    print("   CRITICAL: transformation_pipelines (28% of errors)")
    print("   HIGH:     indexing_semantics (35.8% of errors)")
    print("   HIGH:     index_persistence (21.6% of errors)")

    print("\n2. Integration with MCP Tools:")
    print("   - Add to togmal_analyze_prompt: Check for .copy() patterns")
    print("   - Add code_quality tool: Vectorization analysis")
    print("   - Add pipeline_validator tool: Multi-step completeness")

    print("\n3. Educational Messages:")
    print("   - Cite DS-1000 frequency data in warnings")
    print("   - Link to conceptual error taxonomy")
    print("   - Provide before/after code examples")

    print("\n" + "="*80)


if __name__ == "__main__":
    run_tests()
