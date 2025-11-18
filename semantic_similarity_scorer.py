#!/usr/bin/env python3
"""
Semantic Similarity Scorer using ChromaDB
==========================================

Uses sentence embeddings for semantic similarity matching:
- Sentence transformers for embedding generation
- ChromaDB for fast vector similarity search
- Domain-aware boosting for coherence
- Hybrid mode combining BM25 + semantic similarity

This should significantly outperform pure BM25 keyword matching.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

logging.basicConfig(level=logging.INFO)
logging.getLogger('chromadb').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class SemanticSimilarityScorer:
    """Semantic similarity scorer using ChromaDB with local embeddings"""

    def __init__(
        self,
        questions: List[Dict],
        model_name: str = "all-MiniLM-L6-v2",
        domain_boost: float = 0.2,
        use_local_model: bool = True
    ):
        """
        Args:
            questions: List of question dicts
            model_name: Sentence transformer model name (default: all-MiniLM-L6-v2)
            domain_boost: Score boost for same domain (0-1)
            use_local_model: Use local embedding function to avoid network calls
        """
        import chromadb
        from chromadb.config import Settings

        self.questions = questions
        self.questions_by_id = {q['question_id']: q for q in questions}
        self.domain_boost = domain_boost
        self.model_name = model_name

        # Create ChromaDB client with local persistence
        self.client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            allow_reset=True
        ))

        # Try to use local sentence transformers if available
        try:
            if use_local_model:
                from chromadb.utils import embedding_functions
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=model_name
                )
                logger.info(f"✅ Using local sentence transformer: {model_name}")
            else:
                self.embedding_function = None
                logger.info("Using ChromaDB default embeddings")
        except Exception as e:
            logger.warning(f"Could not load sentence transformer: {e}")
            logger.info("Falling back to ChromaDB default embeddings")
            self.embedding_function = None

        # Create or get collection
        try:
            self.client.delete_collection("questions")
        except:
            pass

        if self.embedding_function:
            self.collection = self.client.create_collection(
                name="questions",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        else:
            self.collection = self.client.create_collection(
                name="questions",
                metadata={"hnsw:space": "cosine"}
            )

        # Index all questions
        self._index_questions()

    def _index_questions(self):
        """Index all questions in ChromaDB"""
        logger.info(f"Indexing {len(self.questions):,} questions...")

        # Batch processing for efficiency
        batch_size = 1000
        for i in range(0, len(self.questions), batch_size):
            batch = self.questions[i:i + batch_size]

            ids = [q['question_id'] for q in batch]
            documents = [q['question_text'] for q in batch]
            metadatas = [{
                'domain': q['domain'],
                'difficulty': float(q['difficulty_score'])
            } for q in batch]

            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            if (i + batch_size) % 5000 == 0:
                logger.info(f"  Indexed {i + batch_size:,} questions...")

        logger.info(f"✅ Indexed {len(self.questions):,} questions in ChromaDB")

    def search(
        self,
        query: str,
        top_k: int = 10,
        query_domain: Optional[str] = None
    ) -> List[Dict]:
        """Search for similar questions using semantic similarity

        Args:
            query: Query text
            top_k: Number of results to return
            query_domain: Domain of query (for domain boosting)

        Returns:
            List of dicts with question_id, score, question
        """
        # Query ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k * 3, 50)  # Get more results for re-ranking
        )

        # Extract results
        ids = results['ids'][0]
        distances = results['distances'][0]

        # Convert distances to similarity scores (ChromaDB returns distances)
        # For cosine distance: similarity = 1 - distance
        scores = [1 - d for d in distances]

        # Apply domain boosting if provided
        if query_domain and self.domain_boost > 0:
            boosted_scores = []
            for i, qid in enumerate(ids):
                score = scores[i]
                q = self.questions_by_id.get(qid)
                if q and q['domain'] == query_domain:
                    score = score * (1 + self.domain_boost)  # Relative boost
                boosted_scores.append(score)
            scores = boosted_scores

        # Sort by boosted scores
        sorted_indices = np.argsort(scores)[::-1][:top_k]

        # Build results
        final_results = []
        for idx in sorted_indices:
            qid = ids[idx]
            if qid in self.questions_by_id:
                final_results.append({
                    'question_id': qid,
                    'score': float(scores[idx]),
                    'question': self.questions_by_id[qid]
                })

        return final_results


class HybridSimilarityScorer:
    """Hybrid scorer combining BM25 + semantic embeddings"""

    def __init__(
        self,
        questions: List[Dict],
        bm25_weight: float = 0.3,
        semantic_weight: float = 0.7,
        domain_boost: float = 0.2,
        **bm25_kwargs
    ):
        """
        Args:
            questions: List of question dicts
            bm25_weight: Weight for BM25 scores (0-1)
            semantic_weight: Weight for semantic scores (0-1)
            domain_boost: Domain boost for both scorers
            **bm25_kwargs: Additional kwargs for BM25 scorer
        """
        from tunable_similarity_scorer import TunableBM25Scorer

        self.questions = questions
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight

        # Load best BM25 params from tuning
        results_path = Path("./tuning_results_similarity.json")
        if results_path.exists():
            with open(results_path, 'r') as f:
                tuning_results = json.load(f)
            best_params = tuning_results['best_params']
            logger.info("Using tuned BM25 parameters")
        else:
            best_params = {
                'k1': 1.5,
                'b': 0.75,
                'max_features': 2000,
                'max_ngram': 2,
                'domain_boost': domain_boost
            }
            logger.info("Using default BM25 parameters")

        # Create BM25 scorer
        self.bm25_scorer = TunableBM25Scorer(
            questions=questions,
            k1=best_params['k1'],
            b=best_params['b'],
            max_features=int(best_params['max_features']),
            ngram_range=(1, int(best_params['max_ngram'])),
            domain_boost=0  # We'll handle domain boost ourselves
        )

        # Create semantic scorer
        self.semantic_scorer = SemanticSimilarityScorer(
            questions=questions,
            domain_boost=0  # We'll handle domain boost ourselves
        )

        self.domain_boost = domain_boost
        logger.info(f"✅ Hybrid scorer ready (BM25: {bm25_weight:.0%}, Semantic: {semantic_weight:.0%})")

    def search(
        self,
        query: str,
        top_k: int = 10,
        query_domain: Optional[str] = None
    ) -> List[Dict]:
        """Search using hybrid BM25 + semantic similarity"""

        # Get results from both scorers
        bm25_results = self.bm25_scorer.search(query, top_k=top_k * 2)
        semantic_results = self.semantic_scorer.search(query, top_k=top_k * 2)

        # Normalize scores to [0, 1]
        bm25_scores = {r['question_id']: r['score'] for r in bm25_results}
        semantic_scores = {r['question_id']: r['score'] for r in semantic_results}

        # Normalize BM25 scores
        if bm25_scores:
            max_bm25 = max(bm25_scores.values())
            if max_bm25 > 0:
                bm25_scores = {qid: score / max_bm25 for qid, score in bm25_scores.items()}

        # Semantic scores are already normalized (cosine similarity)

        # Combine scores
        all_qids = set(bm25_scores.keys()) | set(semantic_scores.keys())
        hybrid_scores = {}

        for qid in all_qids:
            bm25_score = bm25_scores.get(qid, 0)
            semantic_score = semantic_scores.get(qid, 0)

            # Weighted combination
            combined_score = (
                self.bm25_weight * bm25_score +
                self.semantic_weight * semantic_score
            )

            # Apply domain boosting
            if query_domain and self.domain_boost > 0:
                q = self.bm25_scorer.questions_by_id.get(qid)
                if q and q['domain'] == query_domain:
                    combined_score *= (1 + self.domain_boost)

            hybrid_scores[qid] = combined_score

        # Get top-K
        sorted_qids = sorted(hybrid_scores.keys(), key=lambda x: hybrid_scores[x], reverse=True)[:top_k]

        results = []
        for qid in sorted_qids:
            results.append({
                'question_id': qid,
                'score': hybrid_scores[qid],
                'question': self.bm25_scorer.questions_by_id[qid]
            })

        return results


def tune_semantic_scorer():
    """Tune semantic similarity scorer"""
    from evaluate_similarity_scorer import SimilarityScorerEvaluator
    from smart_hyperparameter_search import SmartHyperparameterSearch, HyperparameterSpace

    logger.info("\n" + "="*80)
    logger.info("TUNING: Semantic Similarity Scorer")
    logger.info("="*80)

    # Load questions
    db_path = Path("./data/unified_database_complete.json")
    with open(db_path, 'r') as f:
        data = json.load(f)

    questions = data['questions']

    # Create evaluator
    evaluator = SimilarityScorerEvaluator(questions)

    # Define objective function
    def objective(params):
        """Evaluate semantic scorer with given hyperparameters"""

        # Create scorer with these params
        scorer = SemanticSimilarityScorer(
            questions=questions,
            domain_boost=params['domain_boost']
        )

        # Evaluate (use smaller sample for speed)
        metrics = evaluator.evaluate_retrieval_quality(
            scorer,
            k_values=[1, 3, 5, 10],
            sample_size=300  # Smaller sample for faster tuning
        )

        # Objective: Maximize weighted combination of metrics
        score = (
            0.5 * metrics['precision@k'][10] +      # Precision@10
            0.2 * metrics['ndcg@k'][10] +           # nDCG@10
            0.2 * metrics['domain_coherence'] +     # Domain coherence
            0.1 * metrics['mrr']                    # MRR
        )

        return score

    # Define search space (much simpler than BM25)
    param_space = [
        HyperparameterSpace('domain_boost', 0.0, 0.5, 'uniform'),
    ]

    # Run optimization
    logger.info("\nStarting optimization...")
    optimizer = SmartHyperparameterSearch(
        objective_function=objective,
        param_space=param_space,
        n_calls=10,  # Fewer calls needed (only 1 param)
        n_random_starts=5
    )

    result = optimizer.optimize()

    # Evaluate best model on full sample
    logger.info("\n" + "="*80)
    logger.info("FINAL EVALUATION ON FULL SAMPLE")
    logger.info("="*80)

    best_params = result['best_params']
    logger.info(f"\nBest domain_boost: {best_params['domain_boost']:.3f}")

    best_scorer = SemanticSimilarityScorer(
        questions=questions,
        domain_boost=best_params['domain_boost']
    )

    # Full evaluation
    final_metrics = evaluator.evaluate_retrieval_quality(
        best_scorer,
        k_values=[1, 3, 5, 10],
        sample_size=500  # Full sample
    )

    # Compare with BM25
    logger.info("\n" + "="*80)
    logger.info("COMPARISON: BM25 vs Semantic")
    logger.info("="*80)

    # Load BM25 results
    bm25_path = Path("./tuning_results_similarity.json")
    with open(bm25_path, 'r') as f:
        bm25_data = json.load(f)

    bm25_metrics = bm25_data['final_metrics']

    logger.info(f"\n{'Metric':<25} {'BM25':<20} {'Semantic':<20} {'Improvement':<15}")
    logger.info("-" * 80)

    for k in [1, 3, 5, 10]:
        bm25_p = bm25_metrics[f'precision@{k}']
        semantic_p = final_metrics['precision@k'][k]
        improvement = ((semantic_p - bm25_p) / bm25_p * 100) if bm25_p > 0 else 0
        logger.info(f"{'Precision@' + str(k):<25} {bm25_p:<20.3f} {semantic_p:<20.3f} {improvement:>+13.1f}%")

    logger.info("")
    bm25_mrr = bm25_metrics['mrr']
    semantic_mrr = final_metrics['mrr']
    improvement = ((semantic_mrr - bm25_mrr) / bm25_mrr * 100) if bm25_mrr > 0 else 0
    logger.info(f"{'MRR':<25} {bm25_mrr:<20.3f} {semantic_mrr:<20.3f} {improvement:>+13.1f}%")

    logger.info("")
    bm25_dc = bm25_metrics['domain_coherence']
    semantic_dc = final_metrics['domain_coherence']
    improvement = ((semantic_dc - bm25_dc) / bm25_dc * 100) if bm25_dc > 0 else 0
    logger.info(f"{'Domain Coherence':<25} {bm25_dc:<20.3f} {semantic_dc:<20.3f} {improvement:>+13.1f}%")

    # Save results
    results_path = Path("./tuning_results_semantic.json")
    with open(results_path, 'w') as f:
        json.dump({
            'best_params': {
                'domain_boost': best_params['domain_boost'],
                'model_name': 'all-MiniLM-L6-v2'
            },
            'validation_score': result['best_score'],
            'final_metrics': {
                'precision@1': final_metrics['precision@k'][1],
                'precision@3': final_metrics['precision@k'][3],
                'precision@5': final_metrics['precision@k'][5],
                'precision@10': final_metrics['precision@k'][10],
                'mrr': final_metrics['mrr'],
                'domain_coherence': final_metrics['domain_coherence'],
                'difficulty_coherence': final_metrics['difficulty_coherence']
            },
            'bm25_comparison': {
                'precision@1': bm25_metrics['precision@1'],
                'precision@10': bm25_metrics['precision@10'],
                'mrr': bm25_metrics['mrr'],
                'domain_coherence': bm25_metrics['domain_coherence']
            },
            'n_evaluations': result['n_evaluations']
        }, f, indent=2)

    logger.info(f"\n✅ Results saved to {results_path}")

    return result


if __name__ == "__main__":
    import sys

    print("\n" + "="*80)
    print("Semantic Similarity Scorer")
    print("="*80)

    if len(sys.argv) > 1 and sys.argv[1] == 'tune':
        # Run tuning
        result = tune_semantic_scorer()
    else:
        # Quick test
        print("\nQuick test mode (use 'python semantic_similarity_scorer.py tune' to run full tuning)")

        db_path = Path("./data/unified_database_complete.json")
        with open(db_path, 'r') as f:
            data = json.load(f)

        questions = data['questions'][:1000]  # Small subset for quick test

        # Create semantic scorer
        print("\n1. Testing Semantic Scorer...")
        scorer = SemanticSimilarityScorer(
            questions=questions,
            domain_boost=0.2
        )

        # Test query
        test_query = "Calculate the eigenvalues of a matrix"
        results = scorer.search(test_query, top_k=5, query_domain="Linear Algebra")

        print(f"\nTest query: '{test_query}'")
        print("\nTop 5 semantic results:")
        for i, r in enumerate(results, 1):
            print(f"\n{i}. Score: {r['score']:.3f}")
            print(f"   {r['question']['question_text'][:100]}...")
            print(f"   Domain: {r['question']['domain']}, Difficulty: {r['question']['difficulty_score']:.2f}")

        print("\n" + "="*80)
        print("✅ Quick test complete!")
        print("="*80)
