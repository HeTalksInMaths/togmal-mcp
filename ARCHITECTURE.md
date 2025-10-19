# ToGMAL Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claude Desktop                          │
│                    (or other MCP Client)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ stdio/MCP Protocol
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     ToGMAL MCP Server                           │
│                    (togmal_mcp.py)                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   MCP Tools Layer                         │  │
│  │  - togmal_analyze_prompt                                 │  │
│  │  - togmal_analyze_response                               │  │
│  │  - togmal_submit_evidence                                │  │
│  │  - togmal_get_taxonomy                                   │  │
│  │  - togmal_get_statistics                                 │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     │                                           │
│  ┌──────────────────▼───────────────────────────────────────┐  │
│  │              Detection Heuristics                         │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Math/Physics Speculation Detector                 │  │  │
│  │  │  - Pattern: "theory of everything"                 │  │  │
│  │  │  - Pattern: "new equation"                         │  │  │
│  │  │  - Pattern: excessive notation                     │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Ungrounded Medical Advice Detector                │  │  │
│  │  │  - Pattern: "you probably have"                    │  │  │
│  │  │  - Pattern: "take Xmg"                            │  │  │
│  │  │  - Check: has_sources                              │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Dangerous File Operations Detector                │  │  │
│  │  │  - Pattern: "rm -rf"                              │  │  │
│  │  │  - Pattern: recursive deletion                     │  │  │
│  │  │  - Check: has_safeguards                          │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Vibe Coding Overreach Detector                   │  │  │
│  │  │  - Pattern: "complete app"                         │  │  │
│  │  │  - Pattern: large line counts                      │  │  │
│  │  │  - Check: has_planning                            │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Unsupported Claims Detector                       │  │  │
│  │  │  - Pattern: "always/never"                         │  │  │
│  │  │  - Pattern: statistics without source              │  │  │
│  │  │  - Check: has_hedging                             │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     │                                           │
│  ┌──────────────────▼───────────────────────────────────────┐  │
│  │           Risk Assessment & Interventions                 │  │
│  │  - Calculate weighted risk score                         │  │
│  │  - Map to risk levels (LOW → CRITICAL)                  │  │
│  │  - Recommend interventions                               │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     │                                           │
│  ┌──────────────────▼───────────────────────────────────────┐  │
│  │              Taxonomy Database                            │  │
│  │  - In-memory storage (extendable to persistent)          │  │
│  │  - Evidence entries with metadata                        │  │
│  │  - Filtering and pagination                              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow - Prompt Analysis

```
User Prompt
    │
    ├─────────────────────────────────────────────┐
    │                                             │
    ▼                                             │
togmal_analyze_prompt                             │
    │                                             │
    ├──► Math/Physics Detector ──► Result 1      │
    │                                             │
    ├──► Medical Advice Detector ──► Result 2    │
    │                                             │
    ├──► File Ops Detector ──► Result 3          │
    │                                             │
    ├──► Vibe Coding Detector ──► Result 4       │
    │                                             │
    └──► Unsupported Claims Detector ──► Result 5│
                                                  │
    ┌─────────────────────────────────────────────┘
    │
    ▼
Risk Calculation
    │
    ├─► Weight results
    ├─► Calculate score
    └─► Map to risk level
        │
        ▼
Intervention Recommendation
    │
    ├─► Step breakdown?
    ├─► Human-in-loop?
    ├─► Web search?
    └─► Simplified scope?
        │
        ▼
Format Response (Markdown/JSON)
    │
    └──► Return to Client
```

## Detection Pipeline

```
Input Text
    │
    ▼
┌───────────────────────────┐
│   Preprocessing           │
│   - Lowercase             │
│   - Strip whitespace      │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│   Pattern Matching        │
│   - Regex patterns        │
│   - Keyword detection     │
│   - Structural analysis   │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│   Confidence Scoring      │
│   - Count matches         │
│   - Weight by type        │
│   - Normalize to [0,1]    │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│   Context Checks          │
│   - has_sources?          │
│   - has_hedging?          │
│   - has_safeguards?       │
└───────────┬───────────────┘
            │
            ▼
Detection Result
{
  detected: bool,
  categories: list,
  confidence: float,
  metadata: dict
}
```

## Risk Calculation Algorithm

```
For each detection category:
    
    Math/Physics:
        risk += confidence × 0.5
    
    Medical Advice:
        risk += confidence × 1.5  # Highest weight
    
    File Operations:
        risk += confidence × 2.0  # Critical actions
    
    Vibe Coding:
        risk += confidence × 0.4
    
    Unsupported Claims:
        risk += confidence × 0.3

Total Risk Score:
    
    ≥ 1.5 → CRITICAL
    ≥ 1.0 → HIGH
    ≥ 0.5 → MODERATE
    < 0.5 → LOW
```

## Intervention Decision Tree

```
                    Detection Results
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
  Math/Physics?     Medical Advice?   File Operations?
        │                 │                 │
        ├─► Yes           ├─► Yes           ├─► Yes
        │   │             │   │             │   │
        │   ├─► Step      │   ├─► Human    │   ├─► Human
        │   │   Breakdown │   │   in Loop   │   │   in Loop
        │   │             │   │             │   │
        │   └─► Web       │   └─► Web       │   └─► Step
        │       Search    │       Search    │       Breakdown
        │                 │                 │
        └─► No            └─► No            └─► No
            │                 │                 │
            ▼                 ▼                 ▼
      Continue          Continue          Continue

                    ┌───────────┐
                    │  Combine  │
                    │  Results  │
                    └─────┬─────┘
                          │
                          ▼
              Intervention List
              (deduplicated)
```

## Taxonomy Database Schema

