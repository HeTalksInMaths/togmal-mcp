#!/usr/bin/env python3
"""
Complexity Analyzer for Academic Questions
==========================================

Extracts features that predict question difficulty:
- Mathematical notation density
- Technical term count
- Multi-step reasoning indicators
- Proof requirements
- Domain-specific complexity
"""

import re
import logging
from typing import Dict, List, Tuple
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComplexityAnalyzer:
    """Analyzes question complexity across multiple dimensions"""

    def __init__(self):
        # Math notation patterns
        self.math_patterns = {
            'equations': [
                r'\$.*?\$',  # LaTeX inline
                r'\\\(.*?\\\)',  # LaTeX display
                r'\\frac\{.*?\}\{.*?\}',  # Fractions
                r'\\sqrt\{.*?\}',  # Square roots
                r'\\int.*?d[xyz]',  # Integrals
                r'\\sum.*?',  # Summations
                r'\\prod.*?',  # Products
                r'\\lim.*?',  # Limits
                r'\\partial',  # Partial derivatives
                r'\\nabla',  # Del operator
            ],
            'operators': [r'[+\-*/=<>≤≥≠≈∈∉⊂⊃∩∪∀∃]'],
            'greek_letters': [r'\\[a-z]+(?:alpha|beta|gamma|delta|epsilon|theta|lambda|mu|sigma|omega)'],
            'matrices': [r'\\begin\{(matrix|bmatrix|pmatrix)\}', r'\[.*?\].*?\[.*?\]'],
        }

        # Technical term categories
        self.technical_terms = {
            'advanced_math': [
                'eigenvalue', 'eigenvector', 'determinant', 'jacobian', 'hessian',
                'lagrangian', 'hamiltonian', 'manifold', 'topology', 'homeomorphism',
                'isomorphism', 'homomorphism', 'functor', 'tensor', 'quaternion',
                'geodesic', 'curvature', 'differential form', 'cohomology',
                'spectral', 'hermitian', 'unitary', 'orthogonal', 'symplectic'
            ],
            'quantum_physics': [
                'quantum', 'entanglement', 'superposition', 'wave function', 'hamiltonian',
                'schrodinger', 'heisenberg', 'uncertainty', 'eigenstate', 'qubit',
                'decoherence', 'measurement', 'bell state', 'hilbert space',
                'density matrix', 'pauli', 'fermion', 'boson', 'bra-ket'
            ],
            'theoretical_cs': [
                'np-complete', 'np-hard', 'undecidable', 'turing machine', 'complexity class',
                'polynomial time', 'exponential time', 'reduction', 'halting problem',
                'big-o', 'theta', 'omega', 'amortized', 'randomized algorithm'
            ],
            'abstract_math': [
                'proof', 'theorem', 'lemma', 'corollary', 'axiom', 'induction',
                'contradiction', 'contrapositive', 'iff', 'necessary and sufficient',
                'bijection', 'surjection', 'injection', 'cardinality'
            ],
            'advanced_programming': [
                'recursion', 'memoization', 'dynamic programming', 'backtracking',
                'tree traversal', 'graph algorithm', 'heap', 'trie', 'segment tree',
                'fenwick tree', 'union-find', 'topological sort', 'strongly connected'
            ]
        }

        # Multi-step indicators
        self.multi_step_patterns = [
            r'\b(first|then|next|after|finally|subsequently|therefore)\b',
            r'\b(step \d+|part [a-z]\))',
            r'\b(given|assuming|suppose|let)\b.*\b(find|calculate|determine|prove)\b',
            r'\b(and then|followed by|before|after that)\b',
            r'[;,].*[;,]',  # Multiple clauses
        ]

        # Proof requirement indicators
        self.proof_indicators = [
            r'\bprove\b', r'\bshow that\b', r'\bdemonstrate\b', r'\bderive\b',
            r'\bjustify\b', r'\bverify\b', r'\bestablish\b', r'\bconfirm\b',
            r'\bproof\b', r'\bq\.?e\.?d\b',
        ]

        # Conceptual complexity indicators
        self.conceptual_indicators = [
            r'\bwhy\b', r'\bexplain\b', r'\bcompare\b', r'\bcontrast\b',
            r'\bdiscuss\b', r'\banalyze\b', r'\bevaluate\b', r'\bcritique\b',
            r'\bimplications?\b', r'\bconsequences?\b',
        ]

    def analyze(self, question: str) -> Dict:
        """Analyze question complexity across all dimensions

        Returns:
            Dict with complexity scores and features
        """
        question_lower = question.lower()

        # Math notation analysis
        math_score = self._analyze_math_notation(question)

        # Technical term density
        tech_score, tech_details = self._analyze_technical_terms(question_lower)

        # Multi-step reasoning
        multi_step_score = self._analyze_multi_step(question_lower)

        # Proof requirements
        proof_score = self._analyze_proof_requirements(question_lower)

        # Conceptual complexity
        conceptual_score = self._analyze_conceptual_complexity(question_lower)

        # Question length (normalized)
        length_score = self._analyze_length(question)

        # Overall complexity (weighted combination)
        overall_score = (
            0.25 * math_score +
            0.25 * tech_score +
            0.20 * multi_step_score +
            0.15 * proof_score +
            0.10 * conceptual_score +
            0.05 * length_score
        )

        return {
            'overall_score': min(overall_score, 1.0),  # Clamp to [0, 1]
            'normalized_score': min(overall_score, 1.0),
            'math_notation_score': math_score,
            'technical_term_score': tech_score,
            'multi_step_score': multi_step_score,
            'proof_requirement_score': proof_score,
            'conceptual_complexity_score': conceptual_score,
            'length_score': length_score,
            'technical_term_details': tech_details,
            'features': {
                'has_math_notation': math_score > 0.3,
                'is_multi_step': multi_step_score > 0.5,
                'requires_proof': proof_score > 0.5,
                'is_conceptual': conceptual_score > 0.5,
                'is_long': length_score > 0.5,
            }
        }

    def _analyze_math_notation(self, text: str) -> float:
        """Analyze mathematical notation density"""
        total_matches = 0

        for category, patterns in self.math_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                total_matches += matches

        # Normalize by text length
        words = len(text.split())
        if words == 0:
            return 0.0

        # Score: ratio of math elements to words, scaled
        score = min(total_matches / words, 1.0)

        return score

    def _analyze_technical_terms(self, text: str) -> Tuple[float, Dict]:
        """Analyze technical term density"""
        found_terms = defaultdict(list)
        total_count = 0

        for category, terms in self.technical_terms.items():
            for term in terms:
                if term in text:
                    found_terms[category].append(term)
                    total_count += 1

        # Normalize by text length
        words = len(text.split())
        if words == 0:
            return 0.0, {}

        # Score: ratio of technical terms to words
        score = min(total_count / (words * 0.1), 1.0)  # Scale factor 0.1

        details = {
            'total_terms': total_count,
            'categories': dict(found_terms),
            'category_counts': {cat: len(terms) for cat, terms in found_terms.items()}
        }

        return score, details

    def _analyze_multi_step(self, text: str) -> float:
        """Analyze multi-step reasoning indicators"""
        matches = 0

        for pattern in self.multi_step_patterns:
            matches += len(re.findall(pattern, text, re.IGNORECASE))

        # Score based on number of multi-step indicators
        score = min(matches / 3.0, 1.0)  # 3+ indicators = max score

        return score

    def _analyze_proof_requirements(self, text: str) -> float:
        """Analyze proof requirement indicators"""
        matches = 0

        for pattern in self.proof_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1

        # Score based on presence of proof indicators
        score = min(matches / 2.0, 1.0)  # 2+ indicators = max score

        return score

    def _analyze_conceptual_complexity(self, text: str) -> float:
        """Analyze conceptual complexity indicators"""
        matches = 0

        for pattern in self.conceptual_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1

        # Score based on conceptual indicators
        score = min(matches / 3.0, 1.0)

        return score

    def _analyze_length(self, text: str) -> float:
        """Analyze question length (longer often means harder)"""
        words = len(text.split())

        # Normalize: 0-50 words = 0.0, 200+ words = 1.0
        if words < 50:
            return 0.0
        elif words > 200:
            return 1.0
        else:
            return (words - 50) / 150.0


