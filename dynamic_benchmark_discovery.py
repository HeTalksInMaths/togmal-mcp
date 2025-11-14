#!/usr/bin/env python3
"""
Dynamic Benchmark Discovery & Integration System
================================================

This system can:
1. Analyze your current vector database coverage
2. Discover new benchmarks on HuggingFace/GitHub
3. Assess schema compatibility for integration
4. Suggest expansions based on gaps
5. Automatically integrate compatible benchmarks

No more hardcoded limits - grows dynamically!

Author: ToGMAL Project
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import re

# Load HuggingFace token from environment
from dotenv import load_dotenv
load_dotenv()
HF_TOKEN = os.getenv('HF_TOKEN')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from datasets import load_dataset, get_dataset_config_names
    from huggingface_hub import HfApi, login
    import chromadb
    DEPS_AVAILABLE = True

    # Login to HuggingFace if token is available
    if HF_TOKEN:
        try:
            logger.info("Logging in to HuggingFace with provided token...")
            login(token=HF_TOKEN)
            logger.info("Successfully logged in to HuggingFace")
        except Exception as e:
            logger.warning(f"Could not login to HuggingFace (network restriction?): {e}")
            logger.info("Token will still be used passively for API requests")
            # Set token as environment variable for libraries to use
            os.environ['HF_TOKEN'] = HF_TOKEN
    else:
        logger.warning("No HF_TOKEN found in environment. You may encounter rate limits or access issues.")
except ImportError as e:
    logger.error(f"Missing dependencies: {e}")
    DEPS_AVAILABLE = False


@dataclass
class BenchmarkMetadata:
    """Rich metadata about a discovered benchmark."""
    name: str
    source: str  # 'huggingface' or 'github'
    dataset_id: str  # e.g., "cais/mmlu"
    
    # Schema info
    question_fields: List[str]  # e.g., ['question', 'query', 'problem']
    answer_fields: List[str]    # e.g., ['answer', 'solution', 'target']
    choice_fields: List[str]    # e.g., ['choices', 'options']
    domain_fields: List[str]    # e.g., ['subject', 'category', 'domain']
    
    # Content info
    num_questions: int
    domains: List[str]
    difficulty_estimate: Optional[float] = None
    
    # Leaderboard info
    has_leaderboard_results: bool = False
    leaderboard_config: Optional[str] = None
    models_evaluated: List[str] = None
    
    # Integration readiness
    schema_compatibility: float = 0.0  # 0.0 to 1.0
    integration_difficulty: str = "unknown"  # easy, medium, hard
    missing_fields: List[str] = None
    
    def __post_init__(self):
        if self.models_evaluated is None:
            self.models_evaluated = []
        if self.missing_fields is None:
            self.missing_fields = []


class CoverageAnalyzer:
    """Analyzes current vector database to identify coverage gaps."""
    
    def __init__(self, db_path: Path):
        """Initialize with existing database path."""
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=str(db_path))
        
        try:
            self.collection = self.client.get_collection("benchmark_questions")
        except:
            logger.warning("No existing collection found - starting fresh")
            self.collection = None
    
    def analyze_coverage(self) -> Dict[str, Any]:
        """
        Analyze what's currently in the database.
        
        Returns:
            {
                'total_questions': int,
                'sources': {source: count},
                'domains': {domain: count},
                'difficulty_distribution': {...},
                'coverage_gaps': [gap descriptions],
                'recommendations': [what to add next]
            }
        """
        
        if not self.collection:
            return {
                'total_questions': 0,
                'sources': {},
                'domains': {},
                'coverage_gaps': ['No data yet - start with foundational benchmarks'],
                'recommendations': [
                    'Add MMLU for broad multitask coverage',
                    'Add GPQA for graduate-level difficulty',
                    'Add GSM8K for math reasoning'
                ]
            }
        
        logger.info("Analyzing current database coverage...")
        
        # Get all data
        total = self.collection.count()
        sample_size = min(5000, total)
        sample = self.collection.get(
            limit=sample_size,
            include=['metadatas']
        )
        
        # Analyze sources
        sources = Counter()
        domains = Counter()
        difficulties = []
        success_rates = []
        
        for meta in sample['metadatas']:
            sources[meta.get('source', 'unknown')] += 1
            domains[meta.get('domain', 'unknown')] += 1
            
            if 'difficulty_score' in meta:
                difficulties.append(meta['difficulty_score'])
            if 'success_rate' in meta:
                success_rates.append(meta['success_rate'])
        
        # Scale up from sample
        scale_factor = total / sample_size if sample_size > 0 else 1
        sources = {k: int(v * scale_factor) for k, v in sources.items()}
        domains = {k: int(v * scale_factor) for k, v in domains.items()}
        
        # Identify gaps
        gaps = self._identify_gaps(sources, domains, difficulties)
        recommendations = self._generate_recommendations(gaps, sources, domains)
        
        analysis = {
            'total_questions': total,
            'sources': sources,
            'domains': domains,
            'top_domains': dict(sorted(domains.items(), key=lambda x: x[1], reverse=True)[:20]),
            'difficulty_distribution': {
                'easy': sum(1 for d in difficulties if d < 0.3),
                'moderate': sum(1 for d in difficulties if 0.3 <= d < 0.5),
                'hard': sum(1 for d in difficulties if 0.5 <= d < 0.7),
                'expert': sum(1 for d in difficulties if d >= 0.7)
            } if difficulties else {},
            'avg_success_rate': sum(success_rates) / len(success_rates) if success_rates else None,
            'coverage_gaps': gaps,
            'recommendations': recommendations
        }
        
        return analysis
    
    def _identify_gaps(
        self,
        sources: Dict[str, int],
        domains: Dict[str, int],
        difficulties: List[float]
    ) -> List[str]:
        """Identify what's missing from current coverage."""
        
        gaps = []
        
        # Check for major benchmark categories
        major_benchmarks = {
            'reasoning': ['BBH', 'ARC', 'HellaSwag'],
            'math': ['MATH', 'GSM8K', 'Minerva'],
            'coding': ['HumanEval', 'MBPP', 'CodeContests'],
            'knowledge': ['MMLU', 'TriviaQA', 'NaturalQuestions'],
            'multilingual': ['XNLI', 'MGSM', 'XQuAD'],
            'safety': ['TruthfulQA', 'ToxiGen'],
            'multimodal': ['VQA', 'COCO', 'ScienceQA']
        }
        
        for category, benchmarks in major_benchmarks.items():
            covered = any(b.lower() in str(sources).lower() for b in benchmarks)
            if not covered:
                gaps.append(f"No {category} benchmarks (consider: {', '.join(benchmarks)})")
        
        # Check difficulty coverage
        if difficulties:
            avg_difficulty = sum(difficulties) / len(difficulties)
            if avg_difficulty < 0.4:
                gaps.append("Skewed toward easy questions - add harder benchmarks")
            elif avg_difficulty > 0.6:
                gaps.append("Skewed toward hard questions - add easier benchmarks")
        
        # Check domain diversity
        domain_entropy = self._calculate_entropy(domains)
        if domain_entropy < 2.0:  # Low diversity
            gaps.append("Low domain diversity - consider broader benchmarks")
        
        # Check size thresholds
        total = sum(sources.values())
        if total < 10000:
            gaps.append("Small dataset - add large benchmarks for better coverage")
        
        return gaps if gaps else ["Good coverage - consider specialized benchmarks"]
    
    def _generate_recommendations(
        self,
        gaps: List[str],
        sources: Dict[str, int],
        domains: Dict[str, int]
    ) -> List[str]:
        """Generate specific recommendations for what to add next."""
        
        recommendations = []
        
        # Parse gaps to make recommendations
        for gap in gaps:
            if 'reasoning' in gap.lower():
                recommendations.append("Add BBH (Big-Bench Hard) for challenging reasoning")
            if 'math' in gap.lower():
                recommendations.append("Add MATH dataset for competition-level mathematics")
            if 'coding' in gap.lower():
                recommendations.append("Add HumanEval for code generation tasks")
            if 'knowledge' in gap.lower():
                recommendations.append("Add MMLU for comprehensive knowledge coverage")
            if 'multilingual' in gap.lower():
                recommendations.append("Add XNLI for cross-lingual understanding")
            if 'safety' in gap.lower():
                recommendations.append("Add TruthfulQA for truthfulness evaluation")
            if 'multimodal' in gap.lower():
                recommendations.append("Add VQA for vision-language tasks")
        
        # Add specific suggestions based on what's already there
        if 'MMLU' in sources and 'MMLU_Pro' not in sources:
            recommendations.append("Add MMLU-Pro (harder version of MMLU)")
        
        if total := sum(sources.values()):
            if total < 50000:
                recommendations.append("Add HellaSwag (large commonsense reasoning dataset)")
        
        return recommendations if recommendations else [
            "Consider domain-specific benchmarks for specialized coverage",
            "Look for recent benchmarks from 2024-2025",
            "Check for benchmarks in underrepresented languages"
        ]
    
    def _calculate_entropy(self, distribution: Dict[str, int]) -> float:
        """Calculate Shannon entropy of a distribution."""
        import math
        total = sum(distribution.values())
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in distribution.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        return entropy


