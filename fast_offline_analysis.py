#!/usr/bin/env python3
"""
Fast Offline Mass Failure Analysis
===================================

Analyzes thousands of model failures in seconds using ONLY:
1. Feature Engineering (no external models needed)
2. TF-IDF Embeddings (sklearn, fully offline)
3. Random Forest + Feature Importance
4. PCA/t-SNE for visualization
5. Statistical analysis

NO DEPENDENCIES ON:
- HuggingFace models
- External APIs
- Pre-trained transformers

Pure sklearn + numpy + pandas - blazing fast, fully offline.

Author: ToGMAL Project
"""

import json
import re
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter
import logging

# Traditional NLP
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.manifold import TSNE

# ML and explainability
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FastFeatureExtractor:
    """Extract comprehensive features WITHOUT external dependencies."""

    # Domain-specific keywords
    UNITS = ['psi', 'atm', 'pa', 'bar', '°f', '°c', '°k', 'btu', 'j', 'cal',
             'ft', 'in', 'm', 'cm', 'lb', 'kg', 'g', 'mph', 'w', 'watt', 'mol', 'v', 'volt']

    MATH_SYMBOLS = ['=', '×', '÷', '∫', '∂', '∑', '√', '^']
    FORMULA_WORDS = ['formula', 'equation', 'calculate', 'compute', 'derive', 'prove', 'find']
    REASONING_WORDS = ['if', 'then', 'therefore', 'because', 'given', 'assume', 'suppose']
    COMPARISON_WORDS = ['compare', 'difference', 'between', 'versus', 'vs', 'greater', 'less']
    CAUSATION_WORDS = ['cause', 'effect', 'result', 'lead', 'due to', 'because']

    def extract_all(self, question: str, metadata: Dict = None) -> Dict[str, float]:
        """Extract ALL features in one pass."""

        q_lower = question.lower()
        words = q_lower.split()

        # Calculate basic values first
        len_sentences = question.count('.') + question.count('?') + question.count('!')
        num_count = len(re.findall(r'\d+', question))
        unit_count = sum(1 for u in self.UNITS if u in q_lower)
        formula_words = sum(1 for w in self.FORMULA_WORDS if w in q_lower)
        comma_count = question.count(',')

        features = {
            # Basic statistics
            'len_chars': len(question),
            'len_words': len(words),
            'len_sentences': len_sentences,
            'avg_word_len': np.mean([len(w) for w in words]) if words else 0,
            'unique_ratio': len(set(words)) / len(words) if words else 0,

            # Numerical complexity
            'num_count': num_count,
            'decimal_count': len(re.findall(r'\d+\.\d+', question)),
            'scientific_notation': 1 if any(x in q_lower for x in ['e+', 'e-', '×10', 'x10']) else 0,
            'fraction_count': question.count('/') - q_lower.count('http'),  # Subtract URLs

            # Domain indicators
            'unit_count': unit_count,
            'math_symbol_count': sum(1 for s in self.MATH_SYMBOLS if s in question),

            # Keyword counts
            'formula_words': formula_words,
            'reasoning_words': sum(1 for w in self.REASONING_WORDS if w in q_lower),
            'comparison_words': sum(1 for w in self.COMPARISON_WORDS if w in q_lower),
            'causation_words': sum(1 for w in self.CAUSATION_WORDS if w in q_lower),

            # Structural complexity
            'comma_count': comma_count,
            'semicolon_count': question.count(';'),
            'colon_count': question.count(':'),
            'paren_count': question.count('('),
            'bracket_count': question.count('['),
            'quote_count': question.count('"') + question.count("'"),

            # Question structure
            'has_multiple_sentences': 1 if len_sentences > 1 else 0,
            'question_mark_count': question.count('?'),
            'exclamation_count': question.count('!'),

            # Word patterns
            'capitalized_words': sum(1 for w in question.split() if w and w[0].isupper()),
            'all_caps_words': sum(1 for w in question.split() if w.isupper() and len(w) > 1),
        }

        # Computed features
        features['complexity_score'] = (
            num_count +
            formula_words * 2 +
            unit_count * 3 +
            comma_count
        )

        return features


