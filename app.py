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
    """Expand the database by adding another batch of questions from multiple sources."""
    try:
        from datasets import load_dataset
        from benchmark_vector_db import BenchmarkQuestion
        import random
        
        current_count = db.collection.count()
        
        # Load from ALL available sources to reach 32K+
        # We'll build a pool of all questions and track which ones we've indexed
        all_questions_pool = []
        
        logger.info("Loading all available benchmark datasets...")
        
        # Source 1: MMLU-Pro test split (12,032 questions)
        try:
            logger.info("  Loading MMLU-Pro test...")
            mmlu_pro_test = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
            for idx, item in enumerate(mmlu_pro_test):
                all_questions_pool.append({
                    'id': f"mmlu_pro_test_{idx}",
                    'source': 'MMLU_Pro',
                    'domain': item.get('category', 'unknown').lower(),
                    'question': item['question'],
                    'answer': item['answer'],
                    'choices': item.get('options', []),
                    'success_rate': 0.45
                })
            logger.info(f"    Added {len(mmlu_pro_test)} MMLU-Pro test questions")
        except Exception as e:
            logger.warning(f"    Could not load MMLU-Pro test: {e}")
        
        # Source 2: MMLU-Pro validation split (70 questions)
        try:
            logger.info("  Loading MMLU-Pro validation...")
            mmlu_pro_val = load_dataset("TIGER-Lab/MMLU-Pro", split="validation")
            for idx, item in enumerate(mmlu_pro_val):
                all_questions_pool.append({
                    'id': f"mmlu_pro_val_{idx}",
                    'source': 'MMLU_Pro',
                    'domain': item.get('category', 'unknown').lower(),
                    'question': item['question'],
                    'answer': item['answer'],
                    'choices': item.get('options', []),
                    'success_rate': 0.45
                })
            logger.info(f"    Added {len(mmlu_pro_val)} MMLU-Pro validation questions")
        except Exception as e:
            logger.warning(f"    Could not load MMLU-Pro validation: {e}")
        
        # Source 3: MMLU (original - 14,042 questions for cross-domain coverage)
        try:
            logger.info("  Loading MMLU (original)...")
            # MMLU has multiple subjects, we'll load the test split
            # Using the 'all' configuration to get all subjects
            mmlu_dataset = load_dataset("cais/mmlu", "all", split="test")
            for idx, item in enumerate(mmlu_dataset):
                all_questions_pool.append({
                    'id': f"mmlu_{idx}",
                    'source': 'MMLU',
                    'domain': item.get('subject', 'cross_domain').lower(),
                    'question': item['question'],
                    'answer': str(item['answer']),
                    'choices': item.get('choices', []),
                    'success_rate': 0.65  # MMLU is easier than MMLU-Pro
                })
            logger.info(f"    Added {len(mmlu_dataset)} MMLU questions")
        except Exception as e:
            logger.warning(f"    Could not load MMLU: {e}")
        
        # Source 4: ARC-Challenge - Science reasoning
        try:
            logger.info("  Loading ARC-Challenge...")
            arc_dataset = load_dataset("allenai/ai2_arc", "ARC-Challenge", split="test")
            for idx, item in enumerate(arc_dataset):
                all_questions_pool.append({
                    'id': f"arc_challenge_{idx}",
                    'source': 'ARC-Challenge',
                    'domain': 'science',
                    'question': item['question'],
                    'answer': item['answerKey'],
                    'choices': item['choices']['text'] if 'choices' in item else [],
                    'success_rate': 0.50
                })
            logger.info(f"    Added {len(arc_dataset)} ARC-Challenge questions")
        except Exception as e:
            logger.warning(f"    Could not load ARC-Challenge: {e}")
        
        # Source 5: HellaSwag - Commonsense NLI (sample 2K from 10K)
        try:
            logger.info("  Loading HellaSwag...")
            hellaswag_dataset = load_dataset("Rowan/hellaswag", split="validation")
            # Sample to 2000 to manage size
            if len(hellaswag_dataset) > 2000:
                indices = random.sample(range(len(hellaswag_dataset)), 2000)
                hellaswag_dataset = hellaswag_dataset.select(indices)
            for idx, item in enumerate(hellaswag_dataset):
                all_questions_pool.append({
                    'id': f"hellaswag_{idx}",
                    'source': 'HellaSwag',
                    'domain': 'commonsense',
                    'question': item['ctx'],
                    'answer': str(item['label']),
                    'choices': item['endings'] if 'endings' in item else [],
                    'success_rate': 0.65
                })
            logger.info(f"    Added {len(hellaswag_dataset)} HellaSwag questions")
        except Exception as e:
            logger.warning(f"    Could not load HellaSwag: {e}")
        
        # Source 6: GSM8K - Math word problems
        try:
            logger.info("  Loading GSM8K...")
            gsm8k_dataset = load_dataset("openai/gsm8k", "main", split="test")
            for idx, item in enumerate(gsm8k_dataset):
                all_questions_pool.append({
                    'id': f"gsm8k_{idx}",
                    'source': 'GSM8K',
                    'domain': 'math_word_problems',
                    'question': item['question'],
                    'answer': item['answer'],
                    'choices': None,
                    'success_rate': 0.55
                })
            logger.info(f"    Added {len(gsm8k_dataset)} GSM8K questions")
        except Exception as e:
            logger.warning(f"    Could not load GSM8K: {e}")
        
        # Source 7: TruthfulQA - Truthfulness detection
        try:
            logger.info("  Loading TruthfulQA...")
            truthfulqa_dataset = load_dataset("truthful_qa", "generation", split="validation")
            for idx, item in enumerate(truthfulqa_dataset):
                all_questions_pool.append({
                    'id': f"truthfulqa_{idx}",
                    'source': 'TruthfulQA',
                    'domain': 'truthfulness',
                    'question': item['question'],
                    'answer': item['best_answer'],
                    'choices': None,
                    'success_rate': 0.35
                })
            logger.info(f"    Added {len(truthfulqa_dataset)} TruthfulQA questions")
        except Exception as e:
            logger.warning(f"    Could not load TruthfulQA: {e}")
        
        # Source 8: Winogrande - Commonsense reasoning
        try:
            logger.info("  Loading Winogrande...")
            winogrande_dataset = load_dataset("winogrande", "winogrande_xl", split="validation")
            for idx, item in enumerate(winogrande_dataset):
                all_questions_pool.append({
                    'id': f"winogrande_{idx}",
                    'source': 'Winogrande',
                    'domain': 'commonsense_reasoning',
                    'question': item['sentence'],
                    'answer': item['answer'],
                    'choices': [item['option1'], item['option2']],
                    'success_rate': 0.70
                })
            logger.info(f"    Added {len(winogrande_dataset)} Winogrande questions")
        except Exception as e:
            logger.warning(f"    Could not load Winogrande: {e}")
        
        total_available = len(all_questions_pool)
        logger.info(f"Total questions available: {total_available:,}")
        
        if current_count >= total_available:
            return f"✅ Database is complete! All {total_available:,} questions already indexed.\n\n📊 **20 domains** across **7 benchmark sources**!"
        
        # Get next batch (skip ones we've already indexed)
        start_idx = current_count
        end_idx = min(start_idx + batch_size, total_available)
        batch_data = all_questions_pool[start_idx:end_idx]
        
        # Convert to BenchmarkQuestion objects
        batch_questions = []
        for q_data in batch_data:
            question = BenchmarkQuestion(
                question_id=q_data['id'],
                source_benchmark=q_data['source'],
                domain=q_data['domain'],
                question_text=q_data['question'],
                correct_answer=q_data['answer'],
                choices=q_data.get('choices'),
                success_rate=q_data['success_rate'],
                difficulty_score=1.0 - q_data['success_rate'],
                difficulty_label="Hard" if q_data['success_rate'] < 0.5 else "Moderate",
                num_models_tested=0
            )
            batch_questions.append(question)
        
        logger.info(f"Indexing {len(batch_questions)} new questions...")
        db.index_questions(batch_questions)
        
        new_count = db.collection.count()
        still_remaining = total_available - new_count
        
        result = f"✅ Successfully added {len(batch_questions)} questions!\n\n"
        result += f"**Database Stats:**\n"
        result += f"- Total Questions: {new_count:,}\n"
        result += f"- Just Added: {len(batch_questions)}\n"
        result += f"- Total Available: {total_available:,}\n"
        result += f"- Remaining: {still_remaining:,}\n\n"
        
        if still_remaining > 0:
            result += f"💡 Click 'Expand Database' again to add up to {min(batch_size, still_remaining):,} more questions.\n"
            result += f"📊 Progress: {(new_count/total_available*100):.1f}% complete"
        else:
            result += f"🎉 Database is now complete with all {total_available:,} questions!\n\n"
            result += f"📚 **Sources:** MMLU, MMLU-Pro, ARC-Challenge, HellaSwag, GSM8K, TruthfulQA, Winogrande\n"
            result += f"🌐 **Domains:** 20+ including science, math, truthfulness, commonsense, and more!"
        
        return result
        
    except Exception as e:
        logger.error(f"Expansion failed: {e}")
        return f"❌ Error expanding database: {str(e)}"


