#!/usr/bin/env python3
"""
Deep Logic Error Analyzer for DS-1000

Analyzes the TYPES of logic errors models make, not just that they make them.
Compares generated code with reference solutions to identify specific patterns.
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import defaultdict, Counter
import difflib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeepLogicErrorAnalyzer:
    """Analyzes logic errors at a granular level."""

    def __init__(self, cache_dir: Path = Path("data/ds1000_cache")):
        self.cache_dir = cache_dir
        self.problems = []
        self.model_answers = {}

        # Logic error subcategories
        self.error_categories = {
            'wrong_method': [],           # Used wrong method (.median() instead of .mean())
            'wrong_parameter': [],        # Wrong parameter value (axis=0 vs axis=1)
            'missing_method': [],         # Missing required method call
            'extra_method': [],           # Unnecessary method call
            'wrong_attribute': [],        # Wrong attribute access (.values vs .to_numpy())
            'wrong_indexing': [],         # Wrong indexing pattern (.iloc vs .loc vs [])
            'wrong_operator': [],         # Wrong operator (+= vs =, / vs //)
            'incomplete_solution': [],    # Missing steps
            'overcomplicated': [],        # Extra unnecessary steps
            'wrong_variable': [],         # Used wrong variable name
            'wrong_order': [],           # Steps in wrong order
            'type_mismatch': [],         # Returns wrong type (array vs DataFrame)
        }

    def load_data(self, models: List[str]):
        """Load problems and model answers."""
        logger.info("Loading DS-1000 data...")

        # Load problems
        dataset_path = self.cache_dir / "ds1000.jsonl"
        with open(dataset_path) as f:
            self.problems = [json.loads(line) for line in f]
        logger.info(f"✓ Loaded {len(self.problems)} problems")

        # Load model answers
        for model in models:
            answers_path = self.cache_dir / f"{model}-answers.jsonl"
            with open(answers_path) as f:
                self.model_answers[model] = [json.loads(line) for line in f]
            logger.info(f"✓ Loaded {len(self.model_answers[model])} answers from {model}")

    def normalize_code(self, code: str) -> str:
        """Normalize code for comparison."""
        if isinstance(code, list):
            code = '\n'.join(str(c) for c in code)
        elif not isinstance(code, str):
            code = str(code)

        # Remove comments
        code = re.sub(r'#.*', '', code)
        # Remove extra whitespace
        code = re.sub(r'\s+', ' ', code)
        # Strip
        code = code.strip()

        return code

    def extract_method_calls(self, code: str) -> List[str]:
        """Extract all method calls from code."""
        # Pattern: .method_name(
        pattern = r'\.\w+\('
        methods = re.findall(pattern, code)
        return [m[1:-1] for m in methods]  # Remove . and (

    def extract_attributes(self, code: str) -> List[str]:
        """Extract attribute access patterns."""
        # Pattern: .attribute (not followed by ()
        pattern = r'\.\w+(?!\()'
        attrs = re.findall(pattern, code)
        return [a[1:] for a in attrs]  # Remove leading .

    def extract_indexing_patterns(self, code: str) -> List[str]:
        """Extract indexing patterns."""
        patterns = []
        if '.iloc[' in code:
            patterns.append('iloc')
        if '.loc[' in code:
            patterns.append('loc')
        if re.search(r'\[\d+\]', code):
            patterns.append('numeric_index')
        if re.search(r'\[[\'"]\w+[\'"]\]', code):
            patterns.append('string_index')
        return patterns

    def extract_parameters(self, code: str) -> Dict[str, List[str]]:
        """Extract common parameter patterns."""
        params = defaultdict(list)

        # axis parameter
        axis_matches = re.findall(r'axis\s*=\s*(\d+)', code)
        params['axis'] = axis_matches

        # inplace parameter
        if 'inplace=True' in code:
            params['inplace'].append('True')
        elif 'inplace=False' in code:
            params['inplace'].append('False')

        # ascending/descending
        if 'ascending=True' in code:
            params['ascending'].append('True')
        elif 'ascending=False' in code:
            params['ascending'].append('False')

        return dict(params)

    def compare_codes(self, reference: str, generated: str, problem: Dict, model: str) -> Dict[str, Any]:
        """Deep comparison of reference vs generated code."""
        ref_norm = self.normalize_code(reference)
        gen_norm = self.normalize_code(generated)

        # Exact match (normalized)
        if ref_norm == gen_norm:
            return {'type': 'exact_match', 'error_category': None}

        # Extract features from both
        ref_methods = self.extract_method_calls(reference)
        gen_methods = self.extract_method_calls(generated)

        ref_attrs = self.extract_attributes(reference)
        gen_attrs = self.extract_attributes(generated)

        ref_indexing = self.extract_indexing_patterns(reference)
        gen_indexing = self.extract_indexing_patterns(generated)

        ref_params = self.extract_parameters(reference)
        gen_params = self.extract_parameters(generated)

        analysis = {
            'problem_id': problem['metadata']['problem_id'],
            'library': problem['metadata']['library'],
            'model': model,
            'ref_methods': ref_methods,
            'gen_methods': gen_methods,
            'ref_attrs': ref_attrs,
            'gen_attrs': gen_attrs,
            'ref_indexing': ref_indexing,
            'gen_indexing': gen_indexing,
            'ref_params': ref_params,
            'gen_params': gen_params,
            'error_categories': []
        }

        # Detect specific error types

        # Wrong method calls
        if set(gen_methods) != set(ref_methods):
            missing_methods = set(ref_methods) - set(gen_methods)
            extra_methods = set(gen_methods) - set(ref_methods)

            if missing_methods:
                analysis['error_categories'].append({
                    'type': 'missing_method',
                    'details': f"Missing: {missing_methods}, Used: {set(gen_methods)}"
                })

            if extra_methods:
                # Check if it's a wrong method (e.g., median vs mean)
                if len(ref_methods) == len(gen_methods):
                    analysis['error_categories'].append({
                        'type': 'wrong_method',
                        'details': f"Expected: {ref_methods}, Got: {gen_methods}"
                    })
                else:
                    analysis['error_categories'].append({
                        'type': 'extra_method',
                        'details': f"Extra: {extra_methods}"
                    })

        # Wrong attributes
        if set(gen_attrs) != set(ref_attrs):
            analysis['error_categories'].append({
                'type': 'wrong_attribute',
                'details': f"Expected: {ref_attrs}, Got: {gen_attrs}"
            })

        # Wrong indexing
        if set(gen_indexing) != set(ref_indexing):
            analysis['error_categories'].append({
                'type': 'wrong_indexing',
                'details': f"Expected: {ref_indexing}, Got: {gen_indexing}"
            })

        # Wrong parameters
        for param_name in set(ref_params.keys()) | set(gen_params.keys()):
            ref_val = ref_params.get(param_name, [])
            gen_val = gen_params.get(param_name, [])
            if ref_val != gen_val:
                analysis['error_categories'].append({
                    'type': 'wrong_parameter',
                    'details': f"{param_name}: expected {ref_val}, got {gen_val}"
                })

        # Code length comparison
        ref_lines = len([l for l in reference.split('\n') if l.strip()])
        gen_lines = len([l for l in generated.split('\n') if l.strip()])

        if gen_lines < ref_lines * 0.5:
            analysis['error_categories'].append({
                'type': 'incomplete_solution',
                'details': f"Generated {gen_lines} lines vs {ref_lines} expected"
            })
        elif gen_lines > ref_lines * 2:
            analysis['error_categories'].append({
                'type': 'overcomplicated',
                'details': f"Generated {gen_lines} lines vs {ref_lines} expected"
            })

        # If no specific error detected but codes differ, mark as "complex_logic_error"
        if not analysis['error_categories']:
            analysis['error_categories'].append({
                'type': 'complex_logic_error',
                'details': 'Codes differ but specific pattern not detected'
            })

        return analysis

    def analyze_all_errors(self, models: List[str]) -> Dict[str, Any]:
        """Analyze all logic errors across all models."""
        logger.info("\n" + "="*70)
        logger.info("🔬 DEEP LOGIC ERROR ANALYSIS")
        logger.info("="*70)

        all_analyses = []
        error_type_counts = defaultdict(lambda: defaultdict(int))  # error_type -> model -> count
        library_error_counts = defaultdict(lambda: defaultdict(int))  # library -> error_type -> count

        for model in models:
            logger.info(f"\n📊 Analyzing {model}...")

            for i, problem in enumerate(self.problems):
                reference_code = problem.get('reference_code', '')
                generated_code = self.model_answers[model][i].get('code', '')

                # Skip if either is missing
                if not reference_code or not generated_code:
                    continue

                # Handle type conversion
                if isinstance(generated_code, list):
                    generated_code = '\n'.join(str(c) for c in generated_code)
                elif not isinstance(generated_code, str):
                    generated_code = str(generated_code)

                # Skip if generated code is too short (likely empty or error)
                if len(generated_code.strip()) < 20:
                    continue

                # Compare
                analysis = self.compare_codes(reference_code, generated_code, problem, model)

                if analysis.get('type') == 'exact_match':
                    continue  # Skip correct solutions

                all_analyses.append(analysis)

                # Count error types
                library = problem['metadata']['library']
                for error in analysis['error_categories']:
                    error_type = error['type']
                    error_type_counts[error_type][model] += 1
                    library_error_counts[library][error_type] += 1

        # Generate summary
        logger.info("\n" + "="*70)
        logger.info("📈 ERROR TYPE SUMMARY")
        logger.info("="*70)

        # Sort by total frequency
        error_totals = {et: sum(counts.values()) for et, counts in error_type_counts.items()}
        sorted_errors = sorted(error_totals.items(), key=lambda x: x[1], reverse=True)

        logger.info("\nError Type Distribution (across all models):\n")
        for error_type, total in sorted_errors:
            logger.info(f"{error_type:30s}: {total:4d} occurrences")
            for model in models:
                count = error_type_counts[error_type][model]
                if count > 0:
                    logger.info(f"  - {model:30s}: {count:4d}")

        logger.info("\n" + "="*70)
        logger.info("📚 ERROR TYPES BY LIBRARY")
        logger.info("="*70)

        for library in sorted(library_error_counts.keys()):
            logger.info(f"\n{library}:")
            lib_errors = sorted(library_error_counts[library].items(), key=lambda x: x[1], reverse=True)
            for error_type, count in lib_errors[:5]:  # Top 5 errors per library
                logger.info(f"  {error_type:30s}: {count:4d}")

        return {
            'all_analyses': all_analyses,
            'error_type_counts': dict(error_type_counts),
            'library_error_counts': dict(library_error_counts),
            'error_totals': error_totals
        }

    def find_interesting_examples(self, all_analyses: List[Dict], n_per_type: int = 3) -> Dict[str, List[Dict]]:
        """Find interesting examples for each error type."""
        logger.info("\n" + "="*70)
        logger.info("🔍 INTERESTING EXAMPLES")
        logger.info("="*70)

        examples_by_type = defaultdict(list)

        for analysis in all_analyses:
            for error in analysis['error_categories']:
                error_type = error['type']
                if len(examples_by_type[error_type]) < n_per_type:
                    examples_by_type[error_type].append({
                        'problem_id': analysis['problem_id'],
                        'library': analysis['library'],
                        'model': analysis['model'],
                        'details': error['details'],
                        'ref_methods': analysis['ref_methods'],
                        'gen_methods': analysis['gen_methods'],
                    })

        # Print examples
        for error_type, examples in sorted(examples_by_type.items()):
            logger.info(f"\n{error_type}:")
            for ex in examples[:3]:
                logger.info(f"  Problem {ex['problem_id']} ({ex['library']}, {ex['model']}):")
                logger.info(f"    {ex['details']}")

        return dict(examples_by_type)

    def save_results(self, results: Dict[str, Any], output_dir: Path = Path("data/deep_logic_analysis")):
        """Save results to JSON files."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save error counts
        with open(output_dir / "error_type_counts.json", 'w') as f:
            json.dump(results['error_type_counts'], f, indent=2)

        with open(output_dir / "library_error_counts.json", 'w') as f:
            json.dump(results['library_error_counts'], f, indent=2)

        # Save detailed analyses (first 100 for inspection)
        sample_analyses = results['all_analyses'][:100]
        with open(output_dir / "sample_analyses.json", 'w') as f:
            json.dump(sample_analyses, f, indent=2)

        logger.info(f"\n✓ Results saved to {output_dir}")


def main():
    analyzer = DeepLogicErrorAnalyzer()

    models = ['codex002', 'gpt-3.5-turbo-0613', 'gpt-4-0613']

    # Load data
    analyzer.load_data(models)

    # Analyze errors
    results = analyzer.analyze_all_errors(models)

    # Find interesting examples
    examples = analyzer.find_interesting_examples(results['all_analyses'])
    results['examples'] = examples

    # Save results
    analyzer.save_results(results)

    logger.info("\n" + "="*70)
    logger.info("✅ DEEP LOGIC ERROR ANALYSIS COMPLETE")
    logger.info("="*70)


if __name__ == "__main__":
    main()
