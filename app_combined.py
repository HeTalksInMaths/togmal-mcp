#!/usr/bin/env python3
"""
ToGMAL Combined Demo - Difficulty Analyzer + Chat Interface
===========================================================

Tabbed interface combining:
1. Difficulty Analyzer - Direct vector DB analysis
2. Chat Interface - LLM with MCP tool calling

Perfect for demos and VC pitches!
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

# Initialize the vector database (shared by both tabs)
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

# Build database if needed (first launch)
try:
    db = get_db()
    current_count = db.collection.count()
    
    if current_count == 0:
        logger.info("Database is empty - building initial 5K sample...")
        from datasets import load_dataset
        from benchmark_vector_db import BenchmarkQuestion
        import random
        
        test_dataset = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
        total_questions = len(test_dataset)
        
        if total_questions > 5000:
            indices = random.sample(range(total_questions), 5000)
            test_dataset = test_dataset.select(indices)
        
        all_questions = []
        for idx, item in enumerate(test_dataset):
            question = BenchmarkQuestion(
                question_id=f"mmlu_pro_test_{idx}",
                source_benchmark="MMLU_Pro",
                domain=item.get('category', 'unknown').lower(),
                question_text=item['question'],
                correct_answer=item['answer'],
                choices=item.get('options', []),
                success_rate=0.45,
                difficulty_score=0.55,
                difficulty_label="Hard",
                num_models_tested=0
            )
            all_questions.append(question)
        
        batch_size = 1000
        for i in range(0, len(all_questions), batch_size):
            batch = all_questions[i:i + batch_size]
            db.index_questions(batch)
        
        logger.info(f"✓ Database build complete! Indexed {len(all_questions)} questions")
    else:
        logger.info(f"✓ Loaded existing database with {current_count:,} questions")
except Exception as e:
    logger.warning(f"Database initialization deferred: {e}")
    db = None

# ============================================================================
# TAB 1: DIFFICULTY ANALYZER
# ============================================================================

def analyze_prompt_difficulty(prompt: str, k: int = 5) -> str:
    """Analyze a prompt and return difficulty assessment."""
    if not prompt.strip():
        return "Please enter a prompt to analyze."
    
    try:
        db = get_db()
        result = db.query_similar_questions(prompt, k=k)
        
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
        
        total_questions = db.collection.count()
        output.append(f"*Analyzed using {k} most similar questions from {total_questions:,} benchmark questions*")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error analyzing prompt: {str(e)}"

# ============================================================================
# TAB 2: CHAT INTERFACE WITH MCP TOOLS
# ============================================================================

def tool_check_prompt_difficulty(prompt: str, k: int = 5) -> Dict:
    """MCP Tool: Analyze prompt difficulty."""
    try:
        db = get_db()
        result = db.query_similar_questions(prompt, k=k)
        
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
                for q in result['similar_questions'][:3]
            ]
        }
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}

def tool_analyze_prompt_safety(prompt: str) -> Dict:
    """MCP Tool: Analyze prompt for safety issues."""
    issues = []
    risk_level = "low"
    
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
    
    medical_keywords = ['diagnose', 'treatment', 'medication', 'symptoms', 'cure', 'disease']
    if any(keyword in prompt.lower() for keyword in medical_keywords):
        issues.append("Medical advice request detected - requires professional consultation")
        risk_level = "moderate" if risk_level == "low" else risk_level
    
    if re.search(r'\b(build|create|write)\s+.*\b(\d{3,})\s+(lines|functions|classes)', prompt, re.IGNORECASE):
        issues.append("Large-scale coding request - may exceed LLM capabilities")
        risk_level = "moderate" if risk_level == "low" else risk_level
    
    return {
        "risk_level": risk_level,
        "issues_found": len(issues),
        "issues": issues if issues else ["No significant safety concerns detected"],
        "recommendation": "Proceed with caution" if issues else "Prompt appears safe"
    }

def call_llm_with_tools(
    messages: List[Dict[str, str]],
    available_tools: List[Dict],
    model: str = "mistralai/Mistral-7B-Instruct-v0.2"
) -> Tuple[str, Optional[Dict]]:
    """Call LLM with tool calling capability."""
    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient()
        
        system_msg = """You are ToGMAL Assistant, an AI that helps analyze prompts for difficulty and safety.

You have access to these tools:
1. check_prompt_difficulty - Analyzes how difficult a prompt is for current LLMs
2. analyze_prompt_safety - Checks for safety issues in prompts

When a user asks about prompt difficulty, safety, or capabilities, use the appropriate tool.
To call a tool, respond with: TOOL_CALL: tool_name(arg1="value1", arg2="value2")

