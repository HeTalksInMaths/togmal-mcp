#!/usr/bin/env python3
"""
Tunable BM25 Similarity Scorer
==============================

BM25 with tunable hyperparameters:
- k1: Term saturation parameter (0.5-3.0)
- b: Length normalization (0.0-1.0)
- max_features: Vocabulary size (500-10000)
- ngram_range: Unigrams, bigrams, or both
- domain_boost: Boost score if same domain (0.0-0.5)
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logging.getLogger('sklearn').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class TunableBM25Scorer:
    """BM25 similarity scorer with tunable hyperparameters"""

    def __init__(
        self,
        questions: List[Dict],
        k1: float = 1.5,
        b: float = 0.75,
        max_features: int = 2000,
        ngram_range: tuple = (1, 2),
        domain_boost: float = 0.2,
        stop_words: str = 'english'
    ):
        """
        Args:
            questions: List of question dicts
            k1: BM25 term saturation parameter (higher = less saturation)
            b: BM25 length normalization (0 = no normalization, 1 = full)
            max_features: Maximum vocabulary size
            ngram_range: (min_n, max_n) for n-grams
            domain_boost: Score boost for same domain (0-1)
            stop_words: Stop words to remove ('english' or None)
        """
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.questions = questions
        self.questions_by_id = {q['question_id']: q for q in questions}

        # Store hyperparameters
        self.k1 = k1
        self.b = b
        self.domain_boost = domain_boost

        # Build TF-IDF vectorizer
        texts = [q['question_text'] for q in questions]
        self.vectorizer = TfidfVectorizer(
            max_features=int(max_features),
            ngram_range=ngram_range,
            stop_words=stop_words,
            norm=None,  # We'll do BM25 normalization ourselves
            use_idf=False,  # We'll compute IDF for BM25
            sublinear_tf=False
        )

        # Fit and get term frequencies
        self.tf_matrix = self.vectorizer.fit_transform(texts)

        # Compute IDF for BM25
        N = len(texts)
        df = np.bincount(self.tf_matrix.nonzero()[1], minlength=self.tf_matrix.shape[1])
        self.idf = np.log((N - df + 0.5) / (df + 0.5) + 1.0)

        # Document lengths for normalization
        self.doc_lengths = np.array(self.tf_matrix.sum(axis=1)).flatten()
        self.avg_doc_length = np.mean(self.doc_lengths)

        # Pre-compute BM25 scores for all documents
        self.bm25_matrix = self._compute_bm25_matrix()

        logger.info(f"✅ Built BM25 scorer (k1={k1:.2f}, b={b:.2f}, vocab={max_features})")

    def _compute_bm25_matrix(self):
        """Pre-compute BM25 scores for all documents"""
        # Convert to dense for easier manipulation
        tf_dense = self.tf_matrix.toarray()

        # BM25 formula: IDF * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / avgdl)))
        bm25_scores = np.zeros_like(tf_dense, dtype=float)

        for i in range(len(tf_dense)):
            doc_len = self.doc_lengths[i]
            norm_factor = 1 - self.b + self.b * (doc_len / self.avg_doc_length)

            for j in range(tf_dense.shape[1]):
                tf = tf_dense[i, j]
                if tf > 0:
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * norm_factor
                    bm25_scores[i, j] = self.idf[j] * (numerator / denominator)

        return bm25_scores

    def search(self, query: str, top_k: int = 10, query_domain: Optional[str] = None) -> List[Dict]:
        """Search for similar questions using BM25

        Args:
            query: Query text
            top_k: Number of results to return
            query_domain: Domain of query (for domain boosting)

        Returns:
            List of dicts with question_id, score, question
        """
        # Vectorize query
        query_tf = self.vectorizer.transform([query]).toarray()[0]

        # Compute BM25 score for query
        query_bm25 = np.zeros(len(query_tf))
        for j in range(len(query_tf)):
            if query_tf[j] > 0:
                # For query, we don't do length normalization
                numerator = query_tf[j] * (self.k1 + 1)
                denominator = query_tf[j] + self.k1
                query_bm25[j] = self.idf[j] * (numerator / denominator)

        # Compute similarities (dot product)
        scores = self.bm25_matrix @ query_bm25

        # Apply domain boosting if provided
        if query_domain and self.domain_boost > 0:
            for i, q in enumerate(self.questions):
                if q['domain'] == query_domain:
                    scores[i] += self.domain_boost * scores[i]  # Relative boost

        # Get top-K
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append({
                'question_id': self.questions[idx]['question_id'],
                'score': float(scores[idx]),
                'question': self.questions[idx]
            })

        return results


def tune_similarity_scorer():
    """Tune BM25 similarity scorer with Bayesian optimization"""

    from evaluate_similarity_scorer import SimilarityScorerEvaluator
    from smart_hyperparameter_search import SmartHyperparameterSearch, HyperparameterSpace
    import json

    logger.info("\n" + "="*80)
    logger.info("TUNING: BM25 Similarity Scorer")
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
        """Evaluate scorer with given hyperparameters"""

        # Create scorer with these params
        scorer = TunableBM25Scorer(
            questions=questions,
            k1=params['k1'],
            b=params['b'],
            max_features=int(params['max_features']),
            ngram_range=(1, int(params['max_ngram'])),
            domain_boost=params['domain_boost']
        )

        # Evaluate (use smaller sample for speed)
        metrics = evaluator.evaluate_retrieval_quality(
            scorer,
            k_values=[1, 3, 5, 10],
            sample_size=300  # Smaller sample for faster tuning
        )

        # Objective: Maximize weighted combination of metrics
        # Focus on precision@10 (main metric) and domain coherence
        score = (
            0.5 * metrics['precision@k'][10] +      # Precision@10
            0.2 * metrics['ndcg@k'][10] +           # nDCG@10
            0.2 * metrics['domain_coherence'] +     # Domain coherence
            0.1 * metrics['mrr']                    # MRR
        )

        return score

    # Define search space
    param_space = [
        HyperparameterSpace('k1', 0.5, 3.0, 'uniform'),              # BM25 term saturation
        HyperparameterSpace('b', 0.25, 1.0, 'uniform'),              # BM25 length norm
        HyperparameterSpace('max_features', 1000, 8000, 'log-uniform'),  # Vocabulary size
        HyperparameterSpace('max_ngram', 1, 2, 'uniform'),           # 1=unigrams, 2=bigrams
        HyperparameterSpace('domain_boost', 0.0, 0.4, 'uniform'),    # Domain boost
    ]

    # Run optimization
    logger.info("\nStarting Bayesian optimization...")
    optimizer = SmartHyperparameterSearch(
        objective_function=objective,
        param_space=param_space,
        n_calls=25,  # 25 evaluations (each takes ~30 seconds)
        n_random_starts=8
    )

    result = optimizer.optimize()

    # Evaluate best model on full sample
    logger.info("\n" + "="*80)
    logger.info("FINAL EVALUATION ON FULL SAMPLE")
    logger.info("="*80)

    best_params = result['best_params']
    logger.info("\nBest hyperparameters:")
    logger.info(f"  k1: {best_params['k1']:.3f}")
    logger.info(f"  b: {best_params['b']:.3f}")
    logger.info(f"  max_features: {int(best_params['max_features'])}")
    logger.info(f"  max_ngram: {int(best_params['max_ngram'])}")
    logger.info(f"  domain_boost: {best_params['domain_boost']:.3f}")

    best_scorer = TunableBM25Scorer(
        questions=questions,
        k1=best_params['k1'],
        b=best_params['b'],
        max_features=int(best_params['max_features']),
        ngram_range=(1, int(best_params['max_ngram'])),
        domain_boost=best_params['domain_boost']
    )

    # Full evaluation
    final_metrics = evaluator.evaluate_retrieval_quality(
        best_scorer,
        k_values=[1, 3, 5, 10],
        sample_size=500  # Full sample
    )

    # Compare with baseline
    logger.info("\n" + "="*80)
    logger.info("COMPARISON: Baseline TF-IDF vs Tuned BM25")
    logger.info("="*80)

    # Load baseline metrics
    baseline_path = Path("./similarity_scorer_evaluation.json")
    with open(baseline_path, 'r') as f:
        baseline_data = json.load(f)

    baseline_metrics = baseline_data['baseline_tfidf']

    logger.info(f"\n{'Metric':<25} {'Baseline (TF-IDF)':<20} {'Tuned (BM25)':<20} {'Improvement':<15}")
    logger.info("-" * 80)

    for k in [1, 3, 5, 10]:
        baseline_p = baseline_metrics['precision@k'][str(k)]
        tuned_p = final_metrics['precision@k'][k]
        improvement = ((tuned_p - baseline_p) / baseline_p * 100) if baseline_p > 0 else 0
        logger.info(f"{'Precision@' + str(k):<25} {baseline_p:<20.3f} {tuned_p:<20.3f} {improvement:>+13.1f}%")

    logger.info("")
    baseline_mrr = baseline_metrics['mrr']
    tuned_mrr = final_metrics['mrr']
    improvement = ((tuned_mrr - baseline_mrr) / baseline_mrr * 100) if baseline_mrr > 0 else 0
    logger.info(f"{'MRR':<25} {baseline_mrr:<20.3f} {tuned_mrr:<20.3f} {improvement:>+13.1f}%")

    logger.info("")
    baseline_dc = baseline_metrics['domain_coherence']
    tuned_dc = final_metrics['domain_coherence']
    improvement = ((tuned_dc - baseline_dc) / baseline_dc * 100) if baseline_dc > 0 else 0
    logger.info(f"{'Domain Coherence':<25} {baseline_dc:<20.3f} {tuned_dc:<20.3f} {improvement:>+13.1f}%")

    # Save results
    results_path = Path("./tuning_results_similarity.json")
    with open(results_path, 'w') as f:
        json.dump({
            'best_params': {
                'k1': best_params['k1'],
                'b': best_params['b'],
                'max_features': int(best_params['max_features']),
                'max_ngram': int(best_params['max_ngram']),
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
            'baseline_metrics': {
                'precision@1': baseline_metrics['precision@k']['1'],
                'precision@3': baseline_metrics['precision@k']['3'],
                'precision@5': baseline_metrics['precision@k']['5'],
                'precision@10': baseline_metrics['precision@k']['10'],
                'mrr': baseline_metrics['mrr'],
                'domain_coherence': baseline_metrics['domain_coherence']
            },
            'n_evaluations': result['n_evaluations']
        }, f, indent=2)

    logger.info(f"\n✅ Results saved to {results_path}")

    return result


if __name__ == "__main__":
    import sys

    print("\n" + "="*80)
    print("Tunable BM25 Similarity Scorer")
    print("="*80)

    if len(sys.argv) > 1 and sys.argv[1] == 'tune':
        # Run tuning
        result = tune_similarity_scorer()
    else:
        # Quick test
        import json

        print("\nQuick test mode (use 'python tunable_similarity_scorer.py tune' to run full tuning)")

        db_path = Path("./data/unified_database_complete.json")
        with open(db_path, 'r') as f:
            data = json.load(f)

        questions = data['questions'][:1000]  # Small subset for quick test

        # Create default scorer
        scorer = TunableBM25Scorer(
            questions=questions,
            k1=1.5,
            b=0.75,
            max_features=2000,
            ngram_range=(1, 2),
            domain_boost=0.2
        )

        # Test query
        test_query = "Calculate the eigenvalues of a matrix"
        results = scorer.search(test_query, top_k=5)

        print(f"\nTest query: '{test_query}'")
        print("\nTop 5 results:")
        for i, r in enumerate(results, 1):
            print(f"\n{i}. Score: {r['score']:.3f}")
            print(f"   {r['question']['question_text'][:100]}...")
            print(f"   Domain: {r['question']['domain']}, Difficulty: {r['question']['difficulty_score']:.2f}")

        print("\n" + "="*80)
        print("✅ Quick test complete!")
        print("="*80)
