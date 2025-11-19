# Pseudocode: Extracting 12K MMLU-Pro Questions from GitHub Eval Cache
# ========================================================================

# CONTEXT:
# - MMLU-Pro questions are stored in eval cache files in data/eval_cache/
# - These files were pre-downloaded from model evaluation runs
# - Each file contains predictions from one model on MMLU-Pro benchmark
# - We extract both questions AND model performance from these files

# ==============================================================================
# STEP 1: LOCATE EVAL CACHE FILES
# ==============================================================================

FUNCTION find_eval_files():
    eval_cache_directory = "./data/eval_cache"

    # Find all MMLU-Pro eval output files
    # Pattern: mmlu_pro_model_outputs_{model_name}_{shots}shots.json
    eval_files = GLOB(eval_cache_directory + "mmlu_pro_model_outputs_*.json")

    # Example files found:
    # - mmlu_pro_model_outputs_Llama-2-13b-hf_5shots.json
    # - mmlu_pro_model_outputs_Meta-Llama-3_1-70B_5shots.json
    # - mmlu_pro_model_outputs_claude-3-5-sonnet_5shots.json
    # - ... (47 total files)

    RETURN eval_files  # List of 47 file paths


# ==============================================================================
# STEP 2: EXTRACT QUESTIONS AND PERFORMANCE FROM EACH FILE
# ==============================================================================

FUNCTION extract_from_eval_file(file_path):
    """
    Each eval file has structure:
    {
        "model_name": "model_outputs_Llama-2-13b-hf_5shots",
        "benchmark_name": "MMLU-Pro",
        "overall_score": 23.52,
        "predictions": [
            {
                "question_id": 70,
                "question": "Typical advertising regulatory bodies...",
                "options": ["A", "B", "C", ...],
                "answer": "I",  # Correct answer
                "pred": "I",    # Model's prediction
                "category": "business"
            },
            { ... }  # More questions
        ]
    }
    """

    data = JSON.load(file_path)

    # Extract model name
    model_name = data["model_name"]
    model_name = CLEAN_NAME(model_name)  # Remove "model_outputs_", "_5shots", etc.

    predictions = []

    # Process each question prediction
    FOR EACH pred IN data["predictions"]:
        question_id = pred["question_id"]
        question_text = pred["question"]
        correct_answer = pred["answer"]
        model_prediction = pred["pred"]
        category = pred["category"]  # Domain (business, math, physics, etc.)
        options = pred["options"]

        # Check if model got it right
        is_correct = (model_prediction == correct_answer)

        # Store complete question data
        question_data = {
            "question_id": question_id,
            "question_text": question_text,
            "domain": category,
            "options": options,
            "correct_answer": correct_answer,
            "source": "MMLU-Pro"
        }

        # Store model performance on this question
        performance_data = {
            "model": model_name,
            "prediction": model_prediction,
            "is_correct": is_correct
        }

        predictions.APPEND((question_data, performance_data))

    RETURN model_name, predictions


# ==============================================================================
# STEP 3: AGGREGATE ACROSS ALL MODELS
# ==============================================================================

FUNCTION aggregate_all_eval_files(eval_files):
    """
    Aggregate questions and performance from all 47 files
    Result: Each question has performance from multiple models
    """

    # Data structure: {question_id: {question_data, {model: performance}}}
    all_questions = {}

    FOR EACH file IN eval_files:
        model_name, predictions = extract_from_eval_file(file)

        FOR EACH (question_data, performance_data) IN predictions:
            qid = question_data["question_id"]

            # First time seeing this question
            IF qid NOT IN all_questions:
                all_questions[qid] = {
                    "question": question_data,
                    "model_results": {}
                }

            # Add this model's performance
            model = performance_data["model"]
            all_questions[qid]["model_results"][model] = {
                "prediction": performance_data["prediction"],
                "is_correct": performance_data["is_correct"]
            }

    RETURN all_questions


# ==============================================================================
# STEP 4: BUILD UNIFIED DATABASE FORMAT
# ==============================================================================

FUNCTION build_unified_database(all_questions):
    """
    Convert to standardized format for semantic search
    """

    unified_questions = []

    FOR EACH qid, data IN all_questions:
        question = data["question"]

        # Standardize format
        unified_question = {
            "question_id": "mmlu_pro_" + str(qid),  # Prefix for clarity
            "question_text": question["question_text"],
            "domain": question["domain"],
            "difficulty_score": COMPUTE_DIFFICULTY(data["model_results"]),  # Based on model success rate
            "source": "MMLU-Pro",
            "choices": question["options"],
            "correct_answer": question["correct_answer"],
            "original_id": qid  # Keep for matching with performance DB
        }

        unified_questions.APPEND(unified_question)

    RETURN unified_questions


FUNCTION compute_difficulty(model_results):
    """
    Estimate difficulty based on how many models failed
    """
    total_models = COUNT(model_results)
    failures = COUNT(WHERE is_correct == FALSE IN model_results)

    difficulty = failures / total_models  # 0.0 (easy) to 1.0 (hard)

    RETURN difficulty


# ==============================================================================
# STEP 5: BUILD PERFORMANCE DATABASE
# ==============================================================================

FUNCTION build_performance_database(all_questions):
    """
    Separate database for model-by-model performance
    Used for failure rate prediction
    """

    performance_db = {
        "metadata": {
            "total_questions": COUNT(all_questions),
            "models": SET_OF_ALL_MODELS(all_questions)
        },
        "questions": {}
    }

    FOR EACH qid, data IN all_questions:
        performance_db["questions"][qid] = {}

        FOR EACH model, result IN data["model_results"]:
            performance_db["questions"][qid][model] = {
                "question_id": qid,
                "correct_answer": data["question"]["correct_answer"],
                "model_prediction": result["prediction"],
                "is_correct": result["is_correct"],
                "question_text": data["question"]["question_text"],
                "domain": data["question"]["domain"]
            }

    RETURN performance_db


