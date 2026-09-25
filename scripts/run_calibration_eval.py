import os
import sys
import json
from pathlib import Path

# Add repo root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from spectralq.contracts.schemas import AnalysisContract, Cumulants, ClusterMetrics, SubWindowMetrics, ProvenanceType
from spectralq.pipeline.orchestrator import SpectralQOrchestrator
from spectralq.evidence_ledger.calibration import plot_reliability_diagram, compute_ece, compute_brier_score
from spectralq.n5_hybrid.classifier_adapter import CLASSES


def run_full_calibration_evaluation(
    n_samples_per_class: int = 70,
    output_dir: str = "reports",
    seed: int = 42,
):
    os.makedirs(output_dir, exist_ok=True)
    rng = np.random.RandomState(seed)

    orchestrator = SpectralQOrchestrator(confidence_threshold=0.60, seed=seed)

    confidences = []
    correct_matches = []
    decisions = []

    for true_cls in CLASSES:
        for i in range(n_samples_per_class):
            snr = rng.uniform(2.0, 30.0)
            is_corrupted = rng.uniform(0.0, 1.0) < 0.15  # 15% degraded/ambiguous samples
            noise_scale = 1.0 / (10.0 ** (snr / 20.0))
            if is_corrupted:
                noise_scale *= 4.0

            if true_cls == "BPSK":
                c20 = 1.0 + rng.normal(0, 0.08 * noise_scale)
                c40 = -2.0 + rng.normal(0, 0.15 * noise_scale)
                c42 = -2.0 + rng.normal(0, 0.15 * noise_scale)
                env_var = 0.04 + rng.normal(0, 0.02)
                clusters = 2
            elif true_cls == "QPSK":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = 1.0 + rng.normal(0, 0.12 * noise_scale)
                c42 = -1.0 + rng.normal(0, 0.12 * noise_scale)
                env_var = 0.05 + rng.normal(0, 0.02)
                clusters = 4
            elif true_cls == "8-PSK":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = 0.0 + rng.normal(0, 0.08 * noise_scale)
                c42 = -1.0 + rng.normal(0, 0.12 * noise_scale)
                env_var = 0.06 + rng.normal(0, 0.02)
                clusters = 8
            elif true_cls == "16-QAM":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = -0.68 + rng.normal(0, 0.08 * noise_scale)
                c42 = -0.68 + rng.normal(0, 0.08 * noise_scale)
                env_var = 0.15 + rng.normal(0, 0.03)
                clusters = 16
            elif true_cls == "64-QAM":
                c20 = 0.0 + rng.normal(0, 0.04 * noise_scale)
                c40 = -0.619 + rng.normal(0, 0.08 * noise_scale)
                c42 = -0.619 + rng.normal(0, 0.08 * noise_scale)
                env_var = 0.18 + rng.normal(0, 0.03)
                clusters = 64
            elif true_cls == "2-FSK":
                c20 = 0.0 + rng.normal(0, 0.04)
                c40 = 0.0 + rng.normal(0, 0.08)
                c42 = -1.0 + rng.normal(0, 0.08)
                env_var = 0.45 + rng.normal(0, 0.05)
                clusters = 2
            else:  # 4-FSK
                c20 = 0.0 + rng.normal(0, 0.04)
                c40 = 0.0 + rng.normal(0, 0.08)
                c42 = -1.0 + rng.normal(0, 0.08)
                env_var = 0.50 + rng.normal(0, 0.05)
                clusters = 4

            analysis = AnalysisContract(
                capture_id=f"EVAL_{true_cls}_{i:03d}",
                provenance=ProvenanceType.SYNTHETIC,
                is_valid_burst=True,
                snr_m2m4_db=snr,
                evm=float(np.clip(rng.uniform(0.02, 0.15) * (1.0 + noise_scale), 0.01, 0.90)),
                phase_ambiguity_quality=float(np.clip(rng.uniform(0.80, 1.0) - 0.2 * noise_scale, 0.1, 1.0)),
                envelope_variance=float(max(0.01, env_var)),
                phase_entropy=float(rng.uniform(0.7, 2.0)),
                cumulants=Cumulants(
                    C20=c20, C21=1.0, C40=c40, C42=c42, C60=0.0, C63=0.0, C80=0.0
                ),
                cluster_metrics=ClusterMetrics(
                    cluster_count=clusters,
                    silhouette_score=float(np.clip(0.90 - 0.3 * noise_scale, 0.1, 0.98)),
                    intra_cluster_dist=float(0.10 * (1.0 + noise_scale)),
                    inter_cluster_dist=1.2,
                    cluster_count_stability=float(np.clip(1.0 - 0.3 * noise_scale, 0.2, 1.0)),
                ),
                sub_windows=[
                    SubWindowMetrics(
                        window_idx=w,
                        estimated_snr_db=float(snr + rng.normal(0, 0.3)),
                        estimated_c42=float(c42 + rng.normal(0, 0.05)),
                        estimated_c20=float(c20 + rng.normal(0, 0.05)),
                        cluster_count=clusters,
                    )
                    for w in range(3)
                ],
            )

            res = orchestrator.process(analysis)
            confidences.append(res.final_confidence)
            
            # Ground truth match: True if decision_label matches ground truth class
            is_correct = (res.decision_label == true_cls)
            correct_matches.append(1 if is_correct else 0)
            decisions.append(res.decision_label)

    conf_arr = np.array(confidences)
    match_arr = np.array(correct_matches)

    diagram_path = os.path.join(output_dir, "calibration_reliability_diagram.png")
    metrics = plot_reliability_diagram(
        confidences=conf_arr,
        accuracies=match_arr,
        output_png_path=diagram_path,
        title="SpectralQ N2 Confidence Reliability Diagram",
        n_bins=10,
    )

    ece, bin_stats = compute_ece(conf_arr, match_arr, n_bins=10)
    brier = compute_brier_score(conf_arr, match_arr)

    report_data = {
        "total_eval_samples": len(conf_arr),
        "expected_calibration_error_ece": round(ece, 4),
        "brier_score": round(brier, 4),
        "mean_confidence": round(float(np.mean(conf_arr)), 4),
        "mean_empirical_accuracy": round(float(np.mean(match_arr)), 4),
        "unknown_count": decisions.count("UNKNOWN"),
        "unknown_rate": round(decisions.count("UNKNOWN") / len(decisions), 4),
        "bin_breakdown": bin_stats,
        "diagram_artifact": diagram_path,
    }

    report_json_path = os.path.join(output_dir, "calibration_report.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print("==================================================")
    print("SPECTRALQ CALIBRATION EVALUATION RESULTS")
    print("==================================================")
    print(f"Total Samples Evaluated: {report_data['total_eval_samples']}")
    print(f"Expected Calibration Error (ECE): {report_data['expected_calibration_error_ece']:.4f}")
    print(f"Brier Score: {report_data['brier_score']:.4f}")
    print(f"UNKNOWN Rate: {report_data['unknown_rate'] * 100:.1f}% ({report_data['unknown_count']} samples)")
    print(f"Reliability Diagram saved to: {diagram_path}")
    print(f"Detailed JSON report saved to: {report_json_path}")
    print("==================================================")


if __name__ == "__main__":
    run_full_calibration_evaluation()
