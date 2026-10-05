"""
Phase 3 Unit and Integration Tests for Hypothesis Engine V1.

Tests required:
1. Candidate generation completeness (exactly 175 combinations: 7 x 5 x 5).
2. Pruning correctness (SNR floor, bit length mismatch, negligible classifier prob).
3. LDPC-unavailable handling (35 candidates marked UNSUPPORTED, never faked).
4. Evidence state handling (all 4 states: PASS, FAIL, NOT_RUN, UNAVAILABLE).
5. Deterministic ranking given identical input.
6. One full G1-style pass (QPSK x block x conv_viterbi_k7).
7. One full G2-style pass (2-FSK x none x none or BPSK x none x rs_255_223).
"""

import pytest

from spectralq.contracts.schemas import (
    AnalysisContract,
    ClassifierOutputContract,
    DecoderOutputContract,
    DecoderStatus,
    CrcStatus,
    EvidenceStatus,
    validate_analysis_dict,
    validate_classifier_output_dict,
    validate_decoder_output_dict,
)
from spectralq.hypothesis import (
    HypothesisEngineV1,
    HypothesisCandidate,
    format_hypothesis_dump,
    MODULATIONS,
    INTERLEAVERS,
    FEC_SCHEMES,
)


@pytest.fixture
def g1_analysis_data():
    """G1 Case: Standard clean QPSK signal with 20 dB SNR."""
    return {
        "schema_version": "1.0.0",
        "capture_id": "G1_QPSK_BURST_001",
        "source_mode": "synthetic",
        "fs_hz": 20.0e6,
        "fs_source": "header",
        "bursts": [
            {"start_ms": 10.0, "end_ms": 110.0, "power": -12.0}
        ],
        "estimates": {
            "baud": {"value": 1.0e6, "ci_lo": 0.99e6, "ci_hi": 1.01e6, "method": "cyclic"},
            "cfo": {"value": 100.0, "ci_lo": 50.0, "ci_hi": 150.0, "method": "fft"},
            "bandwidth": {"value": 1.3e6, "ci_lo": 1.25e6, "ci_hi": 1.35e6, "method": "obw"},
            "snr": {"value": 20.0, "ci_lo": 19.0, "ci_hi": 21.0, "method": "m2m4"},
        },
        "features": {
            "cumulants": {
                "C20": 0.01, "C21": 1.0, "C40": 0.98, "C42": -0.99,
                "C60": 0.0, "C63": 0.0, "C80": 0.0,
            },
            "cluster": {
                "count": 4, "silhouette": 0.90, "intra_var": 0.05, "inter_dist": 1.41,
            },
            "evm": 0.035,
            "phase_ambiguity_quality": 0.95,
            "cyclic": None,
        },
    }


@pytest.fixture
def g1_classifier_data():
    """G1 Case: Classifier confidently predicts QPSK."""
    return {
        "schema_version": "1.0.0",
        "capture_id": "G1_QPSK_BURST_001",
        "window_id": 0,
        "ml_prediction": "QPSK",
        "ml_probabilities": {
            "BPSK": 0.01,
            "QPSK": 0.94,
            "8-PSK": 0.02,
            "16-QAM": 0.01,
            "64-QAM": 0.005,
            "2-FSK": 0.005,
            "4-FSK": 0.01,
        },
        "calibrated_probability": 0.92,
        "model_version": "rf-baseline-1.0.0",
        "feature_vector_used": {"C20": 0.01, "C40": 0.98, "C42": -0.99, "snr": 20.0},
    }


@pytest.fixture
def g1_decoder_data():
    """G1 Case: Decoder verified QPSK x block x conv_viterbi_k7 with sync pass, CRC pass, and low BER."""
    return {
        "schema_version": "1.0.0",
        "capture_id": "G1_QPSK_BURST_001",
        "status": "ok",
        "interleaver_used": "block",
        "fec_used": "conv_viterbi_k7",
        "decoded_bits": "110010101111000010101100" * 4,  # 96 bits
        "crc_status": "pass",
        "reencode_ber": 0.001,
        "failure_reason": None,
    }


@pytest.fixture
def g2_analysis_data():
    """G2 Case: Clean 2-FSK unencoded telemetry signal with 16 dB SNR."""
    return {
        "schema_version": "1.0.0",
        "capture_id": "G2_2FSK_BURST_002",
        "source_mode": "synthetic",
        "fs_hz": 10.0e6,
        "fs_source": "header",
        "bursts": [
            {"start_ms": 5.0, "end_ms": 95.0, "power": -15.0}
        ],
        "estimates": {
            "baud": {"value": 50.0e3, "ci_lo": 49.5e3, "ci_hi": 50.5e3, "method": "cyclic"},
            "cfo": {"value": 0.0, "ci_lo": -50.0, "ci_hi": 50.0, "method": "fft"},
            "bandwidth": {"value": 120.0e3, "ci_lo": 115.0e3, "ci_hi": 125.0e3, "method": "obw"},
            "snr": {"value": 16.0, "ci_lo": 15.0, "ci_hi": 17.0, "method": "m2m4"},
        },
        "features": {
            "cumulants": {
                "C20": 0.01, "C21": 1.0, "C40": 0.05, "C42": -0.95,
                "C60": 0.0, "C63": 0.0, "C80": 0.0,
            },
            "cluster": {
                "count": 2, "silhouette": 0.85, "intra_var": 0.10, "inter_dist": 1.0,
            },
            "evm": 0.08,
            "phase_ambiguity_quality": 0.88,
            "cyclic": None,
        },
    }


