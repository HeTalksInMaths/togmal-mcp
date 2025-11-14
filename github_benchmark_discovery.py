#!/usr/bin/env python3
"""
GitHub-based Benchmark Discovery System
========================================

Alternative to HuggingFace discovery for restricted networks.
Discovers and loads benchmarks from GitHub repositories.

Author: ToGMAL Project
"""

import json
import logging
import os
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import re
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class GitHubBenchmark:
    """Metadata for a GitHub-hosted benchmark."""
    name: str
    repo_full_name: str
    stars: int
    description: str

    # Data files
    data_files: List[Dict[str, str]]  # [{path, url, format}]

    # Schema detection
    has_questions: bool = False
    has_answers: bool = False
    question_fields: List[str] = None
    answer_fields: List[str] = None

    # Stats
    estimated_size: int = 0
    num_files: int = 0

    def __post_init__(self):
        if self.question_fields is None:
            self.question_fields = []
        if self.answer_fields is None:
            self.answer_fields = []


class GitHubBenchmarkDiscovery:
    """Discovers benchmarks on GitHub."""

    # Known benchmark repositories
    KNOWN_BENCHMARKS = [
        'openai/evals',
        'EleutherAI/lm-evaluation-harness',
        'google/BIG-bench',
        'tatsu-lab/stanford_alpaca',
        'declare-lab/instruct-eval',
        'anthropics/evals',
        'bigcode-project/bigcodebench'
    ]

    def __init__(self, github_token: Optional[str] = None):
        """Initialize with optional GitHub token for higher rate limits."""
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.session = requests.Session()

        if self.github_token:
            self.session.headers.update({'Authorization': f'token {self.github_token}'})
            logger.info("Using GitHub token for API requests")
        else:
            logger.warning("No GITHUB_TOKEN - using unauthenticated requests (lower rate limit)")

        self.cache_dir = Path("./data/github_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_known_benchmarks(self) -> List[GitHubBenchmark]:
        """Load curated list of known benchmark repos."""
        logger.info(f"Loading {len(self.KNOWN_BENCHMARKS)} known benchmark repos...")
        benchmarks = []

        for repo_name in self.KNOWN_BENCHMARKS:
            try:
                logger.info(f"  Checking {repo_name}...")
                url = f"https://api.github.com/repos/{repo_name}"
                response = self.session.get(url)

                if response.status_code != 200:
                    logger.warning(f"    Could not fetch {repo_name}: {response.status_code}")
                    continue

                repo = response.json()
                benchmark = self._analyze_repo(repo)

                if benchmark:
                    benchmarks.append(benchmark)
                    logger.info(f"    ✓ Added ({benchmark.num_files} files)")

                time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.warning(f"  Error loading {repo_name}: {e}")

        return benchmarks

    def search_benchmark_repos(
        self,
        keywords: Optional[List[str]] = None,
        min_stars: int = 50,
        max_results: int = 20
    ) -> List[GitHubBenchmark]:
        """
        Search GitHub for benchmark repositories.

        Args:
            keywords: Search keywords
            min_stars: Minimum star count
            max_results: Maximum results to return

        Returns:
            List of discovered benchmarks
        """
        if keywords is None:
            keywords = [
                'llm benchmark evaluation',
                'question answering benchmark',
                'nlp evaluation dataset',
                'reasoning benchmark',
                'ai evaluation'
            ]

        discovered = []
        seen_repos = set()

        for keyword in keywords:
            try:
                query = f"{keyword} language:JSON OR language:Python stars:>={min_stars}"
                url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page=10"

                logger.info(f"Searching GitHub: {keyword}")
                response = self.session.get(url)

                if response.status_code == 403:
                    logger.warning("Rate limit hit, waiting 60s...")
                    time.sleep(60)
                    continue

                response.raise_for_status()
                data = response.json()

                for repo in data.get('items', []):
                    repo_name = repo['full_name']

                    if repo_name in seen_repos:
                        continue

                    if self._looks_like_benchmark(repo):
                        benchmark = self._analyze_repo(repo)
                        if benchmark and benchmark.has_questions:
                            discovered.append(benchmark)
                            seen_repos.add(repo_name)
                            logger.info(f"  ✓ Found: {repo_name} ({benchmark.num_files} data files)")

                time.sleep(2)  # Rate limiting

            except Exception as e:
                logger.warning(f"Error searching '{keyword}': {e}")

        return discovered[:max_results]

    def _looks_like_benchmark(self, repo: Dict[str, Any]) -> bool:
        """Heuristic to check if repo is a benchmark."""
        name = repo['name'].lower()
        desc = (repo.get('description') or '').lower()

        benchmark_indicators = [
            'benchmark', 'evaluation', 'eval', 'dataset',
            'test', 'qa', 'question', 'reasoning', 'mmlu',
            'leaderboard', 'assess'
        ]

        exclude_indicators = [
            'tutorial', 'blog', 'demo', 'example',
            'template', 'boilerplate'
        ]

        has_benchmark = any(ind in name or ind in desc for ind in benchmark_indicators)
        has_exclude = any(ind in name or ind in desc for ind in exclude_indicators)

        return has_benchmark and not has_exclude

    def _analyze_repo(self, repo: Dict[str, Any]) -> Optional[GitHubBenchmark]:
        """Analyze a repo to extract benchmark metadata."""
        try:
            repo_name = repo['full_name']

            # Search for data files
            data_files = self._find_data_files(repo_name)

            if not data_files:
                return None

            # Try to detect schema from first file
            has_questions, has_answers, q_fields, a_fields = self._detect_schema(data_files[0])
            logger.info(f"    Schema detected: Q={q_fields}, A={a_fields}")

            return GitHubBenchmark(
                name=repo['name'],
                repo_full_name=repo_name,
                stars=repo['stargazers_count'],
                description=repo.get('description', ''),
                data_files=data_files,
                has_questions=has_questions,
                has_answers=has_answers,
                question_fields=q_fields,
                answer_fields=a_fields,
                num_files=len(data_files)
            )

        except Exception as e:
            logger.warning(f"Error analyzing {repo['full_name']}: {e}")
            return None

    def _find_data_files(self, repo_name: str, max_files: int = 10) -> List[Dict[str, str]]:
        """Find data files in a repository."""
        data_files = []

        try:
            # Common directories to check
            check_dirs = ['', 'data', 'evals', 'examples', 'benchmarks', 'datasets']

            for dir_path in check_dirs:
                try:
                    url = f"https://api.github.com/repos/{repo_name}/contents/{dir_path}"
                    response = self.session.get(url)

                    if response.status_code != 200:
                        continue

                    items = response.json()
                    if not isinstance(items, list):
                        continue

                    for item in items:
                        if item['type'] != 'file':
                            continue

                        file_name = item['name'].lower()

                        # Skip config/metadata files
                        skip_patterns = ['config', 'package', 'tsconfig', 'statistics', 'metadata', 'readme']
                        if any(skip in file_name for skip in skip_patterns):
                            continue

                        # Check if it's a data file
                        if file_name.endswith('.json') or file_name.endswith('.jsonl'):
                            # Prefer files with data indicators in name
                            priority = 0
                            if any(word in file_name for word in ['data', 'test', 'eval', 'question', 'sample', 'alpaca']):
                                priority = 1

                            data_files.append({
                                'path': item['path'],
                                'url': item['download_url'],
                                'format': 'jsonl' if file_name.endswith('.jsonl') else 'json',
                                'size': item.get('size', 0),
                                'priority': priority
                            })

                            if len(data_files) >= max_files * 2:  # Get more, will filter
                                break

                except Exception as e:
                    logger.debug(f"Could not check {dir_path}: {e}")
                    continue

                if len(data_files) >= max_files * 2:
                    break

                time.sleep(0.5)  # Light rate limiting

            # Sort by priority (high first) and return top files
            data_files.sort(key=lambda x: x.get('priority', 0), reverse=True)

        except Exception as e:
            logger.warning(f"Error finding data files in {repo_name}: {e}")

        return data_files[:max_files]

    def _detect_schema(self, file_info: Dict[str, str]) -> Tuple[bool, bool, List[str], List[str]]:
        """Detect if file contains questions/answers."""
        try:
            # Download small sample with streaming to avoid loading huge files
            response = self.session.get(file_info['url'], timeout=10, stream=True)

            if response.status_code != 200:
                logger.debug(f"Failed to download {file_info['url']}: {response.status_code}")
                return False, False, [], []

            # For JSON, we need to read enough to get first complete item
            # Try to get first 100KB which should be enough for most cases
            content = ''
            bytes_read = 0
            max_bytes = 100000
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    content += chunk
                    bytes_read += len(chunk)
                    if bytes_read >= max_bytes:
                        break

            response.close()

            # Parse based on format
            if file_info['format'] == 'json':
                try:
                    # Try to parse full content first
                    data = json.loads(content)
                    if isinstance(data, list) and len(data) > 0:
                        sample = data[0]
                    elif isinstance(data, dict):
                        # Might be nested
                        for key, val in data.items():
                            if isinstance(val, list) and len(val) > 0:
                                sample = val[0]
                                break
                        else:
                            sample = data
                    else:
                        logger.debug("JSON data is not list or dict with list")
                        return False, False, [], []
                except json.JSONDecodeError:
                    # Content might be truncated, try to extract first record
                    try:
                        # Look for first complete object after opening bracket
                        if content.strip().startswith('['):
                            # Find first complete { ... } record
                            start = content.find('{')
                            if start == -1:
                                return False, False, [], []

                            depth = 0
                            end = start
                            for i in range(start, len(content)):
                                if content[i] == '{':
                                    depth += 1
                                elif content[i] == '}':
                                    depth -= 1
                                    if depth == 0:
                                        end = i + 1
                                        break

                            if end > start:
                                sample = json.loads(content[start:end])
                            else:
                                return False, False, [], []
                        else:
                            return False, False, [], []
                    except Exception as e:
                        logger.debug(f"Failed to extract first JSON record: {e}")
                        return False, False, [], []
                except Exception as e:
                    logger.debug(f"Failed to parse JSON: {e}")
                    return False, False, [], []

            elif file_info['format'] == 'jsonl':
                lines = content.strip().split('\n')
                if lines:
                    try:
                        sample = json.loads(lines[0])
                    except:
                        return False, False, [], []
                else:
                    return False, False, [], []

            else:
                return False, False, [], []

            # Check for question/answer fields
            if not isinstance(sample, dict):
                return False, False, [], []

            # Keep original keys, check lowercase
            original_keys = list(sample.keys())
            keys_lower = {k: str(k).lower() for k in original_keys}

            question_indicators = {'question', 'query', 'prompt', 'input', 'problem', 'text', 'instruction'}
            answer_indicators = {'answer', 'target', 'output', 'solution', 'label', 'ground_truth', 'response'}

            q_fields = [k for k in original_keys if any(ind in keys_lower[k] for ind in question_indicators)]
            a_fields = [k for k in original_keys if any(ind in keys_lower[k] for ind in answer_indicators)]

            has_q = len(q_fields) > 0
            has_a = len(a_fields) > 0

            return has_q, has_a, q_fields, a_fields

        except Exception as e:
            logger.warning(f"Error detecting schema: {e}")
            return False, False, [], []

    def load_benchmark_data(
        self,
        benchmark: GitHubBenchmark,
        max_questions: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Load actual data from a GitHub benchmark.

        Returns:
            List of question dictionaries
        """
        all_data = []

        for file_info in benchmark.data_files[:3]:  # Limit to first 3 files
            try:
                logger.info(f"Loading {file_info['path']}...")

                # Check cache
                cache_file = self.cache_dir / f"{benchmark.repo_full_name.replace('/', '_')}_{Path(file_info['path']).name}"

                if cache_file.exists():
                    logger.info(f"  Using cached version")
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                else:
                    # Download
                    response = self.session.get(file_info['url'], timeout=30)
                    response.raise_for_status()

                    # Parse
                    if file_info['format'] == 'json':
                        data = response.json()
                        if isinstance(data, dict):
                            # Extract list from dict
                            for val in data.values():
                                if isinstance(val, list):
                                    data = val
                                    break
                    elif file_info['format'] == 'jsonl':
                        data = [json.loads(line) for line in response.text.strip().split('\n') if line.strip()]
                    else:
                        continue

                    # Cache it
                    with open(cache_file, 'w') as f:
                        json.dump(data, f)

                # Normalize data
                normalized = self._normalize_data(data, benchmark)
                all_data.extend(normalized)

                logger.info(f"  Loaded {len(normalized)} questions")

                if len(all_data) >= max_questions:
                    break

            except Exception as e:
                logger.warning(f"Error loading {file_info['path']}: {e}")

        return all_data[:max_questions]

    def _normalize_data(self, data: List[Dict], benchmark: GitHubBenchmark) -> List[Dict[str, Any]]:
        """Normalize data to standard format."""
        normalized = []

        for item in data:
            if not isinstance(item, dict):
                continue

            # Extract question
            question = None
            for field in benchmark.question_fields:
                if field in item:
                    question = str(item[field])
                    break

            if not question:
                continue

            # Extract answer
            answer = None
            for field in benchmark.answer_fields:
                if field in item:
                    answer = str(item[field])
                    break

            normalized.append({
                'question': question,
                'answer': answer,
                'source': benchmark.repo_full_name,
                'benchmark': benchmark.name,
                'metadata': {
                    'stars': benchmark.stars,
                    'original_data': item
                }
            })

        return normalized


if __name__ == '__main__':
    # Test the discovery system
    logger.info("Testing GitHub Benchmark Discovery...")

    discovery = GitHubBenchmarkDiscovery()

    logger.info("\n=== Loading known benchmarks ===")
    benchmarks = discovery.load_known_benchmarks()

    logger.info(f"\nFound {len(benchmarks)} benchmarks:")
    for bm in benchmarks:
        logger.info(f"  - {bm.repo_full_name} ({bm.stars}⭐) - {bm.num_files} files")
        logger.info(f"    Q fields: {bm.question_fields}, A fields: {bm.answer_fields}")

    if benchmarks:
        logger.info(f"\n=== Loading sample data from {benchmarks[0].repo_full_name} ===")
        data = discovery.load_benchmark_data(benchmarks[0], max_questions=10)
        logger.info(f"Loaded {len(data)} questions")
        if data:
            logger.info(f"Sample question: {data[0]['question'][:100]}...")
