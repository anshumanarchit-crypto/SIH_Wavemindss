"""
Classifier Adapter for SpectralQ.

Provides a decoupled interface to scikit-learn RandomForest classifiers:
- Validates feature names and deterministic ordering against the Phase 1 schema.
- Rejects missing required features.
- Preserves model_version and training metadata.
- Emits raw model probability strictly as 'ml_probability' (never 'final confidence').
- Distinctly separates raw ml_probability from calibrated_ml_probability (Phase 7).
- Tolerates sklearn version differences (not tied to specific internal private APIs).
"""

import os
import pickle
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import numpy as np

from spectralq.contracts.schemas import (
    AnalysisContract,
    ClassifierOutputContract,
    validate_classifier_output_dict,
)
from spectralq.hypothesis.registry import MODULATIONS


CANONICAL_FEATURE_NAMES: List[str] = [
    "C20",
    "C21",
    "C40",
    "C42",
    "C60",
    "C63",
    "C80",
    "cluster_count",
    "silhouette",
    "intra_var",
    "inter_dist",
    "evm",
    "phase_ambiguity_quality",
    "snr",
    "baud",
]


def extract_features_from_analysis(analysis: AnalysisContract) -> Dict[str, float]:
    """
    Extracts the canonical 15-dimensional feature dictionary from AnalysisContract.
    """
    feat = analysis.features
    est = analysis.estimates
    return {
        "C20": float(feat.cumulants.C20),
        "C21": float(feat.cumulants.C21),
        "C40": float(feat.cumulants.C40),
        "C42": float(feat.cumulants.C42),
        "C60": float(feat.cumulants.C60),
        "C63": float(feat.cumulants.C63),
        "C80": float(feat.cumulants.C80),
        "cluster_count": float(feat.cluster.count),
        "silhouette": float(feat.cluster.silhouette),
        "intra_var": float(feat.cluster.intra_var),
        "inter_dist": float(feat.cluster.inter_dist),
        "evm": float(feat.evm),
        "phase_ambiguity_quality": float(feat.phase_ambiguity_quality),
        "snr": float(est.snr.value),
        "baud": float(est.baud.value),
    }


