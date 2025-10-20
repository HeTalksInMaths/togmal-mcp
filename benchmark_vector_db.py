#!/usr/bin/env python3
"""
Benchmark Vector Database for Difficulty-Based Prompt Analysis
===============================================================

Uses vector similarity search to assess prompt difficulty by finding
the nearest benchmark questions and computing weighted difficulty scores.

This replaces static clustering with real-time, explainable similarity matching.

Key Innovation:
- Embed all benchmark questions (GPQA, MMLU-Pro, MATH, etc.) with success rates
- For any incoming prompt, find K nearest questions via cosine similarity
- Return weighted difficulty score based on similar questions' success rates

Author: ToGMAL Project
"""

import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check for required dependencies
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not installed. Run: uv pip install sentence-transformers")
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    logger.warning("chromadb not installed. Run: uv pip install chromadb")
    CHROMADB_AVAILABLE = False

try:
    from datasets import load_dataset
    DATASETS_AVAILABLE = True
except ImportError:
    logger.warning("datasets not installed. Run: uv pip install datasets")
    DATASETS_AVAILABLE = False


@dataclass
class BenchmarkQuestion:
    """Represents a single benchmark question with performance metadata"""
    question_id: str
    source_benchmark: str  # GPQA, MMLU-Pro, MATH, etc.
    domain: str  # physics, biology, mathematics, law, etc.
    question_text: str
    correct_answer: str
    choices: Optional[List[str]] = None  # For multiple choice
    
    # Performance metrics
    success_rate: float = None  # Average across models (0.0 to 1.0)
    difficulty_score: float = None  # 1 - success_rate
    
    # Metadata
    difficulty_label: str = None  # Easy, Medium, Hard, Expert
    num_models_tested: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)


