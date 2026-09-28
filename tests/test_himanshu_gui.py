"""
Unit and Contract Tests for Himanshu's Streamlit GUI Layer (Stage 10).

Covers all 13 required verification items:
1. result JSON loads cleanly.
2. missing schema fields handled with explicit errors.
3. UNKNOWN state preserved without guessing.
4. UNSUPPORTED capability preserved and displayed explicitly.
5. SUCCESS state rendered faithfully.
6. BER displayed honestly (never fabricates 0 when null).
7. Confidence display preserved strictly from backend.
8. Decoder evidence items extracted cleanly.
9. Replay mode discovers cases and loads without live execution.
10. Invalid JSON handled gracefully.
11. Missing artifacts handled gracefully.
12. Export bundle generates valid SigMF metadata.
13. ZERO backend signal processing / calculations occur in GUI modules.
"""

import json
from pathlib import Path
import pytest

from ui.adapters.result_adapter import (
    adapt_result,
    ContractValidationError,
    NormalizedResult,
)
from ui.adapters.analysis_adapter import (
    adapt_analysis,
    AnalysisValidationError,
    NormalizedAnalysis,
)
from ui.adapters.decoder_adapter import (
    adapt_decoder,
    DecoderValidationError,
    NormalizedDecoder,
)
from ui.adapters.evidence_adapter import summarize_evidence
from ui.loaders.case_discovery import discover_available_cases
from ui.loaders.artifact_loader import (
    load_json_file,
    load_case_artifacts,
    ArtifactLoadError,
)
from ui.components.bundle_exporter import generate_sigmf_metadata


REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_METEOR_DIR = REPO_ROOT / "data" / "real" / "meteor_m2_lrpt"
GOLDEN_DIR = REPO_ROOT / "data" / "golden"


