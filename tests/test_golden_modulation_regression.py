"""
Phase 9: Golden Modulation Regression Tests.
Executes the genuine blind pipeline on official golden captures (G1-G10).
Truth metadata is used SOLELY in test assertions, never passed into the runtime pipeline.
"""

import json
from pathlib import Path
import pytest

from spectralq.pipeline.runner import run


GOLDEN_DIR = Path("data/official/sinchana/golden")


def test_g1_qpsk_uncoded_blind_inference():
    """Verify G1 is classified as QPSK by ML, Rule, and Top Hypothesis (not 16-QAM)."""
    p = GOLDEN_DIR / "G1_QPSK_uncoded.cf32"
    if not p.exists():
        pytest.skip(f"Golden capture {p} not found")

    pipeline_res = run(str(p), mode="live")
    res = pipeline_res.result

    assert res.top_hypothesis.modulation == "QPSK", f"Expected QPSK, got {res.top_hypothesis.modulation}"
    assert res.ml_prediction == "QPSK", f"Expected ML QPSK, got {res.ml_prediction}"
    assert res.rule_prediction == "QPSK", f"Expected Rule QPSK, got {res.rule_prediction}"
    assert res.unknown is False, "G1 clean QPSK should be confirmed, not UNKNOWN"
    assert res.final_confidence > 0.85, f"Expected confidence > 0.85, got {res.final_confidence}"


def test_g2_bpsk_conv_blind_inference():
    """Verify G2 is classified as BPSK."""
    p = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    if not p.exists():
        pytest.skip(f"Golden capture {p} not found")

    pipeline_res = run(str(p), mode="live")
    res = pipeline_res.result

    assert res.top_hypothesis.modulation == "BPSK"
    assert res.ml_prediction == "BPSK"
    assert res.unknown is False


def test_g3_8psk_rs_blind_inference():
    """Verify G3 is classified as 8-PSK by ML and top hypothesis."""
    p = GOLDEN_DIR / "G3_8PSK_RS_diagonal.cf32"
    if not p.exists():
        pytest.skip(f"Golden capture {p} not found")

    pipeline_res = run(str(p), mode="live")
    res = pipeline_res.result

    assert res.top_hypothesis.modulation == "8-PSK"
    assert res.ml_prediction == "8-PSK"


def test_g4_16qam_ldpc_blind_inference():
    """Verify G4 is classified as 16-QAM by ML and top hypothesis."""
    p = GOLDEN_DIR / "G4_16QAM_LDPC_pseudorandom.cf32"
    if not p.exists():
        pytest.skip(f"Golden capture {p} not found")

    pipeline_res = run(str(p), mode="live")
    res = pipeline_res.result

    assert res.top_hypothesis.modulation == "16-QAM"
    assert res.ml_prediction == "16-QAM"


def test_g6_bpsk_conv_blind_inference():
    """Verify G6 is classified as BPSK."""
    p = GOLDEN_DIR / "G6_BPSK_conv_interleaved.cf32"
    if not p.exists():
        pytest.skip(f"Golden capture {p} not found")

    pipeline_res = run(str(p), mode="live")
    res = pipeline_res.result

    assert res.top_hypothesis.modulation == "BPSK"
    assert res.unknown is False


def test_g7_near_threshold_stress_abstention():
    """Verify G7 near-threshold capture abstains with UNKNOWN due to degraded SNR."""
    p = GOLDEN_DIR / "G7_QPSK_conv_near_threshold.cf32"
    if not p.exists():
        pytest.skip(f"Golden capture {p} not found")

    pipeline_res = run(str(p), mode="live")
    res = pipeline_res.result

    assert res.unknown is True, "G7 near-threshold degraded signal must abstain with UNKNOWN"
    assert res.unknown_reason is not None and len(res.unknown_reason) > 0


def test_g10_pure_noise_abstention():
    """Verify G10 pure AWGN noise abstains with UNKNOWN."""
    p = GOLDEN_DIR / "G10_Noise_Only_AWGN.cf32"
    if not p.exists():
        pytest.skip(f"Golden capture {p} not found")

    pipeline_res = run(str(p), mode="live")
    res = pipeline_res.result

    assert res.unknown is True, "G10 noise-only input must abstain with UNKNOWN"
    assert res.unknown_reason is not None
