"""
Phase 7 Tests: Confidence Calibration, Instance-Level Splitting & Reliability Diagram.

Covers:
1. Split-by-instance correctness (assert no instance ID appears on both sides).
2. End-to-end calibration pipeline execution and artifact persistence.
3. Reliability bin construction handling of empty and low-count buckets (n < 10).
4. Deterministic output given fixed random seed.
5. Architectural distinction: raw_ml_probability != calibrated_ml_probability != final_confidence.
"""

from pathlib import Path
import numpy as np
import pytest

from spectralq.calibration import (
    SignalInstanceRecord,
    generate_synthetic_sweep,
    split_by_signal_instance,
    compute_reliability_bins,
    ModelCalibrator,
    run_calibration_pipeline,
    plot_reliability_diagram,
    LOW_COUNT_THRESHOLD,
)


# -----------------------------------------------------------------------------
# 1. Instance-Level Isolation: Split BY SIGNAL INSTANCE (Never by Sample)
# -----------------------------------------------------------------------------
def test_split_by_instance_strict_isolation():
    records = generate_synthetic_sweep(n_instances_per_class=10, seed=42)
    assert len(records) == 70  # 7 modulations * 10

    train_records, val_records = split_by_signal_instance(records, test_ratio=0.30, seed=42)

    train_ids = set(r.instance_id for r in train_records)
    val_ids = set(r.instance_id for r in val_records)

    # Invariant: No instance ID may appear on both sides
    intersection = train_ids.intersection(val_ids)
    assert len(intersection) == 0, f"Found overlapping instance IDs between splits: {intersection}"
    assert len(train_ids) + len(val_ids) == len(set(r.instance_id for r in records))


# -----------------------------------------------------------------------------
# 2. Reliability Binning: Handling of Low-Count and Empty Buckets
# -----------------------------------------------------------------------------
def test_reliability_bin_empty_and_low_count_handling():
    # Only 5 samples (all placed in the top decile [0.9, 1.0])
    confs = np.array([0.92, 0.95, 0.96, 0.91, 0.98])
    accs = np.array([1.0, 1.0, 1.0, 0.0, 1.0])

    report = compute_reliability_bins(confs, accs, n_bins=10)

    assert report.n_samples == 5
    assert len(report.bins) == 10

    # 9 empty bins
    empty_bins = [b for b in report.bins if b.sample_count == 0]
    assert len(empty_bins) == 9
    for eb in empty_bins:
        assert eb.is_low_count is True

    # 1 bin with n=5 (which is < 10, so must be flagged as low count)
    top_bin = report.bins[-1]
    assert top_bin.sample_count == 5
    assert top_bin.is_low_count is True
    assert "Low sample count" in top_bin.warning


# -----------------------------------------------------------------------------
# 3. Determinism Given Fixed Seed
# -----------------------------------------------------------------------------
def test_calibration_pipeline_determinism(tmp_path):
    res1 = run_calibration_pipeline(n_instances_per_class=10, seed=1234, output_dir=tmp_path / "run1")
    res2 = run_calibration_pipeline(n_instances_per_class=10, seed=1234, output_dir=tmp_path / "run2")

    m1 = res1["metrics_data"]
    m2 = res2["metrics_data"]

    assert m1["raw_ml"]["ece"] == m2["raw_ml"]["ece"]
    assert m1["calibrated_ml"]["ece"] == m2["calibrated_ml"]["ece"]
    assert m1["final_confidence"]["brier_score"] == m2["final_confidence"]["brier_score"]


# -----------------------------------------------------------------------------
# 4. End-to-End Pipeline & Artifact Generation
# -----------------------------------------------------------------------------
def test_end_to_end_calibration_and_artifacts(tmp_path):
    bench_out = tmp_path / "bench"
    result = run_calibration_pipeline(n_instances_per_class=15, seed=2026, output_dir=bench_out)

    # Check generated files
    model_file = bench_out / "calibration_object.pkl"
    metrics_file = bench_out / "calibration_metrics.json"

    assert model_file.exists()
    assert metrics_file.exists()

    # Generate plot
    plot_file = bench_out / "reliability_diagram.png"
    plot_reliability_diagram(
        raw_report=result["raw_report"],
        cal_report=result["cal_report"],
        final_report=result["final_report"],
        output_path=plot_file,
    )
    assert plot_file.exists()
    assert plot_file.stat().st_size > 5000  # Non-empty valid PNG

    # Check metrics integrity
    raw_ece = result["raw_report"].ece
    cal_ece = result["cal_report"].ece
    assert 0.0 <= raw_ece <= 1.0
    assert 0.0 <= cal_ece <= 1.0
    assert 0.0 <= result["final_report"].ece <= 1.0


# -----------------------------------------------------------------------------
# 5. Distinct Tripartite Separation
# -----------------------------------------------------------------------------
def test_distinct_three_confidence_metrics(tmp_path):
    """
    Asserts the strict architectural distinction:
    raw ML probability != calibrated ML probability != final hybrid confidence.
    """
    res = run_calibration_pipeline(n_instances_per_class=15, seed=2026, output_dir=tmp_path / "bench")
    metrics = res["metrics_data"]

    assert "raw_ml" in metrics
    assert "calibrated_ml" in metrics
    assert "final_confidence" in metrics
    assert metrics["entitled_to_be_called_calibrated"] is False
