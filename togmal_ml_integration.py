"""
ToGMAL + ML Integration

This module integrates the clustering-based anomaly detection models
with the ToGMAL MCP server, enabling ML-enhanced safety detection.
"""

import os
import pickle
from typing import Dict, Any, Tuple, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    import numpy as np
try:
    import numpy as np
except Exception as e:
    raise RuntimeError("Required ML dependencies missing. Please install: numpy, scikit-learn") from e

# ============================================================================
# ML-ENHANCED DETECTION
# ============================================================================

class MLEnhancedDetector:
    """
    Wrapper for clustering models that can be used alongside heuristic detection.
    """
    
    def __init__(self, models_dir: str = "./models"):
        self.models_dir = models_dir
        self.prompt_model = None
        self.response_model = None
        self.joint_model = None
        self._loaded = False
    
    def load_models(self):
        """Load all available trained models."""
        try:
            # Load prompt clustering model
            prompt_path = os.path.join(self.models_dir, "prompt_clustering.pkl")
            if os.path.exists(prompt_path):
                with open(prompt_path, 'rb') as f:
                    data = pickle.load(f)
                    self.prompt_model = {
                        'model': data['model'],
                        'feature_extractor': data['feature_extractor'],
                        'dangerous_clusters': getattr(data.get('model'), 'dangerous_clusters_', [])
                    }
                print(f"✓ Loaded prompt clustering model from {prompt_path}")
            
            # Load joint clustering model
            joint_path = os.path.join(self.models_dir, "joint_clustering.pkl")
            if os.path.exists(joint_path):
                with open(joint_path, 'rb') as f:
                    data = pickle.load(f)
                    self.joint_model = {
                        'model': data['model'],
                        'feature_extractor': data['feature_extractor'],
                        'dangerous_clusters': getattr(data.get('model'), 'dangerous_clusters_', [])
                    }
                print(f"✓ Loaded joint clustering model from {joint_path}")
            
            self._loaded = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to load models: {e}")
            return False
    
    def analyze_prompt_ml(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze a prompt using ML clustering model.
        
        Returns:
            dict with keys:
                - detected: bool
                - cluster_id: int
                - is_dangerous_cluster: bool
                - confidence: float
                - method: str = 'ml_clustering'
        """
        if not self._loaded or self.prompt_model is None:
            return {
                'detected': False,
                'cluster_id': -1,
                'is_dangerous_cluster': False,
                'confidence': 0.0,
                'method': 'ml_clustering_unavailable'
            }
        
        try:
            # Extract features
            feature_extractor = self.prompt_model['feature_extractor']
            features = feature_extractor.transform_prompts([prompt])
            
            # Predict cluster
            model = self.prompt_model['model']
            cluster_id = model.predict(features)[0]
            
            # Check if dangerous
            # Note: We need to recover dangerous clusters from training
            # For now, use distance to cluster center as proxy
            if hasattr(model, 'cluster_centers_'):
                distances = np.linalg.norm(
                    model.cluster_centers_ - features, axis=1
                )
                closest_dangerous = min(
                    [d for i, d in enumerate(distances) if i in [1, 2]],  # From training: clusters 1,2 are dangerous
                    default=float('inf')
                )
                is_dangerous = closest_dangerous < 1.0  # Threshold
                confidence = 1.0 - min(closest_dangerous / 2.0, 1.0)
            else:
                is_dangerous = False
                confidence = 0.0
            
            return {
                'detected': is_dangerous,
                'cluster_id': int(cluster_id),
                'is_dangerous_cluster': is_dangerous,
                'confidence': float(confidence),
                'method': 'ml_clustering'
            }
            
        except Exception as e:
            print(f"ML analysis error: {e}")
            return {
                'detected': False,
                'cluster_id': -1,
                'is_dangerous_cluster': False,
                'confidence': 0.0,
                'method': 'ml_clustering_error',
                'error': str(e)
            }
    
    def analyze_pair_ml(self, prompt: str, response: str) -> Dict[str, Any]:
        """
        Analyze a prompt-response pair using ML clustering model.
        """
        if not self._loaded or self.joint_model is None:
            return {
                'detected': False,
                'cluster_id': -1,
                'is_dangerous_cluster': False,
                'confidence': 0.0,
                'method': 'ml_clustering_unavailable'
            }
        
        try:
            # Extract features from combined text
            combined = f"{prompt} [SEP] {response}"
            feature_extractor = self.joint_model['feature_extractor']
            features = feature_extractor.prompt_vectorizer.transform([combined]).toarray()
            features = feature_extractor.scaler.transform(features)
            
            # Predict cluster
            model = self.joint_model['model']
            cluster_id = model.predict(features)[0]
            
            # Check if dangerous (cluster 0 was dangerous in training)
            if hasattr(model, 'cluster_centers_'):
                distances = np.linalg.norm(
                    model.cluster_centers_ - features, axis=1
                )
                # Cluster 0 is dangerous from training
                closest_dangerous = distances[0]
                is_dangerous = closest_dangerous < 1.0
                confidence = 1.0 - min(closest_dangerous / 2.0, 1.0)
            else:
                is_dangerous = False
                confidence = 0.0
            
            return {
                'detected': is_dangerous,
                'cluster_id': int(cluster_id),
                'is_dangerous_cluster': is_dangerous,
                'confidence': float(confidence),
                'method': 'ml_clustering'
            }
            
        except Exception as e:
            print(f"ML analysis error: {e}")
            return {
                'detected': False,
                'cluster_id': -1,
                'is_dangerous_cluster': False,
                'confidence': 0.0,
                'method': 'ml_clustering_error',
                'error': str(e)
            }

# ============================================================================
# HYBRID DETECTION (Heuristics + ML)
# ============================================================================

def combine_detections(
    heuristic_results: Dict[str, Any],
    ml_results: Dict[str, Any],
    weight_heuristic: float = 0.7,
    weight_ml: float = 0.3
) -> Dict[str, Any]:
    """
    Combine heuristic and ML detection results.
    
    Args:
        heuristic_results: Results from heuristic detection (ToGMAL)
        ml_results: Results from ML clustering
        weight_heuristic: Weight for heuristic confidence (0-1)
        weight_ml: Weight for ML confidence (0-1)
    
    Returns:
        Combined detection result with ensemble confidence
    """
    # Normalize weights
    total_weight = weight_heuristic + weight_ml
    weight_heuristic /= total_weight
    weight_ml /= total_weight
    
    # Extract confidences
    heuristic_conf = heuristic_results.get('confidence', 0.0)
    ml_conf = ml_results.get('confidence', 0.0)
    
    # Combine confidences
    combined_confidence = (
        weight_heuristic * heuristic_conf +
        weight_ml * ml_conf
    )
    
    # Logical OR for detection (if either detects, flag it)
    combined_detected = (
        heuristic_results.get('detected', False) or
        ml_results.get('detected', False)
    )
    
    # Aggregate categories
    combined_categories = list(set(
        heuristic_results.get('categories', []) +
        ([ml_results.get('method', '')] if ml_results.get('detected') else [])
    ))
    
    return {
        'detected': combined_detected,
        'confidence': combined_confidence,
        'categories': combined_categories,
        'heuristic_confidence': heuristic_conf,
        'ml_confidence': ml_conf,
        'ml_cluster_id': ml_results.get('cluster_id', -1),
        'method': 'hybrid_ensemble'
    }

# ============================================================================
# INTEGRATION WITH ToGMAL
# ============================================================================

# Global ML detector instance (lazy loaded)
_ml_detector: Optional[MLEnhancedDetector] = None

def get_ml_detector(models_dir: str = "./models") -> MLEnhancedDetector:
    """Get or create ML detector instance."""
    global _ml_detector
    if _ml_detector is None:
        _ml_detector = MLEnhancedDetector(models_dir)
        _ml_detector.load_models()
    return _ml_detector