def test_complexity_analyzer():
    """Test the complexity analyzer"""
    analyzer = ComplexityAnalyzer()

    test_cases = [
        {
            'question': "What is 2 + 2?",
            'expected': 'very_easy'
        },
        {
            'question': "Calculate the eigenvalues of the matrix [[1, 2], [3, 4]].",
            'expected': 'medium'
        },
        {
            'question': "Prove that the Hamiltonian operator is Hermitian and discuss the implications for quantum measurement theory.",
            'expected': 'very_hard'
        },
        {
            'question': "Given a quantum system in a superposition state, first calculate the density matrix, then determine the entanglement entropy, and finally prove that it satisfies the von Neumann entropy bound.",
            'expected': 'extremely_hard'
        },
        {
            'question': "Write pandas code to filter a dataframe where age > 30.",
            'expected': 'easy'
        },
    ]

    print("\n" + "="*80)
    print("Complexity Analyzer Test")
    print("="*80)

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Question: {test['question'][:80]}...")
        print(f"   Expected: {test['expected']}")

        result = analyzer.analyze(test['question'])

        print(f"   Overall Score: {result['overall_score']:.3f}")
        print(f"   - Math Notation: {result['math_notation_score']:.3f}")
        print(f"   - Technical Terms: {result['technical_term_score']:.3f}")
        print(f"   - Multi-Step: {result['multi_step_score']:.3f}")
        print(f"   - Proof Required: {result['proof_requirement_score']:.3f}")
        print(f"   - Conceptual: {result['conceptual_complexity_score']:.3f}")
        print(f"   - Length: {result['length_score']:.3f}")

        if result['technical_term_details']['total_terms'] > 0:
            print(f"   - Technical Terms Found: {result['technical_term_details']['total_terms']}")
            print(f"     Categories: {list(result['technical_term_details']['category_counts'].keys())}")


if __name__ == "__main__":
    from collections import defaultdict
    test_complexity_analyzer()
