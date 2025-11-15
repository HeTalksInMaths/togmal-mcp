#!/usr/bin/env python3
"""
Dataset Statistics Dashboard
=============================

Quick stats view for the autonomous benchmark dataset.

Author: ToGMAL Project
"""

import json
from pathlib import Path
from datetime import datetime

def format_size(bytes):
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"

def check_stats():
    """Display dataset statistics."""
    print("="*70)
    print("📊 AUTONOMOUS BENCHMARK DATASET - STATISTICS")
    print("="*70)

    # State file
    state_file = Path("data/autonomous_state.json")
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)

        print("\n🎯 SELECTION CRITERIA")
        print(f"  Top SOTA models: {state['selection_criteria']['top_sota']}")
        print(f"  Top Medium (~32B): {state['selection_criteria']['top_medium']}")
        print(f"  Top Small (~8B): {state['selection_criteria']['top_small']}")

        print("\n📈 CURRENT STATUS")
        print(f"  Total questions: {state['total_questions']:,}")
        print(f"  Models selected: {len(state['selected_models'])}")
        print(f"  Benchmarks: {', '.join(state['benchmarks_processed'])}")

        last_check = datetime.fromisoformat(state['last_check'])
        print(f"  Last updated: {last_check.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n🤖 SELECTED MODELS")
        for i, (name, metadata) in enumerate(state['model_metadata'].items(), 1):
            size = f"{metadata['size_params']}B" if metadata['size_params'] else "?B"
            category = metadata['size_category']
            acc = metadata['accuracy']

            category_icon = {
                'small': '📱',
                'medium': '🏢',
                'large': '🏭',
                'unknown': '🌟'
            }.get(category, '❓')

            print(f"  {i}. {category_icon} {name:50s} {size:>6s}  {acc:>5.1f}%  [{category}]")

    # Dataset files
    dataset_file = Path("data/autonomous_benchmarks/autonomous_dataset.json")
    vector_file = Path("data/autonomous_benchmarks/vector_db_ready.json")

    if dataset_file.exists():
        print("\n💾 DATASET FILES")

        size = dataset_file.stat().st_size
        print(f"  Full dataset: {format_size(size):>10s}  ({dataset_file})")

        if vector_file.exists():
            size = vector_file.stat().st_size
            print(f"  Vector ready: {format_size(size):>10s}  ({vector_file})")

        # Sample question
        with open(dataset_file) as f:
            data = json.load(f)

        print(f"\n📊 DATASET ANALYSIS")
        questions = data['questions']
        print(f"  Total questions: {len(questions):,}")
        print(f"  Total predictions: {len(questions) * len(state['selected_models']):,}")

        # Success rate distribution
        success_rates = [q['success_rate'] for q in questions]
        avg_success = sum(success_rates) / len(success_rates)

        high_risk = sum(1 for sr in success_rates if sr < 0.3)
        medium_risk = sum(1 for sr in success_rates if 0.3 <= sr < 0.7)
        low_risk = sum(1 for sr in success_rates if sr >= 0.7)

        print(f"\n🎯 SUCCESS RATE DISTRIBUTION")
        print(f"  Average: {avg_success*100:.1f}%")
        print(f"  🔴 High risk (<30%): {high_risk:,} questions ({high_risk/len(questions)*100:.1f}%)")
        print(f"  🟡 Medium risk (30-70%): {medium_risk:,} questions ({medium_risk/len(questions)*100:.1f}%)")
        print(f"  🟢 Low risk (>70%): {low_risk:,} questions ({low_risk/len(questions)*100:.1f}%)")

        # Category breakdown
        categories = {}
        for q in questions:
            cat = q.get('metadata', {}).get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1

        print(f"\n📚 CATEGORY BREAKDOWN (Top 10)")
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]
        for cat, count in sorted_cats:
            print(f"  {cat:30s}: {count:>5,} questions")

        # Sample question
        print(f"\n📝 SAMPLE QUESTION")
        sample = questions[0]
        print(f"  Q: {sample['question'][:100]}...")
        print(f"  Category: {sample.get('metadata', {}).get('category', 'N/A')}")
        print(f"  Success rate: {sample['success_rate']*100:.1f}%")
        print(f"  Models tested: {len(sample['model_scores'])}")

        passing = sum(1 for v in sample['model_scores'].values() if v)
        print(f"  Passing models: {passing}/{len(sample['model_scores'])}")

    print("\n" + "="*70)
    print("✅ Dataset ready for vector database and ToGMAL MCP!")
    print("="*70)

if __name__ == '__main__':
    check_stats()
