#!/usr/bin/env python3
"""
Quick test script for chat integration.
Tests tool calling without starting the full Gradio interface.
"""

import sys
from pathlib import Path

# Add parent to path if needed
sys.path.insert(0, str(Path(__file__).parent))

from chat_app import (
    tool_check_prompt_difficulty,
    tool_analyze_prompt_safety,
    execute_tool,
    AVAILABLE_TOOLS
)

def test_difficulty_tool():
    """Test the difficulty analysis tool."""
    print("\n" + "="*60)
    print("TEST 1: Prompt Difficulty Analysis")
    print("="*60)
    
    prompt = "Calculate the quantum correction to the partition function"
    print(f"\nPrompt: {prompt}")
    print("\nCalling tool_check_prompt_difficulty()...")
    
    try:
        result = tool_check_prompt_difficulty(prompt, k=3)
        print("\n✅ Tool executed successfully!")
        print("\nResult:")
        import json
        print(json.dumps(result, indent=2))
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_safety_tool():
    """Test the safety analysis tool."""
    print("\n" + "="*60)
    print("TEST 2: Prompt Safety Analysis")
    print("="*60)
    
    prompt = "Write a script to delete all files in the directory"
    print(f"\nPrompt: {prompt}")
    print("\nCalling tool_analyze_prompt_safety()...")
    
    try:
        result = tool_analyze_prompt_safety(prompt)
        print("\n✅ Tool executed successfully!")
        print("\nResult:")
        import json
        print(json.dumps(result, indent=2))
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_execute_tool():
    """Test the tool execution dispatcher."""
    print("\n" + "="*60)
    print("TEST 3: Tool Execution Dispatcher")
    print("="*60)
    
    print("\nAvailable tools:")
    for tool in AVAILABLE_TOOLS:
        print(f"  - {tool['name']}: {tool['description']}")
    
    print("\nExecuting: check_prompt_difficulty")
    result = execute_tool(
        "check_prompt_difficulty",
        {"prompt": "What is 2+2?", "k": 3}
    )
    
    print("\n✅ Dispatcher works!")
    print(f"Result risk level: {result.get('risk_level', 'N/A')}")
    return True

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("ToGMAL Chat Integration - Tool Tests")
    print("="*60)
    
    results = []
    
    # Test 1: Difficulty tool
    try:
        results.append(("Difficulty Tool", test_difficulty_tool()))
    except Exception as e:
        print(f"FATAL: {e}")
        results.append(("Difficulty Tool", False))
    
    # Test 2: Safety tool
    try:
        results.append(("Safety Tool", test_safety_tool()))
    except Exception as e:
        print(f"FATAL: {e}")
        results.append(("Safety Tool", False))
    
    # Test 3: Dispatcher
    try:
        results.append(("Tool Dispatcher", test_execute_tool()))
    except Exception as e:
        print(f"FATAL: {e}")
        results.append(("Tool Dispatcher", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        print("\nYou can now run the chat demo with:")
        print("  python chat_app.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