@pytest.fixture
def g2_classifier_data():
    """G2 Case: Classifier predicts 2-FSK."""
    return {
        "schema_version": "1.0.0",
        "capture_id": "G2_2FSK_BURST_002",
        "window_id": 0,
        "ml_prediction": "2-FSK",
        "ml_probabilities": {
            "BPSK": 0.02,
            "QPSK": 0.01,
            "8-PSK": 0.01,
            "16-QAM": 0.005,
            "64-QAM": 0.001,
            "2-FSK": 0.91,
            "4-FSK": 0.044,
        },
        "calibrated_probability": 0.89,
        "model_version": "rf-baseline-1.0.0",
        "feature_vector_used": {"C20": 0.01, "C40": 0.05, "C42": -0.95, "snr": 16.0},
    }


@pytest.fixture
def g2_decoder_data():
    """G2 Case: 2-FSK unencoded (none x none) with CRC pass."""
    return {
        "schema_version": "1.0.0",
        "capture_id": "G2_2FSK_BURST_002",
        "status": "ok",
        "interleaver_used": "none",
        "fec_used": "none",
        "decoded_bits": "101010101100110011110000",
        "crc_status": "pass",
        "reencode_ber": 0.0,
        "failure_reason": None,
    }


# -----------------------------------------------------------------------------
# 1. Candidate Generation Completeness (7 x 5 x 5 = 175)
# -----------------------------------------------------------------------------
def test_candidate_generation_completeness():
    engine = HypothesisEngineV1()
    candidates = engine.generate_all_candidates()

    assert len(candidates) == 175  # 7 modulations * 5 interleavers * 5 FECs
    
    # Check that all modulations are present
    mods_present = {c.modulation for c in candidates}
    assert mods_present == set(MODULATIONS)

    # Check that all interleavers are present
    intl_present = {c.interleaver for c in candidates}
    assert intl_present == set(INTERLEAVERS)

    # Check that all FEC schemes are present
    fec_present = {c.fec for c in candidates}
    assert fec_present == set(FEC_SCHEMES)


# -----------------------------------------------------------------------------
# 2. LDPC-Unavailable Handling (Never Silently Dropped or Faked)
# -----------------------------------------------------------------------------
def test_ldpc_unsupported_handling(monkeypatch):
    monkeypatch.setattr("spectralq.hypothesis.engine.UNSUPPORTED_FEC", {"ldpc"})
    engine = HypothesisEngineV1()
    candidates = engine.generate_all_candidates()

    ldpc_cands = [c for c in candidates if c.fec == "ldpc"]
    assert len(ldpc_cands) == 35  # 7 modulations * 5 interleavers * 1 LDPC

    for cand in ldpc_cands:
        assert cand.status == "UNSUPPORTED"
        assert "fec:ldpc" in cand.unsupported_components
        assert cand.rejection_reason is not None
        assert "unsupported" in cand.rejection_reason.lower()
        # Verify an UNAVAILABLE evidence item is recorded
        unavail_items = [e for e in cand.evidence if e.status == EvidenceStatus.UNAVAILABLE]
        assert len(unavail_items) >= 1
        assert unavail_items[0].check_name == "fec_support"


# -----------------------------------------------------------------------------
# 3. Pruning Correctness
# -----------------------------------------------------------------------------
def test_coarse_pruning_snr_and_block_length(g1_analysis_data, g1_classifier_data, g1_decoder_data):
    # Alter SNR to 10 dB: 64-QAM requires 18 dB (min floor 15 dB with 3 dB margin)
    g1_analysis_data["estimates"]["snr"]["value"] = 10.0
    analysis = validate_analysis_dict(g1_analysis_data)
    classifier_out = validate_classifier_output_dict(g1_classifier_data)

    # Set decoded bits to 80 bits (insufficient for RS(255,223) which requires 2040 bits)
    g1_decoder_data["decoded_bits"] = "1" * 80
    decoder_out = validate_decoder_output_dict(g1_decoder_data)

    engine = HypothesisEngineV1()
    candidates = engine.generate_all_candidates()
    engine.apply_coarse_pruning(candidates, analysis, classifier_out, decoder_out)

    # Check that 64-QAM candidates were pruned due to SNR
    qam64_cands = [c for c in candidates if c.modulation == "64-QAM" and c.fec != "ldpc"]
    for c in qam64_cands:
        assert c.status == "PRUNED"
        assert "SNR" in c.rejection_reason

    # Check that RS(255,223) candidates with short bit length were pruned
    rs_cands = [c for c in candidates if c.fec == "rs_255_223" and c.status == "PRUNED"]
    assert len(rs_cands) > 0
    for c in rs_cands:
        assert "insufficient" in c.rejection_reason.lower() or "SNR" in c.rejection_reason


