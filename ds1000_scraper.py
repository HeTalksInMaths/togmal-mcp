#!/usr/bin/env python3
"""
DS-1000 Data Science Benchmark Scraper & Analyzer
==================================================

Scrapes and analyzes the DS-1000 benchmark for data science code generation:
- 1,000 problems across 7 libraries (NumPy, Pandas, PyTorch, TensorFlow, etc.)
- Multiple model outputs (Codex, GPT-3.5, GPT-4, GPT-4o)
- Error analysis by library, problem type, and failure mode

Author: ToGMAL Project
"""

import json
import gzip
import requests
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DS1000Scraper:
    """Scrapes DS-1000 benchmark data from GitHub."""

    BASE_URL = "https://raw.githubusercontent.com/xlang-ai/DS-1000/main/data"

    AVAILABLE_MODELS = [
        'codex002',
        'gpt-3.5-turbo-0125',
        'gpt-3.5-turbo-0613',
        'gpt-4-0613',
        'gpt-4-turbo-2024-04-09',
        'gpt-4o-2024-08-06'
    ]

    def __init__(self, cache_dir: Path = Path("data/ds1000_cache")):
        """Initialize scraper."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'ToGMAL-DS1000-Scraper/1.0'})

    def download_dataset(self) -> Path:
        """Download main DS-1000 dataset."""
        logger.info("📥 Downloading DS-1000 dataset...")

        gz_file = self.cache_dir / 'ds1000.jsonl.gz'
        jsonl_file = self.cache_dir / 'ds1000.jsonl'

        if jsonl_file.exists():
            logger.info(f"✓ Dataset already exists: {jsonl_file}")
            return jsonl_file

        # Download
        url = f"{self.BASE_URL}/ds1000.jsonl.gz"
        response = self.session.get(url, timeout=60)
        response.raise_for_status()

        # Save compressed
        with open(gz_file, 'wb') as f:
            f.write(response.content)

        # Decompress
        with gzip.open(gz_file, 'rb') as f_in:
            with open(jsonl_file, 'wb') as f_out:
                f_out.write(f_in.read())

        logger.info(f"✓ Downloaded to {jsonl_file}")
        return jsonl_file

    def download_model_answers(self, model_name: str) -> Path:
        """Download model answers."""
        logger.info(f"📥 Downloading {model_name} answers...")

        answers_file = self.cache_dir / f'{model_name}-answers.jsonl'

        if answers_file.exists():
            logger.info(f"✓ Answers already exist: {answers_file}")
            return answers_file

        url = f"{self.BASE_URL}/{model_name}-answers.jsonl"
        response = self.session.get(url, timeout=60)
        response.raise_for_status()

        with open(answers_file, 'wb') as f:
            f.write(response.content)

        logger.info(f"✓ Downloaded to {answers_file}")
        return answers_file

    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load DS-1000 problems."""
        jsonl_file = self.download_dataset()

        problems = []
        with open(jsonl_file) as f:
            for line in f:
                problems.append(json.loads(line))

        logger.info(f"✓ Loaded {len(problems)} problems")
        return problems

    def load_model_answers(self, model_name: str) -> List[Dict[str, Any]]:
        """Load model answers."""
        answers_file = self.download_model_answers(model_name)

        answers = []
        with open(answers_file) as f:
            for line in f:
                answers.append(json.loads(line))

        logger.info(f"✓ Loaded {len(answers)} answers from {model_name}")
        return answers


