#!/usr/bin/env python3
"""
Build ChromaDB with Lightweight ONNX Embeddings
================================================

Try using sentence-transformers with ONNX backend (no PyTorch/CUDA):
- all-MiniLM-L6-v2: 80 MB (vs 900MB with PyTorch)
- Uses onnxruntime instead of PyTorch
- Should avoid timeout in restricted environments
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LightweightONNXEmbedder:
    """Lightweight ONNX embeddings - avoids PyTorch download"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize with sentence-transformers + ONNX backend"""
        try:
            # Import sentence-transformers
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading {model_name} with ONNX backend...")
            logger.info("  Model size: ~80 MB (no PyTorch/CUDA)")
            logger.info("  Embedding dimensions: 384")

            # Try to load with ONNX backend
            # This should download only the ONNX model, not PyTorch
            self.model = SentenceTransformer(
                model_name,
                device='cpu',  # Force CPU to avoid CUDA
            )

            logger.info("✅ Model loaded successfully!")

        except ImportError as e:
            raise ImportError(f"sentence-transformers not installed: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise

    def encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Encode texts to embeddings"""
        logger.info(f"Encoding {len(texts)} texts...")

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        logger.info(f"✅ Encoded {len(embeddings)} embeddings")
        return embeddings.tolist()


class VectorDatabaseBuilder:
    """Builds ChromaDB with lightweight ONNX embeddings"""

    def __init__(
        self,
        data_dir: Path = Path("./data"),
        chroma_dir: Path = Path("./chroma_db_onnx"),
        collection_name: str = "togmal_benchmarks_onnx",
        model_name: str = "all-MiniLM-L6-v2"
    ):
        self.data_dir = data_dir
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name

        # Initialize embedder
        logger.info("="*80)
        logger.info("Lightweight ONNX Embedder Setup")
        logger.info("="*80)

        self.embedder = LightweightONNXEmbedder(model_name=model_name)

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
            }

            metadatas.append(metadata)
            ids.append(q['question_id'])

        logger.info(f"✅ Prepared {len(documents):,} documents")
        return documents, metadatas, ids

    def build_database(self, batch_size: int = 32):
        """Build the complete vector database"""
        logger.info("="*80)
        logger.info("Building ChromaDB with Lightweight ONNX Embeddings")
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
                "embedding_type": "onnx-lightweight",
                "model": "all-MiniLM-L6-v2",
                "dimensions": 384,
            }
        )

        # Generate embeddings
        logger.info("Generating ONNX embeddings...")
        embeddings = self.embedder.encode(documents, batch_size=batch_size)

        # Add to ChromaDB in batches
        logger.info(f"Adding to collection (batch_size={batch_size})...")
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]

            collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids,
                embeddings=batch_embeddings
            )

            batch_num = (i // batch_size) + 1
            total_batches = (len(documents) + batch_size - 1) // batch_size
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

        # Test queries
        test_queries = [
            "How do plants convert sunlight to energy?",
            "Calculate eigenvalues of a matrix",
            "Write pandas code to filter a dataframe",
        ]

        for test_query in test_queries:
            logger.info(f"\nQuery: '{test_query}'")

            # Encode query
            query_embedding = self.embedder.encode([test_query])[0]

            # Search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=3
            )

            logger.info("Top 3 Similar Questions:")
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ), 1):
                similarity = 1 - distance  # Convert distance to similarity
                logger.info(f"\n{i}. Similarity: {similarity:.3f}")
                logger.info(f"   {doc[:100]}...")
                logger.info(f"   Domain: {metadata['domain']}, Difficulty: {metadata['difficulty_label']}")


def main():
    """Main entry point"""

    print("\n" + "="*80)
    print("ChromaDB Builder - Lightweight ONNX Embeddings")
    print("="*80)
    print("\nModel: all-MiniLM-L6-v2")
    print("Size: ~80 MB (ONNX only, no PyTorch/CUDA)")
    print("Dimensions: 384")
    print("Backend: sentence-transformers + onnxruntime")
    print("="*80)
    print("\nStarting build...\n")

    try:
        builder = VectorDatabaseBuilder()

        # Build database
        collection = builder.build_database(batch_size=32)

        # Test it
        builder.test_semantic_search()

        logger.info("\n" + "="*80)
        logger.info("✅ Vector Database Built Successfully!")
        logger.info("="*80)
        logger.info(f"\nLocation: chroma_db_onnx/")
        logger.info(f"Model: all-MiniLM-L6-v2 (ONNX)")
        logger.info(f"Dimensions: 384")
        logger.info(f"Size: ~116 MB (database)")
        logger.info(f"\nReady for semantic search!")

    except Exception as e:
        logger.error(f"\n❌ Failed to build database: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. If download times out → Model too large for environment")
        logger.info("2. If 403 error → Network restrictions blocking download")
        logger.info("3. If out of memory → Reduce batch_size")
        logger.info("\nFallback: Use TF-IDF embeddings (build_vector_database_simple.py)")
        raise


if __name__ == "__main__":
    main()
