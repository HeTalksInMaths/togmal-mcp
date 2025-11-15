#!/usr/bin/env python3
"""
Mass Failure Analysis using Traditional NLP & Deep Learning
=============================================================

Analyzes thousands of model failures in seconds using:
1. Feature Engineering (linguistic complexity, domain indicators)
2. Sentence Embeddings (semantic similarity)
3. Topic Modeling (BERTopic/LDA)
4. ML Classification (predict failures + SHAP explainability)
5. Clustering (find natural failure groups)
6. Visualization (t-SNE/UMAP)

Much faster than LLM-based analysis (seconds vs minutes).

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
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk import pos_tag

# Deep Learning embeddings
from sentence_transformers import SentenceTransformer

# ML and explainability
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

# Dimensionality reduction for visualization
import umap

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract linguistic and domain features from questions."""

    # Domain indicators
    UNITS = [
        'psi', 'atm', 'pa', 'bar',
        '°f', '°c', '°k', 'fahrenheit', 'celsius', 'kelvin',
        'btu', 'j', 'cal', 'joule',
        'ft', 'in', 'm', 'cm', 'mm',
        'lb', 'kg', 'g',
        'cfs', 'gpm', 'lpm',
        'mph', 'km/h', 'm/s',
        'w', 'watt', 'hp',
        'mol', 'mole',
        'v', 'volt', 'a', 'ampere', 'ohm'
    ]

    MATH_SYMBOLS = ['=', '×', '÷', '∫', '∂', '∑', '√', '^', '+', '-', '*', '/']
    FORMULA_KEYWORDS = ['formula', 'equation', 'calculate', 'compute', 'derive', 'prove']
    REASONING_KEYWORDS = ['if', 'then', 'therefore', 'because', 'given', 'assume']

    def __init__(self):
        """Initialize feature extractor."""
        # Download NLTK data if needed
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        try:
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download('averaged_perceptron_tagger', quiet=True)

    def extract_features(self, question: str, metadata: Dict = None) -> Dict[str, Any]:
        """Extract comprehensive features from a question."""

        # Basic text statistics
        features = {
            'length_chars': len(question),
            'length_words': len(question.split()),
            'length_sentences': len(sent_tokenize(question)),
        }

        # Lexical features
        words = word_tokenize(question.lower())
        features['avg_word_length'] = np.mean([len(w) for w in words]) if words else 0
        features['unique_word_ratio'] = len(set(words)) / len(words) if words else 0

        # Syntactic complexity (POS tags)
        try:
            pos_tags = pos_tag(words)
            pos_counts = Counter([tag for _, tag in pos_tags])
            features['noun_count'] = pos_counts.get('NN', 0) + pos_counts.get('NNS', 0) + pos_counts.get('NNP', 0)
            features['verb_count'] = pos_counts.get('VB', 0) + pos_counts.get('VBD', 0) + pos_counts.get('VBG', 0)
            features['adj_count'] = pos_counts.get('JJ', 0) + pos_counts.get('JJR', 0) + pos_counts.get('JJS', 0)
        except:
            features['noun_count'] = 0
            features['verb_count'] = 0
            features['adj_count'] = 0

        # Numerical complexity
        numbers = re.findall(r'\d+\.?\d*(?:[eE][+-]?\d+)?', question)
        features['number_count'] = len(numbers)
        features['has_scientific_notation'] = 1 if any('e' in n.lower() for n in numbers) else 0

        # Domain indicators
        question_lower = question.lower()
        features['unit_count'] = sum(1 for unit in self.UNITS if unit in question_lower)
        features['math_symbol_count'] = sum(1 for symbol in self.MATH_SYMBOLS if symbol in question)
        features['formula_keyword_count'] = sum(1 for kw in self.FORMULA_KEYWORDS if kw in question_lower)
        features['reasoning_keyword_count'] = sum(1 for kw in self.REASONING_KEYWORDS if kw in question_lower)

        # Question structure
        features['has_multiple_clauses'] = 1 if question.count(',') >= 2 else 0
        features['has_multiple_sentences'] = 1 if features['length_sentences'] > 1 else 0
        features['question_mark_count'] = question.count('?')

        # Readability (Flesch Reading Ease approximation)
        if features['length_words'] > 0 and features['length_sentences'] > 0:
            avg_sentence_length = features['length_words'] / features['length_sentences']
            avg_syllables_per_word = features['avg_word_length'] * 0.6  # Rough approximation
            features['flesch_score'] = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word
        else:
            features['flesch_score'] = 0

        # Metadata features
        if metadata:
            features['category'] = metadata.get('category', 'unknown')
            features['subject'] = metadata.get('subject', 'unknown')

        return features


