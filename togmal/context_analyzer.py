"""
Context analyzer for domain detection
Determines which limitation checks are relevant
"""

import re
from typing import List, Dict, Any, Optional
# from collections import Counter

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
            industry = str(user_context["industry"]).lower()
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
    domain_counts: Dict[str, float] = {}
    total_messages = len(conversation_history)

    for i, message in enumerate(conversation_history):
        content = message.get("content", "").lower()

        # Weight recent messages higher
        recency_weight = 1.0 + (i / total_messages) * (recent_weight - 1.0)

        for domain, keywords in DOMAIN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in content)
            domain_counts[domain] = domain_counts.get(domain, 0.0) + matches * recency_weight

    # Normalize scores
    max_count = max(domain_counts.values()) if domain_counts else 1.0
    return {
        domain: count / max_count
        for domain, count in domain_counts.items()
    }
