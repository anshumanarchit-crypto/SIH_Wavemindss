"""
Tests for N2 Confidence Fusion Engine.
Validates multi-evidence logistic regression fusion, bounding, and sensitivity to penalties.
"""

import pytest
from spectralq.evidence_ledger.confidence_fusion import ConfidenceFusionEngine, evaluate_cross_window_agreement
from spectralq.contracts.schemas import SubWindowMetrics


def test_confidence_fusion_bounding():
    engine = ConfidenceFusionEngine()

    # Extreme high evidence inputs
    conf_high, breakdown_high = engine.compute_confidence(
        ml_calibrated_prob=0.99,
        n5_agreement_score=1.0,
        cross_window_agreement_score=1.0,
        verification_evidence_score=1.0,
        evm=0.01,
        snr_db=30.0,
    )
    assert 0.0 <= conf_high <= 1.0
    assert conf_high > 0.85
    assert conf_high != 0.95  # Strict check against hardcoded 95%

    # Extreme low evidence inputs
    conf_low, breakdown_low = engine.compute_confidence(
        ml_calibrated_prob=0.10,
        n5_agreement_score=0.10,
        cross_window_agreement_score=0.10,
        verification_evidence_score=0.05,
        evm=0.85,
        snr_db=-2.0,
    )
    assert 0.0 <= conf_low <= 1.0
    assert conf_low < 0.25


def test_confidence_evm_penalty():
    engine = ConfidenceFusionEngine()

    conf_clean, _ = engine.compute_confidence(
        ml_calibrated_prob=0.85,
        n5_agreement_score=0.85,
        cross_window_agreement_score=0.90,
        verification_evidence_score=0.70,
        evm=0.04,
        snr_db=20.0,
    )

    conf_noisy, _ = engine.compute_confidence(
        ml_calibrated_prob=0.85,
        n5_agreement_score=0.85,
        cross_window_agreement_score=0.90,
        verification_evidence_score=0.70,
        evm=0.65,  # Much higher EVM
        snr_db=20.0,
    )

    assert conf_clean > conf_noisy


def test_cross_window_agreement_calculation():
    # Stable windows
    stable_windows = [
        SubWindowMetrics(window_idx=0, estimated_snr_db=20.0, estimated_c42=-1.9, estimated_c20=0.98, cluster_count=2),
        SubWindowMetrics(window_idx=1, estimated_snr_db=20.1, estimated_c42=-1.91, estimated_c20=0.97, cluster_count=2),
        SubWindowMetrics(window_idx=2, estimated_snr_db=19.9, estimated_c42=-1.89, estimated_c20=0.99, cluster_count=2),
    ]
    score_stable = evaluate_cross_window_agreement(stable_windows)
    assert score_stable > 0.85

    # Unstable drifting windows
    unstable_windows = [
        SubWindowMetrics(window_idx=0, estimated_snr_db=20.0, estimated_c42=-1.9, estimated_c20=0.98, cluster_count=2),
        SubWindowMetrics(window_idx=1, estimated_snr_db=10.0, estimated_c42=-0.5, estimated_c20=0.2, cluster_count=4),
        SubWindowMetrics(window_idx=2, estimated_snr_db=5.0, estimated_c42=0.2, estimated_c20=0.0, cluster_count=8),
    ]
    score_unstable = evaluate_cross_window_agreement(unstable_windows)
    assert score_unstable < score_stable
