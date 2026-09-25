"""
Phase 2 Integration & Unit Tests for Pipeline Plumbing & Octave/Python Bridge.

Covers:
1. Dynamic Octave function signature discovery.
2. Successful bridge execution (mocked live).
3. Timeout handling (OctaveTimeoutError).
4. Missing Octave handling (OctaveNotFoundError & stub fallback).
5. Malformed JSON handling (OctaveParseError).
6. Non-zero exit code handling (OctaveExecutionError).
7. Full stub-to-stub pipeline run with per-stage status.
8. Provenance preservation across the whole chain.
9. Named smoke test: test_smoke_stub_pipeline.
"""

import json
import hashlib
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from spectralq.contracts.schemas import (
    SourceMode,
    LadderLevel,
    ResultContract,
    AnalysisContract,
)
from spectralq.pipeline.octave_bridge import (
    OctaveBridge,
    OctaveBridgeError,
    OctaveNotFoundError,
    OctaveTimeoutError,
    OctaveExecutionError,
    OctaveParseError,
)
from spectralq.pipeline.runner import run, compute_file_hash


@pytest.fixture
def mock_valid_octave_analysis_json():
    return {
        "schema_version": "1.0.0",
        "capture_id": "OCTAVE_LIVE_001",
        "source_mode": "real",
        "capability_available": True,
        "fs_hz": 25.0e6,
        "fs_source": "header",
        "bursts": [
            {"start_ms": 1.0, "end_ms": 85.0, "power": -10.5}
        ],
        "estimates": {
            "baud": {"value": 2.0e6, "ci_lo": 1.95e6, "ci_hi": 2.05e6, "method": "octave_cyclic"},
            "cfo": {"value": 250.0, "ci_lo": 200.0, "ci_hi": 300.0, "method": "octave_fft"},
            "bandwidth": {"value": 2.5e6, "ci_lo": 2.4e6, "ci_hi": 2.6e6, "method": "octave_obw"},
            "snr": {"value": 22.0, "ci_lo": 21.0, "ci_hi": 23.0, "method": "octave_m2m4"},
        },
        "features": {
            "cumulants": {
                "C20": 0.01, "C21": 1.0, "C40": 0.99, "C42": -0.99,
                "C60": 0.0, "C63": 0.0, "C80": 0.0,
            },
            "cluster": {
                "count": 4, "silhouette": 0.92, "intra_var": 0.05, "inter_dist": 1.41,
            },
            "evm": 0.03,
            "phase_ambiguity_quality": 0.97,
            "cyclic": None,
        },
    }


# -----------------------------------------------------------------------------
# 1. Dynamic Function Signature Detection & Successful Bridge Execution
# -----------------------------------------------------------------------------
def test_octave_bridge_function_detection(tmp_path):
    script_dir = tmp_path / "octave"
    script_dir.mkdir()
    
    # Write an octave function with an arbitrary name (not 'analyse_capture')
    m_code = """
    function [results] = custom_sig_processor_ntro(capture_file_path)
      % Custom NTRO forensic analysis function
      results = struct('status', 'ok');
    end
    """
    (script_dir / "custom_processor.m").write_text(m_code, encoding="utf-8")

    bridge = OctaveBridge(script_dir=str(script_dir))
    func_info = bridge.detect_available_function()
    assert func_info is not None
    func_name, script_path = func_info
    assert func_name == "custom_sig_processor_ntro"
    assert script_path.name == "custom_processor.m"


def test_octave_bridge_successful_live_execution(tmp_path, mock_valid_octave_analysis_json):
    script_dir = tmp_path / "octave"
    script_dir.mkdir()
    (script_dir / "sig_dsp.m").write_text("function out = sig_dsp(f)\n out=0;\nend", encoding="utf-8")

    bridge = OctaveBridge(script_dir=str(script_dir), octave_executable="/mock/bin/octave-cli")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps(mock_valid_octave_analysis_json)
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc):
        analysis = bridge.run("test_capture.cf32")
        assert isinstance(analysis, AnalysisContract)
        assert analysis.source_mode == SourceMode.REAL
        assert analysis.capability_available is True
        assert analysis.capture_id == "OCTAVE_LIVE_001"


# -----------------------------------------------------------------------------
# 2. Timeout Handling
# -----------------------------------------------------------------------------
def test_octave_bridge_timeout(tmp_path):
    script_dir = tmp_path / "octave"
    script_dir.mkdir()
    (script_dir / "sig_dsp.m").write_text("function out = sig_dsp(f)\n out=0;\nend", encoding="utf-8")

    bridge = OctaveBridge(script_dir=str(script_dir), timeout_sec=2.0, octave_executable="/mock/bin/octave-cli")

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="octave", timeout=2.0)):
        with pytest.raises(OctaveTimeoutError) as exc_info:
            bridge.run_live("test_capture.cf32")
        assert "timed out after 2.0s" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 3. Missing Octave Binary