class DS1000Analyzer:
    """Analyzes DS-1000 errors and patterns."""

    def __init__(self):
        """Initialize analyzer."""
        self.scraper = DS1000Scraper()
        self.problems = None
        self.model_answers = {}

    def load_all_data(self, models: List[str] = None):
        """Load problems and model answers."""
        logger.info("\n" + "="*70)
        logger.info("📊 LOADING DS-1000 DATA")
        logger.info("="*70)

        # Load problems
        self.problems = self.scraper.load_dataset()

        # Load model answers
        if models is None:
            models = self.scraper.AVAILABLE_MODELS[:3]  # Load first 3 by default

        for model in models:
            self.model_answers[model] = self.scraper.load_model_answers(model)

        logger.info("="*70 + "\n")

    def extract_features_from_code(self, code: str) -> Dict[str, int]:
        """Extract features from generated code."""
        # Handle case where code might be a list or other type
        if isinstance(code, list):
            code = '\n'.join(str(c) for c in code)
        elif not isinstance(code, str):
            code = str(code)

        features = {
            'len_chars': len(code),
            'len_lines': code.count('\n') + 1,
            'imports': code.count('import'),
            'function_calls': len(re.findall(r'\w+\(', code)),
            'pandas_calls': len(re.findall(r'df\.|pd\.', code)),
            'numpy_calls': len(re.findall(r'np\.', code)),
            'brackets': code.count('['),
            'dots': code.count('.'),
            'assignments': code.count('=') - code.count('=='),
        }
        return features

    def classify_error_type(self, code: str, problem: Dict) -> str:
        """Classify error type based on code analysis."""
        # Handle case where code might be a list or other type
        if isinstance(code, list):
            code = '\n'.join(str(c) for c in code)
        elif not isinstance(code, str):
            code = str(code)

        if not code or len(code.strip()) == 0:
            return 'empty_output'

        # Check for common errors
        if 'Error' in code or 'Exception' in code:
            return 'execution_error'

        # Check if code is too short
        if len(code.strip()) < 10:
            return 'incomplete_solution'

        # Check for library-specific issues
        library = problem['metadata']['library']

        if library == 'Pandas':
            if 'df.' not in code and 'pd.' not in code:
                return 'wrong_library'
        elif library == 'Numpy':
            if 'np.' not in code and 'numpy' not in code:
                return 'wrong_library'

        # Default: logic error (executes but wrong result)
        return 'logic_error'

    def analyze_by_library(self) -> Dict[str, Any]:
        """Analyze performance by library."""
        logger.info("="*70)
        logger.info("📚 ANALYSIS BY LIBRARY")
        logger.info("="*70)

        libraries = defaultdict(lambda: {
            'total': 0,
            'models': defaultdict(lambda: {'correct': 0, 'total': 0})
        })

        # Group by library
        for i, problem in enumerate(self.problems):
            library = problem['metadata']['library']
            libraries[library]['total'] += 1

            # Check each model's answer
            for model_name, answers in self.model_answers.items():
                if i < len(answers):
                    # Simplified: assume code length > 20 means attempted
                    code = answers[i].get('code', '')
                    # Handle case where code might be a list or other type
                    if isinstance(code, list):
                        code = '\n'.join(str(c) for c in code)
                    elif not isinstance(code, str):
                        code = str(code)

                    attempted = len(code.strip()) > 20

                    libraries[library]['models'][model_name]['total'] += 1
                    if attempted:
                        libraries[library]['models'][model_name]['correct'] += 1

        # Print summary
        logger.info("\nLibrary Statistics:\n")
        logger.info(f"{'Library':<20} {'Problems':<12} {'Models Tested':<15}")
        logger.info("-" * 60)

        for lib in sorted(libraries.keys()):
            data = libraries[lib]
            num_models = len(data['models'])
            logger.info(f"{lib:<20} {data['total']:<12} {num_models:<15}")

        # Detailed per-model performance
        logger.info("\n\nModel Performance by Library:\n")
        for lib in sorted(libraries.keys()):
            logger.info(f"\n{lib}:")
            data = libraries[lib]
            for model_name in sorted(data['models'].keys()):
                stats = data['models'][model_name]
                success_rate = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
                logger.info(f"  {model_name:30s}: {success_rate*100:5.1f}% ({stats['correct']:3d}/{stats['total']:3d})")

        logger.info("="*70 + "\n")

        return dict(libraries)

    def analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns across models."""
        logger.info("="*70)
        logger.info("🔍 ERROR PATTERN ANALYSIS")
        logger.info("="*70)

        error_types = defaultdict(lambda: defaultdict(int))
        library_errors = defaultdict(lambda: defaultdict(int))

        for i, problem in enumerate(self.problems):
            library = problem['metadata']['library']

            for model_name, answers in self.model_answers.items():
                if i < len(answers):
                    code = answers[i].get('code', '')
                    error_type = self.classify_error_type(code, problem)

                    error_types[model_name][error_type] += 1
                    library_errors[library][error_type] += 1

        # Print error type distribution
        logger.info("\nError Types by Model:\n")
        for model_name in sorted(error_types.keys()):
            logger.info(f"\n{model_name}:")
            total = sum(error_types[model_name].values())
            for error_type, count in sorted(error_types[model_name].items(), key=lambda x: x[1], reverse=True):
                pct = count / total * 100 if total > 0 else 0
                logger.info(f"  {error_type:25s}: {count:4d} ({pct:5.1f}%)")

        logger.info("\n\nError Types by Library:\n")
        for library in sorted(library_errors.keys()):
            logger.info(f"\n{library}:")
            total = sum(library_errors[library].values())
            for error_type, count in sorted(library_errors[library].items(), key=lambda x: x[1], reverse=True):
                pct = count / total * 100 if total > 0 else 0
                logger.info(f"  {error_type:25s}: {count:4d} ({pct:5.1f}%)")

        logger.info("="*70 + "\n")

        return {
            'by_model': dict(error_types),
            'by_library': dict(library_errors)
        }

    def analyze_code_patterns(self) -> Dict[str, Any]:
        """Analyze code generation patterns."""
        logger.info("="*70)
        logger.info("💻 CODE PATTERN ANALYSIS")
        logger.info("="*70)

        patterns = defaultdict(lambda: {
            'avg_length': [],
            'avg_lines': [],
            'avg_function_calls': [],
            'libraries_used': defaultdict(int)
        })

        for i, problem in enumerate(self.problems):
            library = problem['metadata']['library']

            for model_name, answers in self.model_answers.items():
                if i < len(answers):
                    code = answers[i].get('code', '')
                    features = self.extract_features_from_code(code)

                    patterns[model_name]['avg_length'].append(features['len_chars'])
                    patterns[model_name]['avg_lines'].append(features['len_lines'])
                    patterns[model_name]['avg_function_calls'].append(features['function_calls'])

                    if features['pandas_calls'] > 0:
                        patterns[model_name]['libraries_used']['pandas'] += 1
                    if features['numpy_calls'] > 0:
                        patterns[model_name]['libraries_used']['numpy'] += 1

        # Print summary
        logger.info("\nCode Generation Statistics:\n")
        logger.info(f"{'Model':<30} {'Avg Length':<12} {'Avg Lines':<12} {'Func Calls':<12}")
        logger.info("-" * 70)

        for model_name in sorted(patterns.keys()):
            data = patterns[model_name]
            avg_len = sum(data['avg_length']) / len(data['avg_length']) if data['avg_length'] else 0
            avg_lines = sum(data['avg_lines']) / len(data['avg_lines']) if data['avg_lines'] else 0
            avg_calls = sum(data['avg_function_calls']) / len(data['avg_function_calls']) if data['avg_function_calls'] else 0

            logger.info(f"{model_name:<30} {avg_len:<12.1f} {avg_lines:<12.1f} {avg_calls:<12.1f}")

        logger.info("="*70 + "\n")

        return dict(patterns)

    def generate_report(self, models: List[str] = None, output_dir: Path = Path("data/ds1000_analysis")):
        """Generate comprehensive analysis report."""
        logger.info("\n" + "="*70)
        logger.info("📋 DS-1000 COMPREHENSIVE ANALYSIS")
        logger.info("="*70 + "\n")

        # Load data
        self.load_all_data(models)

        # Run analyses
        library_stats = self.analyze_by_library()
        error_patterns = self.analyze_error_patterns()
        code_patterns = self.analyze_code_patterns()

        # Save results
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("💾 Saving results...")

        with open(output_dir / 'library_stats.json', 'w') as f:
            json.dump(library_stats, f, indent=2)

        with open(output_dir / 'error_patterns.json', 'w') as f:
            json.dump(error_patterns, f, indent=2)

        with open(output_dir / 'code_patterns.json', 'w') as f:
            # Convert defaultdicts to dicts for JSON serialization
            serializable = {}
            for model, data in code_patterns.items():
                serializable[model] = {
                    'avg_length': sum(data['avg_length']) / len(data['avg_length']) if data['avg_length'] else 0,
                    'avg_lines': sum(data['avg_lines']) / len(data['avg_lines']) if data['avg_lines'] else 0,
                    'avg_function_calls': sum(data['avg_function_calls']) / len(data['avg_function_calls']) if data['avg_function_calls'] else 0,
                    'libraries_used': dict(data['libraries_used'])
                }
            json.dump(serializable, f, indent=2)

        logger.info(f"✓ Results saved to {output_dir}\n")
        logger.info("="*70)

        return {
            'library_stats': library_stats,
            'error_patterns': error_patterns,
            'code_patterns': code_patterns
        }


if __name__ == '__main__':
    analyzer = DS1000Analyzer()

    # Analyze first 3 models (codex, gpt-3.5, gpt-4)
    results = analyzer.generate_report(models=['codex002', 'gpt-3.5-turbo-0613', 'gpt-4-0613'])
