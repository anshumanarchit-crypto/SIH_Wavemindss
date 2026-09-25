"""
Statistical Calibration, Reliability Evaluation, and Uncertainty Diagnostics.
Implements ECE (Expected Calibration Error), Brier Score, and reliability diagram generation.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.isotonic import IsotonicRegression


class ConfidenceCalibrator:
    """
    Fits and applies Isotonic Calibration to raw model probabilities / fused scores.
    """

    def __init__(self):
        self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.01, y_max=0.99)
        self.is_fitted = False

    def fit(self, raw_scores: np.ndarray, ground_truth_matches: np.ndarray) -> "ConfidenceCalibrator":
        """
        Fits calibration curve on validation data.
        """
        self.calibrator.fit(raw_scores, ground_truth_matches)
        self.is_fitted = True
        return self

    def calibrate(self, raw_score: float) -> float:
        """
        Applies fitted calibration to a single score.
        """
        if not self.is_fitted:
            return float(np.clip(raw_score, 0.0, 1.0))
        return float(np.clip(self.calibrator.predict([raw_score])[0], 0.01, 0.99))


def compute_ece(
    confidences: np.ndarray,
    accuracies: np.ndarray,
    n_bins: int = 10
) -> Tuple[float, List[Dict[str, float]]]:
    """
    Computes Expected Calibration Error (ECE).
    ECE = sum_{m=1}^M (|B_m| / N) * |acc(B_m) - conf(B_m)|
    """
    confidences = np.asarray(confidences)
    accuracies = np.asarray(accuracies)
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    
    ece = 0.0
    bin_stats = []
    n_total = len(confidences)

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        
        # Select items in bin
        if i == n_bins - 1:
            in_bin = (confidences >= bin_lower) & (confidences <= bin_upper)
        else:
            in_bin = (confidences >= bin_lower) & (confidences < bin_upper)
            
        bin_count = int(np.sum(in_bin))
        if bin_count > 0:
            bin_acc = float(np.mean(accuracies[in_bin]))
            bin_conf = float(np.mean(confidences[in_bin]))
            bin_error = abs(bin_acc - bin_conf)
            ece += (bin_count / n_total) * bin_error
            
            bin_stats.append({
                "bin_idx": i,
                "bin_range": f"[{bin_lower:.2f}, {bin_upper:.2f}]",
                "count": bin_count,
                "mean_confidence": bin_conf,
                "mean_accuracy": bin_acc,
                "calibration_gap": bin_error,
            })
        else:
            bin_stats.append({
                "bin_idx": i,
                "bin_range": f"[{bin_lower:.2f}, {bin_upper:.2f}]",
                "count": 0,
                "mean_confidence": (bin_lower + bin_upper) / 2.0,
                "mean_accuracy": 0.0,
                "calibration_gap": 0.0,
            })

    return float(ece), bin_stats


def compute_brier_score(confidences: np.ndarray, ground_truth: np.ndarray) -> float:
    """
    Computes the Brier score: Mean squared difference between predicted confidence and binary truth.
    Lower is better (0.0 is perfect calibration and sharpness).
    """
    confidences = np.asarray(confidences, dtype=np.float64)
    ground_truth = np.asarray(ground_truth, dtype=np.float64)
    return float(np.mean((confidences - ground_truth) ** 2))


def plot_reliability_diagram(
    confidences: np.ndarray,
    accuracies: np.ndarray,
    output_png_path: str,
    title: str = "SpectralQ Reliability Diagram",
    n_bins: int = 10,
) -> Dict[str, float]:
    """
    Generates and saves a formal reliability diagram with ECE and Brier score.
    """
    ece, bin_stats = compute_ece(confidences, accuracies, n_bins=n_bins)
    brier = compute_brier_score(confidences, accuracies)

    fig, ax = plt.subplots(figsize=(7, 6))
    
    bin_confs = [b["mean_confidence"] for b in bin_stats if b["count"] > 0]
    bin_accs = [b["mean_accuracy"] for b in bin_stats if b["count"] > 0]
    bin_counts = [b["count"] for b in bin_stats if b["count"] > 0]

    # Perfect calibration reference line
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect Calibration")

    # Observed calibration bar / scatter
    ax.scatter(bin_confs, bin_accs, s=[max(20, c * 2) for c in bin_counts], color="#1f77b4", zorder=5, label="Observed Bins")
    ax.plot(bin_confs, bin_accs, marker="o", color="#1f77b4", linewidth=2)

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_xlabel("Mean Predicted Confidence")
    ax.set_ylabel("Empirical Accuracy")
    ax.set_title(f"{title}\nECE = {ece:.4f} | Brier Score = {brier:.4f}")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left")
    
    plt.tight_layout()
    plt.savefig(output_png_path, dpi=150)
    plt.close(fig)

    return {
        "ece": ece,
        "brier_score": brier,
        "diagram_path": output_png_path,
    }
