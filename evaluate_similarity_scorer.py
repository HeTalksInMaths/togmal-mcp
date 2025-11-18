#!/usr/bin/env python3
"""
Similarity Scorer Evaluation Framework
=======================================

Evaluates similarity scorers using information retrieval metrics:
- Precision@K, Recall@K
- nDCG@K (Normalized Discounted Cumulative Gain)
- MRR (Mean Reciprocal Rank)
- Domain coherence
- Difficulty coherence
"""

import logging
import numpy as np
from typing import Dict, List, Optional
from collections import defaultdict
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimilarityScorerEvaluator:
    """Evaluates similarity scorers using IR metrics"""

    def __init__(self, questions: List[Dict]):
        """
        Args:
            questions: List of question dicts with question_id, domain, difficulty_score
        """
        self.questions = questions
        self.questions_by_id = {q['question_id']: q for q in questions}

        # Group questions by domain for sampling
        self.questions_by_domain = defaultdict(list)
        for q in questions:
            self.questions_by_domain[q['domain']].append(q)

        logger.info(f"Evaluator initialized with {len(questions):,} questions")

    def _create_relevance_labels(self, query_question: Dict) -> Dict[str, float]:
        """Create relevance labels for a query question

        Relevance is based on:
        - Same domain = higher relevance
        - Similar difficulty = higher relevance

        Args:
            query_question: The query question dict

        Returns:
            Dict mapping question_id -> relevance score (0-1)
        """
        relevance = {}
        query_domain = query_question['domain']
        query_difficulty = query_question['difficulty_score']

        for q in self.questions:
            if q['question_id'] == query_question['question_id']:
                continue  # Don't include query itself

            score = 0.0

            # Same domain = 0.6
            if q['domain'] == query_domain:
                score += 0.6

            # Similar difficulty (within 0.2) = 0.4
            diff_delta = abs(q['difficulty_score'] - query_difficulty)
            if diff_delta <= 0.2:
                similarity = 1.0 - (diff_delta / 0.2)
                score += 0.4 * similarity

            relevance[q['question_id']] = score

        return relevance

    def _compute_dcg(self, relevances: List[float], k: int) -> float:
        """Compute Discounted Cumulative Gain@K"""
        dcg = 0.0
        for i in range(min(k, len(relevances))):
            dcg += relevances[i] / np.log2(i + 2)  # i+2 because positions start at 1
        return dcg

    def _compute_ndcg(self, retrieved_relevances: List[float], ideal_relevances: List[float], k: int) -> float:
        """Compute Normalized DCG@K"""
        dcg = self._compute_dcg(retrieved_relevances, k)
        idcg = self._compute_dcg(sorted(ideal_relevances, reverse=True), k)

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def evaluate_retrieval_quality(
        self,
        scorer,
        k_values: List[int] = [1, 3, 5, 10],
        sample_size: int = 500
    ) -> Dict:
        """Evaluate retrieval quality using IR metrics

        Args:
            scorer: Scorer with search(query, top_k, query_domain) method
            k_values: List of K values to evaluate
            sample_size: Number of queries to sample

        Returns:
            Dict with metrics
        """
        logger.info(f"\nEvaluating retrieval quality on {sample_size} queries...")

        # Sample queries (stratified by domain)
        queries = []
        domains = list(self.questions_by_domain.keys())
        queries_per_domain = max(1, sample_size // len(domains))

        for domain in domains:
            domain_questions = self.questions_by_domain[domain]
            n_sample = min(queries_per_domain, len(domain_questions))
            queries.extend(random.sample(domain_questions, n_sample))

        # Shuffle
        random.shuffle(queries)
        queries = queries[:sample_size]

        logger.info(f"  Sampled {len(queries)} queries across {len(domains)} domains")

        # Evaluate each query
        max_k = max(k_values)
        precision_at_k = {k: [] for k in k_values}
        recall_at_k = {k: [] for k in k_values}
        ndcg_at_k = {k: [] for k in k_values}
        mrr_scores = []
        domain_coherence_scores = []
        difficulty_coherence_scores = []

        for i, query_q in enumerate(queries):
            if (i + 1) % 100 == 0:
                logger.info(f"  Processed {i + 1}/{len(queries)} queries...")

            # Get relevance labels
            relevance_labels = self._create_relevance_labels(query_q)

            # Retrieve top-K results
            results = scorer.search(
                query=query_q['question_text'],
                top_k=max_k,
                query_domain=query_q['domain']
            )

            retrieved_ids = [r['question_id'] for r in results]
            retrieved_relevances = [relevance_labels.get(qid, 0.0) for qid in retrieved_ids]

            # All possible relevances for nDCG
            all_relevances = list(relevance_labels.values())

            # Compute metrics for each K
            for k in k_values:
                top_k_ids = retrieved_ids[:k]
                top_k_relevances = retrieved_relevances[:k]

                # Precision@K: fraction of retrieved that are relevant (threshold > 0.5)
                relevant_retrieved = sum(1 for r in top_k_relevances if r > 0.5)
                precision = relevant_retrieved / k if k > 0 else 0
                precision_at_k[k].append(precision)

                # Recall@K: fraction of relevant that are retrieved
                total_relevant = sum(1 for r in all_relevances if r > 0.5)
                recall = relevant_retrieved / total_relevant if total_relevant > 0 else 0
                recall_at_k[k].append(recall)

                # nDCG@K
                ndcg = self._compute_ndcg(top_k_relevances, all_relevances, k)
                ndcg_at_k[k].append(ndcg)

            # MRR: reciprocal rank of first relevant result
            first_relevant_rank = None
            for rank, relevance in enumerate(retrieved_relevances, 1):
                if relevance > 0.5:
                    first_relevant_rank = rank
                    break

            if first_relevant_rank:
                mrr_scores.append(1.0 / first_relevant_rank)
            else:
                mrr_scores.append(0.0)

            # Domain coherence: % of top-10 from same domain
            top_10_domains = [self.questions_by_id[qid]['domain'] for qid in retrieved_ids[:10] if qid in self.questions_by_id]
            same_domain_count = sum(1 for d in top_10_domains if d == query_q['domain'])
            domain_coherence = same_domain_count / len(top_10_domains) if top_10_domains else 0
            domain_coherence_scores.append(domain_coherence)

            # Difficulty coherence: % of top-10 with similar difficulty (within 0.2)
            top_10_diffs = [abs(self.questions_by_id[qid]['difficulty_score'] - query_q['difficulty_score'])
                           for qid in retrieved_ids[:10] if qid in self.questions_by_id]
            similar_diff_count = sum(1 for d in top_10_diffs if d <= 0.2)
            difficulty_coherence = similar_diff_count / len(top_10_diffs) if top_10_diffs else 0
            difficulty_coherence_scores.append(difficulty_coherence)

        # Aggregate metrics
        metrics = {
            'precision@k': {k: np.mean(precision_at_k[k]) for k in k_values},
            'recall@k': {k: np.mean(recall_at_k[k]) for k in k_values},
            'ndcg@k': {k: np.mean(ndcg_at_k[k]) for k in k_values},
            'mrr': np.mean(mrr_scores),
            'domain_coherence': np.mean(domain_coherence_scores),
            'difficulty_coherence': np.mean(difficulty_coherence_scores),
            'n_queries': len(queries)
        }

        logger.info("\n  Results:")
        for k in k_values:
            logger.info(f"    Precision@{k}: {metrics['precision@k'][k]:.3f}")
        logger.info(f"    MRR: {metrics['mrr']:.3f}")
        logger.info(f"    Domain Coherence: {metrics['domain_coherence']:.3f}")
        logger.info(f"    Difficulty Coherence: {metrics['difficulty_coherence']:.3f}")

        return metrics


if __name__ == "__main__":
    import json
    from pathlib import Path
    from tunable_similarity_scorer import TunableBM25Scorer

    # Load questions
    db_path = Path("./data/unified_database_complete.json")
    with open(db_path, 'r') as f:
        data = json.load(f)

    questions = data['questions']

    # Create evaluator
    evaluator = SimilarityScorerEvaluator(questions)

    # Test with BM25 scorer
    print("\n" + "="*80)
    print("Testing Evaluator with BM25 Scorer")
    print("="*80)

    scorer = TunableBM25Scorer(
        questions=questions,
        k1=1.5,
        b=0.75,
        max_features=2000,
        ngram_range=(1, 2),
        domain_boost=0.2
    )

    metrics = evaluator.evaluate_retrieval_quality(
        scorer,
        k_values=[1, 3, 5, 10],
        sample_size=100
    )

    print("\n✅ Evaluator test complete!")
