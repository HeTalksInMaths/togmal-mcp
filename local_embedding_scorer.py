#!/usr/bin/env python3
"""
Local Semantic Similarity Scorer (No Network Required)
========================================================

Uses local TF-IDF embeddings converted to dense vectors for semantic similarity:
- No external model downloads needed
- Works offline with network restrictions
- Fast indexing and search with FAISS
- Can be upgraded to sentence transformers later when models are available
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalSemanticScorer:
    """Semantic similarity using local TF-IDF + LSA embeddings"""

    def __init__(
        self,
        questions: List[Dict],
        embedding_dim: int = 384,  # Match sentence-transformers dimension
        max_features: int = 10000,
        domain_boost: float = 0.2
    ):
        """
        Args:
            questions: List of question dicts
            embedding_dim: Embedding dimension (reduced via LSA)
            max_features: TF-IDF vocabulary size
            domain_boost: Score boost for same domain
        """
        self.questions = questions
        self.questions_by_id = {q['question_id']: q for q in questions}
        self.domain_boost = domain_boost
        self.embedding_dim = embedding_dim

        logger.info(f"Building local semantic embeddings (dim={embedding_dim})...")

        # Build TF-IDF vectors
        texts = [q['question_text'] for q in questions]
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            stop_words='english',
            min_df=2
        )
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        logger.info(f"  TF-IDF matrix: {tfidf_matrix.shape}")

        # Reduce dimensionality with LSA (Latent Semantic Analysis)
        # This captures semantic relationships between words
        n_components = min(embedding_dim, tfidf_matrix.shape[1] - 1)
        self.lsa = TruncatedSVD(n_components=n_components, random_state=42)
        embeddings = self.lsa.fit_transform(tfidf_matrix)

        # Normalize to unit vectors (for cosine similarity)
        self.embeddings = normalize(embeddings, norm='l2', axis=1)

        logger.info(f"  LSA embeddings: {self.embeddings.shape}")
        logger.info(f"  Explained variance: {self.lsa.explained_variance_ratio_.sum():.2%}")

        # Build FAISS index for fast similarity search
        try:
            import faiss
            self.use_faiss = True

            # Create FAISS index
            self.index = faiss.IndexFlatIP(self.embeddings.shape[1])  # Inner product (cosine)
            self.index.add(self.embeddings.astype('float32'))
            logger.info(f"✅ FAISS index ready with {len(questions):,} vectors")

        except ImportError:
            self.use_faiss = False
            logger.warning("FAISS not available, using numpy (slower)")
            logger.info(f"✅ Embeddings ready with {len(questions):,} vectors")

    def _embed_query(self, query: str) -> np.ndarray:
        """Embed query text using TF-IDF + LSA"""
        query_tfidf = self.vectorizer.transform([query])
        query_emb = self.lsa.transform(query_tfidf)
        query_emb = normalize(query_emb, norm='l2', axis=1)
        return query_emb[0]

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
        # Embed query
        query_emb = self._embed_query(query)

        if self.use_faiss:
            # FAISS search
            scores, indices = self.index.search(
                query_emb.reshape(1, -1).astype('float32'),
                min(top_k * 3, len(self.questions))
            )
            scores = scores[0]
            indices = indices[0]
        else:
            # Numpy search (slower)
            scores = self.embeddings @ query_emb
            indices = np.argsort(scores)[::-1][:min(top_k * 3, len(self.questions))]
            scores = scores[indices]

        # Apply domain boosting if provided
        if query_domain and self.domain_boost > 0:
            boosted_scores = []
            for i, idx in enumerate(indices):
                score = scores[i]
                q = self.questions[idx]
                if q['domain'] == query_domain:
                    score = score * (1 + self.domain_boost)
                boosted_scores.append(score)
            scores = np.array(boosted_scores)

            # Re-sort after boosting
            sorted_indices = np.argsort(scores)[::-1][:top_k]
            indices = indices[sorted_indices]
            scores = scores[sorted_indices]
        else:
            indices = indices[:top_k]
            scores = scores[:top_k]

        # Build results
        results = []
        for idx, score in zip(indices, scores):
            results.append({
                'question_id': self.questions[idx]['question_id'],
                'score': float(score),
                'question': self.questions[idx]
            })

        return results


def tune_local_semantic_scorer():
    """Tune local semantic similarity scorer"""
    from evaluate_similarity_scorer import SimilarityScorerEvaluator
    from smart_hyperparameter_search import SmartHyperparameterSearch, HyperparameterSpace

    logger.info("\n" + "="*80)
    logger.info("TUNING: Local Semantic Similarity Scorer")
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
        scorer = LocalSemanticScorer(
            questions=questions,
            embedding_dim=int(params['embedding_dim']),
            max_features=int(params['max_features']),
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

    # Define search space
    param_space = [
        HyperparameterSpace('embedding_dim', 128, 512, 'uniform'),
        HyperparameterSpace('max_features', 5000, 15000, 'log-uniform'),
        HyperparameterSpace('domain_boost', 0.0, 0.5, 'uniform'),
    ]

    # Run optimization
    logger.info("\nStarting Bayesian optimization...")
    optimizer = SmartHyperparameterSearch(
        objective_function=objective,
        param_space=param_space,
        n_calls=20,  # 20 evaluations
        n_random_starts=8
    )

    result = optimizer.optimize()

    # Evaluate best model on full sample
    logger.info("\n" + "="*80)
    logger.info("FINAL EVALUATION ON FULL SAMPLE")
    logger.info("="*80)

    best_params = result['best_params']
    logger.info("\nBest hyperparameters:")
    logger.info(f"  embedding_dim: {int(best_params['embedding_dim'])}")
    logger.info(f"  max_features: {int(best_params['max_features'])}")
    logger.info(f"  domain_boost: {best_params['domain_boost']:.3f}")

    best_scorer = LocalSemanticScorer(
        questions=questions,
        embedding_dim=int(best_params['embedding_dim']),
        max_features=int(best_params['max_features']),
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
    logger.info("COMPARISON: BM25 vs Local Semantic (TF-IDF+LSA)")
    logger.info("="*80)

    # Load BM25 results
    bm25_path = Path("./tuning_results_similarity.json")
    with open(bm25_path, 'r') as f:
        bm25_data = json.load(f)

    bm25_metrics = bm25_data['final_metrics']

    logger.info(f"\n{'Metric':<25} {'BM25':<20} {'Semantic (LSA)':<20} {'Improvement':<15}")
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
            'method': 'TF-IDF + LSA (local)',
            'best_params': {
                'embedding_dim': int(best_params['embedding_dim']),
                'max_features': int(best_params['max_features']),
                'domain_boost': best_params['domain_boost']
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
    print("Local Semantic Similarity Scorer (TF-IDF + LSA)")
    print("="*80)

    if len(sys.argv) > 1 and sys.argv[1] == 'tune':
        # Run tuning
        result = tune_local_semantic_scorer()
    else:
        # Quick test
        print("\nQuick test mode (use 'python local_embedding_scorer.py tune' to run full tuning)")

        db_path = Path("./data/unified_database_complete.json")
        with open(db_path, 'r') as f:
            data = json.load(f)

        questions = data['questions'][:1000]  # Small subset for quick test

        # Create semantic scorer
        print("\nTesting Local Semantic Scorer...")
        scorer = LocalSemanticScorer(
            questions=questions,
            embedding_dim=256,
            max_features=8000,
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
