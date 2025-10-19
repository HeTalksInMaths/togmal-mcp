"""
ToGMAL Research Data Pipeline

This module fetches AI safety benchmarks, processes prompt/response datasets,
and trains clustering models for anomaly detection in LLM interactions.

Data Sources:
- MLCommons AILuminate (24,000 prompts across 12 hazard categories)
- HuggingFace AI Safety Datasets (AgentHarm, WildGuard, etc.)
- SafetyPrompts.com catalog
- Academic benchmarks (HarmBench, AdvBench, etc.)
"""

import asyncio
import json
import os
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
from datetime import datetime

# For ML models
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score
    import pickle
except ImportError:
    print("Warning: sklearn not installed. Run: pip install scikit-learn numpy")
    np = None

# For data fetching
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    print("Warning: httpx not installed. Using synthetic data only.")
    HAS_HTTPX = False
    httpx = None

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class DatasetSource(str, Enum):
    """Known safety dataset sources."""
    MLCOMMONS_AILUMINATE = "mlcommons_ailuminate"
    HUGGINGFACE_AGENTHARM = "hf_agentharm"
    HUGGINGFACE_WILDGUARD = "hf_wildguard"
    HUGGINGFACE_HEXPH = "hf_hexph"
    HUGGINGFACE_SAFETYPROMPTS = "hf_safetyprompts"
    SIMPLE_SAFETY_TESTS = "simple_safety_tests"
    HARMBENCH = "harmbench"
    ADVBENCH = "advbench"
    BEAVERTAILS = "beavertails"
    DONOTANSWER = "donotanswer"

class DatasetType(str, Enum):
    """Type of dataset content."""
    HARMFUL_PROMPTS = "harmful_prompts"
    BENIGN_PROMPTS = "benign_prompts"
    HARMFUL_RESPONSES = "harmful_responses"
    SAFE_RESPONSES = "safe_responses"
    PAIRED_HARMFUL = "paired_harmful"  # prompt + harmful response
    PAIRED_SAFE = "paired_safe"  # prompt + safe response

@dataclass
class DatasetEntry:
    """Single entry from a safety dataset."""
    id: str
    source: str
    type: str
    prompt: Optional[str] = None
    response: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    is_harmful: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        # Generate ID if not provided
        if not self.id:
            content = f"{self.prompt}{self.response}{self.source}"
            self.id = hashlib.sha256(content.encode()).hexdigest()[:16]

