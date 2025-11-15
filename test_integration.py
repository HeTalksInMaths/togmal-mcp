#!/usr/bin/env python3
"""
Integration Testing for ToGMAL
===============================

Tests vector database integration and validates data format
for ToGMAL MCP risk assessment use cases.

Author: ToGMAL Project
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import sys

# Check if chromadb is available
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️  ChromaDB not installed. Install with: pip install chromadb")

class ToGMALIntegrationTester:
    """Tests integration with ToGMAL MCP server."""

    def __init__(
        self,
        vector_file: Path = Path("data/autonomous_benchmarks/vector_db_ready.json"),
        dataset_file: Path = Path("data/autonomous_benchmarks/autonomous_dataset.json")
    ):
        """Initialize tester."""
        self.vector_file = vector_file
        self.dataset_file = dataset_file

        # Load data
        with open(vector_file) as f:
            self.vector_data = json.load(f)

        with open(dataset_file) as f:
            self.dataset = json.load(f)

    def run_all_tests(self):
        """Run all integration tests."""
        print("="*70)
        print("🧪 TOGMAL INTEGRATION TESTS")
        print("="*70)

        tests = [
            ("1. Data Format Validation", self.test_data_format),
            ("2. Vector Data Structure", self.test_vector_structure),
            ("3. Metadata Completeness", self.test_metadata_completeness),
            ("4. Risk Signal Quality", self.test_risk_signals),
            ("5. Model Score Distribution", self.test_model_score_distribution),
        ]

        if CHROMADB_AVAILABLE:
            tests.append(("6. ChromaDB Integration", self.test_chromadb_integration))
            tests.append(("7. Similarity Search", self.test_similarity_search))
            tests.append(("8. Risk Assessment Workflow", self.test_risk_assessment))

        passed = 0
        failed = 0

        for name, test_func in tests:
            print(f"\n{name}")
            print("-" * 70)
            try:
                result = test_func()
                if result:
                    passed += 1
                    print(f"✅ PASSED")
                else:
                    failed += 1
                    print(f"❌ FAILED")
            except Exception as e:
                failed += 1
                print(f"❌ FAILED: {e}")

        print("\n" + "="*70)
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("="*70)

        return failed == 0

    def test_data_format(self):
        """Test basic data format requirements."""
        print("Checking data format...")

        # Check vector data has required keys
        required_keys = ['documents', 'metadatas', 'ids', 'source_metadata']
        for key in required_keys:
            if key not in self.vector_data:
                print(f"  ❌ Missing key: {key}")
                return False

        # Check lengths match
        docs_len = len(self.vector_data['documents'])
        meta_len = len(self.vector_data['metadatas'])
        ids_len = len(self.vector_data['ids'])

        if not (docs_len == meta_len == ids_len):
            print(f"  ❌ Length mismatch: docs={docs_len}, meta={meta_len}, ids={ids_len}")
            return False

        print(f"  ✓ All required keys present")
        print(f"  ✓ Consistent lengths: {docs_len:,} items")

        return True

    def test_vector_structure(self):
        """Test vector data structure matches ChromaDB requirements."""
        print("Validating vector structure...")

        # Sample first item
        sample_doc = self.vector_data['documents'][0]
        sample_meta = self.vector_data['metadatas'][0]
        sample_id = self.vector_data['ids'][0]

        # Check document is string
        if not isinstance(sample_doc, str):
            print(f"  ❌ Document is not string: {type(sample_doc)}")
            return False

        # Check metadata is dict
        if not isinstance(sample_meta, dict):
            print(f"  ❌ Metadata is not dict: {type(sample_meta)}")
            return False

        # Check id is string
        if not isinstance(sample_id, str):
            print(f"  ❌ ID is not string: {type(sample_id)}")
            return False

        # Check required metadata fields
        required_meta_fields = ['success_rate', 'num_models', 'model_scores']
        for field in required_meta_fields:
            if field not in sample_meta:
                print(f"  ❌ Missing metadata field: {field}")
                return False

        print(f"  ✓ Document type: string ({len(sample_doc)} chars)")
        print(f"  ✓ Metadata type: dict ({len(sample_meta)} fields)")
        print(f"  ✓ ID type: string ({sample_id})")
        print(f"  ✓ Required metadata fields present")

        return True

    def test_metadata_completeness(self):
        """Test metadata has all necessary fields for ToGMAL."""
        print("Checking metadata completeness...")

        # Check all metadata entries
        issues = []
        for i, meta in enumerate(self.vector_data['metadatas'][:100]):  # Sample 100
            # Check success_rate is valid
            if 'success_rate' not in meta or not (0 <= meta['success_rate'] <= 1):
                issues.append(f"Invalid success_rate at index {i}")

            # Check model_scores can be parsed
            if 'model_scores' in meta:
                try:
                    scores = json.loads(meta['model_scores'])
                    if not isinstance(scores, dict):
                        issues.append(f"model_scores not a dict at index {i}")
                except json.JSONDecodeError:
                    issues.append(f"Invalid JSON in model_scores at index {i}")

        if issues:
            print(f"  ❌ Found {len(issues)} issues:")
            for issue in issues[:5]:
                print(f"    - {issue}")
            return False

        print(f"  ✓ All metadata entries valid (sampled 100)")
        print(f"  ✓ Success rates in valid range [0, 1]")
        print(f"  ✓ Model scores properly JSON-encoded")

        return True

    def test_risk_signals(self):
        """Test that risk signals are diverse and meaningful."""
        print("Analyzing risk signal quality...")

        success_rates = [m['success_rate'] for m in self.vector_data['metadatas']]

        # Check distribution
        low_risk = sum(1 for sr in success_rates if sr > 0.7)
        med_risk = sum(1 for sr in success_rates if 0.3 <= sr <= 0.7)
        high_risk = sum(1 for sr in success_rates if sr < 0.3)

        total = len(success_rates)
        low_pct = low_risk / total * 100
        med_pct = med_risk / total * 100
        high_pct = high_risk / total * 100

        print(f"  Risk distribution:")
        print(f"    Low risk (>70%): {low_risk:,} ({low_pct:.1f}%)")
        print(f"    Medium risk (30-70%): {med_risk:,} ({med_pct:.1f}%)")
        print(f"    High risk (<30%): {high_risk:,} ({high_pct:.1f}%)")

        # Check if distribution is reasonable (not too skewed)
        if low_pct > 80 or low_pct < 20:
            print(f"  ⚠️  Low risk tier heavily skewed ({low_pct:.1f}%)")

        if high_pct < 10:
            print(f"  ⚠️  Very few high-risk examples ({high_pct:.1f}%)")

        # All tiers should have at least some representation
        if high_risk == 0 or med_risk == 0 or low_risk == 0:
            print(f"  ❌ Missing risk tier representation")
            return False

        print(f"  ✓ All risk tiers represented")
        print(f"  ✓ Distribution suitable for risk assessment")

        return True

    def test_model_score_distribution(self):
        """Test model score distribution for each question."""
        print("Checking model score distribution...")

        # Sample questions and check model coverage
        model_coverage = []
        for meta in self.vector_data['metadatas'][:100]:
            scores = json.loads(meta['model_scores'])
            model_coverage.append(len(scores))

        avg_models = sum(model_coverage) / len(model_coverage)
        min_models = min(model_coverage)
        max_models = max(model_coverage)

        print(f"  Models per question: avg={avg_models:.1f}, min={min_models}, max={max_models}")

        if min_models < 5:
            print(f"  ⚠️  Some questions have very few models (<5)")

        if avg_models < 10:
            print(f"  ⚠️  Average model coverage is low ({avg_models:.1f})")
            return False

        print(f"  ✓ Good model coverage (avg {avg_models:.1f} models/question)")

        return True

    def test_chromadb_integration(self):
        """Test loading data into ChromaDB."""
        if not CHROMADB_AVAILABLE:
            print("  ⏭️  Skipped (ChromaDB not installed)")
            return True

        print("Testing ChromaDB integration...")

        try:
            # Create in-memory database
            client = chromadb.Client(Settings(anonymized_telemetry=False))

            # Create collection
            collection = client.create_collection(
                name="togmal_test",
                metadata={"description": "Integration test collection"}
            )

            # Load small sample
            sample_size = 100
            collection.add(
                documents=self.vector_data['documents'][:sample_size],
                metadatas=self.vector_data['metadatas'][:sample_size],
                ids=self.vector_data['ids'][:sample_size]
            )

            # Verify
            count = collection.count()
            print(f"  ✓ Created collection: {count} documents loaded")

            # Test retrieval
            result = collection.get(ids=[self.vector_data['ids'][0]])
            if len(result['ids']) != 1:
                print(f"  ❌ Retrieval failed")
                return False

            print(f"  ✓ Document retrieval works")

            return True

        except Exception as e:
            print(f"  ❌ ChromaDB error: {e}")
            return False

    def test_similarity_search(self):
        """Test similarity search functionality."""
        if not CHROMADB_AVAILABLE:
            print("  ⏭️  Skipped (ChromaDB not installed)")
            return True

        print("Testing similarity search...")

        try:
            # Create database
            client = chromadb.Client(Settings(anonymized_telemetry=False))
            collection = client.create_collection(name="togmal_search_test")

            # Load sample
            sample_size = 1000
            collection.add(
                documents=self.vector_data['documents'][:sample_size],
                metadatas=self.vector_data['metadatas'][:sample_size],
                ids=self.vector_data['ids'][:sample_size]
            )

            # Test queries
            test_queries = [
                "What is the capital of France?",
                "Calculate the derivative of x^2",
                "Explain quantum entanglement"
            ]

            for query in test_queries:
                results = collection.query(
                    query_texts=[query],
                    n_results=5
                )

                if len(results['ids'][0]) != 5:
                    print(f"  ❌ Expected 5 results, got {len(results['ids'][0])}")
                    return False

            print(f"  ✓ Similarity search works")
            print(f"  ✓ Tested {len(test_queries)} queries")

            return True

        except Exception as e:
            print(f"  ❌ Search error: {e}")
            return False

    def test_risk_assessment(self):
        """Test complete ToGMAL risk assessment workflow."""
        if not CHROMADB_AVAILABLE:
            print("  ⏭️  Skipped (ChromaDB not installed)")
            return True

        print("Testing ToGMAL risk assessment workflow...")

        try:
            # Setup
            client = chromadb.Client(Settings(anonymized_telemetry=False))
            collection = client.create_collection(name="togmal_risk_test")

            collection.add(
                documents=self.vector_data['documents'][:500],
                metadatas=self.vector_data['metadatas'][:500],
                ids=self.vector_data['ids'][:500]
            )

            # Simulate ToGMAL query
            user_query = "Solve a complex physics problem involving quantum mechanics"

            # Find similar questions
            results = collection.query(
                query_texts=[user_query],
                n_results=10
            )

            # Extract risk signals
            success_rates = [m['success_rate'] for m in results['metadatas'][0]]
            avg_success = sum(success_rates) / len(success_rates)

            print(f"\n  📝 Example Query: '{user_query[:50]}...'")
            print(f"  🔍 Found {len(success_rates)} similar questions")
            print(f"  📊 Average success rate: {avg_success*100:.1f}%")

            # Determine risk level
            if avg_success < 0.3:
                risk = "🔴 HIGH RISK"
            elif avg_success < 0.7:
                risk = "🟡 MEDIUM RISK"
            else:
                risk = "🟢 LOW RISK"

            print(f"  ⚠️  Risk Assessment: {risk}")

            # Check model size patterns
            model_scores_sample = json.loads(results['metadatas'][0][0]['model_scores'])
            small_models = [k for k in model_scores_sample.keys() if '7B' in k or '8B' in k]
            large_models = [k for k in model_scores_sample.keys() if '70B' in k or '34B' in k]

            print(f"  🤖 Models tested: {len(model_scores_sample)} total")
            print(f"     - Small models (≤10B): {len(small_models)}")
            print(f"     - Large models (>10B): {len(large_models)}")

            print(f"\n  ✓ Complete workflow functional")
            print(f"  ✓ Can extract risk signals")
            print(f"  ✓ Can analyze model size patterns")

            return True

        except Exception as e:
            print(f"  ❌ Workflow error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    tester = ToGMALIntegrationTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
