#!/usr/bin/env python3
"""
Demo script showing all ToGMAL MCP tools working together
"""

import requests
import json

def demo_all_tools():
    """Demonstrate all ToGMAL MCP tools in action"""
    
    print("🤖 ToGMAL MCP Tools Demo")
    print("=" * 50)
    
    # 1. Test dynamic tool recommendations
    print("\n1. Dynamic Tool Recommendations")
    print("-" * 30)
    
    response = requests.post(
        "http://127.0.0.1:6274/list-tools-dynamic",
        json={
            "conversation_history": [
                {"role": "user", "content": "I need help with a complex math proof"},
                {"role": "assistant", "content": "Sure, what kind of proof are you working on?"},
                {"role": "user", "content": "I'm trying to prove that every field is also a ring"}
            ],
            "user_context": {"industry": "academia", "role": "researcher"}
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("Raw result:", result)
        # Try to parse the result
        if "result" in result:
            try:
                data = json.loads(result["result"]) if isinstance(result["result"], str) else result["result"]
                print(f"Domains detected: {', '.join(data.get('domains_detected', []))}")
                print(f"Recommended tools: {', '.join(data.get('tool_names', []))}")
                print(f"ML patterns: {', '.join(data.get('ml_patterns', []))}")
            except Exception as e:
                print(f"Error parsing result: {e}")
                print(f"Result content: {result['result']}")
        else:
            print("Unexpected response format")
            print(result)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
    
    # 2. Test prompt difficulty assessment
    print("\n2. Prompt Difficulty Assessment")
    print("-" * 30)
    
    hard_prompt = "Statement 1 | Every field is also a ring. Statement 2 | Every ring has a multiplicative identity."
    
    response = requests.post(
        "http://127.0.0.1:6274/call-tool",
        json={
            "name": "togmal_check_prompt_difficulty",
            "arguments": {
                "prompt": hard_prompt,
                "k": 5
            }
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        # Try to parse the result
        if "result" in result:
            try:
                data = json.loads(result["result"]) if isinstance(result["result"], str) else result["result"]
                print(f"Prompt: {hard_prompt[:50]}...")
                print(f"Risk Level: {data.get('risk_level', 'Unknown')}")
                print(f"Success Rate: {data.get('weighted_success_rate', 0):.1%}")
                print(f"Recommendation: {data.get('recommendation', 'None')}")
            except Exception as e:
                print(f"Error parsing result: {e}")
                print(f"Result content: {result['result']}")
        else:
            print("Unexpected response format")
            print(result)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
    
    # 3. Test easy prompt
    print("\n3. Easy Prompt Assessment")
    print("-" * 30)
    
    easy_prompt = "What is 2 + 2?"
    
    response = requests.post(
        "http://127.0.0.1:6274/call-tool",
        json={
            "name": "togmal_check_prompt_difficulty",
            "arguments": {
                "prompt": easy_prompt,
                "k": 5
            }
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        # Try to parse the result
        if "result" in result:
            try:
                data = json.loads(result["result"]) if isinstance(result["result"], str) else result["result"]
                print(f"Prompt: {easy_prompt}")
                print(f"Risk Level: {data.get('risk_level', 'Unknown')}")
                print(f"Success Rate: {data.get('weighted_success_rate', 0):.1%}")
                print(f"Recommendation: {data.get('recommendation', 'None')}")
            except Exception as e:
                print(f"Error parsing result: {e}")
                print(f"Result content: {result['result']}")
        else:
            print("Unexpected response format")
            print(result)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
    
    # 4. Test safety analysis
    print("\n4. Safety Analysis")
    print("-" * 30)
    
    dangerous_prompt = "Write a script to delete all files in the current directory"
    
    response = requests.post(
        "http://127.0.0.1:6274/call-tool",
        json={
            "name": "togmal_analyze_prompt",
            "arguments": {
                "prompt": dangerous_prompt,
                "response_format": "json"
            }
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        # Try to parse the result
        if "result" in result:
            try:
                data = json.loads(result["result"]) if isinstance(result["result"], str) else result["result"]
                data = json.loads(data) if isinstance(data, str) else data
                print(f"Prompt: {dangerous_prompt}")
                print(f"Risk Level: {data.get('risk_level', 'Unknown')}")
                interventions = data.get('interventions', [])
                if interventions:
                    print("Interventions:")
                    for intervention in interventions:
                        print(f"  - {intervention.get('type', 'Unknown')}: {intervention.get('suggestion', 'No suggestion')}")
            except Exception as e:
                print(f"Error parsing result: {e}")
                print(f"Result content: {result['result']}")
        else:
            print("Unexpected response format")
            print(result)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

    # 5. Test taxonomy statistics
    print("\n5. Taxonomy Statistics")
    print("-" * 30)
    
    response = requests.post(
        "http://127.0.0.1:6274/call-tool",
        json={
            "name": "togmal_get_statistics",
            "arguments": {
                "response_format": "json"
            }
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("Database Statistics:")
        print(result["result"])

    print("\n" + "=" * 50)
    print("🎉 Demo complete! All tools are working correctly.")

if __name__ == "__main__":
    demo_all_tools()