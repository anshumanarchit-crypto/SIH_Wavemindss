"""
Comprehensive Phase 1 Tests for SpectralQ Data Contracts & Schemas.

Validates:
1. Valid examples of all 5 contracts pass validation cleanly.
2. Deliberately malformed examples fail with specific, informative errors.
3. Schema version mismatches are caught across all contracts.
4. Provenance and epistemic state fields survive round-trip serialization.
5. Real / synthetic / replay states cannot be silently swapped or corrupted.
6. Extra fields are rejected (no silent coercion).
"""

import json
import pytest
from pydantic import ValidationError

from spectralq.contracts.schemas import (
    CURRENT_SCHEMA_VERSION,
    SourceMode,
    FsSource,
    DecoderStatus,
    CrcStatus,
    LadderLevel,
    EvidenceStatus,
    AnalysisContract,
    DecoderOutputContract,
    ClassifierOutputContract,
    TruthContract,
    ResultContract,
    validate_analysis_dict,
    validate_decoder_output_dict,
    validate_classifier_output_dict,
    validate_truth_dict,
    validate_result_dict,
)


# -----------------------------------------------------------------------------
# Fixtures: Valid Examples
# -----------------------------------------------------------------------------
@pytest.fixture
def valid_analysis_data():
    return {
        "schema_version": "1.0.0",
        "capture_id": "CAP_2026_001_REAL",
        "source_mode": "real",
        "fs_hz": 20.0e6,
        "fs_source": "header",
        "bursts": [
            {"start_ms": 10.5, "end_ms": 115.2, "power": -14.2}
        ],
        "estimates": {
            "baud": {"value": 1.0e6, "ci_lo": 0.99e6, "ci_hi": 1.01e6, "method": "cyclic_autocorr"},
            "cfo": {"value": 1250.0, "ci_lo": 1100.0, "ci_hi": 1400.0, "method": "fft_peak"},
            "bandwidth": {"value": 1.2e6, "ci_lo": 1.15e6, "ci_hi": 1.25e6, "method": "power_envelope_99"},
            "snr": {"value": 18.5, "ci_lo": 17.5, "ci_hi": 19.5, "method": "M2M4"},
        },
        "features": {
            "cumulants": {
                "C20": 0.02, "C21": 1.0, "C40": 0.98, "C42": -0.99,
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


@pytest.fixture
def valid_decoder_output_data():
    return {
        "schema_version": "1.0.0",
        "capture_id": "CAP_2026_001_REAL",
        "status": "ok",
        "interleaver_used": "block",
        "fec_used": "conv_viterbi_k7",
        "decoded_bits": "110010101111000010101100",
        "crc_status": "pass",
        "reencode_ber": 0.001,
        "failure_reason": None,
    }


@pytest.fixture
def valid_classifier_output_data():
    return {
        "schema_version": "1.0.0",
        "capture_id": "CAP_2026_001_REAL",
        "window_id": 0,
        "ml_prediction": "QPSK",
        "ml_probabilities": {
            "BPSK": 0.01,
            "QPSK": 0.94,
            "8-PSK": 0.03,
            "16-QAM": 0.01,
            "64-QAM": 0.005,
            "2-FSK": 0.002,
            "4-FSK": 0.003,
        },
        "calibrated_probability": 0.92,
        "model_version": "rf-baseline-1.0.0",
        "feature_vector_used": {
            "C20": 0.02, "C40": 0.98, "C42": -0.99, "snr": 18.5, "evm": 0.045
        },
    }


@pytest.fixture
def valid_truth_data():
    return {
        "schema_version": "1.0.0",
        "modulation": "QPSK",
        "sps": 4.0,
        "roll_off": 0.35,
        "snr_db": 18.0,
        "cfo_hz": 1250.0,
        "phase": 0.785,
        "interleaver": "block",
        "fec": "conv_viterbi_k7",
        "timing_bits": [1, 0, 1, 1, 0, 0, 1, 0],
        "source_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }


@pytest.fixture
def valid_result_data():
    return {
        "schema_version": "1.0.0",
        "capture_id": "CAP_2026_001_REAL",
        "source_mode": "real",
        "ladder_level": "L5",
        "top_hypothesis": {
            "modulation": "QPSK",
            "interleaver": "block",
            "fec": "conv_viterbi_k7",
        },
        "alternate_hypotheses": [
            {
                "modulation": "BPSK",
                "interleaver": "none",
                "fec": "none",
                "prior_score": 0.02,
                "verification_score": 0.0,
                "total_score": 0.01,
                "status": "PRUNED",
                "rejection_reason": "Cumulant C40 and cluster count incompatible",
            },
            {
                "modulation": "QPSK",
                "interleaver": "none",
                "fec": "ldpc",
                "prior_score": 0.85,
                "verification_score": 0.0,
                "total_score": 0.0,
                "status": "UNSUPPORTED",
                "rejection_reason": "FEC scheme 'LDPC' is unsupported in current release (never fabricated)",
            }
        ],
        "ml_prediction": "QPSK",
        "ml_probability": 0.94,
        "calibrated_ml_probability": 0.92,
        "rule_prediction": "QPSK",
        "rule_ml_agreement": True,
        "rule_ml_penalty": 0.0,
        "cross_window_agreement": 0.98,
        "evidence": [
            {
                "evidence_id": "EV_001",
                "source": "Sinchana",
                "check_name": "burst_power",
                "status": "PASS",
                "value": -14.2,
                "explanation": "Valid burst energy detected above background noise floor",
            },
            {
                "evidence_id": "EV_002",
                "source": "Arpit",
                "check_name": "crc_check",
                "status": "PASS",
                "value": True,
                "explanation": "Frame payload CRC verification passed",
            }
        ],
        "final_confidence": 0.965,
        "confidence_version": "n2-logistic-1.0.0",
        "unknown": False,
        "unknown_reason": None,
        "provenance": {
            "input_hash": "a1b2c3d4e5f67890",
            "seed": 42,
            "software_version": "1.0.0",
            "generated_at": "2026-09-25T11:23:45Z",
        },
    }


# -----------------------------------------------------------------------------
# Tests: 1. Valid Data Validates Cleanly
# -----------------------------------------------------------------------------
def test_valid_analysis_validates(valid_analysis_data):
    contract = validate_analysis_dict(valid_analysis_data)
    assert contract.schema_version == "1.0.0"
    assert contract.capture_id == "CAP_2026_001_REAL"
    assert contract.source_mode == SourceMode.REAL
    assert contract.fs_hz == 20.0e6
    assert len(contract.bursts) == 1
    assert contract.features.cumulants.C42 == -0.99


def test_valid_decoder_output_validates(valid_decoder_output_data):
    contract = validate_decoder_output_dict(valid_decoder_output_data)
    assert contract.status == DecoderStatus.OK
    assert contract.crc_status == CrcStatus.PASS
    assert contract.reencode_ber == 0.001


def test_valid_classifier_output_validates(valid_classifier_output_data):
    contract = validate_classifier_output_dict(valid_classifier_output_data)
    assert contract.ml_prediction == "QPSK"
    assert contract.ml_probabilities["QPSK"] == 0.94


def test_valid_truth_validates(valid_truth_data):
    contract = validate_truth_dict(valid_truth_data)
    assert contract.modulation == "QPSK"
    assert contract.sps == 4.0
    assert contract.roll_off == 0.35


def test_valid_result_validates(valid_result_data):
    contract = validate_result_dict(valid_result_data)
    assert contract.ladder_level == LadderLevel.L5
    assert contract.final_confidence == 0.965
    assert contract.unknown is False
    assert len(contract.evidence) == 2


# -----------------------------------------------------------------------------
# Tests: 2. Malformed Data Fails with Specific, Useful Errors
# -----------------------------------------------------------------------------
def test_malformed_analysis_negative_fs(valid_analysis_data):
    valid_analysis_data["fs_hz"] = -1000.0  # Invalid sampling rate <= 0
    with pytest.raises(ValidationError) as exc_info:
        validate_analysis_dict(valid_analysis_data)
    assert "greater than 0" in str(exc_info.value)


def test_malformed_analysis_burst_order(valid_analysis_data):
    valid_analysis_data["bursts"] = [{"start_ms": 100.0, "end_ms": 50.0, "power": -10.0}]  # end < start
    with pytest.raises(ValidationError) as exc_info:
        validate_analysis_dict(valid_analysis_data)
    assert "cannot be less than start_ms" in str(exc_info.value)


def test_malformed_analysis_ci_order(valid_analysis_data):
    valid_analysis_data["estimates"]["snr"]["ci_lo"] = 25.0
    valid_analysis_data["estimates"]["snr"]["ci_hi"] = 15.0  # ci_lo > ci_hi
    with pytest.raises(ValidationError) as exc_info:
        validate_analysis_dict(valid_analysis_data)
    assert "cannot exceed ci_hi" in str(exc_info.value)


def test_malformed_decoder_output_unsupported_without_reason(valid_decoder_output_data):
    valid_decoder_output_data["status"] = "unsupported"
    valid_decoder_output_data["failure_reason"] = None
    with pytest.raises(ValidationError) as exc_info:
        validate_decoder_output_dict(valid_decoder_output_data)
    assert "failure_reason must be provided when status is 'unsupported'" in str(exc_info.value)


def test_malformed_decoder_output_ok_with_crc_fail(valid_decoder_output_data):
    valid_decoder_output_data["status"] = "ok"
    valid_decoder_output_data["crc_status"] = "fail"
    with pytest.raises(ValidationError) as exc_info:
        validate_decoder_output_dict(valid_decoder_output_data)
    assert "cannot be 'ok' when crc_status is 'fail'" in str(exc_info.value)


def test_malformed_classifier_output_prediction_not_in_probs(valid_classifier_output_data):
    valid_classifier_output_data["ml_prediction"] = "UNKNOWN_MOD"
    with pytest.raises(ValidationError) as exc_info:
        validate_classifier_output_dict(valid_classifier_output_data)
    assert "must be present in ml_probabilities" in str(exc_info.value)


def test_malformed_truth_negative_sps(valid_truth_data):
    valid_truth_data["sps"] = -2.0
    with pytest.raises(ValidationError) as exc_info:
        validate_truth_dict(valid_truth_data)
    assert "greater than 0" in str(exc_info.value)


def test_malformed_result_unknown_without_reason(valid_result_data):
    valid_result_data["unknown"] = True
    valid_result_data["unknown_reason"] = None
    with pytest.raises(ValidationError) as exc_info:
        validate_result_dict(valid_result_data)
    assert "unknown_reason must be provided when unknown is True" in str(exc_info.value)


def test_malformed_result_confidence_out_of_bounds(valid_result_data):
    valid_result_data["final_confidence"] = 1.25  # Bounded [0.0, 1.0]
    with pytest.raises(ValidationError) as exc_info:
        validate_result_dict(valid_result_data)
    assert "less than or equal to 1" in str(exc_info.value)


def test_extra_fields_rejected_without_silent_coercion(valid_analysis_data):
    valid_analysis_data["unauthorized_injected_field"] = "malicious_payload"
    with pytest.raises(ValidationError) as exc_info:
        validate_analysis_dict(valid_analysis_data)
    assert "extra_forbidden" in str(exc_info.value) or "Extra inputs are not permitted" in str(exc_info.value)


# -----------------------------------------------------------------------------
# Tests: 3. Schema Version Mismatches Are Caught
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("bad_version", ["0.9.0", "2.0.0", "v1.0", "1.0.1"])
def test_schema_version_mismatch_analysis(valid_analysis_data, bad_version):
    valid_analysis_data["schema_version"] = bad_version
    with pytest.raises(ValidationError) as exc_info:
        validate_analysis_dict(valid_analysis_data)
    assert "Unsupported schema_version" in str(exc_info.value)


@pytest.mark.parametrize("bad_version", ["0.9.0", "2.0.0", "invalid"])
def test_schema_version_mismatch_result(valid_result_data, bad_version):
    valid_result_data["schema_version"] = bad_version
    with pytest.raises(ValidationError) as exc_info:
        validate_result_dict(valid_result_data)
    assert "Unsupported schema_version" in str(exc_info.value)


# -----------------------------------------------------------------------------
# Tests: 4. Provenance Fields Survive Round-Trip Serialization
# -----------------------------------------------------------------------------
def test_provenance_round_trip_serialization(valid_result_data):
    contract = validate_result_dict(valid_result_data)
    
    # Serialize to JSON string
    json_str = contract.model_dump_json(indent=2)
    parsed_back = json.loads(json_str)

    # Re-validate
    reloaded = validate_result_dict(parsed_back)
    assert reloaded.provenance.input_hash == contract.provenance.input_hash
    assert reloaded.provenance.seed == contract.provenance.seed
    assert reloaded.provenance.software_version == contract.provenance.software_version
    assert reloaded.provenance.generated_at == contract.provenance.generated_at
    assert reloaded.source_mode == SourceMode.REAL


# -----------------------------------------------------------------------------
# Tests: 5. State Immutability (Real / Synthetic / Replay Cannot Be Swapped Silently)
# -----------------------------------------------------------------------------
def test_source_mode_cannot_be_arbitrary_string(valid_analysis_data):
    valid_analysis_data["source_mode"] = "live_unverified"  # Invalid state
    with pytest.raises(ValidationError) as exc_info:
        validate_analysis_dict(valid_analysis_data)
    assert "Input should be 'real', 'synthetic' or 'replay'" in str(exc_info.value)


def test_epistemic_state_integrity():
    # Explicitly test that real, synthetic, and replay states are mutually exclusive
    assert SourceMode.REAL != SourceMode.SYNTHETIC
    assert SourceMode.REAL != SourceMode.REPLAY
    assert SourceMode.SYNTHETIC != SourceMode.REPLAY

    # Ensure states parse strictly
    assert SourceMode("real") == SourceMode.REAL
    assert SourceMode("synthetic") == SourceMode.SYNTHETIC
    assert SourceMode("replay") == SourceMode.REPLAY

    with pytest.raises(ValueError):
        SourceMode("fabricated")
