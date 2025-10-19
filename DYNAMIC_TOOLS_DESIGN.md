# Dynamic Tool Exposure Design for ToGMAL MCP

**Date:** October 18, 2025  
**Status:** Design Proposal  
**Impact:** Moderate - improves efficiency, enables ML-driven tool discovery

---

## Problem Statement

Current ToGMAL MCP exposes **all 5 tools at startup**, regardless of conversation context:
- `check_math_physics`
- `check_medical_advice`  
- `check_file_operations`
- `check_code_quality`
- `check_claims`

**Issues:**
1. LLM must decide which tools are relevant (cognitive overhead)
2. Irrelevant tools clutter the tool list
3. No way to automatically add ML-discovered limitation checks
4. Fixed architecture doesn't scale to 10+ professional domains

---

## Proposed Solution

**Dynamic Tool Exposure** based on:
1. **Conversation context** (what domain is being discussed?)
2. **ML clustering results** (what new patterns were discovered?)
3. **User metadata** (what domains does this user work in?)

---

## Design Changes

### 1. Context-Aware Tool Filtering

**Current:**
```python
# server.py
@server.list_tools()
async def list_tools() -> list[Tool]:
    # Always returns all 5 tools
    return [
        Tool(name="check_math_physics", ...),
        Tool(name="check_medical_advice", ...),
        Tool(name="check_file_operations", ...),
        Tool(name="check_code_quality", ...),
        Tool(name="check_claims", ...),
    ]
```

**Proposed:**
```python
# server.py
from typing import Optional
from .context_analyzer import analyze_conversation_context

@server.list_tools()
async def list_tools(
    conversation_history: Optional[list[dict]] = None,
    user_context: Optional[dict] = None
) -> list[Tool]:
    """
    Dynamically expose tools based on conversation context
    
    Args:
        conversation_history: Recent messages for domain detection
        user_context: User metadata (role, industry, preferences)
    """
    # Detect relevant domains from conversation
    domains = await analyze_conversation_context(
        conversation_history=conversation_history,
        user_context=user_context
    )
    
    # Build tool list based on detected domains
    tools = []
    
    # Core tools (always available)
    tools.append(Tool(name="check_claims", ...))  # General-purpose
    
    # Domain-specific tools (conditional)
    if "mathematics" in domains or "physics" in domains:
        tools.append(Tool(name="check_math_physics", ...))
    
    if "medicine" in domains or "healthcare" in domains:
        tools.append(Tool(name="check_medical_advice", ...))
    
    if "coding" in domains or "file_system" in domains:
        tools.append(Tool(name="check_file_operations", ...))
        tools.append(Tool(name="check_code_quality", ...))
    
    # ML-discovered tools (dynamic)
    if ML_CLUSTERING_ENABLED:
        ml_tools = await get_ml_discovered_tools(domains)
        tools.extend(ml_tools)
    
    return tools
```

### 2. Context Analyzer Module

**New file:** `togmal/context_analyzer.py`

