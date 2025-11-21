#!/usr/bin/env python3
"""Run validation using sklearn TF-IDF embeddings instead of sentence-transformers"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from pathlib import Path
import json

# Import our modules
from error_taxonomy import ErrorAnalyzer
from validation_metrics import TaxonomyValidator

# Load the real data
data_file = Path("data/mmlu_pro_full/mmlu_pro_real_results.json")
print(f"Loading data from {data_file}...")

with open(data_file) as f:
    data = json.load(f)

# Classify errors
print("\nClassifying errors...")
analyzer = ErrorAnalyzer()
analyzer.load_benchmark_results(str(data_file))

print(f"✅ Loaded {len(analyzer.errors)} errors")

# Generate TF-IDF embeddings for questions
print("\nGenerating TF-IDF embeddings...")
texts = [e.question_text for e in analyzer.errors]
vectorizer = TfidfVectorizer(max_features=384, stop_words='english')
embeddings = vectorizer.fit_transform(texts).toarray()

# Add embeddings to errors
for i, error in enumerate(analyzer.errors):
    error.question_embedding = embeddings[i]

print(f"✅ Generated embeddings with shape {embeddings.shape}")

# Run validation
print("\nRunning validation metrics...")
validator = TaxonomyValidator()
report = validator.run_all_validations(analyzer)

# Print results
print("\n" + "="*80)
print("VALIDATION RESULTS")
print("="*80)
print(report.to_markdown())

# Save report
output_file = Path("data/error_analysis_results/sklearn_validation.md")
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, 'w') as f:
    f.write(report.to_markdown())

print(f"\n✅ Report saved to {output_file}")
