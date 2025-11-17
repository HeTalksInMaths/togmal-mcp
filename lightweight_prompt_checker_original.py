#!/usr/bin/env python3
"""
Lightweight Prompt Risk Checker
================================

Fast, regex-based pre-screening to determine if a prompt
needs deep ToGMAL analysis.

This runs BEFORE the Skill to avoid expensive analysis on safe prompts.

Architecture:
1. Lightweight check (this file) - Fast pattern matching, no data needed
2. If risky → Activate ToGMAL Skill for deep analysis
3. Skill uses MCP for data-driven risk assessment

Use cases:
- Screen ALL prompts automatically
- Determine which need deep analysis
- Provide quick warnings without full analysis
"""

import re
from typing import Dict, List, Tuple

class LightweightPromptChecker:
    """Fast pattern-based prompt risk screening"""

    # Risky code patterns (DS-1000 patterns)
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

    # Domain keywords that suggest high difficulty
    DIFFICULT_DOMAINS = {
        'quantum': ['quantum', 'qubit', 'entanglement', 'superposition', 'wave function'],
        'medicine': ['diagnose', 'diagnosis', 'patient', 'symptoms', 'disease', 'treatment', 'medical'],
        'physics': ['partition function', 'thermodynamic', 'eigenvalue', 'hamiltonian'],
        'math': ['prove', 'theorem', 'lemma', 'corollary', 'bijection', 'isomorphism'],
        'engineering': ['stress', 'strain', 'modulus', 'yield strength', 'thermal expansion'],
    }

    # Multi-step indicators
    COMPLEXITY_INDICATORS = [
        'first.*then', 'step 1', 'step 2', 'calculate.*and then',
        'multi-step', 'pipeline', 'workflow'
    ]

    # Unit conversion indicators (CoT failure pattern)
    UNIT_CONVERSION_KEYWORDS = [
        r'\b(convert|conversion)\b',
        r'\b(lbs|pounds|kg|kilograms)\b',
        r'\b(inches|feet|meters|cm)\b',
        r'\b(fahrenheit|celsius|kelvin)\b',
        r'\b(BTU|joules|calories)\b',
    ]

    def __init__(self):
        self.code_patterns = [
            (re.compile(pattern, re.IGNORECASE), name, desc)
            for pattern, name, desc in self.CODE_RISK_PATTERNS
        ]

        self.unit_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.UNIT_CONVERSION_KEYWORDS
        ]

    def quick_check(self, prompt: str) -> Dict:
        """
        Fast risk screening (< 1ms typically)

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

        # 1. Check for code patterns
        code_triggers = self._check_code_patterns(prompt)
        if code_triggers:
            triggers.extend(code_triggers)
            risk_score += 0.3 * len(code_triggers)

        # 2. Check for difficult domains
        domain_triggers = self._check_difficult_domains(prompt)
        if domain_triggers:
            triggers.extend(domain_triggers)
            risk_score += 0.2 * len(domain_triggers)

        # 3. Check for complexity
        if self._is_complex(prompt):
            triggers.append('multi-step_complexity')
            risk_score += 0.2

        # 4. Check for unit conversions (CoT failure pattern)
        unit_count = self._count_unit_conversions(prompt)
        if unit_count >= 3:
            triggers.append(f'complex_unit_conversion_{unit_count}_units')
            risk_score += 0.3

        # 5. Check for medical/legal (dangerous domains)
        if self._is_dangerous_domain(prompt):
            triggers.append('dangerous_domain_medical_or_legal')
            risk_score += 0.5

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

        # Should we invoke full analysis?
        should_analyze = risk_score >= 0.3  # Threshold for deep analysis

        # Recommended action
        if risk_level == 'CRITICAL':
            action = 'Invoke ToGMAL Skill for comprehensive analysis + strong warnings'
        elif risk_level == 'HIGH':
            action = 'Invoke ToGMAL Skill for data-driven risk assessment'
        elif risk_level == 'MEDIUM':
            action = 'Consider invoking ToGMAL Skill for pattern verification'
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
        """Check for risky code patterns"""
        triggers = []
        for pattern, name, desc in self.code_patterns:
            if pattern.search(prompt):
                triggers.append(f'code_pattern:{name}')
        return triggers

    def _check_difficult_domains(self, prompt: str) -> List[str]:
        """Check for difficult domain keywords"""
        triggers = []
        prompt_lower = prompt.lower()

        for domain, keywords in self.DIFFICULT_DOMAINS.items():
            if any(kw in prompt_lower for kw in keywords):
                triggers.append(f'difficult_domain:{domain}')

        return triggers

    def _is_complex(self, prompt: str) -> bool:
        """Check for multi-step complexity"""
        prompt_lower = prompt.lower()
        return any(
            re.search(indicator, prompt_lower)
            for indicator in self.COMPLEXITY_INDICATORS
        )

    def _count_unit_conversions(self, prompt: str) -> int:
        """Count unit conversion indicators"""
        count = 0
        for pattern in self.unit_patterns:
            if pattern.search(prompt):
                count += 1
        return count

    def _is_dangerous_domain(self, prompt: str) -> bool:
        """Check for dangerous domains (medical, legal)"""
        prompt_lower = prompt.lower()

        dangerous_keywords = [
            # Medical
            'diagnose', 'diagnosis', 'patient', 'symptoms', 'disease',
            'prescribe', 'medication', 'treatment', 'medical advice',
            # Legal
            'legal advice', 'sue', 'lawsuit', 'liability', 'contract review'
        ]

        return any(kw in prompt_lower for kw in dangerous_keywords)

    def _compute_confidence(self, triggers: List[str], prompt: str) -> float:
        """Compute confidence in risk assessment"""
        if not triggers:
            return 0.9  # High confidence in "no risk"

        # More triggers = higher confidence
        confidence = min(0.5 + 0.1 * len(triggers), 0.95)

        # Boost confidence for code patterns (very reliable)
        if any('code_pattern' in t for t in triggers):
            confidence = min(confidence + 0.1, 0.95)

        return round(confidence, 2)

def test_lightweight_checker():
    """Test the lightweight checker"""
    checker = LightweightPromptChecker()

    test_cases = [
        # Safe prompts
        ("What is 2+2?", "NONE"),
        ("Explain Python lists", "NONE"),

        # Code risks
        ("df['new_col'] = df['old_col'] * 2", "MEDIUM"),  # Mutation
        ("result = df.groupby('category').sum()", "MEDIUM"),  # Missing reset_index
        ("for i in df.iterrows(): print(i)", "MEDIUM"),  # For-loop

        # Difficult domains
        ("Calculate the partition function for a quantum harmonic oscillator", "MEDIUM"),
        ("What disease do these symptoms indicate?", "CRITICAL"),  # Medical

        # Complex unit conversions
        ("Convert 27,000 lbs to kg and then calculate stress in MPa with modulus in psi", "HIGH"),

        # Multi-step
        ("First calculate the mean, then the variance, then normalize", "LOW"),
    ]

    print("="*80)
    print("Lightweight Prompt Risk Checker - Test Results")
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
