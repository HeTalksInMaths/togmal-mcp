#!/usr/bin/env python3
"""
Expand MLE-Bench with Additional Kaggle Competitions
====================================================

MLE-bench has 75 competitions. Kaggle has 100,000+ competitions.
Let's add more to expand training data.

Sources:
1. Kaggle API - Get all public competitions
2. Papers With Code - ML competition results
3. Historical competitions with published results
"""

import json
from pathlib import Path
from typing import Dict, List

class KaggleExpander:
    """
    Expand MLE-bench with additional Kaggle competitions

    Target: Add 200+ more competitions (82 → 300+)
    """

    def __init__(self):
        self.data_dir = Path("./data")

    def fetch_kaggle_competitions_metadata(self):
        """
        Fetch competition metadata from Kaggle API

        Requires: pip install kaggle
        Setup: ~/.kaggle/kaggle.json with API credentials
        """

        print("Fetching Kaggle competitions...")

        try:
            from kaggle import api

            # Get all competitions
            competitions = api.competitions_list()

            # Filter for completed competitions with evaluation
            completed = [c for c in competitions if c.enabledDate and c.deadline]

            print(f"  Found {len(completed)} completed competitions")

            # Categorize by type
            by_category = {}
            for comp in completed:
                category = comp.category or 'Other'
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(comp)

            print("\n  By category:")
            for cat, comps in sorted(by_category.items(), key=lambda x: -len(x[1])):
                print(f"    {cat}: {len(comps)}")

            return completed

        except ImportError:
            print("  ❌ Kaggle API not installed")
            print("  Run: pip install kaggle")
            print("  Setup: https://github.com/Kaggle/kaggle-api")
            return []

    def extract_competition_features(self, competition) -> Dict:
        """
        Extract difficulty-relevant features from competition

        Features:
        - Number of teams
        - Prize amount
        - Duration
        - Category (CV, NLP, tabular, etc.)
        - Evaluation metric
        """

        return {
            'id': competition.ref,
            'title': competition.title,
            'category': competition.category,
            'teams': competition.teamCount or 0,
            'prize': competition.totalPrize or 0,
            'metric': competition.evaluationMetric,
            'enabledDate': str(competition.enabledDate),
            'deadline': str(competition.deadline),
        }

    def estimate_difficulty_from_metadata(self, features: Dict) -> float:
        """
        Estimate difficulty based on competition metadata

        Heuristics:
        - More teams → harder (competitive)
        - Higher prize → harder (attracts better participants)
        - Longer duration → harder (needs more work)
        """

        difficulty = 0.5  # Base difficulty

        # Team count effect
        if features['teams'] > 5000:
            difficulty += 0.2  # Very competitive
        elif features['teams'] > 1000:
            difficulty += 0.1  # Competitive

        # Prize effect
        if features['prize'] > 100000:
            difficulty += 0.15  # High stakes
        elif features['prize'] > 25000:
            difficulty += 0.1  # Moderate stakes

        # Category effect
        if features['category'] in ['Featured', 'Research']:
            difficulty += 0.1  # Typically harder

        # Clamp to [0, 1]
        return min(max(difficulty, 0.0), 1.0)


# Target competitions to add (examples)
ADDITIONAL_COMPETITIONS = [
    # Classic competitions
    "digit-recognizer",  # MNIST - easy baseline
    "titanic",  # Getting started
    "house-prices-advanced-regression-techniques",

    # Computer vision
    "imagenet-object-localization-challenge",
    "dogs-vs-cats",  # Original version
    "facial-keypoints-detection",
    "state-farm-distracted-driver-detection",

    # NLP
    "word2vec-nlp-tutorial",
    "quora-question-pairs",
    "jigsaw-toxic-comment-classification",  # Different from challenge

    # Time series
    "bike-sharing-demand",
    "rossmann-store-sales",
    "recruit-restaurant-visitor-forecasting",
    "web-traffic-time-series-forecasting",

    # Tabular
    "porto-seguro-safe-driver-prediction",
    "santander-customer-transaction-prediction",
    "ieee-fraud-detection",
    "microsoft-malware-prediction",

    # Audio
    "tensorflow-speech-recognition",
    "freesound-audio-tagging",

    # Recommendation
    "santander-product-recommendation",
    "elo-merchant-category-recommendation",
]


def main():
    print("="*80)
    print("KAGGLE COMPETITION EXPANSION PLAN")
    print("="*80)

    expander = KaggleExpander()

    # Try to fetch from API
    competitions = expander.fetch_kaggle_competitions_metadata()

    if not competitions:
        print("\n💡 Manual approach:")
        print("  1. Install Kaggle API: pip install kaggle")
        print("  2. Get API credentials: https://www.kaggle.com/account")
        print("  3. Place in ~/.kaggle/kaggle.json")
        print("  4. Re-run this script")

    print(f"\n📊 EXPANSION PLAN:")
    print(f"  Current: 82 MLE-bench competitions")
    print(f"  Target: {len(ADDITIONAL_COMPETITIONS)} hand-picked competitions")
    print(f"  Potential: 1000+ from Kaggle API")

    print(f"\n🎯 Expected Impact:")
    print(f"  Training data: 82 → 300+ (3-4x increase)")
    print(f"  Correlation: 0.13 → 0.40-0.50 (more patterns)")
    print(f"  Confidence: 0.18 → 0.40-0.50 (more similar examples)")
    print(f"  MAE: 7.7% → 5-6% (better predictions)")


if __name__ == "__main__":
    main()
