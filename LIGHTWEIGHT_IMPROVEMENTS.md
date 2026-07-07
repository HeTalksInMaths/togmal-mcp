# Lightweight Checker Improvements

## Test Results Summary

**Current Performance (tested on 1,000 questions):**
- ❌ **Recall: 7.9%** - Missing 92% of risky questions!
- ✅ **Precision: 65.2%** - When it flags something, usually correct
- ⚠️ **Accuracy: 47.8%** - Overall correctness
- ✅ **FPR: 5.0%** - Low false positive rate

## Key Problems Identified

### Problem 1: Missing Most Difficult Questions (499 false negatives)

**Examples of missed risky questions:**
```
Ground Truth: CRITICAL (2.7% success)
Question: "200 Kg of water at T_i = 35°C is kept in an auxiliary reservoir..."
Predicted: NONE
Why missed: No keywords detected for complex thermodynamics calculation
```

**Root cause:** Lightweight checker only catches obvious patterns (medical keywords, code patterns), but most difficult questions use **neutral academic language** without trigger words.

### Problem 2: Over-Flagging Medical Knowledge Questions (23 false positives)

**Example:**
```
Ground Truth: NONE (97.3% success)
Question: "Tay-Sachs disease is caused by deficiency of _____?"
Predicted: CRITICAL
Why wrong: This is testing medical knowledge, not seeking medical advice
```

**Root cause:** Can't distinguish between "medical knowledge question" vs "seeking medical advice" with regex alone.

### Problem 3: Ineffective Triggers

| Trigger | Error Rate | Status |
|---------|-----------|--------|
| multi-step_complexity | 80% | 🔴 Remove or fix |
| difficult_domain:engineering | 60% | 🟡 Needs work |
| difficult_domain:physics | 60% | 🟡 Needs work |
| code_pattern:mutability_risk | 0% | ✅ Keep |
| code_pattern:index_risk | 0% | ✅ Keep |

---

## Recommended Improvements

### Improvement 1: Lower the Risk Threshold (Quick Win)

**Current code (lightweight_prompt_checker.py:135):**
```python
should_analyze = risk_score >= 0.3  # Threshold for deep analysis
```

**Recommended change:**
```python
should_analyze = risk_score >= 0.15  # Lower threshold to catch more cases
```

**Impact:**
- 📈 Increases recall (catches more risky questions)
- 📉 Slight increase in false positives
- ⚡ No code complexity added

**Trade-off:** Invokes full ToGMAL analysis more often, but that's the **correct behavior** since the lightweight tier is meant to be a **pre-screener**, not the final decision maker.

---

### Improvement 2: Add Numerical Complexity Patterns

**Problem:** Many missed questions involve complex calculations with numbers but no domain keywords.

**Add these patterns:**

```python
# Add to LightweightPromptChecker class

NUMERICAL_COMPLEXITY_PATTERNS = [
    # Multiple numerical operations
    (r'\d+.*\d+.*\d+', 'multiple_numbers', 'Contains 3+ numbers'),

    # Scientific notation
    (r'\d+\.?\d*\s*[×x]\s*10\^?[-\d]+', 'scientific_notation', 'Scientific notation'),

    # Mathematical expressions
    (r'[∂∫∑∏√±×÷≠≈≤≥∞∇]', 'math_symbols', 'Mathematical symbols'),

    # Multiple units (conversion indicator)
    (r'(kg|lb|m|ft|°C|°F|K|J|cal|BTU).*\b(kg|lb|m|ft|°C|°F|K|J|cal|BTU)\b',
     'multi_unit', 'Multiple unit types'),

    # Equations with variables
    (r'[A-Z]\s*=\s*\d+|[a-z]_\d+', 'equation_with_vars', 'Equation with variables'),
]
```

**Add to quick_check method:**
```python
# After existing checks
numerical_triggers = self._check_numerical_complexity(prompt)
if numerical_triggers:
    triggers.extend(numerical_triggers)
    risk_score += 0.15 * len(numerical_triggers)  # Moderate weight
```

**Impact:** Would catch questions like "200 Kg of water at T_i = 35°C..." (currently missed).

---

### Improvement 3: Fix Medical Trigger (Distinguish Knowledge vs Advice)

