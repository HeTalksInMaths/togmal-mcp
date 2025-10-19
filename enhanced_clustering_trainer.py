"""
Enhanced Clustering Trainer with Sentence Transformers
Clusters datasets into GOOD, LIMITATIONS, and HARMFUL categories
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import pickle

import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.preprocessing import StandardScaler
from collections import Counter
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import sentence transformers
try:
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    logger.warning("sentence-transformers not installed. Install with: uv pip install sentence-transformers")
    HAS_TRANSFORMERS = False


@dataclass
class ClusterResult:
    """Result of clustering analysis"""
    cluster_id: int
    size: int
    
    # Cluster composition
    category_distribution: Dict[str, float]  # {good: 0.2, limitations: 0.8}
    domain_distribution: Dict[str, int]  # {mathematics: 50, medicine: 30}
    
    # Quality metrics
    purity: float  # Homogeneity of cluster (0-1)
    is_dangerous: bool  # True if >70% limitations or harmful
    
    # Representative examples
    examples: List[str]
    
    # Pattern description
    pattern_description: str
    detection_heuristic: str  # Rule for detecting this pattern
    
    # Top keywords
    keywords: List[str]


@dataclass
class TrainingResult:
    """Complete training results"""
    timestamp: str
    model_type: str  # "kmeans", "dbscan"
    embedding_model: str  # "all-MiniLM-L6-v2"
    
    # Metrics
    n_clusters: int
    silhouette_score: float
    davies_bouldin_score: float
    
    # Clusters
    clusters: List[ClusterResult]
    dangerous_clusters: List[ClusterResult]  # For ToGMAL tools
    
    # Paths
    model_path: str
    embeddings_path: str


class EnhancedClusteringTrainer:
    """
    Clustering trainer using sentence transformers
    Goal: Separate GOOD, LIMITATIONS, and HARMFUL clusters clearly
    """
    
    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        output_dir: Path = Path("./models/clustering")
    ):
        self.embedding_model_name = embedding_model
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if HAS_TRANSFORMERS:
            logger.info(f"Loading sentence transformer: {embedding_model}")
            self.embedder = SentenceTransformer(embedding_model)
        else:
            logger.error("sentence-transformers not available!")
            self.embedder = None
        
        self.dangerous_threshold = 0.7  # >70% limitations/harmful = dangerous
    
    async def train_clustering(
        self,
        dataset_entries: List[Dict[str, Any]],
        n_clusters: int = 3,
        method: str = "kmeans"
    ) -> TrainingResult:
        """
        Train clustering model
        
        Args:
            dataset_entries: List of {text, cluster_category, domain, source}
            n_clusters: Number of clusters (3 = good, limitations, harmful)
            method: "kmeans" or "dbscan"
        
        Returns:
            TrainingResult with clusters and metrics
        """
        
        if not self.embedder:
            raise RuntimeError("Sentence transformers not available")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Training {method.upper()} Clustering")
        logger.info(f"{'='*60}")
        
        # Extract texts and labels
        texts = [entry['text'] for entry in dataset_entries]
        true_categories = [entry['cluster_category'] for entry in dataset_entries]
        domains = [entry['domain'] for entry in dataset_entries]
        
        logger.info(f"Total samples: {len(texts)}")
        logger.info(f"Categories: {Counter(true_categories)}")
        logger.info(f"Domains: {Counter(domains)}")
        
        # Generate embeddings
        logger.info("\n[1/4] Generating embeddings with sentence transformers...")
        embeddings = await self._generate_embeddings(texts)
        
        # Standardize
        logger.info("[2/4] Standardizing embeddings...")
        scaler = StandardScaler()
        embeddings_scaled = scaler.fit_transform(embeddings)
        
        # Perform clustering
        logger.info(f"[3/4] Clustering with {method}...")
        if method == "kmeans":
            model, labels = self._cluster_kmeans(embeddings_scaled, n_clusters)
        else:  # dbscan
            model, labels = self._cluster_dbscan(embeddings_scaled)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        
        # Calculate metrics
        logger.info("[4/4] Analyzing clusters...")
        silhouette = silhouette_score(embeddings_scaled, labels) if len(set(labels)) > 1 else 0.0
        davies_bouldin = davies_bouldin_score(embeddings_scaled, labels) if len(set(labels)) > 1 else 999.0
        
        logger.info(f"\nMetrics:")
        logger.info(f"  Clusters: {n_clusters}")
        logger.info(f"  Silhouette Score: {silhouette:.4f}")
        logger.info(f"  Davies-Bouldin Score: {davies_bouldin:.4f}")
        
        # Analyze clusters
        clusters = self._analyze_clusters(
            labels, texts, true_categories, domains, dataset_entries
        )
        
        # Identify dangerous clusters
        dangerous_clusters = [c for c in clusters if c.is_dangerous]
        
        logger.info(f"\nDangerous clusters: {len(dangerous_clusters)}/{n_clusters}")
        
        # Save model
        model_path = self.output_dir / f"{method}_model.pkl"
        self._save_model(model, scaler, model_path, clusters)
        
        # Save embeddings
        embeddings_path = self.output_dir / "embeddings.npy"
        np.save(embeddings_path, embeddings)
        
        return TrainingResult(
            timestamp=datetime.now().isoformat(),
            model_type=method,
            embedding_model=self.embedding_model_name,
            n_clusters=n_clusters,
            silhouette_score=silhouette,
            davies_bouldin_score=davies_bouldin,
            clusters=clusters,
            dangerous_clusters=dangerous_clusters,
            model_path=str(model_path),
            embeddings_path=str(embeddings_path)
        )
    
    async def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using sentence transformers"""
        
        embeddings = self.embedder.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # Important for cosine similarity
        )
        
        logger.info(f"Generated embeddings: {embeddings.shape}")
        return embeddings
    
    def _cluster_kmeans(
        self, embeddings: np.ndarray, n_clusters: int
    ) -> Tuple[KMeans, np.ndarray]:
        """Perform K-Means clustering"""
        
        model = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=20,  # More initializations for better results
            max_iter=500
        )
        labels = model.fit_predict(embeddings)
        
        return model, labels
    
    def _cluster_dbscan(
        self, embeddings: np.ndarray, eps: float = 0.5, min_samples: int = 10
    ) -> Tuple[DBSCAN, np.ndarray]:
        """Perform DBSCAN clustering"""
        
        model = DBSCAN(
            eps=eps,
            min_samples=min_samples,
            metric='cosine',
            n_jobs=-1
        )
        labels = model.fit_predict(embeddings)
        
        n_noise = np.sum(labels == -1)
        logger.info(f"  DBSCAN noise points: {n_noise}")
        
        return model, labels
    
    def _analyze_clusters(
        self,
        labels: np.ndarray,
        texts: List[str],
        true_categories: List[str],
        domains: List[str],
        entries: List[Dict[str, Any]]
    ) -> List[ClusterResult]:
        """Analyze cluster composition and identify patterns"""
        
        clusters = []
        
        for cluster_id in set(labels):
            if cluster_id == -1:  # Skip noise in DBSCAN
                continue
            
            # Get cluster members
            mask = labels == cluster_id
            cluster_texts = [t for t, m in zip(texts, mask) if m]
            cluster_categories = [c for c, m in zip(true_categories, mask) if m]
            cluster_domains = [d for d, m in zip(domains, mask) if m]
            
            # Category distribution
            category_counts = Counter(cluster_categories)
            total = len(cluster_categories)
            category_dist = {cat: count/total for cat, count in category_counts.items()}
            
            # Domain distribution
            domain_dist = dict(Counter(cluster_domains))
            
            # Calculate purity (max category %)
            purity = max(category_dist.values()) if category_dist else 0.0
            
            # Is this dangerous? (>70% limitations or harmful)
            limitations_harmful_pct = (
                category_dist.get('limitations', 0.0) + 
                category_dist.get('harmful', 0.0)
            )
            is_dangerous = limitations_harmful_pct > self.dangerous_threshold
            
            # Extract keywords
            keywords = self._extract_keywords(cluster_texts)
            
            # Generate pattern description
            primary_category = max(category_dist, key=category_dist.get)
            primary_domain = max(domain_dist, key=domain_dist.get)
            
            pattern_desc = f"{primary_category.upper()} cluster: {primary_domain}"
            if is_dangerous:
                pattern_desc += f" (DANGEROUS: {limitations_harmful_pct:.1%} limitations/harmful)"
            
            # Generate detection heuristic
            heuristic = self._generate_heuristic(
                primary_category, primary_domain, keywords
            )
            
            # Representative examples
            examples = cluster_texts[:5]
            
            cluster_result = ClusterResult(
                cluster_id=int(cluster_id),
                size=len(cluster_texts),
                category_distribution=category_dist,
                domain_distribution=domain_dist,
                purity=float(purity),
                is_dangerous=is_dangerous,
                examples=examples,
                pattern_description=pattern_desc,
                detection_heuristic=heuristic,
                keywords=keywords
            )
            
            clusters.append(cluster_result)
            
            # Log cluster info
            logger.info(f"\nCluster {cluster_id}:")
            logger.info(f"  Size: {len(cluster_texts)}")
            logger.info(f"  Purity: {purity:.1%}")
            logger.info(f"  Categories: {category_dist}")
            logger.info(f"  Dangerous: {is_dangerous}")
            logger.info(f"  Pattern: {pattern_desc}")
        
        return clusters
    
    def _extract_keywords(self, texts: List[str], top_n: int = 10) -> List[str]:
        """Extract common keywords from cluster texts"""
        
        all_text = " ".join(texts).lower()
        words = re.findall(r'\b[a-z]{4,}\b', all_text)
        
        # Remove common words
        stopwords = {'this', 'that', 'with', 'from', 'have', 'what', 'which', 'would', 'could', 'should'}
        words = [w for w in words if w not in stopwords]
        
        word_counts = Counter(words)
        return [word for word, count in word_counts.most_common(top_n)]
    
    def _generate_heuristic(
        self, category: str, domain: str, keywords: List[str]
    ) -> str:
        """Generate detection heuristic for this cluster"""
        
        if category == "limitations":
            if domain == "mathematics":
                return "keyword_match: [integral, proof, theorem, equation] OR complexity_score > 0.7"
            elif domain == "medicine":
                return f"keyword_match: {keywords[:5]} AND domain=medicine"
            elif domain == "coding":
                return "contains_code AND (has_vulnerability OR cyclomatic_complexity > 10)"
            else:
                return f"keyword_match: {keywords[:5]}"
        
        elif category == "harmful":
            return f"safety_filter_trigger OR keyword_match: {keywords[:5]}"
        
        else:  # good
            return f"domain={domain} AND low_complexity"
    
    def _save_model(
        self, model: Any, scaler: StandardScaler, path: Path, clusters: List[ClusterResult]
    ):
        """Save model with metadata"""
        
        model_data = {
            'model': model,
            'scaler': scaler,
            'clusters': [asdict(c) for c in clusters],
            'dangerous_clusters': [c.cluster_id for c in clusters if c.is_dangerous],
            'timestamp': datetime.now().isoformat(),
            'embedding_model': self.embedding_model_name
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"\n✓ Model saved to {path}")


