"""
Phase 11 Tests: Real Team Integration & Schema Freeze Verification.

Covers:
1. Sinchana Integration:
   - Schema and provenance validation.
   - Parameter uncertainty intervals validation.
   - Feature availability: legitimately absent features handled strictly as UNAVAILABLE, not zero.
2. Arpit Integration:
   - Consumption of real decoder output (demodulated bits, status, CRC, BER).
   - No duplication of decoder logic.
3. Harsh Integration:
   - Feature compatibility guard: exact match on 15 canonical features and ordering.
   - Loud failure with FeatureCompatibilityError on missing, extra, or out-of-order features.
4. End-to-End Real Data Execution:
   - NOAA-19 APT (reaches L3).
   - Meteor-M2 LRPT (reaches L4).
   - Unverified ISM 2400 (reaches L2; strictly avoids "Zigbee" label).
5. Schema Freeze Verification:
   - result.json conforms strictly to frozen v1.0.0 schema specification.
"""

import json
from pathlib import Path
import pytest

from spectralq.contracts.schemas import (
    AnalysisContract,
    DecoderOutputContract,
    ClassifierOutputContract,
    ResultContract,
    LadderLevel,
    SourceMode,
    EvidenceStatus,
    DecoderStatus,
    CrcStatus,
    validate_result_dict,
)
from spectralq.integration.team_adapters import (
    consume_sinchana_analysis,
    consume_arpit_decoder_output,
    consume_harsh_classifier_output,
    validate_harsh_feature_compatibility,
    run_real_team_pipeline,
    FeatureCompatibilityError,
    SinchanaContractError,
)
from spectralq.integration.classifier_adapter import CANONICAL_FEATURE_NAMES


REAL_DATA_DIR = Path(__file__).parent.parent / "data" / "real"


# -----------------------------------------------------------------------------
# 1. Sinchana Integration Tests
# -----------------------------------------------------------------------------
def test_sinchana_consumption_and_uncertainty_validation():
    analysis_file = REAL_DATA_DIR / "noaa19_apt" / "analysis.json"
    analysis = consume_sinchana_analysis(analysis_file)

    assert analysis.schema_version == "1.0.0"
    assert analysis.source_mode == SourceMode.REAL
    assert analysis.capture_id == "REAL_NOAA19_APT_137M1"
    assert analysis.estimates.snr.ci_lo <= analysis.estimates.snr.ci_hi
    assert analysis.estimates.baud.ci_lo <= analysis.estimates.baud.ci_hi


def test_sinchana_absent_feature_handled_as_unavailable():
    """
    Features like phase_ambiguity_quality or cyclic may legitimately be absent.
    Must be handled as UNAVAILABLE in evidence ledger, NEVER silently as 0.0 or pass.
    """
    analysis_file = REAL_DATA_DIR / "noaa19_apt" / "analysis.json"
    dec_file = REAL_DATA_DIR / "noaa19_apt" / "decoder_output.json"
    clf_file = REAL_DATA_DIR / "noaa19_apt" / "classifier_output.json"

    result, stage_status = run_real_team_pipeline(
        analysis_input=analysis_file,
        decoder_input=dec_file,
        classifier_input=clf_file,
    )

    # Check evidence ledger for UNAVAILABLE items
    ev_dict = {ev.check_name: ev for ev in result.evidence}

    assert "phase_ambiguity_quality_check" in ev_dict
    assert ev_dict["phase_ambiguity_quality_check"].status == EvidenceStatus.UNAVAILABLE
    assert "marked UNAVAILABLE per contract" in ev_dict["phase_ambiguity_quality_check"].explanation

    assert "cyclic_prefix_check" in ev_dict
    assert ev_dict["cyclic_prefix_check"].status == EvidenceStatus.UNAVAILABLE


# -----------------------------------------------------------------------------
# 2. Arpit Integration Tests
# -----------------------------------------------------------------------------
def test_arpit_consumption_preserves_decoder_outputs():
    dec_file = REAL_DATA_DIR / "meteor_m2_lrpt" / "decoder_output.json"
    decoder_out = consume_arpit_decoder_output(dec_file)

    assert decoder_out.schema_version == "1.0.0"
    assert decoder_out.status == DecoderStatus.OK
    assert decoder_out.fec_used == "conv_viterbi_k7"
    assert decoder_out.interleaver_used == "block"
    assert decoder_out.crc_status == CrcStatus.PASS
    assert decoder_out.reencode_ber == 0.0008
    assert decoder_out.decoded_bits == 8192


# -----------------------------------------------------------------------------
# 3. Harsh Integration & Feature Compatibility Guard Tests
# -----------------------------------------------------------------------------
def test_harsh_feature_compatibility_exact_match():
    clf_file = REAL_DATA_DIR / "meteor_m2_lrpt" / "classifier_output.json"
    contract = consume_harsh_classifier_output(clf_file)

    assert contract.schema_version == "1.0.0"
    assert contract.ml_prediction == "QPSK"
    assert list(contract.feature_vector_used.keys()) == CANONICAL_FEATURE_NAMES