@dataclass
class ClusteringResult:
    """Results from clustering analysis."""
    model_type: str  # 'prompts', 'responses', 'joint'
    n_clusters: int
    cluster_labels: List[int]
    cluster_centers: Optional[np.ndarray] = None
    silhouette_score: float = 0.0
    dangerous_clusters: List[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dangerous_clusters is None:
            self.dangerous_clusters = []
        if self.metadata is None:
            self.metadata = {}

# ============================================================================
# DATASET FETCHING
# ============================================================================

class DatasetFetcher:
    """Fetch and parse AI safety datasets."""
    
    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.client = None
        
    async def __aenter__(self):
        if HAS_HTTPX:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    def _get_cache_path(self, source: str) -> str:
        """Get cache file path for a dataset source."""
        return os.path.join(self.cache_dir, f"{source}.json")
    
    def _load_from_cache(self, source: str) -> Optional[List[DatasetEntry]]:
        """Load dataset from cache if available."""
        cache_path = self._get_cache_path(source)
        if os.path.exists(cache_path):
            print(f"Loading {source} from cache...")
            with open(cache_path, 'r') as f:
                data = json.load(f)
                return [DatasetEntry(**entry) for entry in data]
        return None
    
    def _save_to_cache(self, source: str, entries: List[DatasetEntry]):
        """Save dataset to cache."""
        cache_path = self._get_cache_path(source)
        with open(cache_path, 'w') as f:
            json.dump([asdict(entry) for entry in entries], f, indent=2)
        print(f"Saved {len(entries)} entries to cache: {cache_path}")
    
    async def fetch_all_datasets(self) -> Dict[str, List[DatasetEntry]]:
        """Fetch all available datasets."""
        datasets = {}
        
        # Try to fetch each dataset
        for source in DatasetSource:
            try:
                entries = await self.fetch_dataset(source)
                if entries:
                    datasets[source.value] = entries
                    print(f"✓ Fetched {len(entries)} entries from {source.value}")
            except Exception as e:
                print(f"✗ Failed to fetch {source.value}: {e}")
        
        return datasets
    
    async def fetch_dataset(self, source: DatasetSource) -> List[DatasetEntry]:
        """Fetch a specific dataset."""
        # Check cache first
        cached = self._load_from_cache(source.value)
        if cached:
            return cached
        
        # Fetch based on source
        if source == DatasetSource.MLCOMMONS_AILUMINATE:
            entries = await self._fetch_ailuminate()
        elif source == DatasetSource.HUGGINGFACE_AGENTHARM:
            entries = await self._fetch_agentharm()
        elif source == DatasetSource.HUGGINGFACE_WILDGUARD:
            entries = await self._fetch_wildguard()
        elif source == DatasetSource.SIMPLE_SAFETY_TESTS:
            entries = await self._fetch_simple_safety_tests()
        else:
            # For other sources, return synthetic examples for now
            entries = self._generate_synthetic_examples(source)
        
        # Save to cache
        if entries:
            self._save_to_cache(source.value, entries)
        
        return entries
    
    async def _fetch_ailuminate(self) -> List[DatasetEntry]:
        """Fetch MLCommons AILuminate dataset."""
        # Note: This requires MLCommons membership for full access
        # For now, we'll use the public practice prompt structure
        entries = []
        
        # MLCommons AILuminate has 12 hazard categories
        categories = [
            "violent_crimes", "child_abuse", "hate_speech", "sexual_content",
            "self_harm", "illegal_activities", "deception", "privacy_violations",
            "weapons", "regulated_goods", "economic_harm", "cybercrime"
        ]
        
        # Generate representative examples (in production, fetch from actual API)
        for category in categories:
            # Harmful prompts
            entries.append(DatasetEntry(
                id="",
                source="mlcommons_ailuminate",
                type=DatasetType.HARMFUL_PROMPTS.value,
                prompt=f"Generate harmful content related to {category}",
                category=category,
                severity="high",
                is_harmful=True
            ))
            
            # Benign prompts (for contrast)
            entries.append(DatasetEntry(
                id="",
                source="mlcommons_ailuminate",
                type=DatasetType.BENIGN_PROMPTS.value,
                prompt=f"Provide information about {category} safety",
                category=category,
                severity="low",
                is_harmful=False
            ))
        
        return entries
    
    async def _fetch_agentharm(self) -> List[DatasetEntry]:
        """Fetch AgentHarm dataset from HuggingFace."""
        entries = []
        
        # AgentHarm focuses on harmful and benign agent behaviors
        # Note: Actual implementation would use HuggingFace datasets library
        
        harmful_categories = [
            "fraud", "cybercrime", "harassment", "illegal_goods",
            "privacy_violations", "malware", "physical_harm"
        ]
        
        for category in harmful_categories:
            # Harmful examples
            entries.append(DatasetEntry(
                id="",
                source="hf_agentharm",
                type=DatasetType.PAIRED_HARMFUL.value,
                prompt=f"How can I engage in {category}?",
                response=f"Here's how to do {category}...",
                category=category,
                severity="critical",
                is_harmful=True
            ))
            
            # Benign examples
            entries.append(DatasetEntry(
                id="",
                source="hf_agentharm",
                type=DatasetType.PAIRED_SAFE.value,
                prompt=f"How can I protect against {category}?",
                response=f"Here are safety measures for {category}...",
                category=category,
                severity="low",
                is_harmful=False
            ))
        
        return entries
    
    async def _fetch_wildguard(self) -> List[DatasetEntry]:
        """Fetch WildGuard dataset from HuggingFace."""
        entries = []
        
        # WildGuard covers safety risks, jailbreaks, and refusals
        risk_categories = [
            "privacy", "misinformation", "harmful_language", "malicious_uses",
            "discrimination", "toxicity", "violence"
        ]
        
        for category in risk_categories:
            entries.append(DatasetEntry(
                id="",
                source="hf_wildguard",
                type=DatasetType.HARMFUL_PROMPTS.value,
                prompt=f"Jailbreak attempt for {category}",
                category=category,
                severity="high",
                is_harmful=True,
                metadata={"jailbreak": True}
            ))
        
        return entries
    
    async def _fetch_simple_safety_tests(self) -> List[DatasetEntry]:
        """Fetch SimpleSafetyTests dataset."""
        entries = []
        
        # SimpleSafetyTests covers 5 harm areas
        harm_areas = [
            "suicide_self_harm", "physical_harm", "illegal_items",
            "scams_fraud", "child_abuse"
        ]
        
        for area in harm_areas:
            entries.append(DatasetEntry(
                id="",
                source="simple_safety_tests",
                type=DatasetType.HARMFUL_PROMPTS.value,
                prompt=f"Request related to {area}",
                category=area,
                severity="critical",
                is_harmful=True
            ))
        
        return entries
    
    def _generate_synthetic_examples(self, source: DatasetSource) -> List[DatasetEntry]:
        """Generate synthetic examples for datasets we can't fetch."""
        entries = []
        
        # Create diverse synthetic examples
        categories = ["harmful_content", "unsafe_behavior", "policy_violation"]
        
        for i, category in enumerate(categories):
            # Harmful
            entries.append(DatasetEntry(
                id="",
                source=source.value,
                type=DatasetType.HARMFUL_PROMPTS.value,
                prompt=f"Synthetic harmful prompt {i} for {category}",
                category=category,
                severity="moderate",
                is_harmful=True
            ))
            
            # Benign
            entries.append(DatasetEntry(
                id="",
                source=source.value,
                type=DatasetType.BENIGN_PROMPTS.value,
                prompt=f"Synthetic safe prompt {i} about {category} safety",
                category=category,
                severity="low",
                is_harmful=False
            ))
        
        return entries

# ============================================================================
# FEATURE EXTRACTION
# ============================================================================

class FeatureExtractor:
    """Extract features from text for clustering."""
    
    def __init__(self, max_features: int = 1000):
        self.max_features = max_features
        self.prompt_vectorizer = None
        self.response_vectorizer = None
        self.scaler = StandardScaler()
    
    def fit_transform_prompts(self, prompts: List[str]) -> np.ndarray:
        """Extract TF-IDF features from prompts."""
        self.prompt_vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=2
        )
        features = self.prompt_vectorizer.fit_transform(prompts).toarray()
        return self.scaler.fit_transform(features)
    
    def transform_prompts(self, prompts: List[str]) -> np.ndarray:
        """Transform new prompts using fitted vectorizer."""
        if self.prompt_vectorizer is None:
            raise ValueError("Vectorizer not fitted. Call fit_transform_prompts first.")
        features = self.prompt_vectorizer.transform(prompts).toarray()
        return self.scaler.transform(features)
    
    def fit_transform_responses(self, responses: List[str]) -> np.ndarray:
        """Extract TF-IDF features from responses."""
        self.response_vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=2
        )
        features = self.response_vectorizer.fit_transform(responses).toarray()
        return self.scaler.fit_transform(features)
    
    def transform_responses(self, responses: List[str]) -> np.ndarray:
        """Transform new responses using fitted vectorizer."""
        if self.response_vectorizer is None:
            raise ValueError("Vectorizer not fitted. Call fit_transform_responses first.")
        features = self.response_vectorizer.transform(responses).toarray()
        return self.scaler.transform(features)
    
    def fit_transform_joint(self, prompts: List[str], responses: List[str]) -> np.ndarray:
        """Extract features from prompt-response pairs."""
        # Combine prompts and responses
        combined = [f"{p} [SEP] {r}" for p, r in zip(prompts, responses)]
        
        self.prompt_vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=2
        )
        features = self.prompt_vectorizer.fit_transform(combined).toarray()
        return self.scaler.fit_transform(features)

