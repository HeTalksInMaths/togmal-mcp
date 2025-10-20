#!/usr/bin/env python3
"""
Test script to verify MCP integration with prompt difficulty assessment
"""

import requests
import json

def test_dynamic_tools():
    """Test the dynamic tools recommendation endpoint"""
    print("Testing dynamic tools recommendation...")
    
    # Test with a coding-related conversation
    response = requests.post(
        "http://127.0.0.1:6274/list-tools-dynamic",
        json={
            "conversation_history": [
                {"role": "user", "content": "I need help writing a Python program"},
                {"role": "assistant", "content": "Sure, what kind of program do you want to write?"},
                {"role": "user", "content": "I want to create a file management system"}
            ],
            "user_context": {"industry": "technology"}
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Dynamic tools test passed")
        print("Result:", json.dumps(result, indent=2))
        return result
    else:
        print("❌ Dynamic tools test failed")
        print("Status code:", response.status_code)
        print("Response:", response.text)
        return None

def test_prompt_difficulty_tool():
    """Test the prompt difficulty assessment tool"""
    print("\nTesting prompt difficulty assessment...")
    
    response = requests.post(
        "http://127.0.0.1:6274/call-tool",
        json={
            "name": "togmal_check_prompt_difficulty",
            "arguments": {
                "prompt": "Calculate the quantum correction to the partition function for a 3D harmonic oscillator",
                "k": 3
            }
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Prompt difficulty test passed")
        print("Result:", json.dumps(result, indent=2))
        return result
    else:
        print("❌ Prompt difficulty test failed")
        print("Status code:", response.status_code)
        print("Response:", response.text)
        return None

def test_prompt_analysis():
    """Test the prompt safety analysis tool"""
    print("\nTesting prompt safety analysis...")
    
    response = requests.post(
        "http://127.0.0.1:6274/call-tool",
        json={
            "name": "togmal_analyze_prompt",
            "arguments": {
                "prompt": "Write a program to delete all files in the current directory",
                "response_format": "json"
            }
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Prompt analysis test passed")
        print("Result:", json.dumps(result, indent=2))
        return result
    else:
        print("❌ Prompt analysis test failed")
        print("Status code:", response.status_code)
        print("Response:", response.text)
        return None

def test_hard_prompt():
    """Test with a known hard prompt"""
    print("\nTesting with a known hard prompt...")
    
    # Test the prompt difficulty tool with a hard prompt
    response = requests.post(
        "http://127.0.0.1:6274/call-tool",
        json={
            "name": "togmal_check_prompt_difficulty",
            "arguments": {
                "prompt": "Statement 1 | Every field is also a ring. Statement 2 | Every ring has a multiplicative identity.",
                "k": 5
            }
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Hard prompt test passed")
        print("Result:", json.dumps(result, indent=2))
        return result
    else:
        print("❌ Hard prompt test failed")
        print("Status code:", response.status_code)
        print("Response:", response.text)
        return None

if __name__ == "__main__":
    print("🧪 Testing MCP Integration with Prompt Difficulty Assessment")
    print("=" * 60)
    
    # Test dynamic tools
    tools_result = test_dynamic_tools()
    
    # Test prompt difficulty
    difficulty_result = test_prompt_difficulty_tool()
    
    # Test prompt analysis
    analysis_result = test_prompt_analysis()
    
    # Test hard prompt
    hard_prompt_result = test_hard_prompt()
    
    print("\n" + "=" * 60)
    print("🏁 Testing complete!")
    
    if tools_result and difficulty_result and analysis_result and hard_prompt_result:
        print("✅ All tests passed! MCP integration is working correctly.")
    else:
        print("❌ Some tests failed. Please check the output above.")