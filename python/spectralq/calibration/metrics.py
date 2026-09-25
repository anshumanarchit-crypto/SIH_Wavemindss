"""
Calibration Metrics: Reliability Binning, Expected Calibration Error (ECE) & Brier Score.

Invariants:
- Confidence partitioned into 10 deciles: [0.0, 0.1), ..., [0.9, 1.0].
- Low count buckets (n < 10) are explicitly flagged as 'is_low_count: True'
  (low confidence in the calibration estimate itself), never silently plotted as reliable.
- Empty buckets (n == 0) are handled gracefully with 0.0 values and low_count flag.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import numpy as np


LOW_COUNT_THRESHOLD = 10


@dataclass
class ReliabilityBin:
    bin_index: int
    bin_lower: float
    bin_upper: float
    sample_count: int
    mean_confidence: float
    empirical_accuracy: float
    is_low_count: bool
    warning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bin_index": self.bin_index,
            "bin_lower": round(self.bin_lower, 2),
            "bin_upper": round(self.bin_upper, 2),
            "sample_count": self.sample_count,
            "mean_confidence": round(self.mean_confidence, 4),
            "empirical_accuracy": round(self.empirical_accuracy, 4),
            "is_low_count": self.is_low_count,
            "warning": self.warning,
        }


@dataclass
class CalibrationReport:
    n_samples: int
    ece: float
    brier_score: float
    bins: List[ReliabilityBin]
    metric_name: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "n_samples": self.n_samples,
            "ece": round(self.ece, 4),
            "brier_score": round(self.brier_score, 4),
            "bins": [b.to_dict() for b in self.bins],
        }


def compute_reliability_bins(
    confidences: np.ndarray,
    accuracies: np.ndarray,
    n_bins: int = 10,
    metric_name: str = "confidence",
) -> CalibrationReport:
    """
    Computes reliability diagram bins, ECE, and Brier score.
    
    Args:
        confidences: 1D array of predicted probabilities/confidences in [0.0, 1.0].
        accuracies: 1D binary array (1 for correct, 0 for incorrect).
        n_bins: Number of equal-width bins (default 10 deciles).
        metric_name: Identifier label for this evaluation.
    """
    confidences = np.asarray(confidences, dtype=np.float64)
    accuracies = np.asarray(accuracies, dtype=np.float64)
    n_samples = len(confidences)

    if n_samples == 0:
        return CalibrationReport(
            n_samples=0,
            ece=0.0,
            brier_score=0.0,
            bins=[],
            metric_name=metric_name,
        )

    brier = float(np.mean((confidences - accuracies) ** 2))

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins: List[ReliabilityBin] = []
    weighted_abs_err_sum = 0.0

    for i in range(n_bins):
        lower = bin_edges[i]
        upper = bin_edges[i + 1]

        # Upper edge inclusive for the last bin
        if i == n_bins - 1:
            mask = (confidences >= lower) & (confidences <= upper)
        else:
            mask = (confidences >= lower) & (confidences < upper)

        count = int(np.sum(mask))

        if count > 0:
            bin_conf = float(np.mean(confidences[mask]))
            bin_acc = float(np.mean(accuracies[mask]))
            abs_err = abs(bin_acc - bin_conf)
            weighted_abs_err_sum += (count / n_samples) * abs_err
        else:
            bin_conf = float((lower + upper) / 2.0)
            bin_acc = 0.0

        is_low = count < LOW_COUNT_THRESHOLD
        warning = f"Low sample count (n={count} < {LOW_COUNT_THRESHOLD}); unreliable bin estimate" if is_low else ""

        bins.append(ReliabilityBin(
            bin_index=i,
            bin_lower=lower,
            bin_upper=upper,
            sample_count=count,
            mean_confidence=bin_conf,
            empirical_accuracy=bin_acc,
            is_low_count=is_low,
            warning=warning,
        ))

    ece = float(weighted_abs_err_sum)

    return CalibrationReport(
        n_samples=n_samples,
        ece=ece,
        brier_score=brier,
        bins=bins,
        metric_name=metric_name,
    )
