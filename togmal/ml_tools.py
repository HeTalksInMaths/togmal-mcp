"""
Dynamically generate tools from ML clustering results
"""

from typing import List, Optional
import json
from pathlib import Path

ML_TOOLS_CACHE_PATH = Path("./data/ml_discovered_tools.json")

async def get_ml_discovered_tools(
    relevant_domains: Optional[List[str]] = None,
    min_confidence: float = 0.8
) -> List[dict]:
    """
    Load ML-discovered limitation checks from cache.

    Args:
        relevant_domains: Only return tools for these domains (None = all)
        min_confidence: Minimum confidence threshold

    Returns:
        List of dict definitions for dynamically discovered checks
    """
    if not ML_TOOLS_CACHE_PATH.exists():
        return []

    with open(ML_TOOLS_CACHE_PATH) as f:
        ml_patterns = json.load(f)

    tools = []

    for pattern in ml_patterns.get("patterns", []):
        domain = pattern.get("domain")

        # Filter by relevant domains
        if relevant_domains and domain not in relevant_domains:
            continue

        # Only include high-confidence patterns
        if float(pattern.get("confidence", 0)) < float(min_confidence):
            continue

        tools.append({
            "name": f"check_{pattern['id']}",
            "domain": domain,
            "description": pattern["description"],
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "response": {"type": "string"}
                },
                "required": ["prompt", "response"]
            },
            "heuristic": pattern.get("heuristic", ""),
            "examples": pattern.get("examples", [])
        })

    return tools


async def update_ml_tools_cache(research_pipeline_output: dict) -> None:
    """
    Called by research pipeline to update available ML tools

    Args:
        research_pipeline_output: Latest clustering/anomaly detection results
    """
    # Extract high-confidence patterns
    patterns = []

    for cluster in research_pipeline_output.get("clusters", []):
        if cluster.get("is_dangerous", False) and float(cluster.get("purity", 0)) > 0.7:
            pattern = {
                "id": cluster["id"],
                "domain": cluster.get("domain", "general"),
                "description": f"Check for {cluster.get('pattern_description', 'unknown pattern')}",
                "confidence": float(cluster["purity"]),
                "heuristic": cluster.get("detection_rule", ""),
                "examples": (cluster.get("examples", []) or [])[:3]
            }
            patterns.append(pattern)

    # Save to cache
    ML_TOOLS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ML_TOOLS_CACHE_PATH, 'w') as f:
        json.dump({
            "updated_at": research_pipeline_output.get("timestamp"),
            "patterns": patterns
        }, f, indent=2)
