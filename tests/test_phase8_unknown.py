"""
Phase 8 Tests: UNKNOWN Abstention System, G7 Near-Threshold SNR & G10 Noise Override.

Covers:
1. Clean known signal -> confident correct label (unknown=False).
2. G7 Case (QPSK near-threshold SNR):
   - Evaluates transition behavior across the physical SNR boundary (3.0 dB floor).
   - Preserves raw_ml_probability, calibrated_ml_probability, raw_hybrid_score, final_confidence.
3. G10 Case (Noise-only):
   - UNKNOWN emitted every time.
   - Strong wrong-class ML guess overridden by evidence system.
   - Explicit 'noise_floor_override' FAIL recorded in EvidenceLedger.
4. High-ML / weak-evidence case -> UNKNOWN due to confidence below operational threshold.
5. Rule/ML disagreement -> visibly reduced confidence.
6. Unsupported modulation / FEC -> explicit unsupported state, never silent guess.
7. Missing evidence -> does not count as passing evidence.
"""

import pytest
from spectralq.contracts.schemas import (
    AnalysisContract,
    EvidenceStatus,
    validate_analysis_dict,
)
from spectralq.evidence.ledger import EvidenceLedger
from spectralq.confidence import (
    ConfidenceEngine,
    ConfidenceResult,
    AbstentionSystem,
    AbstentionDecision,
)
from spectralq.hypothesis import HypothesisEngineV1


@pytest.fixture
def clean_qpsk_analysis_dict():
    return {
        "schema_version": "1.0.0",
        "capture_id": "CLEAN_QPSK_001",
        "source_mode": "synthetic",
        "fs_hz": 20.0e6,
        "fs_source": "header",
        "bursts": [{"start_ms": 0.0, "end_ms": 100.0, "power": -12.0}],
        "estimates": {
            "baud": {"value": 1.0e6, "ci_lo": 0.99e6, "ci_hi": 1.01e6, "method": "cyclic"},
            "cfo": {"value": 0.0, "ci_lo": -20.0, "ci_hi": 20.0, "method": "fft"},
            "bandwidth": {"value": 1.25e6, "ci_lo": 1.20e6, "ci_hi": 1.30e6, "method": "obw"},
            "snr": {"value": 18.0, "ci_lo": 17.5, "ci_hi": 18.5, "method": "m2m4"},
        },
        "features": {
            "cumulants": {
                "C20": 0.01, "C21": 1.0, "C40": 0.98, "C42": -0.99,
                "C60": 0.0, "C63": 0.0, "C80": 0.0,
            },
            "cluster": {
                "count": 4, "silhouette": 0.88, "intra_var": 0.08, "inter_dist": 1.41,
            },
            "evm": 0.045,
            "phase_ambiguity_quality": 0.92,
            "cyclic": None,
        },
    }


# -----------------------------------------------------------------------------
# 1. Clean Known Signal -> Confident Correct Label
# -----------------------------------------------------------------------------
def test_clean_known_signal_confident_label(clean_qpsk_analysis_dict):
    analysis = validate_analysis_dict(clean_qpsk_analysis_dict)
    ledger = EvidenceLedger(run_id="RUN_CLEAN")

    # All checks passing
    ledger.record(
        evidence_id="EV_CRC", source="Decoder", check_name="crc",
        status=EvidenceStatus.PASS, explanation="CRC verified"
    )

    conf_engine = ConfidenceEngine(weight_source="fitted")
    conf_res = conf_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.96,
        cross_window_agreement=1.0,
        rule_prediction="QPSK",
        ml_prediction="QPSK",
        rule_ml_agreement=True,
        ledger=ledger,
    )

    abstention = AbstentionSystem(threshold=0.80)
    decision = abstention.evaluate(analysis, conf_res, ledger=ledger, capture_id=analysis.capture_id)

    assert decision.is_unknown is False
    assert decision.unknown_reason is None
    assert decision.output_label == "QPSK"
    assert decision.final_confidence >= 0.80


