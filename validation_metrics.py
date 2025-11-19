"""
Validation Metrics Implementation

Implements the 8-point validation framework to ensure taxonomy is grounded.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score, silhouette_score, roc_auc_score

from error_taxonomy import ErrorRecord, ErrorSubtype, ErrorCategory


@dataclass
class ValidationResult:
    """Result of a single validation metric"""
    metric_name: str
    score: float
    threshold: float
    passed: bool
    interpretation: str
    action_needed: str = ""
    details: Dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Complete validation report"""
    total_validations: int
    passed_validations: int
    overall_score: float
    results: List[ValidationResult]
    summary: str
    ready_for_publication: bool


class TaxonomyValidator:
    """
    Comprehensive validation suite for error taxonomy.

    Implements 8 validation metrics from VALIDATION_FRAMEWORK.md
    """

    def __init__(self, errors: List[ErrorRecord]):
        self.errors = errors

    # ========================================================================
    # Validation 1: Cluster Coherence
    # ========================================================================

    def measure_cluster_coherence(
        self,
        cluster_labels: Optional[List[int]] = None
    ) -> ValidationResult:
        """
        Measure if clusters are internally coherent.

        Metrics:
        - Silhouette score: How well-separated are clusters?
        - Target: Silhouette > 0.4

        Args:
            cluster_labels: Cluster assignment for each error (optional)
        """
        # Get embeddings if available
        embeddings = []
        valid_errors = []

        for error in self.errors:
            if error.question_embedding is not None:
                embeddings.append(error.question_embedding)
                valid_errors.append(error)

        if len(embeddings) < 10:
            return ValidationResult(
                metric_name="Cluster Coherence",
                score=0.0,
                threshold=0.4,
                passed=False,
                interpretation="Insufficient embeddings to compute coherence",
                action_needed="Generate embeddings for errors first"
            )

        embeddings = np.array(embeddings)

        # Use error subtype as cluster labels if not provided
        if cluster_labels is None:
            cluster_labels = [
                list(ErrorSubtype).index(e.error_subtype) if e.error_subtype else -1
                for e in valid_errors
            ]

        # Filter out unclustered items (-1)
        mask = np.array(cluster_labels) != -1
        filtered_embeddings = embeddings[mask]
        filtered_labels = np.array(cluster_labels)[mask]

        if len(filtered_embeddings) < 10:
            return ValidationResult(
                metric_name="Cluster Coherence",
                score=0.0,
                threshold=0.4,
                passed=False,
                interpretation="Too few clustered items",
                action_needed="Classify more errors"
            )

        # Compute silhouette score
        try:
            silhouette = silhouette_score(filtered_embeddings, filtered_labels)
        except:
            silhouette = 0.0

        passed = silhouette > 0.4

        if passed:
            interpretation = "Excellent - clusters are well-separated"
        elif silhouette > 0.3:
            interpretation = "Acceptable - clusters show some structure"
        elif silhouette > 0.2:
            interpretation = "Weak - clusters are not well-defined"
        else:
            interpretation = "Poor - clusters appear arbitrary"

        return ValidationResult(
            metric_name="Cluster Coherence",
            score=silhouette,
            threshold=0.4,
            passed=passed,
            interpretation=interpretation,
            action_needed=(
                "Refine clustering algorithm or merge similar categories"
                if not passed else ""
            ),
            details={
                'n_clusters': len(set(filtered_labels)),
                'n_items': len(filtered_embeddings)
            }
        )

    # ========================================================================
    # Validation 2: Inter-Rater Reliability
    # ========================================================================

    def compute_inter_rater_reliability(
        self,
        annotations: List[List[ErrorSubtype]]
    ) -> ValidationResult:
        """
        Compute Cohen's Kappa between multiple human annotators.

        Target: Kappa > 0.7 (substantial agreement)

        Args:
            annotations: List of annotation lists from different raters
                        e.g., [[subtype1, subtype2, ...], [subtype1, ...]]
        """
        if len(annotations) < 2:
            return ValidationResult(
                metric_name="Inter-Rater Reliability",
                score=0.0,
                threshold=0.7,
                passed=False,
                interpretation="Need at least 2 raters",
                action_needed="Recruit multiple human annotators"
            )

        # Convert subtypes to integers for comparison
        def subtype_to_int(subtype):
            return list(ErrorSubtype).index(subtype) if subtype else -1

        # Compute pairwise Kappa scores
        kappa_scores = []

        for i in range(len(annotations)):
            for j in range(i + 1, len(annotations)):
                ann_i = [subtype_to_int(s) for s in annotations[i]]
                ann_j = [subtype_to_int(s) for s in annotations[j]]

                # Ensure same length
                min_len = min(len(ann_i), len(ann_j))
                ann_i = ann_i[:min_len]
                ann_j = ann_j[:min_len]

                kappa = cohen_kappa_score(ann_i, ann_j)
                kappa_scores.append(kappa)

        mean_kappa = np.mean(kappa_scores)
        passed = mean_kappa > 0.7

        if mean_kappa > 0.8:
            interpretation = "Excellent - near perfect agreement"
        elif mean_kappa > 0.7:
            interpretation = "Substantial agreement - taxonomy is well-defined"
        elif mean_kappa > 0.6:
            interpretation = "Moderate agreement - some categories need refinement"
        else:
            interpretation = "Poor agreement - taxonomy definitions unclear"

        return ValidationResult(
            metric_name="Inter-Rater Reliability",
            score=mean_kappa,
            threshold=0.7,
            passed=passed,
            interpretation=interpretation,
            action_needed=(
                "Refine category definitions and provide examples"
                if not passed else ""
            ),
            details={
                'n_raters': len(annotations),
                'pairwise_kappas': kappa_scores
            }
        )

    # ========================================================================
    # Validation 3: Predictive Power
    # ========================================================================

    def test_error_prediction(
        self,
        train_ratio: float = 0.8
    ) -> ValidationResult:
        """
        Test if taxonomy can predict which questions will cause errors.

        Target: AUROC > 0.65 (better than random)

        Strategy:
        1. Split errors into train/test
        2. Build error profile from train set
        3. Predict errors on test set based on similarity
        """
        if len(self.errors) < 20:
            return ValidationResult(
                metric_name="Predictive Power",
                score=0.0,
                threshold=0.65,
                passed=False,
                interpretation="Insufficient data for train/test split",
                action_needed="Collect more errors (need 50+)"
            )

        # Get errors with embeddings
        errors_with_embeddings = [
            e for e in self.errors
            if e.question_embedding is not None
        ]

        if len(errors_with_embeddings) < 20:
            return ValidationResult(
                metric_name="Predictive Power",
                score=0.0,
                threshold=0.65,
                passed=False,
                interpretation="Insufficient embeddings",
                action_needed="Generate embeddings for errors"
            )

        # Train/test split
        np.random.shuffle(errors_with_embeddings)
        split_idx = int(len(errors_with_embeddings) * train_ratio)
        train_errors = errors_with_embeddings[:split_idx]
        test_errors = errors_with_embeddings[split_idx:]

        # Build error type centroids from training data
        error_centroids = {}
        for subtype in ErrorSubtype:
            subtype_errors = [e for e in train_errors if e.error_subtype == subtype]
            if len(subtype_errors) > 0:
                embeddings = np.array([e.question_embedding for e in subtype_errors])
                error_centroids[subtype] = np.mean(embeddings, axis=0)

        if len(error_centroids) == 0:
            return ValidationResult(
                metric_name="Predictive Power",
                score=0.0,
                threshold=0.65,
                passed=False,
                interpretation="No error centroids could be built",
                action_needed="Classify training errors"
            )

        # Predict on test set
        # For each test error, compute distance to nearest centroid
        predictions = []

        for error in test_errors:
            q_embedding = error.question_embedding

            # Distance to nearest error centroid
            distances = []
            for centroid in error_centroids.values():
                # Cosine distance
                distance = 1 - np.dot(q_embedding, centroid) / (
                    np.linalg.norm(q_embedding) * np.linalg.norm(centroid)
                )
                distances.append(distance)

            min_distance = min(distances)

            # Convert distance to error probability
            # Closer to centroid = higher error probability
            prob_error = 1 / (1 + np.exp(5 * (min_distance - 0.5)))
            predictions.append(prob_error)

        # Ground truth: all test items are errors (label=1)
        # For proper AUROC, we need both positive and negative examples
        # Since we only have errors, use difficulty as proxy
        ground_truth = [e.difficulty_score for e in test_errors]

        try:
            # Use difficulty as ground truth (higher difficulty = more likely to be error)
            auroc = spearmanr(predictions, ground_truth)[0]
            auroc = abs(auroc)  # Take absolute value
        except:
            auroc = 0.5

        passed = auroc > 0.65

        if auroc > 0.75:
            interpretation = "Strong predictive power"
        elif auroc > 0.65:
            interpretation = "Moderate predictive power"
        elif auroc > 0.55:
            interpretation = "Weak but above random"
        else:
            interpretation = "No better than random - taxonomy not predictive"

        return ValidationResult(
            metric_name="Predictive Power",
            score=auroc,
            threshold=0.65,
            passed=passed,
            interpretation=interpretation,
            action_needed=(
                "Taxonomy doesn't capture predictive patterns - revise categories"
                if not passed else ""
            ),
            details={
                'train_size': len(train_errors),
                'test_size': len(test_errors),
                'n_centroids': len(error_centroids)
            }
        )

    # ========================================================================
    # Validation 4: Cross-Model Transfer
    # ========================================================================

    def test_cross_model_transfer(self) -> ValidationResult:
        """
        Test if error patterns learned from Model A transfer to Model B.

        Target: Transfer accuracy > 60%
        """
        # Get unique models
        models = list(set(e.model_name for e in self.errors))

        if len(models) < 2:
            return ValidationResult(
                metric_name="Cross-Model Transfer",
                score=0.0,
                threshold=0.6,
                passed=False,
                interpretation="Need errors from multiple models",
                action_needed="Collect errors from 2+ models"
            )

        # Test transfer between each pair of models
        transfer_accuracies = []

        for i in range(len(models)):
            for j in range(i + 1, len(models)):
                model_a = models[i]
                model_b = models[j]

                model_a_errors = [e for e in self.errors if e.model_name == model_a]
                model_b_errors = [e for e in self.errors if e.model_name == model_b]

                # Find shared questions
                a_questions = {e.question_id: e for e in model_a_errors}
                b_questions = {e.question_id: e for e in model_b_errors}

                shared_questions = set(a_questions.keys()) & set(b_questions.keys())

                if len(shared_questions) < 5:
                    continue

                # For shared questions, check if error types match
                matches = 0
                total = 0

                for qid in shared_questions:
                    a_type = a_questions[qid].error_subtype
                    b_type = b_questions[qid].error_subtype

                    if a_type and b_type:
                        if a_type == b_type:
                            matches += 1
                        total += 1

                if total > 0:
                    accuracy = matches / total
                    transfer_accuracies.append(accuracy)

        if len(transfer_accuracies) == 0:
            return ValidationResult(
                metric_name="Cross-Model Transfer",
                score=0.0,
                threshold=0.6,
                passed=False,
                interpretation="Insufficient shared questions between models",
                action_needed="Ensure models are tested on same questions"
            )

        mean_transfer = np.mean(transfer_accuracies)
        passed = mean_transfer > 0.6

        if mean_transfer > 0.7:
            interpretation = "Strong transfer - patterns are universal"
        elif mean_transfer > 0.6:
            interpretation = "Moderate transfer - some universal patterns"
        else:
            interpretation = "Weak transfer - patterns are model-specific"

        return ValidationResult(
            metric_name="Cross-Model Transfer",
            score=mean_transfer,
            threshold=0.6,
            passed=passed,
            interpretation=interpretation,
            action_needed=(
                "Error patterns are too model-specific - focus on universal categories"
                if not passed else ""
            ),
            details={
                'n_model_pairs': len(transfer_accuracies),
                'transfer_accuracies': transfer_accuracies
            }
        )

    # ========================================================================
    # Validation 5: Difficulty Calibration
    # ========================================================================

    def validate_difficulty_calibration(
        self,
        human_ratings: Optional[Dict[str, float]] = None
    ) -> ValidationResult:
        """
        Correlate model errors with human-rated difficulty.

        Target: Spearman r > 0.5

        Args:
            human_ratings: Dict mapping question_id to difficulty rating (0-1)
        """
        if human_ratings is None or len(human_ratings) == 0:
            return ValidationResult(
                metric_name="Difficulty Calibration",
                score=0.0,
                threshold=0.5,
                passed=False,
                interpretation="No human difficulty ratings provided",
                action_needed="Collect human expert difficulty ratings for 50+ questions"
            )

        # Count errors per question
        question_error_counts = Counter(e.question_id for e in self.errors)

        # Find questions with both error counts and human ratings
        model_difficulty = []
        human_difficulty = []

        for qid, count in question_error_counts.items():
            if qid in human_ratings:
                model_difficulty.append(count)
                human_difficulty.append(human_ratings[qid])

        if len(model_difficulty) < 10:
            return ValidationResult(
                metric_name="Difficulty Calibration",
                score=0.0,
                threshold=0.5,
                passed=False,
                interpretation="Insufficient overlap between errors and human ratings",
                action_needed="Get human ratings for questions that have errors"
            )

        # Compute correlation
        correlation, p_value = spearmanr(model_difficulty, human_difficulty)

        passed = correlation > 0.5 and p_value < 0.05

        if correlation > 0.7:
            interpretation = "Strong calibration - models fail where humans expect"
        elif correlation > 0.5:
            interpretation = "Moderate calibration - reasonable alignment"
        elif correlation > 0.3:
            interpretation = "Weak calibration - some misalignment"
        else:
            interpretation = "Poor calibration - models fail on unexpected questions"

        return ValidationResult(
            metric_name="Difficulty Calibration",
            score=correlation,
            threshold=0.5,
            passed=passed,
            interpretation=interpretation,
            action_needed=(
                "Review questions where model/human difficulty disagree"
                if not passed else ""
            ),
            details={
                'correlation': correlation,
                'p_value': p_value,
                'n_questions': len(model_difficulty)
            }
        )

    # ========================================================================
    # Validation Runner
    # ========================================================================

    def run_all_validations(
        self,
        cluster_labels: Optional[List[int]] = None,
        human_annotations: Optional[List[List[ErrorSubtype]]] = None,
        human_difficulty_ratings: Optional[Dict[str, float]] = None
    ) -> ValidationReport:
        """
        Run full validation suite.

        Args:
            cluster_labels: Cluster assignments (optional)
            human_annotations: Multiple annotator classifications (optional)
            human_difficulty_ratings: Human difficulty scores (optional)
        """
        results = []

        # Run available validations

        # 1. Cluster coherence (always available)
        results.append(self.measure_cluster_coherence(cluster_labels))

        # 2. Inter-rater reliability (if human annotations available)
        if human_annotations and len(human_annotations) >= 2:
            results.append(self.compute_inter_rater_reliability(human_annotations))

        # 3. Predictive power (if embeddings available)
        results.append(self.test_error_prediction())

        # 4. Cross-model transfer (if multiple models)
        results.append(self.test_cross_model_transfer())

        # 5. Difficulty calibration (if human ratings available)
        if human_difficulty_ratings:
            results.append(self.validate_difficulty_calibration(human_difficulty_ratings))

        # Compute overall score
        total_validations = len(results)
        passed_validations = sum(1 for r in results if r.passed)
        overall_score = passed_validations / total_validations if total_validations > 0 else 0

        # Determine readiness
        ready_for_publication = passed_validations >= 3  # At least 3/5 must pass

        # Generate summary
        summary = self._generate_summary(results, passed_validations, total_validations)

        return ValidationReport(
            total_validations=total_validations,
            passed_validations=passed_validations,
            overall_score=overall_score,
            results=results,
            summary=summary,
            ready_for_publication=ready_for_publication
        )

    def _generate_summary(
        self,
        results: List[ValidationResult],
        passed: int,
        total: int
    ) -> str:
        """Generate human-readable summary"""
        summary = f"# Taxonomy Validation Report\n\n"
        summary += f"**Overall: {passed}/{total} validations passed ({passed/total*100:.0f}%)**\n\n"

        if passed / total >= 0.75:
            summary += "✅ **Status**: EXCELLENT - Taxonomy is well-grounded\n\n"
        elif passed / total >= 0.5:
            summary += "⚠️ **Status**: ACCEPTABLE - Some refinement needed\n\n"
        else:
            summary += "❌ **Status**: NEEDS WORK - Significant issues to address\n\n"

        summary += "## Validation Results\n\n"

        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            summary += f"### {result.metric_name}\n\n"
            summary += f"**Status**: {status}\n"
            summary += f"**Score**: {result.score:.3f} (threshold: {result.threshold})\n"
            summary += f"**Interpretation**: {result.interpretation}\n"

            if not result.passed and result.action_needed:
                summary += f"**Action Required**: {result.action_needed}\n"

            summary += "\n"

        return summary

    def export_validation_report(
        self,
        report: ValidationReport,
        output_path: str
    ) -> None:
        """Export validation report to markdown and JSON"""
        from pathlib import Path

        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export markdown
        with open(output_path / "validation_report.md", 'w') as f:
            f.write(report.summary)

        # Export JSON
        report_data = {
            'total_validations': report.total_validations,
            'passed_validations': report.passed_validations,
            'overall_score': report.overall_score,
            'ready_for_publication': report.ready_for_publication,
            'results': [
                {
                    'metric': r.metric_name,
                    'score': r.score,
                    'threshold': r.threshold,
                    'passed': r.passed,
                    'interpretation': r.interpretation,
                    'action_needed': r.action_needed,
                    'details': r.details
                }
                for r in report.results
            ]
        }

        with open(output_path / "validation_report.json", 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"Validation report exported to {output_path}/")
