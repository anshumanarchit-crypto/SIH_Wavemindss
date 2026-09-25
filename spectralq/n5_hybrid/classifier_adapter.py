"""
Adapter for Harsh's Baseline Classifier (RandomForest / GMM).
Extracts signal-derived features only (cumulants, SNR, cluster stats, envelope, EVM)
and interfaces with trained scikit-learn models.
"""

from typing import Dict, List, Optional
import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV

from spectralq.contracts.schemas import AnalysisContract, ClassifierOutputContract

FEATURE_NAMES = [
    "C20", "C21", "C40", "C42", "C60", "C63", "C80",
    "snr_m2m4_db",
    "envelope_variance",
    "phase_entropy",
    "cluster_count",
    "silhouette_score",
    "intra_cluster_dist",
    "inter_cluster_dist",
    "cluster_count_stability",
    "evm",
    "phase_ambiguity_quality"
]

CLASSES = ["BPSK", "QPSK", "8-PSK", "16-QAM", "64-QAM", "2-FSK", "4-FSK"]


def extract_feature_vector(analysis: AnalysisContract) -> Dict[str, float]:
    """
    Extracts strictly signal-derived scalar features from AnalysisContract.
    """
    c = analysis.cumulants
    cl = analysis.cluster_metrics
    return {
        "C20": float(c.C20),
        "C21": float(c.C21),
        "C40": float(c.C40),
        "C42": float(c.C42),
        "C60": float(c.C60),
        "C63": float(c.C63),
        "C80": float(c.C80),
        "snr_m2m4_db": float(analysis.snr_m2m4_db),
        "envelope_variance": float(analysis.envelope_variance),
        "phase_entropy": float(analysis.phase_entropy),
        "cluster_count": float(cl.cluster_count),
        "silhouette_score": float(cl.silhouette_score),
        "intra_cluster_dist": float(cl.intra_cluster_dist),
        "inter_cluster_dist": float(cl.inter_cluster_dist),
        "cluster_count_stability": float(cl.cluster_count_stability),
        "evm": float(analysis.evm),
        "phase_ambiguity_quality": float(analysis.phase_ambiguity_quality),
    }


def feature_dict_to_array(features: Dict[str, float]) -> np.ndarray:
    """
    Converts feature dictionary to ordered numpy array.
    """
    return np.array([features[k] for k in FEATURE_NAMES], dtype=np.float32).reshape(1, -1)


