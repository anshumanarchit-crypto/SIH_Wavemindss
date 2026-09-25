"""
Reliability Diagram Plotter for SpectralQ.

Generates publication-quality diagnostic diagrams comparing:
- Raw ML probability
- Calibrated ML probability
- Final Hybrid Confidence

Visualizes:
- Empirical accuracy vs. mean predicted confidence deciles.
- Ideal calibration diagonal (y = x).
- Explicit visual flagging for low-count buckets (n < 10) to avoid misleading interpretations.
- Sample distribution histogram per decile.
- Saves high-resolution artifact to bench/reliability_diagram.png.
"""

from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless execution
import matplotlib.pyplot as plt
import numpy as np

from spectralq.calibration.metrics import CalibrationReport


def plot_reliability_diagram(
    raw_report: CalibrationReport,
    cal_report: CalibrationReport,
    final_report: CalibrationReport,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Renders multi-panel reliability diagram comparing raw, calibrated, and final confidence.
    """
    target = output_path or (Path(__file__).parent.parent.parent.parent / "bench" / "reliability_diagram.png")
    target.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)

    reports = [
        ("Raw ML Probability", raw_report, "#e74c3c", axes[0]),
        ("Calibrated ML Probability", cal_report, "#2980b9", axes[1]),
        ("Final Hybrid Confidence", final_report, "#27ae60", axes[2]),
    ]

    for title, rep, color, ax in reports:
        # Ideal diagonal
        ax.plot([0, 1], [0, 1], "k--", alpha=0.7, label="Perfect Calibration (y=x)")

        confs = [b.mean_confidence for b in rep.bins]
        accs = [b.empirical_accuracy for b in rep.bins]
        counts = [b.sample_count for b in rep.bins]
        low_counts = [b.is_low_count for b in rep.bins]

        # Plot bars
        bin_centers = [(b.bin_lower + b.bin_upper) / 2.0 for b in rep.bins]
        width = 0.08

        for idx, b in enumerate(rep.bins):
            if b.sample_count == 0:
                continue
            if b.is_low_count:
                # Hatch pattern indicating low sample count warning (n < 10)
                ax.bar(
                    bin_centers[idx], b.empirical_accuracy, width=width,
                    color=color, alpha=0.35, edgecolor="red", linewidth=1.5,
                    hatch="//", label="Low Count (n<10)" if idx == 0 else ""
                )
                ax.text(
                    bin_centers[idx], b.empirical_accuracy + 0.03, f"n={b.sample_count}*",
                    ha="center", fontsize=8, color="#c0392b", weight="bold"
                )
            else:
                ax.bar(
                    bin_centers[idx], b.empirical_accuracy, width=width,
                    color=color, alpha=0.75, edgecolor="black", linewidth=1.0,
                    label="Reliable Bin (n>=10)" if idx == 0 else ""
                )
                ax.text(
                    bin_centers[idx], b.empirical_accuracy + 0.03, f"n={b.sample_count}",
                    ha="center", fontsize=8, color="#2c3e50"
                )

        ax.set_title(f"{title}\nECE = {rep.ece:.4f} | Brier = {rep.brier_score:.4f}", fontsize=12, weight="bold")
        ax.set_xlabel("Mean Predicted Confidence", fontsize=10)
        ax.set_xlim(0, 1.0)
        ax.set_ylim(0, 1.1)
        ax.grid(True, linestyle=":", alpha=0.6)

    axes[0].set_ylabel("Empirical Accuracy", fontsize=11)

    fig.suptitle(
        "SpectralQ Multi-Stage Reliability Calibration Analysis (Split by Signal Instance)\n"
        "*Flagged bins indicate n < 10 (low statistical confidence in bin estimate itself)",
        fontsize=13, y=1.03
    )

    plt.tight_layout()
    fig.savefig(target, dpi=300, bbox_inches="tight")
    plt.close(fig)

    return target
