#!/usr/bin/env python3
"""
Build Complete Vector Database for ToGMAL MCP
==============================================

Builds ChromaDB vector database from unified database with:
- 13,000 questions (12K MMLU-Pro + 1K DS-1000)
- 32 error patterns integrated
- Embeddings for semantic similarity search
- Rich metadata for filtering and analysis

Architecture:
- MCP uses this DB for DATA FETCHING only
- Skills contain the ANALYSIS PROCEDURES
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorDatabaseBuilder:
    """Builds ChromaDB vector database from unified questions"""

    def __init__(
        self,
        data_dir: Path = Path("./data"),
        chroma_dir: Path = Path("./chroma_db"),
        collection_name: str = "togmal_benchmarks"
    ):
        self.data_dir = data_dir
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name

        # Use sentence-transformers (already installed, no network needed)
        logger.info("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Model loaded successfully")

        # Initialize ChromaDB client
        self.chroma_dir.mkdir(exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(anonymized_telemetry=False)
        )

    def load_unified_database(self) -> List[Dict[str, Any]]:
        """Load unified database from JSON"""
        db_path = self.data_dir / "unified_database_complete.json"

        logger.info(f"Loading unified database from {db_path}...")
        with open(db_path, 'r') as f:
            data = json.load(f)

        questions = data['questions']
        logger.info(f"✅ Loaded {len(questions):,} questions")

        return questions

    def prepare_documents_and_metadata(
        self,
        questions: List[Dict[str, Any]]
    ) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        Prepare documents, metadata, and IDs for ChromaDB.

        Returns:
            (documents, metadatas, ids)
        """
        logger.info("Preparing documents and metadata...")

        documents = []
        metadatas = []
        ids = []

        for q in questions:
            # Document text for embedding (question text)
            doc = q['question_text']
            documents.append(doc)

            # Metadata for filtering and retrieval
            # ChromaDB requires metadata values to be: str, int, float, or bool
            metadata = {
                # Core fields
                'question_id': q['question_id'],
                'benchmark': q['benchmark'],
                'domain': q['domain'],
                'success_rate': float(q['success_rate']),
                'difficulty_score': float(q['difficulty_score']),
                'difficulty_label': q['difficulty_label'],
                'num_models_tested': int(q['num_models_tested']),

                # Error analysis flags
                'has_error_analysis': len(q['error_patterns']) > 0,
                'num_error_patterns': len(q['error_patterns']),
                'is_universal_failure': q.get('is_universal_failure', False),

                # Optional fields (use empty string for None)
                'category': q.get('category') or '',
                'subject': q.get('subject') or '',
                'cot_failure_mode': q.get('cot_failure_mode') or '',

                # Error pattern summary (comma-separated pattern names)
                'error_pattern_names': ','.join([
                    p['pattern'] for p in q['error_patterns']
                ]) if q['error_patterns'] else '',

                # Error pattern sources (comma-separated)
                'error_pattern_sources': ','.join(set([
                    p['source'] for p in q['error_patterns']
                ])) if q['error_patterns'] else '',

                # Conceptual gaps (comma-separated)
                'conceptual_gaps': ','.join(q.get('conceptual_gaps', [])),

                # Error categories (comma-separated)
                'error_categories': ','.join(q.get('error_categories', [])),
            }

            # Store model scores as JSON string (since ChromaDB doesn't support nested objects)
            # We'll parse this when needed
            metadata['model_scores_json'] = json.dumps(q['model_scores'])

            metadatas.append(metadata)
            ids.append(q['question_id'])

        logger.info(f"✅ Prepared {len(documents):,} documents")
        return documents, metadatas, ids

    def build_database(self, batch_size: int = 100):
        """Build the complete vector database"""
        logger.info("="*80)
        logger.info("Building Complete Vector Database")
        logger.info("="*80)

        # Load questions
        questions = self.load_unified_database()

        # Prepare for ChromaDB
        documents, metadatas, ids = self.prepare_documents_and_metadata(questions)

        # Delete existing collection if it exists
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted existing collection: {self.collection_name}")
        except:
            pass

        # Create collection (no embedding function - we'll provide embeddings)
        logger.info(f"Creating collection: {self.collection_name}")
        collection = self.client.create_collection(
            name=self.collection_name,
            metadata={
                "description": "ToGMAL unified benchmark questions with error patterns",
                "total_questions": len(questions),
                "benchmarks": "MMLU-Pro, DS-1000",
                "error_patterns": "32 patterns from 4 sources",
                "embedding_model": "all-MiniLM-L6-v2"
            }
        )

        # Add documents to collection in batches
        # Generate embeddings using sentence-transformers
        logger.info(f"Adding documents to collection (batch_size={batch_size})...")
        logger.info(f"Generating embeddings with sentence-transformers...")

        total_batches = (len(documents) + batch_size - 1) // batch_size

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]

            # Generate embeddings for this batch
            batch_embeddings = self.model.encode(batch_docs, show_progress_bar=False).tolist()

            # Add to collection with pre-computed embeddings
            collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids,
                embeddings=batch_embeddings
            )

            batch_num = (i // batch_size) + 1
            logger.info(f"  Batch {batch_num}/{total_batches} added ({len(batch_docs)} questions)")

        logger.info(f"✅ Added {len(documents):,} questions to vector database")

        # Verify
        count = collection.count()
        logger.info(f"✅ Collection contains {count:,} documents")

        return collection

    def print_statistics(self):
        """Print database statistics"""
        collection = self.client.get_collection(self.collection_name)

        logger.info("\n" + "="*80)
        logger.info("Vector Database Statistics")
        logger.info("="*80)

        # Get all metadata to compute statistics
        results = collection.get(include=['metadatas'])
        metadatas = results['metadatas']

        total = len(metadatas)
        logger.info(f"\nTotal Questions: {total:,}")

        # By benchmark
        by_benchmark = {}
        for m in metadatas:
            bench = m['benchmark']
            by_benchmark[bench] = by_benchmark.get(bench, 0) + 1

        logger.info("\nBy Benchmark:")
        for bench, count in sorted(by_benchmark.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {bench}: {count:,} ({count/total*100:.1f}%)")

        # Error analysis coverage
        with_errors = sum(1 for m in metadatas if m['has_error_analysis'])
        universal_failures = sum(1 for m in metadatas if m['is_universal_failure'])

        logger.info(f"\nError Analysis Coverage:")
        logger.info(f"  With error patterns: {with_errors:,} ({with_errors/total*100:.1f}%)")
        logger.info(f"  Universal failures: {universal_failures:,}")

        # Difficulty distribution
        by_difficulty = {}
        for m in metadatas:
            diff = m['difficulty_label']
            by_difficulty[diff] = by_difficulty.get(diff, 0) + 1

        logger.info("\nDifficulty Distribution:")
        for diff in ['Nearly_Impossible', 'Expert', 'Hard', 'Medium', 'Easy']:
            count = by_difficulty.get(diff, 0)
            if count > 0:
                logger.info(f"  {diff}: {count:,} ({count/total*100:.1f}%)")

        # Success rate statistics
        success_rates = [m['success_rate'] for m in metadatas]
        avg_success = sum(success_rates) / len(success_rates)

        logger.info(f"\nSuccess Rate Statistics:")
        logger.info(f"  Average: {avg_success:.1%}")
        logger.info(f"  Min: {min(success_rates):.1%}")
        logger.info(f"  Max: {max(success_rates):.1%}")

        # Domain distribution
        by_domain = {}
        for m in metadatas:
            domain = m['domain']
            by_domain[domain] = by_domain.get(domain, 0) + 1

        logger.info(f"\nTop 10 Domains:")
        for domain, count in sorted(by_domain.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {domain}: {count:,}")

    def test_queries(self):
        """Test some sample queries"""
        logger.info("\n" + "="*80)
        logger.info("Testing Sample Queries")
        logger.info("="*80)

        collection = self.client.get_collection(self.collection_name)

        # Test 1: Semantic similarity search
        logger.info("\n1. Semantic Similarity: 'Calculate partition function for quantum system'")
        results = collection.query(
            query_texts=["Calculate partition function for quantum system"],
            n_results=3,
            include=['documents', 'metadatas', 'distances']
        )

        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ), 1):
            logger.info(f"\n  Result {i} (distance={dist:.3f}):")
            logger.info(f"    Question: {doc[:100]}...")
            logger.info(f"    Benchmark: {meta['benchmark']}")
            logger.info(f"    Domain: {meta['domain']}")
            logger.info(f"    Success Rate: {meta['success_rate']:.1%}")
            logger.info(f"    Difficulty: {meta['difficulty_label']}")

        # Test 2: Filter by difficulty
        logger.info("\n2. Filter: Nearly_Impossible questions with error analysis")
        results = collection.get(
            where={
                "$and": [
                    {"difficulty_label": "Nearly_Impossible"},
                    {"has_error_analysis": True}
                ]
            },
            limit=3,
            include=['documents', 'metadatas']
        )

        logger.info(f"  Found {len(results['documents'])} questions")
        for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas']), 1):
            logger.info(f"\n  Question {i}:")
            logger.info(f"    Text: {doc[:100]}...")
            logger.info(f"    Success Rate: {meta['success_rate']:.1%}")
            logger.info(f"    Error Patterns: {meta['num_error_patterns']}")
            logger.info(f"    Patterns: {meta['error_pattern_names']}")

        # Test 3: Universal failures
        logger.info("\n3. Filter: Universal failures (all models fail)")
        results = collection.get(
            where={"is_universal_failure": True},
            limit=3,
            include=['documents', 'metadatas']
        )

        logger.info(f"  Found {len(results['documents'])} universal failures")
        for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas']), 1):
            logger.info(f"\n  Question {i}:")
            logger.info(f"    Text: {doc[:100]}...")
            logger.info(f"    Domain: {meta['domain']}")
            logger.info(f"    CoT Failure: {meta['cot_failure_mode']}")

        # Test 4: DS-1000 questions
        logger.info("\n4. Filter: DS-1000 pandas questions")
        results = collection.get(
            where={
                "$and": [
                    {"benchmark": "DS-1000"},
                    {"domain": "Pandas"}
                ]
            },
            limit=3,
            include=['documents', 'metadatas']
        )

        logger.info(f"  Found {len(results['documents'])} DS-1000 Pandas questions")
        for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas']), 1):
            logger.info(f"\n  Question {i}:")
            logger.info(f"    Text: {doc[:100]}...")
            logger.info(f"    Success Rate: {meta['success_rate']:.1%}")

def main():
    """Build the complete vector database"""
    builder = VectorDatabaseBuilder()

    # Build database
    collection = builder.build_database(batch_size=100)

    # Print statistics
    builder.print_statistics()

    # Test queries
    builder.test_queries()

    logger.info("\n" + "="*80)
    logger.info("✅ Vector Database Build Complete!")
    logger.info("="*80)
    logger.info(f"\nDatabase Location: {builder.chroma_dir}")
    logger.info(f"Collection Name: {builder.collection_name}")
    logger.info(f"\nNext Steps:")
    logger.info(f"  1. Refactor MCP to pure data fetching")
    logger.info(f"  2. Create ToGMAL Skill with analysis procedures")
    logger.info(f"  3. Test Skills + MCP integration")

if __name__ == "__main__":
    main()