async def main():
    """Main training pipeline"""
    
    # Load dataset
    dataset_path = Path("./data/datasets/combined_dataset.json")
    
    if not dataset_path.exists():
        logger.error(f"Dataset not found: {dataset_path}")
        logger.info("Run enhanced_dataset_fetcher.py first!")
        return
    
    logger.info(f"Loading dataset from {dataset_path}")
    with open(dataset_path, 'r') as f:
        data = json.load(f)
    
    # Flatten all entries
    all_entries = []
    for category, entries in data['categories'].items():
        all_entries.extend(entries)
    
    logger.info(f"Loaded {len(all_entries)} entries")
    logger.info(f"Summary: {data['summary']}")
    
    # Train clustering
    trainer = EnhancedClusteringTrainer()
    
    # Try K-Means with 3 clusters (good, limitations, harmful)
    result = await trainer.train_clustering(all_entries, n_clusters=3, method="kmeans")
    
    # Save results
    results_path = Path("./data/training_results.json")
    with open(results_path, 'w') as f:
        json.dump({
            **asdict(result),
            'clusters': [asdict(c) for c in result.clusters],
            'dangerous_clusters': [asdict(c) for c in result.dangerous_clusters]
        }, f, indent=2)
    
    logger.info(f"\n✓ Results saved to {results_path}")
    
    # Export to ToGMAL ML tools cache
    await export_to_ml_tools_cache(result)


