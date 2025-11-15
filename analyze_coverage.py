#!/usr/bin/env python3
"""
Coverage Analysis & Gap Detection
==================================

Analyzes dataset coverage and identifies shortfalls to guide growth.

Author: ToGMAL Project
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any
import statistics

class CoverageAnalyzer:
    """Analyzes dataset coverage and identifies gaps."""

    def __init__(self, dataset_file: Path = Path("data/autonomous_benchmarks/autonomous_dataset.json")):
        """Initialize analyzer."""
        self.dataset_file = dataset_file
        with open(dataset_file) as f:
            self.data = json.load(f)
        self.questions = self.data['questions']
        self.metadata = self.data['metadata']

    def analyze_all(self):
        """Run all coverage analyses."""
        print("="*70)
        print("📊 COVERAGE ANALYSIS & GAP DETECTION")
        print("="*70)

        analyses = [
            ("📚 Category Coverage", self.analyze_category_coverage),
            ("🎯 Difficulty Distribution", self.analyze_difficulty_distribution),
            ("🤖 Model Size Coverage", self.analyze_model_size_coverage),
            ("⚠️  Risk Tier Balance", self.analyze_risk_tier_balance),
            ("🔍 Subject Depth", self.analyze_subject_depth),
            ("📈 Performance Gaps", self.analyze_performance_gaps),
            ("💡 Growth Recommendations", self.recommend_growth_targets)
        ]

        for title, analysis_func in analyses:
            print(f"\n{title}")
            print("-" * 70)
            analysis_func()

        print("\n" + "="*70)
        print("✅ ANALYSIS COMPLETE")
        print("="*70)

    def analyze_category_coverage(self):
        """Analyze coverage across categories."""
        category_stats = defaultdict(lambda: {
            'count': 0,
            'avg_success': [],
            'models_tested': set()
        })

        for q in self.questions:
            cat = q.get('metadata', {}).get('category', 'unknown')
            category_stats[cat]['count'] += 1
            category_stats[cat]['avg_success'].append(q['success_rate'])
            category_stats[cat]['models_tested'].update(q['model_scores'].keys())

        # Sort by count
        sorted_cats = sorted(category_stats.items(), key=lambda x: x[1]['count'], reverse=True)

        print(f"\n{'Category':<30s} {'Questions':>10s} {'Avg Success':>12s} {'Models':>8s}")
        print("-" * 70)

        total_q = len(self.questions)
        for cat, stats in sorted_cats:
            count = stats['count']
            avg = statistics.mean(stats['avg_success']) * 100
            models = len(stats['models_tested'])
            pct = count / total_q * 100

            # Flag under-represented categories
            flag = "⚠️ " if count < 300 else "  "
            print(f"{flag}{cat:<30s} {count:>10,} ({pct:>4.1f}%) {avg:>10.1f}% {models:>8}")

        # Identify gaps
        print(f"\n🔴 GAPS IDENTIFIED:")
        underrep = [cat for cat, stats in sorted_cats if stats['count'] < 300]
        if underrep:
            print(f"  Under-represented (<300 questions): {', '.join(underrep[:5])}")
        else:
            print(f"  ✅ All categories well-represented")

    def analyze_difficulty_distribution(self):
        """Analyze difficulty levels based on success rates."""
        difficulty_tiers = {
            'Very Easy (>80%)': [],
            'Easy (60-80%)': [],
            'Medium (40-60%)': [],
            'Hard (20-40%)': [],
            'Very Hard (<20%)': []
        }

        for q in self.questions:
            sr = q['success_rate'] * 100
            if sr > 80:
                difficulty_tiers['Very Easy (>80%)'].append(q)
            elif sr > 60:
                difficulty_tiers['Easy (60-80%)'].append(q)
            elif sr > 40:
                difficulty_tiers['Medium (40-60%)'].append(q)
            elif sr > 20:
                difficulty_tiers['Hard (20-40%)'].append(q)
            else:
                difficulty_tiers['Very Hard (<20%)'].append(q)

        print(f"\n{'Difficulty Tier':<25s} {'Count':>10s} {'Percentage':>12s}")
        print("-" * 70)

        total = len(self.questions)
        for tier, questions in difficulty_tiers.items():
            count = len(questions)
            pct = count / total * 100
            print(f"  {tier:<25s} {count:>10,} {pct:>11.1f}%")

        # Check balance
        print(f"\n🔍 BALANCE CHECK:")
        ideal_range = (15, 35)  # Each tier should be 15-35% ideally
        for tier, questions in difficulty_tiers.items():
            pct = len(questions) / total * 100
            if pct < ideal_range[0]:
                print(f"  ⚠️  {tier}: Under-represented ({pct:.1f}%)")
            elif pct > ideal_range[1]:
                print(f"  ⚠️  {tier}: Over-represented ({pct:.1f}%)")

    def analyze_model_size_coverage(self):
        """Analyze coverage across model sizes."""
        # Extract model size distribution
        size_coverage = {
            'Small (≤10B)': [],
            'Medium (10-40B)': [],
            'Large (>40B)': [],
            'Unknown/API': []
        }

        for model_data in self.metadata['models']:
            size_params = model_data.get('size_params')
            category = model_data.get('size_category')
            accuracy = model_data.get('accuracy')

            if category == 'small':
                size_coverage['Small (≤10B)'].append(model_data)
            elif category == 'medium':
                size_coverage['Medium (10-40B)'].append(model_data)
            elif category == 'large':
                size_coverage['Large (>40B)'].append(model_data)
            else:
                size_coverage['Unknown/API'].append(model_data)

        print(f"\n{'Size Category':<20s} {'Models':>8s} {'Avg Accuracy':>15s} {'Range':>15s}")
        print("-" * 70)

        for category, models in size_coverage.items():
            if not models:
                continue

            count = len(models)
            accuracies = [m['accuracy'] for m in models]
            avg = statistics.mean(accuracies)
            min_acc = min(accuracies)
            max_acc = max(accuracies)

            print(f"  {category:<20s} {count:>8} {avg:>14.1f}% {min_acc:>6.1f}%-{max_acc:<6.1f}%")

        # Check for gaps
        print(f"\n🔍 MODEL SIZE GAPS:")
        total_models = len(self.metadata['models'])
        for category, models in size_coverage.items():
            pct = len(models) / total_models * 100
            if pct < 10:
                print(f"  ⚠️  {category}: Only {len(models)} models ({pct:.1f}%)")

    def analyze_risk_tier_balance(self):
        """Analyze balance of risk tiers for ToGMAL."""
        risk_tiers = {
            'High Risk (<30%)': 0,
            'Medium Risk (30-70%)': 0,
            'Low Risk (>70%)': 0
        }

        # Also track by category
        category_risk = defaultdict(lambda: {'high': 0, 'medium': 0, 'low': 0})

        for q in self.questions:
            sr = q['success_rate']
            cat = q.get('metadata', {}).get('category', 'unknown')

            if sr < 0.3:
                risk_tiers['High Risk (<30%)'] += 1
                category_risk[cat]['high'] += 1
            elif sr < 0.7:
                risk_tiers['Medium Risk (30-70%)'] += 1
                category_risk[cat]['medium'] += 1
            else:
                risk_tiers['Low Risk (>70%)'] += 1
                category_risk[cat]['low'] += 1

        print(f"\n{'Risk Tier':<25s} {'Count':>10s} {'Percentage':>12s}")
        print("-" * 70)

        total = len(self.questions)
        for tier, count in risk_tiers.items():
            pct = count / total * 100
            print(f"  {tier:<25s} {count:>10,} {pct:>11.1f}%")

        # Identify categories with poor risk diversity
        print(f"\n⚠️  CATEGORIES WITH POOR RISK DIVERSITY:")
        for cat, risks in sorted(category_risk.items(), key=lambda x: sum(x[1].values()), reverse=True)[:10]:
            total_cat = sum(risks.values())
            if total_cat < 100:
                continue

            # Check if too concentrated in one tier
            max_tier = max(risks.values())
            if max_tier / total_cat > 0.7:  # >70% in one tier
                print(f"  {cat}: {risks['high']} high, {risks['medium']} med, {risks['low']} low (unbalanced)")

    def analyze_subject_depth(self):
        """Analyze depth of coverage per subject."""
        subject_stats = defaultdict(lambda: {
            'count': 0,
            'categories': set(),
            'success_rates': []
        })

        for q in self.questions:
            subject = q.get('metadata', {}).get('subject', 'unknown')
            cat = q.get('metadata', {}).get('category', 'unknown')

            subject_stats[subject]['count'] += 1
            subject_stats[subject]['categories'].add(cat)
            subject_stats[subject]['success_rates'].append(q['success_rate'])

        # Find subjects with <50 questions
        shallow_subjects = []
        deep_subjects = []

        for subject, stats in subject_stats.items():
            if stats['count'] < 50:
                shallow_subjects.append((subject, stats['count']))
            elif stats['count'] > 500:
                deep_subjects.append((subject, stats['count']))

        print(f"\n📉 SHALLOW COVERAGE (<50 questions): {len(shallow_subjects)} subjects")
        for subject, count in sorted(shallow_subjects, key=lambda x: x[1])[:10]:
            print(f"  {subject}: {count} questions")

        print(f"\n📈 DEEP COVERAGE (>500 questions): {len(deep_subjects)} subjects")
        for subject, count in sorted(deep_subjects, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {subject}: {count:,} questions")

    def analyze_performance_gaps(self):
        """Identify where models struggle most."""
        # Find questions where all models struggle
        universal_failures = []
        universal_successes = []
        high_variance = []

        for q in self.questions:
            sr = q['success_rate']
            scores = list(q['model_scores'].values())

            if sr < 0.2:  # <20% success
                universal_failures.append(q)
            elif sr > 0.9:  # >90% success
                universal_successes.append(q)

            # High variance: some models pass, others fail
            if 0.3 < sr < 0.7:
                high_variance.append(q)

        print(f"\n🔴 UNIVERSAL FAILURES (<20% success): {len(universal_failures)} questions")
        if universal_failures:
            # Sample categories
            cats = [q.get('metadata', {}).get('category', 'unknown') for q in universal_failures[:20]]
            cat_counts = defaultdict(int)
            for c in cats:
                cat_counts[c] += 1
            print(f"  Common categories: {dict(cat_counts)}")

        print(f"\n🟢 UNIVERSAL SUCCESSES (>90% success): {len(universal_successes)} questions")

        print(f"\n🟡 HIGH VARIANCE (30-70% success): {len(high_variance)} questions")
        print(f"  These are ideal for testing model capability differences")

    def recommend_growth_targets(self):
        """Recommend what to grow next."""
        print(f"\n🎯 RECOMMENDED GROWTH PRIORITIES:")

        # Priority 1: Under-represented categories
        category_counts = defaultdict(int)
        for q in self.questions:
            cat = q.get('metadata', {}).get('category', 'unknown')
            category_counts[cat] += 1

        underrep_cats = [cat for cat, count in category_counts.items() if count < 500]
        if underrep_cats:
            print(f"\n1. EXPAND CATEGORIES ({len(underrep_cats)} need more coverage):")
            for cat in sorted(underrep_cats, key=lambda c: category_counts[c])[:5]:
                print(f"   - {cat}: {category_counts[cat]} → target 800+")

        # Priority 2: Add more difficult questions
        hard_count = sum(1 for q in self.questions if q['success_rate'] < 0.4)
        hard_pct = hard_count / len(self.questions) * 100
        if hard_pct < 25:
            print(f"\n2. ADD HARDER QUESTIONS (currently {hard_pct:.1f}%):")
            print(f"   - Target: 25-30% hard questions")
            print(f"   - Need: ~{int(len(self.questions) * 0.25 - hard_count)} more hard questions")

        # Priority 3: More benchmarks
        print(f"\n3. ADD MORE BENCHMARKS:")
        print(f"   - Current: {', '.join(self.metadata['benchmarks'])}")
        print(f"   - Recommended additions:")
        print(f"     • HumanEval (code generation)")
        print(f"     • GSM8K (math reasoning)")
        print(f"     • HellaSwag (commonsense)")
        print(f"     • ARC-Challenge (science reasoning)")

        # Priority 4: Model diversity
        current_models = len(self.metadata['models'])
        available_models = 48  # from MMLU-Pro
        if current_models < available_models * 0.6:
            print(f"\n4. ADD MORE MODELS:")
            print(f"   - Current: {current_models}/48 available ({current_models/48*100:.0f}%)")
            print(f"   - Target: ~30 models (60% coverage)")


if __name__ == '__main__':
    analyzer = CoverageAnalyzer()
    analyzer.analyze_all()
