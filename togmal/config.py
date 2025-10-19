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
