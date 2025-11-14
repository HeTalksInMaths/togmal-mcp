#!/usr/bin/env python3
"""
Massive Vector Database Builder with Two Versions
==================================================

Version 1: DETAILED - Per-question model answers (slower, smaller dataset)
Version 2: TOPLINE - Only aggregate success rates (faster, larger dataset)

This script builds both versions with periodic verification.
Designed to maximize use of Claude Code credits before Nov 18th.

Author: ToGMAL Project
"""

import json
import logging
import os
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import time
from datetime import datetime

# Load HuggingFace token from environment
from dotenv import load_dotenv
load_dotenv()
HF_TOKEN = os.getenv('HF_TOKEN')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vector_db_build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from datasets import load_dataset, get_dataset_config_names
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings
    from huggingface_hub import login
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
class BenchmarkConfig:
    """Configuration for each benchmark to fetch"""
    name: str
    huggingface_dataset: str
    leaderboard_config_pattern: str  # e.g., "harness_gpqa_0" or "harness_hendrycksTest-{subject}_5"
    has_subjects: bool = False
    subjects: Optional[List[str]] = None
    max_questions: Optional[int] = None  # Limit per subject/benchmark
    difficulty_estimate: float = 0.5  # Fallback if no data
    
    # Model availability (which models have this benchmark)
    available_models: Optional[List[str]] = None


