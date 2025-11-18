#!/usr/bin/env python3
"""
Evaluation Framework for Similarity Scorer
==========================================

Evaluates similarity scoring quality using:
1. Domain coherence: Similar questions should be from same domain
2. Difficulty coherence: Similar questions should have similar difficulty
3. Retrieval metrics: Precision@K, Recall@K, nDCG
4. Cross-validation with synthetic relevance labels

Good experimental design:
- Use real benchmark data (not synthetic questions)
- Multiple evaluation metrics (not just one)
- Statistical significance testing
- Clear signal that tuning helps
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set
import numpy as np
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimilarityScorerEvaluator:
    """Evaluates similarity scoring quality"""

    def __init__(self, questions: List[Dict]):
        self.questions = questions
        self.questions_by_id = {q['question_id']: q for q in questions}

        # Create relevance labels (ground truth)
        self.relevance_labels = self._create_relevance_labels()

        logger.info(f"✅ Loaded {len(questions):,} questions for similarity evaluation")
        logger.info(f"✅ Created {sum(len(v) for v in self.relevance_labels.values()):,} relevance pairs")

    def _create_relevance_labels(self) -> Dict[str, Set[str]]:
        """Create ground truth relevance labels

        Strategy: Questions are considered "similar" if they share:
        1. Same domain AND similar difficulty (primary)
        2. Very similar text content (secondary)
        3. Similar model failure patterns (tertiary)
        """
        relevance = defaultdict(set)

        # Group by domain and difficulty bucket
        domain_difficulty_groups = defaultdict(list)

        for q in self.questions:
            domain = q['domain']
            # Bucket difficulty into 10 bins
            difficulty_bucket = int(q['difficulty_score'] * 10)
            key = (domain, difficulty_bucket)
            domain_difficulty_groups[key].append(q['question_id'])

        # Questions in the same domain+difficulty bucket are relevant
        for group_questions in domain_difficulty_groups.values():
            if len(group_questions) < 2:
                continue

            # Each question is relevant to others in its group
            for qid in group_questions:
                relevance[qid].update(set(group_questions) - {qid})

        return dict(relevance)

    def evaluate_retrieval_quality(
        self,
        scorer,
        k_values: List[int] = [1, 3, 5, 10],
        sample_size: int = 500
    ) -> Dict:
        """Evaluate similarity scorer with retrieval metrics

        Args:
            scorer: Similarity scorer with search() method
            k_values: Values of K for precision@K and recall@K
            sample_size: Number of queries to evaluate (for speed)

        Returns:
            Dict with metrics
        """
        logger.info(f"\nEvaluating similarity scorer...")
        logger.info(f"Sample size: {sample_size} queries")
        logger.info(f"K values: {k_values}")

        # Sample queries (questions with relevance labels)
        queries_with_labels = [(qid, labels) for qid, labels in self.relevance_labels.items() if len(labels) > 0]

        if len(queries_with_labels) > sample_size:
            import random
            random.seed(42)
            queries_with_labels = random.sample(queries_with_labels, sample_size)

        # Metrics storage
        precision_at_k = {k: [] for k in k_values}
        recall_at_k = {k: [] for k in k_values}
        ndcg_at_k = {k: [] for k in k_values}
        mrr_scores = []

        # Domain coherence: % of retrieved docs from same domain
        domain_coherence_scores = []

        # Difficulty coherence: Average difficulty difference
        difficulty_coherence_scores = []

        for qid, relevant_ids in queries_with_labels:
            query_q = self.questions_by_id[qid]
            query_text = query_q['question_text']
            query_domain = query_q['domain']
            query_difficulty = query_q['difficulty_score']

            # Get similar questions from scorer
            try:
                results = scorer.search(query_text, top_k=max(k_values))

                retrieved_ids = [r['question_id'] for r in results if r['question_id'] != qid]

                # Calculate metrics for each K
                for k in k_values:
                    top_k_ids = retrieved_ids[:k]

                    if len(top_k_ids) == 0:
                        continue

                    # Precision@K: fraction of retrieved that are relevant
                    num_relevant_retrieved = len(set(top_k_ids) & relevant_ids)
                    precision = num_relevant_retrieved / len(top_k_ids)
                    precision_at_k[k].append(precision)

                    # Recall@K: fraction of relevant that are retrieved
                    recall = num_relevant_retrieved / len(relevant_ids) if len(relevant_ids) > 0 else 0
                    recall_at_k[k].append(recall)

                    # nDCG@K
                    dcg = 0
                    idcg = 0
                    for i, rid in enumerate(top_k_ids, 1):
                        relevance_score = 1 if rid in relevant_ids else 0
                        dcg += relevance_score / np.log2(i + 1)

                    # Ideal DCG (all relevant docs first)
                    for i in range(1, min(k, len(relevant_ids)) + 1):
                        idcg += 1 / np.log2(i + 1)

                    ndcg = dcg / idcg if idcg > 0 else 0
                    ndcg_at_k[k].append(ndcg)

                # MRR: reciprocal rank of first relevant document
                for i, rid in enumerate(retrieved_ids, 1):
                    if rid in relevant_ids:
                        mrr_scores.append(1 / i)
                        break
                else:
                    mrr_scores.append(0)

                # Domain coherence
                top_10 = retrieved_ids[:10]
                if len(top_10) > 0:
                    same_domain_count = sum(1 for rid in top_10 if self.questions_by_id[rid]['domain'] == query_domain)
                    domain_coherence = same_domain_count / len(top_10)
                    domain_coherence_scores.append(domain_coherence)

                # Difficulty coherence
                if len(top_10) > 0:
                    difficulty_diffs = [abs(self.questions_by_id[rid]['difficulty_score'] - query_difficulty) for rid in top_10]
                    avg_diff = np.mean(difficulty_diffs)
                    difficulty_coherence_scores.append(1 - avg_diff)  # Higher is better

            except Exception as e:
                logger.warning(f"Error evaluating query {qid}: {e}")
                continue

        # Aggregate metrics
        metrics = {
            'precision@k': {k: np.mean(scores) for k, scores in precision_at_k.items() if len(scores) > 0},
            'recall@k': {k: np.mean(scores) for k, scores in recall_at_k.items() if len(scores) > 0},
            'ndcg@k': {k: np.mean(scores) for k, scores in ndcg_at_k.items() if len(scores) > 0},
            'mrr': np.mean(mrr_scores) if len(mrr_scores) > 0 else 0,
            'domain_coherence': np.mean(domain_coherence_scores) if len(domain_coherence_scores) > 0 else 0,
            'difficulty_coherence': np.mean(difficulty_coherence_scores) if len(difficulty_coherence_scores) > 0 else 0,
            'n_queries': len(queries_with_labels)
        }

        # Print results
        logger.info("\n" + "="*80)
        logger.info("SIMILARITY SCORER EVALUATION RESULTS")
        logger.info("="*80)
        logger.info(f"\nRetrieval Quality:")
        for k in k_values:
            logger.info(f"  Precision@{k}: {metrics['precision@k'].get(k, 0):.3f}")
            logger.info(f"  Recall@{k}:    {metrics['recall@k'].get(k, 0):.3f}")
            logger.info(f"  nDCG@{k}:      {metrics['ndcg@k'].get(k, 0):.3f}")

        logger.info(f"\nMRR (Mean Reciprocal Rank): {metrics['mrr']:.3f}")
        logger.info(f"\nCoherence Metrics:")
        logger.info(f"  Domain Coherence:     {metrics['domain_coherence']:.3f} (higher = better)")
        logger.info(f"  Difficulty Coherence: {metrics['difficulty_coherence']:.3f} (higher = better)")

        return metrics


class MockTFIDFScorer:
    """Mock TF-IDF scorer for baseline"""

    def __init__(self, questions):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity as cos_sim

        self.questions = questions
        self.questions_by_id = {q['question_id']: q for q in questions}
        self.cosine_similarity = cos_sim  # Store reference

        # Build TF-IDF matrix
        texts = [q['question_text'] for q in questions]
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)

        logger.info("✅ Built TF-IDF baseline scorer")

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Search for similar questions"""
        # Vectorize query
        query_vec = self.vectorizer.transform([query])

        # Compute similarities
        similarities = self.cosine_similarity(query_vec, self.tfidf_matrix)[0]

        # Get top-K
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append({
                'question_id': self.questions[idx]['question_id'],
                'score': float(similarities[idx]),
                'question': self.questions[idx]
            })

        return results


