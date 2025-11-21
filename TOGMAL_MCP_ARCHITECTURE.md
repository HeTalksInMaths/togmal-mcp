# ToGMAL MCP Integration Architecture

**Goal**: Lightweight checker triggers ToGMAL for domain-specific risk assessment via MCP

---

## System Architecture

```
┌─────────────────────┐
│   User Prompt       │
│ "Calculate DCF for  │
│  5-year cash flow"  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────┐
│  Lightweight Checker        │
│  (Fast pattern matching)    │
│                             │
│  Checks:                    │
│  - Keywords (DCF, solve,    │
│    calculate, optimize)     │
│  - Numerical patterns       │
│  - Domain indicators        │
│  - Complexity heuristics    │
└──────────┬──────────────────┘
           │
           │ ✓ Risky detected
           │
           ▼
┌─────────────────────────────┐
│  ToGMAL MCP Server          │
│                             │
│  1. Embed prompt            │
│  2. Similarity search       │
│     against 9 cases         │
│  3. Retrieve top-k          │
│  4. Aggregate risk          │
│  5. Return assessment       │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Risk Assessment Response   │
│                             │
│  {                          │
│    "risk_level": "high",    │
│    "probability": 0.65,     │
│    "why": "Similar to...",  │
│    "evidence": [...],       │
│    "mitigation": "..."      │
│  }                          │
└─────────────────────────────┘
```

---

## Component 1: Lightweight Checker

**Purpose**: Fast triage - only call ToGMAL MCP when needed

### Trigger Patterns (Fast Regex/Keyword Matching)

```python
TRIGGER_PATTERNS = {
    "numerical_computation": {
        "keywords": [
            "calculate", "compute", "solve for", "find the value",
            "what is", "how many", "determine", "evaluate"
        ],
        "indicators": [
            r"\d+\s*(years?|periods?|steps?|iterations?)",  # Multi-step
            r"(compound|discount|interest|NPV|DCF|IRR)",     # Finance
            r"(integrate|differentiate|solve|root|factor)",  # Math
            r"(optimize|maximize|minimize)",                 # Optimization
        ],
        "risk_score": 0.7
    },

    "constraint_satisfaction": {
        "keywords": [
            "schedule", "assign", "allocate", "constraints",
            "must", "cannot", "requirements", "satisfying"
        ],
        "indicators": [
            r"\d+\s*(people|employees|tasks|resources)",
            r"\d+\s*constraints?",
            r"given that.*and.*and",  # Multiple conditions
        ],
        "risk_score": 0.6
    },

    "formula_recall": {
        "keywords": [
            "formula", "equation for", "how to calculate",
            "Black-Scholes", "CAPM", "Baumol-Tobin"
        ],
        "indicators": [
            r"(what|which)\s+is\s+the\s+(formula|equation)",
            r"(apply|use)\s+.*\s+(formula|model)",
        ],
        "risk_score": 0.4
    },

    "multi_step_reasoning": {
        "indicators": [
            r"step\s+\d+",
            r"first.*then.*finally",
            r"\d+\s*stages?",
        ],
        "risk_score": 0.5
    }
}

def should_trigger_togmal(prompt: str) -> tuple[bool, float]:
    """
    Fast check: should we call ToGMAL MCP?

    Returns:
        (should_call, initial_risk_score)
    """
    max_risk = 0.0
    matched_patterns = []

    prompt_lower = prompt.lower()

    for pattern_name, pattern_def in TRIGGER_PATTERNS.items():
        # Check keywords
        keyword_match = any(kw in prompt_lower for kw in pattern_def.get("keywords", []))

        # Check regex indicators
        import re
        indicator_match = any(
            re.search(ind, prompt_lower)
            for ind in pattern_def.get("indicators", [])
        )

        if keyword_match or indicator_match:
            matched_patterns.append(pattern_name)
            max_risk = max(max_risk, pattern_def["risk_score"])

    # Trigger if ANY pattern matched OR prompt is long/complex
    should_call = (
        len(matched_patterns) > 0 or
        len(prompt.split()) > 50 or  # Long prompts
        prompt.count('\n') > 5        # Multi-line structured prompts
    )

    return should_call, max_risk
```

