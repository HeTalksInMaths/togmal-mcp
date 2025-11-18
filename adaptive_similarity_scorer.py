#!/usr/bin/env python3
"""
Adaptive Similarity Scorer
===========================

IMPROVEMENTS OVER BASIC TF-IDF:
1. ✅ BM25 instead of TF-IDF (better relevance scoring)
2. ✅ Domain-specific term boosting
3. ✅ Query expansion from similar terms
4. ✅ Hybrid search (text + metadata filters)
5. ✅ Feedback learning (learns from relevance judgments)
6. ✅ Reranking with cross-encoder simulation

Key Innovation: Combines multiple signals for better semantic matching
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import chromadb

class AdaptiveSimilarityScorer:
    """Adaptive similarity scorer with multiple ranking signals"""

    def __init__(self, data_dir: Path = Path("./data"), chroma_dir: Path = Path("./chroma_db")):
        self.data_dir = data_dir
        self.chroma_dir = chroma_dir

        # Load data
        print("Loading data...")
        self.questions = self._load_questions()
        self.texts = [q['question_text'] for q in self.questions]

        # Load ChromaDB
        self.client = chromadb.PersistentClient(path=str(chroma_dir))
        self.collection = self.client.get_collection("togmal_benchmarks")

        # Build BM25 model (better than TF-IDF)
        print("Building BM25 model...")
        self.bm25_vectorizer, self.bm25_matrix = self._build_bm25()

        # Build domain-specific models
        print("Building domain-specific models...")
        self.domain_models = self._build_domain_models()

        # Term importance scores (learned from data)
        self.term_importance = self._compute_term_importance()

        # Feedback history for learning
        self.feedback_data = []
        self.query_expansions = {}  # Cache expanded queries

        print("✅ Adaptive similarity scorer ready!")

    def _load_questions(self) -> List[Dict]:
        """Load all questions"""
        db_path = self.data_dir / "unified_database_complete.json"
        with open(db_path) as f:
            return json.load(f)['questions']

    def _build_bm25(self) -> Tuple:
        """
        Build BM25 model (better than pure TF-IDF)

        BM25 improvements:
        - Saturation function for term frequency
        - Document length normalization
        - Better for query-document matching
        """
        # Use CountVectorizer for BM25 (need raw term frequencies)
        vectorizer = CountVectorizer(
            max_features=384,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8,
            stop_words='english'
        )

        # Get term frequency matrix
        tf_matrix = vectorizer.fit_transform(self.texts)

        # Convert to BM25 scores
        bm25_matrix = self._tf_to_bm25(tf_matrix, k1=1.5, b=0.75)

        print(f"  ✅ BM25 model built ({bm25_matrix.shape})")
        return vectorizer, bm25_matrix

    def _tf_to_bm25(self, tf_matrix, k1=1.5, b=0.75):
        """
        Convert TF matrix to BM25 scores

        BM25 formula:
        score(D,Q) = Σ IDF(qi) * (f(qi,D) * (k1+1)) / (f(qi,D) + k1*(1-b+b*|D|/avgdl))

        Args:
            k1: Controls term frequency saturation (default: 1.5)
            b: Controls document length normalization (default: 0.75)
        """
        N = tf_matrix.shape[0]  # Number of documents

        # Document lengths
        doc_lengths = np.array(tf_matrix.sum(axis=1)).flatten()
        avg_doc_length = doc_lengths.mean()

        # IDF scores
        df = np.array((tf_matrix > 0).sum(axis=0)).flatten()
        idf = np.log((N - df + 0.5) / (df + 0.5) + 1)

        # BM25 scores
        bm25_matrix = tf_matrix.toarray().copy()

        for i in range(N):
            doc_len = doc_lengths[i]
            norm = 1 - b + b * (doc_len / avg_doc_length)

            for j in range(tf_matrix.shape[1]):
                tf = bm25_matrix[i, j]
                if tf > 0:
                    bm25_matrix[i, j] = idf[j] * (tf * (k1 + 1)) / (tf + k1 * norm)

        return bm25_matrix

    def _build_domain_models(self) -> Dict:
        """Build specialized models for each domain"""
        domain_models = {}

        # Group questions by domain
        by_domain = defaultdict(list)
        for q in self.questions:
            by_domain[q['domain']].append(q['question_text'])

        # Build vectorizer for major domains (with enough data)
        for domain, texts in by_domain.items():
            if len(texts) >= 50:  # Need sufficient data
                vectorizer = TfidfVectorizer(
                    max_features=384,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.8,
                    stop_words='english'
                )
                try:
                    matrix = vectorizer.fit_transform(texts)
                    domain_models[domain] = {
                        'vectorizer': vectorizer,
                        'matrix': matrix,
                        'texts': texts,
                        'boost': 0.2  # Boost score if domain matches
                    }
                except:
                    pass  # Skip if not enough unique terms

        print(f"  ✅ Built {len(domain_models)} domain-specific models")
        return domain_models

    def _compute_term_importance(self) -> Dict[str, float]:
        """
        Compute term importance scores from data

        Terms that appear in difficult questions get higher importance
        """
        term_scores = defaultdict(float)
        term_counts = defaultdict(int)

        # Weight terms by inverse success rate (harder questions = more important terms)
        for q in self.questions:
            success_rate = q.get('success_rate', 0.5)
            difficulty_weight = 1.0 - success_rate  # Lower success = higher weight

            # Extract terms
            text = q['question_text'].lower()
            words = text.split()

            for word in words:
                if len(word) > 3:  # Skip short words
                    term_scores[word] += difficulty_weight
                    term_counts[word] += 1

        # Normalize
        for term in term_scores:
            if term_counts[term] > 0:
                term_scores[term] /= term_counts[term]

        print(f"  ✅ Computed importance for {len(term_scores)} terms")
        return dict(term_scores)

    def adaptive_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None,
        use_expansion: bool = True,
        use_reranking: bool = True
    ) -> List[Dict]:
        """
        Adaptive semantic search with multiple signals

        Args:
            query: Search query
            top_k: Number of results
            filters: Optional metadata filters (difficulty, domain, etc.)
            use_expansion: Use query expansion
            use_reranking: Use reranking signals

        Returns:
            List of results with enhanced scoring
        """

        # Step 1: Query expansion
        if use_expansion:
            expanded_query = self._expand_query(query)
        else:
            expanded_query = query

        # Step 2: BM25 retrieval (first stage)
        bm25_results = self._bm25_search(expanded_query, top_k=top_k * 2)  # Get 2x for reranking

        # Step 3: Apply metadata filters
        if filters:
            bm25_results = self._apply_filters(bm25_results, filters)

        # Step 4: Domain-specific boost
        bm25_results = self._apply_domain_boost(bm25_results, query)

        # Step 5: Reranking (second stage)
        if use_reranking:
            final_results = self._rerank_results(query, bm25_results, top_k=top_k)
        else:
            final_results = bm25_results[:top_k]

        return final_results

    def _expand_query(self, query: str) -> str:
        """
        Expand query with related terms

        Uses term co-occurrence to find related terms
        """
        if query in self.query_expansions:
            return self.query_expansions[query]

        # Find terms that co-occur with query terms
        query_terms = set(query.lower().split())
        related_terms = set()

        # Look at top similar documents
        initial_results = self._bm25_search(query, top_k=10)

        # Extract common terms from similar documents
        term_freq = Counter()
        for res in initial_results:
            doc_terms = res['text'].lower().split()
            for term in doc_terms:
                if term not in query_terms and len(term) > 3:
                    term_freq[term] += 1

        # Add top co-occurring terms
        top_related = [term for term, _ in term_freq.most_common(3)]
        related_terms.update(top_related)

        # Build expanded query
        expanded = query + " " + " ".join(related_terms)
        self.query_expansions[query] = expanded

        return expanded

    def _bm25_search(self, query: str, top_k: int) -> List[Dict]:
        """BM25 retrieval"""
        # Transform query
        query_vec = self.bm25_vectorizer.transform([query])

        # Convert to BM25 (for query, just use TF)
        query_bm25 = query_vec.toarray()[0]

        # Compute similarities
        similarities = cosine_similarity(query_bm25.reshape(1, -1), self.bm25_matrix)[0]

        # Get top k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append({
                'index': int(idx),
                'text': self.texts[idx],
                'metadata': self.questions[idx],
                'bm25_score': float(similarities[idx])
            })

        return results

    def _apply_filters(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """Apply metadata filters"""
        filtered = []

        for res in results:
            meta = res['metadata']

            # Check each filter
            match = True
            if 'difficulty' in filters:
                if meta.get('difficulty_label') != filters['difficulty']:
                    match = False

            if 'domain' in filters:
                if meta.get('domain') != filters['domain']:
                    match = False

            if 'min_success_rate' in filters:
                if meta.get('success_rate', 0) < filters['min_success_rate']:
                    match = False

            if 'max_success_rate' in filters:
                if meta.get('success_rate', 1) > filters['max_success_rate']:
                    match = False

            if match:
                filtered.append(res)

        return filtered

    def _apply_domain_boost(self, results: List[Dict], query: str) -> List[Dict]:
        """
        Boost scores for domain-specific matches

        If query matches domain vocabulary, boost those results
        """
        # Detect query domain
        query_domain = self._detect_domain(query)

        if query_domain and query_domain in self.domain_models:
            domain_model = self.domain_models[query_domain]

            # Recompute scores with domain-specific model
            domain_vec = domain_model['vectorizer'].transform([query])
            domain_sims = cosine_similarity(domain_vec, domain_model['matrix'])[0]

            # Apply boost
            boost = domain_model['boost']

            for res in results:
                if res['metadata'].get('domain') == query_domain:
                    # Find this text in domain model
                    try:
                        domain_idx = domain_model['texts'].index(res['text'])
                        domain_score = domain_sims[domain_idx]
                        res['domain_boost'] = boost * domain_score
                        res['bm25_score'] += res['domain_boost']
                    except:
                        res['domain_boost'] = 0.0
                else:
                    res['domain_boost'] = 0.0

        return results

    def _detect_domain(self, query: str) -> Optional[str]:
        """Detect query domain from keywords"""
        query_lower = query.lower()

        domain_keywords = {
            'Pandas': ['pandas', 'dataframe', 'df[', '.loc', '.iloc'],
            'math': ['calculate', 'solve', 'equation', 'matrix', 'eigenvalue'],
            'physics': ['quantum', 'energy', 'force', 'particle'],
            'chemistry': ['molecule', 'reaction', 'compound', 'element'],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return domain

        return None

    def _rerank_results(self, query: str, results: List[Dict], top_k: int) -> List[Dict]:
        """
        Rerank results with additional signals

        Signals:
        1. BM25 score (already computed)
        2. Query term coverage
        3. Term importance overlap
        4. Success rate (prefer diverse difficulties)
        5. Domain match
        """

        query_terms = set(query.lower().split())

        for res in results:
            text = res['text'].lower()
            text_terms = set(text.split())

            # Signal 1: Query term coverage
            coverage = len(query_terms & text_terms) / max(len(query_terms), 1)
            res['coverage_score'] = coverage

            # Signal 2: Term importance overlap
            importance_sum = sum(self.term_importance.get(term, 0.5) for term in text_terms & query_terms)
            res['importance_score'] = importance_sum / max(len(query_terms), 1)

            # Signal 3: Success rate diversity (slight preference for challenging questions)
            success_rate = res['metadata'].get('success_rate', 0.5)
            res['difficulty_score'] = 0.5 + 0.5 * (1.0 - success_rate)  # 0.5-1.0 range

            # Signal 4: Domain match bonus (already in domain_boost)
            domain_bonus = res.get('domain_boost', 0.0)

            # Combined reranking score
            res['rerank_score'] = (
                0.50 * res['bm25_score'] +
                0.20 * res['coverage_score'] +
                0.15 * res['importance_score'] +
                0.10 * res['difficulty_score'] +
                0.05 * domain_bonus
            )

        # Sort by reranking score
        results.sort(key=lambda x: x['rerank_score'], reverse=True)

        return results[:top_k]

    def record_feedback(self, query: str, result_id: int, relevance: float):
        """
        Record feedback for learning

        Args:
            query: The search query
            result_id: ID of the result
            relevance: Relevance score (0.0-1.0, 1.0 = highly relevant)
        """
        self.feedback_data.append({
            'query': query,
            'result_id': result_id,
            'relevance': relevance
        })

        # Adapt term importance based on feedback
        if len(self.feedback_data) % 10 == 0:
            self._update_term_importance()

    def _update_term_importance(self):
        """Update term importance based on feedback"""
        # Analyze which terms lead to relevant results
        term_relevance = defaultdict(list)

        for feedback in self.feedback_data[-100:]:  # Last 100 feedbacks
            query_terms = set(feedback['query'].lower().split())
            relevance = feedback['relevance']

            for term in query_terms:
                term_relevance[term].append(relevance)

        # Update importance scores
        for term, relevances in term_relevance.items():
            if len(relevances) >= 3:  # Need sufficient data
                avg_relevance = np.mean(relevances)
                # Blend with existing score
                if term in self.term_importance:
                    self.term_importance[term] = 0.7 * self.term_importance[term] + 0.3 * avg_relevance
                else:
                    self.term_importance[term] = avg_relevance

        print(f"📊 Updated term importance from {len(self.feedback_data)} feedbacks")


def test_adaptive_similarity():
    """Test adaptive similarity scorer"""
    print("="*80)
    print("ADAPTIVE SIMILARITY SCORER - TEST")
    print("="*80)

    scorer = AdaptiveSimilarityScorer()

    test_queries = [
        ("Calculate eigenvalues of a matrix", None),
        ("Write pandas code to filter a dataframe", {'domain': 'Pandas'}),
        ("quantum mechanics and entanglement", None),
        ("prove mathematical theorem", {'difficulty': 'Expert'}),
    ]

    for query, filters in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: \"{query}\"")
        if filters:
            print(f"Filters: {filters}")
        print("-"*80)

        results = scorer.adaptive_search(query, top_k=3, filters=filters)

        for i, res in enumerate(results, 1):
            meta = res['metadata']
            print(f"\n{i}. BM25: {res['bm25_score']:.3f} | Rerank: {res['rerank_score']:.3f}")
            print(f"   {res['text'][:100]}...")
            print(f"   Domain: {meta['domain']} | Difficulty: {meta['difficulty_label']}")
            print(f"   Success: {meta['success_rate']:.1%}")
            if 'domain_boost' in res:
                print(f"   Domain Boost: +{res['domain_boost']:.3f}")

    # Test feedback learning
    print("\n" + "="*80)
    print("TESTING FEEDBACK LEARNING")
    print("="*80)

    scorer.record_feedback("eigenvalues matrix", 0, 0.9)  # Relevant
    scorer.record_feedback("eigenvalues matrix", 1, 0.7)  # Somewhat relevant
    scorer.record_feedback("eigenvalues matrix", 2, 0.3)  # Not very relevant

    print("✅ Recorded 3 feedback examples")
    print("Term importance will adapt over time")

if __name__ == "__main__":
    test_adaptive_similarity()