# 1. Result JSON loads
def test_result_json_loads_valid():
    res_path = REAL_METEOR_DIR / "result.json"
    assert res_path.exists()
    with open(res_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    norm = adapt_result(data)
    assert norm.capture_id == "REAL_METEOR_M2_LRPT_72K"
    assert norm.ladder_level == "L4"
    assert norm.top_hypothesis.modulation == "QPSK"
    assert norm.final_confidence == pytest.approx(0.921, abs=0.001)
    assert norm.is_unknown is False


# 2. Missing fields handled
def test_missing_fields_handled():
    incomplete_data = {
        "schema_version": "1.0.0",
        "capture_id": "TEST_FAIL",
        # Missing source_mode, top_hypothesis, final_confidence, etc.
    }
    with pytest.raises(ContractValidationError):
        adapt_result(incomplete_data)


# 3. UNKNOWN state rendered
def test_unknown_state_rendered():
    unknown_data = {
        "schema_version": "1.0.0",
        "capture_id": "CAP_UNKNOWN",
        "source_mode": "synthetic",
        "ladder_level": "L1",
        "top_hypothesis": {"modulation": "QPSK", "interleaver": "none", "fec": "none"},
        "alternate_hypotheses": [],
        "ml_prediction": "QPSK",
        "ml_probability": 0.45,
        "calibrated_ml_probability": 0.42,
        "rule_prediction": "2-FSK",
        "rule_ml_agreement": False,
        "rule_ml_penalty": 0.25,
        "cross_window_agreement": 0.50,
        "evidence": [
            {
                "evidence_id": "EV_001",
                "source": "Sinchana",
                "check_name": "snr_floor_check",
                "status": "FAIL",
                "explanation": "SNR below operating floor",
            }
        ],
        "failed_checks": ["snr_floor_check"],
        "unavailable_checks": [],
        "final_confidence": 0.35,
        "confidence_version": "n2-logistic-1.0.0",
        "unknown": True,
        "unknown_reason": "Low SNR (2.0 dB) below physical demodulation floor",
        "provenance": {
            "input_hash": "a1b2c3d4",
            "seed": 42,
            "software_version": "1.0.0",
            "generated_at": "2026-09-25T12:00:00Z",
        },
        "capability_available": True,
    }
    norm = adapt_result(unknown_data)
    assert norm.is_unknown is True
    assert norm.confidence_label == "UNKNOWN"
    assert norm.unknown_reason == "Low SNR (2.0 dB) below physical demodulation floor"
    assert norm.final_confidence == 0.35  # Preserved honest float, never overwritten to 0


# 4. UNSUPPORTED rendered
def test_unsupported_state_rendered():
    unsupported_decoder = {
        "schema_version": "1.0.0",
        "capture_id": "CAP_LDPC",
        "status": "unsupported",
        "interleaver_used": "pseudo_random",
        "fec_used": "ldpc",
        "decoded_bits": 0,
        "crc_status": "not_run",
        "reencode_ber": None,
        "failure_reason": "LDPC FEC scheme is unsupported in current release (never fabricated)",
    }
    norm_dec = adapt_decoder(unsupported_decoder)
    assert norm_dec.status == "UNSUPPORTED"
    assert norm_dec.fec_used == "ldpc"
    assert norm_dec.reencode_ber is None
    assert norm_dec.ber_display == "N/A (Not Available)"
    assert "unsupported" in norm_dec.failure_reason.lower()


# 5. SUCCESS rendered
def test_success_state_rendered():
    success_decoder = {
        "schema_version": "1.0.0",
        "capture_id": "CAP_SUCCESS",
        "status": "ok",
        "interleaver_used": "block",
        "fec_used": "conv_viterbi_k7",
        "decoded_bits": 8192,
        "crc_status": "pass",
        "reencode_ber": 0.0,
        "failure_reason": None,
    }
    norm_dec = adapt_decoder(success_decoder)
    assert norm_dec.status == "OK"
    assert norm_dec.crc_status == "PASS"
    assert norm_dec.ber_display == "0.000000 (0 errors)"
    assert norm_dec.source_exact_match is True


# 6. BER displayed correctly
def test_ber_displayed_correctly():
    # Test case 1: None -> N/A
    d1 = NormalizedDecoder(
        schema_version="1.0.0",
        capture_id="C1",
        status="UNSUPPORTED",
        interleaver_used="none",
        fec_used="none",
        decoded_bits_count=0,
        decoded_bits_preview=None,
        crc_status="NOT_RUN",
        reencode_ber=None,
        failure_reason="Unsupported",
    )
    assert d1.ber_display == "N/A (Not Available)"

    # Test case 2: 0.0 -> exact 0
    d2 = NormalizedDecoder(
        schema_version="1.0.0",
        capture_id="C2",
        status="OK",
        interleaver_used="none",
        fec_used="none",
        decoded_bits_count=100,
        decoded_bits_preview="1010",
        crc_status="PASS",
        reencode_ber=0.0,
        failure_reason=None,
    )
    assert d2.ber_display == "0.000000 (0 errors)"

    # Test case 3: non-zero
    d3 = NormalizedDecoder(
        schema_version="1.0.0",
        capture_id="C3",
        status="OK",
        interleaver_used="none",
        fec_used="none",
        decoded_bits_count=100,
        decoded_bits_preview="1010",
        crc_status="PASS",
        reencode_ber=0.00125,
        failure_reason=None,
    )
    assert d3.ber_display == "0.001250"


# 7. Confidence displayed correctly
def test_confidence_displayed_correctly():
    res_path = GOLDEN_DIR / "result.json"
    norm = adapt_result(load_json_file(res_path))
    assert norm.final_confidence == 0.975
    assert norm.confidence_label == "CONFIRMED"


# 8. Decoder evidence displayed
def test_decoder_evidence_displayed():
    dec_path = REAL_METEOR_DIR / "decoder_output.json"
    norm = adapt_decoder(load_json_file(dec_path))
    assert norm.status == "OK"
    assert norm.fec_used == "conv_viterbi_k7"
    assert norm.interleaver_used == "block"
    assert norm.crc_status == "PASS"
    assert norm.reencode_ber == 0.0008
    assert norm.decoded_bits_count == 8192


# 9. Replay mode works
def test_replay_mode_discovery_and_loading():
    cases = discover_available_cases(REPO_ROOT)
    assert len(cases) >= 5
    case_ids = [c.case_id for c in cases]
    assert "METEOR_M2_LRPT" in case_ids or any("METEOR" in cid for cid in case_ids)

    # Load Meteor-M2 case
    meteor_case = [c for c in cases if "METEOR" in c.case_id][0]
    res, ana, dec, prov = load_case_artifacts(meteor_case)
    assert res is not None
    assert ana is not None
    assert dec is not None
    assert prov["name"] == meteor_case.name


# 10. Invalid JSON handled
def test_invalid_json_handled(tmp_path):
    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("{ this is not valid json }", encoding="utf-8")
    with pytest.raises(ArtifactLoadError):
        load_json_file(bad_file)


# 11. Missing artifact handled
def test_missing_artifact_handled(tmp_path):
    missing_file = tmp_path / "non_existent.json"
    with pytest.raises(ArtifactLoadError):
        load_json_file(missing_file)


# 12. Export button behavior & SigMF generation
def test_export_bundle_generation():
    res_path = REAL_METEOR_DIR / "result.json"
    ana_path = REAL_METEOR_DIR / "analysis.json"
    norm_res = adapt_result(load_json_file(res_path))
    norm_ana = adapt_analysis(load_json_file(ana_path))

    sigmf = generate_sigmf_metadata(norm_res, norm_ana)
    assert "global" in sigmf
    assert sigmf["global"]["core:datatype"] == "cf32_le"
    assert sigmf["global"]["spectralq:ladder_level"] == "L4"
    assert sigmf["global"]["spectralq:modulation"] == "QPSK"
    assert sigmf["global"]["spectralq:sha256"] == norm_res.input_hash


# 13. Zero backend calculation occurs in GUI
def test_no_backend_calculation_occurs_in_gui():
    ui_dir = REPO_ROOT / "ui"
    forbidden_terms = [
        "octave_cli",
        "Viterbi",
        "Demodulator",
        "fit(",
        "CalibratedClassifierCV",
        "LogisticRegression",
        "train_baseline",
    ]
    for p in ui_dir.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        for term in forbidden_terms:
            assert term not in text, f"Violation in {p}: found forbidden scientific computation term '{term}'"


# 14. G1-G7 Rendering Validation
def test_g1_to_g7_rendering():
    cases_dict = {c.case_id: c for c in discover_available_cases(REPO_ROOT)}
    for g_id in ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]:
        assert g_id in cases_dict, f"Case {g_id} must be discovered dynamically"
        case = cases_dict[g_id]
        res, ana, dec, prov = load_case_artifacts(case)
        assert res is not None, f"Result must be loaded for {g_id}"
        assert res.top_hypothesis.modulation != ""
        if g_id == "G7":
            assert res.is_unknown is True, "G7 must be UNKNOWN"
        else:
            assert res.is_unknown is False, f"{g_id} must not be UNKNOWN"


# 15. Streamlit App Full Execution via AppTest
def test_streamlit_app_executes_cleanly():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(REPO_ROOT / "app.py"))
    at.run(timeout=20)
    assert not at.exception, f"AppTest raised an unhandled exception: {at.exception}"
    assert len(at.markdown) > 0
    assert len(at.button) > 0



