#!/usr/bin/env python3
"""
Semantic Difficulty Checker (Tier 2)
=====================================

Offline TF-IDF semantic similarity over the unified benchmark database.
Predicts prompt difficulty from the measured success rates of the k most
similar benchmark questions.

Why TF-IDF: HuggingFace model downloads are blocked in this environment
(403), so neural sentence embeddings are unavailable. TF-IDF with word +
character n-grams is fully offline and reproducible from the committed
database snapshot.

Usage:
    # Build (writes semantic_index.pkl, ~30s)
    python3 semantic_difficulty_checker.py build

    # Query
    python3 semantic_difficulty_checker.py query "Prove that every finite group..."

    # Evaluate held-out difficulty prediction (excludes near-duplicate leakage)
    python3 semantic_difficulty_checker.py evaluate

As a library:
    from semantic_difficulty_checker import SemanticDifficultyChecker
    checker = SemanticDifficultyChecker.load()
    result = checker.assess("Calculate the partition function ...")
    # result['predicted_success_rate'], result['risk_level'], result['similar_questions']
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import FeatureUnion

DB_PATH = Path("./data/unified_database_complete.json")
INDEX_PATH = Path("./data/semantic_index.pkl")

# Neighbors at or above this cosine similarity to the query are treated as
# duplicates of it during evaluation (MMLU-Pro contains repeated questions
# across source datasets; counting them as neighbors leaks ground truth)
DUP_SIMILARITY = 0.95

# Below this mean top-k similarity the prediction is low-confidence:
# the database has no lexically comparable questions
MIN_CONFIDENT_SIMILARITY = 0.18


class SemanticDifficultyChecker:
    """TF-IDF kNN difficulty assessment over benchmark questions."""

    def __init__(self):
        self.vectorizer = None
        self.vectors = None
        self.meta = None  # list of dicts: question_id, success_rate, domain, benchmark, text

    # ------------------------------------------------------------------ build

    def build(self, db_path: Path = DB_PATH):
        with open(db_path) as f:
            questions = json.load(f)['questions']

        texts = [q['question_text'] for q in questions]
        self.meta = [
            {
                'question_id': q['question_id'],
                'success_rate': q['success_rate'],
                'domain': q['domain'],
                'benchmark': q['benchmark'],
                'difficulty_label': q.get('difficulty_label', ''),
                'has_error_patterns': bool(q.get('error_patterns')),
                'text': q['question_text'][:200],
            }
            for q in questions
        ]

        # Word n-grams capture topic; char n-grams add robustness to
        # notation-heavy text (units, LaTeX fragments, variable names)
        self.vectorizer = FeatureUnion([
            ('word', TfidfVectorizer(
                max_features=20000, stop_words='english',
                ngram_range=(1, 2), sublinear_tf=True)),
            ('char', TfidfVectorizer(
                max_features=20000, analyzer='char_wb',
                ngram_range=(3, 4), sublinear_tf=True)),
        ])

        print(f"Vectorizing {len(texts):,} questions...")
        self.vectors = self.vectorizer.fit_transform(texts)
        # L2-normalize so cosine similarity is a plain dot product
        from sklearn.preprocessing import normalize
        self.vectors = normalize(self.vectors)
        print(f"✅ Index: {self.vectors.shape[0]:,} x {self.vectors.shape[1]:,}")

    def save(self, path: Path = INDEX_PATH):
        with open(path, 'wb') as f:
            pickle.dump({
                'vectorizer': self.vectorizer,
                'vectors': self.vectors,
                'meta': self.meta,
            }, f)
        print(f"✅ Saved {path} ({path.stat().st_size / 1024 / 1024:.1f} MB)")

    @classmethod
    def load(cls, path: Path = INDEX_PATH):
        checker = cls()
        with open(path, 'rb') as f:
            data = pickle.load(f)
        checker.vectorizer = data['vectorizer']
        checker.vectors = data['vectors']
        checker.meta = data['meta']
        return checker

    # ------------------------------------------------------------------ query

    def _similarities(self, text: str) -> np.ndarray:
        from sklearn.preprocessing import normalize
        qv = normalize(self.vectorizer.transform([text]))
        return (self.vectors @ qv.T).toarray().ravel()

    def assess(self, prompt: str, k: int = 10, exclude_dups_of_query: bool = False) -> dict:
        """Predict difficulty of a prompt from its k nearest benchmark questions.

        Returns predicted success rate (similarity-weighted), a risk level,
        a confidence flag, and the supporting neighbors.
        """
        sims = self._similarities(prompt)

        order = np.argsort(sims)[::-1]
        if exclude_dups_of_query:
            order = [i for i in order if sims[i] < DUP_SIMILARITY]
        top = list(order[:k])

        top_sims = np.array([sims[i] for i in top])
        top_rates = np.array([self.meta[i]['success_rate'] for i in top])

        mean_sim = float(top_sims.mean()) if len(top) else 0.0
        confident = mean_sim >= MIN_CONFIDENT_SIMILARITY

        if top_sims.sum() > 0:
            predicted = float(np.average(top_rates, weights=top_sims))
        else:
            predicted = float(top_rates.mean()) if len(top) else 0.5

        if not confident:
            risk = 'UNKNOWN'
        elif predicted < 0.2:
            risk = 'CRITICAL'
        elif predicted < 0.4:
            risk = 'HIGH'
        elif predicted < 0.6:
            risk = 'MEDIUM'
        else:
            risk = 'LOW'

        return {
            'predicted_success_rate': round(predicted, 3),
            'risk_level': risk,
            'confident': confident,
            'mean_similarity': round(mean_sim, 3),
            'similar_questions': [
                {
                    'question_id': self.meta[i]['question_id'],
                    'similarity': round(float(sims[i]), 3),
                    'success_rate': self.meta[i]['success_rate'],
                    'domain': self.meta[i]['domain'],
                    'benchmark': self.meta[i]['benchmark'],
                    'text': self.meta[i]['text'],
                }
                for i in top
            ],
        }

    # --------------------------------------------------------------- evaluate

    def evaluate(self, sample_size: int = 2000, k: int = 10, seed: int = 42) -> dict:
        """Held-out difficulty prediction: for sampled questions, predict
        success rate from neighbors, excluding the question itself and any
        near-duplicates (similarity >= DUP_SIMILARITY) to avoid leakage.
        """
        import random
        rng = random.Random(seed)
        idxs = rng.sample(range(len(self.meta)), min(sample_size, len(self.meta)))

        abs_errors, preds, actuals, confidents = [], [], [], []

        for n, i in enumerate(idxs):
            if (n + 1) % 500 == 0:
                print(f"  {n + 1}/{len(idxs)}...")
            r = self.assess(self.meta[i]['text'], k=k, exclude_dups_of_query=True)
            preds.append(r['predicted_success_rate'])
            actuals.append(self.meta[i]['success_rate'])
            confidents.append(r['confident'])
            abs_errors.append(abs(r['predicted_success_rate'] - self.meta[i]['success_rate']))

        preds = np.array(preds)
        actuals = np.array(actuals)
        confidents = np.array(confidents)
        abs_errors = np.array(abs_errors)

        def binary_metrics(mask):
            """Risky = actual success < 0.6; predicted risky = predicted < 0.6"""
            p, a = preds[mask], actuals[mask]
            pred_risky, act_risky = p < 0.6, a < 0.6
            tp = int((pred_risky & act_risky).sum())
            fp = int((pred_risky & ~act_risky).sum())
            fn = int((~pred_risky & act_risky).sum())
            tn = int((~pred_risky & ~act_risky).sum())
            prec = tp / (tp + fp) if tp + fp else 0.0
            rec = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
            fpr = fp / (fp + tn) if fp + tn else 0.0
            return {'precision': prec, 'recall': rec, 'f1': f1, 'fpr': fpr,
                    'n': int(mask.sum())}

        corr = float(np.corrcoef(preds, actuals)[0, 1])
        results = {
            'sample_size': len(idxs),
            'k': k,
            'mae': float(abs_errors.mean()),
            'correlation': corr,
            'pct_confident': float(confidents.mean()),
            'all': binary_metrics(np.ones(len(preds), bool)),
            'confident_only': binary_metrics(confidents),
        }

        print(f"\n📊 Semantic difficulty prediction (held-out, near-dupes excluded):")
        print(f"   MAE of success-rate prediction: {results['mae']:.3f}")
        print(f"   Correlation (predicted vs actual): {corr:.3f}")
        print(f"   Confident predictions: {results['pct_confident']:.1%}")
        for name in ('all', 'confident_only'):
            m = results[name]
            print(f"   [{name}] risky-classification: "
                  f"P={m['precision']:.1%} R={m['recall']:.1%} "
                  f"F1={m['f1']:.1%} FPR={m['fpr']:.1%} (n={m['n']})")
        return results


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'build'

    if cmd == 'build':
        checker = SemanticDifficultyChecker()
        checker.build()
        checker.save()
    elif cmd == 'query':
        checker = SemanticDifficultyChecker.load()
        result = checker.assess(' '.join(sys.argv[2:]) or 'example prompt')
        print(json.dumps(result, indent=2))
    elif cmd == 'evaluate':
        checker = SemanticDifficultyChecker.load()
        results = checker.evaluate()
        out = Path('./data/semantic_evaluation_results.json')
        with open(out, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Saved {out}")
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
