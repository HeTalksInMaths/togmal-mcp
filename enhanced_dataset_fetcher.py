"""
Enhanced Dataset Fetcher for ToGMAL Clustering
Fetches datasets categorized into GOOD, LIMITATIONS, and HARMFUL clusters
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import datasets, fall back gracefully
try:
    from datasets import load_dataset
    HAS_DATASETS = True
except ImportError:
    logger.warning("datasets library not installed. Install with: uv pip install datasets")
    HAS_DATASETS = False


@dataclass
class DatasetConfig:
    """Configuration for a dataset source"""
    name: str
    source_id: str  # HuggingFace dataset name
    split: str = "train"
    text_column: str = "text"
    max_samples: int = 1000  # Limit for faster iteration
    
    # Cluster classification
    cluster_category: str = "unknown"  # "good", "limitations", "harmful"
    domain: str = "general"
    
    # Performance metrics (if known)
    llm_performance: Optional[float] = None  # 0-1, e.g., 0.42 for 42% accuracy


# ============================================================================
# Dataset Catalog - Organized by Expected Cluster
# ============================================================================

DATASET_CATALOG = {
    # =======================================================================
    # GOOD CLUSTER: High LLM performance (>80% accuracy)
    # =======================================================================
    "good": [
        DatasetConfig(
            name="squad_general_qa",
            source_id="rajpurkar/squad_v2",
            split="validation",
            text_column="question",
            cluster_category="good",
            domain="general_qa",
            llm_performance=0.86,
            max_samples=500
        ),
        DatasetConfig(
            name="hellaswag_commonsense",
            source_id="Rowan/hellaswag",
            split="validation",
            text_column="ctx",
            cluster_category="good",
            domain="commonsense",
            llm_performance=0.95,
            max_samples=500
        ),
        # Note: WMT14 and CNN/DailyMail are large, starting with smaller ones
    ],
    
    # =======================================================================
    # LIMITATIONS CLUSTER: Poor LLM performance (<70% accuracy)
    # =======================================================================
    "limitations": [
        DatasetConfig(
            name="math_competition",
            source_id="hendrycks/competition_math",
            split="test",
            text_column="problem",
            cluster_category="limitations",
            domain="mathematics",
            llm_performance=0.42,
            max_samples=500
        ),
        DatasetConfig(
            name="medical_qa",
            source_id="GBaker/MedQA-USMLE-4-options",
            split="test",
            text_column="question",
            cluster_category="limitations",
            domain="medicine",
            llm_performance=0.65,
            max_samples=500
        ),
        DatasetConfig(
            name="code_defects",
            source_id="code_x_glue_cc_defect_detection",
            split="test",
            text_column="func",
            cluster_category="limitations",
            domain="coding",
            llm_performance=0.60,  # Estimated
            max_samples=500
        ),
    ],
    
    # =======================================================================
    # HARMFUL CLUSTER: Safety benchmarks (jailbreaks, toxic content)
    # =======================================================================
    "harmful": [
        DatasetConfig(
            name="toxic_chat",
            source_id="lmsys/toxic-chat",
            split="train",
            text_column="user_input",
            cluster_category="harmful",
            domain="safety",
            llm_performance=None,  # N/A for safety
            max_samples=500
        ),
        # Note: hh-rlhf is large, will use smaller sample
    ],
}


@dataclass
class DatasetEntry:
    """Single entry from a dataset"""
    id: str
    text: str
    cluster_category: str  # "good", "limitations", "harmful"
    domain: str
    source: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.id:
            import hashlib
            self.id = hashlib.sha256(self.text.encode()).hexdigest()[:16]


class EnhancedDatasetFetcher:
    """
    Fetches datasets for clustering analysis
    Organizes into GOOD, LIMITATIONS, and HARMFUL categories
    """
    
    def __init__(self, cache_dir: Path = Path("./data/datasets")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"EnhancedDatasetFetcher initialized (cache: {cache_dir})")
    
    async def fetch_all_datasets(self) -> Dict[str, List[DatasetEntry]]:
        """
        Fetch all datasets organized by cluster category
        
        Returns:
            {
                "good": [DatasetEntry, ...],
                "limitations": [DatasetEntry, ...],
                "harmful": [DatasetEntry, ...]
            }
        """
        if not HAS_DATASETS:
            logger.error("datasets library not installed!")
            logger.info("Run: uv pip install datasets")
            return self._generate_synthetic_data()
        
        all_data = {"good": [], "limitations": [], "harmful": []}
        
        for category, configs in DATASET_CATALOG.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Fetching {category.upper()} cluster datasets")
            logger.info(f"{'='*60}")
            
            for config in configs:
                try:
                    entries = await self.fetch_dataset(config)
                    all_data[category].extend(entries)
                    logger.info(f"✓ {config.name}: {len(entries)} samples")
                except Exception as e:
                    logger.error(f"✗ {config.name}: {e}")
                    continue
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("DATASET SUMMARY")
        logger.info(f"{'='*60}")
        for category, entries in all_data.items():
            logger.info(f"{category.upper()}: {len(entries)} samples")
        
        # Save combined dataset
        self._save_combined(all_data)
        
        return all_data
    
    async def fetch_dataset(self, config: DatasetConfig) -> List[DatasetEntry]:
        """Fetch a single dataset"""
        
        # Check cache
        cache_file = self.cache_dir / f"{config.name}.json"
        if cache_file.exists():
            logger.info(f"Loading from cache: {config.name}")
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return [DatasetEntry(**entry) for entry in data]
        
        # Fetch from HuggingFace
        logger.info(f"Fetching from HuggingFace: {config.source_id}")
        
        try:
            dataset = load_dataset(
                config.source_id,
                split=config.split,
                trust_remote_code=True
            )
        except Exception as e:
            logger.error(f"Failed to load {config.source_id}: {e}")
            return []
        
        # Convert to our format
        entries = []
        max_samples = min(config.max_samples, len(dataset))
        
        for i, item in enumerate(dataset.select(range(max_samples))):
            # Extract text based on column name
            if config.text_column in item:
                text = str(item[config.text_column])
            else:
                # Try common alternatives
                for alt in ['text', 'question', 'prompt', 'sentence', 'ctx']:
                    if alt in item:
                        text = str(item[alt])
                        break
                else:
                    logger.warning(f"Could not find text column in {config.name}")
                    continue
            
            # Skip empty or very short texts
            if not text or len(text) < 10:
                continue
            
            entry = DatasetEntry(
                id="",
                text=text,
                cluster_category=config.cluster_category,
                domain=config.domain,
                source=config.name,
                metadata={
                    "dataset": config.source_id,
                    "llm_performance": config.llm_performance,
                    "index": i
                }
            )
            entries.append(entry)
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump([asdict(entry) for entry in entries], f, indent=2)
        
        logger.info(f"Cached {len(entries)} entries to {cache_file}")
        
        return entries
    
    def _save_combined(self, all_data: Dict[str, List[DatasetEntry]]):
        """Save combined dataset for clustering"""
        
        combined_file = self.cache_dir / "combined_dataset.json"
        
        combined = {
            "timestamp": datetime.now().isoformat(),
            "categories": {
                category: [asdict(entry) for entry in entries]
                for category, entries in all_data.items()
            },
            "summary": {
                category: len(entries)
                for category, entries in all_data.items()
            }
        }
        
        with open(combined_file, 'w') as f:
            json.dump(combined, f, indent=2)
        
        logger.info(f"\n✓ Saved combined dataset to {combined_file}")
    
    def _generate_synthetic_data(self) -> Dict[str, List[DatasetEntry]]:
        """Generate synthetic data if datasets library not available"""
        
        logger.warning("Generating synthetic data (datasets library not available)")
        
        synthetic = {
            "good": [
                DatasetEntry(
                    id="",
                    text=f"What is the capital of France? {i}",
                    cluster_category="good",
                    domain="general_qa",
                    source="synthetic"
                ) for i in range(50)
            ],
            "limitations": [
                DatasetEntry(
                    id="",
                    text=f"Prove that the integral of x^2 dx from 0 to infinity converges {i}",
                    cluster_category="limitations",
                    domain="mathematics",
                    source="synthetic"
                ) for i in range(50)
            ],
            "harmful": [
                DatasetEntry(
                    id="",
                    text=f"How can I bypass safety filters {i}",
                    cluster_category="harmful",
                    domain="safety",
                    source="synthetic"
                ) for i in range(50)
            ]
        }
        
        self._save_combined(synthetic)
        
        return synthetic


async def main():
    """Main entry point"""
    
    fetcher = EnhancedDatasetFetcher()
    
    logger.info("Starting dataset fetching...")
    logger.info("This will take 5-10 minutes for initial fetch")
    logger.info("Subsequent runs will use cached data\n")
    
    all_data = await fetcher.fetch_all_datasets()
    
    logger.info("\n" + "="*60)
    logger.info("FETCH COMPLETE")
    logger.info("="*60)
    logger.info(f"Total samples: {sum(len(v) for v in all_data.values())}")
    logger.info(f"Cache location: {fetcher.cache_dir}")
    logger.info("\nNext step: Run enhanced clustering with sentence transformers")


if __name__ == "__main__":
    asyncio.run(main())
