# Prompt Improver MCP Server - Comprehensive Plan

## 🎯 Project Vision

**Name:** PromptCraft MCP Server  
**Purpose:** Privacy-preserving, heuristic-based prompt improvement and frustration detection  
**Philosophy:** Local-first, low-latency, deterministic analysis (no LLM judge needed)

---

## 📋 Core Features & Tools

### Tool 1: `promptcraft_analyze_vagueness`

**Detects:**
- Pronouns without context ("it", "that", "this thing")
- Missing specifics (no constraints, timeframes, formats)
- Ambiguous requests ("make it better", "fix this")
- Lack of examples or context
- No success criteria defined

**Heuristics:**
```python
def detect_vague_prompt(text: str, history: List[str] = None) -> Dict:
    """
    Args:
        text: Current prompt
        history: Last 3-5 messages for context resolution
    
    Returns:
        {
            'vagueness_score': 0.0-1.0,
            'vague_elements': ['pronouns', 'no_constraints', 'ambiguous_verbs'],
            'suggestions': [
                'Replace "it" with specific subject from context',
                'Add output format specification',
                'Define success criteria'
            ],
            'improved_prompt': 'Rewritten version with specifics'
        }
    """
    
    # Vague pronoun detection
    vague_pronouns = count_pattern(r'\b(it|that|this|these|those)\b')
    
    # Missing constraint detection
    has_format = bool(re.search(r'(format|style|structure|template)', text))
    has_length = bool(re.search(r'(words|lines|pages|characters|sentences)', text))
    has_deadline = bool(re.search(r'(by|before|within|deadline)', text))
    
    # Ambiguous verb detection
    vague_verbs = ['make', 'fix', 'improve', 'enhance', 'update', 'change']
    vague_verb_count = sum(1 for verb in vague_verbs if verb in text.lower())
    
    # Context analysis (if history provided)
    if history:
        # Check if pronouns reference previous messages
        # Resolve "it" to actual subject from history
        pass
    
    return analysis
```

**Example:**
```
Input: "Make it better"
Output:
  Vagueness Score: 0.95 (CRITICAL)
  Issues:
    - Pronoun "it" without context
    - Vague verb "make better"
    - No success criteria
    - No constraints specified
  
  Suggested Improvement:
    "Improve the [SUBJECT FROM CONTEXT] by:
     1. [Specific improvement 1]
     2. [Specific improvement 2]
     Success criteria: [Define what 'better' means]
     Format: [Specify output format]"
```

---

### Tool 2: `promptcraft_detect_frustration`

**Detects:**
- Repeated similar prompts (user trying multiple times)
- Escalating specificity (sign of failed attempts)
- Negative sentiment keywords
- Contradictory requirements
- "Never mind" / giving up signals

**Heuristics:**
```python
def detect_frustration_pattern(current: str, history: List[str]) -> Dict:
    """
    Analyzes conversation history for frustration signals.
    
    Patterns:
    1. Repetition: Same request with minor variations
    2. Escalation: Adding "please", "I need", "urgently"
    3. Contradiction: Reversing previous requirements
    4. Abandonment: "forget it", "never mind"
    5. Negation: "not what I wanted", "that's wrong"
    """
    
    # Repetition detection (Levenshtein distance)
    similarity_scores = [
        levenshtein_ratio(current, prev) 
        for prev in history[-5:]
    ]
    is_repeating = max(similarity_scores) > 0.7
    
    # Escalation keywords
    urgency_words = ['please', 'need', 'urgent', 'asap', 'immediately']
    urgency_trend = count_trend(urgency_words, history)
    
    # Negation detection
    negation_patterns = [
        r'(not|don\'t|doesn\'t) (what|how) I (want|need|meant)',
        r'(that\'s|this is) (wrong|incorrect|not right)',
        r'(try again|one more time|let me rephrase)',
    ]
    
    # Abandonment signals
    abandon_keywords = ['forget it', 'never mind', 'give up', 'whatever']
    
    return {
        'frustration_level': 'low' | 'moderate' | 'high',
        'patterns': ['repetition', 'escalation'],
        'root_cause_hypothesis': 'Likely missing: output format specification',
        'suggested_restart_prompt': 'Here\'s how you could have asked initially...'
    }
```

