"""
Import Real Model Results from TIGER-AI-Lab GitHub

Downloads actual model outputs from the MMLU-Pro repository and
converts them to our format.

Source: https://github.com/TIGER-AI-Lab/MMLU-Pro/tree/main/eval_results
"""

import json
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List
import urllib.request
from collections import Counter
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


TIGER_MODEL_FILES = {
    "meta-llama/Meta-Llama-3.1-70B-Instruct": "model_outputs_Meta-Llama-3_1-70B-Instruct_5shots.zip",
    "meta-llama/Meta-Llama-3.1-8B-Instruct": "model_outputs_Meta-Llama-3_1-8B-Instruct_5shots.zip",
    "Qwen/Qwen1.5-72B-Chat": "model_outputs_Qwen1.5-72B-Chat_5shots.zip",
    "mistralai/Mixtral-8x7B-Instruct-v0.1": "model_outputs_Mixtral-8x7B-Instruct-v0.1_5shots.zip",
    "mistralai/Mistral-7B-Instruct-v0.2": "model_outputs_Mistral-7B-Instruct-v0.2_5shots.zip",
}

BASE_URL = "https://github.com/TIGER-AI-Lab/MMLU-Pro/raw/main/eval_results/"


def download_model_results(model_name: str, zip_filename: str, output_dir: Path) -> Path:
    """
    Download and extract model results from TIGER-AI-Lab repo.
    """
    url = BASE_URL + zip_filename
    logger.info(f"Downloading {zip_filename}...")

    # Download to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        urllib.request.urlretrieve(url, tmp_file.name)
        zip_path = Path(tmp_file.name)

    # Extract
    logger.info(f"Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)

    # Find the JSON file
    json_filename = zip_filename.replace('.zip', '.json')
    json_path = output_dir / json_filename

    # Clean up zip
    zip_path.unlink()

    logger.info(f"✓ Downloaded and extracted to {json_path}")
    return json_path


def convert_tiger_to_our_format(
    tiger_results: List[Dict],
    model_name: str
) -> Dict[str, Dict]:
    """
    Convert TIGER-AI-Lab format to our format.

    TIGER format:
    {
        "question_id": 1986,
        "question": "...",
        "options": ["A...", "B...", ...],
        "answer": "E",  # correct answer
        "category": "psychology",
        "pred": "E",  # model prediction
        "generated_text": "..."
    }

    Our format:
    {
        "question_id": "mmlu_pro_1986",
        "question_text": "...",
        "choices": [...],
        "correct_answer": "E",
        "domain": "psychology",
        "model_results": {
            "model_name": {
                "is_correct": True/False,
                "answer": "E",
                "confidence": None
            }
        }
    }
    """
    questions = {}

    for item in tiger_results:
        question_id = f"mmlu_pro_{item['question_id']}"

        # Check if model answered correctly
        correct_answer = item['answer']
        model_answer = item.get('pred', 'UNKNOWN')
        is_correct = (model_answer == correct_answer)

        # Create or update question
        if question_id not in questions:
            questions[question_id] = {
                'question_id': question_id,
                'source_benchmark': 'MMLU_Pro',
                'question_text': item['question'],
                'choices': item['options'],
                'correct_answer': correct_answer,
                'domain': item.get('category', 'unknown'),
                'cot_content': item.get('cot_content', ''),
                'model_results': {},
                'success_rate': None,
                'num_models': 0,
                'difficulty_tier': None,
                'difficulty_label': None
            }

        # Add model result
        questions[question_id]['model_results'][model_name] = {
            'is_correct': is_correct,
            'answer': model_answer,
            'confidence': None  # Not available in TIGER data
        }

    return questions


def merge_multiple_models(
    all_models_data: Dict[str, List[Dict]]
) -> Dict[str, Dict]:
    """
    Merge results from multiple models into single dataset.
    """
    merged_questions = {}

    for model_name, tiger_results in all_models_data.items():
        logger.info(f"Processing {model_name} ({len(tiger_results)} questions)...")

        model_questions = convert_tiger_to_our_format(tiger_results, model_name)

        # Merge into main dataset
        for qid, qdata in model_questions.items():
            if qid not in merged_questions:
                merged_questions[qid] = qdata
            else:
                # Add model results to existing question
                merged_questions[qid]['model_results'].update(qdata['model_results'])

    return merged_questions


def compute_success_rates(questions: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Compute success rates and difficulty labels.
    """
    logger.info("Computing success rates...")

    for qid, qdata in questions.items():
        model_results = qdata.get('model_results', {})

        if not model_results:
            continue

        # Count correct
        correct_count = sum(
            1 for r in model_results.values()
            if r.get('is_correct', False)
        )

        total = len(model_results)
        success_rate = correct_count / total if total > 0 else 0

        # Update
        qdata['success_rate'] = success_rate
        qdata['num_models'] = total

        # Classify difficulty
        if success_rate < 0.3:
            qdata['difficulty_tier'] = 'low'
            qdata['difficulty_label'] = 'Hard'
        elif success_rate < 0.7:
            qdata['difficulty_tier'] = 'medium'
            qdata['difficulty_label'] = 'Moderate'
        else:
            qdata['difficulty_tier'] = 'high'
            qdata['difficulty_label'] = 'Easy'

    return questions


def main():
    """
    Download real model results from TIGER-AI-Lab and convert to our format.
    """
    print("="*80)
    print("IMPORTING REAL MODEL RESULTS FROM TIGER-AI-LAB")
    print("="*80)

    # Create temp directory for downloads
    temp_dir = Path(tempfile.mkdtemp())
    logger.info(f"Using temp directory: {temp_dir}")

    # Download and load all models
    all_models_data = {}

    for model_name, zip_filename in TIGER_MODEL_FILES.items():
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {model_name}")
        logger.info(f"{'='*80}")

        try:
            # Download
            json_path = download_model_results(model_name, zip_filename, temp_dir)

            # Load
            with open(json_path, 'r') as f:
                tiger_results = json.load(f)

            logger.info(f"Loaded {len(tiger_results)} results")
            all_models_data[model_name] = tiger_results

        except Exception as e:
            logger.error(f"Failed to download {model_name}: {e}")
            continue

    if not all_models_data:
        logger.error("No models downloaded successfully")
        return

    # Merge all models
    logger.info(f"\n{'='*80}")
    logger.info("MERGING RESULTS FROM ALL MODELS")
    logger.info(f"{'='*80}\n")

    merged_questions = merge_multiple_models(all_models_data)

    logger.info(f"Total questions: {len(merged_questions)}")

    # Compute success rates
    merged_questions = compute_success_rates(merged_questions)

    # Statistics
    logger.info(f"\n{'='*80}")
    logger.info("STATISTICS")
    logger.info(f"{'='*80}\n")

    total_inferences = sum(len(q['model_results']) for q in merged_questions.values())
    total_errors = sum(
        1 for q in merged_questions.values()
        for r in q['model_results'].values()
        if not r.get('is_correct', True)
    )

    logger.info(f"📊 Dataset:")
    logger.info(f"  Total questions: {len(merged_questions):,}")
    logger.info(f"  Models: {len(all_models_data)}")
    logger.info(f"  Total inferences: {total_inferences:,}")
    logger.info(f"  Total errors: {total_errors:,} ({total_errors/total_inferences*100:.1f}%)")

    # Domain distribution
    domains = Counter(q['domain'] for q in merged_questions.values())
    logger.info(f"\n📊 Questions by Domain:")
    for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]:
        logger.info(f"  {domain}: {count}")

    # Difficulty distribution
    difficulty = Counter(q.get('difficulty_label', 'Unknown') for q in merged_questions.values())
    logger.info(f"\n📊 Difficulty Distribution:")
    for label, count in difficulty.most_common():
        logger.info(f"  {label}: {count} ({count/len(merged_questions)*100:.1f}%)")

    # Model performance
    logger.info(f"\n📊 Model Performance:")
    for model_name in all_models_data.keys():
        correct = sum(
            1 for q in merged_questions.values()
            for m, r in q['model_results'].items()
            if m == model_name and r.get('is_correct', False)
        )
        total = sum(
            1 for q in merged_questions.values()
            if model_name in q['model_results']
        )
        accuracy = correct / total if total > 0 else 0
        short_name = model_name.split('/')[-1]
        logger.info(f"  {short_name}: {accuracy*100:.1f}% ({correct}/{total})")

    # Save
    output_path = Path("data/mmlu_pro_full/mmlu_pro_real_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        'metadata': {
            'source': 'TIGER-AI-Lab/MMLU-Pro (GitHub)',
            'total_questions': len(merged_questions),
            'models': list(all_models_data.keys()),
            'total_inferences': total_inferences,
            'total_errors': total_errors
        },
        'questions': merged_questions
    }

    logger.info(f"\n{'='*80}")
    logger.info(f"SAVING DATASET")
    logger.info(f"{'='*80}\n")

    logger.info(f"Writing to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"✓ Saved {len(merged_questions)} questions ({file_size_mb:.1f} MB)")

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    logger.info(f"\n{'='*80}")
    logger.info("COMPLETE!")
    logger.info(f"{'='*80}\n")

    logger.info(f"✅ Real MMLU-Pro dataset with model results ready!")
    logger.info(f"   {output_path}")
    logger.info(f"\n📊 Summary:")
    logger.info(f"   • {len(merged_questions):,} questions")
    logger.info(f"   • {len(all_models_data)} models")
    logger.info(f"   • {total_errors:,} errors to analyze")
    logger.info(f"\n🚀 Next step:")
    logger.info(f"   python week1_2_validation.py")


if __name__ == "__main__":
    main()