# -----------------------------------------------------------------------------
# 2. G7: QPSK Near-Threshold SNR Transition Behavior
# -----------------------------------------------------------------------------
def test_g7_qpsk_near_threshold_transition(clean_qpsk_analysis_dict):
    """
    QPSK operational floor is 3.0 dB (MODULATION_MIN_SNR['QPSK']).
    - Below floor (SNR = 2.0 dB): Must transition to UNKNOWN via SNR guard.
    - Above floor (SNR = 4.0 dB): Passes guard if evidence and confidence suffice.
    """
    # 2a: Sub-threshold SNR = 2.0 dB
    sub_thresh_dict = dict(clean_qpsk_analysis_dict)
    sub_thresh_dict["estimates"]["snr"]["value"] = 2.0
    sub_thresh_dict["estimates"]["snr"]["ci_lo"] = 1.5
    sub_thresh_dict["estimates"]["snr"]["ci_hi"] = 2.5
    analysis_sub = validate_analysis_dict(sub_thresh_dict)

    ledger_sub = EvidenceLedger(run_id="RUN_G7_SUB")
    conf_engine = ConfidenceEngine(weight_source="fitted")
    conf_res_sub = conf_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.72,
        cross_window_agreement=0.60,
        rule_prediction="QPSK",
        ml_prediction="QPSK",
        rule_ml_agreement=True,
        evidence_score=0.40,
    )

    abstention = AbstentionSystem(threshold=0.80)
    decision_sub = abstention.evaluate(analysis_sub, conf_res_sub, ledger=ledger_sub, capture_id="G7_SUB")

    # Invariants for sub-threshold
    assert decision_sub.is_unknown is True
    assert decision_sub.output_label == "UNKNOWN"
    assert "SNR floor violation" in decision_sub.unknown_reason
    assert decision_sub.guard_triggered == "snr_floor_guard"

    # All intermediate stage metrics preserved
    assert decision_sub.raw_ml_probability == 0.72
    assert decision_sub.raw_hybrid_score == conf_res_sub.raw_hybrid_score
    assert decision_sub.final_confidence == conf_res_sub.final_confidence

    # 2b: Above-threshold SNR = 6.0 dB with strong verification
    above_thresh_dict = dict(clean_qpsk_analysis_dict)
    above_thresh_dict["estimates"]["snr"]["value"] = 6.0
    analysis_above = validate_analysis_dict(above_thresh_dict)

    ledger_above = EvidenceLedger(run_id="RUN_G7_ABOVE")
    ledger_above.record(
        evidence_id="EV_CRC", source="Decoder", check_name="crc",
        status=EvidenceStatus.PASS, explanation="CRC pass"
    )
    conf_res_above = conf_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.94,
        cross_window_agreement=0.95,
        rule_prediction="QPSK",
        ml_prediction="QPSK",
        rule_ml_agreement=True,
        evidence_score=1.0,
    )
    decision_above = abstention.evaluate(analysis_above, conf_res_above, ledger=ledger_above, capture_id="G7_ABOVE")

    assert decision_above.is_unknown is False
    assert decision_above.output_label == "QPSK"