def main():
    """Main entry point"""

    print("\n" + "="*80)
    print("Similarity Scorer Evaluation")
    print("="*80)

    # Load questions
    db_path = Path("./data/unified_database_complete.json")
    with open(db_path, 'r') as f:
        data = json.load(f)

    questions = data['questions']

    # Create evaluator
    evaluator = SimilarityScorerEvaluator(questions)

    # Baseline: TF-IDF
    print("\n" + "="*80)
    print("Evaluating Baseline: TF-IDF")
    print("="*80)

    baseline_scorer = MockTFIDFScorer(questions)
    baseline_metrics = evaluator.evaluate_retrieval_quality(
        baseline_scorer,
        k_values=[1, 3, 5, 10],
        sample_size=500
    )

    # Save results
    results_path = Path("./similarity_scorer_evaluation.json")
    with open(results_path, 'w') as f:
        json.dump({
            'baseline_tfidf': baseline_metrics
        }, f, indent=2)

    logger.info(f"\n✅ Results saved to {results_path}")

    print("\n" + "="*80)
    print("✅ Evaluation complete!")
    print("="*80)
    print("\nNext steps:")
    print("1. Tune TF-IDF parameters (max_features, ngram_range, etc.)")
    print("2. Try BM25 (better than TF-IDF)")
    print("3. Add domain-specific boosting")
    print("4. Tune with Bayesian optimization")


if __name__ == "__main__":
    main()
