#!/usr/bin/env python3
"""
Extract Model Performance from Eval Cache
==========================================

Processes eval cache files to extract per-question model performance.
This enables failure rate prediction based on similar questions.
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

def load_all_model_predictions():
    """Load all model predictions from eval cache"""

    eval_cache_dir = Path("./data/eval_cache")
    all_predictions = defaultdict(lambda: defaultdict(dict))  # {question_id: {model: {result}}}

    eval_files = list(eval_cache_dir.glob("mmlu_pro_model_outputs_*.json"))

    print(f"Loading {len(eval_files)} eval files...")

    models_loaded = 0
    total_predictions = 0

    for eval_file in eval_files:
        with open(eval_file, 'r') as f:
            data = json.load(f)

        model_name = data.get('model_name', eval_file.stem)

        # Clean model name
        model_name = model_name.replace('model_outputs_', '').replace('_5shots', '').replace('_0shots', '')

        if 'predictions' not in data or not data['predictions']:
            continue

        predictions = data['predictions']
        models_loaded += 1

        for pred in predictions:
            qid = pred.get('question_id')
            if qid is None:
                continue

            # Store prediction result
            correct_answer = pred.get('answer')
            model_pred = pred.get('pred')

            result = {
                'question_id': qid,
                'correct_answer': correct_answer,
                'model_prediction': model_pred,
                'is_correct': correct_answer == model_pred if (correct_answer and model_pred) else None,
                'question_text': pred.get('question'),
                'category': pred.get('category'),
                'domain': pred.get('category'),  # MMLU Pro uses 'category' for domain
                'generated_text': pred.get('generated_text', '')[:200]  # Truncate
            }

            all_predictions[qid][model_name] = result
            total_predictions += 1

    print(f"✅ Loaded {models_loaded} models")
    print(f"✅ Extracted {total_predictions} predictions")
    print(f"✅ Covering {len(all_predictions)} unique questions")

    return dict(all_predictions)


def aggregate_model_performance(predictions):
    """Aggregate performance statistics"""

    stats = {
        'total_questions': len(predictions),
        'models': set(),
        'by_domain': defaultdict(lambda: {'total': 0, 'by_model': defaultdict(lambda: {'correct': 0, 'total': 0})}),
        'by_model': defaultdict(lambda: {'correct': 0, 'total': 0, 'accuracy': 0.0})
    }

    for qid, model_results in predictions.items():
        for model, result in model_results.items():
            stats['models'].add(model)

            # Overall model stats
            stats['by_model'][model]['total'] += 1
            if result['is_correct']:
                stats['by_model'][model]['correct'] += 1

            # By domain stats
            domain = result.get('domain', 'unknown')
            stats['by_domain'][domain]['total'] += 1
            stats['by_domain'][domain]['by_model'][model]['total'] += 1
            if result['is_correct']:
                stats['by_domain'][domain]['by_model'][model]['correct'] += 1

    # Calculate accuracies
    for model, data in stats['by_model'].items():
        data['accuracy'] = (data['correct'] / data['total'] * 100) if data['total'] > 0 else 0

    for domain, data in stats['by_domain'].items():
        for model, model_data in data['by_model'].items():
            model_data['accuracy'] = (model_data['correct'] / model_data['total'] * 100) if model_data['total'] > 0 else 0

    stats['models'] = sorted(list(stats['models']))
    stats['by_domain'] = dict(stats['by_domain'])

    return stats


def save_performance_database(predictions, stats):
    """Save performance database for MCP use"""

    output = {
        'metadata': {
            'total_questions': stats['total_questions'],
            'total_models': len(stats['models']),
            'models': stats['models'],
            'description': 'Per-question model performance for failure rate prediction'
        },
        'overall_stats': {
            'by_model': stats['by_model'],
            'by_domain': stats['by_domain']
        },
        'questions': predictions
    }

    output_path = Path("./data/model_performance_database.json")
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Saved to {output_path}")
    print(f"   Size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")

    return output_path


def print_statistics(stats):
    """Print performance statistics"""

    print("\n" + "="*80)
    print("MODEL PERFORMANCE STATISTICS")
    print("="*80)

    print(f"\nTotal models evaluated: {len(stats['models'])}")
    print(f"Total questions: {stats['total_questions']}")

    print("\n" + "-"*80)
    print("TOP 10 MODELS BY ACCURACY")
    print("-"*80)

    sorted_models = sorted(stats['by_model'].items(), key=lambda x: x[1]['accuracy'], reverse=True)

    print(f"\n{'Rank':<6} {'Model':<50} {'Accuracy':<12} {'Correct':<10} {'Total':<10}")
    print("-" * 88)

    for rank, (model, data) in enumerate(sorted_models[:10], 1):
        print(f"{rank:<6} {model:<50} {data['accuracy']:>10.1f}% {data['correct']:>9} {data['total']:>9}")

    print("\n" + "-"*80)
    print("PERFORMANCE BY DOMAIN (Sample)")
    print("-"*80)

    # Show a few domains
    sample_domains = list(stats['by_domain'].items())[:5]

    for domain, data in sample_domains:
        print(f"\n{domain.upper()} ({data['total']} questions)")

        # Show top 3 models in this domain
        sorted_domain_models = sorted(data['by_model'].items(), key=lambda x: x[1]['accuracy'], reverse=True)

        for model, model_data in sorted_domain_models[:3]:
            print(f"  {model:<50} {model_data['accuracy']:>6.1f}%  ({model_data['correct']}/{model_data['total']})")


if __name__ == "__main__":
    print("="*80)
    print("EXTRACTING MODEL PERFORMANCE DATA")
    print("="*80)

    # Load all predictions
    predictions = load_all_model_predictions()

    # Aggregate statistics
    print("\nAggregating statistics...")
    stats = aggregate_model_performance(predictions)

    # Print statistics
    print_statistics(stats)

    # Save database
    print("\n" + "="*80)
    print("SAVING PERFORMANCE DATABASE")
    print("="*80)

    save_performance_database(predictions, stats)

    print("\n✅ Extraction complete!")
    print("\nThis database enables:")
    print("  • Failure rate prediction based on similar questions")
    print("  • Model comparison across question types")
    print("  • Domain-specific performance analysis")
    print("  • Taxonomy of model limitations")