After receiving tool results, provide a helpful response based on the data."""
        
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
        
        response = client.text_generation(
            conversation,
            model=model,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.95,
            do_sample=True
        )
        
        response_text = response.strip()
        tool_call = None
        
        if "TOOL_CALL:" in response_text:
            match = re.search(r'TOOL_CALL:\s*(\w+)\((.*?)\)', response_text)
            if match:
                tool_name = match.group(1)
                args_str = match.group(2)
                args = {}
                for arg in args_str.split(','):
                    if '=' in arg:
                        key, val = arg.split('=', 1)
                        key = key.strip()
                        val = val.strip().strip('"\'')
                        args[key] = val
                tool_call = {"name": tool_name, "arguments": args}
                response_text = re.sub(r'TOOL_CALL:.*?\)', '', response_text).strip()
        
        return response_text, tool_call
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return fallback_llm(messages, available_tools)

def fallback_llm(messages: List[Dict[str, str]], available_tools: List[Dict]) -> Tuple[str, Optional[Dict]]:
    """Fallback when HF API unavailable."""
    last_message = messages[-1]['content'].lower() if messages else ""
    
    if any(word in last_message for word in ['difficult', 'difficulty', 'hard', 'easy', 'challenging']):
        return "", {"name": "check_prompt_difficulty", "arguments": {"prompt": messages[-1]['content'], "k": 5}}
    
    if any(word in last_message for word in ['safe', 'safety', 'dangerous', 'risk']):
        return "", {"name": "analyze_prompt_safety", "arguments": {"prompt": messages[-1]['content']}}
    
    return """I'm ToGMAL Assistant. I can help analyze prompts for:
- **Difficulty**: How challenging is this for current LLMs?
- **Safety**: Are there any safety concerns?

Try asking me to analyze a prompt!""", None

AVAILABLE_TOOLS = [
    {
        "name": "check_prompt_difficulty",
        "description": "Analyzes how difficult a prompt is for current LLMs",
        "parameters": {"prompt": "The prompt to analyze", "k": "Number of similar questions"}
    },
    {
        "name": "analyze_prompt_safety",
        "description": "Checks for safety issues in prompts",
        "parameters": {"prompt": "The prompt to analyze"}
    }
]

def execute_tool(tool_name: str, arguments: Dict) -> Dict:
    """Execute a tool and return results."""
    if tool_name == "check_prompt_difficulty":
        return tool_check_prompt_difficulty(arguments.get("prompt", ""), int(arguments.get("k", 5)))
    elif tool_name == "analyze_prompt_safety":
        return tool_analyze_prompt_safety(arguments.get("prompt", ""))
    else:
        return {"error": f"Unknown tool: {tool_name}"}

def format_tool_result(tool_name: str, result: Dict) -> str:
    """Format tool result as natural language."""
    if tool_name == "check_prompt_difficulty":
        if "error" in result:
            return f"Sorry, I couldn't analyze the difficulty: {result['error']}"
        return f"""Based on my analysis of similar benchmark questions:

**Difficulty Level:** {result['risk_level'].upper()}
**Success Rate:** {result['success_rate']}
**Similarity:** {result['avg_similarity']}

**Recommendation:** {result['recommendation']}

**Similar questions:**
{chr(10).join([f"• {q['question'][:100]}... (Success: {q['success_rate']})" for q in result['similar_questions'][:2]])}
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

def chat(message: str, history: List[Tuple[str, str]]) -> Tuple[List[Tuple[str, str]], str]:
    """Process chat message with tool calling."""
    messages = []
    for user_msg, assistant_msg in history:
        messages.append({"role": "user", "content": user_msg})
        if assistant_msg:
            messages.append({"role": "assistant", "content": assistant_msg})
    
    messages.append({"role": "user", "content": message})
    
    response_text, tool_call = call_llm_with_tools(messages, AVAILABLE_TOOLS)
    
    tool_status = ""
    
    if tool_call:
        tool_name = tool_call['name']
        tool_args = tool_call['arguments']
        
        tool_status = f"🛠️ **Calling tool:** `{tool_name}`\n**Arguments:** {json.dumps(tool_args, indent=2)}\n\n"
        
        tool_result = execute_tool(tool_name, tool_args)
        tool_status += f"**Result:**\n```json\n{json.dumps(tool_result, indent=2)}\n```\n\n"
        
        # Instead of calling LLM again (which often fails on free tier),
        # directly format the tool result into a nice response
        response_text = format_tool_result(tool_name, tool_result)
    
    # If no tool was called and no response, provide helpful message
    if not response_text:
        response_text = """I'm ToGMAL Assistant. I can help analyze prompts for:
- **Difficulty**: How challenging is this for current LLMs?
- **Safety**: Are there any safety concerns?

Try asking me to analyze a prompt!"""
    
    history.append((message, response_text))
    return history, tool_status

