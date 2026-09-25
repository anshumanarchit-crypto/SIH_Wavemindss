"""
Classifier & Confidence Benchmarking Evaluator for SpectralQ Phase 10.

Evaluates:
1. Instance-level isolation and Leakage Guard validation.
2. Classifier accuracy, 7x7 confusion matrix, and per-class precision/recall/F1.
3. Accuracy vs. SNR performance across calibrated SNR regimes.
4. Confidence calibration metrics (from Phase 7).
5. Abstention operating point, coverage, and honest disclosure of confident-but-incorrect failures.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV

from spectralq.calibration.dataset import (
    SignalInstanceRecord,
    generate_synthetic_sweep,
    split_by_signal_instance,
)
from spectralq.calibration.calibrator import ModelCalibrator
from spectralq.confidence.engine import ConfidenceEngine
from spectralq.confidence.abstention import AbstentionSystem, DEFAULT_ABSTENTION_THRESHOLD
from spectralq.contracts.schemas import AnalysisContract, validate_analysis_dict
from spectralq.hypothesis.registry import MODULATIONS
from spectralq.integration.classifier_adapter import CANONICAL_FEATURE_NAMES
from spectralq.evidence.ledger import EvidenceLedger


BENCH_DIR = Path(__file__).parent.parent.parent.parent / "bench"


class ClassifierEvaluator:
    """
    Evaluates ML classifier and confidence engine performance against synthetic sweeps.
    """

    def __init__(
        self,
        seed: int = 2026,
        n_instances_per_class: int = 50,
        test_ratio: float = 0.30,
        bench_dir: Optional[Path] = None,
    ):
        self.seed = seed
        self.n_instances_per_class = n_instances_per_class
        self.test_ratio = test_ratio
        self.bench_dir = bench_dir or BENCH_DIR
        self.classes = list(MODULATIONS)

    def run_evaluation(self) -> Dict[str, Any]:
        """
        Executes complete training, testing, and confidence validation.
        Returns a comprehensive metrics dictionary.
        """
        # 1. Dataset Generation
        records = generate_synthetic_sweep(
            n_instances_per_class=self.n_instances_per_class,
            seed=self.seed,
        )
        total_instances = len(records)

        # 2. Strict Split by Signal Instance
        train_records, test_records = split_by_signal_instance(
            records=records,
            test_ratio=self.test_ratio,
            seed=self.seed,
        )

        train_ids: Set[str] = set(r.instance_id for r in train_records)
        test_ids: Set[str] = set(r.instance_id for r in test_records)

        # LEAKAGE GUARD ENFORCEMENT
        overlap = train_ids.intersection(test_ids)
        if len(overlap) > 0:
            raise RuntimeError(f"LEAKAGE DETECTED: {len(overlap)} instance IDs appear in both train and test sets!")

        # 3. Fit Calibrated Model
        calibrator = ModelCalibrator(random_state=self.seed)
        calibrator.fit(train_records)

        # 4. Evaluate Classifier on Held-Out Test Set
        y_true: List[str] = []
        y_pred: List[str] = []
        snr_list: List[float] = []
        eval_details: List[Dict[str, Any]] = []

        confidence_engine = ConfidenceEngine()
        abstention_system = AbstentionSystem(threshold=DEFAULT_ABSTENTION_THRESHOLD)

        confident_incorrect_cases: List[Dict[str, Any]] = []
        accepted_count = 0
        abstained_count = 0

        for r in test_records:
            true_mod = r.true_modulation
            y_true.append(true_mod)
            snr_list.append(r.snr_db)

            # Predict using calibrator
            top_pred, raw_p, cal_p, raw_dict, cal_dict = calibrator.predict_raw_and_calibrated(r.features)
            y_pred.append(top_pred)

            is_correct = (top_pred == true_mod)

            # Build mock AnalysisContract to test confidence and abstention
            sim_analysis = validate_analysis_dict({
                "schema_version": "1.0.0",
                "capture_id": r.instance_id,
                "source_mode": "synthetic",
                "fs_hz": 20.0e6,
                "fs_source": "header",
                "bursts": [{"start_ms": 0.0, "end_ms": 100.0, "power": -15.0}],
                "estimates": {
                    "baud": {"value": 1.0e6, "ci_lo": 0.99e6, "ci_hi": 1.01e6, "method": "test"},
                    "cfo": {"value": r.cfo_hz, "ci_lo": r.cfo_hz - 10, "ci_hi": r.cfo_hz + 10, "method": "test"},
                    "bandwidth": {"value": 1.2e6, "ci_lo": 1.1e6, "ci_hi": 1.3e6, "method": "test"},
                    "snr": {"value": r.snr_db, "ci_lo": r.snr_db - 0.5, "ci_hi": r.snr_db + 0.5, "method": "test"},
                },
                "features": {
                    "cumulants": {
                        "C20": r.features["C20"], "C21": r.features["C21"],
                        "C40": r.features["C40"], "C42": r.features["C42"],
                        "C60": r.features["C60"], "C63": r.features["C63"], "C80": r.features["C80"],
                    },
                    "cluster": {
                        "count": int(r.features["cluster_count"]),
                        "silhouette": r.features["silhouette"],
                        "intra_var": r.features["intra_var"],
                        "inter_dist": r.features["inter_dist"],
                    },
                    "evm": r.features["evm"],
                    "phase_ambiguity_quality": r.features["phase_ambiguity_quality"],
                    "cyclic": None,
                },
            })

            ledger = EvidenceLedger(run_id=f"EVAL_{r.instance_id}")
            conf_res = confidence_engine.compute_confidence(
                prediction=top_pred,
                ml_probability=raw_p,
                cross_window_agreement=1.0,
                rule_prediction=top_pred,
                ml_prediction=top_pred,
                rule_ml_agreement=True,
                ledger=ledger,
                calibrated_ml_probability=cal_p,
            )

            decision = abstention_system.evaluate(
                analysis=sim_analysis,
                confidence_result=conf_res,
                ledger=ledger,
                capture_id=r.instance_id,
            )

            if decision.is_unknown:
                abstained_count += 1
            else:
                accepted_count += 1
                if not is_correct:
                    # Confident but incorrect failure mode!
                    confident_incorrect_cases.append({
                        "instance_id": r.instance_id,
                        "true_modulation": true_mod,
                        "predicted_modulation": top_pred,
                        "final_confidence": round(decision.final_confidence, 4),
                        "snr_db": round(r.snr_db, 1),
                        "raw_ml_prob": round(raw_p, 4),
                        "calibrated_ml_prob": round(cal_p, 4),
                    })

            eval_details.append({
                "instance_id": r.instance_id,
                "true_modulation": true_mod,
                "predicted_modulation": top_pred,
                "is_correct": is_correct,
                "snr_db": r.snr_db,
                "final_confidence": conf_res.final_confidence,
                "is_unknown": decision.is_unknown,
            })

        # 5. Metrics Computation
        total_test = len(y_true)
        overall_accuracy = float(np.mean([1 if yt == yp else 0 for yt, yp in zip(y_true, y_pred)]))

        # Confusion Matrix
        cm = confusion_matrix(y_true, y_pred, labels=self.classes).tolist()

        # Per-Class Precision, Recall, F1
        clf_rep = classification_report(
            y_true,
            y_pred,
            labels=self.classes,
            target_names=self.classes,
            output_dict=True,
            zero_division=0,
        )
        per_class_results = {}
        for cls_name in self.classes:
            if cls_name in clf_rep:
                per_class_results[cls_name] = {
                    "precision": round(float(clf_rep[cls_name]["precision"]), 4),
                    "recall": round(float(clf_rep[cls_name]["recall"]), 4),
                    "f1_score": round(float(clf_rep[cls_name]["f1-score"]), 4),
                    "support": int(clf_rep[cls_name]["support"]),
                }

        # Accuracy vs SNR Bins
        snr_bins = [
            ("2-6 dB", 2.0, 6.0),
            ("6-10 dB", 6.0, 10.0),
            ("10-14 dB", 10.0, 14.0),
            ("14-18 dB", 14.0, 18.0),
            ("18-22 dB", 18.0, 22.0),
            ("22-26 dB", 22.0, 26.5),
        ]
        accuracy_vs_snr = []
        for bin_label, low, high in snr_bins:
            bin_items = [d for d in eval_details if low <= d["snr_db"] < high]
            if bin_items:
                bin_acc = float(np.mean([1.0 if d["is_correct"] else 0.0 for d in bin_items]))
                accuracy_vs_snr.append({
                    "snr_bin": bin_label,
                    "sample_count": len(bin_items),
                    "accuracy": round(bin_acc, 4),
                })
            else:
                accuracy_vs_snr.append({
                    "snr_bin": bin_label,
                    "sample_count": 0,
                    "accuracy": 0.0,
                })

        # 6. Load Phase 7 Calibration Result
        calib_metrics_path = self.bench_dir / "calibration_metrics.json"
        calib_data = {}
        if calib_metrics_path.exists():
            try:
                calib_data = json.loads(calib_metrics_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # 7. Confidence & Abstention Summary
        coverage_rate = accepted_count / total_test if total_test > 0 else 0.0
        abstention_rate = abstained_count / total_test if total_test > 0 else 0.0

        return {
            "metadata": {
                "model_version": "rf-baseline-1.0.0",
                "feature_version": "1.0.0-canonical-15",
                "dataset_id": f"synthetic_sweep_n{self.n_instances_per_class}_seed{self.seed}",
                "seed": self.seed,
                "split_ratio": round(1.0 - self.test_ratio, 2),
                "test_ratio": self.test_ratio,
            },
            "leakage_guard": {
                "status": "PASSED",
                "train_instances": len(train_ids),
                "test_instances": len(test_ids),
                "overlap_instances": len(overlap),
                "is_strictly_disjoint": True,
            },
            "classifier_performance": {
                "overall_accuracy": round(overall_accuracy, 4),
                "total_train_samples": len(train_records),
                "total_test_samples": total_test,
                "classes": self.classes,
                "confusion_matrix": cm,
                "per_class_results": per_class_results,
                "accuracy_vs_snr": accuracy_vs_snr,
            },
            "confidence_calibration": {
                "phase7_ece_raw_ml": calib_data.get("raw_ml", {}).get("ece", None),
                "phase7_ece_calibrated_ml": calib_data.get("calibrated_ml", {}).get("ece", None),
                "phase7_brier_score": calib_data.get("final_confidence", {}).get("brier_score", None),
                "reliability_diagram_reference": "bench/reliability_diagram.png",
                "calibration_method": "CalibratedClassifierCV(method='sigmoid', cv=3)",
            },
            "abstention_analysis": {
                "chosen_threshold": DEFAULT_ABSTENTION_THRESHOLD,
                "threshold_rationale": "Minimize FAR subject to FRR <= 10.0% from Phase 8 empirical threshold sweep",
                "coverage_rate": round(coverage_rate, 4),
                "abstention_rate": round(abstention_rate, 4),
                "accepted_count": accepted_count,
                "abstained_count": abstained_count,
                "confident_incorrect_count": len(confident_incorrect_cases),
                "confident_incorrect_cases": confident_incorrect_cases,
            },
        }


def evaluate_classifier_and_confidence(seed: int = 2026) -> Dict[str, Any]:
    """Convenience entry point for evaluator execution."""
    evaluator = ClassifierEvaluator(seed=seed)
    return evaluator.run_evaluation()
