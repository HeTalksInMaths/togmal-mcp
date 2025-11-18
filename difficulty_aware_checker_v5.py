#!/usr/bin/env python3
"""
Difficulty-Aware Checker V5
===========================

Predicts question difficulty using:
1. Domain-based difficulty (from MCP statistics)
2. Complexity analysis (math, technical terms, multi-step)
3. Similarity-based prediction (from ChromaDB)

All hyperparameters are tunable via grid search.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import defaultdict

from complexity_analyzer import ComplexityAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DifficultyAwareChecker:
    """V5 checker with tunable hyperparameters"""

    def __init__(
        self,
        # Feature weights (must sum to 1.0)
        domain_weight: float = 0.40,
        complexity_weight: float = 0.30,
        similarity_weight: float = 0.30,

        # Difficulty thresholds
        high_risk_threshold: float = 0.70,
        medium_risk_threshold: float = 0.40,

        # Complexity feature weights
        math_notation_weight: float = 1.0,
        technical_terms_weight: float = 1.0,
        multi_step_bonus: float = 0.15,
        proof_bonus: float = 0.20,

        # Similarity parameters
        num_neighbors: int = 5,
        min_similarity_threshold: float = 0.5,

        # Data paths
        statistics_path: Path = Path("./mcp_datastore/statistics.json"),
        chroma_db_path: Optional[Path] = Path("./chroma_db"),
    ):
        """Initialize with tunable hyperparameters"""

        # Store hyperparameters
        self.domain_weight = domain_weight
        self.complexity_weight = complexity_weight
        self.similarity_weight = similarity_weight

        self.high_risk_threshold = high_risk_threshold
        self.medium_risk_threshold = medium_risk_threshold

        self.math_notation_weight = math_notation_weight
        self.technical_terms_weight = technical_terms_weight
        self.multi_step_bonus = multi_step_bonus
        self.proof_bonus = proof_bonus

        self.num_neighbors = num_neighbors
        self.min_similarity_threshold = min_similarity_threshold

        # Validate weights sum to 1.0
        weight_sum = domain_weight + complexity_weight + similarity_weight
        if not np.isclose(weight_sum, 1.0, atol=0.01):
            logger.warning(f"Feature weights sum to {weight_sum:.3f}, normalizing...")
            self.domain_weight /= weight_sum
            self.complexity_weight /= weight_sum
            self.similarity_weight /= weight_sum

        # Load domain statistics
        self.domain_stats = self._load_domain_statistics(statistics_path)

        # Initialize complexity analyzer
        self.complexity_analyzer = ComplexityAnalyzer()

        # Initialize ChromaDB (optional, for similarity-based features)
        # DISABLED for now due to ONNX embedding issues in Claude Code web
        self.chroma_client = None
        self.chroma_collection = None
        # if chroma_db_path and chroma_db_path.exists():
        #     try:
        #         import chromadb
        #         from chromadb.config import Settings

        #         self.chroma_client = chromadb.PersistentClient(
        #             path=str(chroma_db_path),
        #             settings=Settings(anonymized_telemetry=False)
        #         )
        #         self.chroma_collection = self.chroma_client.get_collection("togmal_benchmarks")
        #         logger.info(f"✅ Loaded ChromaDB with {self.chroma_collection.count():,} questions")
        #     except Exception as e:
        #         logger.warning(f"ChromaDB not available: {e}")
        logger.info("ChromaDB disabled for fast evaluation (similarity features use default 0.5)")

        # Domain name normalization
        self.domain_mapping = {
            'pandas': 'Pandas',
            'numpy': 'Numpy',
            'matplotlib': 'Matplotlib',
            'tensorflow': 'Tensorflow',
            'scipy': 'Scipy',
            'sklearn': 'Sklearn',
            'pytorch': 'Pytorch',
        }

    def _load_domain_statistics(self, path: Path) -> Dict:
        """Load domain statistics - compute from unified database"""

        # Load unified database to compute domain stats
        db_path = Path("./data/unified_database_complete.json")
        if not db_path.exists():
            logger.warning(f"Unified database not found: {db_path}")
            return {}

        with open(db_path, 'r') as f:
            data = json.load(f)

        # Compute per-domain difficulty scores
        domain_scores = defaultdict(list)

        for q in data['questions']:
            domain = q.get('domain', 'unknown')
            difficulty = q.get('difficulty_score', 0.5)
            domain_scores[domain].append(difficulty)

        # Average per domain
        domain_avg = {}
        for domain, scores in domain_scores.items():
            domain_avg[domain] = np.mean(scores)

        logger.info(f"✅ Loaded statistics for {len(domain_avg)} domains")
        return domain_avg

    def quick_check(self, question: str, context: Optional[Dict] = None) -> Dict:
        """Main prediction method - matches V3 API"""

        # 1. Domain-based difficulty
        domain_score = self._get_domain_difficulty(question, context)

        # 2. Complexity-based difficulty
        complexity_result = self.complexity_analyzer.analyze(question)
        complexity_score = self._compute_weighted_complexity(complexity_result)

        # 3. Similarity-based difficulty
        similarity_score = self._get_similarity_difficulty(question)

        # Combine scores with learned weights
        final_score = (
            self.domain_weight * domain_score +
            self.complexity_weight * complexity_score +
            self.similarity_weight * similarity_score
        )

        # Apply bonuses
        if complexity_result['features']['is_multi_step']:
            final_score += self.multi_step_bonus
        if complexity_result['features']['requires_proof']:
            final_score += self.proof_bonus

        # Clamp to [0, 1]
        final_score = np.clip(final_score, 0.0, 1.0)

        # Determine risk level based on thresholds
        if final_score >= self.high_risk_threshold:
            risk_level = 'HIGH_RISK'
        elif final_score >= self.medium_risk_threshold:
            risk_level = 'MEDIUM_RISK'
        else:
            risk_level = 'LOW_RISK'

        # Compute confidence
        confidence = self._compute_confidence(domain_score, complexity_score, similarity_score)

        return {
            'risk_level': risk_level,
            'risk_score': final_score,
            'confidence': confidence,
            'components': {
                'domain_score': domain_score,
                'complexity_score': complexity_score,
                'similarity_score': similarity_score,
            },
            'complexity_details': complexity_result,
            'explanation': self._generate_explanation(
                risk_level, domain_score, complexity_score, similarity_score, complexity_result
            )
        }

    def _get_domain_difficulty(self, question: str, context: Optional[Dict] = None) -> float:
        """Get domain-based difficulty score"""

        # Try to get domain from context first
        domain = None
        if context and 'domain' in context:
            domain = context['domain']
        else:
            # Simple domain detection from question text
            domain = self._detect_domain(question)

        if domain and domain in self.domain_stats:
            return self.domain_stats[domain]

        # Default to medium difficulty if domain unknown
        return 0.5

    def _detect_domain(self, question: str) -> Optional[str]:
        """Simple domain detection from question text"""
        question_lower = question.lower()

        # Check for data science libraries
        for lib in ['pandas', 'numpy', 'matplotlib', 'tensorflow', 'scipy', 'sklearn', 'pytorch']:
            if lib in question_lower:
                return self.domain_mapping.get(lib, lib)

        # Check for domain keywords
        domain_keywords = {
            'quantum': ['quantum', 'qubit', 'entanglement', 'superposition'],
            'chemistry': ['molecule', 'chemical', 'reaction', 'compound'],
            'biology': ['cell', 'gene', 'protein', 'organism', 'dna'],
            'physics': ['force', 'energy', 'momentum', 'particle'],
            'math': ['theorem', 'proof', 'equation', 'matrix', 'integral'],
            'law': ['legal', 'court', 'statute', 'jurisdiction'],
            'economics': ['market', 'price', 'demand', 'supply', 'gdp'],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in question_lower for kw in keywords):
                return domain

        return None

    def _compute_weighted_complexity(self, complexity_result: Dict) -> float:
        """Compute weighted complexity score"""

        # Apply learned weights to complexity components
        weighted_score = (
            self.math_notation_weight * complexity_result['math_notation_score'] +
            self.technical_terms_weight * complexity_result['technical_term_score'] +
            0.8 * complexity_result['multi_step_score'] +
            0.6 * complexity_result['proof_requirement_score'] +
            0.4 * complexity_result['conceptual_complexity_score'] +
            0.2 * complexity_result['length_score']
        )

        # Normalize (weights don't sum to 1)
        total_weight = (
            self.math_notation_weight +
            self.technical_terms_weight +
            0.8 + 0.6 + 0.4 + 0.2
        )

        return weighted_score / total_weight

    def _get_similarity_difficulty(self, question: str) -> float:
        """Get difficulty from similar questions"""

        if not self.chroma_collection:
            return 0.5  # Default if ChromaDB not available

        try:
            # Search for similar questions
            results = self.chroma_collection.query(
                query_texts=[question],
                n_results=self.num_neighbors,
                include=['metadatas', 'distances']
            )

            if not results['metadatas'] or not results['metadatas'][0]:
                return 0.5

            # Extract difficulty scores from similar questions
            difficulties = []
            distances = results['distances'][0]

            for metadata, distance in zip(results['metadatas'][0], distances):
                # Convert distance to similarity
                similarity = 1 - distance

                # Only use sufficiently similar questions
                if similarity >= self.min_similarity_threshold:
                    # Use difficulty_score (1 - success_rate)
                    difficulty = metadata.get('difficulty_score', 0.5)
                    difficulties.append(difficulty)

            if difficulties:
                # Weighted average (closer questions have more weight)
                return np.mean(difficulties)
            else:
                return 0.5

        except Exception as e:
            logger.warning(f"Similarity search failed: {e}")
            return 0.5

    def _compute_confidence(
        self,
        domain_score: float,
        complexity_score: float,
        similarity_score: float
    ) -> float:
        """Compute confidence in the prediction"""

        # If all components agree (low variance), confidence is high
        scores = [domain_score, complexity_score, similarity_score]
        variance = np.var(scores)

        # Low variance → high confidence
        confidence = 1.0 - min(variance * 4, 1.0)  # Scale factor 4

        # Bonus if ChromaDB available (more reliable)
        if self.chroma_collection:
            confidence = min(confidence * 1.1, 1.0)

        return confidence

    def _generate_explanation(
        self,
        risk_level: str,
        domain_score: float,
        complexity_score: float,
        similarity_score: float,
        complexity_result: Dict
    ) -> str:
        """Generate human-readable explanation"""

        explanations = []

        # Risk level
        explanations.append(f"Predicted difficulty: {risk_level}")

        # Component contributions
        if domain_score > 0.6:
            explanations.append(f"Domain difficulty is high ({domain_score:.2f})")
        if complexity_score > 0.6:
            explanations.append(f"Question complexity is high ({complexity_score:.2f})")
        if similarity_score > 0.6:
            explanations.append(f"Similar questions are difficult ({similarity_score:.2f})")

        # Specific features
        if complexity_result['features']['has_math_notation']:
            explanations.append("Contains mathematical notation")
        if complexity_result['features']['is_multi_step']:
            explanations.append("Requires multi-step reasoning")
        if complexity_result['features']['requires_proof']:
            explanations.append("Requires formal proof")

        # Technical terms
        tech_details = complexity_result['technical_term_details']
        if tech_details['total_terms'] > 0:
            categories = list(tech_details['category_counts'].keys())
            explanations.append(f"Contains {tech_details['total_terms']} technical terms ({', '.join(categories)})")

        return " | ".join(explanations)


def test_v5_checker():
    """Test V5 difficulty-aware checker"""

    print("\n" + "="*80)
    print("Difficulty-Aware Checker V5 - Test")
    print("="*80)

    # Initialize checker with default hyperparameters
    checker = DifficultyAwareChecker()

    test_cases = [
        "What is 2 + 2?",
        "Calculate the eigenvalues of the matrix [[1, 2], [3, 4]].",
        "Prove that the Hamiltonian operator is Hermitian and discuss the implications for quantum measurement theory.",
        "Given a quantum system in a superposition state, first calculate the density matrix, then determine the entanglement entropy, and finally prove that it satisfies the von Neumann entropy bound.",
        "Write pandas code to filter a dataframe where age > 30.",
        "Implement a dynamic programming solution for the longest common subsequence problem with O(n*m) time complexity.",
    ]

    for i, question in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}: {question[:60]}...")
        print('='*80)

        result = checker.quick_check(question)

        print(f"\nRisk Level: {result['risk_level']}")
        print(f"Risk Score: {result['risk_score']:.3f}")
        print(f"Confidence: {result['confidence']:.3f}")
        print(f"\nComponent Scores:")
        print(f"  - Domain:     {result['components']['domain_score']:.3f}")
        print(f"  - Complexity: {result['components']['complexity_score']:.3f}")
        print(f"  - Similarity: {result['components']['similarity_score']:.3f}")
        print(f"\nExplanation: {result['explanation']}")


if __name__ == "__main__":
    test_v5_checker()