class ClassifierAdapter:
    """
    Integrates Harsh's RandomForest classifier into SpectralQ.
    """

    def __init__(self, model_path: Optional[str] = None, seed: int = 42):
        self.seed = seed
        self.model_path = model_path
        self.model = None
        self.is_synthetic_model = False

        if model_path and os.path.exists(model_path):
            self.model = joblib.load(model_path)
            self.is_synthetic_model = False
        else:
            # Initialize a calibrated baseline model for deterministic offline testing
            self.model = self._create_baseline_calibrated_model(seed=self.seed)
            self.is_synthetic_model = True

    def _create_baseline_calibrated_model(self, seed: int = 42) -> CalibratedClassifierCV:
        """
        Creates and fits a deterministic baseline RandomForest model with calibration.
        Used as default when external model artifact is not loaded.
        """
        rng = np.random.RandomState(seed)
        n_samples_per_class = 60
        X_list = []
        y_list = []

        # Generate synthetic feature samples reflecting physical characteristics
        for cls_name in CLASSES:
            for _ in range(n_samples_per_class):
                snr = rng.uniform(5.0, 30.0)
                noise_scale = 1.0 / (10.0 ** (snr / 20.0))

                if cls_name == "BPSK":
                    c20 = 1.0 + rng.normal(0, 0.1 * noise_scale)
                    c40 = -2.0 + rng.normal(0, 0.2 * noise_scale)
                    c42 = -2.0 + rng.normal(0, 0.2 * noise_scale)
                    env_var = 0.05 + rng.normal(0, 0.02)
                    clusters = 2.0
                elif cls_name == "QPSK":
                    c20 = 0.0 + rng.normal(0, 0.05 * noise_scale)
                    c40 = 1.0 + rng.normal(0, 0.15 * noise_scale)
                    c42 = -1.0 + rng.normal(0, 0.15 * noise_scale)
                    env_var = 0.05 + rng.normal(0, 0.02)
                    clusters = 4.0
                elif cls_name == "8-PSK":
                    c20 = 0.0 + rng.normal(0, 0.05 * noise_scale)
                    c40 = 0.0 + rng.normal(0, 0.1 * noise_scale)
                    c42 = -1.0 + rng.normal(0, 0.15 * noise_scale)
                    env_var = 0.06 + rng.normal(0, 0.02)
                    clusters = 8.0
                elif cls_name == "16-QAM":
                    c20 = 0.0 + rng.normal(0, 0.05 * noise_scale)
                    c40 = -0.68 + rng.normal(0, 0.1 * noise_scale)
                    c42 = -0.68 + rng.normal(0, 0.1 * noise_scale)
                    env_var = 0.15 + rng.normal(0, 0.03)
                    clusters = 16.0
                elif cls_name == "64-QAM":
                    c20 = 0.0 + rng.normal(0, 0.05 * noise_scale)
                    c40 = -0.619 + rng.normal(0, 0.1 * noise_scale)
                    c42 = -0.619 + rng.normal(0, 0.1 * noise_scale)
                    env_var = 0.18 + rng.normal(0, 0.03)
                    clusters = 64.0
                elif cls_name == "2-FSK":
                    c20 = 0.0 + rng.normal(0, 0.05)
                    c40 = 0.0 + rng.normal(0, 0.1)
                    c42 = -1.0 + rng.normal(0, 0.1)
                    env_var = 0.45 + rng.normal(0, 0.05)
                    clusters = 2.0
                else:  # 4-FSK
                    c20 = 0.0 + rng.normal(0, 0.05)
                    c40 = 0.0 + rng.normal(0, 0.1)
                    c42 = -1.0 + rng.normal(0, 0.1)
                    env_var = 0.50 + rng.normal(0, 0.05)
                    clusters = 4.0

                feat = [
                    c20, 1.0, c40, c42,
                    0.0, 0.0, 0.0,
                    snr,
                    max(0.01, env_var),
                    rng.uniform(0.8, 1.5),
                    clusters,
                    rng.uniform(0.6, 0.95),
                    rng.uniform(0.05, 0.2),
                    rng.uniform(0.5, 1.2),
                    rng.uniform(0.85, 1.0),
                    rng.uniform(0.02, 0.15) * (1.0 + noise_scale),
                    rng.uniform(0.8, 1.0)
                ]
                X_list.append(feat)
                y_list.append(cls_name)

        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list)

        base_rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=12,
            random_state=seed,
            class_weight="balanced"
        )

        calibrated = CalibratedClassifierCV(estimator=base_rf, method="sigmoid", cv=3)
        calibrated.fit(X, y)
        return calibrated

    def predict(self, analysis: AnalysisContract) -> ClassifierOutputContract:
        """
        Executes prediction and probability estimation on an AnalysisContract.
        """
        features_dict = extract_feature_vector(analysis)
        X = feature_dict_to_array(features_dict)

        probs = self.model.predict_proba(X)[0]
        classes = self.model.classes_

        prob_dict = {str(c): float(p) for c, p in zip(classes, probs)}
        top_class = max(prob_dict, key=prob_dict.get)

        return ClassifierOutputContract(
            predicted_class=top_class,
            class_probabilities=prob_dict,
            feature_vector=features_dict,
            model_name="RandomForest_Baseline",
            model_version="1.0.0",
            is_synthetic_model=self.is_synthetic_model,
        )
