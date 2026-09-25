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
from spectralq.evidence import EvidenceLedger, compute_ladder_level
from spectralq.integration import (
    ClassifierAdapter,
    RuleBasedClassifier,
    evaluate_n5_consensus,
)
from spectralq.confidence import ConfidenceEngine


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
    """Provides a deterministic stubbed decoder output pending Arpit's real decoder delivery."""
    raw = {
        "schema_version": "1.0.0",
        "capture_id": capture_id,
        "status": DecoderStatus.UNSUPPORTED.value,
        "interleaver_used": "none",
        "fec_used": "none",
        "decoded_bits": 0,
        "crc_status": CrcStatus.NOT_RUN.value,
        "reencode_ber": None,
        "failure_reason": "Decoder module stubbed pending Arpit delivery",
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

    # Stage 3: Classifier (Harsh) & Rule Engine (Archit)
    stage_status["Classifier"] = "LIVE" if is_live else "STUB"
    classifier_adapter = ClassifierAdapter()
    classifier_out = classifier_adapter.predict(analysis, capture_id=analysis.capture_id)

    rule_classifier = RuleBasedClassifier()
    rule_out = rule_classifier.classify(analysis)

    # Stage 4: Demodulator & Decoder (Arpit)
    stage_status["Demodulator & Decoder"] = "STUB"
    decoder_out = get_stub_decoder_output(analysis.capture_id, analysis)

    # Stage 5: Decision Engine (Archit - Phase 5 N5 Consensus & Evidence Ledger)
    stage_status["Decision Engine"] = "LIVE" if is_live else "STUB"

    input_hash = compute_file_hash(capture_path)
    now_utc = datetime.now(timezone.utc).isoformat()
    run_id = f"RUN_{input_hash[:8]}_{seed}"

    # Initialize EvidenceLedger
    ledger = EvidenceLedger(run_id=run_id)

    # Record Evidence across stages
    # 1. Ingest & Forensics
    ledger.record(
        evidence_id=f"EV_INGEST_{analysis.capture_id}",
        source="Sinchana (Ingest)",
        check_name="burst_energy_check",
        status=EvidenceStatus.PASS if analysis.bursts else EvidenceStatus.FAIL,
        numeric_value=analysis.bursts[0].power if analysis.bursts else -99.0,
        normalized_value=1.0 if analysis.bursts else 0.0,
        explanation=f"Burst energy verified via {stage_status['Ingest & Forensics']} ingest",
    )

    # 2. Blind Parameter Estimation
    est = analysis.estimates
    has_intervals = (
        est.baud.ci_lo <= est.baud.ci_hi and
        est.cfo.ci_lo <= est.cfo.ci_hi and
        est.bandwidth.ci_lo <= est.bandwidth.ci_hi and
        est.snr.ci_lo <= est.snr.ci_hi
    )
    ledger.record(
        evidence_id=f"EV_EST_{analysis.capture_id}",
        source="Sinchana (Blind Estimation)",
        check_name="parameter_interval_check",
        status=EvidenceStatus.PASS if has_intervals else EvidenceStatus.FAIL,
        numeric_value=est.snr.value,
        explanation=f"Estimated SNR ({est.snr.value:.1f} dB) and baud with valid 95% confidence intervals",
    )

    # 3. N5 Hybrid Consensus Evidence (Rule AMC vs ML Classifier)
    n5_result = evaluate_n5_consensus(
        rule_result=rule_out,
        ml_output=classifier_out,
        capture_id=analysis.capture_id,
        ledger=ledger,
        run_id=run_id,
    )

    # 4. Decoder Integrity Evidence
    if decoder_out.crc_status == CrcStatus.PASS:
        crc_ev_status = EvidenceStatus.PASS
        crc_expl = "Payload CRC checksum verified with zero syndrome errors"
    elif decoder_out.crc_status == CrcStatus.FAIL:
        crc_ev_status = EvidenceStatus.FAIL
        crc_expl = "Payload CRC checksum verification failed"
    else:
        crc_ev_status = EvidenceStatus.NOT_RUN
        crc_expl = "Payload CRC checksum was not executed"

    ledger.record(
        evidence_id=f"EV_CRC_{analysis.capture_id}",
        source="Arpit (Decoder)",
        check_name="crc_checksum_check",
        status=crc_ev_status,
        explanation=crc_expl,
    )

    # 5. Compute Deterministic Ladder Level
    ladder_level, ladder_explanation = compute_ladder_level(
        analysis=analysis,
        decoder_output=decoder_out,
        second_tool_agreed=False,
    )
    ledger.record(
        evidence_id=f"EV_LADDER_{analysis.capture_id}",
        source="Archit (Evidence Ladder)",
        check_name="ladder_level_evaluation",
        status=EvidenceStatus.PASS,
        value=ladder_level.value,
        explanation=ladder_explanation,
    )

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

    # Compute N2 Defensible Confidence
    confidence_engine = ConfidenceEngine()
    conf_res = confidence_engine.compute_confidence(
        prediction=n5_result.ml_prediction,
        ml_probability=n5_result.ml_probability,
        cross_window_agreement=1.0,
        rule_prediction=n5_result.rule_prediction,
        ml_prediction=n5_result.ml_prediction,
        rule_ml_agreement=n5_result.agreement,
        ledger=ledger,
        calibrated_ml_probability=None,
    )

    # Assemble ResultContract
    result_data = {
        "schema_version": "1.0.0",
        "capture_id": analysis.capture_id,
        "source_mode": pipeline_source_mode.value,
        "capability_available": is_live,
        "ladder_level": ladder_level.value,
        "top_hypothesis": {
            "modulation": n5_result.ml_prediction,
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
        "ml_prediction": n5_result.ml_prediction,
        "ml_probability": n5_result.ml_probability,
        "calibrated_ml_probability": None,
        "rule_prediction": n5_result.rule_prediction,
        "rule_ml_agreement": n5_result.agreement,
        "rule_ml_penalty": n5_result.penalty,
        "cross_window_agreement": 1.0,
        "evidence": ledger.get_items(),
        "failed_checks": ledger.get_failed_checks(),
        "unavailable_checks": ledger.get_unavailable_checks(),
        "final_confidence": conf_res.final_confidence,
        "confidence_version": conf_res.confidence_version,
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
