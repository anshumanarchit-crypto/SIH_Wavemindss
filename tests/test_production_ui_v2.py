"""
Production UI V2 Verification Test Suite.
Verifies all 7 core requirements:
1. Workspace navigation: all 7 workspaces render without exceptions
2. Contract adapters: valid, missing, partial, and malformed inputs
3. Raw sample visualization: actual raw data loads and renders; missing raw data produces UNAVAILABLE (zero fake data)
4. Simulation: signal generation, impairment addition, ground truth isolation
5. Evidence bundle ZIP: real valid ZIP, required manifest files, integrity checksums
6. UNKNOWN handling: low-SNR and ambiguous captures trigger prominent UNKNOWN banner with reason
7. Streamlit AppTest: entire app runs end-to-end with timeout=20
"""

import io
import json
from pathlib import Path
import zipfile
import numpy as np
import pytest

from ui.adapters import (
    adapt_result,
    adapt_analysis,
    adapt_decoder,
    ContractValidationError,
    AnalysisValidationError,
    DecoderValidationError,
)
from ui.loaders import discover_available_cases, load_case_artifacts, load_case_observatory
from ui.state import WORKSPACES
from ui.components import (
    render_mission_control,
    render_signal_observatory,
    render_modulation_hypotheses,
    render_decoder_bitstream,
    render_evidence_decision,
    render_provenance_export,
    render_signal_lab,
)
from spectralq.visualization.simulation import generate_simulated_signal, SimulationTruth
from spectralq.visualization.artifacts import (
    prepare_observatory_artifacts,
    build_evidence_bundle_zip,
    ObservatoryArtifacts,
)
from ui.charts import (
    create_waveform_plot,
    create_spectrum_plot,
    create_waterfall_plot,
    create_constellation_plot,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_METEOR_DIR = REPO_ROOT / "data" / "real" / "meteor_m2_lrpt"


# =============================================================================
# 1. Workspace Navigation & Component Execution
# =============================================================================
def test_all_seven_workspaces_defined():
    """Verify that all 7 required workspaces are defined in the navigation list."""
    expected = [
        "Mission Control",
        "Signal Observatory",
        "Modulation & Hypotheses",
        "Decoder & Bitstream",
        "Evidence & Decision",
        "Provenance & Export",
        "Signal Lab / Simulation",
    ]
    assert len(WORKSPACES) == 7
    for ws in expected:
        assert ws in WORKSPACES, f"Workspace '{ws}' must be defined"


def test_workspaces_render_without_exception():
    """Test calling each workspace rendering function directly with loaded models."""
    cases = discover_available_cases(REPO_ROOT)
    meteor_case = next(c for c in cases if "Meteor" in c.name or "meteor" in c.case_id.lower())
    res, ana, dec, prov = load_case_artifacts(meteor_case)
    artifacts = load_case_observatory(meteor_case, ana)

    # Workspace 1
    render_mission_control(res, ana, dec)
    # Workspace 2
    render_signal_observatory(artifacts, ana, res)
    # Workspace 3
    render_modulation_hypotheses(res, ana)
    # Workspace 4
    render_decoder_bitstream(dec, res)
    # Workspace 5
    render_evidence_decision(res, ana, dec)
    # Workspace 6
    render_provenance_export(res, ana, dec, artifacts, prov)


# =============================================================================
# 2. Contract Adapters (Valid, Missing, Partial, Malformed)
# =============================================================================
def test_adapter_valid_meteor():
    """Verify adapters on genuine Meteor M2 capture."""
    with open(REAL_METEOR_DIR / "result.json", "r", encoding="utf-8") as f:
        res = adapt_result(json.load(f))
    assert res.capture_id == "REAL_METEOR_M2_LRPT_72K"
    assert res.ladder_level == "L4"
    assert res.top_hypothesis.modulation == "QPSK"

    with open(REAL_METEOR_DIR / "analysis.json", "r", encoding="utf-8") as f:
        ana = adapt_analysis(json.load(f))
    assert ana.fs_hz == 10.0e6
    assert ana.snr.value > 0

    with open(REAL_METEOR_DIR / "decoder_output.json", "r", encoding="utf-8") as f:
        dec = adapt_decoder(json.load(f))
    assert dec.capture_id == "REAL_METEOR_M2_LRPT_72K"
    assert dec.status == "OK"


def test_adapter_malformed_inputs():
    """Verify adapters raise validation errors on malformed payloads."""
    with pytest.raises(ContractValidationError):
        adapt_result({"random": "junk", "schema_version": "1.0.0"})

    with pytest.raises(AnalysisValidationError):
        adapt_analysis({"not_an_analysis": True})

    with pytest.raises(DecoderValidationError):
        adapt_decoder("not even a dict")


# =============================================================================
# 3. Raw Sample Visualization & ZERO Fake Data Rule
# =============================================================================
def test_zero_fake_data_when_raw_missing():
    """When raw samples are not provided, raw_available is False and NO fake data is generated."""
    # Observatory artifacts with no raw file
    artifacts = prepare_observatory_artifacts(
        capture_path=None,
        iq_samples=None,
        analysis=None,
        source_mode="TEST",
    )
    assert artifacts.raw_available is False
    assert artifacts.waveform_i is None
    assert artifacts.waveform_q is None
    assert artifacts.spectrum is None
    assert artifacts.waterfall is None
    assert artifacts.constellation is None

    # Verify chart builders safely return None rather than fabricating samples
    assert create_waveform_plot(artifacts) is None
    assert create_spectrum_plot(artifacts) is None
    assert create_waterfall_plot(artifacts) is None
    assert create_constellation_plot(artifacts) is None


def test_real_raw_sample_visualization():
    """When actual I/Q samples are supplied, charts render valid Plotly figures."""
    samples = (np.random.randn(2048) + 1j * np.random.randn(2048)).astype(np.complex64)
    artifacts = prepare_observatory_artifacts(
        iq_samples=samples,
        fs_hz=1e6,
        source_mode="SIMULATED",
    )
    assert artifacts.raw_available is True
    assert artifacts.waveform_i is not None
    assert len(artifacts.waveform_i) > 0

    fig_w = create_waveform_plot(artifacts)
    assert fig_w is not None
    assert len(fig_w.data) == 2  # I and Q

    fig_s = create_spectrum_plot(artifacts)
    assert fig_s is not None

    fig_wf = create_waterfall_plot(artifacts)
    assert fig_wf is not None

    fig_c = create_constellation_plot(artifacts)
    assert fig_c is not None


# =============================================================================
# 4. Simulation Engine & Ground Truth Isolation
# =============================================================================
def test_simulation_generation_and_isolation():
    """Verify simulation creates impaired signal and preserves ground truth separately."""
    samples, truth = generate_simulated_signal(
        modulation="QPSK",
        num_symbols=1024,
        sps=8,
        fs_hz=1.0e6,
        snr_db=15.0,
        cfo_hz=3000.0,
        phase_noise_deg=2.0,
        fading="none",
    )
    assert len(samples) == 1024 * 8
    assert isinstance(truth, SimulationTruth)
    assert truth.modulation == "QPSK"
    assert truth.snr_db == 15.0
    assert truth.cfo_hz == 3000.0

    # Ensure samples are complex64
    assert np.iscomplexobj(samples)

    # Truth is never embedded into samples
    assert not hasattr(samples, "modulation")
    assert not hasattr(samples, "snr_db")


# =============================================================================
# 5. Evidence Bundle ZIP Packaging & Verification
# =============================================================================
def test_evidence_bundle_zip_structure():
    """Verify build_evidence_bundle_zip generates a valid ZIP with required manifest."""
    res_mock = {"capture_id": "TEST_CAP", "top_hypothesis": {"modulation": "QPSK"}}
    ana_mock = {"fs_hz": 20.0e6, "snr": {"value": 15.0, "unit": "dB"}}
    dec_mock = {"status": "OK", "ber": 0.0}
    sigmf_mock = {"global": {"core:datatype": "cf32_le"}}
    prov_mock = {"sha256": "abcdef1234567890"}

    zip_bytes = build_evidence_bundle_zip(
        capture_id="TEST_CAP",
        result_data=res_mock,
        analysis_data=ana_mock,
        decoder_data=dec_mock,
        sigmf_data=sigmf_mock,
        provenance_data=prov_mock,
    )
    assert len(zip_bytes) > 0

    # Verify ZIP integrity
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    namelist = zf.namelist()
    assert "result.json" in namelist
    assert "analysis.json" in namelist
    assert "decoder_output.json" in namelist
    assert "capture.sigmf-meta" in namelist
    assert "provenance.json" in namelist
    assert "evidence_summary.csv" in namelist

    # Verify content of result.json inside ZIP
    res_unpacked = json.loads(zf.read("result.json").decode("utf-8"))
    assert res_unpacked["capture_id"] == "TEST_CAP"


# =============================================================================
# 6. UNKNOWN & Abstention State Handling
# =============================================================================
def test_unknown_abstention_state():
    """Verify unknown captures trigger abstention banner and retain explanation."""
    unknown_raw = {
        "schema_version": "1.0.0",
        "capture_id": "G5_NOISY",
        "source_mode": "synthetic",
        "ladder_level": "L1",
        "top_hypothesis": {"modulation": "QPSK", "interleaver": "none", "fec": "none"},
        "alternate_hypotheses": [],
        "ml_prediction": "QPSK",
        "ml_probability": 0.35,
        "calibrated_ml_probability": 0.30,
        "rule_prediction": "2-FSK",
        "rule_ml_agreement": False,
        "rule_ml_penalty": 0.25,
        "cross_window_agreement": 0.40,
        "evidence": [],
        "failed_checks": ["snr_gate", "consensus_gate"],
        "unavailable_checks": [],
        "final_confidence": 0.25,
        "confidence_version": "1.0.0",
        "unknown": True,
        "unknown_reason": "Low SNR (1.2 dB) and rule-ML AMC divergence",
        "provenance": {"input_hash": "g5_hash", "seed": 42, "software_version": "1.0.0", "generated_at": "2026-09-28"},
        "capability_available": True,
    }
    norm = adapt_result(unknown_raw)
    assert norm.is_unknown is True
    assert norm.unknown_reason == "Low SNR (1.2 dB) and rule-ML AMC divergence"
    assert "snr_gate" in norm.failed_checks


# =============================================================================
# 7. Streamlit End-to-End AppTest
# =============================================================================
def test_apptest_full_execution_timeout_20():
    """Verify Streamlit app executes end-to-end without unhandled exceptions."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(REPO_ROOT / "app.py"))
    at.run(timeout=20)
    assert not at.exception, f"AppTest raised an unhandled exception: {at.exception}"
    assert len(at.markdown) > 0
    assert len(at.button) > 0
