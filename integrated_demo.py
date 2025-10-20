#!/usr/bin/env python3
"""
Integrated ToGMAL MCP + Prompt Difficulty Demo
=============================================

Gradio demo that combines:
1. Prompt difficulty assessment using vector similarity
2. MCP server tools for safety analysis
3. Dynamic tool recommendations based on context

Shows real-time difficulty scores, safety analysis, and tool recommendations.
"""

import gradio as gr
import json
import asyncio
import requests
from pathlib import Path
from benchmark_vector_db import BenchmarkVectorDB

# Initialize the vector database
db = BenchmarkVectorDB(
    db_path=Path("./data/benchmark_vector_db"),
    embedding_model="all-MiniLM-L6-v2"
)

def analyze_prompt_difficulty(prompt: str, k: int = 5) -> str:
    """
    Analyze a prompt's difficulty using the vector database.
    
    Args:
        prompt: The user's prompt/question
        k: Number of similar questions to retrieve
    
    Returns:
        Formatted difficulty analysis results
    """
    if not prompt.strip():
        return "Please enter a prompt to analyze."
    
    try:
        # Query the vector database
        result = db.query_similar_questions(prompt, k=k)
        
        # Format results
        output = []
        output.append(f"## 🎯 Difficulty Assessment\n")
        output.append(f"**Risk Level**: {result['risk_level']}")
        output.append(f"**Success Rate**: {result['weighted_success_rate']:.1%}")
        output.append(f"**Avg Similarity**: {result['avg_similarity']:.3f}")
        output.append("")
        output.append(f"**Recommendation**: {result['recommendation']}")
        output.append("")
        output.append(f"## 🔍 Similar Benchmark Questions\n")
        
        for i, q in enumerate(result['similar_questions'], 1):
            output.append(f"{i}. **{q['question_text'][:100]}...**")
            output.append(f"   - Source: {q['source']} ({q['domain']})")
            output.append(f"   - Success Rate: {q['success_rate']:.1%}")
            output.append(f"   - Similarity: {q['similarity']:.3f}")
            output.append("")
        
        output.append(f"*Analyzed using {k} most similar questions from 14,042 benchmark questions*")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"Error analyzing prompt difficulty: {str(e)}"

