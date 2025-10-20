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

# Build expanded database if not exists (first launch on Hugging Face)
current_count = db.collection.count()

if current_count == 0:
    logger.info("Database is empty - building expanded database from scratch...")
    logger.info("This will take ~10-15 minutes on first launch (building 26K+ questions).")
    
    # Load MMLU-Pro test split for comprehensive coverage
    try:
        from datasets import load_dataset
        from benchmark_vector_db import BenchmarkQuestion
        
        # Load MMLU-Pro validation + test splits
        logger.info("Loading MMLU-Pro validation split...")
        val_dataset = load_dataset("TIGER-Lab/MMLU-Pro", split="validation")
        logger.info(f"  Loaded {len(val_dataset)} validation questions")
        
        logger.info("Loading MMLU-Pro test split...")
        test_dataset = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
        logger.info(f"  Loaded {len(test_dataset)} test questions")
        
        all_questions = []
        
        # Process validation split
        for idx, item in enumerate(val_dataset):
            question = BenchmarkQuestion(
                question_id=f"mmlu_pro_val_{idx}",
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
        
        # Process test split
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
        
        logger.info(f"Total questions to index: {len(all_questions)}")
        
        # Index in batches of 1000 for stability
        batch_size = 1000
        for i in range(0, len(all_questions), batch_size):
            batch = all_questions[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(all_questions) + batch_size - 1) // batch_size
            logger.info(f"Indexing batch {batch_num}/{total_batches} ({len(batch)} questions)...")
            db.index_questions(batch)
        
        logger.info(f"✓ Database build complete! Indexed {len(all_questions)} questions")
        
    except Exception as e:
        logger.error(f"Failed to build expanded database: {e}")
        logger.info("Falling back to standard build...")
        db.build_database(
            load_gpqa=False,  # Skip GPQA (requires auth)
            load_mmlu_pro=True,
            load_math=False,  # Skip MATH (dataset path issues)
            max_samples_per_dataset=1000
        )
else:
    logger.info(f"✓ Loaded existing database with {current_count:,} questions")

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
        
        # Get current database size
        total_questions = db.collection.count()
        output.append(f"*Analyzed using {k} most similar questions from {total_questions:,} benchmark questions*")
        
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