**Example:**
```
History:
  1. "Create a dashboard"
  2. "Create a dashboard with charts"
  3. "Please create a dashboard with charts and filters"
  4. "I need a dashboard with charts, filters, and export"

Analysis:
  Frustration Level: HIGH
  Pattern: Escalating specificity
  Root Cause: Original prompt too vague
  
  Suggested Initial Prompt:
    "Create a data dashboard with the following requirements:
     - Charts: [specify types: bar, line, pie]
     - Filters: [specify dimensions: date, category, region]
     - Features: Export to CSV/PDF
     - Tech stack: [React, Vue, vanilla JS?]
     - Design: [minimal, colorful, corporate]
     - Data source: [API endpoint or sample data]"
```

---

### Tool 3: `promptcraft_extract_requirements`

**Purpose:** Parse ambiguous prompts into structured requirements

**Heuristics:**
```python
def extract_structured_requirements(text: str) -> Dict:
    """
    Converts unstructured prompt into structured requirements.
    
    Extracts:
    - Functional requirements (what it should do)
    - Non-functional requirements (performance, style)
    - Constraints (time, budget, technology)
    - Success criteria (how to measure completion)
    - Assumptions (fill in gaps with reasonable defaults)
    """
    
    # Functional requirement patterns
    action_verbs = ['create', 'build', 'make', 'develop', 'generate']
    features = extract_pattern(r'(with|that has|including) ([^.,]+)')
    
    # Constraint extraction
    tech_stack = extract_pattern(r'(using|with|in) (Python|React|Node\.js|etc)')
    time_constraint = extract_pattern(r'(by|within|in) (\d+ (days|hours|weeks))')
    
    # Implicit assumptions
    if 'website' in text and 'tech stack' not in text:
        assumptions.append('Assuming modern web stack (React/Vue/Svelte)')
    
    return {
        'functional': ['Feature 1', 'Feature 2'],
        'non_functional': ['Performance: Fast', 'Style: Minimal'],
        'constraints': ['Time: 2 weeks', 'Tech: Python'],
        'success_criteria': ['User can do X', 'Output matches Y'],
        'assumptions': ['Modern browser support'],
        'missing_info': ['Color scheme', 'Authentication method']
    }
```

---

### Tool 4: `promptcraft_suggest_examples`

**Purpose:** Recommend example-driven prompting

**Heuristics:**
```python
def suggest_example_addition(text: str) -> Dict:
    """
    Detects when examples would improve prompt clarity.
    
    Triggers:
    - Abstract concepts without concrete examples
    - Style/tone requests without samples
    - Format requests without templates
    - "Like X" comparisons without showing X
    """
    
    # Pattern: "in the style of" without example
    has_style_reference = bool(re.search(r'(style|tone|like|similar to)', text))
    has_example = bool(re.search(r'(for example|e\.g\.|such as)', text))
    
    if has_style_reference and not has_example:
        return {
            'recommendation': 'Add concrete example',
            'template': '''
                Original: "Write in a casual tone"
                Improved: "Write in a casual tone, like this example:
                         'Hey there! Just wanted to share...'
                         (friendly, conversational, uses contractions)"
            '''
        }
    
    # Pattern: Format request without template
    if 'format' in text.lower() and not has_example:
        return {
            'recommendation': 'Provide format template',
            'template': 'Specify exact structure with placeholders'
        }
```

---

### Tool 5: `promptcraft_decompose_task`

**Purpose:** Break complex prompts into subtasks