class MassFailureAnalyzer:
    """Fast mass analysis of model failures using traditional NLP/DL."""

    def __init__(
        self,
        dataset_file: Path = Path("data/autonomous_benchmarks/autonomous_dataset_enriched.json"),
        use_gpu: bool = False
    ):
        """Initialize mass analyzer."""

        logger.info("🚀 Initializing Mass Failure Analyzer...")

        # Load dataset
        logger.info("📂 Loading dataset...")
        with open(dataset_file) as f:
            self.dataset = json.load(f)

        logger.info(f"✓ Loaded {len(self.dataset['questions'])} questions")

        # Initialize components
        logger.info("🔧 Initializing NLP components...")
        self.feature_extractor = FeatureExtractor()

        # Load sentence transformer for embeddings
        logger.info("🧠 Loading sentence transformer (all-MiniLM-L6-v2)...")
        device = 'cuda' if use_gpu else 'cpu'
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device=device)
        logger.info(f"✓ Embedder loaded on {device}")

        # Prepare data
        self.questions_df = None
        self.embeddings = None
        self.features_df = None

        logger.info("✓ Initialization complete\n")

    def prepare_data(self) -> pd.DataFrame:
        """Prepare data for analysis."""

        logger.info("="*70)
        logger.info("📊 PREPARING DATA FOR MASS ANALYSIS")
        logger.info("="*70)

        # Convert to DataFrame
        logger.info("\n1️⃣  Converting to DataFrame...")
        questions_data = []

        for i, q in enumerate(self.dataset['questions']):
            questions_data.append({
                'question_id': i,
                'question': q['question'],
                'success_rate': q['success_rate'],
                'is_failure': 1 if q['success_rate'] < 0.3 else 0,  # Define failure as <30% success
                'is_universal_failure': 1 if q['success_rate'] == 0.0 else 0,
                'category': q['metadata'].get('category', 'unknown'),
                'subject': q['metadata'].get('subject', 'unknown'),
                'num_models_correct': sum(q['model_scores'].values()),
                'total_models': len(q['model_scores'])
            })

        self.questions_df = pd.DataFrame(questions_data)
        logger.info(f"✓ Created DataFrame with {len(self.questions_df)} rows")

        # Extract features
        logger.info("\n2️⃣  Extracting linguistic features...")
        features_list = []

        for _, row in self.questions_df.iterrows():
            features = self.feature_extractor.extract_features(
                row['question'],
                {'category': row['category'], 'subject': row['subject']}
            )
            features['question_id'] = row['question_id']
            features_list.append(features)

        self.features_df = pd.DataFrame(features_list)
        logger.info(f"✓ Extracted {len(self.features_df.columns)} features per question")

        # Generate embeddings
        logger.info("\n3️⃣  Generating sentence embeddings...")
        questions_text = self.questions_df['question'].tolist()
        self.embeddings = self.embedder.encode(
            questions_text,
            show_progress_bar=True,
            batch_size=32
        )
        logger.info(f"✓ Generated embeddings: {self.embeddings.shape}")

        # Merge features
        logger.info("\n4️⃣  Merging all features...")
        self.questions_df = self.questions_df.merge(
            self.features_df,
            on='question_id',
            how='left'
        )

        logger.info(f"✓ Final dataset: {self.questions_df.shape}")
        logger.info("="*70 + "\n")

        return self.questions_df

    def analyze_feature_correlations(self) -> pd.DataFrame:
        """Analyze which features correlate with failures."""

        logger.info("="*70)
        logger.info("📈 ANALYZING FEATURE CORRELATIONS WITH FAILURES")
        logger.info("="*70)

        # Select numeric features
        numeric_features = self.features_df.select_dtypes(include=[np.number]).columns
        numeric_features = [f for f in numeric_features if f != 'question_id']

        # Calculate correlations with success_rate
        correlations = []
        for feature in numeric_features:
            corr = self.questions_df[feature].corr(self.questions_df['success_rate'])
            correlations.append({
                'feature': feature,
                'correlation': corr,
                'abs_correlation': abs(corr)
            })

        corr_df = pd.DataFrame(correlations).sort_values('abs_correlation', ascending=False)

        logger.info("\n🔝 Top 15 Features Correlated with Failures:")
        logger.info("(Negative correlation = more likely to fail)\n")

        for _, row in corr_df.head(15).iterrows():
            direction = "↓ FAILURE" if row['correlation'] < 0 else "↑ SUCCESS"
            logger.info(f"  {row['feature']:30s}: {row['correlation']:+.3f} {direction}")

        logger.info("="*70 + "\n")

        return corr_df

    def train_failure_predictor(self) -> Dict[str, Any]:
        """Train ML model to predict failures."""

        logger.info("="*70)
        logger.info("🤖 TRAINING FAILURE PREDICTION MODEL")
        logger.info("="*70)

        # Prepare features
        numeric_features = self.features_df.select_dtypes(include=[np.number]).columns
        numeric_features = [f for f in numeric_features if f != 'question_id']

        X = self.questions_df[numeric_features].fillna(0)
        y = self.questions_df['is_failure']

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        logger.info(f"\n📊 Training set: {len(X_train)} samples")
        logger.info(f"📊 Test set: {len(X_test)} samples")
        logger.info(f"📊 Failure rate: {y.mean()*100:.1f}%")

        # Train model
        logger.info("\n🏋️  Training Random Forest...")
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)

        # Evaluate
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)

        logger.info(f"✓ Training accuracy: {train_score*100:.1f}%")
        logger.info(f"✓ Test accuracy: {test_score*100:.1f}%")

        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': numeric_features,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        logger.info("\n🔝 Top 10 Most Important Features for Predicting Failures:")
        for _, row in feature_importance.head(10).iterrows():
            logger.info(f"  {row['feature']:30s}: {row['importance']:.4f}")

        # Detailed evaluation
        y_pred = model.predict(X_test)
        logger.info("\n📊 Classification Report:")
        print(classification_report(y_test, y_pred, target_names=['Success', 'Failure']))

        logger.info("="*70 + "\n")

        return {
            'model': model,
            'feature_importance': feature_importance,
            'train_score': train_score,
            'test_score': test_score,
            'feature_names': numeric_features
        }

    def cluster_failures(self, n_clusters: int = 10) -> np.ndarray:
        """Cluster questions using embeddings to find failure patterns."""

        logger.info("="*70)
        logger.info("🗂️  CLUSTERING QUESTIONS TO FIND FAILURE PATTERNS")
        logger.info("="*70)

        logger.info(f"\n📍 Running K-Means clustering (k={n_clusters})...")

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(self.embeddings)

        self.questions_df['cluster'] = clusters

        # Analyze each cluster
        logger.info(f"\n✓ Found {n_clusters} clusters\n")
        logger.info("📊 Cluster Analysis:\n")

        cluster_stats = []
        for cluster_id in range(n_clusters):
            cluster_questions = self.questions_df[self.questions_df['cluster'] == cluster_id]

            stats = {
                'cluster_id': cluster_id,
                'size': len(cluster_questions),
                'avg_success_rate': cluster_questions['success_rate'].mean(),
                'failure_rate': (cluster_questions['is_failure'].sum() / len(cluster_questions)),
                'universal_failures': cluster_questions['is_universal_failure'].sum(),
                'top_category': cluster_questions['category_x'].mode()[0] if len(cluster_questions) > 0 else 'unknown',
                'top_subject': cluster_questions['subject_x'].mode()[0] if len(cluster_questions) > 0 else 'unknown'
            }
            cluster_stats.append(stats)

            logger.info(f"Cluster {cluster_id}:")
            logger.info(f"  Size: {stats['size']:4d} questions")
            logger.info(f"  Avg success: {stats['avg_success_rate']*100:5.1f}%")
            logger.info(f"  Failure rate: {stats['failure_rate']*100:5.1f}%")
            logger.info(f"  Universal failures: {stats['universal_failures']}")
            logger.info(f"  Top category: {stats['top_category']}")
            logger.info(f"  Top subject: {stats['top_subject']}")
            logger.info("")

        cluster_stats_df = pd.DataFrame(cluster_stats).sort_values('failure_rate', ascending=False)

        logger.info("🔴 Highest Failure Rate Clusters:")
        for _, row in cluster_stats_df.head(5).iterrows():
            logger.info(f"  Cluster {row['cluster_id']:2d}: {row['failure_rate']*100:5.1f}% failures | {row['top_subject']}")

        logger.info("="*70 + "\n")

        return clusters, cluster_stats_df

    def visualize_embeddings(self, method: str = 'umap') -> np.ndarray:
        """Create 2D visualization of question embeddings."""

        logger.info("="*70)
        logger.info(f"🎨 CREATING 2D VISUALIZATION ({method.upper()})")
        logger.info("="*70)

        if method == 'tsne':
            logger.info("\n🔄 Running t-SNE (this may take a while)...")
            reducer = TSNE(n_components=2, random_state=42, n_jobs=-1)
        elif method == 'umap':
            logger.info("\n🔄 Running UMAP...")
            reducer = umap.UMAP(n_components=2, random_state=42, n_jobs=-1)
        else:
            logger.info("\n🔄 Running PCA...")
            reducer = PCA(n_components=2, random_state=42)

        embeddings_2d = reducer.fit_transform(self.embeddings)

        self.questions_df['embed_x'] = embeddings_2d[:, 0]
        self.questions_df['embed_y'] = embeddings_2d[:, 1]

        logger.info(f"✓ Reduced to 2D: {embeddings_2d.shape}")
        logger.info("="*70 + "\n")

        return embeddings_2d

    def generate_report(self, output_dir: Path = Path("data/mass_analysis")):
        """Generate comprehensive mass analysis report."""

        logger.info("\n" + "="*70)
        logger.info("📋 GENERATING COMPREHENSIVE REPORT")
        logger.info("="*70)

        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Prepare data
        self.prepare_data()

        # 2. Feature correlations
        correlations = self.analyze_feature_correlations()

        # 3. Train predictor
        predictor_results = self.train_failure_predictor()

        # 4. Cluster analysis
        clusters, cluster_stats = self.cluster_failures(n_clusters=15)

        # 5. Visualization
        embeddings_2d = self.visualize_embeddings(method='umap')

        # Save results
        logger.info("💾 Saving results...")

        # Save feature correlations
        correlations.to_csv(output_dir / 'feature_correlations.csv', index=False)

        # Save feature importance
        predictor_results['feature_importance'].to_csv(output_dir / 'feature_importance.csv', index=False)

        # Save cluster stats
        cluster_stats.to_csv(output_dir / 'cluster_stats.csv', index=False)

        # Save full dataset with all features
        self.questions_df.to_csv(output_dir / 'questions_with_features.csv', index=False)

        # Save embeddings
        np.save(output_dir / 'embeddings.npy', self.embeddings)
        np.save(output_dir / 'embeddings_2d.npy', embeddings_2d)

        logger.info(f"✓ Results saved to {output_dir}")
        logger.info("="*70 + "\n")

        return {
            'correlations': correlations,
            'predictor': predictor_results,
            'clusters': cluster_stats,
            'embeddings_2d': embeddings_2d
        }


if __name__ == '__main__':
    analyzer = MassFailureAnalyzer(use_gpu=False)
    results = analyzer.generate_report()