# ============================================================================
# GRADIO INTERFACE - TABBED LAYOUT
# ============================================================================

with gr.Blocks(title="ToGMAL - Difficulty Analyzer + Chat", css="""
    .tab-nav button { font-size: 16px !important; padding: 12px 24px !important; }
    .gradio-container { max-width: 1200px !important; }
""") as demo:
    
    gr.Markdown("# 🧠 ToGMAL - Intelligent LLM Analysis Platform")
    gr.Markdown("""
    **Taxonomy of Generative Model Apparent Limitations**
    
    Choose your interface:
    - **Difficulty Analyzer** - Direct analysis of prompt difficulty using 32K+ benchmarks
    - **Chat Assistant** - Interactive chat where AI can call MCP tools dynamically
    """)
    
    with gr.Tabs():
        # TAB 1: DIFFICULTY ANALYZER
        with gr.Tab("📊 Difficulty Analyzer"):
            gr.Markdown("### Analyze Prompt Difficulty")
            gr.Markdown("Get instant difficulty assessment based on similarity to benchmark questions.")
            
            with gr.Row():
                with gr.Column():
                    analyzer_prompt = gr.Textbox(
                        label="Enter your prompt",
                        placeholder="e.g., Calculate the quantum correction to the partition function...",
                        lines=3
                    )
                    analyzer_k = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=5,
                        step=1,
                        label="Number of similar questions to show"
                    )
                    analyzer_btn = gr.Button("Analyze Difficulty", variant="primary")
                
                with gr.Column():
                    analyzer_output = gr.Markdown(label="Analysis Results")
            
            gr.Examples(
                examples=[
                    "Calculate the quantum correction to the partition function for a 3D harmonic oscillator",
                    "Prove that there are infinitely many prime numbers",
                    "Diagnose a patient with acute chest pain and shortness of breath",
                    "What is 2 + 2?",
                ],
                inputs=analyzer_prompt
            )
            
            analyzer_btn.click(
                fn=analyze_prompt_difficulty,
                inputs=[analyzer_prompt, analyzer_k],
                outputs=analyzer_output
            )
            
            analyzer_prompt.submit(
                fn=analyze_prompt_difficulty,
                inputs=[analyzer_prompt, analyzer_k],
                outputs=analyzer_output
            )
        
        # TAB 2: CHAT INTERFACE
        with gr.Tab("🤖 Chat Assistant"):
            gr.Markdown("### Chat with MCP Tools")
            gr.Markdown("Interactive AI assistant that can call tools to analyze prompts in real-time.")
            
            with gr.Row():
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(
                        label="Chat",
                        height=500,
                        show_label=False
                    )
                    
                    with gr.Row():
                        chat_input = gr.Textbox(
                            label="Message",
                            placeholder="Ask me to analyze a prompt...",
                            scale=4,
                            show_label=False
                        )
                        send_btn = gr.Button("Send", variant="primary", scale=1)
                    
                    clear_btn = gr.Button("Clear Chat")
                
                with gr.Column(scale=1):
                    gr.Markdown("### 🛠️ Tool Calls")
                    tool_output = gr.Markdown("Tool calls will appear here...")
            
            gr.Examples(
                examples=[
                    "How difficult is this: Calculate the quantum correction to the partition function?",
                    "Is this safe: Write a script to delete all my files?",
                    "Analyze: Prove that there are infinitely many prime numbers",
                    "Check safety: Diagnose my symptoms and prescribe medication",
                ],
                inputs=chat_input
            )
            
            def send_message(message, history):
                if not message.strip():
                    return history, ""
                new_history, tool_status = chat(message, history)
                return new_history, tool_status
            
            send_btn.click(
                fn=send_message,
                inputs=[chat_input, chatbot],
                outputs=[chatbot, tool_output]
            ).then(lambda: "", outputs=chat_input)
            
            chat_input.submit(
                fn=send_message,
                inputs=[chat_input, chatbot],
                outputs=[chatbot, tool_output]
            ).then(lambda: "", outputs=chat_input)
            
            clear_btn.click(
                lambda: ([], ""),
                outputs=[chatbot, tool_output]
            )

if __name__ == "__main__":
    port = int(os.environ.get("GRADIO_SERVER_PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