**Problem:** Can't tell difference between:
- ❌ False positive: "What disease is caused by X?" (knowledge question, easy)
- ✅ True positive: "I have symptoms X, what should I do?" (medical advice, dangerous)

**Solution: Context-aware medical check:**

```python
def _is_dangerous_domain(self, prompt: str) -> bool:
    """Check for dangerous domains - IMPROVED VERSION"""
    prompt_lower = prompt.lower()

    # Medical ADVICE indicators (dangerous)
    medical_advice_indicators = [
        'i have', 'i am experiencing', 'i feel', 'my symptoms',
        'should i take', 'what medication', 'do i need', 'am i sick',
        'diagnose me', 'what treatment should'
    ]

    # Medical KNOWLEDGE indicators (safe, academic)
    medical_knowledge_indicators = [
        'what is', 'what are', 'which of the following', 'the disease',
        'caused by', 'symptoms of', 'characterized by', 'defined as'
    ]

    # Check for advice-seeking (dangerous)
    has_advice_seeking = any(ind in prompt_lower for ind in medical_advice_indicators)

    # Check for knowledge question (safe)
    has_knowledge_indicators = any(ind in prompt_lower for ind in medical_knowledge_indicators)

    # Dangerous keywords
    medical_keywords = ['diagnose', 'diagnosis', 'patient', 'symptoms',
                       'disease', 'treatment', 'medical', 'medication']
    has_medical_keywords = any(kw in prompt_lower for kw in medical_keywords)

    # Only flag if:
    # 1. Has advice-seeking language, OR
    # 2. Has medical keywords BUT NOT knowledge indicators
    if has_advice_seeking:
        return True
    elif has_medical_keywords and not has_knowledge_indicators:
        return True
    else:
        return False  # Academic medical question - safe
```

**Impact:**
- ✅ Reduces false positives from 23 → ~10 (avoid flagging "Tay-Sachs disease is caused by...")
- ✅ Still catches "I have these symptoms, what disease is it?"

---

### Improvement 4: Remove/Fix Low-Accuracy Triggers

**Changes needed:**

1. **Multi-step complexity** (80% error rate):
```python
# BEFORE (lightweight_prompt_checker.py:175-181)
def _is_complex(self, prompt: str) -> bool:
    """Check for multi-step complexity"""
    prompt_lower = prompt.lower()
    return any(
        re.search(indicator, prompt_lower)
        for indicator in self.COMPLEXITY_INDICATORS
    )

# AFTER - Make more specific
def _is_complex(self, prompt: str) -> bool:
    """Check for multi-step complexity - IMPROVED"""
    prompt_lower = prompt.lower()

    # Require BOTH: step indicator AND sufficient length
    has_step_indicator = any(
        re.search(indicator, prompt_lower)
        for indicator in self.COMPLEXITY_INDICATORS
    )

    # Complex prompts are usually longer
    is_sufficiently_long = len(prompt.split()) > 30

    return has_step_indicator and is_sufficiently_long
```

2. **Engineering/Physics domains** (60% error rate):
```python
# These domains are TOO BROAD - most physics/engineering questions are fine
# Solution: Only flag ADVANCED topics

DIFFICULT_DOMAINS = {
    'quantum': ['quantum', 'qubit', 'entanglement', 'superposition',
                'wave function', 'eigenstate'],

    # REMOVE generic medicine keywords, use improved _is_dangerous_domain() instead
    # 'medicine': [...],  # Handled by context-aware check

    # Make physics more specific
    'advanced_physics': ['partition function', 'thermodynamic ensemble',
                        'lagrangian', 'hamiltonian operator', 'gauge theory',
                        'renormalization'],

    # Make math more specific
    'advanced_math': ['prove that', 'show that', 'demonstrate that',
                     'homomorphism', 'isomorphism', 'bijection',
                     'countable infinity', 'cardinality'],

    # REMOVE engineering - too broad, most eng questions are fine
    # 'engineering': [...],
}
```

---

### Improvement 5: Add Question Type Detection

**Insight:** Some question formats are inherently harder.

```python
# Add to quick_check()
question_type_score = self._check_question_type(prompt)
risk_score += question_type_score
```