# -----------------------------------------------------------------------------
def test_octave_bridge_missing_binary(tmp_path):
    script_dir = tmp_path / "octave"
    script_dir.mkdir()
    bridge = OctaveBridge(script_dir=str(script_dir), octave_executable=None)
    # Ensure is_octave_installed is False when binary is missing
    bridge.octave_bin = None

    with pytest.raises(OctaveNotFoundError) as exc_info:
        bridge.run_live("dummy.cf32")
    assert "GNU Octave binary" in str(exc_info.value)

    # Calling run() directly must fall back safely to deterministic stub
    analysis_stub = bridge.run("dummy.cf32")
    assert analysis_stub.source_mode == SourceMode.STUB
    assert analysis_stub.capability_available is False


# -----------------------------------------------------------------------------
# 4. Malformed JSON Handling
# -----------------------------------------------------------------------------
def test_octave_bridge_malformed_json(tmp_path):
    script_dir = tmp_path / "octave"
    script_dir.mkdir()
    (script_dir / "sig_dsp.m").write_text("function out = sig_dsp(f)\n out=0;\nend", encoding="utf-8")

    bridge = OctaveBridge(script_dir=str(script_dir), octave_executable="/mock/bin/octave-cli")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "warning: internal matrix dimension mismatch\nNaN Inf"
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc):
        with pytest.raises(OctaveParseError) as exc_info:
            bridge.run_live("dummy.cf32")
        assert "Failed to parse Octave JSON output" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 5. Non-Zero Exit Code Handling
# -----------------------------------------------------------------------------
def test_octave_bridge_nonzero_exit(tmp_path):
    script_dir = tmp_path / "octave"
    script_dir.mkdir()
    (script_dir / "sig_dsp.m").write_text("function out = sig_dsp(f)\n out=0;\nend", encoding="utf-8")

    bridge = OctaveBridge(script_dir=str(script_dir), octave_executable="/mock/bin/octave-cli")

    mock_proc = MagicMock()
    mock_proc.returncode = 127
    mock_proc.stdout = ""
    mock_proc.stderr = "error: signal_processing_toolbox not loaded"

    with patch("subprocess.run", return_value=mock_proc):
        with pytest.raises(OctaveExecutionError) as exc_info:
            bridge.run_live("dummy.cf32")
        assert "non-zero code 127" in str(exc_info.value)
        assert "signal_processing_toolbox" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 6. Full Stub Pipeline Run with Per-Stage Status
# -----------------------------------------------------------------------------
def test_full_stub_pipeline_run(tmp_path):
    dummy_capture = tmp_path / "capture_sample_01.cf32"
    dummy_capture.write_bytes(b"\x00\x01\x02\x03" * 1024)

    pipeline_res = run(str(dummy_capture), seed=123)
    res = pipeline_res.result
    status = pipeline_res.stage_status

    # Check that per-stage statuses are explicitly tracked
    assert status["Ingest & Forensics"] == "STUB"
    assert status["Feature Extraction"] == "STUB"
    assert status["Classifier"] == "STUB"
    assert status["Demodulator & Decoder"] == "STUB"
    assert status["Decision Engine"] == "STUB"

    # Check ResultContract
    assert isinstance(res, ResultContract)
    assert res.source_mode == SourceMode.STUB
    assert res.capability_available is False
    assert res.ladder_level == LadderLevel.L2
    assert res.top_hypothesis.modulation == "QPSK"


# -----------------------------------------------------------------------------
# 7. Provenance Preservation Across Entire Pipeline Chain
# -----------------------------------------------------------------------------
def test_provenance_survives_chain(tmp_path):
    capture_file = tmp_path / "provenance_test.cf32"
    test_content = b"SpectralQ NTRO Phase 2 Provenance Test Payload"
    capture_file.write_bytes(test_content)
    expected_hash = hashlib.sha256(test_content).hexdigest()

    pipeline_res = run(str(capture_file), seed=999)
    res = pipeline_res.result

    assert res.provenance.input_hash == expected_hash
    assert res.provenance.seed == 999
    assert res.provenance.software_version == "1.0.0"
    assert len(res.provenance.generated_at) > 0


# -----------------------------------------------------------------------------
# 8. Named Smoke Test (Required Milestone)
# -----------------------------------------------------------------------------
def test_smoke_stub_pipeline(tmp_path):
    """
    Named smoke test:
    stub analysis.json + stub decoder output + stub ML output -> pipeline.run() -> valid result.json
    """
    sample_file = tmp_path / "smoke_signal.cf32"
    sample_file.write_bytes(b"\xaa\x55" * 512)

    pipeline_res = run(str(sample_file))
    res = pipeline_res.result

    # 1. Returned object must be a valid ResultContract
    assert isinstance(res, ResultContract)
    # 2. Strict field integrity
    assert res.schema_version == "1.0.0"
    assert res.capture_id == "smoke_signal"
    assert res.source_mode == SourceMode.STUB
    assert res.capability_available is False
    assert res.unknown is False
    assert 0.0 <= res.final_confidence <= 1.0
    assert len(res.evidence) >= 2
    # 3. Serializability to valid JSON
    json_output = res.model_dump_json(indent=2)
    parsed = json.loads(json_output)
    assert parsed["capture_id"] == "smoke_signal"
    assert parsed["source_mode"] == "stub"