**Heuristics:**
```python
def detect_complex_task(text: str) -> Dict:
    """
    Identifies prompts that should be broken into steps.
    
    Complexity indicators:
    - Multiple "and" conjunctions (>3)
    - Different domains in one prompt (code + design + deployment)
    - Sequential dependencies ("first X then Y then Z")
    - Large scope verbs ("complete", "entire", "full")
    """
    
    # Count conjunctions
    and_count = text.lower().count(' and ')
    
    # Multi-domain detection
    domains = {
        'code': ['function', 'class', 'API', 'database'],
        'design': ['UI', 'layout', 'colors', 'font'],
        'deployment': ['deploy', 'host', 'server', 'cloud'],
        'testing': ['test', 'validate', 'verify'],
    }
    
    active_domains = sum(
        1 for keywords in domains.values() 
        if any(k in text.lower() for k in keywords)
    )
    
    if active_domains >= 3 or and_count >= 4:
        return {
            'complexity': 'high',
            'recommendation': 'Break into phases',
            'suggested_phases': [
                'Phase 1: Core functionality',
                'Phase 2: UI/UX',
                'Phase 3: Testing',
                'Phase 4: Deployment'
            ]
        }
```

---

### Tool 6: `promptcraft_check_specificity`

**Purpose:** Score prompts on specificity dimensions

**Heuristics:**
```python
def calculate_specificity_score(text: str) -> Dict:
    """
    Multi-dimensional specificity analysis.
    
    Dimensions:
    - Who: Target audience specified?
    - What: Clear deliverable defined?
    - When: Timeframe mentioned?
    - Where: Context/platform specified?
    - Why: Purpose/goal stated?
    - How: Method/approach indicated?
    """
    
    scores = {
        'who': check_audience(text),      # 0.0-1.0
        'what': check_deliverable(text),  # 0.0-1.0
        'when': check_timeframe(text),    # 0.0-1.0
        'where': check_context(text),     # 0.0-1.0
        'why': check_purpose(text),       # 0.0-1.0
        'how': check_method(text),        # 0.0-1.0
    }
    
    overall = sum(scores.values()) / len(scores)
    
    return {
        'overall_score': overall,
        'dimension_scores': scores,
        'weakest_dimensions': sorted(scores, key=scores.get)[:2],
        'improvement_priority': [
            f"Add {dim}: {suggestion}" 
            for dim, score in scores.items() 
            if score < 0.5
        ]
    }
```

---

## 🏗️ Project Structure

```
prompt-improver/
├── promptcraft_mcp.py          # Main MCP server
├── requirements.txt             # Dependencies (mcp, pydantic)
├── README.md                    # Documentation
├── ARCHITECTURE.md              # Design decisions
├── claude_desktop_config.json   # Integration config
├── test_examples.py             # Test cases
├── heuristics/                  # Detection modules
│   ├── __init__.py
│   ├── vagueness.py            # Vague prompt detection
│   ├── frustration.py          # Frustration pattern detection
│   ├── requirements.py         # Requirement extraction
│   ├── examples.py             # Example suggestion
│   ├── decomposition.py        # Task breakdown
│   └── specificity.py          # Specificity scoring
├── utils/                       # Helper utilities
│   ├── __init__.py
│   ├── text_analysis.py        # Text processing utilities
│   ├── similarity.py           # Levenshtein, cosine similarity
│   └── patterns.py             # Common regex patterns
└── tests/                       # Unit tests
    ├── test_vagueness.py
    ├── test_frustration.py
    └── test_integration.py
```

---

## 🎨 Heuristic Design Philosophy

### **Why Heuristics Over LLMs?**

1. **Privacy:** No data sent to external APIs
2. **Latency:** Instant analysis (<100ms)
3. **Cost:** Zero API costs
4. **Determinism:** Same input = same output
5. **Explainability:** Clear rules, easy to debug
6. **Control:** No hallucinations or drift

### **Evolution Path:**