```python
"""
Context analyzer for domain detection
Determines which limitation checks are relevant
"""

import re
from typing import List, Dict, Any, Optional
from collections import Counter

# Domain keywords mapping
DOMAIN_KEYWORDS = {
    "mathematics": ["math", "calculus", "algebra", "geometry", "proof", "theorem", "equation"],
    "physics": ["physics", "force", "energy", "quantum", "relativity", "mechanics"],
    "medicine": ["medical", "diagnosis", "treatment", "symptom", "disease", "patient", "doctor"],
    "healthcare": ["health", "medication", "drug", "therapy", "clinical"],
    "law": ["legal", "law", "court", "regulation", "compliance", "attorney", "contract"],
    "finance": ["financial", "investment", "stock", "portfolio", "trading", "tax"],
    "coding": ["code", "programming", "function", "class", "debug", "git", "api"],
    "file_system": ["file", "directory", "path", "write", "delete", "permission"],
}

async def analyze_conversation_context(
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_context: Optional[Dict[str, Any]] = None,
    threshold: float = 0.3
) -> List[str]:
    """
    Analyze conversation to detect relevant domains
    
    Args:
        conversation_history: Recent messages [{"role": "user", "content": "..."}]
        user_context: User metadata {"industry": "healthcare", "role": "developer"}
        threshold: Minimum confidence to include domain (0-1)
    
    Returns:
        List of detected domains, e.g., ["mathematics", "coding"]
    """
    detected_domains = set()
    
    # Strategy 1: Keyword matching in conversation
    if conversation_history:
        domain_scores = _score_domains_by_keywords(conversation_history)
        
        # Add domains above threshold
        for domain, score in domain_scores.items():
            if score >= threshold:
                detected_domains.add(domain)
    
    # Strategy 2: User context hints
    if user_context:
        if "industry" in user_context:
            industry = user_context["industry"].lower()
            # Map industry to domains
            if "health" in industry or "medical" in industry:
                detected_domains.update(["medicine", "healthcare"])
            elif "tech" in industry or "software" in industry:
                detected_domains.add("coding")
            elif "finance" in industry or "bank" in industry:
                detected_domains.add("finance")
    
    # Strategy 3: Always include if explicitly mentioned in last message
    if conversation_history and len(conversation_history) > 0:
        last_message = conversation_history[-1].get("content", "").lower()
        
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in last_message for kw in keywords):
                detected_domains.add(domain)
    
    return list(detected_domains)


def _score_domains_by_keywords(
    conversation_history: List[Dict[str, str]],
    recent_weight: float = 2.0
) -> Dict[str, float]:
    """
    Score domains based on keyword frequency (recent messages weighted higher)
    
    Returns:
        Dict of {domain: score} normalized 0-1
    """
    domain_counts = Counter()
    total_messages = len(conversation_history)
    
    for i, message in enumerate(conversation_history):
        content = message.get("content", "").lower()
        
        # Weight recent messages higher
        recency_weight = 1.0 + (i / total_messages) * (recent_weight - 1.0)
        
        for domain, keywords in DOMAIN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in content)
            domain_counts[domain] += matches * recency_weight
    
    # Normalize scores
    max_count = max(domain_counts.values()) if domain_counts else 1
    return {
        domain: count / max_count
        for domain, count in domain_counts.items()
    }
```

### 3. ML-Discovered Tools Integration

**New file:** `togmal/ml_tools.py`

```python
"""
Dynamically generate tools from ML clustering results
"""

from typing import List, Optional
from mcp.types import Tool
import json
from pathlib import Path

ML_TOOLS_CACHE_PATH = Path("./data/ml_discovered_tools.json")

async def get_ml_discovered_tools(
    relevant_domains: Optional[List[str]] = None
) -> List[Tool]:
    """
    Load ML-discovered limitation checks as MCP tools
    
    Args:
        relevant_domains: Only return tools for these domains (None = all)
    
    Returns:
        List of dynamically generated Tool objects
    """
    if not ML_TOOLS_CACHE_PATH.exists():
        return []
    
    # Load ML-discovered patterns
    with open(ML_TOOLS_CACHE_PATH) as f:
        ml_patterns = json.load(f)
    
    tools = []
    
    for pattern in ml_patterns.get("patterns", []):
        domain = pattern.get("domain")
        
        # Filter by relevant domains
        if relevant_domains and domain not in relevant_domains:
            continue
        
        # Only include high-confidence patterns
        if pattern.get("confidence", 0) < 0.8:
            continue
        
        # Generate tool dynamically
        tool = Tool(
            name=f"check_{pattern['id']}",
            description=pattern["description"],
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "response": {"type": "string"}
                },
                "required": ["prompt", "response"]
            }
        )
        
        tools.append(tool)
    
    return tools


async def update_ml_tools_cache(research_pipeline_output: dict):
    """
    Called by research pipeline to update available ML tools
    
    Args:
        research_pipeline_output: Latest clustering/anomaly detection results
    """
    # Extract high-confidence patterns
    patterns = []
    
    for cluster in research_pipeline_output.get("clusters", []):
        if cluster.get("is_dangerous", False) and cluster.get("purity", 0) > 0.7:
            pattern = {
                "id": cluster["id"],
                "domain": cluster["domain"],
                "description": f"Check for {cluster['pattern_description']}",
                "confidence": cluster["purity"],
                "heuristic": cluster.get("detection_rule", ""),
                "examples": cluster.get("examples", [])[:3]
            }
            patterns.append(pattern)
    
    # Save to cache
    ML_TOOLS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ML_TOOLS_CACHE_PATH, 'w') as f:
        json.dump({
            "updated_at": research_pipeline_output["timestamp"],
            "patterns": patterns
        }, f, indent=2)
```