# ==============================================================================
# STEP 6: SAVE TO DISK
# ==============================================================================

FUNCTION save_databases(unified_questions, performance_db):
    """
    Save both databases for MCP use
    """

    # Database 1: All questions for semantic search
    unified_db = {
        "metadata": {
            "total_questions": COUNT(unified_questions),
            "sources": ["MMLU-Pro", "Original 13K questions"]
        },
        "questions": unified_questions
    }

    JSON.save("data/unified_database_with_mmlu_pro.json", unified_db)
    # Result: 13,100 questions (13,000 original + 100 MMLU-Pro)

    # Database 2: Performance data for failure prediction
    JSON.save("data/model_performance_database.json", performance_db)
    # Result: 170 questions with model performance


# ==============================================================================
# MAIN EXECUTION FLOW
# ==============================================================================

FUNCTION main():
    PRINT("Extracting MMLU-Pro questions from eval cache...")

    # Step 1: Find all eval files
    eval_files = find_eval_files()
    PRINT(f"Found {COUNT(eval_files)} eval files")

    # Step 2-3: Extract and aggregate
    all_questions = aggregate_all_eval_files(eval_files)
    PRINT(f"Extracted {COUNT(all_questions)} unique questions")

    # Step 4: Build unified database
    unified_questions = build_unified_database(all_questions)

    # Step 5: Build performance database
    performance_db = build_performance_database(all_questions)

    # Step 6: Save
    save_databases(unified_questions, performance_db)

    PRINT("✅ Complete!")
    PRINT(f"   Unified DB: {COUNT(unified_questions)} questions")
    PRINT(f"   Performance DB: {COUNT(performance_db['questions'])} questions with model results")


# ==============================================================================
# EXAMPLE DATA FLOW
# ==============================================================================

"""
INPUT (from eval cache file):
{
    "model_name": "Llama-2-13b-hf_5shots",
    "predictions": [
        {
            "question_id": 70,
            "question": "Typical advertising regulatory bodies suggest...",
            "answer": "I",
            "pred": "I",  # Model got it right
            "category": "business"
        }
    ]
}

↓ EXTRACT ↓

INTERMEDIATE (per-question aggregation):
{
    "70": {
        "question": {
            "id": 70,
            "text": "Typical advertising regulatory bodies suggest...",
            "domain": "business",
            "correct_answer": "I"
        },
        "model_results": {
            "Llama-2-13b-hf": {"prediction": "I", "is_correct": True},
            "Llama-2-7b-hf": {"prediction": "D", "is_correct": False},
            "Meta-Llama-3-70B": {"prediction": "A", "is_correct": False}
        }
    }
}

↓ SPLIT INTO TWO DATABASES ↓

OUTPUT 1 - Unified Database (for semantic search):
{
    "questions": [
        {
            "question_id": "mmlu_pro_70",
            "question_text": "Typical advertising regulatory bodies suggest...",
            "domain": "business",
            "difficulty_score": 0.67,  # 2 of 3 models failed
            "source": "MMLU-Pro",
            "original_id": 70
        }
    ]
}

OUTPUT 2 - Performance Database (for failure prediction):
{
    "questions": {
        "70": {
            "Llama-2-13b-hf": {
                "is_correct": True,
                "model_prediction": "I",
                "correct_answer": "I"
            },
            "Llama-2-7b-hf": {
                "is_correct": False,
                "model_prediction": "D",
                "correct_answer": "I"
            },
            "Meta-Llama-3-70B": {
                "is_correct": False,
                "model_prediction": "A",
                "correct_answer": "I"
            }
        }
    }
}
"""


# ==============================================================================
# ACTUAL NUMBERS FROM OUR EXTRACTION
# ==============================================================================

"""
WHAT WE ACTUALLY EXTRACTED:

Input:
- 47 eval cache files
- Each file: 100-12,000 predictions per model

Process:
- Files with complete predictions: 4 models
  (Llama-2: 7B, 13B, 70B + Meta-Llama-3-70B)
- Many files only had metadata, no predictions array

Output:
- Unified DB: 13,100 questions total
  - 13,000 original questions
  - 100 MMLU-Pro questions with full data

- Performance DB: 170 questions
  - With results from 4 models
  - Coverage: 1.3% of total database

LIMITATION:
- Only 4 models extracted (most eval files missing predictions array)
- Only 170 questions have performance data
- To get all 12K MMLU-Pro: would need to re-download eval results from GitHub
"""


# ==============================================================================
# TO GET FULL 12K MMLU-PRO FROM GITHUB (NOT YET IMPLEMENTED)
# ==============================================================================

"""
PSEUDOCODE for downloading from original source:

FUNCTION download_full_mmlu_pro():
    # Source: https://github.com/TIGER-AI-Lab/MMLU-Pro

    # Option 1: From Hugging Face
    dataset = huggingface.load_dataset("TIGER-Lab/MMLU-Pro")

    # Option 2: From GitHub releases
    URL = "https://github.com/TIGER-AI-Lab/MMLU-Pro/releases/download/v1.0/data.json"
    data = DOWNLOAD(URL)

    # Extract all 12,031 questions
    FOR EACH question IN data:
        question_id = question["question_id"]
        question_text = question["question"]
        category = question["category"]
        options = question["options"]
        answer = question["answer"]

        # Store in unified format
        ...

    # Note: This gives questions but NOT model performance
    # Would need separate eval results download for performance data

LIMITATION:
- Network restrictions prevented downloading from GitHub/HuggingFace
- Had to work with local eval cache only
- Hence only got 170 questions with performance instead of 12,031
"""