def analyze_prompt_safety(prompt: str, response_format: str = "markdown") -> str:
    """
    Analyze a prompt for safety issues using the MCP server via HTTP facade.
    
    Args:
        prompt: The user's prompt to analyze
        response_format: Output format ("markdown" or "json")
    
    Returns:
        Formatted safety analysis results
    """
    try:
        # Call the MCP server via HTTP facade
        response = requests.post(
            "http://127.0.0.1:6274/call-tool",
            json={
                "name": "togmal_analyze_prompt",
                "arguments": {
                    "prompt": prompt,
                    "response_format": response_format
                }
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("result", "No result returned")
        else:
            return f"Error calling MCP server: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Error analyzing prompt safety: {str(e)}"

def get_dynamic_tools(conversation_text: str) -> str:
    """
    Get recommended tools based on conversation context.
    
    Args:
        conversation_text: Simulated conversation history
    
    Returns:
        Formatted tool recommendations
    """
    try:
        # Convert text to conversation history format
        conversation_history = []
        if conversation_text.strip():
            # Simple split by lines for demo
            lines = conversation_text.strip().split('\n')
            for i, line in enumerate(lines):
                role = "user" if i % 2 == 0 else "assistant"
                conversation_history.append({
                    "role": role,
                    "content": line
                })
        
        # Call the MCP server via HTTP facade
        response = requests.post(
            "http://127.0.0.1:6274/list-tools-dynamic",
            json={
                "conversation_history": conversation_history if conversation_history else None,
                "user_context": {"industry": "technology"}
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            result_data = result.get("result", {})
            
            # Parse if it's a JSON string
            if isinstance(result_data, str):
                try:
                    result_data = json.loads(result_data)
                except:
                    pass
            
            # Format results
            output = []
            output.append("## 🛠️ Dynamic Tool Recommendations\n")
            
            if isinstance(result_data, dict):
                output.append(f"**Mode**: {result_data.get('mode', 'unknown')}")
                output.append(f"**Domains Detected**: {', '.join(result_data.get('domains_detected', [])) or 'None'}")
                output.append("")
                output.append("**Recommended Tools**:")
                for tool in result_data.get('tool_names', []):
                    output.append(f"- `{tool}`")
                output.append("")
                output.append("**Recommended Checks**:")
                for check in result_data.get('check_names', []):
                    output.append(f"- `{check}`")
                
                if result_data.get('ml_patterns'):
                    output.append("")
                    output.append("**ML-Discovered Patterns**:")
                    for pattern in result_data.get('ml_patterns', []):
                        output.append(f"- `{pattern}`")
            else:
                output.append(str(result_data))
            
            return "\n".join(output)
        else:
            return f"Error calling MCP server: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Error getting dynamic tools: {str(e)}"

def integrated_analysis(prompt: str, k: int = 5, conversation_context: str = "") -> tuple:
    """
    Perform integrated analysis combining difficulty assessment, safety analysis, and tool recommendations.
    
    Args:
        prompt: The user's prompt to analyze
        k: Number of similar questions to retrieve for difficulty assessment
        conversation_context: Simulated conversation history
    
    Returns:
        Tuple of (difficulty_analysis, safety_analysis, tool_recommendations)
    """
    difficulty_result = analyze_prompt_difficulty(prompt, k)
    safety_result = analyze_prompt_safety(prompt, "markdown")
    tools_result = get_dynamic_tools(conversation_context)
    
    return difficulty_result, safety_result, tools_result

# Create Gradio interface
with gr.Blocks(title="ToGMAL Integrated Demo") as demo:
    gr.Markdown("# 🧠 ToGMAL Integrated Demo")
    gr.Markdown("Combines prompt difficulty assessment, safety analysis, and dynamic tool recommendations.")
    
    with gr.Row():
        with gr.Column():
            prompt_input = gr.Textbox(
                label="Enter your prompt",
                placeholder="e.g., Calculate the quantum correction to the partition function...",
                lines=3
            )
            k_slider = gr.Slider(
                minimum=1,
                maximum=10,
                value=5,
                step=1,
                label="Number of similar questions to show"
            )
            context_input = gr.TextArea(
                label="Conversation Context (optional)",
                placeholder="Enter previous conversation messages (one per line)",
                lines=3
            )
            submit_btn = gr.Button("Analyze Prompt")
        
        with gr.Column():
            difficulty_output = gr.Markdown(label="Difficulty Assessment")
            safety_output = gr.Markdown(label="Safety Analysis")
            tools_output = gr.Markdown(label="Tool Recommendations")
    
    # Examples
    gr.Examples(
        examples=[
            ["Calculate the quantum correction to the partition function for a 3D harmonic oscillator", 5, ""],
            ["Prove that there are infinitely many prime numbers", 5, ""],
            ["Diagnose a patient with acute chest pain and shortness of breath", 5, ""],
            ["What is 2 + 2?", 5, ""],
            ["Write a program to delete all files in the current directory", 5, "User wants to clean up their computer"],
        ],
        inputs=[prompt_input, k_slider, context_input]
    )
    
    # Event handling
    submit_btn.click(
        fn=integrated_analysis,
        inputs=[prompt_input, k_slider, context_input],
        outputs=[difficulty_output, safety_output, tools_output]
    )
    
    prompt_input.submit(
        fn=integrated_analysis,
        inputs=[prompt_input, k_slider, context_input],
        outputs=[difficulty_output, safety_output, tools_output]
    )

if __name__ == "__main__":
    # Check if HTTP facade is running
    try:
        response = requests.get("http://127.0.0.1:6274/")
        print("✅ HTTP facade is running")
    except:
        print("⚠️  HTTP facade is not running. Please start it with: python http_facade.py")
    
    demo.launch(share=True, server_port=7862)
