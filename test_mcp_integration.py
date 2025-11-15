#!/usr/bin/env python3
"""
Test the integrated ToGMAL MCP with DS-1000 patterns.

This script imports the actual MCP detection functions and tests them
against real error patterns from the DS-1000 benchmark analysis.
"""

import sys
import json
from typing import Dict, List

# Import the actual detection functions
from togmal_mcp import (
    detect_pandas_code_issues,
    calculate_risk_level,
    recommend_interventions
)

# Test cases from DS-1000 analysis
TEST_CASES = [
    {
        "name": "Missing .copy() - Mutability Gap",
        "code": """
result = df.iloc[List]
""",
        "expected_patterns": ['mutability_misunderstanding'],
        "expected_severity": "CRITICAL"
    },
    {
        "name": "Wrong Indexing (.loc vs .iloc)",
        "code": """
result = df.groupby('url').apply(lambda x: x.iloc[0] if x['drop_if_dup'].iloc[0] == 'Yes' else x)
""",
        "expected_patterns": ['mutability_misunderstanding'],  # No .copy()
        "expected_severity": "CRITICAL"
    },
    {
        "name": "For-loop Over DataFrame",
        "code": """
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
        "expected_patterns": ['vectorization_concept', 'mutability_misunderstanding'],
        "expected_severity": "CRITICAL"
    },
    {
        "name": "Deprecated .values",
        "code": """
arr = df.values
result = arr.mean()
""",
        "expected_patterns": ['api_evolution', 'mutability_misunderstanding'],
        "expected_severity": "MEDIUM"
    },
    {
        "name": "Missing .reset_index() after groupby",
        "code": """
result = df.groupby('category').sum()
""",
        "expected_patterns": ['index_persistence', 'mutability_misunderstanding'],
        "expected_severity": "CRITICAL"
    },
    {
        "name": "Incomplete Pipeline",
        "code": """
result = df.iloc[List]
# Missing: .reindex(), .reset_index(), comparison, .sum()
""",
        "expected_patterns": ['transformation_pipelines', 'mutability_misunderstanding'],
        "expected_severity": "CRITICAL"
    },
    {
        "name": "Wrong Method (.replace vs .apply)",
        "code": """
def replace_values(df, column, threshold):
    counts = df[column].value_counts()
    mask = counts >= threshold
    df[column] = df[column].replace(counts[mask].index, 'other')
    return df

result = df.pipe(replace_values, 'Qu1', 3).pipe(replace_values, 'Qu3', 2)
""",
        "expected_patterns": ['method_semantics', 'mutability_misunderstanding'],
        "expected_severity": "CRITICAL"
    },
    {
        "name": "Missing axis Parameter",
        "code": """
result = pd.concat([df1, df2])
""",
        "expected_patterns": ['dimensional_operations'],
        "expected_severity": "MEDIUM"
    },
    {
        "name": "Clean Code - With .copy()",
        "code": """
def g(df, List):
    return df.iloc[List]

result = g(df.copy(), List)
""",
        "expected_patterns": [],  # Should detect nothing
        "expected_severity": "LOW"
    },
    {
        "name": "Clean Code - Proper groupby",
        "code": """
result = df.groupby('category').sum().reset_index()
""",
        "expected_patterns": [],  # reset_index present, but no .copy()
        "expected_severity": "CRITICAL"  # Still missing .copy()
    }
]


def run_test(test_case: Dict, verbose: bool = True) -> Dict:
    """Run a single test case."""

    if verbose:
        print(f"\n{'='*80}")
        print(f"TEST: {test_case['name']}")
        print(f"{'='*80}")
        print(f"\nCode:")
        print(test_case['code'])

    # Run detection
    result = detect_pandas_code_issues(test_case['code'])

    if verbose:
        print(f"\n--- Detection Results ---")
        print(f"Detected: {result['detected']}")
        print(f"Confidence: {result.get('confidence', 0.0):.2%}")
        print(f"Patterns: {result.get('categories', [])}")

        if result.get('details'):
            print(f"\nDetails:")
            for detail in result['details']:
                print(f"  {detail['severity']}: {detail['pattern']}")
                print(f"    Message: {detail['message']}")
                print(f"    Evidence: {detail['evidence']}")

    # Calculate risk level
    analysis_results = {
        'type': 'test',
        'math_physics': {'detected': False, 'confidence': 0.0},
        'medical_advice': {'detected': False, 'confidence': 0.0},
        'file_operations': {'detected': False, 'confidence': 0.0},
        'vibe_coding': {'detected': False, 'confidence': 0.0},
        'unsupported_claims': {'detected': False, 'confidence': 0.0},
        'pandas_code': result
    }

    risk_level = calculate_risk_level(analysis_results)
    interventions = recommend_interventions(analysis_results)

    if verbose:
        print(f"\nRisk Level: {risk_level}")
        if interventions:
            print(f"\nRecommended Interventions ({len(interventions)}):")
            for intervention in interventions:
                print(f"  - {intervention['type']}: {intervention['reason']}")

    # Check if test passed
    detected_patterns = set(result.get('categories', []))
    expected_patterns = set(test_case.get('expected_patterns', []))

    # For "clean code" tests, we expect NO patterns (except maybe .copy())
    if not expected_patterns:
        # Clean code should have low detections
        passed = len(detected_patterns) <= 1  # Allow 1 detection (like missing .copy())
    else:
        # Check if at least one expected pattern was detected
        passed = bool(detected_patterns & expected_patterns)

    if verbose:
        print(f"\n{'✓ PASS' if passed else '✗ FAIL'}")
        if not passed:
            print(f"  Expected patterns: {expected_patterns}")
            print(f"  Detected patterns: {detected_patterns}")

    return {
        'name': test_case['name'],
        'passed': passed,
        'detected': result['detected'],
        'patterns': list(detected_patterns),
        'expected_patterns': list(expected_patterns),
        'risk_level': risk_level,
        'expected_severity': test_case.get('expected_severity', 'UNKNOWN')
    }


def run_all_tests(verbose: bool = True):
    """Run all test cases and print summary."""

    print("\n" + "="*80)
    print("ToGMAL MCP Integration Test Suite")
    print("Testing DS-1000 Pattern Detection")
    print("="*80)

    results = []
    for test_case in TEST_CASES:
        result = run_test(test_case, verbose=verbose)
        results.append(result)

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")

    # Risk level distribution
    print(f"\nRisk Level Distribution:")
    risk_counts = {}
    for r in results:
        risk = r['risk_level']
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

    for risk in ['CRITICAL', 'HIGH', 'MODERATE', 'LOW']:
        count = risk_counts.get(risk, 0)
        if count > 0:
            bar = '█' * count
            print(f"  {risk:10s}: {count:2d} {bar}")

    # Pattern detection stats
    print(f"\nPattern Detection Statistics:")
    all_patterns = {}
    for r in results:
        for pattern in r['patterns']:
            all_patterns[pattern] = all_patterns.get(pattern, 0) + 1

    for pattern, count in sorted(all_patterns.items(), key=lambda x: x[1], reverse=True):
        print(f"  {pattern:30s}: {count:2d} detections")

    # Failed tests
    if failed > 0:
        print(f"\nFailed Tests:")
        for r in results:
            if not r['passed']:
                print(f"  ✗ {r['name']}")
                print(f"    Expected: {r['expected_patterns']}")
                print(f"    Got: {r['patterns']}")

    print("\n" + "="*80)
    print("Integration Test Complete")
    print("="*80)

    return results


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    results = run_all_tests(verbose=verbose)

    # Exit with error code if any tests failed
    failed_count = sum(1 for r in results if not r['passed'])
    sys.exit(0 if failed_count == 0 else 1)
