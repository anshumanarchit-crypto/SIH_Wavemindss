"""
SpectralQ Pipeline Runner (Phase 2 Plumbing).
Coordinates:
1. Ingest via OctaveBridge (live or stub).
2. Schema validation of analysis.json.
3. Stubbed classifier and decoder outputs.
4. Pass-through decision engine stub.
5. Emitting schema-valid result.json with per-stage execution tracking.
"""

import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from spectralq.contracts.schemas import (
    AnalysisContract,
    ClassifierOutputContract,
    DecoderOutputContract,
    DecoderStatus,
    CrcStatus,
    LadderLevel,
    EvidenceStatus,
    EvidenceItem,
    HypothesisItem,
    AlternateHypothesisItem,
    ProvenanceBlock,
    ResultContract,
    SourceMode,
    validate_analysis_dict,
    validate_classifier_output_dict,
    validate_decoder_output_dict,
    validate_result_dict,
)
from spectralq.pipeline.octave_bridge import OctaveBridge


def compute_file_hash(file_path: str) -> str:
    """Computes SHA-256 hash of a file or string path if file is virtual/missing."""
    p = Path(file_path)
    if p.exists() and p.is_file():
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    else:
        return hashlib.sha256(file_path.encode("utf-8")).hexdigest()


def get_stub_classifier_output(capture_id: str, analysis: AnalysisContract) -> ClassifierOutputContract:
    """Provides a deterministic stubbed classifier output."""
    raw = {
        "schema_version": "1.0.0",
        "capture_id": capture_id,
        "window_id": 0,
        "ml_prediction": "QPSK",
        "ml_probabilities": {
            "BPSK": 0.05,
            "QPSK": 0.85,
            "8-PSK": 0.04,
            "16-QAM": 0.03,
            "64-QAM": 0.01,
            "2-FSK": 0.01,
            "4-FSK": 0.01,
        },
        "calibrated_probability": 0.82,
        "model_version": "stub-rf-1.0.0",
        "feature_vector_used": {
            "C20": analysis.features.cumulants.C20,
            "C40": analysis.features.cumulants.C40,
            "C42": analysis.features.cumulants.C42,
            "snr": analysis.estimates.snr.value,
            "evm": analysis.features.evm,
        },
    }
    return validate_classifier_output_dict(raw)


def get_stub_decoder_output(capture_id: str, analysis: AnalysisContract) -> DecoderOutputContract:
    """Provides a deterministic stubbed decoder output."""
    raw = {
        "schema_version": "1.0.0",
        "capture_id": capture_id,
        "status": DecoderStatus.OK.value,
        "interleaver_used": "none",
        "fec_used": "none",
        "decoded_bits": "1010110011110000",
        "crc_status": CrcStatus.PASS.value,
        "reencode_ber": 0.002,
        "failure_reason": None,
    }
    return validate_decoder_output_dict(raw)


class PipelineResult:
    """Encapsulates the ResultContract and per-stage execution status metadata."""
    def __init__(self, result: ResultContract, stage_status: Dict[str, str]):
        self.result = result
        self.stage_status = stage_status


def run(
    capture_path: str,
    bridge: Optional[OctaveBridge] = None,
    seed: int = 42,
) -> PipelineResult:
    """
    Executes the end-to-end SpectralQ pipeline plumbing.
    Per-stage execution is tracked as LIVE, STUB, or REPLAY.
    """
    bridge = bridge or OctaveBridge()
    stage_status: Dict[str, str] = {}

    # Stage 1 & 2: Ingest, Forensics & Feature Extraction
    is_live = bridge.is_live_capable()
    stage_status["Ingest & Forensics"] = "LIVE" if is_live else "STUB"
    stage_status["Feature Extraction"] = "LIVE" if is_live else "STUB"

    analysis: AnalysisContract = bridge.run(capture_path)

    # Stage 3: Classifier (Harsh)
    stage_status["Classifier"] = "STUB"
    classifier_out = get_stub_classifier_output(analysis.capture_id, analysis)

    # Stage 4: Demodulator & Decoder (Arpit)
    stage_status["Demodulator & Decoder"] = "STUB"
    decoder_out = get_stub_decoder_output(analysis.capture_id, analysis)

    # Stage 5: Decision Engine (Archit - pass-through stub for Phase 2)
    stage_status["Decision Engine"] = "STUB"

    input_hash = compute_file_hash(capture_path)
    now_utc = datetime.now(timezone.utc).isoformat()

    # Determine source mode
    if analysis.source_mode == SourceMode.REPLAY:
        pipeline_source_mode = SourceMode.REPLAY
        stage_status["Ingest & Forensics"] = "REPLAY"
    elif analysis.source_mode == SourceMode.REAL:
        pipeline_source_mode = SourceMode.REAL
    elif analysis.source_mode == SourceMode.SYNTHETIC:
        pipeline_source_mode = SourceMode.SYNTHETIC
    else:
        pipeline_source_mode = SourceMode.STUB

    # Assemble ResultContract
    result_data = {
        "schema_version": "1.0.0",
        "capture_id": analysis.capture_id,
        "source_mode": pipeline_source_mode.value,
        "capability_available": is_live,
        "ladder_level": LadderLevel.L2.value if pipeline_source_mode == SourceMode.STUB else LadderLevel.L3.value,
        "top_hypothesis": {
            "modulation": classifier_out.ml_prediction,
            "interleaver": decoder_out.interleaver_used,
            "fec": decoder_out.fec_used,
        },
        "alternate_hypotheses": [
            {
                "modulation": "BPSK",
                "interleaver": "none",
                "fec": "none",
                "prior_score": 0.05,
                "verification_score": 0.0,
                "total_score": 0.02,
                "status": "PRUNED",
                "rejection_reason": "Cumulant distance favors QPSK",
            }
        ],
        "ml_prediction": classifier_out.ml_prediction,
        "ml_probability": classifier_out.ml_probabilities.get(classifier_out.ml_prediction, 0.85),
        "calibrated_ml_probability": classifier_out.calibrated_probability,
        "rule_prediction": "QPSK",
        "rule_ml_agreement": True,
        "rule_ml_penalty": 0.0,
        "cross_window_agreement": 0.95,
        "evidence": [
            {
                "evidence_id": "EV_INGEST_001",
                "source": "octave_bridge",
                "check_name": "burst_energy_check",
                "status": EvidenceStatus.PASS.value,
                "value": analysis.bursts[0].power if analysis.bursts else 0.0,
                "explanation": f"Burst energy verified via {stage_status['Ingest & Forensics']} ingest",
            },
            {
                "evidence_id": "EV_DECODE_001",
                "source": "decoder_stub",
                "check_name": "crc_status",
                "status": EvidenceStatus.PASS.value,
                "value": decoder_out.crc_status.value,
                "explanation": "Frame integrity check pass",
            },
        ],
        "final_confidence": 0.82,
        "confidence_version": "phase2-plumbing-1.0.0",
        "unknown": False,
        "unknown_reason": None,
        "provenance": {
            "input_hash": input_hash,
            "seed": seed,
            "software_version": "1.0.0",
            "generated_at": now_utc,
        },
    }

    result = validate_result_dict(result_data)
    return PipelineResult(result=result, stage_status=stage_status)
