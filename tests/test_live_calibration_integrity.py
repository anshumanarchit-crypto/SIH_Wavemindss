"""
Tests for Live Calibration Integrity (Phase 2).

Validates the full calibration trace:
ML prediction -> raw probability -> actual calibration module -> calibrated probability -> confidence engine -> final result.

Invariants:
- raw_ml_probability remains strictly raw from base estimators.
- calibrated_ml_probability exists only when actual calibration occurs.
- calibrated_ml_probability != raw_ml_probability (no copying).
- no heuristic multipliers.
- uncalibrated/stub models emit calibrated_probability = None.
- ConfidenceEngine correctly flags provisional vs calibrated ML probability.
"""

from pathlib import Path
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from spectralq.integration.classifier_adapter import ClassifierAdapter
from spectralq.contracts.schemas import ClassifierOutputContract, ResultContract
from spectralq.pipeline.runner import run_samples, get_stub_classifier_output
from tests.test_adversarial_suite import make_bpsk


def test_baseline_model_calibrated_separation():
    """Verify that baseline_rf.joblib produces distinct raw and calibrated probabilities."""
    model_path = Path("models/baseline_rf.joblib")
    if not model_path.exists():
        pytest.skip("models/baseline_rf.joblib not present")

    adapter = ClassifierAdapter.load_from_file(str(model_path))
    sample_feat = {
        "C20": 0.8,
        "C21": 1.0,
        "C40": 0.5,
        "C42": -0.9,
        "C60": 0.0,
        "C63": 0.0,
        "C80": 0.0,
        "cluster_count": 4,
        "silhouette": 0.85,
        "intra_var": 0.05,
        "inter_dist": 1.2,
        "evm": 8.5,
        "phase_ambiguity_quality": 0.95,
        "snr": 18.0,
        "baud": 2400.0,
    }

    output = adapter.predict(sample_feat, capture_id="TEST_CALIB_SEP")
    assert isinstance(output, ClassifierOutputContract)
    assert output.calibrated_probability is not None
    assert 0.0 <= output.calibrated_probability <= 1.0

    raw_prob = output.ml_probabilities[output.ml_prediction]
    assert 0.0 <= raw_prob <= 1.0
    # Must be distinct values from two separate mathematical layers
    assert output.calibrated_probability != raw_prob
    assert abs(output.calibrated_probability - raw_prob) > 0.001


def test_uncalibrated_model_emits_none():
    """An uncalibrated RandomForestClassifier must emit calibrated_probability = None."""
    X_train = np.random.randn(20, 15)
    y_train = np.array(["QPSK", "BPSK"] * 10)
    rf = RandomForestClassifier(n_estimators=10, random_state=42)
    rf.fit(X_train, y_train)

    adapter = ClassifierAdapter(model=rf, model_version="rf-uncalibrated-test")
    sample_feat = {f: 0.1 for f in adapter.expected_features}
    output = adapter.predict(sample_feat, capture_id="TEST_UNCALIB")

    assert output.calibrated_probability is None
    assert output.ml_prediction in ["QPSK", "BPSK"]
    assert output.ml_probabilities[output.ml_prediction] > 0.0


def test_fallback_and_stub_emit_none():
    """Deterministic fallback and stub classifier must emit calibrated_probability = None."""
    adapter = ClassifierAdapter(model=None, model_version="mock-fallback")
    sample_feat = {f: 0.1 for f in adapter.expected_features}
    output = adapter.predict(sample_feat, capture_id="TEST_FALLBACK")
    assert output.calibrated_probability is None

    # Stub classifier in runner
    from spectralq.features.iq_extractor import iq_to_analysis_contract
    sig = make_bpsk(snr_db=20.0, seed=42)
    analysis = iq_to_analysis_contract(sig, fs_hz=1e6, meta={"sps": 8}, capture_id="STUB_TEST")
    stub_out = get_stub_classifier_output("STUB_TEST", analysis)
    assert stub_out.calibrated_probability is None


def test_pipeline_runner_calibrated_trace():
    """Full live pipeline execution must propagate calibrated probability through confidence engine."""
    model_path = Path("models/baseline_rf.joblib")
    if not model_path.exists():
        pytest.skip("models/baseline_rf.joblib not present")

    iq = make_bpsk(snr_db=20.0, seed=42)
    res = run_samples(iq, fs_hz=1e6, meta={"sps": 8}, capture_id="TEST_PIPE_CALIB", mode="live")

    assert isinstance(res.result, ResultContract)
    assert res.result.calibrated_ml_probability is not None
    assert res.result.ml_probability is not None
    assert 0.0 <= res.result.calibrated_ml_probability <= 1.0
    assert 0.0 <= res.result.ml_probability <= 1.0
    assert res.result.calibrated_ml_probability != res.result.ml_probability


def test_no_heuristic_multipliers():
    """Verify that calibration is a non-linear probability mapping, not a fixed scaling factor."""
    model_path = Path("models/baseline_rf.joblib")
    if not model_path.exists():
        pytest.skip("models/baseline_rf.joblib not present")

    adapter = ClassifierAdapter.load_from_file(str(model_path))

    # Evaluate multiple synthetic feature vectors
    ratios = []
    for snr in [5.0, 12.0, 20.0]:
        sample_feat = {
            "C20": 0.8,
            "C21": 1.0,
            "C40": 0.5,
            "C42": -0.9,
            "C60": 0.0,
            "C63": 0.0,
            "C80": 0.0,
            "cluster_count": 4,
            "silhouette": 0.85,
            "intra_var": 0.05,
            "inter_dist": 1.2,
            "evm": 25.0 - snr,
            "phase_ambiguity_quality": 0.95,
            "snr": snr,
            "baud": 2400.0,
        }
        out = adapter.predict(sample_feat, capture_id=f"TEST_SNR_{snr}")
        raw = out.ml_probabilities[out.ml_prediction]
        cal = out.calibrated_probability
        assert cal is not None
        ratios.append(cal / raw)

    # Ratios must not all be identical (which would indicate a fixed scaling factor)
    assert len(set(np.round(ratios, 3))) > 1, f"Calibration appears to be a constant multiplier: {ratios}"
