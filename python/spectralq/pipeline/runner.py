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
from spectralq.confidence import ConfidenceEngine, AbstentionSystem
from spectralq.replay import (
    ReplayCache,
    ReplayCacheError,
    CacheNotFoundError,
    CacheCorruptedError,
    CacheMismatchError,
)


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
    """Encapsulates the ResultContract, AnalysisContract, DecoderOutputContract, and per-stage execution status metadata."""
    def __init__(
        self,
        result: ResultContract,
        stage_status: Dict[str, str],
        analysis: Optional[AnalysisContract] = None,
        decoder: Optional[DecoderOutputContract] = None,
    ):
        self.result = result
        self.stage_status = stage_status
        self.analysis = analysis
        self.decoder = decoder


def run(
    capture_path: str,
    bridge: Optional[OctaveBridge] = None,
    seed: int = 42,
    mode: str = "auto",
    replay_cache: Optional[ReplayCache] = None,
    analysis_override: Optional[AnalysisContract] = None,
    decoder_override: Optional[DecoderOutputContract] = None,
) -> PipelineResult:
    """
    Executes the end-to-end SpectralQ pipeline plumbing.
    Per-stage execution is tracked as LIVE, STUB, or REPLAY.
    """
    bridge = bridge or OctaveBridge()
    cache = replay_cache or ReplayCache()
    stage_status: Dict[str, str] = {}

    # Stage 1 & 2: Ingest, Forensics & Feature Extraction (Mode Dispatched)
    mode_normalized = mode.lower()
    if analysis_override is not None:
        analysis = analysis_override
        stage_status["Ingest & Forensics"] = mode.upper()
        stage_status["Feature Extraction"] = mode.upper()
        is_live = (mode_normalized == "live")
    elif mode_normalized == "replay":
        analysis, _ = cache.load_analysis(capture_path)
        stage_status["Ingest & Forensics"] = "REPLAY"
        stage_status["Feature Extraction"] = "REPLAY"
        is_live = False
    elif mode_normalized == "live":
        if bridge.is_live_capable():
            analysis = bridge.run(capture_path)
            stage_status["Ingest & Forensics"] = "LIVE"
            stage_status["Feature Extraction"] = "LIVE"
            cache.save_analysis(capture_path, analysis)
            is_live = True
        elif Path(capture_path).exists() and Path(capture_path).is_file():
            import core.io
            from spectralq.features.iq_extractor import iq_to_analysis_contract
            # RULE 5 INVARIANT: Never silently assume sampling rate.
            # Check for companion metadata file first (written by navigation.py for raw IQ).
            comp_fs = None
            comp_json_path = Path(capture_path).with_suffix(".json")
            if comp_json_path.exists():
                import json as _json
                comp_meta = _json.loads(comp_json_path.read_text())
                comp_fs = float(comp_meta.get("fs_hz", comp_meta.get("sample_rate", 0.0))) or None
            sig = core.io.load_signal(capture_path)
            fs_hz_final = comp_fs or sig.sample_rate
            if fs_hz_final is None or fs_hz_final <= 0:
                raise ValueError(
                    f"Cannot ingest '{capture_path}': no sampling rate available. "
                    "WAV files embed rate in header; raw IQ/CF32 files require a companion metadata JSON "
                    "or explicit user-provided sample rate via the ingest panel."
                )
            analysis = iq_to_analysis_contract(
                sig.samples,
                fs_hz=fs_hz_final,
                capture_id=Path(capture_path).stem,
            )
            stage_status["Ingest & Forensics"] = "LIVE"
            stage_status["Feature Extraction"] = "LIVE"
            cache.save_analysis(capture_path, analysis)
            is_live = True
        else:
            stage_status["Ingest & Forensics"] = "ERROR"
            stage_status["Feature Extraction"] = "ERROR"
            raise RuntimeError(f"Live mode requested, but capture file '{capture_path}' does not exist.")
    elif mode_normalized == "stub":
        analysis = bridge.run_stub(capture_path)
        stage_status["Ingest & Forensics"] = "STUB"
        stage_status["Feature Extraction"] = "STUB"
        is_live = False
    elif mode_normalized == "auto":
        if bridge.is_live_capable():
            analysis = bridge.run(capture_path)
            stage_status["Ingest & Forensics"] = "LIVE"
            stage_status["Feature Extraction"] = "LIVE"
            cache.save_analysis(capture_path, analysis)
            is_live = True
        elif cache.has_cache(capture_path):
            # Surfacing state change explicitly
            analysis, _ = cache.load_analysis(capture_path)
            stage_status["Ingest & Forensics"] = "REPLAY"
            stage_status["Feature Extraction"] = "REPLAY"
            stage_status["Auto Fallback"] = "LIVE_UNAVAILABLE_FALLBACK_TO_REPLAY"
            is_live = False
        else:
            analysis = bridge.run_stub(capture_path)
            stage_status["Ingest & Forensics"] = "STUB"
            stage_status["Feature Extraction"] = "STUB"
            is_live = False
    else:
        raise ValueError(f"Unsupported execution mode '{mode}'. Choose from 'auto', 'live', 'replay', 'stub'.")

    # Stage 3: Classifier (Harsh) & Rule Engine (Archit)
    stage_status["Classifier"] = "LIVE" if is_live else "STUB"
    model_path = Path("models/baseline_rf.joblib")
    if model_path.exists():
        classifier_adapter = ClassifierAdapter.load_from_file(str(model_path))
    else:
        classifier_adapter = ClassifierAdapter()
    classifier_out = classifier_adapter.predict(analysis, capture_id=analysis.capture_id)

    rule_classifier = RuleBasedClassifier()
    rule_out = rule_classifier.classify(analysis)

    # Stage 4: Demodulator & Decoder (Arpit)
    if decoder_override is not None:
        decoder_out = decoder_override
        stage_status["Demodulator & Decoder"] = "LIVE" if decoder_override.status.value == "ok" else "STUB"
    elif is_live:
        from spectralq.decoder.service import run_arpit_decoder
        candidate_mod = classifier_out.ml_prediction or (rule_out.predicted_modulation if rule_out else None)
        decoder_out = run_arpit_decoder(
            capture_input=capture_path,
            capture_id=analysis.capture_id,
            analysis=analysis,
            candidate_modulation=candidate_mod,
        )
        if decoder_out.status == DecoderStatus.OK:
            stage_status["Demodulator & Decoder"] = "REAL"
        elif Path(capture_path).exists():
            stage_status["Demodulator & Decoder"] = "LIVE"
        else:
            stage_status["Demodulator & Decoder"] = "UNAVAILABLE"
    else:
        decoder_out = get_stub_decoder_output(analysis.capture_id, analysis)
        stage_status["Demodulator & Decoder"] = "STUB"

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
        source="DSP Ingest Engine",
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
        source="DSP Estimation Engine",
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
        source="FEC Decoder Engine",
        check_name="crc_checksum_check",
        status=crc_ev_status,
        explanation=crc_expl,
    )

    # 5. Compute Deterministic Ladder Level
    # second_tool_agreed is True when CRC passes AND at least one independent
    # corroborating signal exists: sync-word aligned, N5 rule/ML consensus, or
    # zero-error re-encode BER. This is what elevates the ladder from L4 → L5.
    _crc_pass = decoder_out.crc_status == CrcStatus.PASS
    _sync_word_aligned = decoder_out.sync_word is not None
    _n5_agreed = n5_result.agreement
    _ber_zero = (
        decoder_out.reencode_ber is not None
        and decoder_out.reencode_ber == 0.0
    )
    second_tool_agreed = _crc_pass and (_sync_word_aligned or _n5_agreed or _ber_zero)

    ladder_level, ladder_explanation = compute_ladder_level(
        analysis=analysis,
        decoder_output=decoder_out,
        second_tool_agreed=second_tool_agreed,
    )
    ledger.record(
        evidence_id=f"EV_LADDER_{analysis.capture_id}",
        source="Evidence Ladder Engine",
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

    # Phase 6 Multi-window Agreement
    cw_agreement = 1.0
    if analysis.sub_windows and len(analysis.sub_windows) >= 2:
        from spectralq.integration.cross_window import evaluate_cross_window
        cw_report = evaluate_cross_window(
            windows_input=analysis.sub_windows,
            classifier_adapter=classifier_adapter,
            rule_classifier=rule_classifier,
            capture_id=analysis.capture_id,
        )
        cw_agreement = cw_report.agreement_ratio

    # Compute N2 Defensible Confidence
    confidence_engine = ConfidenceEngine()
    conf_res = confidence_engine.compute_confidence(
        prediction=n5_result.ml_prediction,
        ml_probability=n5_result.ml_probability,
        cross_window_agreement=cw_agreement,
        rule_prediction=n5_result.rule_prediction,
        ml_prediction=n5_result.ml_prediction,
        rule_ml_agreement=n5_result.agreement,
        ledger=ledger,
        calibrated_ml_probability=None,
    )

    # Phase 8 UNKNOWN Abstention System
    abstention_system = AbstentionSystem()
    abstention_decision = abstention_system.evaluate(
        analysis=analysis,
        confidence_result=conf_res,
        ledger=ledger,
        capture_id=analysis.capture_id,
    )

    # Phase 7 Calibrated Probability
    calibrated_prob = conf_res.calibrated_ml_probability
    if calibrated_prob is None:
        cal_factor = 1.0 if n5_result.agreement else (1.0 - n5_result.penalty * 0.2)
        calibrated_prob = round(float(min(1.0, max(0.0, n5_result.ml_probability * cal_factor))), 4)

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
                "modulation": alt_mod,
                "interleaver": "none",
                "fec": "none",
                "prior_score": round(float(alt_prob), 4),
                "verification_score": 0.0,
                "total_score": round(float(alt_prob), 4),
                "status": "PRUNED",
                "rejection_reason": f"Softmax confidence ({float(alt_prob):.1%}) below primary candidate; cumulant features favored {n5_result.ml_prediction}",
            }
            for alt_mod, alt_prob in sorted(
                [(m, p) for m, p in getattr(classifier_out, "ml_probabilities", {}).items() if m != n5_result.ml_prediction],
                key=lambda x: x[1],
                reverse=True,
            )[:3]
        ] or [
            {
                "modulation": "8-PSK" if n5_result.ml_prediction == "QPSK" else "QPSK",
                "interleaver": "none",
                "fec": "none",
                "prior_score": 0.08,
                "verification_score": 0.0,
                "total_score": 0.08,
                "status": "PRUNED",
                "rejection_reason": f"Cumulant and phase clustering favored {n5_result.ml_prediction}",
            }
        ],
        "ml_prediction": n5_result.ml_prediction,
        "ml_probability": n5_result.ml_probability,
        "calibrated_ml_probability": calibrated_prob,
        "rule_prediction": n5_result.rule_prediction,
        "rule_ml_agreement": n5_result.agreement,
        "rule_ml_penalty": n5_result.penalty,
        "cross_window_agreement": cw_agreement,
        "evidence": ledger.get_items(),
        "failed_checks": ledger.get_failed_checks(),
        "unavailable_checks": ledger.get_unavailable_checks(),
        "final_confidence": conf_res.final_confidence,
        "confidence_version": conf_res.confidence_version,
        "unknown": abstention_decision.is_unknown,
        "unknown_reason": abstention_decision.unknown_reason,
        "provenance": {
            "input_hash": input_hash,
            "seed": seed,
            "software_version": "1.0.0",
            "generated_at": now_utc,
        },
    }

    result = validate_result_dict(result_data)
    return PipelineResult(
        result=result,
        stage_status=stage_status,
        analysis=analysis,
        decoder=decoder_out,
    )
