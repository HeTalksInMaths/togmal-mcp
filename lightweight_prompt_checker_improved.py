#!/usr/bin/env python3
"""
Lightweight Prompt Risk Checker - IMPROVED VERSION
===================================================

Improvements based on effectiveness testing:
1. ✅ Lowered threshold (0.3 → 0.15) for better recall
2. ✅ Context-aware medical trigger (reduces false positives)
3. ✅ Numerical complexity detection (catches calculation questions)
4. ✅ Question type detection (proof-based, multi-part)
5. ✅ More specific domain triggers (fewer false positives)
6. ✅ Removed/fixed low-accuracy triggers

Expected improvement: Recall 7.9% → 45-55%
"""

import re
from typing import Dict, List, Tuple

class LightweightPromptChecker:
    """Fast pattern-based prompt risk screening - IMPROVED"""

    # Risky code patterns (DS-1000 patterns) - UNCHANGED, these work well
    CODE_RISK_PATTERNS = [
        # Pandas/DataFrame issues
        (r'df\[.*?\]\s*=', 'mutability_risk', 'DataFrame mutation without .copy()'),
        (r'\.groupby\(.*?\)(?!.*reset_index)', 'index_risk', 'groupby without .reset_index()'),
        (r'for\s+\w+\s+in\s+df', 'vectorization_risk', 'for-loop over DataFrame'),
        (r'\.values(?!\()', 'api_deprecation', 'Deprecated .values (use .to_numpy())'),
        (r'\.iloc\[.*?\.loc\[|\.loc\[.*?\.iloc\[', 'indexing_confusion', 'Mixing .loc and .iloc'),

        # General code smells
        (r'eval\(|exec\(', 'code_injection_risk', 'Using eval() or exec()'),
        (r'pickle\.loads?\(', 'deserialization_risk', 'Unsafe pickle deserialization'),
        (r'__import__\(', 'dynamic_import_risk', 'Dynamic imports'),
    ]

    # NEW: Numerical complexity patterns
    NUMERICAL_COMPLEXITY_PATTERNS = [
        # Scientific notation
        (r'\d+\.?\d*\s*[×x]\s*10\^?[-\d]+', 'scientific_notation', 'Scientific notation'),

        # Mathematical symbols
        (r'[∂∫∑∏√±×÷≠≈≤≥∞∇⊗⊕]', 'math_symbols', 'Mathematical symbols'),

        # Multiple units (conversion indicator) — word boundaries on both
        # occurrences so short units like 'm' or 'K' only match as standalone tokens
        (r'\b(kg|lb|lbs|ft|°C|°F|J|cal|BTU|MPa|psi)\b.*\b(kg|lb|lbs|ft|°C|°F|J|cal|BTU|MPa|psi)\b',
         'multi_unit', 'Multiple unit types'),

        # Equations with variables (subscripted notation like T_i = 35)
        (r'[A-Z]_\w+\s*=|[a-z]_\d+', 'equation_with_vars', 'Equation with variables'),

        # LaTeX/scientific notation ($2.00 \mathrm{~mJ}$, \mu, \frac) —
        # benchmark questions written in LaTeX are calculation-heavy
        (r'\\(mathrm|mu|frac|sqrt|times|cdot|hat|vec)\b|\$[^$]*\d[^$]*\$',
         'latex_notation', 'LaTeX scientific notation'),
    ]

    # Numbers threshold: questions with this many numeric values are
    # calculation-heavy (checked via findall, not a backtracking regex)
    MULTIPLE_NUMBERS_THRESHOLD = 3
    NUMBER_TOKEN = re.compile(r'\b\d+(?:[,\.]\d+)*\b')

    # IMPROVED: More specific domain keywords (removed too-broad categories)
    DIFFICULT_DOMAINS = {
        'quantum': ['quantum', 'qubit', 'entanglement', 'superposition', 'wave function', 'eigenstate'],

        # REMOVED: generic 'medicine' - now handled by context-aware check

        # More specific physics (not all physics questions are hard)
        'advanced_physics': ['partition function', 'thermodynamic ensemble', 'lagrangian',
                            'hamiltonian operator', 'gauge theory', 'renormalization'],

        # More specific math (not "prove" alone, need context)
        'advanced_math': ['homomorphism', 'isomorphism', 'bijection',
                         'countable infinity', 'cardinality', 'field extension'],

        # REMOVED: 'engineering' - too broad, causes false positives
    }

    # IMPROVED: More specific complexity indicators
    COMPLEXITY_INDICATORS = [
        'first.*then.*finally', 'step 1.*step 2.*step 3',
        'calculate.*and then.*calculate',
        'multi-step', 'step-by-step', 'sequential'
    ]

    # Unit conversion indicators (CoT failure pattern)
    UNIT_CONVERSION_KEYWORDS = [
        r'\b(convert|conversion)\b',
        r'\b(lbs|pounds|kg|kilograms)\b',
        r'\b(inches|feet|meters|cm|mm)\b',
        r'\b(fahrenheit|celsius|kelvin)\b',
        r'\b(BTU|joules|calories|kJ)\b',
        r'\b(MPa|psi|pascal|atm|torr)\b',
    ]

    def __init__(self):
        self.code_patterns = [
            (re.compile(pattern, re.IGNORECASE), name, desc)
            for pattern, name, desc in self.CODE_RISK_PATTERNS
        ]

        # NEW: Compile numerical patterns
        self.numerical_patterns = [
            (re.compile(pattern, re.IGNORECASE), name, desc)
            for pattern, name, desc in self.NUMERICAL_COMPLEXITY_PATTERNS
        ]

        self.unit_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.UNIT_CONVERSION_KEYWORDS
        ]

    def quick_check(self, prompt: str) -> Dict:
        """
        Fast risk screening (< 1ms typically)

        IMPROVED VERSION with better recall and precision

        Returns:
            {
                'should_analyze': bool,  # Should invoke full ToGMAL analysis?
                'risk_level': str,       # NONE, LOW, MEDIUM, HIGH, CRITICAL
                'triggers': List[str],   # What triggered the risk
                'confidence': float,     # Confidence in assessment (0-1)
                'recommended_action': str
            }
        """
        triggers = []
        risk_score = 0.0

        # 1. Check for code patterns (UNCHANGED - works well)
        code_triggers = self._check_code_patterns(prompt)
        if code_triggers:
            triggers.extend(code_triggers)
            risk_score += 0.3 * len(code_triggers)

        # 2. Check for difficult domains (IMPROVED - more specific)
        domain_triggers = self._check_difficult_domains(prompt)
        if domain_triggers:
            triggers.extend(domain_triggers)
            risk_score += 0.2 * len(domain_triggers)

        # 3. Check for complexity (IMPROVED - more stringent)
        if self._is_complex(prompt):
            triggers.append('multi-step_complexity')
            risk_score += 0.15  # Reduced weight from 0.2

        # 4. Check for unit conversions (IMPROVED - graded by unit class count;
        # 2 classes already signals a conversion, the documented CoT failure mode)
        unit_count = self._count_unit_conversions(prompt)
        if unit_count >= 3:
            triggers.append(f'complex_unit_conversion_{unit_count}_units')
            risk_score += 0.3
        elif unit_count == 2:
            triggers.append('unit_conversion_2_units')
            risk_score += 0.15

        # 5. Check for medical/legal (IMPROVED - context-aware)
        # Direct first-person advice-seeking is weighted CRITICAL on its own;
        # keyword-only matches (no knowledge-question phrasing) weigh less
        dangerous_domain = self._is_dangerous_domain(prompt)
        if dangerous_domain:
            triggers.append(f'dangerous_domain_{dangerous_domain}')
            risk_score += 0.7 if dangerous_domain.endswith('_direct') else 0.5

        # 6. NEW: Check for numerical complexity
        numerical_triggers = self._check_numerical_complexity(prompt)
        if numerical_triggers:
            triggers.extend(numerical_triggers)
            risk_score += 0.15 * len(numerical_triggers)

        # 7. NEW: Check question type
        question_type_score, question_type_trigger = self._check_question_type(prompt)
        if question_type_trigger:
            triggers.append(question_type_trigger)
            risk_score += question_type_score

        # Determine risk level
        if risk_score >= 0.7:
            risk_level = 'CRITICAL'
        elif risk_score >= 0.5:
            risk_level = 'HIGH'
        elif risk_score >= 0.3:
            risk_level = 'MEDIUM'
        elif risk_score > 0:
            risk_level = 'LOW'
        else:
            risk_level = 'NONE'

        # IMPROVED: Lower threshold for deep analysis (0.3 → 0.15)
        should_analyze = risk_score >= 0.15  # Better recall!

        # Recommended action
        if risk_level == 'CRITICAL':
            action = 'Invoke ToGMAL Skill for comprehensive analysis + strong warnings'
        elif risk_level == 'HIGH':
            action = 'Invoke ToGMAL Skill for data-driven risk assessment'
        elif risk_level == 'MEDIUM':
            action = 'Consider invoking ToGMAL Skill for pattern verification'
        elif risk_level == 'LOW' and should_analyze:
            action = 'Quick ToGMAL check recommended (low risk but some indicators)'
        else:
            action = 'Proceed normally (low/no risk detected)'

        return {
            'should_analyze': should_analyze,
            'risk_level': risk_level,
            'triggers': triggers,
            'risk_score': round(risk_score, 2),
            'confidence': self._compute_confidence(triggers, prompt),
            'recommended_action': action
        }

    def _check_code_patterns(self, prompt: str) -> List[str]:
        """Check for risky code patterns - UNCHANGED"""
        triggers = []
        for pattern, name, desc in self.code_patterns:
            if pattern.search(prompt):
                triggers.append(f'code_pattern:{name}')
        return triggers

    def _check_numerical_complexity(self, prompt: str) -> List[str]:
        """NEW: Check for numerical complexity patterns"""
        triggers = []
        for pattern, name, desc in self.numerical_patterns:
            if pattern.search(prompt):
                triggers.append(f'numerical:{name}')

        # Count numeric tokens without a repetition regex (avoids backtracking)
        number_count = len(self.NUMBER_TOKEN.findall(prompt))
        if number_count >= self.MULTIPLE_NUMBERS_THRESHOLD:
            triggers.append('numerical:multiple_numbers')

        return triggers

    def _check_difficult_domains(self, prompt: str) -> List[str]:
        """Check for difficult domain keywords - IMPROVED (more specific)"""
        triggers = []
        prompt_lower = prompt.lower()

        for domain, keywords in self.DIFFICULT_DOMAINS.items():
            if any(kw in prompt_lower for kw in keywords):
                triggers.append(f'difficult_domain:{domain}')

        return triggers

    def _is_complex(self, prompt: str) -> bool:
        """
        Check for multi-step complexity - IMPROVED

        Now requires BOTH step indicators AND sufficient length
        to reduce false positives
        """
        prompt_lower = prompt.lower()

        # Check for step indicators
        has_step_indicator = any(
            re.search(indicator, prompt_lower)
            for indicator in self.COMPLEXITY_INDICATORS
        )

        # Complex prompts are usually longer (> 30 words)
        is_sufficiently_long = len(prompt.split()) > 30

        # Require both conditions
        return has_step_indicator and is_sufficiently_long

    def _count_unit_conversions(self, prompt: str) -> int:
        """Count unit conversion indicators - UNCHANGED"""
        count = 0
        for pattern in self.unit_patterns:
            if pattern.search(prompt):
                count += 1
        return count

    def _is_dangerous_domain(self, prompt: str) -> str:
        """
        Check for dangerous domains - IMPROVED with context awareness

        Returns: 'medical_advice', 'legal_advice', or empty string
        """
        prompt_lower = prompt.lower()

        # Medical advice detection (IMPROVED)
        medical_advice_indicators = [
            'i have', 'i am experiencing', 'i feel', 'my symptoms',
            'should i take', 'what medication', 'do i need', 'am i sick',
            'diagnose me', 'what treatment should', 'prescribe'
        ]

        medical_knowledge_indicators = [
            'what is', 'what are', 'which of the following', 'the disease',
            'caused by', 'symptoms of', 'characterized by', 'defined as',
            'deficiency of', 'treatment for', 'referred to as', 'known as'
        ]

        # Prompts opening with an interrogative are quiz/knowledge phrasing
        # ("What disease is called..."), not personal advice-seeking
        starts_interrogative = bool(re.match(
            r'\s*(what|which|who|when|where|how many|how much)\b',
            prompt_lower
        ))

        medical_keywords = ['diagnose', 'diagnosis', 'patient', 'symptoms',
                           'disease', 'treatment', 'medical', 'medication']

        # Check for medical advice-seeking (dangerous)
        has_advice_seeking = any(ind in prompt_lower for ind in medical_advice_indicators)

        # Check for medical knowledge question (safe, academic)
        has_knowledge_indicators = (
            any(ind in prompt_lower for ind in medical_knowledge_indicators)
            or starts_interrogative
        )

        has_medical_keywords = any(kw in prompt_lower for kw in medical_keywords)

        # Direct advice-seeking ("I have...", "should I take...") is the most
        # dangerous case and is flagged even alongside knowledge phrasing
        if has_advice_seeking:
            return 'medical_advice_direct'

        # Medical keywords without knowledge-question phrasing: likely advice
        if has_medical_keywords and not has_knowledge_indicators:
            return 'medical_advice'

        # Legal advice detection
        legal_indicators = [
            'should i sue', 'can i sue', 'legal action', 'my lawyer',
            'am i liable', 'contract says', 'what are my rights'
        ]

        legal_knowledge_indicators = [
            'what is', 'which of the following', 'defined as', 'characterized by'
        ]

        has_legal_seeking = any(ind in prompt_lower for ind in legal_indicators)
        has_legal_knowledge = any(ind in prompt_lower for ind in legal_knowledge_indicators)

        legal_keywords = ['lawsuit', 'liability', 'contract', 'legal']
        has_legal_keywords = any(kw in prompt_lower for kw in legal_keywords)

        is_legal_advice = (has_legal_seeking or
                          (has_legal_keywords and not has_legal_knowledge))

        if is_legal_advice:
            return 'legal_advice'

        return ''  # Not dangerous

    def _check_question_type(self, prompt: str) -> tuple[float, str]:
        """
        NEW: Detect question types that correlate with difficulty

        Returns: (risk_score_contribution, trigger_name)
        """
        prompt_lower = prompt.lower()
        risk = 0.0
        trigger = ''

        # Proof-based questions (very hard)
        if re.search(r'\b(prove|show that|demonstrate that|derive)\b', prompt_lower):
            risk += 0.3
            trigger = 'question_type:proof_based'

        # Calculation with multiple givens
        elif 'calculate' in prompt_lower and 'given' in prompt_lower:
            risk += 0.1
            trigger = 'question_type:calculation_with_constraints'

        # Multi-part questions (a, b, c, ...)
        else:
            part_count = len(re.findall(r'\b(a\)|b\)|c\)|d\)|part \w+|\(i\)|\(ii\)|\(iii\))', prompt_lower))
            if part_count >= 3:
                risk += 0.15
                trigger = f'question_type:multi_part_{part_count}_parts'

        return (min(risk, 0.3), trigger)  # Cap contribution at 0.3

    def _compute_confidence(self, triggers: List[str], prompt: str) -> float:
        """Compute confidence in risk assessment - IMPROVED"""
        if not triggers:
            return 0.9  # High confidence in "no risk"

        # More triggers = higher confidence
        confidence = min(0.5 + 0.08 * len(triggers), 0.95)

        # Boost confidence for code patterns (very reliable)
        if any('code_pattern' in t for t in triggers):
            confidence = min(confidence + 0.1, 0.95)

        # Boost confidence for numerical patterns (reliable)
        if any('numerical' in t for t in triggers):
            confidence = min(confidence + 0.05, 0.95)

        return round(confidence, 2)

