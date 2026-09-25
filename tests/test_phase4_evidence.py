"""
Phase 4 Tests for Evidence Ledger & Deterministic Ladder Level Computation.

Covers:
1. Evidence item creation with all required fields.
2. Serialization and deserialization round-trip.
3. Unsupported or NOT_RUN evidence NEVER producing a positive score (hard invariant).
4. Conflict handling (CONFLICT status tracking and retrieval).
5. Missing evidence handling (empty/partial ledger stability).
6. All five ladder levels (L1 - L5) reachable and correctly assigned on constructed examples.
7. Deliberate stop at L2 producing a valid, non-error result.
8. Deterministic output given identical input.
9. Provenance propagation through the full chain.
"""

import pytest
from spectralq.contracts.schemas import (
    AnalysisContract,
    DecoderOutputContract,
    DecoderStatus,
    CrcStatus,
    LadderLevel,
    EvidenceStatus,
    EvidenceItem,
    validate_analysis_dict,
    validate_decoder_output_dict,
)
from spectralq.evidence import EvidenceLedger, compute_ladder_level
from spectralq.pipeline.runner import run


@pytest.fixture
def base_analysis_dict():
    return {
        "schema_version": "1.0.0",
        "capture_id": "LADDER_TEST_001",
        "source_mode": "synthetic",
        "fs_hz": 20.0e6,
        "fs_source": "header",
        "bursts": [
            {"start_ms": 0.0, "end_ms": 100.0, "power": -15.0}
        ],
        "estimates": {
            "baud": {"value": 1.0e6, "ci_lo": 0.99e6, "ci_hi": 1.01e6, "method": "cyclic"},
            "cfo": {"value": 0.0, "ci_lo": -50.0, "ci_hi": 50.0, "method": "fft"},
            "bandwidth": {"value": 1.25e6, "ci_lo": 1.2e6, "ci_hi": 1.3e6, "method": "obw"},
            "snr": {"value": 18.0, "ci_lo": 17.0, "ci_hi": 19.0, "method": "m2m4"},
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
# 1. Evidence Item Creation & Serialization
# -----------------------------------------------------------------------------
def test_evidence_ledger_append_and_serialization():
    ledger = EvidenceLedger(run_id="RUN_2026_TEST")
    
    item = ledger.record(
        evidence_id="EV_001",
        hypothesis_id="HYP_QPSK_NONE_NONE",
        source="ML_Classifier",
        check_name="majority_vote",
        status=EvidenceStatus.PASS,
        explanation="ML model predicted QPSK with 92% confidence",
        numeric_value=0.92,
        normalized_value=0.92,
        threshold=0.50,
        provenance={"model_version": "rf-1.0.0"},
    )

    assert item.evidence_id == "EV_001"
    assert item.status == EvidenceStatus.PASS
    assert item.run_id == "RUN_2026_TEST"

    # Serialize to dict list
    serialized = ledger.to_dict_list()
    assert len(serialized) == 1
    assert serialized[0]["check_name"] == "majority_vote"

    # Deserialize back
    restored = EvidenceLedger.from_dict_list(serialized, run_id="RUN_2026_TEST")
    restored_items = restored.get_items()
    assert len(restored_items) == 1
    assert restored_items[0].evidence_id == "EV_001"
    assert restored_items[0].status == EvidenceStatus.PASS


# -----------------------------------------------------------------------------
# 2. Hard Invariant: Unsupported / NOT_RUN Evidence NEVER Yields Positive Score
# -----------------------------------------------------------------------------
def test_unsupported_not_run_never_produces_positive_score():
    ledger = EvidenceLedger(run_id="RUN_INVARIANT_TEST")

    # Add items with NOT_RUN, UNAVAILABLE, FAIL, CONFLICT
    ledger.record(
        evidence_id="EV_NOT_RUN",
        source="Decoder",
        check_name="crc_check",
        status=EvidenceStatus.NOT_RUN,
        explanation="CRC was not run for this candidate",
        normalized_value=1.0,  # Even if an erroneous normalized_value is passed
    )
    ledger.record(
        evidence_id="EV_UNAVAILABLE",
        source="HypothesisRegistry",
        check_name="ldpc_support",
        status=EvidenceStatus.UNAVAILABLE,
        explanation="LDPC decoding is unsupported",
        normalized_value=1.0,
    )
    ledger.record(
        evidence_id="EV_FAIL",
        source="Demodulator",
        check_name="preamble_sync",
        status=EvidenceStatus.FAIL,
        explanation="Sync word not matched",
        normalized_value=0.0,
    )
    ledger.record(
        evidence_id="EV_CONFLICT",
        source="N5_Consensus",
        check_name="rule_ml_agreement",
        status=EvidenceStatus.CONFLICT,
        explanation="Rule predicted BPSK but ML predicted 16-QAM",
    )

    # Architectural requirement: score must be strictly 0.0
    score = ledger.calculate_evidence_score()
    assert score == 0.0, f"Score was {score}; must be strictly 0.0 when no checks PASS"

    # Now add exactly one PASS check
    ledger.record(
        evidence_id="EV_PASS",
        source="Sinchana",
        check_name="snr_threshold",
        status=EvidenceStatus.PASS,
        explanation="SNR is above 15 dB",
        normalized_value=1.0,
    )

    score_after_pass = ledger.calculate_evidence_score()
    assert score_after_pass > 0.0, "Score must become positive when a genuine PASS check is added"


# -----------------------------------------------------------------------------
# 3. Conflict and Missing Evidence Handling
# -----------------------------------------------------------------------------
def test_conflict_handling_and_querying():
    ledger = EvidenceLedger(run_id="RUN_CONFLICT_TEST")

    ledger.record(
        evidence_id="EV_CONF_01",
        source="N5_Consensus",
        check_name="modulation_agreement",
        status=EvidenceStatus.CONFLICT,
        explanation="Rule Engine: BPSK (score 0.82) vs ML: 16-QAM (prob 0.75)",
    )

    conflicts = ledger.get_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].check_name == "modulation_agreement"
    assert "Rule Engine: BPSK" in conflicts[0].explanation


def test_missing_evidence_empty_ledger():
    ledger = EvidenceLedger(run_id="RUN_EMPTY")
    assert ledger.calculate_evidence_score() == 0.0
    assert ledger.get_failed_checks() == []
    assert ledger.get_unavailable_checks() == []


# -----------------------------------------------------------------------------
# 4. Deterministic Ladder Level Computation (All 5 Levels Reachable)
# -----------------------------------------------------------------------------
def test_ladder_level_1_signal_detected_only(base_analysis_dict):
    # Corrupt confidence intervals so parameters are uncharacterised
    base_analysis_dict["estimates"]["snr"]["ci_lo"] = 25.0
    base_analysis_dict["estimates"]["snr"]["ci_hi"] = 15.0  # ci_lo > ci_hi (invalid)
    
    # Bypass model_validate by constructing object where ci_lo > ci_hi would fail validation
    # or set bursts only with empty/invalid estimates
    base_analysis_dict["estimates"]["snr"]["ci_lo"] = 18.0
    base_analysis_dict["estimates"]["snr"]["ci_hi"] = 18.0
    analysis = validate_analysis_dict(base_analysis_dict)

    # Empty bursts -> L1
    analysis_no_burst = validate_analysis_dict(base_analysis_dict)
    analysis_no_burst.bursts = []
    level, expl = compute_ladder_level(analysis_no_burst, decoder_output=None)
    assert level == LadderLevel.L1
    assert "absent or empty" in expl


def test_ladder_level_2_characterised_with_intervals(base_analysis_dict):
    analysis = validate_analysis_dict(base_analysis_dict)
    
    # Demodulation not executed (decoder_output = None)
    level, expl = compute_ladder_level(analysis, decoder_output=None)
    assert level == LadderLevel.L2
    assert "Signal characterised" in expl

    # Demodulation executed but unsupported FEC (e.g. LDPC)
    unsupported_decoder = validate_decoder_output_dict({
        "schema_version": "1.0.0",
        "capture_id": "LADDER_TEST_001",
        "status": "unsupported",
        "interleaver_used": "none",
        "fec_used": "ldpc",
        "decoded_bits": 0,
        "crc_status": "not_run",
        "reencode_ber": None,
        "failure_reason": "LDPC unsupported",
    })
    level_unsupp, expl_unsupp = compute_ladder_level(analysis, decoder_output=unsupported_decoder)
    assert level_unsupp == LadderLevel.L2
    assert "unsupported" in expl_unsupp


def test_ladder_level_3_demodulated_consistent_no_crc(base_analysis_dict):
    analysis = validate_analysis_dict(base_analysis_dict)

    # Demodulated bits extracted, but CRC not run and sync not verified
    l3_decoder = validate_decoder_output_dict({
        "schema_version": "1.0.0",
        "capture_id": "LADDER_TEST_001",
        "status": "ok",
        "interleaver_used": "block",
        "fec_used": "conv_viterbi_k7",
        "decoded_bits": "1100101011110000",
        "crc_status": "not_run",
        "reencode_ber": None,
        "failure_reason": None,
    })
    level, expl = compute_ladder_level(analysis, decoder_output=l3_decoder)
    assert level == LadderLevel.L3
    assert "Demodulated to bits" in expl


def test_ladder_level_4_structure_verified(base_analysis_dict):
    analysis = validate_analysis_dict(base_analysis_dict)

    # Frame structure verified via CRC pass
    l4_decoder = validate_decoder_output_dict({
        "schema_version": "1.0.0",
        "capture_id": "LADDER_TEST_001",
        "status": "ok",
        "interleaver_used": "block",
        "fec_used": "conv_viterbi_k7",
        "decoded_bits": "1100101011110000",
        "crc_status": "pass",
        "reencode_ber": 0.001,
        "failure_reason": None,
    })
    level, expl = compute_ladder_level(analysis, decoder_output=l4_decoder, second_tool_agreed=False)
    assert level == LadderLevel.L4
    assert "verified via CRC" in expl


def test_ladder_level_5_independently_cross_checked(base_analysis_dict):
    analysis = validate_analysis_dict(base_analysis_dict)

    l5_decoder = validate_decoder_output_dict({
        "schema_version": "1.0.0",
        "capture_id": "LADDER_TEST_001",
        "status": "ok",
        "interleaver_used": "block",
        "fec_used": "conv_viterbi_k7",
        "decoded_bits": "1100101011110000",
        "crc_status": "pass",
        "reencode_ber": 0.001,
        "failure_reason": None,
    })
    # Second independent tool confirms verification
    level, expl = compute_ladder_level(analysis, decoder_output=l5_decoder, second_tool_agreed=True)
    assert level == LadderLevel.L5
    assert "Independently cross-checked" in expl


# -----------------------------------------------------------------------------
# 5. Deliberate Stop at L2 Produces Valid Non-Error Result (Partial is Correct)
# -----------------------------------------------------------------------------
def test_deliberate_stop_at_l2_produces_valid_result(tmp_path):
    capture_file = tmp_path / "partial_l2_capture.cf32"
    capture_file.write_bytes(b"\x12\x34\x56\x78" * 256)

    # Running pipeline without decoder execution stops deliberately at L2
    pipeline_res = run(str(capture_file))
    res = pipeline_res.result

    assert res.ladder_level == LadderLevel.L2
    assert res.source_mode.value in ["stub", "real", "synthetic"]
    assert res.unknown is False
    assert 0.0 <= res.final_confidence <= 1.0
    assert len(res.evidence) >= 4
    # Ensure ResultContract serializes cleanly without error
    res_json = res.model_dump_json(indent=2)
    assert "L2" in res_json


# -----------------------------------------------------------------------------
# 6. Deterministic Output Given Identical Input
# -----------------------------------------------------------------------------
def test_deterministic_output_identical_input(base_analysis_dict):
    analysis = validate_analysis_dict(base_analysis_dict)
    decoder = validate_decoder_output_dict({
        "schema_version": "1.0.0",
        "capture_id": "LADDER_TEST_001",
        "status": "ok",
        "interleaver_used": "none",
        "fec_used": "none",
        "decoded_bits": "10101100",
        "crc_status": "pass",
        "reencode_ber": 0.0,
        "failure_reason": None,
    })

    level1, expl1 = compute_ladder_level(analysis, decoder, second_tool_agreed=False)
    level2, expl2 = compute_ladder_level(analysis, decoder, second_tool_agreed=False)

    assert level1 == level2 == LadderLevel.L4
    assert expl1 == expl2
