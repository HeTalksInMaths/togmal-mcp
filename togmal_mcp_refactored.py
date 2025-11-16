#!/usr/bin/env python3
"""
ToGMAL MCP Server - Refactored for Skills Architecture
======================================================

Architecture: MCP provides DATA, Skills provide ANALYSIS

This MCP server provides:
- Data fetching from benchmark questions
- Error pattern retrieval
- Statistics and metadata

This MCP server does NOT provide:
- Risk analysis (moved to Skill)
- Pattern detection logic (moved to Skill)
- User warnings (moved to Skill)

The ToGMAL Skill handles all analysis and decision-making logic.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from lightweight_prompt_checker import LightweightPromptChecker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data store paths
DATASTORE_DIR = Path("./mcp_datastore")

# Initialize MCP server
server = Server("togmal-mcp")

# Initialize lightweight checker
lightweight_checker = LightweightPromptChecker()

# ============================================================================
# Data Loading Functions
# ============================================================================

def load_json(filename: str) -> Any:
    """Load JSON file from datastore"""
    path = DATASTORE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {filename}")

    with open(path, 'r') as f:
        return json.load(f)

# ============================================================================
# MCP Tool Handlers - Pure Data Fetching
# ============================================================================

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="quick_risk_check",
            description="LIGHTWEIGHT pre-screening tool: Fast pattern-based check to determine if a prompt needs deep ToGMAL analysis. Run this FIRST on every prompt. Uses regex patterns, no data needed. Returns risk level and whether to invoke full Skill analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The user's prompt to check for risk indicators"
                    }
                },
                "required": ["prompt"]
            }
        ),
        types.Tool(
            name="fetch_question",
            description="Fetch a specific benchmark question by ID. Returns question text, difficulty, success rate, model scores, and error patterns (if available).",
            inputSchema={
                "type": "object",
                "properties": {
                    "question_id": {
                        "type": "string",
                        "description": "Question ID (e.g., 'mmlu_pro_engineering_0001', 'ds1000_pandas_42')"
                    }
                },
                "required": ["question_id"]
            }
        ),
        types.Tool(
            name="query_questions",
            description="Query questions by filters (benchmark, difficulty, domain, with_errors). Returns matching questions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "benchmark": {
                        "type": "string",
                        "description": "Filter by benchmark: 'MMLU-Pro' or 'DS-1000'",
                        "enum": ["MMLU-Pro", "DS-1000"]
                    },
                    "difficulty": {
                        "type": "string",
                        "description": "Filter by difficulty level",
                        "enum": ["Easy", "Medium", "Hard", "Expert", "Nearly_Impossible"]
                    },
                    "domain": {
                        "type": "string",
                        "description": "Filter by domain (e.g., 'math', 'physics', 'Pandas', etc.)"
                    },
                    "with_errors": {
                        "type": "boolean",
                        "description": "If true, only return questions with error patterns"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
        types.Tool(
            name="get_universal_failures",
            description="Get questions that ALL models failed. These are universally difficult questions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
        types.Tool(
            name="get_error_patterns_catalog",
            description="Get catalog of all discovered error patterns (32 patterns from 4 sources: DS-1000, universal failures, CoT failures, ML-discovered).",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_statistics",
            description="Get summary statistics about the dataset (total questions, benchmarks, difficulty distribution, error analysis coverage, etc.).",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="search_by_domain",
            description="Search questions in a specific domain. Returns all questions for that domain.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name (e.g., 'math', 'physics', 'Pandas', 'engineering')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls"""

    if name == "quick_risk_check":
        prompt = arguments.get("prompt", "")
        result = lightweight_checker.quick_check(prompt)
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    elif name == "fetch_question":
        question_id = arguments.get("question_id")
        questions_by_id = load_json("questions_by_id.json")

        if question_id not in questions_by_id:
            return [types.TextContent(
                type="text",
                text=f"Question not found: {question_id}"
            )]

        question = questions_by_id[question_id]
        return [types.TextContent(
            type="text",
            text=json.dumps(question, indent=2)
        )]

    elif name == "query_questions":
        benchmark = arguments.get("benchmark")
        difficulty = arguments.get("difficulty")
        domain = arguments.get("domain")
        with_errors = arguments.get("with_errors", False)
        limit = arguments.get("limit", 10)

        # Start with all questions
        if benchmark:
            questions_by_benchmark = load_json("questions_by_benchmark.json")
            questions = questions_by_benchmark.get(benchmark, [])
        elif difficulty:
            questions_by_difficulty = load_json("questions_by_difficulty.json")
            questions = questions_by_difficulty.get(difficulty, [])
        elif domain:
            questions_by_domain = load_json("questions_by_domain.json")
            questions = questions_by_domain.get(domain, [])
        else:
            # No filter specified, return error
            return [types.TextContent(
                type="text",
                text="Please specify at least one filter: benchmark, difficulty, or domain"
            )]

        # Apply additional filters
        if with_errors:
            questions = [q for q in questions if len(q.get('error_patterns', [])) > 0]

        # Apply limit
        questions = questions[:limit]

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "count": len(questions),
                "questions": questions
            }, indent=2)
        )]

    elif name == "get_universal_failures":
        limit = arguments.get("limit", 10)
        universal_failures = load_json("universal_failures.json")
        results = universal_failures[:limit]

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "count": len(results),
                "total_universal_failures": len(universal_failures),
                "questions": results
            }, indent=2)
        )]

    elif name == "get_error_patterns_catalog":
        catalog = load_json("error_patterns_catalog.json")
        return [types.TextContent(
            type="text",
            text=json.dumps(catalog, indent=2)
        )]

    elif name == "get_statistics":
        stats = load_json("statistics.json")
        return [types.TextContent(
            type="text",
            text=json.dumps(stats, indent=2)
        )]

    elif name == "search_by_domain":
        domain = arguments.get("domain")
        limit = arguments.get("limit", 10)

        questions_by_domain = load_json("questions_by_domain.json")
        questions = questions_by_domain.get(domain, [])[:limit]

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "domain": domain,
                "count": len(questions),
                "questions": questions
            }, indent=2)
        )]

    else:
        raise ValueError(f"Unknown tool: {name}")

# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Run the MCP server"""
    # Verify datastore exists
    if not DATASTORE_DIR.exists():
        logger.error(f"Datastore not found at {DATASTORE_DIR}")
        logger.error("Please run build_mcp_datastore.py first")
        return

    logger.info("ToGMAL MCP Server (Refactored)")
    logger.info("Architecture: MCP for DATA, Skills for ANALYSIS")
    logger.info(f"Datastore: {DATASTORE_DIR}")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="togmal-mcp",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