class ClassifierAdapter:
    """
    Adapter wrapping scikit-learn RandomForest models.
    """

    def __init__(
        self,
        model: Optional[Any] = None,
        model_version: str = "rf-baseline-1.0.0",
        expected_features: Optional[List[str]] = None,
        classes: Optional[List[str]] = None,
        training_metadata: Optional[Dict[str, Any]] = None,
    ):
        self.model = model
        self.model_version = model_version
        self.classes = classes or list(MODULATIONS)
        self.training_metadata = training_metadata or {
            "framework": "scikit-learn",
            "classifier": "RandomForestClassifier",
            "training_dataset": "synthetic_sweep_v1",
        }

        # Determine feature names and ordering
        if expected_features is not None:
            self.expected_features = list(expected_features)
        elif model is not None and hasattr(model, "feature_names_in_"):
            self.expected_features = list(model.feature_names_in_)
        else:
            self.expected_features = list(CANONICAL_FEATURE_NAMES)

    @classmethod
    def load_from_file(
        cls,
        filepath: str,
        model_version: Optional[str] = None,
        training_metadata: Optional[Dict[str, Any]] = None,
    ) -> "ClassifierAdapter":
        """Loads a pickled/joblib model from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found at: {filepath}")

        # Try joblib if available, else standard pickle
        try:
            import joblib
            model = joblib.load(filepath)
        except Exception:
            with open(filepath, "rb") as f:
                model = pickle.load(f)

        version = model_version or getattr(model, "spectralq_version", "rf-loaded-1.0.0")
        return cls(model=model, model_version=version, training_metadata=training_metadata)

    def validate_features(self, features: Dict[str, float]) -> List[float]:
        """
        Validates presence and exact ordering of all required features.
        Returns the ordered numeric feature vector for model input.
        """
        missing = [f for f in self.expected_features if f not in features]
        if missing:
            raise ValueError(
                f"Missing required features for model {self.model_version}: {missing}. "
                f"Expected features: {self.expected_features}"
            )

        ordered_vector = [float(features[f]) for f in self.expected_features]
        return ordered_vector

    def predict(
        self,
        analysis_or_features: Union[AnalysisContract, Dict[str, float]],
        capture_id: str = "UNKNOWN_CAPTURE",
        window_id: Union[str, int] = 0,
    ) -> ClassifierOutputContract:
        """
        Executes prediction and returns a validated ClassifierOutputContract.
        Probability is strictly labeled ml_probability (never final confidence).
        """
        if isinstance(analysis_or_features, AnalysisContract):
            feat_dict = extract_features_from_analysis(analysis_or_features)
            cid = analysis_or_features.capture_id
        else:
            feat_dict = analysis_or_features
            cid = capture_id

        # Validate feature presence and ordering
        ordered_vec = self.validate_features(feat_dict)
        X = np.array([ordered_vec], dtype=np.float64)

        if self.model is not None and hasattr(self.model, "predict_proba"):
            raw_probs = self.model.predict_proba(X)[0]
            if hasattr(self.model, "classes_"):
                model_classes = list(self.model.classes_)
            else:
                model_classes = self.classes

            # Ensure all canonical modulations have an explicit probability
            prob_dict: Dict[str, float] = {}
            for cls_name in self.classes:
                if cls_name in model_classes:
                    idx = model_classes.index(cls_name)
                    prob_dict[cls_name] = float(raw_probs[idx])
                else:
                    prob_dict[cls_name] = 0.0

            # Normalize probabilities if sum > 0
            total_p = sum(prob_dict.values())
            if total_p > 0.0:
                prob_dict = {k: v / total_p for k, v in prob_dict.items()}

            top_class = max(prob_dict, key=prob_dict.get)
        else:
            # Deterministic mock/fallback if no external weights mounted
            prob_dict = self._deterministic_fallback_predict(feat_dict)
            top_class = max(prob_dict, key=prob_dict.get)

        raw_contract = {
            "schema_version": "1.0.0",
            "capture_id": cid,
            "window_id": window_id,
            "ml_prediction": top_class,
            "ml_probabilities": prob_dict,
            "calibrated_probability": None,  # Strictly None until Phase 7
            "model_version": self.model_version,
            "feature_vector_used": feat_dict,
        }
        return validate_classifier_output_dict(raw_contract)

    def _deterministic_fallback_predict(self, feat: Dict[str, float]) -> Dict[str, float]:
        """
        Heuristic fallback model approximating Harsh's trained RF behavior.
        Used for hermetic testing and offline validation before live model weights mount.
        """
        c20 = abs(feat.get("C20", 0.0))
        c21 = max(1e-9, abs(feat.get("C21", 1.0)))
        c40 = feat.get("C40", 0.0)
        c42 = feat.get("C42", -1.0)
        cluster_count = feat.get("cluster_count", 4)
        silhouette = feat.get("silhouette", 0.8)

        rho20 = c20 / c21
        rho40 = c40 / (c21 ** 2)

        # Baseline probability assignment
        probs = {m: 0.01 for m in self.classes}

        if rho20 > 0.60:
            probs["BPSK"] = 0.92
        elif silhouette < 0.40:
            if cluster_count <= 2:
                probs["2-FSK"] = 0.88
            else:
                probs["4-FSK"] = 0.86
        elif rho40 > 0.45:
            probs["QPSK"] = 0.89
        elif abs(rho40) <= 0.30 and abs(c42 / (c21**2)) >= 0.82:
            probs["8-PSK"] = 0.85
        elif cluster_count > 24:
            probs["64-QAM"] = 0.82
        else:
            probs["16-QAM"] = 0.84

        total = sum(probs.values())
        return {k: round(v / total, 4) for k, v in probs.items()}