**Example Outputs**:
```python
should_trigger_togmal("Calculate NPV for 5-year cash flow with 8% discount")
# → (True, 0.7)  # Matches numerical_computation

should_trigger_togmal("Schedule 10 employees with these constraints...")
# → (True, 0.6)  # Matches constraint_satisfaction

should_trigger_togmal("What's the capital of France?")
# → (False, 0.0)  # No match, simple factual
```

---

## Component 2: ToGMAL MCP Server

**Purpose**: Deep similarity-based risk assessment

### MCP Tool Definition

```json
{
  "name": "assess_task_risk",
  "description": "Assess likelihood of LLM failure on a task using similarity to known failure cases",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_description": {
        "type": "string",
        "description": "The task/prompt to assess"
      },
      "include_reasoning": {
        "type": "boolean",
        "description": "Whether to include detailed reasoning (default: true)"
      },
      "top_k": {
        "type": "number",
        "description": "Number of similar cases to retrieve (default: 3)"
      }
    },
    "required": ["task_description"]
  }
}
```

### Implementation

```python
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
import json

class ToGMALMCPServer:
    def __init__(self, annotations_path: str):
        # Load the 9 annotated cases
        with open(annotations_path) as f:
            self.data = json.load(f)
        self.cases = self.data["cases"]

        # Load embedding model
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')

        # Pre-compute embeddings for all 9 cases
        self.case_embeddings = self._compute_case_embeddings()

    def _compute_case_embeddings(self) -> np.ndarray:
        """Embed all 9 cases for similarity search"""
        texts = []
        for case in self.cases:
            # Combine multiple fields for rich representation
            text = f"""
            Domain: {case['domain']}
            Question: {case['task_description']}
            Requirements: {' '.join(case['conceptual_requirements'])}
            Failure: {case['domain_specific_why']['reason']}
            """
            texts.append(text)

        return self.encoder.encode(texts)

    def assess_task_risk(
        self,
        task_description: str,
        top_k: int = 3,
        include_reasoning: bool = True
    ) -> Dict:
        """
        Main MCP tool: assess risk of task failure

        Returns:
            {
                "risk_level": "high" | "medium" | "low",
                "failure_probability": 0.65,
                "similar_cases": [...],
                "why_fails": "...",
                "evidence": [...],
                "recommended_mitigation": "...",
                "reasoning": {...}  # if include_reasoning
            }
        """
        # 1. Embed the new task
        task_embedding = self.encoder.encode([task_description])[0]

        # 2. Compute similarities
        similarities = np.dot(self.case_embeddings, task_embedding) / (
            np.linalg.norm(self.case_embeddings, axis=1) * np.linalg.norm(task_embedding)
        )

        # 3. Get top-k most similar cases
        top_k_indices = np.argsort(similarities)[-top_k:][::-1]
        top_k_cases = [self.cases[i] for i in top_k_indices]
        top_k_similarities = [similarities[i] for i in top_k_indices]

        # 4. Aggregate risk assessment
        assessment = self._aggregate_risk(
            task_description,
            top_k_cases,
            top_k_similarities,
            include_reasoning
        )

        return assessment

    def _aggregate_risk(
        self,
        task: str,
        cases: List[Dict],
        similarities: List[float],
        include_reasoning: bool
    ) -> Dict:
        """Aggregate risk from multiple similar cases"""

        # Weighted average of risk multipliers
        weighted_risk = sum(
            case['risk_features_for_similarity']['risk_multiplier'] * sim
            for case, sim in zip(cases, similarities)
        ) / sum(similarities)

        # Convert to probability (heuristic)
        # risk_multiplier 1.0 → 20% failure
        # risk_multiplier 3.5 → 70% failure
        base_failure_rate = 0.20
        failure_probability = min(0.95, base_failure_rate * weighted_risk)

        # Determine risk level
        if failure_probability > 0.6:
            risk_level = "high"
        elif failure_probability > 0.35:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Extract domain-specific why
        primary_case = cases[0]  # Most similar
        why_fails = primary_case['domain_specific_why']['reason']

        # Collect evidence
        evidence = []
        for case, sim in zip(cases, similarities):
            evidence.append({
                "case_id": case['case_id'],
                "similarity": float(sim),
                "domain": case['domain'],
                "failure_point": case['execution_failure_point']['error_type'],
                "pattern": case['failure_mechanism']['pattern']
            })

        # Generate mitigation from primary case
        mitigation = self._generate_mitigation(primary_case)

        # Build response
        response = {
            "risk_level": risk_level,
            "failure_probability": round(failure_probability, 2),
            "similar_cases": [
                {
                    "case_id": case['case_id'],
                    "similarity": round(sim, 2),
                    "domain": case['domain']
                }
                for case, sim in zip(cases, similarities)
            ],
            "why_fails": why_fails,
            "evidence": evidence,
            "recommended_mitigation": mitigation
        }

        # Add detailed reasoning if requested
        if include_reasoning:
            response["reasoning"] = {
                "weighted_risk_multiplier": round(weighted_risk, 2),
                "base_failure_rate": base_failure_rate,
                "calculation": f"{base_failure_rate} * {weighted_risk:.2f} = {failure_probability:.2f}",
                "primary_case_domain_why": primary_case['domain_specific_why'],
                "all_matching_patterns": list(set(
                    case['failure_mechanism']['pattern'] for case in cases
                ))
            }

        return response

    def _generate_mitigation(self, case: Dict) -> str:
        """Generate mitigation strategy based on case patterns"""

        pattern = case['failure_mechanism']['pattern']
        domain = case['domain']

        # Pattern-specific mitigations
        if "Arithmetic" in pattern:
            return (
                "Use LLM to structure the problem, then execute calculations "
                "in a verified computation tool (Python/NumPy, Excel, calculator). "
                "LLM cannot reliably perform multi-step arithmetic."
            )
        elif "Algebraic" in pattern:
            return (
                "Use LLM to set up equations, then solve using symbolic math "
                "tools (SymPy, Mathematica, WolframAlpha). Request verification "
                "by substitution if LLM attempts solving."
            )
        elif "Variable Confusion" in pattern or "State" in pattern:
            return (
                "Use structured output format to track variables/states explicitly. "
                "Before final answer, ask LLM to verify which variable the question "
                "asks for. Consider using JSON output with named fields."
            )
        elif "Consistency Checking" in pattern:
            return (
                "After LLM proposes solution, explicitly ask it to verify the "
                "solution satisfies ALL constraints. Consider using external "
                "constraint validator (e.g., Z3 solver for SAT problems)."
            )
        elif "Factual Recall" in pattern:
            return (
                "Provide the formula explicitly rather than asking LLM to recall. "
                "If LLM states formula, verify against authoritative source before "
                "using. Do not trust constants/factors from memory."
            )
        else:
            return (
                f"Based on {domain} domain failures, use LLM for understanding "
                "and structuring only. Execute computation/verification in "
                "specialized tools."
            )
```

