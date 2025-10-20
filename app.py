#!/usr/bin/env python3
"""
ToGMAL Difficulty Assessment Demo
=================================

Gradio demo for the vector database-based prompt difficulty assessment.
Shows real-time difficulty scores and recommendations.
"""

import gradio as gr
import json
from pathlib import Path
from benchmark_vector_db import BenchmarkVectorDB
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the vector database
db_path = Path("./data/benchmark_vector_db")
db = BenchmarkVectorDB(
    db_path=db_path,
    embedding_model="all-MiniLM-L6-v2"
)

# Build database if not exists (first launch on Hugging Face)
if db.collection.count() == 0:
    logger.info("Database is empty - building from scratch...")
    logger.info("This will take 3-5 minutes on first launch.")
    db.build_database(
        load_gpqa=True,
        load_mmlu_pro=True,
        load_math=True,
        max_samples_per_dataset=1000
    )
    logger.info("✓ Database build complete!")
else:
    logger.info(f"✓ Loaded existing database with {db.collection.count()} questions")

def analyze_prompt(prompt: str, k: int = 5) -> str:
    """
    Analyze a prompt and return difficulty assessment.
    
    Args:
        prompt: The user's prompt/question
        k: Number of similar questions to retrieve
    
    Returns:
        Formatted analysis results
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
        return f"Error analyzing prompt: {str(e)}"

# Create Gradio interface
with gr.Blocks(title="ToGMAL Prompt Difficulty Analyzer") as demo:
    gr.Markdown("# 🧠 ToGMAL Prompt Difficulty Analyzer")
    gr.Markdown("Enter any prompt to see how difficult it is for current LLMs based on real benchmark data.")
    
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
            submit_btn = gr.Button("Analyze Difficulty")
        
        with gr.Column():
            result_output = gr.Markdown(label="Analysis Results")
    
    # Examples
    gr.Examples(
        examples=[
            "Calculate the quantum correction to the partition function for a 3D harmonic oscillator",
            "Prove that there are infinitely many prime numbers",
            "Diagnose a patient with acute chest pain and shortness of breath",
            "Explain the legal doctrine of precedent in common law systems",
            "Implement a binary search tree with insert and search operations",
            "What is 2 + 2?",
            "What is the capital of France?"
        ],
        inputs=prompt_input
    )
    
    # Event handling
    submit_btn.click(
        fn=analyze_prompt,
        inputs=[prompt_input, k_slider],
        outputs=result_output
    )
    
    prompt_input.submit(
        fn=analyze_prompt,
        inputs=[prompt_input, k_slider],
        outputs=result_output
    )

if __name__ == "__main__":
    demo.launch(share=True, server_port=7861)