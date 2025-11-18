"""
Error Pattern Discovery Through Clustering

Uses vector embeddings and clustering algorithms to discover
novel error patterns in MMLU-Pro dataset.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.decomposition import PCA
import json

from error_taxonomy import ErrorRecord, ErrorCluster, ErrorSubtype


# ============================================================================
# Error Embedding and Clustering
# ============================================================================

class ErrorPatternDiscovery:
    """
    Discover patterns in errors through clustering and analysis.
    """

    def __init__(self, vector_db=None):
        """
        vector_db: Optional BenchmarkVectorDB instance for embeddings
        """
        self.vector_db = vector_db
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )

    def embed_errors(self, errors: List[ErrorRecord]) -> np.ndarray:
        """
        Get embeddings for error questions.

        If vector_db is available, use existing embeddings.
        Otherwise, use TF-IDF as fallback.
        """
        if self.vector_db is not None:
            # Use sentence transformer embeddings from vector DB
            embeddings = []
            for error in errors:
                # Query vector DB for this question
                result = self.vector_db.query_similar_questions(
                    error.question_text,
                    k=1
                )
                # Get embedding from metadata or recompute
                # For now, assume we need to recompute
                embedding = self.vector_db.model.encode([error.question_text])[0]
                embeddings.append(embedding)

            return np.array(embeddings)

        else:
            # Fallback: TF-IDF embeddings
            texts = [e.question_text for e in errors]
            return self.tfidf_vectorizer.fit_transform(texts).toarray()

    def cluster_errors_hdbscan(
        self,
        errors: List[ErrorRecord],
        min_cluster_size: int = 5,
        min_samples: int = 3
    ) -> List[ErrorCluster]:
        """
        Cluster errors using HDBSCAN (good for varying densities).

        HDBSCAN advantages:
        - Automatically determines number of clusters
        - Handles noise (outlier errors)
        - Works with varying cluster densities
        """
        if len(errors) < min_cluster_size:
            return []

        # Get embeddings
        embeddings = self.embed_errors(errors)

        # Cluster
        clusterer = HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric='euclidean'
        )

        labels = clusterer.fit_predict(embeddings)

        # Build clusters
        clusters = []
        for label in set(labels):
            if label == -1:  # Noise cluster
                continue

            cluster_errors = [e for e, l in zip(errors, labels) if l == label]

            cluster = self._build_cluster(
                cluster_id=label,
                errors=cluster_errors
            )

            clusters.append(cluster)

        return clusters

    def cluster_errors_kmeans(
        self,
        errors: List[ErrorRecord],
        n_clusters: int = 10
    ) -> List[ErrorCluster]:
        """
        Cluster errors using K-Means (when you know number of clusters).
        """
        if len(errors) < n_clusters:
            n_clusters = max(2, len(errors) // 5)

        embeddings = self.embed_errors(errors)

        clusterer = KMeans(n_clusters=n_clusters, random_state=42)
        labels = clusterer.fit_predict(embeddings)

        clusters = []
        for label in range(n_clusters):
            cluster_errors = [e for e, l in zip(errors, labels) if l == label]

            if len(cluster_errors) < 2:  # Skip tiny clusters
                continue

            cluster = self._build_cluster(
                cluster_id=label,
                errors=cluster_errors
            )

            clusters.append(cluster)

        return clusters

    def _build_cluster(
        self,
        cluster_id: int,
        errors: List[ErrorRecord]
    ) -> ErrorCluster:
        """
        Build ErrorCluster object with analysis.
        """
        # Common characteristics
        common_domains = Counter(e.domain for e in errors)
        avg_difficulty = np.mean([e.difficulty_score for e in errors])
        affected_models = set(e.model_name for e in errors)

        # Extract keywords using TF-IDF
        keywords = self._extract_keywords(errors)

        # Sample questions
        sample_questions = [e.question_text for e in errors[:5]]

        # Dominant error type
        error_types = [e.error_subtype for e in errors if e.error_subtype]
        dominant_type = Counter(error_types).most_common(1)[0][0] if error_types else None

        # Generate cluster interpretation
        cluster_name, cluster_description = self._interpret_cluster(
            errors, common_domains, keywords, dominant_type
        )

        return ErrorCluster(
            cluster_id=cluster_id,
            size=len(errors),
            error_records=errors,
            common_domains=dict(common_domains),
            avg_difficulty=avg_difficulty,
            affected_models=affected_models,
            common_keywords=keywords,
            sample_questions=sample_questions,
            dominant_error_type=dominant_type,
            cluster_name=cluster_name,
            cluster_description=cluster_description
        )

    def _extract_keywords(
        self,
        errors: List[ErrorRecord],
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Extract characteristic keywords for this cluster using TF-IDF.
        """
        texts = [e.question_text for e in errors]

        if len(texts) < 2:
            return []

        try:
            # Fit TF-IDF on this cluster
            vectorizer = TfidfVectorizer(
                max_features=top_n,
                stop_words='english',
                ngram_range=(1, 2)
            )

            tfidf_matrix = vectorizer.fit_transform(texts)

            # Get average TF-IDF score for each term
            avg_scores = tfidf_matrix.mean(axis=0).A1

            # Get feature names and scores
            feature_names = vectorizer.get_feature_names_out()

            # Sort by score
            keyword_scores = list(zip(feature_names, avg_scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)

            return keyword_scores[:top_n]

        except:
            return []

    def _interpret_cluster(
        self,
        errors: List[ErrorRecord],
        common_domains: Counter,
        keywords: List[Tuple[str, float]],
        dominant_type: Optional[ErrorSubtype]
    ) -> Tuple[str, str]:
        """
        Generate human-readable cluster name and description.
        """
        # Find most common domain
        if common_domains:
            top_domain = common_domains.most_common(1)[0][0]
            domain_pct = common_domains.most_common(1)[0][1] / len(errors) * 100
        else:
            top_domain = "unknown"
            domain_pct = 0

        # Build name
        if domain_pct >= 70:  # Domain-specific cluster
            if dominant_type:
                name = f"{top_domain.title()} - {dominant_type.value.replace('_', ' ').title()}"
            else:
                name = f"{top_domain.title()} Errors"
        else:  # Cross-domain cluster
            if dominant_type:
                name = f"Cross-domain {dominant_type.value.replace('_', ' ').title()}"
            else:
                name = f"Mixed Error Cluster {errors[0].question_id[:8]}"

        # Build description
        desc_parts = []

        desc_parts.append(f"{len(errors)} errors")

        if domain_pct >= 70:
            desc_parts.append(f"primarily in {top_domain}")
        else:
            top_3_domains = [d for d, _ in common_domains.most_common(3)]
            desc_parts.append(f"across {', '.join(top_3_domains)}")

        if dominant_type:
            desc_parts.append(f"showing {dominant_type.value.replace('_', ' ')}")

        if keywords:
            top_keywords = [kw for kw, _ in keywords[:3]]
            desc_parts.append(f"related to: {', '.join(top_keywords)}")

        description = "; ".join(desc_parts)

        return name, description


# ============================================================================
# Error Co-occurrence Analysis
# ============================================================================

class ErrorCooccurrenceAnalyzer:
    """
    Analyze which errors tend to occur together across models/questions.
    """

    @staticmethod
    def build_error_matrix(
        errors: List[ErrorRecord]
    ) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        Build question × model error matrix.

        Returns:
        - matrix: Binary matrix where matrix[i,j] = 1 if model j failed question i
        - question_ids: List of question IDs (rows)
        - model_names: List of model names (columns)
        """
        # Get unique questions and models
        question_ids = sorted(list(set(e.question_id for e in errors)))
        model_names = sorted(list(set(e.model_name for e in errors)))

        # Build matrix
        matrix = np.zeros((len(question_ids), len(model_names)), dtype=int)

        question_to_idx = {qid: i for i, qid in enumerate(question_ids)}
        model_to_idx = {m: i for i, m in enumerate(model_names)}

        for error in errors:
            i = question_to_idx[error.question_id]
            j = model_to_idx[error.model_name]
            matrix[i, j] = 1

        return matrix, question_ids, model_names

    @staticmethod
    def find_correlated_questions(
        errors: List[ErrorRecord],
        min_correlation: float = 0.5
    ) -> List[Tuple[str, str, float]]:
        """
        Find pairs of questions where errors are correlated across models.

        If model fails question A, it's likely to fail question B.
        This suggests similar underlying difficulty.
        """
        matrix, question_ids, model_names = (
            ErrorCooccurrenceAnalyzer.build_error_matrix(errors)
        )

        if matrix.shape[0] < 2 or matrix.shape[1] < 2:
            return []

        # Compute correlation matrix (question × question)
        correlation_matrix = np.corrcoef(matrix)

        # Find pairs with high correlation
        correlated_pairs = []

        for i in range(len(question_ids)):
            for j in range(i + 1, len(question_ids)):
                corr = correlation_matrix[i, j]

                if corr >= min_correlation and not np.isnan(corr):
                    correlated_pairs.append((
                        question_ids[i],
                        question_ids[j],
                        corr
                    ))

        # Sort by correlation strength
        correlated_pairs.sort(key=lambda x: x[2], reverse=True)

        return correlated_pairs

    @staticmethod
    def find_correlated_errors_across_models(
        errors: List[ErrorRecord],
        min_jaccard: float = 0.5
    ) -> List[Tuple[str, str, float]]:
        """
        Find pairs of models with similar error patterns.

        Uses Jaccard similarity: intersection / union of failed questions.
        """
        # Group errors by model
        model_to_questions = defaultdict(set)
        for error in errors:
            model_to_questions[error.model_name].add(error.question_id)

        model_names = list(model_to_questions.keys())

        if len(model_names) < 2:
            return []

        # Compute pairwise Jaccard similarity
        similar_models = []

        for i in range(len(model_names)):
            for j in range(i + 1, len(model_names)):
                model_a = model_names[i]
                model_b = model_names[j]

                questions_a = model_to_questions[model_a]
                questions_b = model_to_questions[model_b]

                intersection = len(questions_a & questions_b)
                union = len(questions_a | questions_b)

                if union == 0:
                    continue

                jaccard = intersection / union

                if jaccard >= min_jaccard:
                    similar_models.append((model_a, model_b, jaccard))

        similar_models.sort(key=lambda x: x[2], reverse=True)

        return similar_models


# ============================================================================
# Distractor Analysis
# ============================================================================

@dataclass
class DistractorAnalysis:
    """
    Analysis of wrong answer choices (distractors) and why they're attractive.
    """
    question_id: str
    correct_answer: str

    # Distractor strength (how often each wrong choice is selected)
    distractor_frequency: Dict[str, int]

    # Most common wrong answer
    strongest_distractor: Optional[str]
    distractor_strength: float  # % of errors that chose this distractor

    # Why is this distractor attractive?
    plausibility_reasons: List[str]


class DistractorAnalyzer:
    """
    Analyze why certain wrong answers are frequently chosen.
    """

    @staticmethod
    def analyze_distractors(
        question_id: str,
        correct_answer: str,
        errors: List[ErrorRecord]
    ) -> DistractorAnalysis:
        """
        Analyze distractor strength for a question.
        """
        # Filter errors for this question
        question_errors = [e for e in errors if e.question_id == question_id]

        if not question_errors:
            return None

        # Count wrong answers
        wrong_answers = [e.model_answer for e in question_errors
                        if e.model_answer != "UNKNOWN"]

        if not wrong_answers:
            return None

        distractor_freq = Counter(wrong_answers)

        # Find strongest distractor
        if distractor_freq:
            strongest = distractor_freq.most_common(1)[0][0]
            strength = distractor_freq[strongest] / len(wrong_answers)
        else:
            strongest = None
            strength = 0.0

        # Analyze why distractors are plausible
        plausibility = []

        if strength >= 0.7:
            plausibility.append("Systematic error - most models chose same wrong answer")

        if len(distractor_freq) == 1:
            plausibility.append("All errors chose the same wrong answer")

        # Check if distractor is adjacent to correct answer
        if strongest and correct_answer:
            correct_ord = ord(correct_answer)
            strongest_ord = ord(strongest)
            if abs(correct_ord - strongest_ord) == 1:
                plausibility.append("Adjacent to correct answer (position bias?)")

        return DistractorAnalysis(
            question_id=question_id,
            correct_answer=correct_answer,
            distractor_frequency=dict(distractor_freq),
            strongest_distractor=strongest,
            distractor_strength=strength,
            plausibility_reasons=plausibility
        )


# ============================================================================
# Pattern Exporter
# ============================================================================

class PatternExporter:
    """
    Export discovered patterns to various formats.
    """

    @staticmethod
    def export_clusters_to_json(
        clusters: List[ErrorCluster],
        output_path: str
    ) -> None:
        """Export clusters to JSON format"""
        cluster_data = []

        for cluster in clusters:
            cluster_data.append({
                'cluster_id': cluster.cluster_id,
                'name': cluster.cluster_name,
                'description': cluster.cluster_description,
                'size': cluster.size,
                'avg_difficulty': cluster.avg_difficulty,
                'common_domains': cluster.common_domains,
                'affected_models': list(cluster.affected_models),
                'keywords': [(kw, float(score)) for kw, score in cluster.common_keywords],
                'dominant_error_type': cluster.dominant_error_type.value if cluster.dominant_error_type else None,
                'sample_questions': cluster.sample_questions
            })

        with open(output_path, 'w') as f:
            json.dump(cluster_data, f, indent=2)

    @staticmethod
    def export_cooccurrence_matrix(
        errors: List[ErrorRecord],
        output_path: str
    ) -> None:
        """Export question-model error matrix to CSV"""
        matrix, question_ids, model_names = (
            ErrorCooccurrenceAnalyzer.build_error_matrix(errors)
        )

        with open(output_path, 'w') as f:
            # Header
            f.write('question_id,' + ','.join(model_names) + '\n')

            # Rows
            for i, qid in enumerate(question_ids):
                row = [qid] + [str(matrix[i, j]) for j in range(len(model_names))]
                f.write(','.join(row) + '\n')

    @staticmethod
    def generate_pattern_report(
        clusters: List[ErrorCluster],
        cooccurrence_results: Dict,
        output_path: str
    ) -> None:
        """Generate human-readable pattern discovery report"""
        with open(output_path, 'w') as f:
            f.write("# Error Pattern Discovery Report\n\n")

            # Overview
            f.write(f"## Overview\n\n")
            f.write(f"- Total clusters discovered: {len(clusters)}\n")
            f.write(f"- Total errors analyzed: {sum(c.size for c in clusters)}\n\n")

            # Top clusters
            f.write("## Top Error Patterns\n\n")

            sorted_clusters = sorted(clusters, key=lambda c: c.size, reverse=True)

            for i, cluster in enumerate(sorted_clusters[:10], 1):
                f.write(f"### {i}. {cluster.cluster_name}\n\n")
                f.write(f"**Description**: {cluster.cluster_description}\n\n")
                f.write(f"**Size**: {cluster.size} errors\n\n")
                f.write(f"**Avg Difficulty**: {cluster.avg_difficulty:.2f}\n\n")

                if cluster.common_keywords:
                    f.write("**Keywords**: ")
                    kw_str = ", ".join([kw for kw, _ in cluster.common_keywords[:5]])
                    f.write(f"{kw_str}\n\n")

                if cluster.dominant_error_type:
                    f.write(f"**Error Type**: {cluster.dominant_error_type.value}\n\n")

                f.write("**Sample Question**:\n")
                f.write(f"> {cluster.sample_questions[0][:200]}...\n\n")

                f.write("---\n\n")

            # Correlations
            if cooccurrence_results:
                f.write("## Correlated Errors\n\n")

                if 'question_pairs' in cooccurrence_results:
                    f.write("### Questions with Similar Error Patterns\n\n")
                    for q1, q2, corr in cooccurrence_results['question_pairs'][:5]:
                        f.write(f"- {q1} ↔ {q2}: {corr:.2f} correlation\n")
                    f.write("\n")

                if 'model_pairs' in cooccurrence_results:
                    f.write("### Models with Similar Error Patterns\n\n")
                    for m1, m2, jaccard in cooccurrence_results['model_pairs'][:5]:
                        f.write(f"- {m1} ↔ {m2}: {jaccard:.2f} Jaccard similarity\n")
                    f.write("\n")