# -----------------------------------------------------------------------------
# 4. Evidence State Handling (All 4 States Reachable and Distinguishable)
# -----------------------------------------------------------------------------
def test_all_four_evidence_states_reachable(monkeypatch, g1_analysis_data, g1_classifier_data, g1_decoder_data):
    monkeypatch.setattr("spectralq.hypothesis.engine.UNSUPPORTED_FEC", {"ldpc"})
    analysis = validate_analysis_dict(g1_analysis_data)
    classifier_out = validate_classifier_output_dict(g1_classifier_data)
    decoder_out = validate_decoder_output_dict(g1_decoder_data)

    engine = HypothesisEngineV1()
    ranked = engine.run(analysis, classifier_out, decoder_out)

    all_statuses = set()
    for c in ranked:
        for ev in c.evidence:
            all_statuses.add(ev.status)

    # All 4 states must be present across the candidates
    assert EvidenceStatus.PASS in all_statuses        # On the matching candidate (sync & CRC pass)
    assert EvidenceStatus.NOT_RUN in all_statuses     # On non-matching candidates (decoder not run for them)
    assert EvidenceStatus.UNAVAILABLE in all_statuses  # On LDPC candidates or missing metrics

    # Test FAIL state specifically by simulating CRC fail
    g1_decoder_data["status"] = "failed"
    g1_decoder_data["crc_status"] = "fail"
    g1_decoder_data["failure_reason"] = "CRC checksum failure"
    decoder_fail = validate_decoder_output_dict(g1_decoder_data)

    ranked_fail = engine.run(analysis, classifier_out, decoder_fail)
    fail_statuses = {ev.status for c in ranked_fail for ev in c.evidence}
    assert EvidenceStatus.FAIL in fail_statuses


# -----------------------------------------------------------------------------
# 5. Deterministic Ranking Given Identical Input
# -----------------------------------------------------------------------------
def test_deterministic_ranking_identical_input(g1_analysis_data, g1_classifier_data, g1_decoder_data):
    analysis = validate_analysis_dict(g1_analysis_data)
    classifier_out = validate_classifier_output_dict(g1_classifier_data)
    decoder_out = validate_decoder_output_dict(g1_decoder_data)

    engine = HypothesisEngineV1()

    run1 = engine.run(analysis, classifier_out, decoder_out)
    run2 = engine.run(analysis, classifier_out, decoder_out)

    assert len(run1) == len(run2) == 175
    for c1, c2 in zip(run1, run2):
        assert c1.modulation == c2.modulation
        assert c1.interleaver == c2.interleaver
        assert c1.fec == c2.fec
        assert c1.status == c2.status
        assert c1.final_rank_score == c2.final_rank_score


# -----------------------------------------------------------------------------
# 6. Full G1-Style Pass End-to-End
# -----------------------------------------------------------------------------
def test_full_g1_style_pass(g1_analysis_data, g1_classifier_data, g1_decoder_data):
    analysis = validate_analysis_dict(g1_analysis_data)
    classifier_out = validate_classifier_output_dict(g1_classifier_data)
    decoder_out = validate_decoder_output_dict(g1_decoder_data)

    engine = HypothesisEngineV1()
    ranked = engine.run(analysis, classifier_out, decoder_out)

    top = ranked[0]
    # G1 winning hypothesis must be QPSK x block x conv_viterbi_k7
    assert top.modulation == "QPSK"
    assert top.interleaver == "block"
    assert top.fec == "conv_viterbi_k7"
    assert top.status == "EVALUATED"
    assert top.final_rank_score > 0.85
    assert len(top.failed_checks) == 0

    # Ensure debug dump formats without error
    dump = format_hypothesis_dump(ranked, top_n=5, title="G1 Test Run Dump")
    assert "G1 TEST RUN DUMP" in dump
    assert "QPSK x block x conv_viterbi_k7" in dump


# -----------------------------------------------------------------------------
# 7. Full G2-Style Pass End-to-End
# -----------------------------------------------------------------------------
def test_full_g2_style_pass(g2_analysis_data, g2_classifier_data, g2_decoder_data):
    analysis = validate_analysis_dict(g2_analysis_data)
    classifier_out = validate_classifier_output_dict(g2_classifier_data)
    decoder_out = validate_decoder_output_dict(g2_decoder_data)

    engine = HypothesisEngineV1()
    ranked = engine.run(analysis, classifier_out, decoder_out)

    top = ranked[0]
    # G2 winning hypothesis must be 2-FSK x none x none
    assert top.modulation == "2-FSK"
    assert top.interleaver == "none"
    assert top.fec == "none"
    assert top.status == "EVALUATED"
    assert top.final_rank_score > 0.80
    assert len(top.failed_checks) == 0

    dump = format_hypothesis_dump(ranked, top_n=5, title="G2 Test Run Dump")
    assert "G2 TEST RUN DUMP" in dump
    assert "2-FSK x none x none" in dump
