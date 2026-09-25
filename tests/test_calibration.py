"""
Tests for Calibration Metrics (ECE, Brier Score, Reliability Diagram).
"""

import os
import numpy as np
import pytest
from spectralq.evidence_ledger.calibration import (
    ConfidenceCalibrator,
    compute_ece,
    compute_brier_score,
    plot_reliability_diagram,
)


def test_compute_ece_perfect_calibration():
    # If confidences match empirical accuracy perfectly, ECE should be near 0
    confidences = np.array([0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.0])
    accuracies = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 0])
    ece, stats = compute_ece(confidences, accuracies, n_bins=5)
    assert ece < 0.15


def test_brier_score():
    # Perfect predictions: score = 0.0
    confidences = np.array([1.0, 1.0, 0.0, 0.0])
    ground_truth = np.array([1.0, 1.0, 0.0, 0.0])
    bs = compute_brier_score(confidences, ground_truth)
    assert bs == 0.0

    # Totally wrong predictions: score = 1.0
    conf_wrong = np.array([0.0, 0.0, 1.0, 1.0])
    bs_wrong = compute_brier_score(conf_wrong, ground_truth)
    assert bs_wrong == 1.0


def test_plot_reliability_diagram(tmp_path):
    confidences = np.random.uniform(0.1, 0.9, size=100)
    accuracies = (confidences > 0.5).astype(int)
    png_path = str(tmp_path / "test_reliability.png")

    result = plot_reliability_diagram(
        confidences=confidences,
        accuracies=accuracies,
        output_png_path=png_path,
        title="Test Reliability Diagram",
        n_bins=5,
    )
    assert os.path.exists(png_path)
    assert "ece" in result
    assert "brier_score" in result


def test_confidence_calibrator():
    calibrator = ConfidenceCalibrator()
    assert calibrator.calibrate(0.8) == 0.8  # Unfitted passes through bounded

    X = np.linspace(0.1, 0.9, 50)
    y = (X > 0.4).astype(float)
    calibrator.fit(X, y)

    calibrated_val = calibrator.calibrate(0.85)
    assert 0.01 <= calibrated_val <= 0.99