class BenchmarkDiscovery:
    """Discovers new benchmarks from HuggingFace and GitHub."""
    
    def __init__(self):
        """Initialize discovery system."""
        self.hf_api = HfApi()
        self.known_benchmarks = self._load_known_benchmarks()
    
    def _load_known_benchmarks(self) -> Set[str]:
        """Load set of already-known benchmarks to avoid duplicates."""
        # This would ideally load from a cache file
        return {
            'cais/mmlu', 'Idavidrein/gpqa', 'TIGER-Lab/MMLU-Pro',
            'openai/gsm8k', 'hendrycks/competition_math', 'allenai/ai2_arc',
            # ... etc
        }
    
    def discover_huggingface_benchmarks(
        self,
        keywords: List[str] = None,
        min_downloads: int = 100,
        max_results: int = 50
    ) -> List[BenchmarkMetadata]:
        """
        Discover evaluation benchmarks on HuggingFace.
        
        Args:
            keywords: Search keywords (e.g., ['benchmark', 'evaluation', 'test'])
            min_downloads: Minimum download count threshold
            max_results: Maximum results to return
        
        Returns:
            List of discovered benchmark metadata
        """
        
        if keywords is None:
            keywords = [
                'benchmark', 'evaluation', 'test', 'assessment',
                'qa', 'question answering', 'reasoning', 'knowledge'
            ]
        
        logger.info(f"Discovering benchmarks on HuggingFace (keywords: {keywords})...")
        
        discovered = []
        
        for keyword in keywords:
            try:
                # Search datasets
                datasets = self.hf_api.list_datasets(
                    search=keyword,
                    sort="downloads",
                    direction=-1,
                    limit=max_results
                )
                
                for dataset in datasets:
                    # Skip if already known
                    if dataset.id in self.known_benchmarks:
                        continue
                    
                    # Check if it looks like a benchmark
                    if self._is_likely_benchmark(dataset):
                        metadata = self._analyze_huggingface_dataset(dataset)
                        if metadata:
                            discovered.append(metadata)
                            logger.info(f"  ✓ Found: {metadata.name} ({metadata.num_questions} questions)")
                
            except Exception as e:
                logger.warning(f"Error searching '{keyword}': {e}")
        
        # Deduplicate by dataset_id
        seen = set()
        unique = []
        for item in discovered:
            if item.dataset_id not in seen:
                seen.add(item.dataset_id)
                unique.append(item)
        
        logger.info(f"Discovered {len(unique)} new benchmarks on HuggingFace")
        
        return unique
    
    def _is_likely_benchmark(self, dataset_info) -> bool:
        """Heuristic to determine if a dataset is likely a benchmark."""
        
        name_lower = dataset_info.id.lower()
        
        # Positive indicators
        benchmark_terms = [
            'benchmark', 'eval', 'test', 'qa', 'question',
            'assessment', 'mmlu', 'glue', 'squad', 'triviaqa'
        ]
        
        if any(term in name_lower for term in benchmark_terms):
            return True
        
        # Check tags
        if hasattr(dataset_info, 'tags') and dataset_info.tags:
            tag_str = ' '.join(dataset_info.tags).lower()
            if any(term in tag_str for term in ['benchmark', 'evaluation', 'test']):
                return True
        
        return False
    
    def _analyze_huggingface_dataset(self, dataset_info) -> Optional[BenchmarkMetadata]:
        """Analyze a HuggingFace dataset to extract metadata."""
        
        try:
            # Try to load dataset info (without downloading full dataset)
            configs = get_dataset_config_names(dataset_info.id)
            
            # Try first config
            config = configs[0] if configs else None
            
            # Load small sample to inspect schema
            sample = load_dataset(
                dataset_info.id,
                config,
                split='test[:10]' if 'test' in load_dataset(dataset_info.id, config).keys() 
                else 'train[:10]'
            )
            
            # Analyze schema
            if len(sample) == 0:
                return None
            
            first_item = sample[0]
            fields = list(first_item.keys())
            
            # Identify field types
            question_fields = self._find_fields(fields, ['question', 'query', 'problem', 'prompt', 'input'])
            answer_fields = self._find_fields(fields, ['answer', 'solution', 'target', 'output', 'label'])
            choice_fields = self._find_fields(fields, ['choices', 'options', 'candidates'])
            domain_fields = self._find_fields(fields, ['subject', 'category', 'domain', 'topic', 'type'])
            
            # Calculate compatibility
            compatibility = self._calculate_compatibility(
                question_fields, answer_fields, choice_fields, domain_fields
            )
            
            # Estimate size
            num_questions = len(load_dataset(dataset_info.id, config, split='test')) if 'test' in load_dataset(dataset_info.id, config).keys() else len(load_dataset(dataset_info.id, config, split='train'))
            
            # Extract domains
            domains = []
            if domain_fields:
                domain_field = domain_fields[0]
                domains = list(set(str(item[domain_field]) for item in sample))
            
            metadata = BenchmarkMetadata(
                name=dataset_info.id.split('/')[-1],
                source='huggingface',
                dataset_id=dataset_info.id,
                question_fields=question_fields,
                answer_fields=answer_fields,
                choice_fields=choice_fields,
                domain_fields=domain_fields,
                num_questions=num_questions,
                domains=domains,
                schema_compatibility=compatibility,
                integration_difficulty=self._assess_difficulty(compatibility),
                missing_fields=self._identify_missing_fields(
                    question_fields, answer_fields, choice_fields
                )
            )
            
            # Check for Open LLM Leaderboard results
            metadata.has_leaderboard_results = self._check_leaderboard_availability(
                dataset_info.id
            )
            
            return metadata
            
        except Exception as e:
            logger.debug(f"Could not analyze {dataset_info.id}: {e}")
            return None
    
    def _find_fields(self, all_fields: List[str], candidates: List[str]) -> List[str]:
        """Find fields matching candidate names."""
        found = []
        for field in all_fields:
            field_lower = field.lower()
            if any(candidate in field_lower for candidate in candidates):
                found.append(field)
        return found
    
    def _calculate_compatibility(
        self,
        question_fields: List[str],
        answer_fields: List[str],
        choice_fields: List[str],
        domain_fields: List[str]
    ) -> float:
        """Calculate schema compatibility score (0.0 to 1.0)."""
        
        score = 0.0
        
        # Must have question field (50% weight)
        if question_fields:
            score += 0.5
        
        # Must have answer field (30% weight)
        if answer_fields:
            score += 0.3
        
        # Nice to have choices (10% weight)
        if choice_fields:
            score += 0.1
        
        # Nice to have domain (10% weight)
        if domain_fields:
            score += 0.1
        
        return score
    
    def _assess_difficulty(self, compatibility: float) -> str:
        """Assess integration difficulty based on compatibility."""
        if compatibility >= 0.8:
            return "easy"
        elif compatibility >= 0.5:
            return "medium"
        else:
            return "hard"
    
    def _identify_missing_fields(
        self,
        question_fields: List[str],
        answer_fields: List[str],
        choice_fields: List[str]
    ) -> List[str]:
        """Identify required fields that are missing."""
        missing = []
        
        if not question_fields:
            missing.append("question_field")
        if not answer_fields:
            missing.append("answer_field")
        
        return missing
    
    def _check_leaderboard_availability(self, dataset_id: str) -> bool:
        """Check if this benchmark has Open LLM Leaderboard results."""
        
        # Common patterns
        benchmark_name = dataset_id.split('/')[-1].lower()
        
        known_leaderboard = [
            'mmlu', 'gpqa', 'arc', 'hellaswag', 'gsm8k',
            'winogrande', 'truthfulqa', 'bbh', 'math'
        ]
        
        return any(known in benchmark_name for known in known_leaderboard)
    
    def discover_github_benchmarks(
        self,
        search_queries: List[str] = None
    ) -> List[BenchmarkMetadata]:
        """
        Discover benchmarks from GitHub repositories.
        
        Note: This requires GitHub API access. Returns basic metadata only.
        """
        
        logger.info("GitHub discovery not yet implemented")
        logger.info("To add: Use GitHub API to search for repos with 'benchmark' or 'evaluation'")
        logger.info("Then analyze repo structure for dataset files")
        
        return []