```
Phase 1: Pure Heuristics (Launch)
  ↓
Phase 2: Lightweight ML (Logistic Regression, Decision Trees)
  - Train on collected examples
  - Still local, fast inference
  ↓
Phase 3: Hybrid Approach
  - Heuristics for simple cases (90%)
  - Small transformer for edge cases (10%)
  - Local model, no API calls
  ↓
Phase 4: Federated Learning (Optional)
  - Learn from user corrections
  - Privacy-preserving model updates
```

---

## 📊 Test Cases & Examples

### Test Case 1: Vague Prompt
```python
Input: "Make the code better"
History: ["Write a Python function to sort numbers"]

Expected Output:
  Vagueness: CRITICAL (0.95)
  Issues:
    - Pronoun "the code" - which code?
    - Vague verb "make better" - how?
  
  Improved:
    "Improve the Python sorting function by:
     1. Using merge sort instead of bubble sort (O(n log n) time)
     2. Adding type hints for better IDE support
     3. Including docstring with usage examples
     4. Handling edge cases: empty list, single element
     Success: Passes all test cases, runs 2x faster"
```

### Test Case 2: Frustration Pattern
```python
History:
  1. "Create a login page"
  2. "Create a login page with email"
  3. "Create a login page with email and password"
  4. "Please create a login page with email, password, and remember me"

Expected Output:
  Frustration: HIGH
  Pattern: Escalating specificity
  
  Root Cause: Incomplete initial requirements
  
  Suggested Restart:
    "Create a login page with these specifications:
     
     Fields:
     - Email (validated with regex)
     - Password (min 8 chars, hidden)
     - 'Remember me' checkbox
     
     Actions:
     - Submit button (primary CTA)
     - 'Forgot password?' link
     - 'Sign up' redirect
     
     Behavior:
     - Show inline validation errors
     - Disable submit until valid
     - Redirect to /dashboard on success
     
     Styling:
     - Center-aligned form
     - Minimal design (no background images)
     - Responsive (mobile-friendly)
     
     Tech: React + Tailwind CSS"
```

### Test Case 3: Missing Context
```python
Input: "Add dark mode support"
History: []  # No context

Expected Output:
  Context Missing: YES
  
  Questions to Ask:
    - What technology stack? (React, Vue, vanilla JS?)
    - What's the current styling approach? (CSS, SCSS, Tailwind?)
    - Should it persist? (localStorage, cookies, database?)
    - Toggle location? (navbar, settings page, both?)
    - Color scheme preferences? (custom colors or preset theme?)
  
  Template:
    "Add dark mode to [YOUR APP] with:
     - Toggle: [location]
     - Persistence: [method]
     - Colors: [specify palette]
     - Scope: [which components]
     - Default: [light/dark/system]"
```

---

## 🔧 Implementation Details

### Data Structures

```python
# Vagueness Analysis Result
class VaguenessAnalysis(BaseModel):
    vagueness_score: float  # 0.0-1.0
    vague_elements: List[str]
    suggestions: List[str]
    improved_prompt: str
    missing_info: List[str]

# Frustration Detection Result
class FrustrationAnalysis(BaseModel):
    frustration_level: Literal['low', 'moderate', 'high', 'critical']
    patterns: List[str]  # ['repetition', 'escalation', 'negation']
    attempt_count: int
    root_cause: str
    suggested_restart: str

# Requirement Extraction Result
class RequirementExtraction(BaseModel):
    functional: List[str]
    non_functional: List[str]
    constraints: List[str]
    success_criteria: List[str]
    assumptions: List[str]
    missing_info: List[str]
    completeness_score: float
```

### Key Algorithms

```python
# Levenshtein distance for repetition detection
def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate edit distance between two strings."""
    # Dynamic programming implementation
    pass

# Context resolution
def resolve_pronouns(text: str, history: List[str]) -> str:
    """Replace pronouns with actual subjects from history."""
    # Find "it", "that", "this"
    # Search previous messages for likely referent
    # Replace with specific noun
    pass

# Requirement extraction
def extract_functional_requirements(text: str) -> List[str]:
    """Use dependency parsing to extract actions and objects."""
    # Pattern: verb + object
    # "create dashboard" → Functional: "Dashboard creation"
    pass
```

