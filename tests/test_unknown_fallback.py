"""
Tests for UNKNOWN Fallback Logic and Operational Gatekeeping.
"""

import pytest
from spectralq.evidence_ledger.thresholds import evaluate_decision_label, DEFAULT_CONFIDENCE_THRESHOLD
from spectralq.contracts.schemas import LadderLevel


def test_unknown_no_valid_burst():
    label, reason = evaluate_decision_label(
        top_modulation="BPSK",
        fused_confidence=0.85,
        ladder_level=LadderLevel.L2,
        n5_agreement=True,
        n5_agreement_score=0.9,
        cross_window_score=0.9,
        snr_db=20.0,
        is_valid_burst=False,
    )
    assert label == "UNKNOWN"
    assert "NO_VALID_BURST" in reason


def test_unknown_low_snr_floor():
    label, reason = evaluate_decision_label(
        top_modulation="QPSK",
        fused_confidence=0.85,
        ladder_level=LadderLevel.L3,
        n5_agreement=True,
        n5_agreement_score=0.9,
        cross_window_score=0.9,
        snr_db=-1.5,  # Below 1.0 dB minimum floor
        is_valid_burst=True,
    )
    assert label == "UNKNOWN"
    assert "SNR_BELOW_OPERATIONAL_FLOOR" in reason


def test_unknown_window_instability():
    label, reason = evaluate_decision_label(
        top_modulation="16-QAM",
        fused_confidence=0.75,
        ladder_level=LadderLevel.L3,
        n5_agreement=True,
        n5_agreement_score=0.8,
        cross_window_score=0.20,  # Below 0.35 stability floor
        snr_db=25.0,
        is_valid_burst=True,
    )
    assert label == "UNKNOWN"
    assert "CROSS_WINDOW_INSTABILITY" in reason


def test_unknown_low_confidence_below_threshold():
    label, reason = evaluate_decision_label(
        top_modulation="8-PSK",
        fused_confidence=0.45,  # Below default 0.60
        ladder_level=LadderLevel.L3,
        n5_agreement=True,
        n5_agreement_score=0.7,
        cross_window_score=0.8,
        snr_db=15.0,
        is_valid_burst=True,
        threshold=0.60,
    )
    assert label == "UNKNOWN"
    assert "CONFIDENCE_BELOW_THRESHOLD" in reason


def test_assertion_when_evidence_valid():
    label, reason = evaluate_decision_label(
        top_modulation="BPSK",
        fused_confidence=0.88,
        ladder_level=LadderLevel.L4,
        n5_agreement=True,
        n5_agreement_score=0.9,
        cross_window_score=0.95,
        snr_db=22.0,
        is_valid_burst=True,
        threshold=0.60,
    )
    assert label == "BPSK"
    assert reason is None