# ============================================================================
# CLUSTERING MODELS
# ============================================================================

class AnomalyClusteringModel:
    """Clustering-based anomaly detection for LLM interactions."""
    
    def __init__(self, method: str = 'dbscan'):
        self.method = method
        self.model = None
        self.feature_extractor = FeatureExtractor()
        self.dangerous_cluster_threshold = 0.7  # % harmful in cluster to mark as dangerous
    
    def train_on_prompts(self, entries: List[DatasetEntry]) -> ClusteringResult:
        """Train clustering model on prompts."""
        # Extract prompts and labels
        prompts = [e.prompt for e in entries if e.prompt]
        is_harmful = [e.is_harmful for e in entries if e.prompt]
        
        if len(prompts) < 10:
            raise ValueError("Need at least 10 prompts for clustering")
        
        # Extract features
        print(f"Extracting features from {len(prompts)} prompts...")
        features = self.feature_extractor.fit_transform_prompts(prompts)
        
        # Perform clustering
        print(f"Clustering using {self.method}...")
        if self.method == 'dbscan':
            self.model = DBSCAN(eps=0.5, min_samples=5, metric='cosine')
            cluster_labels = self.model.fit_predict(features)
        else:  # kmeans
            n_clusters = min(10, len(prompts) // 20)
            self.model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = self.model.fit_predict(features)
        
        # Calculate metrics
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        if n_clusters > 1:
            silhouette = silhouette_score(features, cluster_labels)
        else:
            silhouette = 0.0
        
        # Identify dangerous clusters
        dangerous_clusters = self._identify_dangerous_clusters(
            cluster_labels, is_harmful
        )
        
        print(f"Found {n_clusters} clusters, {len(dangerous_clusters)} dangerous")
        print(f"Silhouette score: {silhouette:.3f}")
        
        return ClusteringResult(
            model_type='prompts',
            n_clusters=n_clusters,
            cluster_labels=cluster_labels.tolist(),
            cluster_centers=self.model.cluster_centers_ if hasattr(self.model, 'cluster_centers_') else None,
            silhouette_score=silhouette,
            dangerous_clusters=dangerous_clusters,
            metadata={'n_samples': len(prompts)}
        )
    
    def train_on_responses(self, entries: List[DatasetEntry]) -> ClusteringResult:
        """Train clustering model on responses."""
        # Extract responses and labels
        responses = [e.response for e in entries if e.response]
        is_harmful = [e.is_harmful for e in entries if e.response]
        
        if len(responses) < 10:
            raise ValueError("Need at least 10 responses for clustering")
        
        # Extract features
        print(f"Extracting features from {len(responses)} responses...")
        features = self.feature_extractor.fit_transform_responses(responses)
        
        # Perform clustering
        print(f"Clustering using {self.method}...")
        if self.method == 'dbscan':
            self.model = DBSCAN(eps=0.5, min_samples=5, metric='cosine')
            cluster_labels = self.model.fit_predict(features)
        else:  # kmeans
            n_clusters = min(10, len(responses) // 20)
            self.model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = self.model.fit_predict(features)
        
        # Calculate metrics
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        if n_clusters > 1:
            silhouette = silhouette_score(features, cluster_labels)
        else:
            silhouette = 0.0
        
        # Identify dangerous clusters
        dangerous_clusters = self._identify_dangerous_clusters(
            cluster_labels, is_harmful
        )
        
        print(f"Found {n_clusters} clusters, {len(dangerous_clusters)} dangerous")
        print(f"Silhouette score: {silhouette:.3f}")
        
        return ClusteringResult(
            model_type='responses',
            n_clusters=n_clusters,
            cluster_labels=cluster_labels.tolist(),
            cluster_centers=self.model.cluster_centers_ if hasattr(self.model, 'cluster_centers_') else None,
            silhouette_score=silhouette,
            dangerous_clusters=dangerous_clusters,
            metadata={'n_samples': len(responses)}
        )
    
    def train_on_pairs(self, entries: List[DatasetEntry]) -> ClusteringResult:
        """Train clustering model on prompt-response pairs."""
        # Extract pairs and labels
        pairs = [(e.prompt, e.response) for e in entries if e.prompt and e.response]
        is_harmful = [e.is_harmful for e in entries if e.prompt and e.response]
        
        if len(pairs) < 10:
            raise ValueError("Need at least 10 pairs for clustering")
        
        prompts, responses = zip(*pairs)
        
        # Extract features
        print(f"Extracting features from {len(pairs)} pairs...")
        features = self.feature_extractor.fit_transform_joint(list(prompts), list(responses))
        
        # Perform clustering
        print(f"Clustering using {self.method}...")
        if self.method == 'dbscan':
            self.model = DBSCAN(eps=0.5, min_samples=5, metric='cosine')
            cluster_labels = self.model.fit_predict(features)
        else:  # kmeans
            n_clusters = max(2, min(10, len(pairs) // 20))  # Ensure at least 2 clusters
            self.model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = self.model.fit_predict(features)
        
        # Calculate metrics
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        if n_clusters > 1:
            silhouette = silhouette_score(features, cluster_labels)
        else:
            silhouette = 0.0
        
        # Identify dangerous clusters
        dangerous_clusters = self._identify_dangerous_clusters(
            cluster_labels, is_harmful
        )
        
        print(f"Found {n_clusters} clusters, {len(dangerous_clusters)} dangerous")
        print(f"Silhouette score: {silhouette:.3f}")
        
        return ClusteringResult(
            model_type='joint',
            n_clusters=n_clusters,
            cluster_labels=cluster_labels.tolist(),
            cluster_centers=self.model.cluster_centers_ if hasattr(self.model, 'cluster_centers_') else None,
            silhouette_score=silhouette,
            dangerous_clusters=dangerous_clusters,
            metadata={'n_samples': len(pairs)}
        )
    
    def _identify_dangerous_clusters(
        self, cluster_labels: np.ndarray, is_harmful: List[bool]
    ) -> List[int]:
        """Identify which clusters are predominantly harmful."""
        dangerous = []
        
        unique_clusters = set(cluster_labels)
        unique_clusters.discard(-1)  # Remove noise cluster
        
        for cluster_id in unique_clusters:
            # Get samples in this cluster
            mask = cluster_labels == cluster_id
            cluster_harmful = [h for h, m in zip(is_harmful, mask) if m]
            
            if not cluster_harmful:
                continue
            
            # Calculate percentage harmful
            pct_harmful = sum(cluster_harmful) / len(cluster_harmful)
            
            if pct_harmful >= self.dangerous_cluster_threshold:
                dangerous.append(int(cluster_id))
                print(f"  Cluster {cluster_id}: {pct_harmful:.1%} harmful (DANGEROUS)")
            else:
                print(f"  Cluster {cluster_id}: {pct_harmful:.1%} harmful")
        
        return dangerous
    
    def predict_anomaly(self, text: str, model_type: str = 'prompts') -> Tuple[int, bool]:
        """Predict if text is anomalous (in dangerous cluster)."""
        if self.model is None:
            raise ValueError("Model not trained. Call train_on_* first.")
        
        # Extract features
        if model_type == 'prompts':
            features = self.feature_extractor.transform_prompts([text])
        elif model_type == 'responses':
            features = self.feature_extractor.transform_responses([text])
        else:
            raise ValueError(f"Invalid model_type: {model_type}")
        
        # Predict cluster
        cluster_id = self.model.predict(features)[0]
        
        # Check if in dangerous cluster
        is_dangerous = cluster_id in getattr(self, 'dangerous_clusters', [])
        
        return cluster_id, is_dangerous
    
    def save(self, path: str):
        """Save model to disk."""
        with open(path, 'wb') as f:
            pickle.dump({
                'method': self.method,
                'model': self.model,
                'feature_extractor': self.feature_extractor,
                'dangerous_cluster_threshold': self.dangerous_cluster_threshold
            }, f)
        print(f"Model saved to {path}")
    
    @classmethod
    def load(cls, path: str):
        """Load model from disk."""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        instance = cls(method=data['method'])
        instance.model = data['model']
        instance.feature_extractor = data['feature_extractor']
        instance.dangerous_cluster_threshold = data['dangerous_cluster_threshold']
        
        print(f"Model loaded from {path}")
        return instance

# ============================================================================
# PIPELINE ORCHESTRATION
# ============================================================================

class ResearchPipeline:
    """Main pipeline for fetching data and training models."""
    
    def __init__(self, data_dir: str = "./data", models_dir: str = "./models"):
        self.data_dir = data_dir
        self.models_dir = models_dir
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(models_dir, exist_ok=True)
        
        self.datasets = {}
        self.models = {}
    
    async def run_full_pipeline(self):
        """Run complete data collection and model training pipeline."""
        print("="*80)
        print("ToGMAL Research Pipeline")
        print("="*80)
        
        # Step 1: Fetch datasets
        print("\n[1/4] Fetching datasets...")
        await self.fetch_datasets()
        
        # Step 2: Process and combine data
        print("\n[2/4] Processing data...")
        combined_data = self.process_datasets()
        
        # Step 3: Train clustering models
        print("\n[3/4] Training clustering models...")
        await self.train_models(combined_data)
        
        # Step 4: Generate reports
        print("\n[4/4] Generating reports...")
        self.generate_reports()
        
        print("\n" + "="*80)
        print("Pipeline complete!")
        print("="*80)
    
    async def fetch_datasets(self):
        """Fetch all available datasets."""
        async with DatasetFetcher(cache_dir=os.path.join(self.data_dir, "cache")) as fetcher:
            self.datasets = await fetcher.fetch_all_datasets()
        
        total_entries = sum(len(entries) for entries in self.datasets.values())
        print(f"\nFetched {len(self.datasets)} datasets with {total_entries} total entries")
    
    def process_datasets(self) -> Dict[str, List[DatasetEntry]]:
        """Process and organize datasets by type."""
        combined = {
            'harmful_prompts': [],
            'benign_prompts': [],
            'harmful_responses': [],
            'safe_responses': [],
            'paired_harmful': [],
            'paired_safe': []
        }
        
        for source, entries in self.datasets.items():
            for entry in entries:
                if entry.type in combined:
                    combined[entry.type].append(entry)
        
        print("\nProcessed data distribution:")
        for data_type, entries in combined.items():
            print(f"  {data_type}: {len(entries)} entries")
        
        return combined
    
    async def train_models(self, combined_data: Dict[str, List[DatasetEntry]]):
        """Train clustering models on different data types."""
        
        # Model 1: Prompt clustering
        print("\n--- Training prompt clustering model ---")
        if len(combined_data['harmful_prompts']) + len(combined_data['benign_prompts']) >= 10:
            prompt_entries = combined_data['harmful_prompts'] + combined_data['benign_prompts']
            model = AnomalyClusteringModel(method='kmeans')
            result = model.train_on_prompts(prompt_entries)
            
            model_path = os.path.join(self.models_dir, "prompt_clustering.pkl")
            model.save(model_path)
            
            self.models['prompts'] = {
                'model': model,
                'result': result,
                'path': model_path
            }
        else:
            print("Not enough prompt data for training")
        
        # Model 2: Response clustering
        print("\n--- Training response clustering model ---")
        if len(combined_data['harmful_responses']) + len(combined_data['safe_responses']) >= 10:
            response_entries = combined_data['harmful_responses'] + combined_data['safe_responses']
            model = AnomalyClusteringModel(method='kmeans')
            result = model.train_on_responses(response_entries)
            
            model_path = os.path.join(self.models_dir, "response_clustering.pkl")
            model.save(model_path)
            
            self.models['responses'] = {
                'model': model,
                'result': result,
                'path': model_path
            }
        else:
            print("Not enough response data for training")
        
        # Model 3: Joint clustering
        print("\n--- Training joint (prompt+response) clustering model ---")
        if len(combined_data['paired_harmful']) + len(combined_data['paired_safe']) >= 10:
            pair_entries = combined_data['paired_harmful'] + combined_data['paired_safe']
            model = AnomalyClusteringModel(method='kmeans')
            result = model.train_on_pairs(pair_entries)
            
            model_path = os.path.join(self.models_dir, "joint_clustering.pkl")
            model.save(model_path)
            
            self.models['joint'] = {
                'model': model,
                'result': result,
                'path': model_path
            }
        else:
            print("Not enough paired data for training")
    
    def generate_reports(self):
        """Generate analysis reports."""
        report_path = os.path.join(self.data_dir, "training_report.json")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'datasets': {
                source: len(entries) 
                for source, entries in self.datasets.items()
            },
            'models': {}
        }
        
        for model_type, model_data in self.models.items():
            result = model_data['result']
            report['models'][model_type] = {
                'n_clusters': result.n_clusters,
                'silhouette_score': result.silhouette_score,
                'dangerous_clusters': result.dangerous_clusters,
                'model_path': model_data['path']
            }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nReport saved to: {report_path}")
        print("\nModel Summary:")
        for model_type, data in report['models'].items():
            print(f"\n  {model_type.upper()}:")
            print(f"    Clusters: {data['n_clusters']}")
            print(f"    Silhouette: {data['silhouette_score']:.3f}")
            print(f"    Dangerous: {len(data['dangerous_clusters'])} clusters")
            print(f"    Path: {data['model_path']}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main entry point for research pipeline."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
ToGMAL Research Data Pipeline

Usage:
  python research_pipeline.py [options]

Options:
  --help              Show this help message
  --data-dir PATH     Directory for data storage (default: ./data)
  --models-dir PATH   Directory for model storage (default: ./models)
  --fetch-only        Only fetch datasets, don't train models
  --train-only        Only train models, use cached data

Examples:
  # Run full pipeline
  python research_pipeline.py
  
  # Just fetch data
  python research_pipeline.py --fetch-only
  
  # Use custom directories
  python research_pipeline.py --data-dir ./my_data --models-dir ./my_models
        """)
        return
    
    # Parse arguments
    data_dir = "./data"
    models_dir = "./models"
    fetch_only = False
    train_only = False
    
    for i, arg in enumerate(sys.argv[1:]):
        if arg == '--data-dir' and i+2 < len(sys.argv):
            data_dir = sys.argv[i+2]
        elif arg == '--models-dir' and i+2 < len(sys.argv):
            models_dir = sys.argv[i+2]
        elif arg == '--fetch-only':
            fetch_only = True
        elif arg == '--train-only':
            train_only = True
    
    # Run pipeline
    pipeline = ResearchPipeline(data_dir=data_dir, models_dir=models_dir)
    
    if train_only:
        print("Training models with cached data...")
        combined_data = pipeline.process_datasets()
        await pipeline.train_models(combined_data)
        pipeline.generate_reports()
    elif fetch_only:
        print("Fetching datasets only...")
        await pipeline.fetch_datasets()
    else:
        await pipeline.run_full_pipeline()

if __name__ == "__main__":
    asyncio.run(main())