---

## 🚀 Development Roadmap

### **Phase 1: MVP (Week 1-2)**
- [ ] Set up project structure
- [ ] Implement vagueness detection
- [ ] Implement frustration detection
- [ ] Create basic test suite
- [ ] Write documentation
- [ ] Test with Claude Desktop

### **Phase 2: Enhancement (Week 3-4)**
- [ ] Add requirement extraction
- [ ] Add example suggestion
- [ ] Add task decomposition
- [ ] Add specificity scoring
- [ ] Expand test coverage
- [ ] Create demo video

### **Phase 3: Polish (Week 5-6)**
- [ ] Optimize heuristics based on testing
- [ ] Add more pattern matching rules
- [ ] Create comprehensive docs
- [ ] Build example use cases
- [ ] Prepare for launch

### **Phase 4: ML Integration (Month 2-3)**
- [ ] Collect training data from usage
- [ ] Train lightweight classifiers
- [ ] A/B test heuristics vs ML
- [ ] Keep best of both

---

## 💡 Additional Tool Ideas

### 7. `promptcraft_check_ambiguity`
- Detect multiple possible interpretations
- Suggest disambiguating questions

### 8. `promptcraft_estimate_complexity`
- Predict how long task will take LLM
- Warn if beyond single response capacity

### 9. `promptcraft_suggest_constraints`
- Recommend adding constraints based on domain
- "For code: Add language, style guide, testing requirements"

### 10. `promptcraft_validate_examples`
- Check if provided examples are consistent
- Detect contradictory example patterns

---

## 🎯 Success Metrics

### **User Metrics:**
- Average vagueness score improvement: Target >40%
- Frustration pattern detection rate: Target >80%
- User satisfaction with suggestions: Target >4/5

### **Technical Metrics:**
- Analysis latency: Target <50ms
- False positive rate: Target <10%
- False negative rate: Target <15%

### **Business Metrics:**
- Prompts improved per user per day: Target 5+
- Time saved per improved prompt: Target 2-5 min
- Adoption rate in teams: Target 60% active monthly users

---

## 🔐 Privacy & Security

### **Data Handling:**
- ✅ All analysis local (no external API calls)
- ✅ No prompt storage by default
- ✅ Optional: Anonymous analytics (prompt length, vagueness score)
- ✅ User control: Can disable all telemetry

### **Enterprise Considerations:**
- Self-hosted deployment option
- Air-gapped environment support
- No data exfiltration possible
- Audit logs for compliance

---

## 📦 Deliverables

1. **promptcraft_mcp.py** - Main MCP server (500-800 LOC)
2. **Heuristics modules** - 6 detection modules (~100 LOC each)
3. **Test suite** - 50+ test cases
4. **Documentation** - README, ARCHITECTURE, API docs
5. **Demo materials** - Video, example prompts, VC pitch deck
6. **Integration guide** - Claude Desktop, VS Code, Cursor

---

## 🤝 Synergy with ToGMAL

### **Combined Value Proposition:**

**ToGMAL:** Prevents LLM from giving bad advice  
**PromptCraft:** Prevents user from asking bad questions  

**Together:** Complete safety & quality layer for LLM workflows

### **Potential Integration:**

```python
# Combined analysis pipeline
1. User writes prompt
2. PromptCraft: "Your prompt is vague, here's improvement"
3. User revises prompt
4. LLM generates response
5. ToGMAL: "This response has medical advice without sources"
6. User gets safer, higher-quality output
```

### **Business Strategy:**

- **Bundle pricing:** ToGMAL + PromptCraft package
- **Enterprise suite:** Add monitoring, analytics, custom rules
- **Platform play:** Become the safety/quality layer for all LLM tools

---

**Next Steps:** Ready to implement? Let me know and I'll start creating the actual code structure!