### 4. Tool Handler Registration

**Modified:** `togmal/server.py`

```python
# Dynamic handler registration for ML tools
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Route tool calls to appropriate handlers
    Supports both static and ML-discovered tools
    """
    # Static tools (existing)
    if name == "check_math_physics":
        return await check_math_physics(**arguments)
    elif name == "check_medical_advice":
        return await check_medical_advice(**arguments)
    # ... etc
    
    # ML-discovered tools (dynamic)
    elif name.startswith("check_ml_"):
        return await handle_ml_tool(name, arguments)
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_ml_tool(tool_name: str, arguments: dict) -> list[TextContent]:
    """
    Execute ML-discovered limitation check
    
    Args:
        tool_name: e.g., "check_ml_cluster_47"
        arguments: {"prompt": "...", "response": "..."}
    """
    # Load ML pattern definition
    pattern = await load_ml_pattern(tool_name)
    
    if not pattern:
        return [TextContent(
            type="text",
            text=f"Error: ML pattern not found for {tool_name}"
        )]
    
    # Run heuristic check
    result = await run_ml_heuristic(
        prompt=arguments["prompt"],
        response=arguments["response"],
        heuristic=pattern["heuristic"],
        examples=pattern["examples"]
    )
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]
```

---

## Configuration

**New file:** `togmal/config.py`

```python
"""Configuration for dynamic tool exposure"""

# Enable/disable dynamic behavior
DYNAMIC_TOOLS_ENABLED = True

# Enable ML-discovered tools
ML_CLUSTERING_ENABLED = True

# Context analysis settings
DOMAIN_DETECTION_THRESHOLD = 0.3  # 0-1, confidence required
CONVERSATION_HISTORY_LENGTH = 10  # How many messages to analyze

# ML tools settings
ML_TOOLS_MIN_CONFIDENCE = 0.8  # Only expose high-confidence patterns
ML_TOOLS_CACHE_TTL = 3600  # Seconds to cache ML tools

# Always-available tools (never filtered)
CORE_TOOLS = ["check_claims"]  # General-purpose checks
```

---

## Example Usage

### Before (Static)

```python
# LLM sees all 5 tools regardless of context
tools = [
    "check_math_physics",      # Not relevant
    "check_medical_advice",    # Not relevant
    "check_file_operations",   # RELEVANT
    "check_code_quality",      # RELEVANT
    "check_claims"             # RELEVANT
]

# User: "How do I delete all files in a directory?"
# LLM must reason about which tools to use
```

### After (Dynamic)

```python
# Conversation: "How do I delete all files in a directory?"
# Detected domains: ["coding", "file_system"]

tools = [
    "check_file_operations",   # ✅ Relevant
    "check_code_quality",      # ✅ Relevant
    "check_claims"             # ✅ Core tool
    # check_math_physics - filtered out
    # check_medical_advice - filtered out
]

# Cleaner tool list, LLM focuses on relevant checks
```

### With ML Tools

