#!/usr/bin/env python3
"""
ToGMAL Chat Demo with MCP Tool Integration
==========================================

Interactive chat demo where a free LLM can call MCP tools to provide
informed responses about prompt difficulty, safety analysis, and more.

Features:
- Chat with Mistral-7B-Instruct (free via HuggingFace Inference API)
- LLM can call MCP tools to analyze prompts and assess difficulty
- Transparent tool calling with results shown to user
- No API key required (uses public Inference API)
"""

import gradio as gr
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from benchmark_vector_db import BenchmarkVectorDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the vector database (lazy loading)
db_path = Path("./data/benchmark_vector_db")
db = None

def get_db():
    """Lazy load the vector database."""
    global db
    if db is None:
        try:
            logger.info("Initializing BenchmarkVectorDB...")
            db = BenchmarkVectorDB(
                db_path=db_path,
                embedding_model="all-MiniLM-L6-v2"
            )
            logger.info("✓ BenchmarkVectorDB initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BenchmarkVectorDB: {e}")
            raise
    return db

# ============================================================================
# MCP TOOL FUNCTIONS (Local implementations)
# ============================================================================

def tool_check_prompt_difficulty(prompt: str, k: int = 5) -> Dict:
    """
    MCP Tool: Analyze prompt difficulty using vector database.
    
    Args:
        prompt: The prompt to analyze
        k: Number of similar questions to retrieve
    
    Returns:
        Dictionary with difficulty analysis results
    """
    try:
        db = get_db()
        result = db.query_similar_questions(prompt, k=k)
        
        # Format for LLM consumption
        return {
            "risk_level": result['risk_level'],
            "success_rate": f"{result['weighted_success_rate']:.1%}",
            "avg_similarity": f"{result['avg_similarity']:.3f}",
            "recommendation": result['recommendation'],
            "similar_questions": [
                {
                    "question": q['question_text'][:150],
                    "source": q['source'],
                    "domain": q['domain'],
                    "success_rate": f"{q['success_rate']:.1%}",
                    "similarity": f"{q['similarity']:.3f}"
                }
                for q in result['similar_questions'][:3]  # Top 3 only
            ]
        }
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}