```
TAXONOMY_DB = {
    "category_name": [
        {
            "id": "abc123def456",
            "category": "math_physics_speculation",
            "prompt": "User's prompt text...",
            "response": "LLM's response text...",
            "description": "Why problematic...",
            "severity": "high",
            "timestamp": "2025-10-18T00:00:00",
            "prompt_hash": "a1b2c3d4"
        },
        { ... more entries ... }
    ],
    "another_category": [ ... ]
}

Indices:
- By category (dict key)
- By severity (filter)
- By timestamp (sort)
- By hash (deduplication)
```

## Component Responsibilities

### MCP Tools Layer
**Responsibilities:**
- Input validation (Pydantic models)
- Parameter extraction
- Tool orchestration
- Response formatting
- Character limit enforcement

**Does NOT:**
- Perform detection logic
- Calculate risk scores
- Store data directly

### Detection Heuristics Layer
**Responsibilities:**
- Pattern matching
- Confidence scoring
- Context analysis
- Detection result generation

**Does NOT:**
- Make intervention decisions
- Format responses
- Handle I/O

### Risk Assessment Layer
**Responsibilities:**
- Aggregate detection results
- Calculate weighted risk scores
- Map scores to risk levels
- Generate intervention recommendations

**Does NOT:**
- Perform detection
- Format responses
- Store data

### Taxonomy Database
**Responsibilities:**
- Store evidence entries
- Support filtering/pagination
- Provide statistics
- Maintain capacity limits

**Does NOT:**
- Perform analysis
- Make decisions
- Format responses

## Extension Points

### Adding New Detection Categories

```python
# 1. Add enum value
class CategoryType(str, Enum):
    NEW_CATEGORY = "new_category"

# 2. Create detector function
def detect_new_category(text: str) -> Dict[str, Any]:
    patterns = { ... }
    # Detection logic
    return {
        'detected': bool,
        'categories': list,
        'confidence': float
    }

# 3. Update analysis functions
def analyze_prompt(params):
    results['new_category'] = detect_new_category(params.prompt)
    # ... rest of logic

# 4. Update risk calculation
def calculate_risk_level(results):
    if results['new_category']['detected']:
        risk_score += results['new_category']['confidence'] * WEIGHT

# 5. Add intervention logic
def recommend_interventions(results):
    if results['new_category']['detected']:
        interventions.append({ ... })
```

### Adding Persistent Storage

```python
# 1. Define storage backend
class TaxonomyStorage:
    def save(self, category, entry): ...
    def load(self, category, filters): ...
    def get_stats(self): ...

# 2. Replace in-memory dict
storage = TaxonomyStorage(backend="sqlite")  # or "postgres", "mongodb"

# 3. Update tool functions
@mcp.tool()
async def submit_evidence(params):
    # Instead of: TAXONOMY_DB[category].append(entry)
    await storage.save(params.category, entry)
```

### Adding ML Models

```python
# 1. Define model interface
class AnomalyDetector:
    def fit(self, X): ...
    def predict(self, x) -> float: ...

# 2. Train from taxonomy
detector = AnomalyDetector()
training_data = get_training_data_from_taxonomy()
detector.fit(training_data)

# 3. Use in detection
def detect_with_ml(text: str) -> float:
    features = extract_features(text)
    anomaly_score = detector.predict(features)
    return anomaly_score
```

## Performance Characteristics

### Time Complexity
- **Pattern Matching**: O(n) where n = text length
- **All Detectors**: O(n) (parallel constant time)
- **Risk Calculation**: O(1) (fixed number of categories)
- **Taxonomy Query**: O(m·log m) where m = matching entries
- **Overall**: O(n + m·log m)

### Space Complexity
- **Server Base**: ~50 MB
- **Per Request**: ~1 KB (temporary)
- **Per Taxonomy Entry**: ~1 KB
- **Total with 1000 entries**: ~51 MB

### Latency
- **Single Detection**: ~10-50 ms
- **All Detections**: ~50-100 ms
- **Format Response**: ~1-10 ms
- **Total Per Request**: ~100-150 ms

## Security Considerations

### Input Validation
```
User Input
    │
    ▼
Pydantic Model
    │
    ├─► Type checking
    ├─► Length limits
    ├─► Pattern validation
    └─► Field constraints
        │
        ▼
    Valid Input
```

### Privacy Protection
```
┌────────────────────────────────────┐
│  NO External API Calls             │
│  NO Data Transmission              │
│  NO Logging Sensitive Info         │
│  YES Local Processing Only         │
│  YES User Consent Required         │
│  YES Data Stays on Device          │
└────────────────────────────────────┘
```

### Human-in-the-Loop
```
Sensitive Operation Detected
    │
    ▼
Request User Confirmation
    │
    ├─► Yes → Proceed
    │
    └─► No → Cancel
```

## Scalability Path

### Current: Single Instance
```
Client → stdio → ToGMAL Server → Response
```

### Future: HTTP Transport
```
Multiple Clients → HTTP → ToGMAL Server → Response
                          ↓
                    Shared Database
```

### Advanced: Distributed
```
Clients → Load Balancer → ToGMAL Servers (N)
                              ↓
                        Shared Database
                              ↓
                        ML Model Cache
```

## Monitoring Points

```
┌─────────────────────────────────────┐
│  Metrics to Track                   │
├─────────────────────────────────────┤
│  - Tool call frequency              │
│  - Detection rates by category      │
│  - Risk level distribution          │
│  - Intervention effectiveness       │
│  - False positive rate              │
│  - Response latency                 │
│  - Taxonomy growth rate             │
│  - User feedback submissions        │
└─────────────────────────────────────┘
```

---

This architecture supports:
- ✅ Privacy-preserving analysis
- ✅ Low-latency detection
- ✅ Extensible design
- ✅ Production readiness
- ✅ Future ML integration