class FastOfflineAnalyzer:
    """Lightning-fast mass analysis with ZERO external dependencies."""

    def __init__(self, dataset_file: Path = Path("data/autonomous_benchmarks/autonomous_dataset_enriched.json")):
        """Initialize analyzer."""

        logger.info("⚡ Initializing FAST Offline Analyzer (no external models)...")

        # Load dataset
        with open(dataset_file) as f:
            self.dataset = json.load(f)

        logger.info(f"✓ Loaded {len(self.dataset['questions'])} questions")

        self.feature_extractor = FastFeatureExtractor()
        self.df = None
        self.tfidf_vectors = None
        self.feature_vectors = None

    def prepare_data(self) -> pd.DataFrame:
        """Prepare data with feature extraction."""

        logger.info("\n" + "="*70)
        logger.info("🔧 EXTRACTING FEATURES (Pure Python + sklearn)")
        logger.info("="*70)

        questions_data = []

        logger.info("\n📊 Processing questions...")
        for i, q in enumerate(self.dataset['questions']):
            if i % 2000 == 0 and i > 0:
                logger.info(f"  Processed {i}/{len(self.dataset['questions'])}...")

            # Extract features
            features = self.feature_extractor.extract_all(q['question'], q['metadata'])

            # Add core data
            data = {
                'question_id': i,
                'question': q['question'],
                'success_rate': q['success_rate'],
                'is_failure': 1 if q['success_rate'] < 0.3 else 0,
                'is_universal_failure': 1 if q['success_rate'] == 0.0 else 0,
                'category': q['metadata'].get('category', 'unknown'),
                'subject': q['metadata'].get('subject', 'unknown'),
            }

            # Merge features
            data.update(features)
            questions_data.append(data)

        self.df = pd.DataFrame(questions_data)
        logger.info(f"✓ Extracted {len(self.df.columns)} features for {len(self.df)} questions")

        # Create TF-IDF vectors
        logger.info("\n📝 Creating TF-IDF vectors...")
        tfidf = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=5
        )
        self.tfidf_vectors = tfidf.fit_transform(self.df['question'])
        logger.info(f"✓ TF-IDF shape: {self.tfidf_vectors.shape}")

        # Select numeric features
        feature_cols = [c for c in self.df.columns if isinstance(self.df[c].iloc[0], (int, float, np.number))
                       and c not in ['question_id', 'success_rate', 'is_failure', 'is_universal_failure']]
        self.feature_vectors = self.df[feature_cols].values

        logger.info(f"✓ Feature vectors shape: {self.feature_vectors.shape}")
        logger.info("="*70 + "\n")

        return self.df

    def analyze_feature_importance(self):
        """Analyze which features predict failures best."""

        logger.info("="*70)
        logger.info("🎯 FEATURE IMPORTANCE ANALYSIS")
        logger.info("="*70)

        # Get feature columns
        feature_cols = [c for c in self.df.columns if isinstance(self.df[c].iloc[0], (int, float, np.number))
                       and c not in ['question_id', 'success_rate', 'is_failure', 'is_universal_failure']]

        X = self.df[feature_cols].fillna(0)
        y = self.df['is_failure']

        logger.info(f"\n📊 Features: {len(feature_cols)}")
        logger.info(f"📊 Samples: {len(X)}")
        logger.info(f"📊 Failure rate: {y.mean()*100:.1f}%\n")

        # Train Random Forest
        logger.info("🌳 Training Random Forest...")
        rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
        rf.fit(X, y)

        # Feature importance
        importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': rf.feature_importances_
        }).sort_values('importance', ascending=False)

        logger.info("\n🔝 TOP 20 FEATURES PREDICTING FAILURES:\n")
        for i, row in importance.head(20).iterrows():
            bar = '█' * int(row['importance'] * 100)
            logger.info(f"  {row['feature']:25s} {row['importance']:.4f} {bar}")

        # Correlation analysis
        logger.info("\n\n📈 CORRELATION WITH SUCCESS RATE:\n")
        correlations = []
        for col in feature_cols:
            corr = self.df[col].corr(self.df['success_rate'])
            correlations.append({'feature': col, 'correlation': corr})

        corr_df = pd.DataFrame(correlations).sort_values('correlation')

        logger.info("Negative correlation = More likely to FAIL:\n")
        for _, row in corr_df.head(10).iterrows():
            logger.info(f"  {row['feature']:25s} {row['correlation']:+.3f} ↓ FAILURE INDICATOR")

        logger.info("\n\nPositive correlation = More likely to SUCCEED:\n")
        for _, row in corr_df.tail(10).iterrows():
            logger.info(f"  {row['feature']:25s} {row['correlation']:+.3f} ↑ SUCCESS INDICATOR")

        logger.info("="*70 + "\n")

        return importance, corr_df

    def train_failure_predictor(self):
        """Train model to predict failures."""

        logger.info("="*70)
        logger.info("🤖 TRAINING FAILURE PREDICTION MODEL")
        logger.info("="*70)

        feature_cols = [c for c in self.df.columns if isinstance(self.df[c].iloc[0], (int, float, np.number))
                       and c not in ['question_id', 'success_rate', 'is_failure', 'is_universal_failure']]

        X = self.df[feature_cols].fillna(0)
        y = self.df['is_failure']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        # Train multiple models
        models = {
            'Random Forest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
            'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42),
            'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42, n_jobs=-1)
        }

        logger.info("\n🏋️  Training 3 models...\n")

        results = {}
        for name, model in models.items():
            model.fit(X_train, y_train)
            train_score = model.score(X_train, y_train)
            test_score = model.score(X_test, y_test)

            y_pred = model.predict(X_test)

            # Try to get probabilities for ROC AUC
            try:
                y_pred_proba = model.predict_proba(X_test)[:, 1]
                auc = roc_auc_score(y_test, y_pred_proba)
            except:
                auc = None

            results[name] = {
                'model': model,
                'train_score': train_score,
                'test_score': test_score,
                'auc': auc
            }

            logger.info(f"{name}:")
            logger.info(f"  Train Accuracy: {train_score*100:.1f}%")
            logger.info(f"  Test Accuracy:  {test_score*100:.1f}%")
            if auc:
                logger.info(f"  ROC AUC:        {auc:.3f}")
            logger.info("")

        # Detailed report for best model
        best_model_name = max(results.items(), key=lambda x: x[1]['test_score'])[0]
        best_model = results[best_model_name]['model']

        logger.info(f"🏆 Best Model: {best_model_name}\n")
        logger.info("📊 Classification Report:\n")
        y_pred = best_model.predict(X_test)
        print(classification_report(y_test, y_pred, target_names=['Success', 'Failure']))

        logger.info("="*70 + "\n")

        return results

    def cluster_analysis(self, n_clusters=15):
        """Cluster questions to find failure patterns."""

        logger.info("="*70)
        logger.info(f"🗂️  CLUSTERING ANALYSIS (k={n_clusters})")
        logger.info("="*70)

        # Use TF-IDF vectors for clustering
        logger.info("\n🔄 Running K-Means on TF-IDF vectors...")

        # Reduce dimensionality first for speed
        svd = TruncatedSVD(n_components=50, random_state=42)
        vectors_reduced = svd.fit_transform(self.tfidf_vectors)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(vectors_reduced)

        self.df['cluster'] = clusters

        logger.info(f"✓ Clustered into {n_clusters} groups\n")

        # Analyze clusters
        cluster_stats = []
        for cid in range(n_clusters):
            cluster_qs = self.df[self.df['cluster'] == cid]

            stats = {
                'cluster_id': cid,
                'size': len(cluster_qs),
                'avg_success': cluster_qs['success_rate'].mean(),
                'failure_rate': cluster_qs['is_failure'].mean(),
                'universal_failures': cluster_qs['is_universal_failure'].sum(),
                'top_category': cluster_qs['category'].mode()[0] if len(cluster_qs) > 0 else 'unknown',
                'top_subject': cluster_qs['subject'].mode()[0] if len(cluster_qs) > 0 else 'unknown',
                'avg_complexity': cluster_qs['complexity_score'].mean() if 'complexity_score' in cluster_qs else 0,
                'avg_unit_count': cluster_qs['unit_count'].mean() if 'unit_count' in cluster_qs else 0,
            }
            cluster_stats.append(stats)

        cluster_df = pd.DataFrame(cluster_stats).sort_values('failure_rate', ascending=False)

        logger.info("📊 Cluster Statistics:\n")
        logger.info(f"{'Cluster':<10} {'Size':<8} {'Failures':<12} {'Subject':<30} {'Units':<8}")
        logger.info("-" * 80)

        for _, row in cluster_df.head(15).iterrows():
            logger.info(f"{row['cluster_id']:<10} {row['size']:<8} {row['failure_rate']*100:>5.1f}%       "
                       f"{row['top_subject']:<30} {row['avg_unit_count']:>5.1f}")

        logger.info("\n🔴 Highest Risk Clusters:\n")
        for _, row in cluster_df.head(5).iterrows():
            logger.info(f"  Cluster {row['cluster_id']:2d}: {row['failure_rate']*100:5.1f}% fail rate | "
                       f"{row['top_subject']:30s} | {row['size']} questions")

        logger.info("="*70 + "\n")

        return cluster_df

    def identify_failure_patterns(self):
        """Find specific patterns that lead to failures."""

        logger.info("="*70)
        logger.info("🔍 IDENTIFYING FAILURE PATTERNS")
        logger.info("="*70)

        failures = self.df[self.df['is_failure'] == 1]
        successes = self.df[self.df['is_failure'] == 0]

        logger.info(f"\n📊 Comparing {len(failures)} failures vs {len(successes)} successes\n")

        # Compare key metrics
        metrics = ['unit_count', 'num_count', 'complexity_score', 'formula_words',
                  'len_words', 'comma_count', 'reasoning_words']

        logger.info("📈 METRIC COMPARISON (Failures vs Successes):\n")
        logger.info(f"{'Metric':<25} {'Failures':<12} {'Successes':<12} {'Difference':<12}")
        logger.info("-" * 70)

        patterns = []
        for metric in metrics:
            if metric in self.df.columns:
                fail_avg = failures[metric].mean()
                success_avg = successes[metric].mean()
                diff = fail_avg - success_avg
                diff_pct = (diff / success_avg * 100) if success_avg > 0 else 0

                logger.info(f"{metric:<25} {fail_avg:>10.2f}  {success_avg:>10.2f}  "
                           f"{diff:>+10.2f} ({diff_pct:>+6.1f}%)")

                patterns.append({
                    'metric': metric,
                    'failure_avg': fail_avg,
                    'success_avg': success_avg,
                    'difference': diff,
                    'pct_difference': diff_pct
                })

        patterns_df = pd.DataFrame(patterns).sort_values('pct_difference', key=abs, ascending=False)

        logger.info("\n\n🔑 KEY FINDINGS:\n")
        for _, row in patterns_df.head(5).iterrows():
            if row['pct_difference'] > 10:
                logger.info(f"  ⚠️  Failures have {row['pct_difference']:+.0f}% more {row['metric']}")
            elif row['pct_difference'] < -10:
                logger.info(f"  ✓ Successes have {abs(row['pct_difference']):.0f}% more {row['metric']}")

        # Subject-level analysis
        logger.info("\n\n📚 SUBJECT-LEVEL FAILURE RATES:\n")
        subject_stats = self.df.groupby('subject').agg({
            'is_failure': ['mean', 'sum', 'count']
        }).round(3)
        subject_stats.columns = ['failure_rate', 'num_failures', 'total']
        subject_stats = subject_stats[subject_stats['total'] >= 20]  # Min 20 questions
        subject_stats = subject_stats.sort_values('failure_rate', ascending=False)

        logger.info(f"{'Subject':<40} {'Failure Rate':<15} {'Failures/Total':<15}")
        logger.info("-" * 75)
        for subject, row in subject_stats.head(15).iterrows():
            logger.info(f"{subject:<40} {row['failure_rate']*100:>5.1f}%          "
                       f"{int(row['num_failures']):>3d}/{int(row['total']):>4d}")

        logger.info("="*70 + "\n")

        return patterns_df, subject_stats

    def generate_full_report(self, output_dir: Path = Path("data/fast_analysis")):
        """Generate complete analysis report."""

        logger.info("\n" + "="*70)
        logger.info("📋 RUNNING COMPLETE FAST ANALYSIS")
        logger.info("="*70 + "\n")

        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Prepare data
        self.prepare_data()

        # 2. Feature importance
        importance, correlations = self.analyze_feature_importance()

        # 3. Train predictor
        predictor_results = self.train_failure_predictor()

        # 4. Clustering
        cluster_stats = self.cluster_analysis(n_clusters=15)

        # 5. Pattern identification
        patterns, subject_stats = self.identify_failure_patterns()

        # Save results
        logger.info("="*70)
        logger.info("💾 SAVING RESULTS")
        logger.info("="*70 + "\n")

        importance.to_csv(output_dir / 'feature_importance.csv', index=False)
        correlations.to_csv(output_dir / 'correlations.csv', index=False)
        cluster_stats.to_csv(output_dir / 'cluster_stats.csv', index=False)
        patterns.to_csv(output_dir / 'failure_patterns.csv', index=False)
        subject_stats.to_csv(output_dir / 'subject_failure_rates.csv')
        self.df.to_csv(output_dir / 'full_dataset_with_features.csv', index=False)

        logger.info(f"✓ All results saved to {output_dir}\n")
        logger.info("="*70)

        return {
            'importance': importance,
            'correlations': correlations,
            'cluster_stats': cluster_stats,
            'patterns': patterns,
            'subject_stats': subject_stats
        }


if __name__ == '__main__':
    analyzer = FastOfflineAnalyzer()
    results = analyzer.generate_full_report()
