#!/usr/bin/env python3
"""
Build ChromaDB with Simple Embeddings (No External Downloads)
==============================================================

Alternatives to ONNX/sentence-transformers that work in restricted environments:

1. TF-IDF embeddings (no model download needed)
2. Hash-based embeddings (no model download needed)
3. OpenAI API embeddings (no local model needed)
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

class SimpleTFIDFEmbedder:
    """TF-IDF based embeddings - no model download needed"""

    def __init__(self, max_features=384):
        """Initialize with sklearn's TfidfVectorizer"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=max_features,
                ngram_range=(1, 2),  # unigrams and bigrams
                min_df=2,
                max_df=0.8,
                stop_words='english'
            )
            self.fitted = False
            logger.info("✅ TF-IDF vectorizer initialized (sklearn)")
        except ImportError:
            raise ImportError("sklearn not installed. Run: pip install scikit-learn")

    def fit_transform(self, texts: List[str]) -> np.ndarray:
        """Fit vectorizer and transform texts"""
        logger.info(f"Fitting TF-IDF on {len(texts)} documents...")
        matrix = self.vectorizer.fit_transform(texts)
        self.fitted = True
        logger.info(f"✅ TF-IDF fitted (vocabulary size: {len(self.vectorizer.vocabulary_)})")
        return matrix.toarray()

    def transform(self, texts: List[str]) -> np.ndarray:
        """Transform texts using fitted vectorizer"""
        if not self.fitted:
            raise ValueError("Vectorizer not fitted yet!")
        return self.vectorizer.transform(texts).toarray()


class OpenAIEmbedder:
    """OpenAI API embeddings - no model download, just API calls"""

    def __init__(self, api_key: str = None):
        """Initialize with OpenAI API key"""
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            logger.info("✅ OpenAI API client initialized")
            logger.info("   Model: text-embedding-3-small (1536 dimensions)")
            logger.info("   Cost: ~$0.02 per 1M tokens")
        except ImportError:
            raise ImportError("openai not installed. Run: pip install openai")

    def encode(self, texts: List[str], batch_size: int = 100) -> np.ndarray:
        """Encode texts using OpenAI API"""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                input=batch,
                model="text-embedding-3-small"
            )
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)

            if (i + batch_size) % 1000 == 0:
                logger.info(f"  Processed {i + batch_size}/{len(texts)} documents")

        return np.array(all_embeddings)


class VectorDatabaseBuilder:
    """Builds ChromaDB with simple embeddings"""

    def __init__(
        self,
        data_dir: Path = Path("./data"),
        chroma_dir: Path = Path("./chroma_db"),
        collection_name: str = "togmal_benchmarks",
        embedding_type: str = "tfidf"  # "tfidf" or "openai"
    ):
        self.data_dir = data_dir
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name
        self.embedding_type = embedding_type

        # Initialize embedder
        if embedding_type == "tfidf":
            self.embedder = SimpleTFIDFEmbedder(max_features=384)
        elif embedding_type == "openai":
            api_key = input("Enter OpenAI API key: ").strip()
            self.embedder = OpenAIEmbedder(api_key=api_key)
        else:
            raise ValueError(f"Unknown embedding type: {embedding_type}")

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

    def build_database(self, batch_size: int = 100):
        """Build the complete vector database"""
        logger.info("="*80)
        logger.info(f"Building ChromaDB with {self.embedding_type.upper()} Embeddings")
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
                "embedding_type": self.embedding_type,
            }
        )

        # Generate embeddings
        logger.info(f"Generating {self.embedding_type.upper()} embeddings...")

        if self.embedding_type == "tfidf":
            # TF-IDF: fit on all documents at once
            embeddings = self.embedder.fit_transform(documents)

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

        elif self.embedding_type == "openai":
            # OpenAI: encode in batches (API has rate limits)
            embeddings = self.embedder.encode(documents, batch_size=batch_size)

            # Add to ChromaDB
            logger.info(f"Adding to collection...")
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
    """Main entry point"""

    print("\n" + "="*80)
    print("ChromaDB Builder - Simple Embeddings (No External Downloads)")
    print("="*80)
    print("\nAvailable options:")
    print("1. TF-IDF embeddings (sklearn, no download, works offline)")
    print("2. OpenAI API embeddings (requires API key, ~$0.26 for 13K questions)")
    print("="*80)

    choice = input("\nSelect option (1 or 2): ").strip()

    if choice == "1":
        embedding_type = "tfidf"
    elif choice == "2":
        embedding_type = "openai"
    else:
        print("Invalid choice!")
        return

    builder = VectorDatabaseBuilder(embedding_type=embedding_type)

    # Build database
    collection = builder.build_database(batch_size=100)

    # Test it
    builder.test_semantic_search()

    logger.info("\n" + "="*80)
    logger.info("✅ Vector Database Built Successfully!")
    logger.info("="*80)
    logger.info(f"\nLocation: chroma_db/")
    logger.info(f"Embedding type: {embedding_type.upper()}")
    if embedding_type == "tfidf":
        logger.info(f"Features: TF-IDF (384 dimensions)")
        logger.info(f"Cost: $0 (no API calls)")
    else:
        logger.info(f"Model: text-embedding-3-small (1536 dimensions)")
        logger.info(f"Cost: ~$0.26 for 13K questions")
    logger.info(f"\nReady for semantic search!")


if __name__ == "__main__":
    main()
