import os
import sys
from pathlib import Path

# Add repo root to sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from spectralq.n5_hybrid.classifier_adapter import CLASSES, FEATURE_NAMES


def generate_feature_dataset(n_samples_per_class: int = 250, seed: int = 42):
    rng = np.random.RandomState(seed)
    X_list = []
    y_list = []

    for cls_name in CLASSES:
        for _ in range(n_samples_per_class):
            snr = rng.uniform(4.0, 32.0)
            noise_scale = 1.0 / (10.0 ** (snr / 20.0))

            if cls_name == "BPSK":
                c20 = 1.0 + rng.normal(0, 0.08 * noise_scale)
                c40 = -2.0 + rng.normal(0, 0.15 * noise_scale)
                c42 = -2.0 + rng.normal(0, 0.15 * noise_scale)
                env_var = 0.04 + rng.normal(0, 0.02)
                clusters = 2.0
            elif cls_name == "QPSK":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = 1.0 + rng.normal(0, 0.12 * noise_scale)
                c42 = -1.0 + rng.normal(0, 0.12 * noise_scale)
                env_var = 0.05 + rng.normal(0, 0.02)
                clusters = 4.0
            elif cls_name == "8-PSK":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = 0.0 + rng.normal(0, 0.08 * noise_scale)
                c42 = -1.0 + rng.normal(0, 0.12 * noise_scale)
                env_var = 0.06 + rng.normal(0, 0.02)
                clusters = 8.0
            elif cls_name == "16-QAM":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = -0.68 + rng.normal(0, 0.08 * noise_scale)
                c42 = -0.68 + rng.normal(0, 0.08 * noise_scale)
                env_var = 0.15 + rng.normal(0, 0.03)
                clusters = 16.0
            elif cls_name == "64-QAM":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = -0.619 + rng.normal(0, 0.08 * noise_scale)
                c42 = -0.619 + rng.normal(0, 0.08 * noise_scale)
                env_var = 0.18 + rng.normal(0, 0.03)
                clusters = 64.0
            elif cls_name == "2-FSK":
                c20 = 0.0 + rng.normal(0, 0.04)
                c40 = 0.0 + rng.normal(0, 0.08)
                c42 = -1.0 + rng.normal(0, 0.08)
                env_var = 0.45 + rng.normal(0, 0.05)
                clusters = 2.0
            else:  # 4-FSK
                c20 = 0.0 + rng.normal(0, 0.04)
                c40 = 0.0 + rng.normal(0, 0.08)
                c42 = -1.0 + rng.normal(0, 0.08)
                env_var = 0.50 + rng.normal(0, 0.05)
                clusters = 4.0

            feat = [
                c20, 1.0, c40, c42,
                0.0, 0.0, 0.0,
                snr,
                max(0.01, env_var),
                rng.uniform(0.8, 1.5),
                clusters,
                rng.uniform(0.65, 0.95),
                rng.uniform(0.05, 0.2),
                rng.uniform(0.5, 1.2),
                rng.uniform(0.85, 1.0),
                rng.uniform(0.02, 0.15) * (1.0 + noise_scale),
                rng.uniform(0.8, 1.0)
            ]
            X_list.append(feat)
            y_list.append(cls_name)

    return np.array(X_list, dtype=np.float32), np.array(y_list)


def train_and_save_model(output_path: str = "models/baseline_rf.joblib", seed: int = 42):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    X, y = generate_feature_dataset(n_samples_per_class=300, seed=seed)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=seed, stratify=y
    )

    base_rf = RandomForestClassifier(
        n_estimators=120,
        max_depth=14,
        random_state=seed,
        class_weight="balanced"
    )

    calibrated_clf = CalibratedClassifierCV(estimator=base_rf, method="sigmoid", cv=3)
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