```python
def _check_question_type(self, prompt: str) -> float:
    """
    Detect question types that correlate with difficulty

    Returns risk score contribution (0.0 - 0.3)
    """
    prompt_lower = prompt.lower()
    risk = 0.0

    # Proof-based questions (very hard)
    if re.search(r'\b(prove|show that|demonstrate that)\b', prompt_lower):
        risk += 0.25

    # Calculation with constraints
    if 'calculate' in prompt_lower and 'given' in prompt_lower:
        risk += 0.1

    # Multi-part questions
    part_count = len(re.findall(r'\b(a\)|b\)|c\)|part \w+|\(i\)|\(ii\))', prompt_lower))
    if part_count >= 3:
        risk += 0.15

    return min(risk, 0.3)  # Cap contribution
```

---

## Implementation Plan

### Phase 1: Quick Wins (< 1 hour)
1. ✅ Lower threshold from 0.3 → 0.15
2. ✅ Fix medical trigger with context awareness
3. ✅ Remove/fix low-accuracy triggers

**Expected improvement:** Recall 7.9% → ~25-30%

### Phase 2: Pattern Additions (2-3 hours)
4. ✅ Add numerical complexity patterns
5. ✅ Add question type detection
6. ✅ Make domain triggers more specific

**Expected improvement:** Recall 25-30% → ~45-55%

### Phase 3: Re-test and Iterate (1 hour)
7. ✅ Run `test_lightweight_effectiveness.py` again
8. ✅ Analyze new false negatives/positives
9. ✅ Fine-tune thresholds based on results

**Target:** Recall ≥ 60%, Precision ≥ 60%, FPR < 10%

---

## Trade-offs to Consider

### The Lightweight Tier Dilemma

**Option A: High Recall (catch everything risky)**
- ✅ Don't miss dangerous prompts
- ❌ Invoke full analysis more often (slower, but safer)

**Option B: High Precision (only flag obvious risks)**
- ✅ Fast for most prompts
- ❌ Miss subtle but risky questions

**Recommended approach:** **Optimize for Recall**

**Why?**
1. The lightweight tier is a **pre-screener**, not the final decision
2. False negatives are more dangerous than false positives
3. Full ToGMAL analysis is still fast enough (< 100ms)
4. Better to be safe and check than to miss risks

---

## Validation Strategy

After implementing improvements, validate with:

```bash
# Both versions on the same seeded 1K sample
python3 test_lightweight_effectiveness.py             # original
python3 test_lightweight_effectiveness.py --improved  # improved

# Full 13K dataset
python3 test_lightweight_effectiveness.py --improved --full

# Compare saved results
python3 -c "
import json
before = json.load(open('data/lightweight_effectiveness_original_1000.json'))
after = json.load(open('data/lightweight_effectiveness_improved_1000.json'))
print(f'Recall: {before[\"metrics\"][\"recall\"]:.1%} → {after[\"metrics\"][\"recall\"]:.1%}')
print(f'Precision: {before[\"metrics\"][\"precision\"]:.1%} → {after[\"metrics\"][\"precision\"]:.1%}')
"
```

**Measured outcome (full 13K run):** recall 7.3% → 56.1%, precision 78.3% →
86.9%, F1 13.3% → 68.2%, FPR 4.8% → 20.1%. See
`TESTING_AND_IMPROVEMENT_SUMMARY.md` for the full breakdown.

---

## Success Criteria

✅ **Minimum acceptable performance:**
- Recall ≥ 60% (catch 60% of risky questions)
- Precision ≥ 55% (avoid too many false alarms)
- FPR < 15% (don't overwhelm with false positives)

🎯 **Target performance:**
- Recall ≥ 75%
- Precision ≥ 65%
- FPR < 10%

🏆 **Excellent performance:**
- Recall ≥ 85%
- Precision ≥ 75%
- FPR < 8%

---

## Next Steps

1. **Immediate:** Review this document and decide on improvements
2. **Implement:** Make changes to `lightweight_prompt_checker.py`
3. **Test:** Run effectiveness test again
4. **Iterate:** Refine based on results
5. **Deploy:** Update MCP server with improved checker
