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
# Start with a manageable size to avoid build timeout
current_count = db.collection.count()

if current_count == 0:
    logger.info("Database is empty - building database...")
    logger.info("Building 5K questions to stay within build time limits.")
    
    try:
        from datasets import load_dataset
        from benchmark_vector_db import BenchmarkQuestion
        
        # Load MMLU-Pro test split (sample 5K for fast build)
        logger.info("Loading MMLU-Pro test split (5K sample)...")
        test_dataset = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
        logger.info(f"  Dataset has {len(test_dataset)} questions total")
        
        # Sample 5000 questions for fast initial build
        import random
        total_questions = len(test_dataset)
        if total_questions > 5000:
            indices = random.sample(range(total_questions), 5000)
            test_dataset = test_dataset.select(indices)
            logger.info(f"  Sampled 5000 questions for initial build")
        
        all_questions = []
        
        # Process questions
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
        
        logger.info(f"Indexing {len(all_questions)} questions...")
        
        # Index in batches of 1000
        batch_size = 1000
        for i in range(0, len(all_questions), batch_size):
            batch = all_questions[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(all_questions) + batch_size - 1) // batch_size
            logger.info(f"  Batch {batch_num}/{total_batches}...")
            db.index_questions(batch)
        
        logger.info(f"✓ Database build complete! Indexed {len(all_questions)} questions")
        logger.info("Note: This is a 5K subset. Full 26K database available locally.")
        
    except Exception as e:
        logger.error(f"Failed to build database: {e}")
        logger.info("Falling back to minimal build...")
        db.build_database(
            load_gpqa=False,
            load_mmlu_pro=True,
            load_math=False,
            max_samples_per_dataset=1000
        )
else:
    logger.info(f"✓ Loaded existing database with {current_count:,} questions")

def analyze_prompt(prompt: str, k: int = 5) -> str:
    """Analyze a prompt and return difficulty assessment."""
    if not prompt.strip():
        return "Please enter a prompt to analyze."
    
    try:
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
        
        total_questions = db.collection.count()
        output.append(f"*Analyzed using {k} most similar questions from {total_questions:,} benchmark questions*")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"Error analyzing prompt: {str(e)}"


def expand_database(batch_size: int = 5000) -> str:
    """Expand the database by adding another batch of questions."""
    try:
        from datasets import load_dataset
        from benchmark_vector_db import BenchmarkQuestion
        import random
        
        current_count = db.collection.count()
        
        # Load full MMLU-Pro test dataset
        logger.info("Loading MMLU-Pro test dataset...")
        test_dataset = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
        total_available = len(test_dataset)
        
        # Figure out which questions we haven't indexed yet
        # We'll use a simple offset approach
        already_indexed = current_count
        remaining = total_available - already_indexed
        
        if remaining <= 0:
            return f"✅ Database is complete! All {total_available:,} questions indexed."
        
        # Sample next batch
        start_idx = already_indexed
        end_idx = min(start_idx + batch_size, total_available)
        batch_questions = []
        
        logger.info(f"Expanding database: adding questions {start_idx} to {end_idx}...")
        
        for idx in range(start_idx, end_idx):
            item = test_dataset[idx]
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
            batch_questions.append(question)
        
        # Index the batch
        logger.info(f"Indexing {len(batch_questions)} new questions...")
        db.index_questions(batch_questions)
        
        new_count = db.collection.count()
        still_remaining = total_available - new_count
        
        result = f"✅ Successfully added {len(batch_questions)} questions!\n\n"
        result += f"**Database Stats:**\n"
        result += f"- Total Questions: {new_count:,}\n"
        result += f"- Just Added: {len(batch_questions)}\n"
        result += f"- Remaining: {still_remaining:,}\n\n"
        
        if still_remaining > 0:
            result += f"Click 'Expand Database' again to add {min(batch_size, still_remaining)} more questions."
        else:
            result += f"🎉 Database is now complete with all {total_available:,} questions!"
        
        return result
        
    except Exception as e:
        logger.error(f"Expansion failed: {e}")
        return f"❌ Error expanding database: {str(e)}"


def get_database_info() -> str:
    """Get current database statistics."""
    try:
        current_count = db.collection.count()
        
        # Estimate total available (MMLU-Pro test has ~12K)
        total_available = 12032
        remaining = total_available - current_count
        
        info = f"### 📊 Database Status\n\n"
        info += f"**Current Size:** {current_count:,} questions\n"
        info += f"**Available:** {total_available:,} questions\n"
        info += f"**Remaining:** {max(0, remaining):,} questions\n\n"
        
        if remaining > 0:
            info += f"💡 Click 'Expand Database' to add 5,000 more questions (takes ~2-3 min)"
        else:
            info += f"✅ Database is complete!"
        
        return info
    except Exception as e:
        return f"Error getting database info: {str(e)}"

# Create Gradio interface
with gr.Blocks(title="ToGMAL Prompt Difficulty Analyzer") as demo:
    gr.Markdown("# 🧠 ToGMAL Prompt Difficulty Analyzer")
    gr.Markdown("Enter any prompt to see how difficult it is for current LLMs based on real benchmark data.")
    
    # Database expansion section
    with gr.Accordion("📊 Database Management", open=False):
        db_info = gr.Markdown(get_database_info())
        with gr.Row():
            expand_btn = gr.Button("🚀 Expand Database (+5K questions)", variant="secondary")
            refresh_btn = gr.Button("🔄 Refresh Stats", variant="secondary")
        expand_output = gr.Markdown()
    
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
            submit_btn = gr.Button("Analyze Difficulty", variant="primary")
        
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
    
    expand_btn.click(
        fn=expand_database,
        inputs=[],
        outputs=expand_output
    )
    
    refresh_btn.click(
        fn=get_database_info,
        inputs=[],
        outputs=db_info
    )

if __name__ == "__main__":
    demo.launch(share=True, server_port=7861)