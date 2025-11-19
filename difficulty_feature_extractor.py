#!/usr/bin/env python3
"""
Difficulty Feature Extractor
=============================

Extract features from questions that correlate with difficulty,
going beyond semantic similarity.

Feature categories:
1. Syntactic complexity (length, clauses, nesting)
2. Numerical complexity (numbers, equations, units)
3. Semantic abstraction (technical terms, proof words)
4. Domain-specific patterns
5. Answer choice complexity (if available)
"""

import re
import numpy as np
from typing import Dict, List, Optional
from collections import Counter


class DifficultyFeatureExtractor:
    """Extract difficulty-predictive features from question text"""

    # Domain-specific technical term dictionaries
    TECHNICAL_TERMS = {
        'math': ['eigenvalue', 'eigenvector', 'derivative', 'integral', 'theorem', 'proof',
                 'lemma', 'corollary', 'bijection', 'isomorphism', 'homomorphism'],
        'physics': ['quantum', 'thermodynamic', 'lagrangian', 'hamiltonian', 'momentum',
                   'entropy', 'partition function', 'wave function', 'uncertainty'],
        'chemistry': ['stoichiometry', 'equilibrium', 'reaction mechanism', 'orbital',
                     'electronegativity', 'ionization', 'thermochemistry'],
        'biology': ['phylogenetic', 'genotype', 'phenotype', 'metabolism', 'enzyme',
                   'chromosome', 'transcription', 'translation'],
        'cs': ['algorithm', 'complexity', 'recursion', 'dynamic programming', 'hash table',
              'binary tree', 'graph', 'NP-complete', 'big-O']
    }

    PROOF_KEYWORDS = [
        'prove', 'show that', 'demonstrate', 'derive', 'establish',
        'verify', 'justify', 'proof', 'q.e.d', 'therefore'
    ]

    MULTI_STEP_INDICATORS = [
        'first.*then', 'step 1.*step 2', 'calculate.*and then',
        'multi-step', 'sequential', 'in order'
    ]

    ABSTRACT_WORDS = [
        'concept', 'principle', 'theory', 'philosophy', 'paradigm',
        'framework', 'methodology', 'approach', 'perspective'
    ]

    def __init__(self):
        """Initialize feature extractor"""
        # Compile regex patterns
        self.proof_patterns = [re.compile(kw, re.IGNORECASE) for kw in self.PROOF_KEYWORDS]
        self.multi_step_patterns = [re.compile(ind, re.IGNORECASE) for ind in self.MULTI_STEP_INDICATORS]
        self.abstract_patterns = [re.compile(word, re.IGNORECASE) for word in self.ABSTRACT_WORDS]

    def extract_features(self, question: Dict) -> Dict[str, float]:
        """
        Extract all features from a question

        Args:
            question: Dict with 'question_text', 'domain', optionally 'options'

        Returns:
            Dict of feature_name -> feature_value
        """
        text = question['question_text']
        domain = question.get('domain', 'unknown').lower()
        options = question.get('options', [])

        features = {}

        # ===== 1. SYNTACTIC COMPLEXITY =====
        features.update(self._extract_syntactic_features(text))

        # ===== 2. NUMERICAL COMPLEXITY =====
        features.update(self._extract_numerical_features(text))

        # ===== 3. SEMANTIC FEATURES =====
        features.update(self._extract_semantic_features(text, domain))

        # ===== 4. STRUCTURAL FEATURES =====
        features.update(self._extract_structural_features(text))

        # ===== 5. ANSWER CHOICE FEATURES =====
        if options:
            features.update(self._extract_option_features(options))

        # ===== 6. DOMAIN INDICATORS =====
        features[f'domain_{domain}'] = 1.0

        return features

    def _extract_syntactic_features(self, text: str) -> Dict[str, float]:
        """Extract syntactic complexity features"""
        words = text.split()
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

        return {
            # Length-based
            'question_length_words': len(words),
            'question_length_chars': len(text),
            'avg_word_length': np.mean([len(w) for w in words]) if words else 0,

            # Sentence complexity
            'num_sentences': len(sentences),
            'avg_sentence_length': len(words) / len(sentences) if sentences else 0,

            # Punctuation density (indicates complexity)
            'comma_count': text.count(','),
            'semicolon_count': text.count(';'),
            'colon_count': text.count(':'),
            'parenthesis_count': text.count('(') + text.count(')'),
            'bracket_count': text.count('[') + text.count(']'),

            # Clause complexity
            'clause_density': (text.count(',') + text.count(';')) / len(words) if words else 0,

            # Capital letters (acronyms, proper nouns)
            'capital_ratio': sum(1 for c in text if c.isupper()) / len(text) if text else 0,
        }

    def _extract_numerical_features(self, text: str) -> Dict[str, float]:
        """Extract numerical complexity features"""
        # Find all numbers
        numbers = re.findall(r'\d+\.?\d*', text)

        # Find scientific notation (e.g., 2.5×10^6)
        sci_notation = re.findall(r'\d+\.?\d*\s*[×x]\s*10\^?[-\d]+', text)

        # Find equations (= signs, inequalities)
        equations = re.findall(r'[=<>≤≥≠]', text)

        # Find mathematical symbols
        math_symbols = re.findall(r'[∂∫∑∏√±×÷≠≈≤≥∞∇⊗⊕]', text)

        # Find units
        units = re.findall(r'\b(kg|lb|m|ft|cm|mm|°C|°F|K|J|cal|BTU|MPa|psi|mol|Hz|V|A|W)\b', text)

        # Find fractions
        fractions = re.findall(r'\d+/\d+', text)

        # Find percentages
        percentages = re.findall(r'\d+\.?\d*\s*%', text)

        return {
            'num_numbers': len(numbers),
            'num_sci_notation': len(sci_notation),
            'num_equations': len(equations),
            'num_math_symbols': len(math_symbols),
            'num_units': len(set(units)),  # Unique units
            'num_fractions': len(fractions),
            'num_percentages': len(percentages),

            # Density metrics
            'number_density': len(numbers) / len(text.split()) if text.split() else 0,
            'equation_density': len(equations) / len(text.split()) if text.split() else 0,

            # Multiple unit types (indicates unit conversion)
            'has_unit_conversion': 1.0 if len(set(units)) >= 2 else 0.0,

            # Complex numbers (3+ numbers)
            'has_multiple_numbers': 1.0 if len(numbers) >= 3 else 0.0,
        }

    def _extract_semantic_features(self, text: str, domain: str) -> Dict[str, float]:
        """Extract semantic abstraction features"""
        text_lower = text.lower()

        # Proof-based question
        has_proof = any(pattern.search(text) for pattern in self.proof_patterns)

        # Multi-step complexity
        has_multi_step = any(pattern.search(text) for pattern in self.multi_step_patterns)

        # Abstract language
        abstract_count = sum(1 for pattern in self.abstract_patterns if pattern.search(text))

        # Technical term density
        technical_terms = self.TECHNICAL_TERMS.get(domain, [])
        tech_term_count = sum(1 for term in technical_terms if term in text_lower)

        # Vocabulary sophistication (word length as proxy)
        words = text_lower.split()
        long_words = [w for w in words if len(w) > 8]

        return {
            'has_proof_language': 1.0 if has_proof else 0.0,
            'has_multi_step': 1.0 if has_multi_step else 0.0,
            'abstract_word_count': abstract_count,
            'technical_term_count': tech_term_count,
            'technical_term_density': tech_term_count / len(words) if words else 0,
            'long_word_count': len(long_words),
            'long_word_ratio': len(long_words) / len(words) if words else 0,
        }

    def _extract_structural_features(self, text: str) -> Dict[str, float]:
        """Extract question structure features"""
        # Question marks (multiple questions)
        num_questions = text.count('?')

        # Enumeration (a), b), c), ...)
        enumeration_patterns = [
            r'\b[a-e]\)',
            r'\([a-e]\)',
            r'\b[ivx]+\)',
            r'\([ivx]+\)',
            r'part [a-e]',
        ]
        enum_count = sum(len(re.findall(pattern, text.lower())) for pattern in enumeration_patterns)

        # Given/find structure (indicates multi-step)
        has_given = bool(re.search(r'\bgiven\b', text.lower()))
        has_find = bool(re.search(r'\bfind\b|\bcalculate\b|\bdetermine\b', text.lower()))

        # Lists (numbered or bulleted)
        has_list = bool(re.search(r'\d+\.|\d+\)', text))

        return {
            'num_question_marks': num_questions,
            'enumeration_count': enum_count,
            'has_multi_part': 1.0 if enum_count >= 2 else 0.0,
            'has_given_find': 1.0 if (has_given and has_find) else 0.0,
            'has_list': 1.0 if has_list else 0.0,
        }

    def _extract_option_features(self, options: List[str]) -> Dict[str, float]:
        """Extract features from answer choices"""
        if not options:
            return {'has_options': 0.0}

        option_lengths = [len(opt) for opt in options]

        return {
            'has_options': 1.0,
            'num_options': len(options),
            'avg_option_length': np.mean(option_lengths),
            'max_option_length': max(option_lengths),
            'option_length_variance': np.var(option_lengths),

            # Long options suggest complex concepts
            'has_long_options': 1.0 if max(option_lengths) > 50 else 0.0,

            # Numeric options
            'has_numeric_options': 1.0 if any(re.search(r'\d', opt) for opt in options) else 0.0,
        }

    def get_feature_names(self) -> List[str]:
        """Get list of all possible feature names"""
        # Create dummy question to extract feature names
        dummy = {
            'question_text': 'What is the eigenvalue of this matrix A = [[1,2],[3,4]]?',
            'domain': 'math',
            'options': ['1', '2', '3', '4']
        }

        features = self.extract_features(dummy)
        return sorted(features.keys())

    def extract_batch(self, questions: List[Dict]) -> np.ndarray:
        """
        Extract features for a batch of questions

        Returns:
            np.ndarray of shape (n_questions, n_features)
        """
        feature_dicts = [self.extract_features(q) for q in questions]

        # Get all feature names
        all_feature_names = self.get_feature_names()

        # Convert to matrix
        X = np.zeros((len(questions), len(all_feature_names)))

        for i, feat_dict in enumerate(feature_dicts):
            for j, feat_name in enumerate(all_feature_names):
                X[i, j] = feat_dict.get(feat_name, 0.0)

        return X, all_feature_names


