"""
Regression test suite for Phase 9: Known QPSK Golden Classification.

Guarantees that the known QPSK golden capture (G1) is accurately and honestly
classified as QPSK by both the Rule-based AMC and the Calibrated Machine Learning
classifier, preventing the historical regression where QPSK was misclassified as 16-QAM.

Strict Invariant:
No truth data or metadata is injected into the runtime inference path.
Truth labels are strictly confined to test assertions.
"""

from pathlib import Path
import pytest
from spectralq.pipeline.runner import run
from spectralq.contracts.schemas import LadderLevel


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_qPSK_golden_capture_classifies_as_qpsk_not_16qam():
    """
    Critical Regression Test (Phase 9):
    A known QPSK golden capture (G1) must be classified as QPSK by both the
    ML model and the rule engine, resolving to top_hypothesis.modulation == 'QPSK'.
    Under no circumstances should it fall through to 16-QAM.
    """
    # Prefer sample_captures/07_QPSK_uncoded_golden.cf32 or data/official/sinchana/golden/G1_QPSK_uncoded.cf32
    cap_candidates = [
        REPO_ROOT / "sample_captures" / "07_QPSK_uncoded_golden.cf32",
        REPO_ROOT / "data" / "official" / "sinchana" / "golden" / "G1_QPSK_uncoded.cf32",
    ]
    cap_path = None
    for c in cap_candidates:
        if c.exists():
            cap_path = c
            break

    assert cap_path is not None, f"Neither candidate QPSK capture file exists: {cap_candidates}"

    # Execute the end-to-end real pipeline in live mode
    pipe_out = run(capture_path=str(cap_path), mode="live")
    res = pipe_out.result

    # Assertions
    assert res is not None, "Pipeline failed to produce a valid ResultContract"
    assert res.rule_prediction == "QPSK", (
        f"Rule AMC failed: expected QPSK, got '{res.rule_prediction}'. "
        f"Cumulants: C40={pipe_out.analysis.features.cumulants.C40}, C42={pipe_out.analysis.features.cumulants.C42}"
    )
    assert res.ml_prediction == "QPSK", (
        f"ML classifier failed: expected QPSK, got '{res.ml_prediction}' "
        f"with probability {res.ml_probability:.4f}"
    )
    assert res.top_hypothesis.modulation == "QPSK", (
        f"Decision engine top hypothesis failed: expected QPSK, got '{res.top_hypothesis.modulation}'"
    )
    assert res.unknown is False, f"Pipeline abstained unexpectedly: {res.unknown_reason}"
    assert res.rule_ml_agreement is True, "Rule and ML should reach consensus on clean QPSK capture"
    assert res.ladder_level in (LadderLevel.L2, LadderLevel.L3, LadderLevel.L4, LadderLevel.L5), (
        f"Expected ladder level >= L2 for QPSK golden capture, got {res.ladder_level}"
    )


def test_bpsk_golden_capture_classifies_as_bpsk():
    """Verifies that BPSK clean capture is identified as BPSK."""
    cap_candidates = [
        REPO_ROOT / "sample_captures" / "01_BPSK_clean_20dB.wav",
        REPO_ROOT / "sample_captures" / "08_BPSK_conv_block.cf32",
    ]
    cap_path = next((c for c in cap_candidates if c.exists()), None)
    assert cap_path is not None, "No BPSK capture found"

    pipe_out = run(capture_path=str(cap_path), mode="live")
    res = pipe_out.result
    assert res.top_hypothesis.modulation == "BPSK"
    assert res.unknown is False


def test_8psk_capture_classifies_as_8psk():
    """Verifies that 8-PSK capture candidate is identified as 8-PSK."""
    cap_candidates = [
        REPO_ROOT / "sample_captures" / "15_8PSK_carrier_locked_18dB.wav",
        REPO_ROOT / "sample_captures" / "09_8PSK_RS_diagonal.cf32",
    ]
    cap_path = next((c for c in cap_candidates if c.exists()), None)
    assert cap_path is not None, "No 8-PSK capture found"

    pipe_out = run(capture_path=str(cap_path), mode="live")
    res = pipe_out.result
    assert res.top_hypothesis.modulation == "8-PSK"


def test_16qam_capture_classifies_as_16qam():
    """Verifies that 16-QAM capture candidate is identified as 16-QAM."""
    cap_candidates = [
        REPO_ROOT / "sample_captures" / "04_16QAM_high_density_22dB.wav",
        REPO_ROOT / "sample_captures" / "10_16QAM_LDPC_pseudo.cf32",
    ]
    cap_path = next((c for c in cap_candidates if c.exists()), None)
    assert cap_path is not None, "No 16-QAM capture found"

    pipe_out = run(capture_path=str(cap_path), mode="live")
    res = pipe_out.result
    assert res.top_hypothesis.modulation == "16-QAM"