---

## Component 3: Integration Flow

### Example: LLM Wrapper with Risk Check

```python
import anthropic
from togmal_mcp_client import ToGMALClient

class RiskAwareLLM:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.togmal = ToGMALClient()  # MCP client

    def generate(self, prompt: str, check_risk: bool = True):
        """
        Generate response with optional risk checking
        """
        # Step 1: Lightweight check
        should_assess, initial_risk = should_trigger_togmal(prompt)

        if check_risk and should_assess:
            # Step 2: Call ToGMAL via MCP
            risk_assessment = self.togmal.assess_task_risk(
                task_description=prompt,
                top_k=3,
                include_reasoning=True
            )

            # Step 3: Decide what to do based on risk
            if risk_assessment['risk_level'] == 'high':
                # Show warning to user
                print(f"⚠️  HIGH RISK TASK DETECTED")
                print(f"Failure probability: {risk_assessment['failure_probability']*100:.0f}%")
                print(f"Why: {risk_assessment['why_fails']}")
                print(f"Recommendation: {risk_assessment['recommended_mitigation']}")
                print()

                # Optionally modify prompt to include mitigation
                augmented_prompt = self._augment_with_mitigation(
                    prompt,
                    risk_assessment
                )

                response = self.client.messages.create(
                    model="claude-sonnet-4",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": augmented_prompt}]
                )
            else:
                # Low/medium risk, proceed normally
                response = self.client.messages.create(
                    model="claude-sonnet-4",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )

            return response, risk_assessment
        else:
            # No risk check needed
            response = self.client.messages.create(
                model="claude-sonnet-4",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return response, None

    def _augment_with_mitigation(self, prompt: str, risk: Dict) -> str:
        """Add mitigation guidance to prompt"""
        return f"""{prompt}

IMPORTANT: {risk['recommended_mitigation']}

Please structure your solution accordingly."""
```