def test_harsh_feature_compatibility_fails_loudly_on_missing_feature():
    """
    If Harsh's feature vector is missing a required feature, fails loudly
    with FeatureCompatibilityError and specific diagnostic report.
    """
    valid_features = {f: 1.0 for f in CANONICAL_FEATURE_NAMES}
    del valid_features["C40"]  # Missing feature

    with pytest.raises(FeatureCompatibilityError) as exc_info:
        validate_harsh_feature_compatibility(valid_features)

    err = exc_info.value
    assert "C40" in err.report["missing_features"]
    assert err.report["error_type"] == "FeatureCompatibilityMismatch"


def test_harsh_feature_compatibility_fails_loudly_on_out_of_order_features():
    """
    If Harsh's feature vector has all 15 features but in wrong order,
    fails loudly with FeatureCompatibilityError (never silently reorders and hopes).
    """
    swapped_features = list(CANONICAL_FEATURE_NAMES)
    swapped_features[0], swapped_features[1] = swapped_features[1], swapped_features[0]

    with pytest.raises(FeatureCompatibilityError) as exc_info:
        validate_harsh_feature_compatibility(swapped_features)

    err = exc_info.value
    assert len(err.report["ordering_mismatches"]) > 0
    assert err.report["ordering_mismatches"][0]["index"] == 0


# -----------------------------------------------------------------------------
# 4. End-to-End Real Data Execution & Ladder Level Verification
# -----------------------------------------------------------------------------
def test_real_capture_noaa19_reaches_l3():
    """NOAA-19 APT is demodulated to subcarrier audio/bits with internal consistency, reaching L3."""
    res, status = run_real_team_pipeline(
        analysis_input=REAL_DATA_DIR / "noaa19_apt" / "analysis.json",
        decoder_input=REAL_DATA_DIR / "noaa19_apt" / "decoder_output.json",
        classifier_input=REAL_DATA_DIR / "noaa19_apt" / "classifier_output.json",
    )

    assert res.source_mode == SourceMode.REAL
    assert res.ladder_level == LadderLevel.L3
    assert res.top_hypothesis.modulation == "2-FSK"
    assert res.unknown is False
    assert status["Ingest & Forensics"] == "REAL"
    assert status["Classifier"] == "REAL"


def test_real_capture_meteor_m2_reaches_l4():
    """Meteor-M2 LRPT has digital Viterbi decode and verified CRC-16, reaching L4."""
    res, status = run_real_team_pipeline(
        analysis_input=REAL_DATA_DIR / "meteor_m2_lrpt" / "analysis.json",
        decoder_input=REAL_DATA_DIR / "meteor_m2_lrpt" / "decoder_output.json",
        classifier_input=REAL_DATA_DIR / "meteor_m2_lrpt" / "classifier_output.json",
    )

    assert res.source_mode == SourceMode.REAL
    assert res.ladder_level == LadderLevel.L4
    assert res.top_hypothesis.modulation == "QPSK"
    assert res.top_hypothesis.fec == "conv_viterbi_k7"
    assert res.unknown is False


def test_real_capture_unverified_ism_reaches_l2_and_avoids_zigbee_label():
    """
    Unverified 2.4 GHz ISM burst:
    - Must NOT carry 'Zigbee' label (strictly 'real IQ capture, protocol not independently verified').
    - Reaches ladder level L2 honestly.
    """
    analysis_file = REAL_DATA_DIR / "unverified_ism_2400" / "analysis.json"
    analysis_raw = json.loads(analysis_file.read_text(encoding="utf-8"))

    # Enforce constraint: "Zigbee" label must NOT be carried into this system
    assert "zigbee" not in analysis_raw["notes"].lower(), "The 'Zigbee' label must NOT be carried into this system!"
    assert "protocol not independently verified" in analysis_raw["notes"]

    res, status = run_real_team_pipeline(
        analysis_input=analysis_file,
        decoder_input=REAL_DATA_DIR / "unverified_ism_2400" / "decoder_output.json",
        classifier_input=REAL_DATA_DIR / "unverified_ism_2400" / "classifier_output.json",
    )

    assert res.source_mode == SourceMode.REAL
    assert res.ladder_level == LadderLevel.L2, "Unverified protocol must honestly only reach L2 (Characterised)"
    assert res.unknown is False


# -----------------------------------------------------------------------------
# 5. Schema Freeze Verification
# -----------------------------------------------------------------------------
def test_schema_freeze_specification_compliance():
    """
    Verifies that real pipeline results conform strictly to frozen ResultContract
    and that docs/SCHEMA_FREEZE.md documents this release.
    """
    freeze_doc = Path(__file__).parent.parent / "docs" / "SCHEMA_FREEZE.md"
    assert freeze_doc.exists()
    content = freeze_doc.read_text(encoding="utf-8")
    assert "v1.0.0-FROZEN" in content
    assert "FIELD IMMUTABILITY POLICY" in content

    # Test that result produced by real pipeline validates against ResultContract
    res, _ = run_real_team_pipeline(
        analysis_input=REAL_DATA_DIR / "meteor_m2_lrpt" / "analysis.json",
        decoder_input=REAL_DATA_DIR / "meteor_m2_lrpt" / "decoder_output.json",
        classifier_input=REAL_DATA_DIR / "meteor_m2_lrpt" / "classifier_output.json",
    )

    result_dict = res.model_dump()
    validated = validate_result_dict(result_dict)
    assert validated.schema_version == "1.0.0"
    assert validated.ladder_level == LadderLevel.L4