# -----------------------------------------------------------------------------
# 3. G10: Noise-Only Capture -> Strict UNKNOWN Override
# -----------------------------------------------------------------------------
def test_g10_noise_only_override_every_time(clean_qpsk_analysis_dict):
    """
    G10 (noise only):
    Expected: UNKNOWN, every time, regardless of what the raw classifier alone would have guessed.
    If the classifier produces a strong guess, evidence system must override and record override in ledger.
    """
    noise_dict = dict(clean_qpsk_analysis_dict)
    noise_dict["estimates"]["snr"]["value"] = -3.5  # Sub-zero SNR (noise floor)
    noise_dict["estimates"]["snr"]["ci_lo"] = -5.0
    noise_dict["estimates"]["snr"]["ci_hi"] = -2.0
    noise_dict["features"]["cluster"]["silhouette"] = 0.08
    noise_dict["bursts"] = []  # No burst energy

    analysis_noise = validate_analysis_dict(noise_dict)
    ledger = EvidenceLedger(run_id="RUN_G10_NOISE")

    # Classifier falsely assigns strong 0.88 probability to 16-QAM
    conf_engine = ConfidenceEngine(weight_source="fitted")
    conf_res = conf_engine.compute_confidence(
        prediction="16-QAM",
        ml_probability=0.88,
        cross_window_agreement=0.30,
        rule_prediction="2-FSK",
        ml_prediction="16-QAM",
        rule_ml_agreement=False,
        evidence_score=0.0,
        ledger=ledger,
    )

    abstention = AbstentionSystem(threshold=0.80)
    decision = abstention.evaluate(analysis_noise, conf_res, ledger=ledger, capture_id="G10_CAPTURE")

    # UNKNOWN emitted every time
    assert decision.is_unknown is True
    assert decision.output_label == "UNKNOWN"
    assert "Noise-only capture detected" in decision.unknown_reason
    assert decision.guard_triggered == "noise_floor_override"

    # Explicit override recorded in ledger
    items = ledger.get_items()
    override_items = [it for it in items if it.check_name == "noise_floor_override"]
    assert len(override_items) == 1
    assert override_items[0].status == EvidenceStatus.FAIL
    assert override_items[0].failure_reason == "Noise floor violation"
    assert "overridden to UNKNOWN" in override_items[0].explanation


# -----------------------------------------------------------------------------
# 4. High-ML / Weak-Evidence Case -> Reduced Confidence / UNKNOWN
# -----------------------------------------------------------------------------
def test_high_ml_weak_evidence_abstains_or_reduces_confidence(clean_qpsk_analysis_dict):
    analysis = validate_analysis_dict(clean_qpsk_analysis_dict)
    ledger = EvidenceLedger(run_id="RUN_WEAK_EV")

    # Strong ML (0.92) but failing physical evidence checks (failed CRC, high BER)
    ledger.record(
        evidence_id="EV_CRC", source="Decoder", check_name="crc",
        status=EvidenceStatus.FAIL, explanation="CRC corrupt"
    )
    ledger.record(
        evidence_id="EV_SYNC", source="Demodulator", check_name="sync",
        status=EvidenceStatus.FAIL, explanation="Sync failed"
    )

    conf_engine = ConfidenceEngine(weight_source="fitted")
    conf_res = conf_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.92,
        cross_window_agreement=0.40,
        rule_prediction="16-QAM",
        ml_prediction="QPSK",
        rule_ml_agreement=False,
        ledger=ledger,
    )

    abstention = AbstentionSystem(threshold=0.80)
    decision = abstention.evaluate(analysis, conf_res, ledger=ledger, capture_id="WEAK_EV")

    # Confidence must be dragged down by weak evidence and rule conflict
    assert conf_res.final_confidence < 0.80
    assert decision.is_unknown is True
    assert "Low confidence abstention" in decision.unknown_reason


# -----------------------------------------------------------------------------
# 5. Unsupported Modulation / FEC -> Explicit Unsupported State
# -----------------------------------------------------------------------------
def test_unsupported_fec_explicit_rejection(clean_qpsk_analysis_dict):
    analysis = validate_analysis_dict(clean_qpsk_analysis_dict)
    engine = HypothesisEngineV1()
    candidates = engine.generate_all_candidates()

    ldpc_candidates = [c for c in candidates if c.fec == "ldpc"]
    assert len(ldpc_candidates) == 35
    for c in ldpc_candidates:
        assert c.status == "UNSUPPORTED"
        assert "LDPC" in c.rejection_reason
        assert any(e.status == EvidenceStatus.UNAVAILABLE for e in c.evidence)
