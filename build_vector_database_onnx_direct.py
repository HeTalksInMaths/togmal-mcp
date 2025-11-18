#!/usr/bin/env python3
"""
Build ChromaDB with Direct ONNX Model Download
===============================================

Try downloading ONNX model directly from public URL:
- all-MiniLM-L6-v2.onnx from Hugging Face or other public source
- Use onnxruntime directly (no sentence-transformers needed)
- Should avoid PyTorch download
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
import numpy as np
import requests
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DirectONNXEmbedder:
    """Use ONNX Runtime directly with downloaded model"""

    def __init__(self, model_url: str = None):
        """Initialize with ONNX Runtime"""
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer

            # Model URL (all-MiniLM-L6-v2 ONNX from public source)
            if model_url is None:
                # Try Hugging Face's ONNX models
                model_url = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/onnx/model.onnx"

            logger.info(f"Downloading ONNX model from: {model_url}")
            logger.info("  Model: all-MiniLM-L6-v2")
            logger.info("  Size: ~23 MB (ONNX only)")
            logger.info("  Dimensions: 384")

            # Download model
            model_path = Path("./models/all-MiniLM-L6-v2.onnx")
            model_path.parent.mkdir(exist_ok=True)

            if not model_path.exists():
                logger.info("  Downloading...")
                response = requests.get(model_url, stream=True, timeout=60)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))

                with open(model_path, 'wb') as f:
                    if total_size:
                        with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                                pbar.update(len(chunk))
                    else:
                        f.write(response.content)

                logger.info(f"  ✅ Downloaded to {model_path}")
            else:
                logger.info(f"  ✅ Using cached model: {model_path}")

            # Load ONNX model
            logger.info("Loading ONNX session...")
            self.session = ort.InferenceSession(
                str(model_path),
                providers=['CPUExecutionProvider']
            )

            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                "sentence-transformers/all-MiniLM-L6-v2"
            )

            logger.info("✅ Model loaded successfully!")

        except ImportError as e:
            raise ImportError(f"Required library not installed: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise

    def mean_pooling(self, token_embeddings, attention_mask):
        """Mean pooling - take attention mask into account"""
        input_mask_expanded = np.expand_dims(attention_mask, -1)
        input_mask_expanded = np.broadcast_to(input_mask_expanded, token_embeddings.shape).astype(float)

        sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)

        return sum_embeddings / sum_mask

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts to embeddings"""
        logger.info(f"Encoding {len(texts)} texts...")

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            # Tokenize
            encoded = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors='np'
            )

            # Run ONNX inference
            onnx_inputs = {
                'input_ids': encoded['input_ids'].astype(np.int64),
                'attention_mask': encoded['attention_mask'].astype(np.int64),
                'token_type_ids': encoded['token_type_ids'].astype(np.int64)
            }

            outputs = self.session.run(None, onnx_inputs)
            token_embeddings = outputs[0]

            # Mean pooling
            embeddings = self.mean_pooling(token_embeddings, encoded['attention_mask'])

            # Normalize
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

            all_embeddings.append(embeddings)

            if (i + batch_size) % 1000 == 0:
                logger.info(f"  Processed {i + batch_size}/{len(texts)} documents")

        all_embeddings = np.vstack(all_embeddings)
        logger.info(f"✅ Encoded {len(all_embeddings)} embeddings")

        return all_embeddings


class VectorDatabaseBuilder:
    """Builds ChromaDB with direct ONNX embeddings"""

    def __init__(
        self,
        data_dir: Path = Path("./data"),
        chroma_dir: Path = Path("./chroma_db_onnx"),
        collection_name: str = "togmal_benchmarks_onnx"
    ):
        self.data_dir = data_dir
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name

        # Initialize embedder
        logger.info("="*80)
        logger.info("Direct ONNX Embedder Setup")
        logger.info("="*80)

        self.embedder = DirectONNXEmbedder()

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
            documents.append(q['question_text'])

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
        logger.info("Building ChromaDB with Direct ONNX Embeddings")
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
                "embedding_type": "onnx-direct",
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
            batch_embeddings = embeddings[i:i + batch_size].tolist()

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


def main():
    """Main entry point"""

    print("\n" + "="*80)
    print("ChromaDB Builder - Direct ONNX Download")
    print("="*80)
    print("\nModel: all-MiniLM-L6-v2 (ONNX)")
    print("Source: Hugging Face")
    print("Size: ~23 MB (ONNX model only)")
    print("Dimensions: 384")
    print("Backend: onnxruntime + transformers tokenizer")
    print("="*80)
    print("\nStarting build...\n")

    try:
        builder = VectorDatabaseBuilder()

        # Build database
        collection = builder.build_database(batch_size=32)

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
        logger.info("1. If download blocked → Network restrictions")
        logger.info("2. If tokenizer fails → transformers library issue")
        logger.info("3. If out of memory → Reduce batch_size")
        logger.info("\nFallback: Use TF-IDF embeddings (build_vector_database_simple.py)")
        raise


if __name__ == "__main__":
    main()
