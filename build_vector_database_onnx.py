#!/usr/bin/env python3
"""
Build ChromaDB with ONNX Embeddings (Lightweight!)
===================================================

Uses ONNX Runtime for embeddings - much lighter than PyTorch:
- Download: ~90 MB (vs 900 MB for sentence-transformers)
- No PyTorch/CUDA dependencies
- Fast inference on CPU
- Model from GitHub releases
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ONNXEmbedder:
    """Lightweight embeddings using ONNX Runtime"""
    
    def __init__(self):
        logger.info("Loading ONNX embedding model...")
        
        # Option 1: Use ChromaDB's built-in ONNX embeddings (downloads from GitHub)
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        self.embedding_function = ONNXMiniLM_L6_V2()
        
        logger.info("✅ ONNX model loaded (all-MiniLM-L6-v2)")
        logger.info("   Source: GitHub releases (chromadb/onnx-models)")
        logger.info("   Size: ~90 MB (vs 900 MB for PyTorch)")
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings"""
        return np.array(self.embedding_function(texts))


class VectorDatabaseBuilder:
    """Builds ChromaDB with ONNX embeddings"""

    def __init__(
        self,
        data_dir: Path = Path("./data"),
        chroma_dir: Path = Path("./chroma_db"),
        collection_name: str = "togmal_benchmarks"
    ):
        self.data_dir = data_dir
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name

        # Use ONNX embeddings (lightweight!)
        self.embedder = ONNXEmbedder()

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
        """Prepare documents, metadata, and IDs for ChromaDB"""
        logger.info("Preparing documents and metadata...")

        documents = []
        metadatas = []
        ids = []

        for q in questions:
            # Document text for embedding
            doc = q['question_text']
            documents.append(doc)

            # Metadata for filtering
            metadata = {
                'question_id': q['question_id'],
                'benchmark': q['benchmark'],
                'domain': q['domain'],
                'success_rate': float(q['success_rate']),
                'difficulty_score': float(q['difficulty_score']),
                'difficulty_label': q['difficulty_label'],
                'num_models_tested': int(q['num_models_tested']),
                'has_error_analysis': len(q['error_patterns']) > 0,
                'num_error_patterns': len(q['error_patterns']),
                'is_universal_failure': q.get('is_universal_failure', False),
                'category': q.get('category') or '',
                'subject': q.get('subject') or '',
                'cot_failure_mode': q.get('cot_failure_mode') or '',
                'error_pattern_names': ','.join([
                    p['pattern'] for p in q['error_patterns']
                ]) if q['error_patterns'] else '',
                'error_pattern_sources': ','.join(set([
                    p['source'] for p in q['error_patterns']
                ])) if q['error_patterns'] else '',
                'conceptual_gaps': ','.join(q.get('conceptual_gaps', [])),
                'error_categories': ','.join(q.get('error_categories', [])),
            }

            metadatas.append(metadata)
            ids.append(q['question_id'])

        logger.info(f"✅ Prepared {len(documents):,} documents")
        return documents, metadatas, ids

    def build_database(self, batch_size: int = 100):
        """Build the complete vector database with ONNX embeddings"""
        logger.info("="*80)
        logger.info("Building ChromaDB with ONNX Embeddings (Lightweight!)")
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

        # Create collection
        logger.info(f"Creating collection: {self.collection_name}")
        collection = self.client.create_collection(
            name=self.collection_name,
            metadata={
                "description": "ToGMAL unified benchmark questions",
                "total_questions": len(questions),
                "benchmarks": "MMLU-Pro, DS-1000",
                "embedding_model": "all-MiniLM-L6-v2 (ONNX)",
                "embedding_source": "GitHub (chromadb/onnx-models)"
            }
        )

        # Add documents in batches with ONNX embeddings
        logger.info(f"Generating embeddings with ONNX Runtime...")
        logger.info(f"Adding to collection (batch_size={batch_size})...")

        total_batches = (len(documents) + batch_size - 1) // batch_size

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]

            # Generate embeddings with ONNX
            batch_embeddings = self.embedder.encode(batch_docs).tolist()

            # Add to collection
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

    def test_semantic_search(self):
        """Test semantic search functionality"""
        logger.info("\n" + "="*80)
        logger.info("Testing Semantic Search")
        logger.info("="*80)

        collection = self.client.get_collection(self.collection_name)

        # Test query
        test_query = "How do plants convert sunlight to energy?"
        logger.info(f"\nQuery: '{test_query}'")

        results = collection.query(
            query_texts=[test_query],
            n_results=3
        )

        logger.info("\nTop 3 Similar Questions:")
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
            logger.info(f"\n{i}. {doc[:100]}...")
            logger.info(f"   Domain: {metadata['domain']}")
            logger.info(f"   Difficulty: {metadata['difficulty_label']}")
            logger.info(f"   Success Rate: {metadata['success_rate']:.1%}")


def main():
    builder = VectorDatabaseBuilder()
    
    # Build database
    collection = builder.build_database(batch_size=100)
    
    # Test it
    builder.test_semantic_search()
    
    logger.info("\n" + "="*80)
    logger.info("✅ Vector Database Built Successfully!")
    logger.info("="*80)
    logger.info(f"\nLocation: chroma_db/")
    logger.info(f"Model: all-MiniLM-L6-v2 (ONNX from GitHub)")
    logger.info(f"Download: ~90 MB (vs 900 MB for PyTorch)")
    logger.info(f"\nReady for semantic search!")


if __name__ == "__main__":
    main()