class BenchmarkVectorDB:
    """
    Vector database for benchmark questions with difficulty-based retrieval.
    
    Core functionality:
    1. Load benchmark datasets from HuggingFace
    2. Compute embeddings using SentenceTransformer
    3. Store in ChromaDB with metadata (success rates, domains)
    4. Query similar questions and compute weighted difficulty
    """
    
    def __init__(
        self,
        db_path: Path = Path("./data/benchmark_vector_db"),
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "benchmark_questions"
    ):
        """
        Initialize the vector database.
        
        Args:
            db_path: Path to store ChromaDB persistence
            embedding_model: SentenceTransformer model name
            collection_name: Name for the ChromaDB collection
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not CHROMADB_AVAILABLE:
            raise ImportError(
                "Required dependencies not installed. Run:\n"
                "  uv pip install sentence-transformers chromadb datasets"
            )
        
        self.db_path = db_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Initialize ChromaDB
        logger.info(f"Initializing ChromaDB at {db_path}")
        self.client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Benchmark questions with difficulty scores"}
            )
            logger.info(f"Created new collection: {collection_name}")
        
        self.questions: List[BenchmarkQuestion] = []
    
    def load_gpqa_dataset(self, fetch_real_scores: bool = True) -> List[BenchmarkQuestion]:
        """
        Load GPQA Diamond dataset - the hardest benchmark.
        
        GPQA (Graduate-Level Google-Proof Q&A):
        - 448 expert-written questions (198 in Diamond subset)
        - Physics, Biology, Chemistry at graduate level
        - Even PhD holders get ~65% accuracy
        - GPT-4: ~50% success rate
        
        Dataset: Idavidrein/gpqa
        
        Args:
            fetch_real_scores: If True, fetch per-question results from top models
        """
        if not DATASETS_AVAILABLE:
            logger.error("datasets library not available")
            return []
        
        logger.info("Loading GPQA Diamond dataset from HuggingFace...")
        
        questions = []
        
        try:
            # Load GPQA Diamond (hardest subset)
            dataset = load_dataset("Idavidrein/gpqa", "gpqa_diamond")
            
            # Get real success rates from top models if requested
            per_question_scores = {}
            if fetch_real_scores:
                logger.info("Fetching per-question results from top models...")
                per_question_scores = self._fetch_gpqa_model_results()
            
            for idx, item in enumerate(dataset['train']):
                # GPQA has 4 choices: Correct Answer + 3 Incorrect Answers
                choices = [
                    item['Correct Answer'],
                    item['Incorrect Answer 1'],
                    item['Incorrect Answer 2'],
                    item['Incorrect Answer 3']
                ]
                
                question_id = f"gpqa_diamond_{idx}"
                
                # Use real success rate if available, otherwise estimate
                if question_id in per_question_scores:
                    success_rate = per_question_scores[question_id]['success_rate']
                    num_models = per_question_scores[question_id]['num_models']
                else:
                    success_rate = 0.30  # Conservative estimate
                    num_models = 0
                
                difficulty_score = 1.0 - success_rate
                
                # Classify difficulty
                if success_rate < 0.1:
                    difficulty_label = "Nearly_Impossible"
                elif success_rate < 0.3:
                    difficulty_label = "Expert"
                elif success_rate < 0.5:
                    difficulty_label = "Hard"
                else:
                    difficulty_label = "Moderate"
                
                question = BenchmarkQuestion(
                    question_id=question_id,
                    source_benchmark="GPQA_Diamond",
                    domain=item.get('Subdomain', 'unknown').lower(),
                    question_text=item['Question'],
                    correct_answer=item['Correct Answer'],
                    choices=choices,
                    success_rate=success_rate,
                    difficulty_score=difficulty_score,
                    difficulty_label=difficulty_label,
                    num_models_tested=num_models
                )
                
                questions.append(question)
            
            logger.info(f"Loaded {len(questions)} questions from GPQA Diamond")
            if fetch_real_scores and per_question_scores:
                logger.info(f"  Real success rates available for {len(per_question_scores)} questions")
            
        except Exception as e:
            logger.error(f"Failed to load GPQA dataset: {e}")
            logger.info("GPQA may require authentication. Try: huggingface-cli login")
        
        return questions
    
    def _fetch_gpqa_model_results(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch per-question GPQA results from top models on OpenLLM Leaderboard.
        
        Returns:
            Dictionary mapping question_id to {success_rate, num_models}
        """
        # Top models to evaluate (based on OpenLLM Leaderboard v2)
        top_models = [
            "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "mistralai/Mixtral-8x22B-Instruct-v0.1",
        ]
        
        question_results = defaultdict(list)
        
        for model_name in top_models:
            try:
                logger.info(f"  Fetching results for {model_name}...")
                # OpenLLM Leaderboard v2 uses different dataset naming
                dataset_name = f"open-llm-leaderboard/details_{model_name.replace('/', '__')}"
                
                # Try to load GPQA results
                try:
                    results = load_dataset(dataset_name, "harness_gpqa_0", split="latest")
                except:
                    # Try alternative naming
                    logger.warning(f"  Could not find GPQA results for {model_name}")
                    continue
                
                # Process results
                for row in results:
                    question_id = f"gpqa_diamond_{row.get('doc_id', row.get('example', 0))}"
                    predicted = row.get('pred', row.get('prediction', ''))
                    correct = row.get('target', row.get('answer', ''))
                    
                    is_correct = (str(predicted).strip().lower() == str(correct).strip().lower())
                    question_results[question_id].append(is_correct)
                
                logger.info(f"    ✓ Processed {len(results)} questions")
                
            except Exception as e:
                logger.warning(f"  Skipping {model_name}: {e}")
                continue
        
        # Compute success rates
        per_question_scores = {}
        for qid, results in question_results.items():
            if results:
                success_rate = sum(results) / len(results)
                per_question_scores[qid] = {
                    'success_rate': success_rate,
                    'num_models': len(results)
                }
        
        return per_question_scores
    
    def load_mmlu_pro_dataset(self, max_samples: int = 1000) -> List[BenchmarkQuestion]:
        """
        Load MMLU-Pro dataset - advanced multitask knowledge evaluation.
        
        MMLU-Pro improvements over MMLU:
        - 10 choices instead of 4 (reduces guessing)
        - Removed trivial/noisy questions
        - Added harder reasoning problems
        - 12K questions across 14 domains
        
        Dataset: TIGER-Lab/MMLU-Pro
        """
        if not DATASETS_AVAILABLE:
            logger.error("datasets library not available")
            return []
        
        logger.info(f"Loading MMLU-Pro dataset (max {max_samples} samples)...")
        
        questions = []
        
        try:
            # Load MMLU-Pro validation set
            dataset = load_dataset("TIGER-Lab/MMLU-Pro", split="validation")
            
            # Sample to avoid overwhelming the DB initially
            if len(dataset) > max_samples:
                dataset = dataset.shuffle(seed=42).select(range(max_samples))
            
            for idx, item in enumerate(dataset):
                question = BenchmarkQuestion(
                    question_id=f"mmlu_pro_{idx}",
                    source_benchmark="MMLU_Pro",
                    domain=item.get('category', 'unknown').lower(),
                    question_text=item['question'],
                    correct_answer=item['answer'],
                    choices=item.get('options', []),
                    # MMLU-Pro is hard - estimate ~45% average success
                    success_rate=0.45,
                    difficulty_score=0.55,
                    difficulty_label="Hard",
                    num_models_tested=0
                )
                
                questions.append(question)
            
            logger.info(f"Loaded {len(questions)} questions from MMLU-Pro")
            
        except Exception as e:
            logger.error(f"Failed to load MMLU-Pro dataset: {e}")
        
        return questions
    
    def load_math_dataset(self, max_samples: int = 500) -> List[BenchmarkQuestion]:
        """
        Load MATH (competition mathematics) dataset.
        
        MATH dataset:
        - 12,500 competition-level math problems
        - Requires multi-step reasoning
        - Free-form answers with LaTeX
        - GPT-4: ~50% success rate
        
        Dataset: hendrycks/competition_math
        """
        if not DATASETS_AVAILABLE:
            logger.error("datasets library not available")
            return []
        
        logger.info(f"Loading MATH dataset (max {max_samples} samples)...")
        
        questions = []
        
        try:
            # Load MATH test set
            dataset = load_dataset("hendrycks/competition_math", split="test")
            
            # Sample to manage size
            if len(dataset) > max_samples:
                dataset = dataset.shuffle(seed=42).select(range(max_samples))
            
            for idx, item in enumerate(dataset):
                question = BenchmarkQuestion(
                    question_id=f"math_{idx}",
                    source_benchmark="MATH",
                    domain=item.get('type', 'mathematics').lower(),
                    question_text=item['problem'],
                    correct_answer=item['solution'],
                    choices=None,  # Free-form answer
                    # MATH is very hard - estimate ~35% average success
                    success_rate=0.35,
                    difficulty_score=0.65,
                    difficulty_label="Expert",
                    num_models_tested=0
                )
                
                questions.append(question)
            
            logger.info(f"Loaded {len(questions)} questions from MATH")
            
        except Exception as e:
            logger.error(f"Failed to load MATH dataset: {e}")
        
        return questions
    
    def index_questions(self, questions: List[BenchmarkQuestion]):
        """
        Index questions into the vector database.
        
        Steps:
        1. Generate embeddings for all questions
        2. Store in ChromaDB with metadata
        3. Save questions list for reference
        """
        if not questions:
            logger.warning("No questions to index")
            return
        
        logger.info(f"Indexing {len(questions)} questions into vector database...")
        
        # Generate embeddings
        question_texts = [q.question_text for q in questions]
        logger.info("Generating embeddings (this may take a few minutes)...")
        embeddings = self.embedding_model.encode(
            question_texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Prepare metadata
        metadatas = []
        ids = []
        
        for q in questions:
            metadatas.append({
                "source": q.source_benchmark,
                "domain": q.domain,
                "success_rate": q.success_rate,
                "difficulty_score": q.difficulty_score,
                "difficulty_label": q.difficulty_label,
                "num_models": q.num_models_tested
            })
            ids.append(q.question_id)
        
        # Add to ChromaDB in batches (ChromaDB has batch size limits)
        batch_size = 1000
        for i in range(0, len(questions), batch_size):
            end_idx = min(i + batch_size, len(questions))
            
            self.collection.add(
                embeddings=embeddings[i:end_idx].tolist(),
                metadatas=metadatas[i:end_idx],
                documents=question_texts[i:end_idx],
                ids=ids[i:end_idx]
            )
            
            logger.info(f"Indexed batch {i//batch_size + 1} ({end_idx}/{len(questions)})")
        
        # Save questions for reference
        self.questions.extend(questions)
        
        logger.info(f"Successfully indexed {len(questions)} questions")
    
    def query_similar_questions(
        self,
        prompt: str,
        k: int = 5,
        domain_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find k most similar benchmark questions to the given prompt.
        
        Args:
            prompt: The user's prompt/question
            k: Number of similar questions to retrieve
            domain_filter: Optional domain to filter by (e.g., "physics")
        
        Returns:
            Dictionary with:
            - similar_questions: List of similar questions with metadata
            - weighted_difficulty: Difficulty score weighted by similarity
            - avg_success_rate: Average success rate of similar questions
            - risk_level: LOW, MODERATE, HIGH, CRITICAL
            - explanation: Human-readable explanation
        """
        logger.info(f"Querying similar questions for prompt: {prompt[:100]}...")
        
        # Generate embedding for the prompt
        prompt_embedding = self.embedding_model.encode([prompt], convert_to_numpy=True)
        
        # Build where clause for domain filtering
        where_clause = None
        if domain_filter:
            where_clause = {"domain": domain_filter}
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=prompt_embedding.tolist(),
            n_results=k,
            where=where_clause
        )
        
        # Extract results
        similar_questions = []
        similarities = []
        difficulty_scores = []
        success_rates = []
        
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            
            # Convert L2 distance to cosine similarity approximation
            # For normalized embeddings: similarity ≈ 1 - (distance²/2)
            similarity = max(0, 1 - (distance ** 2) / 2)
            
            similar_questions.append({
                "question_id": results['ids'][0][i],
                "question_text": results['documents'][0][i][:200] + "...",  # Truncate
                "source": metadata['source'],
                "domain": metadata['domain'],
                "success_rate": metadata['success_rate'],
                "difficulty_score": metadata['difficulty_score'],
                "similarity": round(similarity, 3)
            })
            
            similarities.append(similarity)
            difficulty_scores.append(metadata['difficulty_score'])
            success_rates.append(metadata['success_rate'])
        
        # Compute weighted difficulty (weighted by similarity)
        total_weight = sum(similarities)
        if total_weight > 0:
            weighted_difficulty = sum(
                diff * sim for diff, sim in zip(difficulty_scores, similarities)
            ) / total_weight
            
            weighted_success_rate = sum(
                sr * sim for sr, sim in zip(success_rates, similarities)
            ) / total_weight
        else:
            weighted_difficulty = np.mean(difficulty_scores)
            weighted_success_rate = np.mean(success_rates)
        
        # Determine risk level
        if weighted_success_rate < 0.1:
            risk_level = "CRITICAL"
            explanation = "Nearly impossible - similar to questions with <10% success rate"
        elif weighted_success_rate < 0.3:
            risk_level = "HIGH"
            explanation = "Very hard - similar to questions with <30% success rate"
        elif weighted_success_rate < 0.5:
            risk_level = "MODERATE"
            explanation = "Hard - similar to questions with <50% success rate"
        elif weighted_success_rate < 0.7:
            risk_level = "LOW"
            explanation = "Moderate difficulty - within typical LLM capability"
        else:
            risk_level = "MINIMAL"
            explanation = "Easy - LLMs typically handle this well"
        
        return {
            "similar_questions": similar_questions,
            "weighted_difficulty_score": round(weighted_difficulty, 3),
            "weighted_success_rate": round(weighted_success_rate, 3),
            "avg_similarity": round(np.mean(similarities), 3),
            "risk_level": risk_level,
            "explanation": explanation,
            "recommendation": self._get_recommendation(risk_level, weighted_success_rate)
        }
    
    def _get_recommendation(self, risk_level: str, success_rate: float) -> str:
        """Generate recommendation based on difficulty assessment"""
        if risk_level == "CRITICAL":
            return "Recommend: Break into smaller steps, use external tools, or human-in-the-loop"
        elif risk_level == "HIGH":
            return "Recommend: Multi-step reasoning with verification, consider using web search"
        elif risk_level == "MODERATE":
            return "Recommend: Use chain-of-thought prompting for better accuracy"
        else:
            return "Recommend: Standard LLM response should be adequate"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the indexed benchmark questions"""
        count = self.collection.count()
        
        if count == 0:
            return {"total_questions": 0, "message": "No questions indexed yet"}
        
        # Get ALL questions for accurate stats (not just sample of 1000)
        logger.info(f"Computing statistics from all {count} questions...")
        sample = self.collection.get(limit=count, include=["metadatas"])
        
        domains = defaultdict(int)
        sources = defaultdict(int)
        difficulty_levels = defaultdict(int)
        
        for metadata in sample['metadatas']:
            domains[metadata['domain']] += 1
            sources[metadata['source']] += 1
            difficulty_levels[metadata['difficulty_label']] += 1
        
        return {
            "total_questions": count,
            "domains": dict(domains),
            "sources": dict(sources),
            "difficulty_levels": dict(difficulty_levels)
        }
    
    def build_database(
        self,
        load_gpqa: bool = True,
        load_mmlu_pro: bool = True,
        load_math: bool = True,
        max_samples_per_dataset: int = 1000
    ):
        """
        Build the complete vector database from benchmark datasets.
        
        Args:
            load_gpqa: Load GPQA Diamond (hardest)
            load_mmlu_pro: Load MMLU-Pro (hard, broad coverage)
            load_math: Load MATH (hard, math-focused)
            max_samples_per_dataset: Max samples per dataset to manage size
        """
        logger.info("="*80)
        logger.info("Building Benchmark Vector Database")
        logger.info("="*80)
        
        all_questions = []
        
        # Load datasets
        if load_gpqa:
            gpqa_questions = self.load_gpqa_dataset()
            all_questions.extend(gpqa_questions)
        
        if load_mmlu_pro:
            mmlu_questions = self.load_mmlu_pro_dataset(max_samples=max_samples_per_dataset)
            all_questions.extend(mmlu_questions)
        
        if load_math:
            math_questions = self.load_math_dataset(max_samples=max_samples_per_dataset // 2)
            all_questions.extend(math_questions)
        
        # Index all questions
        if all_questions:
            self.index_questions(all_questions)
        
        # Print statistics
        stats = self.get_statistics()
        logger.info("\nDatabase Statistics:")
        logger.info(f"  Total Questions: {stats['total_questions']}")
        logger.info(f"  Sources: {stats.get('sources', {})}")
        logger.info(f"  Domains: {stats.get('domains', {})}")
        
        logger.info("="*80)
        logger.info("Database build complete!")
        logger.info("="*80)


def main():
    """Main entry point for building the vector database"""
    
    # Initialize database
    db = BenchmarkVectorDB(
        db_path=Path("/Users/hetalksinmaths/togmal/data/benchmark_vector_db"),
        embedding_model="all-MiniLM-L6-v2"
    )
    
    # Build database with hardest benchmarks
    db.build_database(
        load_gpqa=True,  # Start with hardest
        load_mmlu_pro=True,
        load_math=True,
        max_samples_per_dataset=1000
    )
    
    # Test query
    print("\n" + "="*80)
    print("Testing with example prompts:")
    print("="*80)
    
    test_prompts = [
        "Calculate the quantum correction to the partition function for a 3D harmonic oscillator",
        "What is the capital of France?",
        "Prove that the square root of 2 is irrational"
    ]
    
    for prompt in test_prompts:
        print(f"\nPrompt: {prompt}")
        result = db.query_similar_questions(prompt, k=3)
        print(f"  Risk Level: {result['risk_level']}")
        print(f"  Weighted Success Rate: {result['weighted_success_rate']:.1%}")
        print(f"  Explanation: {result['explanation']}")
        print(f"  Recommendation: {result['recommendation']}")


if __name__ == "__main__":
    main()