if __name__ == "__main__":
    print("="*80)
    print("DIFFICULTY FEATURE EXTRACTOR - DEMO")
    print("="*80)

    extractor = DifficultyFeatureExtractor()

    # Test questions
    test_questions = [
        {
            'question_text': 'What is 2+2?',
            'domain': 'math',
            'options': ['1', '2', '3', '4']
        },
        {
            'question_text': 'Prove that the eigenvalues of a Hermitian matrix are real.',
            'domain': 'math',
            'options': []
        },
        {
            'question_text': 'Given T_i = 35°C and P = 2.5×10^6 Pa, calculate the final entropy change when 200 kg of water undergoes an isothermal expansion.',
            'domain': 'physics',
            'options': []
        },
        {
            'question_text': 'Which of the following best describes the principle of natural selection?',
            'domain': 'biology',
            'options': [
                'Organisms adapt to their environment through conscious effort',
                'Random mutations provide variation, and advantageous traits are more likely to be passed on',
                'All organisms evolve at the same rate',
                'Evolution only occurs in isolated populations'
            ]
        }
    ]

    for i, q in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}")
        print(f"{'='*80}")
        print(f"\nQuestion: {q['question_text'][:100]}...")
        print(f"Domain: {q['domain']}")

        features = extractor.extract_features(q)

        print(f"\n📊 EXTRACTED FEATURES (top 15):")
        # Sort by value descending
        sorted_features = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)

        for feat_name, feat_value in sorted_features[:15]:
            if feat_value != 0:
                print(f"   {feat_name:<30} {feat_value:>10.2f}")

    # Feature names
    print(f"\n{'='*80}")
    print(f"TOTAL FEATURES: {len(extractor.get_feature_names())}")
    print(f"{'='*80}")
    print("\nFeature categories:")
    print("  • Syntactic complexity: length, punctuation, clauses")
    print("  • Numerical complexity: numbers, equations, units")
    print("  • Semantic abstraction: technical terms, proof words")
    print("  • Structural: multi-part, given/find, enumeration")
    print("  • Answer choices: length, variance, numeric")
    print("  • Domain indicators: one-hot encoding")

    print("\n" + "="*80)
    print("✅ Feature extraction complete!")
    print("="*80)