```python
# After research pipeline discovers new pattern:
# "Users frequently attempt dangerous recursive deletions"

# Next conversation about file operations:
tools = [
    "check_file_operations",
    "check_code_quality", 
    "check_claims",
    "check_ml_recursive_delete_danger"  # ✅ Auto-added by ML!
]
```

---

## Implementation Priority

**Phase 1 (Week 1):** Context analyzer
- Implement keyword-based domain detection
- Add conversation history parameter to `list_tools()`
- Test with existing 5 tools

**Phase 2 (Week 2):** ML tool integration
- Create `ml_tools.py` module
- Implement tool caching from research pipeline
- Dynamic handler registration

**Phase 3 (Week 3):** Optimization
- Add user context hints
- Improve domain detection accuracy
- Performance testing

---

## Benefits

1. **Reduced Cognitive Load:** LLM sees only relevant tools
2. **Scalability:** Can add 10+ domains without overwhelming LLM
3. **ML Integration:** Research pipeline automatically exposes new checks
4. **Efficiency:** Fewer irrelevant tool calls
5. **Personalization:** Tools adapt to user context

---

## Backward Compatibility

**Option 1 (Recommended):** Feature flag
```python
if DYNAMIC_TOOLS_ENABLED:
    tools = await list_tools_dynamic(conversation_history)
else:
    tools = await list_tools_static()  # Original behavior
```

**Option 2:** MCP protocol parameter
```python
# Client can request static or dynamic
@server.list_tools()
async def list_tools(mode: str = "dynamic") -> list[Tool]:
    if mode == "static":
        return ALL_TOOLS
    else:
        return filter_tools_by_context()
```

---

## Testing Strategy

```python
# tests/test_dynamic_tools.py

async def test_math_context_exposes_math_tool():
    conversation = [
        {"role": "user", "content": "What's the derivative of x^2?"}
    ]
    
    tools = await list_tools(conversation_history=conversation)
    tool_names = [t.name for t in tools]
    
    assert "check_math_physics" in tool_names
    assert "check_medical_advice" not in tool_names


async def test_medical_context_exposes_medical_tool():
    conversation = [
        {"role": "user", "content": "What are symptoms of diabetes?"}
    ]
    
    tools = await list_tools(conversation_history=conversation)
    tool_names = [t.name for t in tools]
    
    assert "check_medical_advice" in tool_names
    assert "check_math_physics" not in tool_names


async def test_ml_tool_added_after_research_update():
    # Simulate research pipeline discovering new pattern
    research_output = {
        "timestamp": "2025-10-18T10:00:00Z",
        "clusters": [
            {
                "id": "cluster_recursive_delete",
                "domain": "file_system",
                "is_dangerous": True,
                "purity": 0.92,
                "pattern_description": "recursive deletion without confirmation",
                "detection_rule": "check for 'rm -rf' or 'shutil.rmtree' without safeguards"
            }
        ]
    }
    
    await update_ml_tools_cache(research_output)
    
    # Check that new tool is exposed
    conversation = [{"role": "user", "content": "Delete all files recursively"}]
    tools = await list_tools(conversation_history=conversation)
    tool_names = [t.name for t in tools]
    
    assert "check_ml_cluster_recursive_delete" in tool_names
```

---

## Future Enhancements

1. **Semantic Analysis:** Use embeddings for domain detection (more accurate)
2. **User Learning:** Remember which tools user frequently needs
3. **Proactive Suggestions:** "This conversation may benefit from medical advice check"
4. **Tool Composition:** Combine multiple ML patterns into meta-tools
5. **A/B Testing:** Measure if dynamic exposure improves safety outcomes

---

## Decision

**Recommendation:** ✅ **Implement dynamic tool exposure**

**Rationale:**
- Essential for scaling beyond 5 tools
- Enables ML-driven tool discovery (key innovation!)
- Improves LLM efficiency
- Maintains backward compatibility
- Relatively low implementation cost (~1 week)

**When:** Implement in **Phase 2** of integration (after core ToGMAL-Aqumen bidirectional flow working)