class MassiveVectorDBBuilder:
    """
    Builds two versions of vector database:
    1. DETAILED: Per-question with individual model answers
    2. TOPLINE: Aggregate success rates only (larger dataset)
    """
    
    def __init__(
        self,
        detailed_db_path: Path = Path("./data/vector_db_detailed"),
        topline_db_path: Path = Path("./data/vector_db_topline"),
        embedding_model: str = "all-MiniLM-L6-v2",
        checkpoint_dir: Path = Path("./data/checkpoints")
    ):
        """Initialize builder with separate paths for detailed and topline versions."""
        
        if not DEPS_AVAILABLE:
            raise ImportError("Required dependencies not installed")
        
        self.detailed_db_path = detailed_db_path
        self.topline_db_path = topline_db_path
        self.checkpoint_dir = checkpoint_dir
        
        # Create directories
        for path in [detailed_db_path, topline_db_path, checkpoint_dir]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model (shared across both DBs)
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Initialize ChromaDB clients
        logger.info("Initializing ChromaDB clients...")
        self.detailed_client = chromadb.PersistentClient(
            path=str(detailed_db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        self.topline_client = chromadb.PersistentClient(
            path=str(topline_db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collections
        self.detailed_collection = self._get_or_create_collection(
            self.detailed_client, 
            "detailed_questions",
            "Questions with individual model answers"
        )
        self.topline_collection = self._get_or_create_collection(
            self.topline_client,
            "topline_questions", 
            "Questions with aggregate success rates only"
        )
        
        # Statistics
        self.stats = {
            'detailed': defaultdict(int),
            'topline': defaultdict(int),
            'errors': [],
            'start_time': datetime.now(),
            'benchmarks_completed': []
        }
    
    def _get_or_create_collection(self, client, name, description):
        """Get existing collection or create new one."""
        try:
            return client.get_collection(name)
        except:
            return client.create_collection(
                name=name,
                metadata={"description": description}
            )
    
    def get_benchmark_configs(self) -> List[BenchmarkConfig]:
        """
        Define all benchmarks to fetch.
        
        Returns comprehensive list of benchmarks available on Open LLM Leaderboard.
        """
        
        # Top models ranked by average performance
        top_models = [
            "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "mistralai/Mixtral-8x22B-Instruct-v0.1",
            "google/gemma-2-27b-it",
            "microsoft/Phi-3-medium-4k-instruct",
        ]
        
        # MMLU subjects (all 57)
        mmlu_subjects = [
            "abstract_algebra", "anatomy", "astronomy", "business_ethics",
            "clinical_knowledge", "college_biology", "college_chemistry",
            "college_computer_science", "college_mathematics", "college_medicine",
            "college_physics", "computer_security", "conceptual_physics",
            "econometrics", "electrical_engineering", "elementary_mathematics",
            "formal_logic", "global_facts", "high_school_biology",
            "high_school_chemistry", "high_school_computer_science",
            "high_school_european_history", "high_school_geography",
            "high_school_government_and_politics", "high_school_macroeconomics",
            "high_school_mathematics", "high_school_microeconomics",
            "high_school_physics", "high_school_psychology", "high_school_statistics",
            "high_school_us_history", "high_school_world_history", "human_aging",
            "human_sexuality", "international_law", "jurisprudence",
            "logical_fallacies", "machine_learning", "management", "marketing",
            "medical_genetics", "miscellaneous", "moral_disputes",
            "moral_scenarios", "nutrition", "philosophy", "prehistory",
            "professional_accounting", "professional_law", "professional_medicine",
            "professional_psychology", "public_relations", "security_studies",
            "sociology", "us_foreign_policy", "virology", "world_religions"
        ]
        
        configs = [
            # GPQA Diamond - Graduate level, very hard
            BenchmarkConfig(
                name="GPQA_Diamond",
                huggingface_dataset="Idavidrein/gpqa",
                leaderboard_config_pattern="harness_gpqa_0",
                has_subjects=False,
                difficulty_estimate=0.30,
                available_models=top_models
            ),
            
            # MMLU - All 57 subjects
            BenchmarkConfig(
                name="MMLU",
                huggingface_dataset="cais/mmlu",
                leaderboard_config_pattern="harness_hendrycksTest-{subject}_5",
                has_subjects=True,
                subjects=mmlu_subjects,
                difficulty_estimate=0.65,
                available_models=top_models
            ),
            
            # MMLU-Pro - Harder version with 10 choices
            BenchmarkConfig(
                name="MMLU_Pro",
                huggingface_dataset="TIGER-Lab/MMLU-Pro",
                leaderboard_config_pattern="harness_mmlu_pro_0",
                has_subjects=False,
                max_questions=2000,
                difficulty_estimate=0.45,
                available_models=top_models[:3]  # Not all models have this
            ),
            
            # ARC Challenge - Grade school science
            BenchmarkConfig(
                name="ARC_Challenge",
                huggingface_dataset="allenai/ai2_arc",
                leaderboard_config_pattern="harness_arc_challenge_25",
                has_subjects=False,
                difficulty_estimate=0.70,
                available_models=top_models
            ),
            
            # HellaSwag - Commonsense reasoning
            BenchmarkConfig(
                name="HellaSwag",
                huggingface_dataset="Rowan/hellaswag",
                leaderboard_config_pattern="harness_hellaswag_10",
                has_subjects=False,
                max_questions=5000,
                difficulty_estimate=0.75,
                available_models=top_models
            ),
            
            # GSM8K - Grade school math
            BenchmarkConfig(
                name="GSM8K",
                huggingface_dataset="openai/gsm8k",
                leaderboard_config_pattern="harness_gsm8k_5",
                has_subjects=False,
                difficulty_estimate=0.60,
                available_models=top_models
            ),
            
            # WinoGrande - Coreference resolution
            BenchmarkConfig(
                name="WinoGrande",
                huggingface_dataset="allenai/winogrande",
                leaderboard_config_pattern="harness_winogrande_5",
                has_subjects=False,
                max_questions=2000,
                difficulty_estimate=0.75,
                available_models=top_models
            ),
            
            # TruthfulQA - Truthfulness evaluation
            BenchmarkConfig(
                name="TruthfulQA",
                huggingface_dataset="truthful_qa",
                leaderboard_config_pattern="harness_truthfulqa_mc_0",
                has_subjects=False,
                difficulty_estimate=0.40,
                available_models=top_models
            ),
            
            # BBH (Big-Bench Hard) - Challenging reasoning
            BenchmarkConfig(
                name="BBH",
                huggingface_dataset="lukaemon/bbh",
                leaderboard_config_pattern="harness_bbh_0",
                has_subjects=False,
                difficulty_estimate=0.45,
                available_models=top_models[:3]
            ),
            
            # MATH - Competition mathematics
            BenchmarkConfig(
                name="MATH",
                huggingface_dataset="hendrycks/competition_math",
                leaderboard_config_pattern="harness_minerva_math_4",
                has_subjects=False,
                max_questions=1000,
                difficulty_estimate=0.35,
                available_models=top_models[:3]
            ),
        ]
        
        return configs
    
    def fetch_detailed_results(
        self,
        config: BenchmarkConfig,
        top_k: int = 5
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch DETAILED per-question results with individual model answers.
        
        This is slower but provides full model-by-model results.
        Used for DETAILED database version.
        
        Returns:
            {
                question_id: {
                    'success_rate': 0.6,
                    'num_models': 5,
                    'model_answers': {
                        'model1': True,
                        'model2': False,
                        ...
                    }
                }
            }
        """
        logger.info(f"Fetching DETAILED results for {config.name}...")
        
        models = (config.available_models or [])[:top_k]
        question_results = defaultdict(lambda: {'results': [], 'model_answers': {}})
        
        if config.has_subjects:
            # Process each subject
            for subject in config.subjects:
                config_name = config.leaderboard_config_pattern.format(subject=subject)
                self._fetch_config_for_models(
                    models, config_name, f"{config.name}_{subject}", question_results
                )
        else:
            # Single config
            self._fetch_config_for_models(
                models, config.leaderboard_config_pattern, config.name, question_results
            )
        
        # Aggregate results
        aggregated = {}
        for qid, data in question_results.items():
            if data['results']:
                aggregated[qid] = {
                    'success_rate': sum(data['results']) / len(data['results']),
                    'num_models': len(data['results']),
                    'model_answers': data['model_answers']
                }
        
        logger.info(f"  DETAILED: {len(aggregated)} questions with full model answers")
        return aggregated
    
    def fetch_topline_results(
        self,
        config: BenchmarkConfig,
        top_k: int = 5
    ) -> Dict[str, float]:
        """
        Fetch TOPLINE aggregate results only (no individual model answers).
        
        This is faster and allows larger datasets.
        Used for TOPLINE database version.
        
        Returns:
            {question_id: success_rate}
        """
        logger.info(f"Fetching TOPLINE results for {config.name}...")
        
        # For topline, we only need aggregate stats, not individual answers
        # This allows us to be more aggressive with fetching
        detailed = self.fetch_detailed_results(config, top_k=top_k)
        
        # Strip out model_answers to save memory
        topline = {
            qid: data['success_rate']
            for qid, data in detailed.items()
        }
        
        logger.info(f"  TOPLINE: {len(topline)} questions with aggregate rates")
        return topline
    
    def _fetch_config_for_models(
        self,
        models: List[str],
        config_name: str,
        prefix: str,
        question_results: Dict
    ):
        """Helper to fetch a specific config across multiple models."""
        
        for model in models:
            try:
                dataset_name = f"open-llm-leaderboard/details_{model.replace('/', '__')}"
                
                results = load_dataset(dataset_name, config_name, split="latest")
                
                for row in results:
                    doc_id = row.get('doc_id', row.get('example', 0))
                    question_id = f"{prefix}_{doc_id}"
                    
                    is_correct = row.get('exact_match', False)
                    
                    question_results[question_id]['results'].append(bool(is_correct))
                    question_results[question_id]['model_answers'][model] = bool(is_correct)
                
                logger.info(f"    ✓ {model.split('/')[-1]}: {len(results)} questions")
                
            except Exception as e:
                logger.warning(f"    ✗ {model}: {e}")
    
    def load_original_questions(
        self,
        config: BenchmarkConfig
    ) -> List[Dict[str, Any]]:
        """Load original questions from HuggingFace dataset."""
        
        logger.info(f"Loading original questions for {config.name}...")
        
        questions = []
        
        try:
            if config.has_subjects:
                # Load each subject
                for subject in config.subjects:
                    dataset = load_dataset(config.huggingface_dataset, "all", split="test")
                    
                    # Filter by subject
                    subject_questions = [
                        item for item in dataset 
                        if item.get('subject') == subject
                    ]
                    
                    for idx, item in enumerate(subject_questions):
                        if config.max_questions and idx >= config.max_questions:
                            break
                        
                        questions.append({
                            'question_id': f"{config.name}_{subject}_{idx}",
                            'question_text': item['question'],
                            'domain': subject,
                            'source': config.name,
                            'choices': item.get('choices', []),
                            'correct_answer': item.get('choices', [])[item.get('answer', 0)] if item.get('choices') else item.get('answer'),
                        })
            else:
                # Single dataset
                dataset = load_dataset(config.huggingface_dataset, split="test")
                
                for idx, item in enumerate(dataset):
                    if config.max_questions and idx >= config.max_questions:
                        break
                    
                    questions.append({
                        'question_id': f"{config.name}_{idx}",
                        'question_text': self._extract_question_text(item),
                        'domain': config.name.lower(),
                        'source': config.name,
                        'choices': item.get('choices', []),
                        'correct_answer': self._extract_answer(item),
                    })
            
            logger.info(f"  Loaded {len(questions)} original questions")
            
        except Exception as e:
            logger.error(f"  Failed to load {config.name}: {e}")
        
        return questions
    
    def _extract_question_text(self, item: Dict) -> str:
        """Extract question text from dataset item."""
        for key in ['question', 'Question', 'problem', 'query', 'prompt']:
            if key in item:
                return item[key]
        return str(item)
    
    def _extract_answer(self, item: Dict) -> str:
        """Extract answer from dataset item."""
        for key in ['answer', 'Answer', 'solution', 'target']:
            if key in item:
                return str(item[key])
        return ""
    
    def integrate_and_index(
        self,
        config: BenchmarkConfig,
        detailed_results: Dict[str, Dict[str, Any]],
        topline_results: Dict[str, float],
        original_questions: List[Dict[str, Any]]
    ):
        """
        Integrate results with original questions and index into both databases.
        
        Args:
            detailed_results: Per-question results with model answers
            topline_results: Per-question aggregate success rates
            original_questions: Original question texts
        """
        
        logger.info(f"Integrating and indexing {config.name}...")
        
        detailed_batch = []
        topline_batch = []
        
        for q in original_questions:
            qid = q['question_id']
            
            # Prepare detailed version (with model answers)
            if qid in detailed_results:
                detailed_batch.append({
                    **q,
                    'success_rate': detailed_results[qid]['success_rate'],
                    'num_models': detailed_results[qid]['num_models'],
                    'model_answers': detailed_results[qid]['model_answers'],
                    'difficulty_score': 1.0 - detailed_results[qid]['success_rate'],
                    'has_real_data': True
                })
            else:
                detailed_batch.append({
                    **q,
                    'success_rate': config.difficulty_estimate,
                    'num_models': 0,
                    'model_answers': {},
                    'difficulty_score': 1.0 - config.difficulty_estimate,
                    'has_real_data': False
                })
            
            # Prepare topline version (aggregate only)
            if qid in topline_results:
                topline_batch.append({
                    **q,
                    'success_rate': topline_results[qid],
                    'difficulty_score': 1.0 - topline_results[qid],
                    'has_real_data': True
                })
            else:
                topline_batch.append({
                    **q,
                    'success_rate': config.difficulty_estimate,
                    'difficulty_score': 1.0 - config.difficulty_estimate,
                    'has_real_data': False
                })
        
        # Index detailed version
        self._index_batch(
            self.detailed_collection,
            detailed_batch,
            include_model_answers=True
        )
        self.stats['detailed'][config.name] = len(detailed_batch)
        
        # Index topline version
        self._index_batch(
            self.topline_collection,
            topline_batch,
            include_model_answers=False
        )
        self.stats['topline'][config.name] = len(topline_batch)
        
        logger.info(f"  ✓ Indexed {len(detailed_batch)} questions to both databases")
    
    def _index_batch(
        self,
        collection,
        questions: List[Dict[str, Any]],
        include_model_answers: bool
    ):
        """Index a batch of questions into ChromaDB."""
        
        if not questions:
            return
        
        # Generate embeddings
        texts = [q['question_text'] for q in questions]
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        # Prepare metadata (exclude model_answers if topline)
        metadatas = []
        for q in questions:
            meta = {
                'source': q['source'],
                'domain': q['domain'],
                'success_rate': q['success_rate'],
                'difficulty_score': q['difficulty_score'],
                'has_real_data': q['has_real_data']
            }
            if include_model_answers and 'model_answers' in q:
                # Store as JSON string
                meta['model_answers'] = json.dumps(q['model_answers'])
            metadatas.append(meta)
        
        # Add to collection in batches
        batch_size = 1000
        for i in range(0, len(questions), batch_size):
            end_idx = min(i + batch_size, len(questions))
            
            collection.add(
                embeddings=embeddings[i:end_idx].tolist(),
                metadatas=metadatas[i:end_idx],
                documents=texts[i:end_idx],
                ids=[q['question_id'] for q in questions[i:end_idx]]
            )
    
    def save_checkpoint(self, benchmark_name: str):
        """Save progress checkpoint."""
        checkpoint = {
            'benchmark': benchmark_name,
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats
        }
        
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{benchmark_name}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        logger.info(f"  Checkpoint saved: {checkpoint_file}")
    
    def verify_database(self, db_name: str):
        """Run verification checks on database."""
        
        logger.info(f"\n{'='*60}")
        logger.info(f"VERIFYING {db_name.upper()} DATABASE")
        logger.info('='*60)
        
        collection = (self.detailed_collection if db_name == 'detailed' 
                     else self.topline_collection)
        
        # Get total count
        total = collection.count()
        logger.info(f"Total questions: {total}")
        
        # Sample and check
        sample = collection.get(limit=100, include=['metadatas'])
        
        if sample['metadatas']:
            # Check for real data
            with_real_data = sum(1 for m in sample['metadatas'] if m.get('has_real_data'))
            logger.info(f"Questions with real data: {with_real_data}/100 ({with_real_data}%)")
            
            # Check success rate distribution
            rates = [m['success_rate'] for m in sample['metadatas']]
            logger.info(f"Success rate range: {min(rates):.1%} - {max(rates):.1%}")
            logger.info(f"Average success rate: {sum(rates)/len(rates):.1%}")
            
            # Check sources
            sources = {}
            for m in sample['metadatas']:
                sources[m['source']] = sources.get(m['source'], 0) + 1
            logger.info(f"Sources in sample: {sources}")
        
        logger.info('='*60 + '\n')
    
    def build_all(
        self,
        top_k_models: int = 5,
        verify_every_n: int = 3
    ):
        """
        Build complete vector databases with all benchmarks.
        
        Args:
            top_k_models: Number of top models to use for each benchmark
            verify_every_n: Run verification every N benchmarks
        """
        
        configs = self.get_benchmark_configs()
        
        logger.info("\n" + "="*80)
        logger.info("MASSIVE VECTOR DATABASE BUILD")
        logger.info("="*80)
        logger.info(f"Total benchmarks to process: {len(configs)}")
        logger.info(f"Top-K models per benchmark: {top_k_models}")
        logger.info(f"Building TWO versions:")
        logger.info(f"  1. DETAILED: {self.detailed_db_path} (with model answers)")
        logger.info(f"  2. TOPLINE: {self.topline_db_path} (aggregate only)")
        logger.info("="*80 + "\n")
        
        for idx, config in enumerate(configs, 1):
            try:
                logger.info(f"\n{'#'*80}")
                logger.info(f"BENCHMARK {idx}/{len(configs)}: {config.name}")
                logger.info('#'*80 + '\n')
                
                start_time = time.time()
                
                # Step 1: Fetch detailed results
                detailed_results = self.fetch_detailed_results(config, top_k=top_k_models)
                
                # Step 2: Fetch topline results
                topline_results = self.fetch_topline_results(config, top_k=top_k_models)
                
                # Step 3: Load original questions
                original_questions = self.load_original_questions(config)
                
                # Step 4: Integrate and index
                self.integrate_and_index(
                    config, detailed_results, topline_results, original_questions
                )
                
                # Step 5: Save checkpoint
                self.save_checkpoint(config.name)
                self.stats['benchmarks_completed'].append(config.name)
                
                elapsed = time.time() - start_time
                logger.info(f"\n✓ {config.name} completed in {elapsed:.1f}s")
                
                # Periodic verification
                if idx % verify_every_n == 0:
                    self.verify_database('detailed')
                    self.verify_database('topline')
                
            except Exception as e:
                logger.error(f"✗ Failed to process {config.name}: {e}")
                self.stats['errors'].append({
                    'benchmark': config.name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # Final statistics
        self.print_final_stats()
    
    def print_final_stats(self):
        """Print final build statistics."""
        
        elapsed = datetime.now() - self.stats['start_time']
        
        logger.info("\n" + "="*80)
        logger.info("BUILD COMPLETE!")
        logger.info("="*80)
        logger.info(f"Total time: {elapsed}")
        logger.info(f"Benchmarks completed: {len(self.stats['benchmarks_completed'])}")
        logger.info(f"Errors: {len(self.stats['errors'])}")
        
        logger.info("\nDETAILED Database:")
        for benchmark, count in self.stats['detailed'].items():
            logger.info(f"  {benchmark}: {count:,} questions")
        logger.info(f"  TOTAL: {self.detailed_collection.count():,} questions")
        
        logger.info("\nTOPLINE Database:")
        for benchmark, count in self.stats['topline'].items():
            logger.info(f"  {benchmark}: {count:,} questions")
        logger.info(f"  TOTAL: {self.topline_collection.count():,} questions")
        
        if self.stats['errors']:
            logger.info("\nErrors encountered:")
            for err in self.stats['errors']:
                logger.info(f"  {err['benchmark']}: {err['error']}")
        
        logger.info("="*80)


def main():
    """Main entry point."""
    
    # Initialize builder
    builder = MassiveVectorDBBuilder(
        detailed_db_path=Path("./data/vector_db_detailed"),
        topline_db_path=Path("./data/vector_db_topline"),
        embedding_model="all-MiniLM-L6-v2"
    )
    
    # Build everything
    builder.build_all(
        top_k_models=5,      # Use top 5 models per benchmark
        verify_every_n=3     # Verify every 3 benchmarks
    )
    
    logger.info("\n🎉 All done! Both databases are ready to use.")


if __name__ == "__main__":
    main()
