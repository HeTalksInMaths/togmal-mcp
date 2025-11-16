#!/usr/bin/env python3
"""
Simple Vector Store (Offline, No HuggingFace)
==============================================

Uses TF-IDF from scikit-learn for semantic similarity.
No internet required, no downloads, works offline.

Pros:
- Works offline
- Fast
- No dependencies on external services

Cons:
- Less sophisticated than neural embeddings
- Keyword-based similarity (not semantic)
"""

import json
import pickle
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class SimpleTFIDFVectorStore:
    """Simple TF-IDF based vector store for semantic search"""

    def __init__(self, datastore_dir: Path = Path("./mcp_datastore")):
        self.datastore_dir = datastore_dir
        self.vectorizer = None
        self.vectors = None
        self.questions = None

    def build(self):
        """Build TF-IDF vectors from questions"""
        print("Building TF-IDF vector store...")

        # Load all questions
        with open(self.datastore_dir / "questions_by_id.json") as f:
            questions_dict = json.load(f)

        self.questions = list(questions_dict.values())

        # Extract question texts
        texts = [q['question_text'] for q in self.questions]

        print(f"  Processing {len(texts):,} questions...")

        # Build TF-IDF vectors
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )

        self.vectors = self.vectorizer.fit_transform(texts)

        print(f"  ✅ Built {self.vectors.shape[0]:,} vectors with {self.vectors.shape[1]:,} features")

    def save(self, output_path: Path = Path("./simple_vector_store.pkl")):
        """Save vectorizer and vectors"""
        data = {
            'vectorizer': self.vectorizer,
            'vectors': self.vectors,
            'question_ids': [q['question_id'] for q in self.questions]
        }

        with open(output_path, 'wb') as f:
            pickle.dump(data, f)

        print(f"  ✅ Saved to {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")

    def load(self, input_path: Path = Path("./simple_vector_store.pkl")):
        """Load vectorizer and vectors"""
        with open(input_path, 'rb') as f:
            data = pickle.load(f)

        self.vectorizer = data['vectorizer']
        self.vectors = data['vectors']

        # Load questions
        with open(self.datastore_dir / "questions_by_id.json") as f:
            questions_dict = json.load(f)

        self.questions = [questions_dict[qid] for qid in data['question_ids']]

        print(f"  ✅ Loaded {len(self.questions):,} questions")

    def search(self, query: str, k: int = 5):
        """Search for similar questions"""
        # Vectorize query
        query_vector = self.vectorizer.transform([query])

        # Compute similarities
        similarities = cosine_similarity(query_vector, self.vectors)[0]

        # Get top k
        top_indices = np.argsort(similarities)[-k:][::-1]

        results = []
        for idx in top_indices:
            results.append({
                'question': self.questions[idx],
                'similarity': float(similarities[idx])
            })

        return results

def main():
    """Build and test simple vector store"""
    store = SimpleTFIDFVectorStore()

    # Build
    store.build()
    store.save()

    # Test
    print("\n" + "="*80)
    print("Testing Search")
    print("="*80)

    test_queries = [
        "filter pandas DataFrame by column value",
        "calculate quantum partition function",
        "unit conversion engineering problem"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = store.search(query, k=3)

        for i, result in enumerate(results, 1):
            q = result['question']
            sim = result['similarity']
            print(f"\n  {i}. Similarity: {sim:.3f}")
            print(f"     Benchmark: {q['benchmark']}")
            print(f"     Domain: {q['domain']}")
            print(f"     Success Rate: {q['success_rate']:.1%}")
            print(f"     Question: {q['question_text'][:100]}...")

if __name__ == "__main__":
    main()
