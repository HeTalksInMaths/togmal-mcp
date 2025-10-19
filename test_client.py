#!/usr/bin/env python3
"""
Simple test client for ToGMAL MCP Server
Demonstrates how to programmatically interact with the server
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_togmal():
    """Test the ToGMAL MCP server."""
    
    print("🚀 Starting ToGMAL MCP Client Test\n")
    print("=" * 60)
    
    # Configure server connection
    server_params = StdioServerParameters(
        command="/Users/hetalksinmaths/togmal/.venv/bin/python",
        args=["/Users/hetalksinmaths/togmal/togmal_mcp.py"]
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize session
                await session.initialize()
                print("✅ Connected to ToGMAL MCP Server\n")
                
                # List available tools
                tools = await session.list_tools()
                print(f"📋 Available Tools ({len(tools.tools)}):")
                for tool in tools.tools:
                    print(f"   • {tool.name}")
                print()
                
                # Test 1: Analyze a speculative physics prompt
                print("=" * 60)
                print("TEST 1: Math/Physics Speculation Detection")
                print("=" * 60)
                
                test_prompt = "I've discovered a new theory of quantum gravity that unifies all forces using my equation E = mc³"
                print(f"Prompt: {test_prompt}\n")
                
                result = await session.call_tool(
                    "togmal_analyze_prompt",
                    arguments={
                        "prompt": test_prompt,
                        "response_format": "markdown"
                    }
                )
                print(result.content[0].text)
                print()
                
                # Test 2: Analyze medical advice
                print("=" * 60)
                print("TEST 2: Medical Advice Detection")
                print("=" * 60)
                
                test_response = "You definitely have the flu. Take 1000mg of vitamin C and you'll be fine."
                print(f"Response: {test_response}\n")
                
                result = await session.call_tool(
                    "togmal_analyze_response",
                    arguments={
                        "response": test_response,
                        "context": "I have a fever and sore throat",
                        "response_format": "markdown"
                    }
                )
                print(result.content[0].text)
                print()
                
                # Test 3: Get statistics
                print("=" * 60)
                print("TEST 3: Taxonomy Statistics")
                print("=" * 60)
                
                result = await session.call_tool(
                    "togmal_get_statistics",
                    arguments={"response_format": "markdown"}
                )
                print(result.content[0].text)
                print()
                
                print("=" * 60)
                print("✅ All tests completed successfully!")
                print("=" * 60)
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_togmal())