def test_lightweight_checker():
    """Test the IMPROVED lightweight checker"""
    checker = LightweightPromptChecker()

    test_cases = [
        # Safe prompts
        ("What is 2+2?", "NONE"),
        ("Explain Python lists", "NONE"),

        # Medical knowledge (should NOT flag as dangerous now)
        ("Tay-Sachs disease is caused by deficiency of what?", "NONE"),
        ("Which of the following symptoms characterize appendicitis?", "NONE"),

        # Medical advice (should still flag)
        ("I have a fever and headache, what medication should I take?", "CRITICAL"),

        # Code risks
        ("df['new_col'] = df['old_col'] * 2", "MEDIUM"),
        ("result = df.groupby('category').sum()", "MEDIUM"),

        # Numerical complexity (NEW - should catch)
        ("200 Kg of water at T_i = 35°C is kept in reservoir. Calculate final temp.", "MEDIUM"),
        ("Convert 27,000 lbs to kg and then calculate stress in MPa", "MEDIUM"),

        # Proof-based (NEW - should catch)
        ("Prove that the function f(x) = x^2 is continuous", "MEDIUM"),

        # Advanced physics
        ("Calculate the partition function for a quantum harmonic oscillator", "MEDIUM"),
    ]

    print("="*80)
    print("Lightweight Prompt Risk Checker - IMPROVED VERSION Test Results")
    print("="*80)

    for prompt, expected in test_cases:
        result = checker.quick_check(prompt)

        status = "✅" if result['risk_level'] == expected else f"❌ (expected {expected})"

        print(f"\n{status} Prompt: '{prompt[:60]}...'")
        print(f"   Risk: {result['risk_level']} (score: {result['risk_score']})")
        print(f"   Should analyze: {result['should_analyze']}")
        print(f"   Triggers: {', '.join(result['triggers']) if result['triggers'] else 'none'}")
        print(f"   Confidence: {result['confidence']:.0%}")
        print(f"   Action: {result['recommended_action']}")

if __name__ == "__main__":
    test_lightweight_checker()