def tool_analyze_prompt_safety(prompt: str) -> Dict:
    """
    MCP Tool: Analyze prompt for safety issues (heuristic-based).
    
    Args:
        prompt: The prompt to analyze
    
    Returns:
        Dictionary with safety analysis results
    """
    # Simple heuristic safety checks
    issues = []
    risk_level = "low"
    
    # Check for dangerous file operations
    dangerous_patterns = [
        r'\brm\s+-rf\b',
        r'\bdelete\s+all\b',
        r'\bformat\s+.*drive\b',
        r'\bdrop\s+database\b'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            issues.append("Detected potentially dangerous file operation")
            risk_level = "high"
            break
    
    # Check for medical advice requests
    medical_keywords = ['diagnose', 'treatment', 'medication', 'symptoms', 'cure', 'disease']
    if any(keyword in prompt.lower() for keyword in medical_keywords):
        issues.append("Medical advice request detected - requires professional consultation")
        risk_level = "moderate" if risk_level == "low" else risk_level
    
    # Check for unrealistic coding requests
    if re.search(r'\b(build|create|write)\s+.*\b(\d{3,})\s+(lines|functions|classes)', prompt, re.IGNORECASE):
        issues.append("Large-scale coding request - may exceed LLM capabilities")
        risk_level = "moderate" if risk_level == "low" else risk_level
    
    return {
        "risk_level": risk_level,
        "issues_found": len(issues),
        "issues": issues if issues else ["No significant safety concerns detected"],
        "recommendation": "Proceed with caution" if issues else "Prompt appears safe"
    }


# ============================================================================
# LLM BACKEND (HuggingFace Inference API)
# ============================================================================

def call_llm_with_tools(
    messages: List[Dict[str, str]],
    available_tools: List[Dict],
    model: str = "mistralai/Mistral-7B-Instruct-v0.2"
) -> Tuple[str, Optional[Dict]]:
    """
    Call LLM with tool calling capability.
    
    Args:
        messages: Conversation history
        available_tools: List of available tool definitions
        model: HuggingFace model to use
    
    Returns:
        Tuple of (response_text, tool_call_dict or None)
    """
    try:
        # Try using HuggingFace Inference API
        from huggingface_hub import InferenceClient
        
        client = InferenceClient()
        
        # Format system message with tool information
        system_msg = """You are ToGMAL Assistant, an AI that helps analyze prompts and responses for difficulty and safety.

You have access to these tools:
1. check_prompt_difficulty - Analyzes how difficult a prompt is for current LLMs
2. analyze_prompt_safety - Checks for safety issues in prompts

When a user asks about prompt difficulty, safety, or capabilities, use the appropriate tool.
To call a tool, respond with: TOOL_CALL: tool_name(arg1="value1", arg2="value2")

After a tool is called, you will receive: TOOL_RESULT: name=<tool_name> data=<json>
Use TOOL_RESULT to provide a helpful, comprehensive response to the user."""
        
        # Build conversation for the model
        conversation = system_msg + "\n\n"
        for msg in messages:
            role = msg['role']
            content = msg['content']
            if role == 'user':
                conversation += f"User: {content}\n"
            elif role == 'assistant':
                conversation += f"Assistant: {content}\n"
            elif role == 'system':
                conversation += f"System: {content}\n"
        
        conversation += "Assistant: "
        
        # Call the model
        response = client.text_generation(
            conversation,
            model=model,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.95,
            do_sample=True
        )
        
        response_text = response.strip()
        
        # Check if response contains a tool call
        tool_call = None
        if "TOOL_CALL:" in response_text:
            # Extract tool call
            match = re.search(r'TOOL_CALL:\s*(\w+)\((.*?)\)', response_text)
            if match:
                tool_name = match.group(1)
                args_str = match.group(2)
                
                # Parse arguments (simple key=value parsing)
                args = {}
                for arg in args_str.split(','):
                    if '=' in arg:
                        key, val = arg.split('=', 1)
                        key = key.strip()
                        val = val.strip().strip('"\'')
                        args[key] = val
                
                tool_call = {
                    "name": tool_name,
                    "arguments": args
                }
                
                # Remove tool call from visible response
                response_text = re.sub(r'TOOL_CALL:.*?\)', '', response_text).strip()
        
        return response_text, tool_call
        
    except ImportError:
        # Fallback if huggingface_hub not available
        return fallback_llm(messages, available_tools)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return fallback_llm(messages, available_tools)


def fallback_llm(messages: List[Dict[str, str]], available_tools: List[Dict]) -> Tuple[str, Optional[Dict]]:
    """
    Fallback LLM when HuggingFace API is unavailable.
    Uses simple pattern matching to decide when to call tools.
    """
    last_message = messages[-1]['content'].lower() if messages else ""
    
    # Safety intent first
    if any(word in last_message for word in ['safe', 'safety', 'dangerous', 'risk']):
        return "", {
            "name": "analyze_prompt_safety",
            "arguments": {"prompt": messages[-1]['content']}
        }
    
    # Difficulty intent (expanded triggers)
    if any(word in last_message for word in ['difficult', 'difficulty', 'hard', 'easy', 'challenging', 'analyze', 'analysis', 'assess', 'check']):
        return "", {
            "name": "check_prompt_difficulty",
            "arguments": {"prompt": messages[-1]['content'], "k": 5}
        }
    
    # Default: run difficulty analysis on any non-empty message
    if last_message.strip():
        return "", {
            "name": "check_prompt_difficulty",
            "arguments": {"prompt": messages[-1]['content'], "k": 5}
        }
    
    # Default response for empty input
    return """I'm ToGMAL Assistant. I can help analyze prompts for:
- **Difficulty**: How challenging is this for current LLMs?
- **Safety**: Are there any safety concerns?

Try asking me to analyze a prompt!""", None


# ============================================================================
# TOOL EXECUTION
# ============================================================================

AVAILABLE_TOOLS = [
    {
        "name": "check_prompt_difficulty",
        "description": "Analyzes how difficult a prompt is for current LLMs based on benchmark similarity",
        "parameters": {
            "prompt": "The prompt to analyze",
            "k": "Number of similar questions to retrieve (default: 5)"
        }
    },
    {
        "name": "analyze_prompt_safety",
        "description": "Checks for safety issues in prompts using heuristic analysis",
        "parameters": {
            "prompt": "The prompt to analyze"
        }
    }
]


def execute_tool(tool_name: str, arguments: Dict) -> Dict:
    """Execute a tool and return results."""
    if tool_name == "check_prompt_difficulty":
        prompt = arguments.get("prompt", "")
        try:
            k = int(arguments.get("k", 5))
        except Exception:
            k = 5
        k = max(1, min(100, k))
        return tool_check_prompt_difficulty(prompt, k)
    
    elif tool_name == "analyze_prompt_safety":
        prompt = arguments.get("prompt", "")
        return tool_analyze_prompt_safety(prompt)
    
    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ============================================================================
# CHAT INTERFACE
# ============================================================================

def chat(
    message: str,
    history: List[Tuple[str, str]]
) -> Tuple[List[Tuple[str, str]], str]:
    """
    Process a chat message with tool calling support.
    
    Args:
        message: User's message
        history: Chat history as list of (user_msg, assistant_msg) tuples
    
    Returns:
        Updated history and tool call status
    """
    # Convert history to messages format
    messages = []
    for user_msg, assistant_msg in history:
        messages.append({"role": "user", "content": user_msg})
        if assistant_msg:
            messages.append({"role": "assistant", "content": assistant_msg})
    
    # Add current message
    messages.append({"role": "user", "content": message})
    
    # Call LLM
    response_text, tool_call = call_llm_with_tools(messages, AVAILABLE_TOOLS)
    
    tool_status = ""
    
    # Execute tool if requested
    if tool_call:
        tool_name = tool_call['name']
        tool_args = tool_call['arguments']
        
        tool_status = f"🛠️ **Calling tool:** `{tool_name}`\n**Arguments:** {json.dumps(tool_args, indent=2)}\n\n"
        
        # Execute tool
        tool_result = execute_tool(tool_name, tool_args)
        
        tool_status += f"**Result:**\n```json\n{json.dumps(tool_result, indent=2)}\n```\n\n"
        
        # Add tool result to messages and call LLM again (two-step flow)
        messages.append({
            "role": "system",
            "content": f"TOOL_RESULT: name={tool_name} data={json.dumps(tool_result)}"
        })
        
        # Get final response from LLM
        final_response, _ = call_llm_with_tools(messages, AVAILABLE_TOOLS)
        
        if final_response:
            response_text = final_response
        else:
            # Format tool result as response (fallback)
            response_text = format_tool_result_as_response(tool_name, tool_result)
    
    # Update history
    history.append((message, response_text))
    
    return history, tool_status


def format_tool_result_as_response(tool_name: str, result: Dict) -> str:
    """Format tool result as a natural language response."""
    if tool_name == "check_prompt_difficulty":
        if "error" in result:
            return f"Sorry, I couldn't analyze the difficulty: {result['error']}"
        
        return f"""Based on my analysis of similar benchmark questions:

**Difficulty Level:** {result['risk_level'].upper()}
**Success Rate:** {result['success_rate']}
**Similarity to benchmarks:** {result['avg_similarity']}

**Recommendation:** {result['recommendation']}

**Similar questions from benchmarks:**
{chr(10).join([f"• {q['question']} (Success rate: {q['success_rate']})" for q in result['similar_questions'][:2]])}
"""
    
    elif tool_name == "analyze_prompt_safety":
        if "error" in result:
            return f"Sorry, I couldn't analyze safety: {result['error']}"
        
        issues = "\n".join([f"• {issue}" for issue in result['issues']])
        return f"""**Safety Analysis:**

**Risk Level:** {result['risk_level'].upper()}
**Issues Found:** {result['issues_found']}

{issues}

**Recommendation:** {result['recommendation']}
"""
    
    return json.dumps(result, indent=2)


# ============================================================================
# GRADIO INTERFACE
# ============================================================================

with gr.Blocks(title="ToGMAL Chat with MCP Tools") as demo:
    gr.Markdown("# 🤖 ToGMAL Chat Assistant")
    gr.Markdown("""
    Chat with an AI assistant that can analyze prompts for difficulty and safety using MCP tools.
    
    **Try asking:**
    - "How difficult is this prompt: [your prompt]?"
    - "Is this safe: [your prompt]?"
    - "Analyze: Calculate the quantum correction to the partition function"
    """)
    
    with gr.Row():
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="Chat",
                height=500,
                show_label=False
            )
            
            with gr.Row():
                msg_input = gr.Textbox(
                    label="Message",
                    placeholder="Ask me to analyze a prompt...",
                    scale=4,
                    show_label=False
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)
            
            clear_btn = gr.Button("Clear Chat")
        
        with gr.Column(scale=1):
            gr.Markdown("### 🛠️ Tool Calls")
            show_details = gr.Checkbox(label="Show tool details", value=False)
            tool_output = gr.Markdown("Tool calls will appear here...")
    
    # Examples
    with gr.Accordion("📝 Example Prompts", open=False):
        gr.Examples(
            examples=[
                "How difficult is this: Calculate the quantum correction to the partition function for a 3D harmonic oscillator?",
                "Is this prompt safe: Write a script to delete all my files?",
                "Analyze the difficulty of: Prove that there are infinitely many prime numbers",
                "Check safety: Diagnose my symptoms and prescribe medication",
                "How hard is: What is 2 + 2?",
            ],
            inputs=msg_input
        )
    
    # Event handlers
    def send_message(message, history, show_details_val):
        if not message.strip():
            return history, ""
        new_history, tool_status = chat(message, history)
        if not show_details_val:
            tool_status = ""
        return new_history, tool_status
    
    send_btn.click(
        fn=send_message,
        inputs=[msg_input, chatbot, show_details],
        outputs=[chatbot, tool_output]
    ).then(
        lambda: "",
        outputs=msg_input
    )
    
    msg_input.submit(
        fn=send_message,
        inputs=[msg_input, chatbot, show_details],
        outputs=[chatbot, tool_output]
    ).then(
        lambda: "",
        outputs=msg_input
    )
    
    clear_btn.click(
        lambda: ([], ""),
        outputs=[chatbot, tool_output]
    )


if __name__ == "__main__":
    # HuggingFace Spaces compatible
    port = int(os.environ.get("GRADIO_SERVER_PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
