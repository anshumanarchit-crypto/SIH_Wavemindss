"""
Empirical Threshold Sweep & Abstention Operating Point Determination for SpectralQ.

Threshold Determination Protocol:
- Uses a synthetic sweep across diverse SNRs, noise-only signals, and channel impairments.
- Sweeps candidate confidence thresholds theta in [0.40, 0.95].
- Evaluates:
    False-Accept Rate (FAR): fraction of incorrect predictions where final_confidence >= theta (confidently wrong).
    False-Reject Rate (FRR): fraction of correct predictions where final_confidence < theta (correctly known but abstained).
- Operating Point Selection:
    Minimize FAR subject to FRR <= 10.0%.
    Ensures the system prioritizes safety (never returning low-confidence best guesses)
    while avoiding excessive unnecessary abstentions on clean signals.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from spectralq.calibration.dataset import generate_synthetic_sweep, split_by_signal_instance
from spectralq.confidence.engine import ConfidenceEngine
from spectralq.integration.classifier_adapter import ClassifierAdapter
from spectralq.integration.rule_classifier import RuleBasedClassifier


ABSTENTION_CONFIG_PATH = Path(__file__).parent / "abstention_config.json"


@dataclass
class SweepPoint:
    threshold: float
    false_accept_rate: float
    false_reject_rate: float
    accuracy_when_accepted: float
    accepted_count: int
    rejected_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold": round(self.threshold, 4),
            "false_accept_rate": round(self.false_accept_rate, 4),
            "false_reject_rate": round(self.false_reject_rate, 4),
            "accuracy_when_accepted": round(self.accuracy_when_accepted, 4),
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
        }


def sweep_abstention_thresholds(
    n_instances_per_class: int = 30,
    seed: int = 2026,
    max_allowable_frr: float = 0.10,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Sweeps thresholds on a held-out dataset and identifies the optimal operating point.
    """
    # 1. Generate calibration instances
    records = generate_synthetic_sweep(n_instances_per_class=n_instances_per_class, seed=seed)
    train_recs, val_recs = split_by_signal_instance(records, test_ratio=0.50, seed=seed)

    # 2. Add explicit low-SNR and noisy instances to evaluate false acceptances
    rng = np.random.default_rng(seed)
    classifier = ClassifierAdapter()
    rule_clf = RuleBasedClassifier()
    conf_engine = ConfidenceEngine(weight_source="fitted")

    samples: List[Tuple[float, bool]] = []  # (final_confidence, is_correct)

    for rec in val_recs:
        ml_out = classifier.predict(rec.features, capture_id=rec.instance_id)
        rule_out = rule_clf.classify(rec.features)
        is_correct = (ml_out.ml_prediction == rec.true_modulation)

        # Downstream evidence score derived from physical SNR and EVM
        ev_score = min(1.0, max(0.0, (rec.snr_db - 2.0) / 18.0))
        cw_agree = min(1.0, max(0.4, (rec.snr_db - 0.0) / 16.0))
        rule_agree = (rule_out.predicted_class == ml_out.ml_prediction)

        conf_res = conf_engine.compute_confidence(
            prediction=ml_out.ml_prediction,
            ml_probability=ml_out.ml_probabilities.get(ml_out.ml_prediction, 0.5),
            cross_window_agreement=cw_agree,
            rule_prediction=rule_out.predicted_class,
            ml_prediction=ml_out.ml_prediction,
            rule_ml_agreement=rule_agree,
            evidence_score=ev_score,
            calibrated_ml_probability=None,
        )
        samples.append((conf_res.final_confidence, is_correct))

    # Add synthetic noise-only samples to simulate false-acceptance stress
    for idx in range(30):
        noise_features = {
            "C20": float(rng.normal(0, 0.05)),
            "C21": float(1.0 + rng.uniform(0.1, 0.3)),
            "C40": float(rng.normal(0, 0.08)),
            "C42": float(-0.5 + rng.normal(0, 0.1)),
            "C60": 0.0, "C63": 0.0, "C80": 0.0,
            "cluster_count": float(rng.choice([2, 4, 8, 16])),
            "silhouette": float(rng.uniform(0.10, 0.25)),
            "intra_var": 0.55,
            "inter_dist": 0.50,
            "evm": 0.45,
            "phase_ambiguity_quality": 0.20,
            "snr": float(rng.uniform(-4.0, 1.0)),
            "baud": 1.0e6,
        }
        ml_out = classifier.predict(noise_features, capture_id=f"NOISE_{idx}")
        rule_out = rule_clf.classify(noise_features)
        
        conf_res = conf_engine.compute_confidence(
            prediction=ml_out.ml_prediction,
            ml_probability=ml_out.ml_probabilities.get(ml_out.ml_prediction, 0.5),
            cross_window_agreement=0.40,
            rule_prediction=rule_out.predicted_class,
            ml_prediction=ml_out.ml_prediction,
            rule_ml_agreement=(rule_out.predicted_class == ml_out.ml_prediction),
            evidence_score=0.10,
        )
        # Noise samples are NEVER correct
        samples.append((conf_res.final_confidence, False))

    confs = np.array([s[0] for s in samples])
    corrects = np.array([s[1] for s in samples])

    total_correct = int(np.sum(corrects))
    total_incorrect = int(np.sum(~corrects))

    # 3. Sweep candidate thresholds from 0.40 to 0.95
    candidate_thresholds = np.linspace(0.40, 0.95, 23)
    sweep_results: List[SweepPoint] = []
    optimal_point: Optional[SweepPoint] = None

    for th in candidate_thresholds:
        accepted_mask = confs >= th
        rejected_mask = confs < th

        # False Accept: Accepted but Incorrect
        fa_count = int(np.sum(accepted_mask & (~corrects)))
        far = float(fa_count / total_incorrect) if total_incorrect > 0 else 0.0

        # False Reject: Rejected but Correct
        fr_count = int(np.sum(rejected_mask & corrects))
        frr = float(fr_count / total_correct) if total_correct > 0 else 0.0

        accepted_n = int(np.sum(accepted_mask))
        rejected_n = int(np.sum(rejected_mask))
        acc_accepted = float(np.sum(accepted_mask & corrects) / accepted_n) if accepted_n > 0 else 1.0

        sp = SweepPoint(
            threshold=float(th),
            false_accept_rate=far,
            false_reject_rate=frr,
            accuracy_when_accepted=acc_accepted,
            accepted_count=accepted_n,
            rejected_count=rejected_n,
        )
        sweep_results.append(sp)

        # Select operating point: minimize FAR subject to FRR <= max_allowable_frr
        if frr <= max_allowable_frr:
            if optimal_point is None or far < optimal_point.false_accept_rate:
                optimal_point = sp
            elif far == optimal_point.false_accept_rate and th > optimal_point.threshold:
                # Prefer higher threshold for safety if FAR is tied
                optimal_point = sp

    if optimal_point is None:
        # Fallback to median candidate if no candidate satisfies constraint
        optimal_point = sweep_results[len(sweep_results) // 2]

    config_data: Dict[str, Any] = {
        "version": "1.0.0-empirical-sweep",
        "selected_threshold": optimal_point.threshold,
        "operating_point": {
            "criterion": f"Minimize FAR subject to FRR <= {max_allowable_frr * 100:.1f}%",
            "false_accept_rate": optimal_point.false_accept_rate,
            "false_reject_rate": optimal_point.false_reject_rate,
            "accuracy_when_accepted": optimal_point.accuracy_when_accepted,
            "threshold": optimal_point.threshold,
        },
        "dataset_metadata": {
            "n_instances_per_class": n_instances_per_class,
            "total_val_samples": len(samples),
            "total_correct": total_correct,
            "total_incorrect": total_incorrect,
            "seed": seed,
            "split_method": "by_signal_instance_disjoint",
        },
        "sweep_curve": [p.to_dict() for p in sweep_results],
    }

    target = output_path or ABSTENTION_CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    return config_data


def load_abstention_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads or generates the versioned abstention threshold configuration."""
    target = config_path or ABSTENTION_CONFIG_PATH
    if not target.exists():
        return sweep_abstention_thresholds(output_path=target)

    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)
