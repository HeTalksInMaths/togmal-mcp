#!/usr/bin/env python3
"""
Rebuild MMLU-Pro Dataset From Local eval_results
=================================================

Offline replacement for the GitHub-API portion of autonomous_benchmark_grower.py.

The grower lists TIGER-AI-Lab/MMLU-Pro eval_results via api.github.com, which
fails with 403 when unauthenticated (60 req/hour rate limit). This script reads
the same model-output zips from a local checkout instead:

    git clone --depth 1 --filter=blob:none --sparse \
        https://github.com/TIGER-AI-Lab/MMLU-Pro.git
    cd MMLU-Pro && git sparse-checkout set eval_results

Then:

    python3 rebuild_mmlu_pro_from_local.py /path/to/MMLU-Pro/eval_results

Outputs (same formats the grower produces):
    data/autonomous_benchmarks/autonomous_dataset.json
    data/autonomous_benchmarks/vector_db_ready.json
"""

import io
import json
import logging
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("./data/autonomous_benchmarks")


def parse_model_name(zip_path: Path) -> str:
    """model_outputs_<NAME>_5shots.zip -> <NAME>"""
    m = re.match(r'model_outputs_(.+?)_5shots\.zip$', zip_path.name)
    return m.group(1) if m else zip_path.stem


def load_predictions(zip_path: Path):
    """Yield prediction records from a model-output zip.

    Handles the format variants present in eval_results:
    - a single JSON list of prediction dicts (most models)
    - a dict of category -> list of prediction dicts
    - summary.json files (aggregate scores only) are skipped
    - malformed JSON files are skipped with a warning
    """
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.endswith('.json') or 'summary' in name.lower():
                continue
            try:
                with zf.open(name) as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"  ✗ Malformed JSON in {zip_path.name}:{name}, skipping file")
                continue

            if isinstance(data, list):
                for rec in data:
                    if isinstance(rec, dict):
                        yield rec
            elif isinstance(data, dict):
                for value in data.values():
                    if isinstance(value, list):
                        for rec in value:
                            if isinstance(rec, dict):
                                yield rec


def build_dataset(eval_dir: Path, max_questions: int = 13000) -> dict:
    zips = sorted(eval_dir.glob('model_outputs_*_5shots.zip'))
    if not zips:
        raise FileNotFoundError(f"No model_outputs_*_5shots.zip files in {eval_dir}")

    logger.info(f"Found {len(zips)} model output archives in {eval_dir}")

    question_map = {}
    models_loaded = []

    for zip_path in zips:
        model_name = parse_model_name(zip_path)
        count = 0

        try:
            for pred in load_predictions(zip_path):
                q_id = pred.get('question_id')
                if q_id is None:
                    q_id = pred.get('question', '')[:100]
                q_id = str(q_id)

                if q_id not in question_map:
                    question_map[q_id] = {
                        'question': pred.get('question', ''),
                        'benchmark': 'MMLU-Pro',
                        'model_scores': {},
                        'metadata': {
                            'subject': pred.get('src', ''),
                            'category': pred.get('category', ''),
                            'options': pred.get('options', [])
                        }
                    }

                if 'correct' in pred:
                    is_correct = bool(pred['correct'])
                else:
                    is_correct = pred.get('pred') == pred.get('answer')

                question_map[q_id]['model_scores'][model_name] = is_correct
                count += 1
        except (zipfile.BadZipFile, json.JSONDecodeError) as e:
            logger.warning(f"  ✗ Skipping {zip_path.name}: {e}")
            continue

        models_loaded.append(model_name)
        logger.info(f"  ✓ {model_name}: {count:,} predictions")

    logger.info(f"\n📊 {len(question_map):,} unique questions from {len(models_loaded)} models")

    questions = []
    for q_id, q_data in question_map.items():
        scores = q_data['model_scores']
        q_data['success_rate'] = (
            sum(1 for v in scores.values() if v) / len(scores) if scores else 0.0
        )
        questions.append(q_data)
        if len(questions) >= max_questions:
            break

    return {
        'metadata': {
            'total_questions': len(questions),
            'num_models': len(models_loaded),
            'models': models_loaded,
            'benchmarks': ['MMLU-Pro'],
            'source': 'local eval_results checkout (offline rebuild)',
            'created_at': datetime.now().isoformat()
        },
        'questions': questions
    }


def export_for_vector_db(dataset: dict, output_file: Path):
    """Same ChromaDB-compatible format as the grower's export_for_vector_db."""
    documents, metadatas, ids = [], [], []

    for i, q in enumerate(dataset['questions']):
        documents.append(q['question'])
        metadatas.append({
            'benchmark': q.get('benchmark', ''),
            'success_rate': q['success_rate'],
            'num_models': len(q['model_scores']),
            'model_scores': json.dumps(q['model_scores']),
            'category': q.get('metadata', {}).get('category', ''),
            'subject': q.get('metadata', {}).get('subject', '')
        })
        ids.append(f"q_{i}")

    vector_data = {
        'documents': documents,
        'metadatas': metadatas,
        'ids': ids,
        'source_metadata': dataset['metadata']
    }

    with open(output_file, 'w') as f:
        json.dump(vector_data, f, indent=2)

    logger.info(f"💾 Vector DB ready: {output_file} "
                f"({output_file.stat().st_size / 1024 / 1024:.1f} MB)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    eval_dir = Path(sys.argv[1])
    max_questions = int(sys.argv[2]) if len(sys.argv) > 2 else 13000

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset = build_dataset(eval_dir, max_questions=max_questions)

    dataset_file = OUTPUT_DIR / "autonomous_dataset.json"
    with open(dataset_file, 'w') as f:
        json.dump(dataset, f, indent=2)
    logger.info(f"💾 Saved: {dataset_file} "
                f"({dataset_file.stat().st_size / 1024 / 1024:.1f} MB)")

    export_for_vector_db(dataset, OUTPUT_DIR / "vector_db_ready.json")

    logger.info("\n✅ Rebuild complete. Next: python3 build_complete_unified_db.py")


if __name__ == '__main__':
    main()
