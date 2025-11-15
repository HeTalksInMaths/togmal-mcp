#!/usr/bin/env python3
"""
Map syntactic errors to conceptual misunderstandings.

This analyzer identifies the MENTAL MODEL GAPS that cause API-level errors.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import re

# Conceptual Error Taxonomy
CONCEPTUAL_ERRORS = {
    'mutability_misunderstanding': {
        'description': "Doesn't understand object mutability and side effects",
        'syntactic_manifestations': [
            'missing .copy()',
            'missing inplace parameter',
            'unexpected DataFrame modification'
        ],
        'examples': [
            'result = df.iloc[List]  # Modifies df without .copy()',
            'df.drop(columns=[...])  # Returns new df, doesn\'t modify original'
        ],
        'correct_mental_model': (
            'Pandas DataFrames can be modified in-place OR return new copies. '
            'Without .copy(), operations on slices modify the original. '
            'Methods without inplace=True return NEW DataFrames.'
        ),
        'learning_resources': [
            'Pandas view vs copy semantics',
            'Python mutability (mutable vs immutable types)',
            'Reference vs value semantics'
        ]
    },

    'indexing_semantics': {
        'description': "Doesn't understand label-based vs position-based indexing",
        'syntactic_manifestations': [
            '.loc vs .iloc confusion',
            'string index with .iloc[]',
            'numeric index with .loc[]',
            'wrong indexing pattern'
        ],
        'examples': [
            'df.iloc["column_name"]  # WRONG: .iloc is position-based',
            'df.loc[0]  # May fail if index labels aren\'t 0,1,2...',
        ],
        'correct_mental_model': (
            '.loc[] selects by LABELS (row/column names). '
            '.iloc[] selects by POSITIONS (0, 1, 2...). '
            'Use .loc[] for named selection, .iloc[] for positional selection.'
        ),
        'learning_resources': [
            'Pandas indexing documentation',
            'Label-based vs position-based selection',
            'When to use .loc vs .iloc vs []'
        ]
    },

    'dimensional_operations': {
        'description': "Doesn't understand axis parameter and dimensional operations",
        'syntactic_manifestations': [
            'axis=0 vs axis=1 confusion',
            'missing axis parameter',
            'wrong dimension for operation'
        ],
        'examples': [
            'df.mean()  # Defaults to axis=0 (columnwise), may want axis=1 (rowwise)',
            'pd.concat([df1, df2])  # Defaults to axis=0 (stack rows), may want axis=1 (join columns)'
        ],
        'correct_mental_model': (
            'axis=0 means "operate along rows" (result per COLUMN). '
            'axis=1 means "operate along columns" (result per ROW). '
            'Think: axis specifies which dimension to COLLAPSE.'
        ),
        'learning_resources': [
            'NumPy axis parameter guide',
            'Pandas aggregation along axes',
            'Broadcasting and dimensional operations'
        ]
    },

    'vectorization_concept': {
        'description': "Doesn't understand vectorization (thinks imperatively, not declaratively)",
        'syntactic_manifestations': [
            'for-loop over DataFrame rows',
            'manual iteration instead of .apply()',
            'overcomplicated iterative solution'
        ],
        'examples': [
            'for i in range(len(df)): df.loc[i, "new"] = df.loc[i, "old"] * 2  # SLOW',
            'df["new"] = df["old"] * 2  # FAST (vectorized)'
        ],
        'correct_mental_model': (
            'Pandas/NumPy operations work on entire arrays at once (vectorized). '
            'Avoid for-loops - use vectorized operations, .apply(), or broadcasting. '
            'Vectorized code is 10-100x faster and more readable.'
        ),
        'learning_resources': [
            'Vectorization in NumPy/Pandas',
            'Broadcasting rules',
            'When to use .apply() vs vectorized operations'
        ]
    },

    'transformation_pipelines': {
        'description': "Doesn't understand multi-step transformation sequences",
        'syntactic_manifestations': [
            'incomplete solution (only step 1 of 4)',
            'missing aggregation step',
            'missing final transformation'
        ],
        'examples': [
            '# Task: reindex, reset, then compare\nresult = df.iloc[List]  # Only did step 1!',
            '# Task: group, aggregate, then transform\nresult = df.groupby("col")  # Forgot to aggregate!'
        ],
        'correct_mental_model': (
            'Data transformations often require multiple steps: '
            'filter → transform → aggregate → format. '
            'Each step produces input for the next. Think in pipelines.'
        ),
        'learning_resources': [
            'Method chaining in Pandas',
            'ETL pipeline concepts',
            'Functional programming for data transformation'
        ]
    },

    'index_persistence': {
        'description': "Doesn't understand how operations affect DataFrame index",
        'syntactic_manifestations': [
            'missing .reset_index() after groupby',
            'missing .reset_index(drop=True)',
            'unexpected multi-level index'
        ],
        'examples': [
            'df.groupby("col").sum()  # Creates index from groupby keys',
            'df.groupby("col").sum().reset_index()  # Converts index back to column'
        ],
        'correct_mental_model': (
            'Many operations (groupby, set_index, pivot) change the index. '
            'Use .reset_index() to convert index back to regular columns. '
            'Use drop=True to discard the old index.'
        ),
        'learning_resources': [
            'Pandas index management',
            'When and why to reset_index()',
            'Multi-level indexes'
        ]
    },

    'method_semantics': {
        'description': "Doesn't understand what specific methods do",
        'syntactic_manifestations': [
            'using .replace() when .apply() needed',
            'using .map() when .apply() needed',
            'using .median() when .mean() needed'
        ],
        'examples': [
            'df["col"].replace(lambda x: x*2)  # WRONG: replace is for value substitution',
            'df["col"].apply(lambda x: x*2)  # CORRECT: apply is for transformation'
        ],
        'correct_mental_model': (
            '.replace(): Substitute values (old_value -> new_value). '
            '.map(): Apply mapping dict or function (Series only). '
            '.apply(): Apply function to each element/row/column. '
            'Each method has specific semantics - choose based on task.'
        ),
        'learning_resources': [
            'Pandas method reference',
            'Difference between replace, map, apply',
            'When to use which transformation method'
        ]
    },

    'grouping_vs_filtering': {
        'description': "Doesn't understand difference between grouping and filtering",
        'syntactic_manifestations': [
            'using .groupby() when boolean indexing would work',
            'unnecessary aggregation',
            'overcomplicated filtering logic'
        ],
        'examples': [
            'df.groupby("col").first()  # If just filtering, use df[condition]',
            'df[df["col"] == value]  # Direct filtering, no groupby needed'
        ],
        'correct_mental_model': (
            'Filtering: Select subset of rows (boolean indexing). '
            'Grouping: Partition data for aggregation/transformation. '
            'Use filtering for simple selection, groupby for aggregation.'
        ),
        'learning_resources': [
            'Boolean indexing in Pandas',
            'When to use groupby vs boolean indexing',
            'Split-apply-combine pattern'
        ]
    },

    'attribute_vs_method': {
        'description': "Doesn't understand difference between attributes and methods",
        'syntactic_manifestations': [
            'calling attribute as method (.values() instead of .values)',
            'accessing method as attribute',
            'wrong attribute access'
        ],
        'examples': [
            'df.values()  # WRONG: values is attribute, not method',
            'df.values  # CORRECT',
            'df.shape()  # WRONG: shape is attribute',
            'df.shape  # CORRECT'
        ],
        'correct_mental_model': (
            'Attributes: Properties of objects (no parentheses) - .values, .shape, .dtype. '
            'Methods: Functions that DO something (parentheses required) - .mean(), .copy(). '
            'Attributes return state, methods perform operations.'
        ),
        'learning_resources': [
            'Python attributes vs methods',
            'Pandas API design patterns',
            '@property decorator explanation'
        ]
    },

    'api_evolution': {
        'description': "Using deprecated/old API patterns from training data",
        'syntactic_manifestations': [
            'using .values instead of .to_numpy()',
            'using .append() instead of pd.concat()',
            'using old parameter names'
        ],
        'examples': [
            'df.values  # Deprecated in favor of df.to_numpy()',
            'df.append(other)  # Deprecated in favor of pd.concat([df, other])'
        ],
        'correct_mental_model': (
            'Pandas/NumPy APIs evolve over time. '
            'Methods get deprecated, renamed, or replaced with better alternatives. '
            'Use current best practices, not legacy patterns.'
        ),
        'learning_resources': [
            'Pandas deprecation warnings',
            'Migration guides (Pandas 1.x to 2.x)',
            'Modern Pandas best practices'
        ]
    },

    'defensive_programming': {
        'description': "Over-engineering with unnecessary operations",
        'syntactic_manifestations': [
            'extra .reset_index() calls',
            'redundant type conversions',
            'unnecessary intermediate variables'
        ],
        'examples': [
            'df.reset_index().reset_index()  # Second reset_index unnecessary',
            'df.groupby("col").sum().reset_index().reset_index()  # Too many resets'
        ],
        'correct_mental_model': (
            'Add operations only when necessary for correctness. '
            'Understand what each operation does before adding it. '
            'Simpler code = fewer bugs.'
        ),
        'learning_resources': [
            'Code simplification techniques',
            'YAGNI (You Aren\'t Gonna Need It) principle',
            'Minimal viable solution approach'
        ]
    }
}


def map_syntactic_to_conceptual(syntactic_error: str, context: Dict) -> List[str]:
    """Map a syntactic error to conceptual misunderstanding(s)."""

    conceptual_errors = []

    # Map each syntactic error type to conceptual errors
    mapping = {
        'missing_method': {
            'copy': ['mutability_misunderstanding'],
            'reset_index': ['index_persistence'],
            'apply': ['method_semantics', 'vectorization_concept'],
            'sum|mean|std': ['transformation_pipelines'],
        },
        'wrong_attribute': {
            'values': ['api_evolution', 'attribute_vs_method'],
            'loc|iloc': ['indexing_semantics'],
            'shape|dtype': ['attribute_vs_method'],
        },
        'extra_method': {
            'groupby': ['grouping_vs_filtering', 'defensive_programming'],
            'reset_index': ['index_persistence', 'defensive_programming'],
        },
        'overcomplicated': {
            'for ': ['vectorization_concept'],
            'while ': ['vectorization_concept'],
        },
        'wrong_indexing': {
            'iloc|loc': ['indexing_semantics'],
        },
        'wrong_parameter': {
            'axis': ['dimensional_operations'],
            'inplace': ['mutability_misunderstanding'],
        },
        'wrong_method': {
            'replace|map|apply': ['method_semantics'],
            'median|mean|mode': ['method_semantics'],
        },
        'incomplete_solution': {
            'default': ['transformation_pipelines'],
        }
    }

    return conceptual_errors


def analyze_conceptual_patterns():
    """Analyze what conceptual errors cause syntactic errors."""

    # Load our error analysis
    analysis_dir = Path("data/deep_logic_analysis")

    with open(analysis_dir / "error_type_counts.json") as f:
        error_counts = json.load(f)

    print("="*80)
    print("🧠 SYNTACTIC ERRORS → CONCEPTUAL MISUNDERSTANDINGS")
    print("="*80)

    # Manual mapping based on our analysis
    syntactic_to_conceptual = {
        'wrong_attribute (27.6%)': [
            ('api_evolution', 'Using deprecated .values instead of .to_numpy()'),
            ('attribute_vs_method', 'Calling attribute as method or vice versa'),
            ('indexing_semantics', 'Confusing .loc vs .iloc as attributes'),
        ],
        'missing_method (21.6%)': [
            ('mutability_misunderstanding', 'Missing .copy() - doesn\'t understand side effects'),
            ('index_persistence', 'Missing .reset_index() - doesn\'t understand index changes'),
            ('transformation_pipelines', 'Missing aggregation step - incomplete pipeline'),
        ],
        'extra_method (15.8%)': [
            ('grouping_vs_filtering', 'Using .groupby() when boolean indexing would work'),
            ('defensive_programming', 'Extra .reset_index() calls without understanding necessity'),
        ],
        'overcomplicated (9.6%)': [
            ('vectorization_concept', 'For-loops instead of vectorized operations'),
            ('method_semantics', 'Manual iteration instead of built-in methods'),
        ],
        'wrong_indexing (8.2%)': [
            ('indexing_semantics', '.loc[] (labels) vs .iloc[] (positions) confusion'),
        ],
        'incomplete_solution (6.4%)': [
            ('transformation_pipelines', 'Only completes step 1 of multi-step solution'),
        ],
        'wrong_method (4.2%)': [
            ('method_semantics', '.replace() vs .map() vs .apply() confusion'),
        ],
        'wrong_parameter (4.0%)': [
            ('dimensional_operations', 'axis=0 vs axis=1 confusion'),
            ('mutability_misunderstanding', 'inplace parameter misuse'),
        ],
    }

    print("\n📊 MAPPING:\n")

    for syntactic, conceptual_list in syntactic_to_conceptual.items():
        print(f"{syntactic}:")
        for concept_key, example in conceptual_list:
            concept = CONCEPTUAL_ERRORS[concept_key]
            print(f"  → {concept_key}")
            print(f"     '{concept['description']}'")
            print(f"     Example: {example}")
        print()

    # Count conceptual error frequency
    print("\n" + "="*80)
    print("📈 CONCEPTUAL ERROR FREQUENCY")
    print("="*80)
    print("\nBased on syntactic error distribution:\n")

    conceptual_frequency = {
        'mutability_misunderstanding': 21.6 + 4.0,  # missing_method + wrong_parameter
        'indexing_semantics': 27.6 + 8.2,  # wrong_attribute + wrong_indexing
        'vectorization_concept': 9.6,  # overcomplicated
        'transformation_pipelines': 21.6 + 6.4,  # missing_method + incomplete
        'method_semantics': 15.8 + 4.2 + 9.6,  # extra + wrong_method + overcomplicated
        'dimensional_operations': 4.0,  # wrong_parameter
        'api_evolution': 27.6,  # wrong_attribute
        'index_persistence': 21.6,  # missing_method
        'grouping_vs_filtering': 15.8,  # extra_method
        'defensive_programming': 15.8,  # extra_method
        'attribute_vs_method': 27.6,  # wrong_attribute
    }

    for concept, freq in sorted(conceptual_frequency.items(), key=lambda x: x[1], reverse=True):
        bar = '█' * int(freq / 2)
        print(f"{concept:35s} ~{freq:4.1f}% {bar}")

    # Generate report
    print("\n" + "="*80)
    print("💡 TOP CONCEPTUAL GAPS TO ADDRESS")
    print("="*80)

    top_concepts = [
        ('indexing_semantics', 35.8),
        ('api_evolution', 27.6),
        ('attribute_vs_method', 27.6),
        ('transformation_pipelines', 28.0),
        ('mutability_misunderstanding', 25.6),
    ]

    for concept_key, estimated_freq in top_concepts:
        concept = CONCEPTUAL_ERRORS[concept_key]
        print(f"\n{concept_key.upper().replace('_', ' ')} (~{estimated_freq:.1f}%)")
        print(f"  Description: {concept['description']}")
        print(f"  Correct Model: {concept['correct_mental_model']}")
        print(f"  Learn: {', '.join(concept['learning_resources'][:2])}")


if __name__ == "__main__":
    analyze_conceptual_patterns()