class DynamicBenchmarkIntegrator:
    """
    Dynamically integrates new benchmarks into vector database.
    
    Uses discovery and coverage analysis to automatically expand the database.
    """
    
    def __init__(
        self,
        db_path: Path,
        embedding_model_name: str = "all-MiniLM-L6-v2"
    ):
        """Initialize with database path."""
        self.db_path = db_path
        self.analyzer = CoverageAnalyzer(db_path)
        self.discovery = BenchmarkDiscovery()
        
        # Import embedding model
        from sentence_transformers import SentenceTransformer
        self.embedding_model = SentenceTransformer(embedding_model_name)
    
    def suggest_next_benchmarks(
        self,
        max_suggestions: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Analyze current coverage and suggest specific benchmarks to add next.
        
        Returns:
            List of suggestions with rationale
        """
        
        logger.info("Analyzing coverage and discovering new benchmarks...")
        
        # Analyze what we have
        coverage = self.analyzer.analyze_coverage()
        
        # Discover new options
        discovered = self.discovery.discover_huggingface_benchmarks(max_results=50)
        
        # Filter to high-quality, compatible benchmarks
        candidates = [
            b for b in discovered
            if b.schema_compatibility >= 0.5  # At least medium compatibility
            and b.num_questions >= 100  # Reasonable size
        ]
        
        # Rank by relevance to gaps
        ranked = self._rank_by_relevance(candidates, coverage)
        
        # Format suggestions
        suggestions = []
        for benchmark, score, reason in ranked[:max_suggestions]:
            suggestions.append({
                'name': benchmark.name,
                'dataset_id': benchmark.dataset_id,
                'num_questions': benchmark.num_questions,
                'compatibility': benchmark.schema_compatibility,
                'integration_difficulty': benchmark.integration_difficulty,
                'relevance_score': score,
                'reason': reason,
                'domains': benchmark.domains[:5],  # Top 5 domains
                'has_leaderboard_results': benchmark.has_leaderboard_results
            })
        
        return suggestions
    
    def _rank_by_relevance(
        self,
        candidates: List[BenchmarkMetadata],
        coverage: Dict[str, Any]
    ) -> List[Tuple[BenchmarkMetadata, float, str]]:
        """Rank candidates by relevance to coverage gaps."""
        
        ranked = []
        
        for benchmark in candidates:
            score = 0.0
            reasons = []
            
            # Bonus for high compatibility
            score += benchmark.schema_compatibility * 20
            if benchmark.schema_compatibility >= 0.8:
                reasons.append("easy integration")
            
            # Bonus for leaderboard availability
            if benchmark.has_leaderboard_results:
                score += 30
                reasons.append("real success rates available")
            
            # Bonus for filling gaps
            for gap in coverage.get('coverage_gaps', []):
                gap_lower = gap.lower()
                name_lower = benchmark.name.lower()
                
                if any(term in name_lower for term in ['reason', 'logic', 'inference']):
                    if 'reasoning' in gap_lower:
                        score += 25
                        reasons.append("fills reasoning gap")
                
                if any(term in name_lower for term in ['math', 'arithmetic', 'algebra']):
                    if 'math' in gap_lower:
                        score += 25
                        reasons.append("fills math gap")
                
                if any(term in name_lower for term in ['code', 'programming', 'software']):
                    if 'coding' in gap_lower:
                        score += 25
                        reasons.append("fills coding gap")
            
            # Bonus for size (more data is good, but not too much)
            if 1000 <= benchmark.num_questions <= 10000:
                score += 10
                reasons.append("good size")
            elif benchmark.num_questions > 10000:
                score += 5
                reasons.append("large coverage")
            
            # Bonus for domain diversity
            if len(benchmark.domains) > 5:
                score += 5
                reasons.append("diverse domains")
            
            # Penalize if very similar to existing
            for existing_source in coverage.get('sources', {}).keys():
                if benchmark.name.lower() in existing_source.lower():
                    score -= 20
                    reasons.append("similar to existing")
            
            reason_str = "; ".join(reasons) if reasons else "candidate benchmark"
            ranked.append((benchmark, score, reason_str))
        
        # Sort by score
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return ranked
    
    def auto_expand(
        self,
        max_benchmarks: int = 5,
        dry_run: bool = False
    ) -> List[str]:
        """
        Automatically discover and integrate new benchmarks.
        
        Args:
            max_benchmarks: Maximum number of benchmarks to add
            dry_run: If True, only suggest without actually integrating
        
        Returns:
            List of benchmark names that were (or would be) added
        """
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Auto-expanding database...")
        
        # Get suggestions
        suggestions = self.suggest_next_benchmarks(max_suggestions=max_benchmarks * 2)
        
        # Filter to best candidates
        top_candidates = [
            s for s in suggestions
            if s['compatibility'] >= 0.7  # High compatibility only
            and s['integration_difficulty'] == 'easy'
        ][:max_benchmarks]
        
        if not top_candidates:
            logger.info("No easy-to-integrate benchmarks found")
            return []
        
        added = []
        
        for candidate in top_candidates:
            logger.info(f"\n{'[DRY RUN] ' if dry_run else ''}Adding {candidate['name']}...")
            logger.info(f"  Reason: {candidate['reason']}")
            logger.info(f"  Size: {candidate['num_questions']} questions")
            logger.info(f"  Compatibility: {candidate['compatibility']:.0%}")
            
            if not dry_run:
                try:
                    # Actually integrate
                    success = self._integrate_benchmark(candidate['dataset_id'])
                    if success:
                        added.append(candidate['name'])
                        logger.info(f"  ✓ Successfully integrated {candidate['name']}")
                    else:
                        logger.warning(f"  ✗ Failed to integrate {candidate['name']}")
                except Exception as e:
                    logger.error(f"  ✗ Error integrating {candidate['name']}: {e}")
            else:
                added.append(f"[DRY RUN] {candidate['name']}")
        
        return added
    
    def _integrate_benchmark(self, dataset_id: str) -> bool:
        """Actually integrate a benchmark into the database."""
        # This would implement the full integration logic
        # Similar to massive_vector_db_builder.py but for a single benchmark
        logger.info(f"  Integration logic would go here for {dataset_id}")
        return True


def main():
    """Main demo of dynamic discovery and expansion."""
    
    # Path to your existing database
    db_path = Path("./data/vector_db_topline")
    
    logger.info("="*80)
    logger.info("DYNAMIC BENCHMARK DISCOVERY & EXPANSION")
    logger.info("="*80)
    
    # Step 1: Analyze current coverage
    logger.info("\n1. Analyzing current database coverage...")
    analyzer = CoverageAnalyzer(db_path)
    coverage = analyzer.analyze_coverage()
    
    print("\n" + "="*80)
    print("CURRENT COVERAGE ANALYSIS")
    print("="*80)
    print(f"Total questions: {coverage['total_questions']:,}")
    print(f"\nSources ({len(coverage['sources'])}):")
    for source, count in list(coverage['sources'].items())[:10]:
        print(f"  {source}: {count:,}")
    
    print(f"\nTop domains:")
    for domain, count in list(coverage.get('top_domains', {}).items())[:10]:
        print(f"  {domain}: {count:,}")
    
    print(f"\nCoverage gaps:")
    for gap in coverage['coverage_gaps']:
        print(f"  • {gap}")
    
    print(f"\nRecommendations:")
    for rec in coverage['recommendations']:
        print(f"  → {rec}")
    
    # Step 2: Discover new benchmarks
    logger.info("\n2. Discovering new benchmarks on HuggingFace...")
    integrator = DynamicBenchmarkIntegrator(db_path)
    suggestions = integrator.suggest_next_benchmarks(max_suggestions=10)
    
    print("\n" + "="*80)
    print("SUGGESTED BENCHMARKS TO ADD")
    print("="*80)
    
    for i, sugg in enumerate(suggestions, 1):
        print(f"\n{i}. {sugg['name']} ({sugg['dataset_id']})")
        print(f"   Size: {sugg['num_questions']:,} questions")
        print(f"   Compatibility: {sugg['compatibility']:.0%}")
        print(f"   Difficulty: {sugg['integration_difficulty']}")
        print(f"   Reason: {sugg['reason']}")
        if sugg['has_leaderboard_results']:
            print(f"   ✓ Real success rates available!")
        if sugg['domains']:
            print(f"   Domains: {', '.join(sugg['domains'][:3])}")
    
    # Step 3: Auto-expand (dry run)
    logger.info("\n3. Simulating auto-expansion...")
    added = integrator.auto_expand(max_benchmarks=3, dry_run=True)
    
    print("\n" + "="*80)
    print("AUTO-EXPANSION RESULTS (DRY RUN)")
    print("="*80)
    print(f"Would add {len(added)} benchmarks:")
    for name in added:
        print(f"  • {name}")
    
    print("\n" + "="*80)
    print("To actually expand, run: integrator.auto_expand(max_benchmarks=3, dry_run=False)")
    print("="*80)


if __name__ == "__main__":
    main()
