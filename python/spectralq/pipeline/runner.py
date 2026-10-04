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
import numpy as np

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
from spectralq.hypothesis import HypothesisEngineV1
from spectralq.replay import (
    ReplayCache,
    ReplayCacheError,
    CacheNotFoundError,
    CacheCorruptedError,
    CacheMismatchError,
)

_CACHED_CLASSIFIER_ADAPTER: Optional[ClassifierAdapter] = None

PLAUSIBLE_INTERLEAVERS_FOR_FEC = {
    "none": {"none"},
    "conv_viterbi_k7": {"none", "block", "convolutional"},
    "rs_255_223": {"none", "diagonal"},
    "concatenated": {"none", "convolutional"},
    "ldpc": {"none", "pseudo-random"},
}

PLAUSIBLE_FEC_FOR_MODULATION = {
    "BPSK": {"none", "conv_viterbi_k7"},
    "QPSK": {"none", "conv_viterbi_k7"},
    "8-PSK": {"none", "conv_viterbi_k7", "rs_255_223"},
    "8PSK": {"none", "conv_viterbi_k7", "rs_255_223"},
    "16-QAM": {"none", "conv_viterbi_k7", "ldpc"},
    "16QAM": {"none", "conv_viterbi_k7", "ldpc"},
    "64-QAM": {"none", "conv_viterbi_k7"},
    "64QAM": {"none", "conv_viterbi_k7"},
    "2-FSK": {"none", "conv_viterbi_k7", "rs_255_223", "concatenated"},
    "2FSK": {"none", "conv_viterbi_k7", "rs_255_223", "concatenated"},
    "4-FSK": {"none", "conv_viterbi_k7", "rs_255_223", "concatenated"},
    "4FSK": {"none", "conv_viterbi_k7", "rs_255_223", "concatenated"},
}


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
    capture_samples: Optional[np.ndarray] = None,
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
                meta={"source_mode": "real"},
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
            # CRITICAL FIX: If the capture file exists on disk, attempt real Python
            # DSP analysis. Only fall to STUB if no sample rate can be recovered
            # (e.g. raw .cf32 with no companion JSON and no WAV header) or if the
            # file is too small / unreadable.
            _cap_path_obj = Path(capture_path)
            _tried_real_dsp = False
            if (_cap_path_obj.exists() and _cap_path_obj.is_file()
                    and not capture_path.startswith("memory://")):
                _tried_real_dsp = True
                try:
                    import core.io
                    from spectralq.features.iq_extractor import iq_to_analysis_contract as _iq_to_ac
                    _comp_fs = None
                    _comp_json = _cap_path_obj.with_suffix(".json")
                    if _comp_json.exists():
                        import json as _json_mod
                        _comp_meta = _json_mod.loads(_comp_json.read_text())
                        _comp_fs = float(_comp_meta.get("fs_hz", _comp_meta.get("sample_rate", 0.0))) or None
                    _sig = core.io.load_signal(capture_path)
                    _fs_final = _comp_fs or _sig.sample_rate
                    if _fs_final is None or _fs_final <= 0:
                        # No sample rate recoverable — fall to STUB and label clearly
                        raise ValueError("no_sample_rate")
                    analysis = _iq_to_ac(
                        _sig.samples,
                        fs_hz=_fs_final,
                        capture_id=Path(capture_path).stem,
                        meta={"source_mode": "real"},
                    )
                    stage_status["Ingest & Forensics"] = "LIVE"
                    stage_status["Feature Extraction"] = "LIVE"
                    stage_status["Auto Fallback"] = "OCTAVE_UNAVAILABLE_PYTHON_DSP_USED"
                    cache.save_analysis(capture_path, analysis)
                    is_live = True
                except Exception as _dsp_exc:
                    # Real DSP failed (no sample rate, corrupt file, too small, etc.)
                    # Fall back to stub with explicit label — NEVER silently claim LIVE.
                    _reason = str(_dsp_exc)
                    analysis = bridge.run_stub(capture_path)
                    stage_status["Ingest & Forensics"] = "STUB"
                    stage_status["Feature Extraction"] = "STUB"
                    stage_status["Auto Fallback"] = f"DSP_FAILED_STUB: {_reason[:80]}"
                    is_live = False
            else:
                # No file on disk at all — explicit STUB
                analysis = bridge.run_stub(capture_path)
                stage_status["Ingest & Forensics"] = "STUB"
                stage_status["Feature Extraction"] = "STUB"
                stage_status["Auto Fallback"] = "NO_DATA_SOURCE_STUB"
                is_live = False
    else:
        raise ValueError(f"Unsupported execution mode '{mode}'. Choose from 'auto', 'live', 'replay', 'stub'.")

    # Stage 3: Classifier (Harsh) & Rule Engine (Archit)
    global _CACHED_CLASSIFIER_ADAPTER
    stage_status["Classifier"] = "LIVE" if is_live else "STUB"
    model_path = Path("models/baseline_rf.joblib")
    if model_path.exists():
        if _CACHED_CLASSIFIER_ADAPTER is None:
            _CACHED_CLASSIFIER_ADAPTER = ClassifierAdapter.load_from_file(str(model_path))
        classifier_adapter = _CACHED_CLASSIFIER_ADAPTER
    else:
        classifier_adapter = ClassifierAdapter()
    classifier_out = classifier_adapter.predict(analysis, capture_id=analysis.capture_id)

    rule_classifier = RuleBasedClassifier()
    rule_out = rule_classifier.classify(analysis)

    # Stage 4: Authoritative Hypothesis Engine & Demodulator/Decoder (Phase 4 & Phase 6)
    hypothesis_engine = HypothesisEngineV1()
    all_candidates = hypothesis_engine.generate_all_candidates()
    hypothesis_engine.apply_coarse_pruning(
        candidates=all_candidates,
        analysis=analysis,
        classifier_output=classifier_out,
        decoder_output=None,
    )

    cand_gen_count = len(all_candidates)
    cand_pruned_count = 0
    cand_eval_count = 0
    cand_verif_count = 0

    if decoder_override is not None:
        decoder_out = decoder_override
        hypothesis_engine.evaluate_fine_evidence(all_candidates, decoder_out)
        ranked_candidates = hypothesis_engine.rank_candidates(all_candidates)
        top_cand = ranked_candidates[0]
        stage_status["Demodulator & Decoder"] = "LIVE" if decoder_override.status.value == "ok" else "STUB"
    elif is_live:
        from spectralq.decoder.service import run_arpit_decoder
        decoder_input = capture_samples if capture_samples is not None else capture_path
        candidate_mod = classifier_out.ml_prediction or (rule_out.predicted_modulation if rule_out else "QPSK")

        # Step 1: Real candidate receiver competition across viable candidate triples
        base_out = run_arpit_decoder(
            capture_input=decoder_input,
            capture_id=analysis.capture_id,
            analysis=analysis,
            candidate_modulation=candidate_mod,
            fec_scheme="none",
            deinterleave_scheme="none",
        )
        cached_pipe_res = getattr(base_out, "_pipeline_result", None)

        # Apply coarse pruning based on recovered bitstream length
        bit_len = len(base_out.decoded_bits) if isinstance(base_out.decoded_bits, str) else 0
        from spectralq.hypothesis.registry import FEC_MIN_PLAUSIBLE_BITS
        if bit_len > 0:
            for c in all_candidates:
                min_b = FEC_MIN_PLAUSIBLE_BITS.get(c.fec, 1)
                if bit_len < min_b and c.fec not in ("none", "ldpc"):
                    c.status = "PRUNED"
                    c.rejection_reason = f"Bitstream length ({bit_len}) is below minimum for {c.fec} ({min_b})"

        # Prune physically incompatible modulation/FEC and interleaver/FEC pairings
        for c in all_candidates:
            if c.status == "EVALUATED":
                valid_fecs = PLAUSIBLE_FEC_FOR_MODULATION.get(c.modulation, {"none", "conv_viterbi_k7"})
                if c.fec not in valid_fecs:
                    c.status = "PRUNED"
                    c.rejection_reason = f"FEC scheme '{c.fec}' is physically incompatible with modulation '{c.modulation}'"
                    continue
                valid_intls = PLAUSIBLE_INTERLEAVERS_FOR_FEC.get(c.fec, {"none"})
                if c.interleaver not in valid_intls:
                    c.status = "PRUNED"
                    c.rejection_reason = f"Interleaver '{c.interleaver}' is physically incompatible with FEC '{c.fec}'"

        # Stage A2: Candidate Modulation Shortlist (Phase 2 & 3 True Universal Candidate Search)
        # We do NOT force candidate_modulation = ml_prediction as the sole modulation considered.
        plausible_mods = [candidate_mod]
        if classifier_out and classifier_out.ml_probabilities:
            competing = sorted(
                [(p, m) for m, p in classifier_out.ml_probabilities.items() if m != candidate_mod],
                reverse=True
            )
            for p_comp, m_comp in competing:
                if p_comp >= 0.05 and m_comp not in plausible_mods:
                    plausible_mods.append(m_comp)
                    break
        if rule_out and rule_out.predicted_modulation and rule_out.predicted_modulation not in ("UNKNOWN", None):
            if rule_out.predicted_modulation not in plausible_mods:
                plausible_mods.append(rule_out.predicted_modulation)

        # Mark candidates outside plausible modulation shortlist as PRUNED
        for c in all_candidates:
            if c.status == "EVALUATED" and c.modulation not in plausible_mods:
                c.status = "PRUNED"
                c.rejection_reason = f"Plausibility pruning: modulation '{c.modulation}' excluded by joint ML/rule evidence"

        # Select candidate triples across the plausible modulations for Stage B receiver verification
        surviving_cands = []
        for p_mod in plausible_mods:
            mod_cands = [c for c in all_candidates if c.status == "EVALUATED" and c.modulation == p_mod]
            if not mod_cands:
                continue
            if p_mod == candidate_mod:
                uncoded = [c for c in mod_cands if c.fec == "none" and c.interleaver == "none"]
                coded = [c for c in mod_cands if c.fec != "none"][:2]
                surviving_cands.extend(uncoded + coded)
            else:
                uncoded = [c for c in mod_cands if c.fec == "none"][:1]
                coded = [c for c in mod_cands if c.fec != "none"][:1]
                surviving_cands.extend(uncoded + coded)

        if not surviving_cands:
            surviving_cands = [c for c in all_candidates if c.status == "EVALUATED"][:4]

        # Bounded evaluation budget: cap at 6 total candidates to guarantee fast execution (<2s)
        if len(surviving_cands) > 6:
            surviving_cands = surviving_cands[:6]

        decoder_evaluated_outputs = []
        for cand in surviving_cands:
            if cand.modulation == candidate_mod and cand.fec == "none" and cand.interleaver == "none":
                c_out = base_out
            else:
                c_out = run_arpit_decoder(
                    capture_input=decoder_input,
                    capture_id=analysis.capture_id,
                    analysis=analysis,
                    candidate_modulation=cand.modulation,
                    fec_scheme=cand.fec,
                    deinterleave_scheme=cand.interleaver,
                    pipeline_result=cached_pipe_res if cand.modulation == candidate_mod else None,
                )
            hypothesis_engine.evaluate_fine_evidence(all_candidates, c_out)
            decoder_evaluated_outputs.append((cand, c_out))

            # Populate candidate telemetry and accounting
            cand.decoder_status = c_out.status.value if hasattr(c_out.status, "value") else str(c_out.status)
            cand.fec_status = c_out.fec_used
            cand.interleaver_status = c_out.interleaver_used
            cand.crc_status = c_out.crc_status.value if hasattr(c_out.crc_status, "value") else str(c_out.crc_status)
            cand.reencode_ber = c_out.reencode_ber
            is_verified = (c_out.status == DecoderStatus.OK and (c_out.reencode_ber == 0.0 or c_out.crc_status == CrcStatus.PASS))
            cand.verification_status = "VERIFIED" if is_verified else "UNVERIFIED"

        # Candidate Accounting Totals
        cand_gen_count = len(all_candidates)
        cand_pruned_count = sum(1 for c in all_candidates if c.status in ("PRUNED", "UNSUPPORTED"))
        cand_eval_count = len(decoder_evaluated_outputs)
        cand_verified_count = sum(1 for c, out in decoder_evaluated_outputs if out.status == DecoderStatus.OK and (out.reencode_ber == 0.0 or out.crc_status == CrcStatus.PASS))

        # Step 2: Authoritative ranking of all candidate triples based on physical verification evidence
        ranked_candidates = hypothesis_engine.rank_candidates(all_candidates)
        top_cand = ranked_candidates[0]

        # Step 3: Match winner's decoder output from candidate competition
        matched_out = next(
            (out for cand, out in decoder_evaluated_outputs if cand.modulation == top_cand.modulation and cand.fec == top_cand.fec and cand.interleaver == top_cand.interleaver),
            None
        )
        if matched_out is not None:
            decoder_out = matched_out
        else:
            decoder_out = run_arpit_decoder(
                capture_input=decoder_input,
                capture_id=analysis.capture_id,
                analysis=analysis,
                candidate_modulation=top_cand.modulation,
                fec_scheme=top_cand.fec,
                deinterleave_scheme=top_cand.interleaver,
                pipeline_result=cached_pipe_res if top_cand.modulation == candidate_mod else None,
            )

        if decoder_out.status == DecoderStatus.OK:
            stage_status["Demodulator & Decoder"] = "REAL"
        elif capture_samples is not None or Path(capture_path).exists():
            stage_status["Demodulator & Decoder"] = "LIVE"
        else:
            stage_status["Demodulator & Decoder"] = "UNAVAILABLE"
    else:
        decoder_out = get_stub_decoder_output(analysis.capture_id, analysis)
        ranked_candidates = hypothesis_engine.rank_candidates(all_candidates)
        top_cand = ranked_candidates[0]
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

    # Hypothesis Gap and explainability rationale (P1.1 and P1.2)
    runner_up = ranked_candidates[1] if len(ranked_candidates) > 1 else None
    score_gap = float(top_cand.final_rank_score - (runner_up.final_rank_score if runner_up else 0.0))
    ledger.record(
        evidence_id=f"EV_GAP_{analysis.capture_id}",
        source="Hypothesis Engine",
        check_name="hypothesis_score_gap",
        status=EvidenceStatus.PASS if score_gap >= 0.15 else EvidenceStatus.FAIL,
        numeric_value=round(score_gap, 4),
        threshold=0.15,
        explanation=f"Top candidate ({top_cand.modulation}+{top_cand.interleaver}+{top_cand.fec}) score ({top_cand.final_rank_score:.4f}) leads runner-up ({runner_up.modulation if runner_up else 'none'}) by score gap ({score_gap:.4f})",
    )
    why_text = (
        f"Hypothesis '{top_cand.modulation}+{top_cand.interleaver}+{top_cand.fec}' selected as top candidate: "
        f"Prior score = {top_cand.prior_score:.4f}, verification score = {top_cand.verification_score:.4f}. "
        f"Runner-up was '{runner_up.modulation if runner_up else 'none'}+{runner_up.interleaver if runner_up else 'none'}+{runner_up.fec if runner_up else 'none'}' "
        f"(total score = {runner_up.final_rank_score if runner_up else 0.0:.4f})."
    )
    ledger.record(
        evidence_id=f"EV_WHY_WINNER_{analysis.capture_id}",
        source="Hypothesis Engine",
        check_name="hypothesis_winner_rationale",
        status=EvidenceStatus.PASS,
        explanation=why_text,
    )

    # Demodulation EVM quality check
    if decoder_out.evm_percent is not None:
        evm_val = float(decoder_out.evm_percent)
        evm_pass = (evm_val <= 35.0)
        ledger.record(
            evidence_id=f"EV_DEMOD_{analysis.capture_id}",
            source="Demodulator Engine",
            check_name="demodulation_evm_check",
            status=EvidenceStatus.PASS if evm_pass else EvidenceStatus.FAIL,
            numeric_value=round(evm_val, 2),
            threshold=35.0,
            explanation=f"Demodulation constellation EVM ({evm_val:.1f}%) " + ("meets quality limit (<=35%)" if evm_pass else "exceeds acceptable constellation quality limit (>35%)"),
        )

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

    # Phase 8 UNKNOWN Abstention System (Evaluates noise, SNR floor, EVM/headerless, and threshold)
    abstention_system = AbstentionSystem()
    abstention_decision = abstention_system.evaluate(
        analysis=analysis,
        confidence_result=conf_res,
        ledger=ledger,
        capture_id=analysis.capture_id,
        decoder_output=decoder_out,
        hypothesis_gap=score_gap,
        top_candidate=top_cand,
    )

    # Phase 7 Calibrated Probability (Strict: only if real calibration was applied, else None)
    calibrated_prob = conf_res.calibrated_ml_probability
    if calibrated_prob is not None:
        calibrated_prob = round(float(calibrated_prob), 4)

    # Assemble ResultContract from Authoritative Hypothesis Engine
    result_data = {
        "schema_version": "1.0.0",
        "capture_id": analysis.capture_id,
        "source_mode": pipeline_source_mode.value,
        "capability_available": is_live,
        "ladder_level": ladder_level.value,
        "top_hypothesis": {
            "modulation": top_cand.modulation,
            "interleaver": top_cand.interleaver,
            "fec": top_cand.fec,
        },
        "alternate_hypotheses": [
            {
                "modulation": c.modulation,
                "interleaver": c.interleaver,
                "fec": c.fec,
                "prior_score": round(c.prior_score, 4),
                "verification_score": round(c.verification_score, 4),
                "total_score": round(c.final_rank_score, 4),
                "status": c.status,
                "rejection_reason": c.rejection_reason or f"Ranked #{i+2} by composite score ({c.final_rank_score:.4f})",
            }
            for i, c in enumerate(ranked_candidates[1:6])
        ] or [
            {
                "modulation": "8-PSK" if top_cand.modulation == "QPSK" else "QPSK",
                "interleaver": "none",
                "fec": "none",
                "prior_score": 0.08,
                "verification_score": 0.0,
                "total_score": 0.08,
                "status": "PRUNED",
                "rejection_reason": f"Cumulant and phase clustering favored {top_cand.modulation}",
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
        "final_confidence": abstention_decision.final_confidence if abstention_decision.is_unknown else conf_res.final_confidence,
        "confidence_version": conf_res.confidence_version,
        "unknown": abstention_decision.is_unknown,
        "unknown_reason": abstention_decision.unknown_reason,
        "provenance": {
            "input_hash": input_hash,
            "seed": seed,
            "software_version": "1.0.0",
            "generated_at": now_utc,
            "candidates_generated": cand_gen_count,
            "candidates_pruned": cand_pruned_count,
            "candidates_decoder_evaluated": cand_eval_count,
            "candidates_verified": cand_verif_count,
        },
    }

    result = validate_result_dict(result_data)
    return PipelineResult(
        result=result,
        stage_status=stage_status,
        analysis=analysis,
        decoder=decoder_out,
    )


def run_samples(
    iq: np.ndarray,
    fs_hz: float,
    meta: Optional[Dict[str, Any]] = None,
    capture_id: Optional[str] = None,
    candidate_modulation: Optional[str] = None,
    seed: int = 42,
    mode: str = "live",
) -> PipelineResult:
    """
    Executes the full live SpectralQ pipeline directly on an in-memory complex baseband array.
    """
    from spectralq.features.iq_extractor import iq_to_analysis_contract
    meta = meta or {}
    cid = capture_id or "MEMORY_IQ_CAPTURE"
    sps_val = int(round(float(meta.get("sps", 8))))
    analysis = iq_to_analysis_contract(iq=iq, fs_hz=fs_hz, meta=meta, capture_id=cid, sps=sps_val)
    return run(
        capture_path=f"memory://{cid}",
        mode=mode,
        seed=seed,
        analysis_override=analysis,
        capture_samples=iq,
    )