async def export_to_ml_tools_cache(result: TrainingResult):
    """Export dangerous clusters to ToGMAL ML tools cache"""
    
    patterns = []
    
    for cluster in result.dangerous_clusters:
        # Extract primary domain
        primary_domain = max(cluster.domain_distribution, key=cluster.domain_distribution.get)
        
        pattern = {
            "id": f"cluster_{cluster.cluster_id}",
            "domain": primary_domain,
            "description": cluster.pattern_description,
            "confidence": float(cluster.purity),
            "heuristic": cluster.detection_heuristic,
            "examples": cluster.examples[:3],
            "keywords": cluster.keywords,
            "metadata": {
                "cluster_size": cluster.size,
                "category_distribution": cluster.category_distribution,
                "discovered_at": result.timestamp
            }
        }
        patterns.append(pattern)
    
    # Save to ML tools cache
    ml_tools_cache = {
        "updated_at": result.timestamp,
        "patterns": patterns,
        "metadata": {
            "embedding_model": result.embedding_model,
            "silhouette_score": result.silhouette_score,
            "n_clusters": result.n_clusters,
            "total_patterns": len(patterns)
        }
    }
    
    cache_path = Path("./data/ml_discovered_tools.json")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(cache_path, 'w') as f:
        json.dump(ml_tools_cache, f, indent=2)
    
    logger.info(f"\n✓ Exported {len(patterns)} patterns to {cache_path}")
    logger.info("\nDangerous patterns discovered:")
    for pattern in patterns:
        logger.info(f"  - {pattern['domain']}: {pattern['description']}")


if __name__ == "__main__":
    asyncio.run(main())
