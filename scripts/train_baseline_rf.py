import os
import sys
from pathlib import Path

# Add repo root to sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from spectralq.integration.classifier_adapter import CANONICAL_FEATURE_NAMES
from spectralq.hypothesis.registry import MODULATIONS
from spectralq.features.iq_extractor import iq_to_analysis_contract
from tests.test_spectralq_extended_suite import synth_capture

CLASSES = list(MODULATIONS)


def generate_feature_dataset(n_samples_per_class: int = 400, seed: int = 42):
    rng = np.random.RandomState(seed)
    X_list = []
    y_list = []

    # 1. Direct Signal Extraction for Grounded Training Features
    print("Generating grounded training signals...")
    mod_map = {
        "BPSK": "BPSK",
        "QPSK": "QPSK",
        "8-PSK": "8PSK",
        "16-QAM": "16QAM",
        "64-QAM": "64QAM",
        "2-FSK": "2FSK",
        "4-FSK": "4FSK",
    }
    for cls_name in CLASSES:
        synth_mod = mod_map[cls_name]
        for s in range(25):
            snr_val = float(rng.uniform(8.0, 30.0))
            iq_sig, truth_meta = synth_capture(synth_mod, snr_db=snr_val, seed=seed * 1000 + s)
            analysis = iq_to_analysis_contract(iq_sig, truth_meta["fs_hz"])
            feat_dict = {
                "C20": float(analysis.features.cumulants.C20),
                "C21": float(analysis.features.cumulants.C21),
                "C40": float(analysis.features.cumulants.C40),
                "C42": float(analysis.features.cumulants.C42),
                "C60": float(analysis.features.cumulants.C60),
                "C63": float(analysis.features.cumulants.C63),
                "C80": float(analysis.features.cumulants.C80),
                "cluster_count": float(analysis.features.cluster.count),
                "silhouette": float(analysis.features.cluster.silhouette),
                "intra_var": float(analysis.features.cluster.intra_var),
                "inter_dist": float(analysis.features.cluster.inter_dist),
                "evm": float(analysis.features.evm),
                "phase_ambiguity_quality": float(analysis.features.phase_ambiguity_quality or 0.8),
                "snr": float(analysis.estimates.snr.value),
                "baud": float(analysis.estimates.baud.value),
            }
            feat = [feat_dict[f] for f in CANONICAL_FEATURE_NAMES]
            X_list.append(feat)
            y_list.append(cls_name)

    # 2. Augmented Feature Vectors Matching Physical Invariants
    for cls_name in CLASSES:
        for _ in range(n_samples_per_class):
            snr = rng.uniform(4.0, 32.0)
            noise_scale = 1.0 / (10.0 ** (snr / 20.0))

            if cls_name == "BPSK":
                c20 = 1.0 + rng.normal(0, 0.08 * noise_scale)
                c40 = 2.0 + rng.normal(0, 0.15 * noise_scale)
                c42 = -2.0 + rng.normal(0, 0.15 * noise_scale)
                clusters = 2.0
                silhouette = rng.uniform(0.85, 0.98)
                evm = rng.uniform(0.02, 0.12) * (1.0 + noise_scale)
                phase_q = rng.uniform(0.85, 1.0)
            elif cls_name == "QPSK":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = 1.0 + rng.normal(0, 0.10 * noise_scale)
                c42 = -1.0 + rng.normal(0, 0.10 * noise_scale)
                clusters = rng.choice([4.0, 8.0], p=[0.8, 0.2])
                silhouette = rng.uniform(0.75, 0.95)
                evm = rng.uniform(0.03, 0.15) * (1.0 + noise_scale)
                phase_q = rng.uniform(0.8, 1.0)
            elif cls_name == "8-PSK":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = 0.0 + rng.normal(0, 0.08 * noise_scale)
                c42 = -1.0 + rng.normal(0, 0.10 * noise_scale)
                clusters = rng.choice([8.0, 4.0], p=[0.85, 0.15])
                silhouette = rng.uniform(0.65, 0.90)
                evm = rng.uniform(0.04, 0.18) * (1.0 + noise_scale)
                phase_q = rng.uniform(0.75, 0.95)
            elif cls_name == "16-QAM":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = 0.68 + rng.normal(0, 0.08 * noise_scale)
                c42 = -0.68 + rng.normal(0, 0.08 * noise_scale)
                clusters = rng.choice([16.0, 8.0, 4.0], p=[0.6, 0.25, 0.15])
                silhouette = rng.uniform(0.55, 0.85)
                evm = rng.uniform(0.05, 0.20) * (1.0 + noise_scale)
                phase_q = rng.uniform(0.7, 0.9)
            elif cls_name == "64-QAM":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = 0.619 + rng.normal(0, 0.08 * noise_scale)
                c42 = -0.619 + rng.normal(0, 0.08 * noise_scale)
                clusters = rng.choice([64.0, 16.0, 8.0, 4.0], p=[0.4, 0.3, 0.2, 0.1])
                silhouette = rng.uniform(0.50, 0.80)
                evm = rng.uniform(0.06, 0.22) * (1.0 + noise_scale)
                phase_q = rng.uniform(0.65, 0.85)
            elif cls_name == "2-FSK":
                c20 = 0.0 + rng.normal(0, 0.04)
                c40 = 0.0 + rng.normal(0, 0.08)
                c42 = -1.0 + rng.normal(0, 0.08)
                clusters = 2.0
                silhouette = rng.uniform(0.15, 0.35)
                evm = rng.uniform(0.6, 1.2)
                phase_q = rng.uniform(0.1, 0.4)
            else:  # 4-FSK
                c20 = 0.0 + rng.normal(0, 0.04)
                c40 = 0.0 + rng.normal(0, 0.08)
                c42 = -1.0 + rng.normal(0, 0.08)
                clusters = 4.0
                silhouette = rng.uniform(0.15, 0.35)
                evm = rng.uniform(0.6, 1.2)
                phase_q = rng.uniform(0.1, 0.4)

            feat_dict = {
                "C20": float(c20),
                "C21": 1.0,
                "C40": float(max(0.0, c40)),
                "C42": float(c42),
                "C60": 0.0,
                "C63": 0.0,
                "C80": 0.0,
                "cluster_count": float(clusters),
                "silhouette": float(silhouette),
                "intra_var": float(rng.uniform(0.05, 0.2)),
                "inter_dist": float(rng.uniform(0.5, 1.5)),
                "evm": float(evm),
                "phase_ambiguity_quality": float(phase_q),
                "snr": float(snr),
                "baud": 100000.0,
            }
            feat = [feat_dict[f] for f in CANONICAL_FEATURE_NAMES]
            X_list.append(feat)
            y_list.append(cls_name)

    return np.array(X_list, dtype=np.float32), np.array(y_list)


def train_and_save_model(output_path: str = "models/baseline_rf.joblib", seed: int = 42):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    X, y = generate_feature_dataset(n_samples_per_class=400, seed=seed)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=seed, stratify=y
    )

    base_rf = RandomForestClassifier(
        n_estimators=150,
        max_depth=16,
        random_state=seed,
        class_weight="balanced",
    )

    calibrated_clf = CalibratedClassifierCV(estimator=base_rf, method="sigmoid", cv=5)
    calibrated_clf.fit(X_train, y_train)

    # Evaluate
    y_pred = calibrated_clf.predict(X_test)
    report = classification_report(y_test, y_pred)
    print("Baseline RandomForest Classification Report on Held-out Test Set:")
    print(report)

    joblib.dump(calibrated_clf, output_path)
    print(f"Calibrated model artifact saved to: {output_path}")


if __name__ == "__main__":
    train_and_save_model()