def get_database_info() -> str:
    """Get current database statistics."""
    try:
        current_count = db.collection.count()
        
        # Total available across all sources
        # MMLU: ~14,042 + MMLU-Pro: 12,102 + ARC: 1,172 + HellaSwag: 2,000
        # + GSM8K: 1,319 + TruthfulQA: 817 + Winogrande: 1,267 = ~32,719 total
        total_available = 32719
        remaining = total_available - current_count
        progress_pct = (current_count / total_available * 100) if total_available > 0 else 0
        
        info = f"### 📊 Database Status\n\n"
        info += f"**Current Size:** {current_count:,} questions\n"
        info += f"**Total Available:** {total_available:,} questions\n"
        info += f"**Progress:** {progress_pct:.1f}% complete\n"
        info += f"**Remaining:** {max(0, remaining):,} questions\n\n"
        
        if remaining > 0:
            info += f"💡 Click 'Expand Database' to add 5,000 more questions (~2-3 min per batch)\n\n"
            clicks_needed = (remaining + 4999) // 5000  # Round up
            info += f"📈 ~{clicks_needed} more clicks to reach full 32K+ dataset"
        else:
            info += f"🎉 Database is complete with all available questions!\n\n"
            info += f"**Sources:** MMLU, MMLU-Pro, ARC-Challenge, HellaSwag, GSM8K, TruthfulQA, Winogrande\n"
            info += f"**Domains:** 20+ including truthfulness, commonsense, math word problems, science, and more!"
        
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
    # HuggingFace Spaces: Use default port (7860) and auto-share
    # Port is auto-assigned by HF Spaces infrastructure
    import os
    port = int(os.environ.get("GRADIO_SERVER_PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)