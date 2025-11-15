#!/usr/bin/env python3
"""
Subject Enrichment Script
==========================

Enriches the existing dataset with fine-grained subject information
by extracting the 'src' field from MMLU-Pro prediction files.

Discovered: 90 subjects across 14 categories (vs just 14 categories before)

Author: ToGMAL Project
"""

import json
import logging
import requests
import zipfile
import io
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SubjectEnricher:
    """Enriches dataset with subject-level metadata."""

    def __init__(self):
        """Initialize enricher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ToGMAL-Subject-Enricher/1.0'
        })

    def extract_subject_from_src(self, src: str) -> str:
        """Extract subject from src field."""
        if not src:
            return ""

        # Format: ori_mmlu-SUBJECT or scibench-SUBJECT or theoremqa-SUBJECT
        if '-' in src:
            subject = src.split('-', 1)[1]
        else:
            subject = src

        return subject

    def fetch_subject_mapping(self, model_name: str = "Meta-Llama-3_1-8B-Instruct_5shots") -> Dict[str, str]:
        """
        Fetch a model's predictions to build question_id → subject mapping.

        Returns:
            Dict mapping question text → subject
        """
        logger.info(f"📥 Fetching subject mapping from {model_name}...")

        # Construct download URL
        zip_url = f"https://raw.githubusercontent.com/TIGER-AI-Lab/MMLU-Pro/main/eval_results/model_outputs_{model_name}.zip"

        try:
            response = self.session.get(zip_url, timeout=60)
            response.raise_for_status()

            # Extract ZIP
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                # Find JSON file
                json_files = [f for f in zf.namelist() if f.endswith('.json')]
                if not json_files:
                    logger.error("No JSON file found in ZIP")
                    return {}

                # Read predictions
                with zf.open(json_files[0]) as f:
                    predictions = json.load(f)

                logger.info(f"✓ Loaded {len(predictions)} predictions")

                # Build mapping: question → subject
                mapping = {}
                for pred in predictions:
                    question = pred.get('question', '')
                    src = pred.get('src', '')
                    subject = self.extract_subject_from_src(src)
                    category = pred.get('category', '')

                    if question:
                        # Use first 200 chars as key (questions may be truncated)
                        q_key = question[:200]
                        mapping[q_key] = {
                            'subject': subject,
                            'category': category,
                            'src': src
                        }

                logger.info(f"✓ Built mapping for {len(mapping)} unique questions")
                return mapping

        except Exception as e:
            logger.error(f"Error fetching subject mapping: {e}")
            return {}

    def enrich_dataset(
        self,
        dataset_file: Path = Path("data/autonomous_benchmarks/autonomous_dataset.json"),
        output_file: Path = Path("data/autonomous_benchmarks/autonomous_dataset_enriched.json")
    ):
        """Enrich dataset with subject information."""

        logger.info("\n" + "="*70)
        logger.info("🔬 ENRICHING DATASET WITH SUBJECT METADATA")
        logger.info("="*70)

        # Load existing dataset
        logger.info(f"\n📂 Loading dataset from {dataset_file}...")
        with open(dataset_file) as f:
            dataset = json.load(f)

        logger.info(f"✓ Loaded {len(dataset['questions'])} questions")

        # Fetch subject mapping
        mapping = self.fetch_subject_mapping()

        if not mapping:
            logger.error("Failed to fetch subject mapping. Aborting.")
            return

        # Enrich each question
        logger.info("\n🏗️  Enriching questions with subject metadata...")

        enriched = 0
        not_found = 0
        subject_counts = defaultdict(int)
        category_subject_counts = defaultdict(lambda: defaultdict(int))

        for question in dataset['questions']:
            q_text = question['question'][:200]

            # Try to find mapping
            if q_text in mapping:
                # Update metadata
                question['metadata']['subject'] = mapping[q_text]['subject']
                question['metadata']['src'] = mapping[q_text]['src']

                # Update category if it was missing/empty
                if not question['metadata'].get('category'):
                    question['metadata']['category'] = mapping[q_text]['category']

                # Track counts
                subject = mapping[q_text]['subject']
                category = mapping[q_text]['category']
                subject_counts[subject] += 1
                category_subject_counts[category][subject] += 1
                enriched += 1
            else:
                not_found += 1

        logger.info(f"✓ Enriched {enriched:,} questions ({enriched/len(dataset['questions'])*100:.1f}%)")
        logger.info(f"  Not found: {not_found:,} questions")

        # Add enrichment metadata
        dataset['metadata']['enrichment'] = {
            'enriched_count': enriched,
            'total_subjects': len(subject_counts),
            'enrichment_date': '2025-11-15',
            'source': 'MMLU-Pro src field extraction'
        }

        # Save enriched dataset
        logger.info(f"\n💾 Saving enriched dataset to {output_file}...")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(dataset, f, indent=2)

        logger.info(f"✓ Saved {output_file.stat().st_size / 1024 / 1024:.1f} MB")

        # Print summary
        logger.info("\n" + "="*70)
        logger.info("📊 ENRICHMENT SUMMARY")
        logger.info("="*70)

        logger.info(f"\n✅ Total subjects discovered: {len(subject_counts)}")
        logger.info(f"✅ Questions enriched: {enriched:,} / {len(dataset['questions']):,}")

        logger.info("\n📚 Subjects by Category:")
        for category in sorted(category_subject_counts.keys()):
            subjects = category_subject_counts[category]
            logger.info(f"\n  {category.upper()} ({len(subjects)} subjects, {sum(subjects.values())} questions):")
            for subject, count in sorted(subjects.items(), key=lambda x: x[1], reverse=True)[:5]:
                logger.info(f"    • {subject:40s}: {count:4d} questions")
            if len(subjects) > 5:
                remaining = len(subjects) - 5
                remaining_count = sum(count for subj, count in sorted(subjects.items(), key=lambda x: x[1], reverse=True)[5:])
                logger.info(f"    • ... {remaining} more subjects: {remaining_count} questions")

        logger.info("\n" + "="*70)

        return dataset


if __name__ == '__main__':
    enricher = SubjectEnricher()
    enricher.enrich_dataset()