### Usage Example

```python
llm = RiskAwareLLM()

# Example 1: High-risk numerical task
prompt1 = "Calculate NPV of cash flows: Year 1: $100K, Year 2: $120K, Year 3: $150K, Year 4: $180K, Year 5: $200K. Discount rate: 8%"

response, risk = llm.generate(prompt1)

# Output:
# ⚠️  HIGH RISK TASK DETECTED
# Failure probability: 65%
# Why: Numerical methods require exact arithmetic across iterations - errors compound exponentially
# Similar to: Case 4 (Euler's method, similarity=0.87)
# Recommendation: Use LLM to structure the problem, then execute calculations
#                 in a verified computation tool (Python/NumPy, Excel, calculator).
```

---

## Response Format Examples

### High-Risk Example

```json
{
  "risk_level": "high",
  "failure_probability": 0.65,
  "similar_cases": [
    {
      "case_id": "case_4_eulers_method",
      "similarity": 0.87,
      "domain": "Numerical Methods"
    },
    {
      "case_id": "case_6_combinatorics",
      "similarity": 0.71,
      "domain": "Combinatorics/Discrete Math"
    }
  ],
  "why_fails": "Numerical methods require exact arithmetic across iterations - errors compound exponentially in iterative algorithms",
  "evidence": [
    {
      "case_id": "case_4_eulers_method",
      "similarity": 0.87,
      "domain": "Numerical Methods",
      "failure_point": "Basic arithmetic failures in multi-step computation",
      "pattern": "Pattern 4: Arithmetic errors compound"
    }
  ],
  "recommended_mitigation": "Use LLM to structure the problem, then execute calculations in a verified computation tool (Python/NumPy, Excel, calculator). LLM cannot reliably perform multi-step arithmetic.",
  "reasoning": {
    "weighted_risk_multiplier": 3.25,
    "base_failure_rate": 0.2,
    "calculation": "0.2 * 3.25 = 0.65",
    "primary_case_domain_why": {
      "reason": "Numerical methods require exact arithmetic across many iterations - errors propagate exponentially",
      "when_this_matters": "Any iterative numerical algorithm (Newton's method, Runge-Kutta, finite differences, gradient descent)",
      "root_cause": "Cannot reliably compute multi-step arithmetic chains"
    },
    "all_matching_patterns": [
      "Pattern 4: Arithmetic errors compound"
    ]
  }
}
```

### Medium-Risk Example

```json
{
  "risk_level": "medium",
  "failure_probability": 0.42,
  "similar_cases": [
    {
      "case_id": "case_8_dp_restaurant",
      "similarity": 0.73,
      "domain": "Dynamic Programming"
    }
  ],
  "why_fails": "DP state transitions require tracking 'from state X, action A, go to state Y' - confuses source and target",
  "recommended_mitigation": "Use structured output format to track variables/states explicitly. Before final answer, ask LLM to verify which variable the question asks for.",
  "reasoning": {
    "weighted_risk_multiplier": 2.1,
    "all_matching_patterns": ["Pattern 3: Variable confusion"]
  }
}
```

---

## Key Benefits

1. **Fast Triage**: Lightweight checker avoids expensive MCP calls for simple prompts
2. **Domain-Specific**: Not just "risky" but "fails because iterative arithmetic in financial calculations"
3. **Evidence-Based**: "Similar to Case 4 with 87% similarity"
4. **Actionable**: Specific mitigation strategies per pattern
5. **Probabilistic**: 65% failure rate, not binary yes/no
6. **Transparent**: Full reasoning available for debugging/trust

---

## Next Steps

1. **Implement lightweight checker** - regex/keyword patterns
2. **Build MCP server** - similarity search + aggregation
3. **Create MCP client wrapper** - easy integration
4. **Test on new prompts** - validate similarity matching works
5. **Tune risk calibration** - adjust base_failure_rate, risk_multiplier mapping
6. **Expand annotations** - add more cases beyond 9 for better coverage

This gives you the **what** (risk level), **why** (domain-specific reason), and **how to fix** (mitigation) - all backed by evidence from real SOTA failures.
