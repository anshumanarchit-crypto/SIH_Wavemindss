"""
Real Team Integration Adapters for SpectralQ Phase 11.

Consumes real outputs from teammates:
- SINCHANA: Ingest, Blind Estimation, Forensics, and Feature Extraction (analysis.json)
- ARPIT: Carrier/Timing Recovery, Demodulation, Deinterleaving, and FEC Decoding (decoder_output.json)
- HARSH: RandomForest Modulation Classifier (predictions and probabilities)

Strict Invariants:
1. Sinchana: Consumes real analysis.json without recomputing her DSP features.
   Validates schema, provenance, uncertainty intervals, sub-window info, and handles
   legitimately absent features strictly as UNAVAILABLE (never as zero or fake passes).
2. Arpit: Consumes real decoder output (demodulated bits, decoder status, interleaver/FEC,
   CRC result, BER/re-encode evidence). Does NOT duplicate his decoder logic.
3. Harsh: Consumes real classifier predictions/probabilities. Validates feature name and
   exact ordering compatibility against Phase 1 schema explicitly. If feature vector
   does not match, fails loudly with a structured FeatureCompatibilityError.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from spectralq.contracts.schemas import (
    AnalysisContract,
    DecoderOutputContract,
    ClassifierOutputContract,
    ResultContract,
    EvidenceStatus,
    DecoderStatus,
    CrcStatus,
    LadderLevel,
    SourceMode,
    validate_analysis_dict,
    validate_decoder_output_dict,
    validate_classifier_output_dict,
    validate_result_dict,
)
from spectralq.evidence.ledger import EvidenceLedger
from spectralq.evidence.ladder import compute_ladder_level
from spectralq.hypothesis.engine import HypothesisEngineV1
from spectralq.hypothesis.registry import MODULATIONS
from spectralq.integration.classifier_adapter import (
    CANONICAL_FEATURE_NAMES,
    ClassifierAdapter,
)
from spectralq.integration.rule_classifier import RuleBasedClassifier
from spectralq.integration.n5_fusion import evaluate_n5_consensus

DEFAULT_ABSTENTION_THRESHOLD = 0.80


class IntegrationError(Exception):
    """Base exception for team integration errors."""
    pass


class FeatureCompatibilityError(IntegrationError):
    """
    Raised when Harsh's classifier feature vector does not strictly match
    the canonical Phase 1 schema in names or order. Fails loudly with full diagnostics.
    """
    def __init__(self, message: str, report: Dict[str, Any]):
        super().__init__(message)
        self.report = report

    def __str__(self) -> str:
        return f"{super().__str__()}\nMismatch Diagnostics: {json.dumps(self.report, indent=2)}"


class SinchanaContractError(IntegrationError):
    """Raised when Sinchana's analysis fails schema or provenance validation."""
    pass


class ArpitContractError(IntegrationError):
    """Raised when Arpit's decoder output fails schema validation."""
    pass


# -----------------------------------------------------------------------------
# 1. Sinchana Integration Adapter
# -----------------------------------------------------------------------------
def consume_sinchana_analysis(
    source: Union[str, Path, Dict[str, Any], AnalysisContract]
) -> AnalysisContract:
    """
    Consumes real analysis.json from Sinchana.
    Does NOT recompute her DSP features.
    Validates schema, provenance, known-vs-estimated fields, uncertainty fields,
    sub-window info, and preserves feature availability.
    """
    if isinstance(source, AnalysisContract):
        analysis = source
    elif isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists():
            raise SinchanaContractError(f"Sinchana analysis file not found at: {source}")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            analysis = validate_analysis_dict(data)
        except Exception as exc:
            raise SinchanaContractError(f"Failed to validate Sinchana analysis from '{source}': {exc}") from exc
    elif isinstance(source, dict):
        try:
            analysis = validate_analysis_dict(source)
        except Exception as exc:
            raise SinchanaContractError(f"Failed to validate Sinchana analysis dict: {exc}") from exc
    else:
        raise SinchanaContractError(f"Unsupported source type for Sinchana analysis: {type(source)}")

    # Verify uncertainty interval order on all estimates
    est = analysis.estimates
    for param_name, param_est in [
        ("baud", est.baud),
        ("cfo", est.cfo),
        ("bandwidth", est.bandwidth),
        ("snr", est.snr),
    ]:
        if param_est.ci_lo > param_est.ci_hi:
            raise SinchanaContractError(
                f"Invalid uncertainty interval for estimate '{param_name}': "
                f"ci_lo ({param_est.ci_lo}) > ci_hi ({param_est.ci_hi})"
            )

    return analysis


# -----------------------------------------------------------------------------
# 2. Arpit Integration Adapter
# -----------------------------------------------------------------------------
def consume_arpit_decoder_output(
    source: Union[str, Path, Dict[str, Any], DecoderOutputContract]
) -> DecoderOutputContract:
    """
    Consumes real decoder output from Arpit.
    Demodulated bits, decoder status, interleaver/FEC, CRC result, and BER/re-encode evidence.
    Does NOT duplicate Arpit's decoding logic.
    """
    if isinstance(source, DecoderOutputContract):
        return source
    elif isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists():
            raise ArpitContractError(f"Arpit decoder output file not found at: {source}")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return validate_decoder_output_dict(data)
        except Exception as exc:
            raise ArpitContractError(f"Failed to validate Arpit decoder output from '{source}': {exc}") from exc
    elif isinstance(source, dict):
        try:
            return validate_decoder_output_dict(source)
        except Exception as exc:
            raise ArpitContractError(f"Failed to validate Arpit decoder output dict: {exc}") from exc
    else:
        raise ArpitContractError(f"Unsupported source type for Arpit decoder output: {type(source)}")


# -----------------------------------------------------------------------------
# 3. Harsh Integration Adapter & Feature Compatibility Guard
# -----------------------------------------------------------------------------
def validate_harsh_feature_compatibility(
    features: Union[Dict[str, float], List[str]],
    expected_features: Optional[List[str]] = None,
) -> None:
    """
    Validates feature name and exact ordering compatibility against Phase 1 schema.
    If feature names or order do not match, fails loudly with a specific mismatch report.
    Never silently reorders or guesses.
    """
    expected = expected_features or CANONICAL_FEATURE_NAMES

    if isinstance(features, dict):
        received_names = list(features.keys())
    else:
        received_names = list(features)

    expected_set = set(expected)
    received_set = set(received_names)

    missing = [f for f in expected if f not in received_set]
    extra = [f for f in received_names if f not in expected_set]

    # Check exact ordering
    ordering_mismatches = []
    if not missing and not extra:
        for idx, (exp, rec) in enumerate(zip(expected, received_names)):
            if exp != rec:
                ordering_mismatches.append({
                    "index": idx,
                    "expected_feature": exp,
                    "received_feature": rec,
                })

    if missing or extra or ordering_mismatches:
        report = {
            "error_type": "FeatureCompatibilityMismatch",
            "expected_feature_count": len(expected),
            "received_feature_count": len(received_names),
            "expected_features_in_order": expected,
            "received_features_in_order": received_names,
            "missing_features": missing,
            "extra_features": extra,
            "ordering_mismatches": ordering_mismatches,
        }
        raise FeatureCompatibilityError(
            f"Harsh classifier feature vector does NOT match Phase 1 canonical schema! "
            f"Missing: {missing}, Extra: {extra}, Ordering Mismatches: {len(ordering_mismatches)}",
            report=report,
        )


def consume_harsh_classifier_output(
    source: Union[str, Path, Dict[str, Any], ClassifierOutputContract],
    expected_features: Optional[List[str]] = None,
) -> ClassifierOutputContract:
    """
    Consumes real classifier output from Harsh.
    Validates schema and strictly enforces feature name/order compatibility.
    """
    if isinstance(source, ClassifierOutputContract):
        contract = source
    elif isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists():
            raise IntegrationError(f"Harsh classifier output file not found at: {source}")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            contract = validate_classifier_output_dict(data)
        except Exception as exc:
            raise IntegrationError(f"Failed to validate Harsh classifier output from '{source}': {exc}") from exc
    elif isinstance(source, dict):
        try:
            contract = validate_classifier_output_dict(source)
        except Exception as exc:
            raise IntegrationError(f"Failed to validate Harsh classifier output dict: {exc}") from exc
    else:
        raise IntegrationError(f"Unsupported source type for Harsh classifier output: {type(source)}")

    # Enforce strict feature compatibility on feature_vector_used
    validate_harsh_feature_compatibility(
        contract.feature_vector_used,
        expected_features=expected_features,
    )

    return contract


# -----------------------------------------------------------------------------
# 4. Full Real Pipeline Chain Execution
# -----------------------------------------------------------------------------
def run_real_team_pipeline(
    analysis_input: Union[str, Path, Dict[str, Any], AnalysisContract],
    decoder_input: Union[str, Path, Dict[str, Any], DecoderOutputContract],
    classifier_input: Optional[Union[str, Path, Dict[str, Any], ClassifierOutputContract]] = None,
    classifier_adapter: Optional[ClassifierAdapter] = None,
    seed: int = 42,
    abstention_threshold: float = DEFAULT_ABSTENTION_THRESHOLD,
    capture_path: Optional[str] = None,
) -> Tuple[ResultContract, Dict[str, str]]:
    """
    Executes the end-to-end SpectralQ chain using real data from Sinchana, Arpit, and Harsh:
    analysis -> feature/classifier integration -> rule path -> N5 -> hypothesis engine
    -> evidence ledger -> ladder_level -> calibrated probability -> hybrid confidence
    -> UNKNOWN threshold -> result.json.
    """
    stage_status: Dict[str, str] = {}

    # 1. SINCHANA: Ingest & Feature Extraction
    analysis = consume_sinchana_analysis(analysis_input)
    stage_status["Ingest & Forensics"] = "REAL" if analysis.source_mode == SourceMode.REAL else "LIVE"
    stage_status["Feature Extraction"] = "REAL" if analysis.source_mode == SourceMode.REAL else "LIVE"

    # 2. ARPIT: Demodulator & Decoder Output
    decoder_output = consume_arpit_decoder_output(decoder_input)
    stage_status["Demodulator & Decoder"] = "REAL" if decoder_output.status == DecoderStatus.OK else "LIVE"

    # 3. HARSH: Classifier Predictions & Feature Compatibility
    if classifier_input is not None:
        classifier_output = consume_harsh_classifier_output(classifier_input)
        stage_status["Classifier"] = "REAL"
    else:
        adapter = classifier_adapter or ClassifierAdapter()
        # Extract features and validate compatibility
        feat_dict = {}
        for f in CANONICAL_FEATURE_NAMES:
            if f in ("C20", "C21", "C40", "C42", "C60", "C63", "C80"):
                feat_dict[f] = float(getattr(analysis.features.cumulants, f))
            elif f == "cluster_count":
                feat_dict[f] = float(analysis.features.cluster.count)
            elif f in ("silhouette", "intra_var", "inter_dist"):
                feat_dict[f] = float(getattr(analysis.features.cluster, f))
            elif f == "evm":
                feat_dict[f] = float(analysis.features.evm)
            elif f == "phase_ambiguity_quality":
                # Handle legitimately absent feature as UNAVAILABLE in evidence, and median 0.5 for classifier vector
                val = analysis.features.phase_ambiguity_quality
                feat_dict[f] = float(val) if val is not None else 0.5
            elif f == "snr":
                feat_dict[f] = float(analysis.estimates.snr.value)
            elif f == "baud":
                feat_dict[f] = float(analysis.estimates.baud.value)

        validate_harsh_feature_compatibility(feat_dict)
        classifier_output = adapter.predict(feat_dict, capture_id=analysis.capture_id)
        stage_status["Classifier"] = "LIVE"

    # 4. ARCHIT: Rule Engine & AMC Path
    rule_classifier = RuleBasedClassifier()
    rule_out = rule_classifier.classify(analysis)

    # 5. Evidence Ledger Setup
    cap_path_str = capture_path or f"real/{analysis.capture_id}.cf32"
    run_id = f"RUN_REAL_{analysis.capture_id[:12]}_{seed}"
    ledger = EvidenceLedger(run_id=run_id)

    # Record Ingest Evidence
    if analysis.bursts:
        ledger.record(
            evidence_id=f"EV_INGEST_{analysis.capture_id}",
            source="Sinchana (Ingest)",
            check_name="burst_energy_check",
            status=EvidenceStatus.PASS,
            numeric_value=analysis.bursts[0].power,
            normalized_value=1.0,
            explanation=f"Burst energy detected ({analysis.bursts[0].power:.1f} dBm) via real ingest",
        )
    else:
        ledger.record(
            evidence_id=f"EV_INGEST_{analysis.capture_id}",
            source="Sinchana (Ingest)",
            check_name="burst_energy_check",
            status=EvidenceStatus.FAIL,
            explanation="No signal burst detected above noise floor",
            failure_reason="Zero bursts detected",
        )

    # Record Parameter Estimation Uncertainty Evidence
    est = analysis.estimates
    has_valid_intervals = (
        est.baud.ci_lo <= est.baud.ci_hi and
        est.cfo.ci_lo <= est.cfo.ci_hi and
        est.bandwidth.ci_lo <= est.bandwidth.ci_hi and
        est.snr.ci_lo <= est.snr.ci_hi
    )
    ledger.record(
        evidence_id=f"EV_EST_{analysis.capture_id}",
        source="Sinchana (Blind Estimation)",
        check_name="parameter_uncertainty_check",
        status=EvidenceStatus.PASS if has_valid_intervals else EvidenceStatus.FAIL,
        numeric_value=est.snr.value,
        explanation=f"Estimated SNR ({est.snr.value:.1f} dB) and baud ({est.baud.value:.0f} Hz) with 95% confidence bounds",
    )

    # Record Feature Availability: Legitimate absence is marked UNAVAILABLE (never zero!)
    if analysis.features.phase_ambiguity_quality is None:
        ledger.record(
            evidence_id=f"EV_FEAT_PHASE_AMB_{analysis.capture_id}",
            source="Sinchana (Features)",
            check_name="phase_ambiguity_quality_check",
            status=EvidenceStatus.UNAVAILABLE,
            explanation="Phase ambiguity quality was not computed by Sinchana; marked UNAVAILABLE per contract",
        )
    else:
        paq = analysis.features.phase_ambiguity_quality
        ledger.record(
            evidence_id=f"EV_FEAT_PHASE_AMB_{analysis.capture_id}",
            source="Sinchana (Features)",
            check_name="phase_ambiguity_quality_check",
            status=EvidenceStatus.PASS if paq >= 0.50 else EvidenceStatus.FAIL,
            numeric_value=paq,
            explanation=f"Phase ambiguity resolution quality: {paq:.3f}",
        )

    if analysis.features.cyclic is None:
        ledger.record(
            evidence_id=f"EV_FEAT_CYCLIC_{analysis.capture_id}",
            source="Sinchana (Features)",
            check_name="cyclic_prefix_check",
            status=EvidenceStatus.UNAVAILABLE,
            explanation="Cyclic prefix feature is absent in upstream analysis; marked UNAVAILABLE per contract",
        )

    # 6. N5 Hybrid Consensus
    n5_result = evaluate_n5_consensus(
        rule_result=rule_out,
        ml_output=classifier_output,
        capture_id=analysis.capture_id,
        ledger=ledger,
        run_id=run_id,
    )

    # 7. Arpit Decoder Evidence (No duplication of decoding logic)
    if decoder_output.crc_status == CrcStatus.PASS:
        crc_status = EvidenceStatus.PASS
        crc_expl = "Payload CRC checksum verified with zero syndrome errors"
    elif decoder_output.crc_status == CrcStatus.FAIL:
        crc_status = EvidenceStatus.FAIL
        crc_expl = "Payload CRC verification failed (checksum mismatch)"
    else:
        crc_status = EvidenceStatus.NOT_RUN
        crc_expl = "Payload CRC checksum check was not executed"

    ledger.record(
        evidence_id=f"EV_CRC_{analysis.capture_id}",
        source="Arpit (Decoder)",
        check_name="crc_checksum_check",
        status=crc_status,
        explanation=crc_expl,
    )

    if decoder_output.reencode_ber is not None:
        ber = decoder_output.reencode_ber
        ber_pass = (ber <= 0.05)
        ledger.record(
            evidence_id=f"EV_BER_{analysis.capture_id}",
            source="Arpit (Decoder)",
            check_name="reencode_ber_check",
            status=EvidenceStatus.PASS if ber_pass else EvidenceStatus.FAIL,
            numeric_value=ber,
            explanation=f"Re-encode residual Bit Error Rate: {ber:.4f}",
        )
    else:
        ledger.record(
            evidence_id=f"EV_BER_{analysis.capture_id}",
            source="Arpit (Decoder)",
            check_name="reencode_ber_check",
            status=EvidenceStatus.UNAVAILABLE,
            explanation="Re-encode residual BER not available from decoder output",
        )

    # 8. Deterministic Ladder Level Computation
    # Elevate to L5 when CRC passes AND at least one independent corroborating
    # signal exists: sync word aligned, N5 rule/ML consensus, or zero-BER re-encode.
    _ta_crc_pass = decoder_output.crc_status == CrcStatus.PASS
    _ta_sync_aligned = decoder_output.sync_word is not None
    _ta_n5_agreed = n5_result.agreement
    _ta_ber_zero = (
        decoder_output.reencode_ber is not None
        and decoder_output.reencode_ber == 0.0
    )
    _ta_second_tool_agreed = _ta_crc_pass and (
        _ta_sync_aligned or _ta_n5_agreed or _ta_ber_zero
    )

    ladder_level, ladder_expl = compute_ladder_level(
        analysis=analysis,
        decoder_output=decoder_output,
        second_tool_agreed=_ta_second_tool_agreed,
    )
    ledger.record(
        evidence_id=f"EV_LADDER_{analysis.capture_id}",
        source="Archit (Evidence Ladder)",
        check_name="ladder_level_evaluation",
        status=EvidenceStatus.PASS,
        value=ladder_level.value,
        explanation=ladder_expl,
    )

    # 9. Hypothesis Engine Evaluation
    hypo_engine = HypothesisEngineV1()
    ranked_hypotheses = hypo_engine.run(
        analysis=analysis,
        classifier_output=classifier_output,
        decoder_output=decoder_output,
    )
    top_hypo = ranked_hypotheses[0]
    alternate_hypos = ranked_hypotheses[1:]

    # 10. N2 Defensible Confidence Computation
    from spectralq.confidence.engine import ConfidenceEngine
    from spectralq.confidence.abstention import AbstentionSystem

    conf_engine = ConfidenceEngine()
    conf_res = conf_engine.compute_confidence(
        prediction=n5_result.ml_prediction,
        ml_probability=n5_result.ml_probability,
        cross_window_agreement=1.0,
        rule_prediction=n5_result.rule_prediction,
        ml_prediction=n5_result.ml_prediction,
        rule_ml_agreement=n5_result.agreement,
        ledger=ledger,
        calibrated_ml_probability=classifier_output.calibrated_probability,
    )

    # 11. Phase 8 UNKNOWN Abstention System
    abstention_system = AbstentionSystem(threshold=abstention_threshold)
    abstention_decision = abstention_system.evaluate(
        analysis=analysis,
        confidence_result=conf_res,
        ledger=ledger,
        capture_id=analysis.capture_id,
    )

    stage_status["Decision Engine"] = "REAL" if analysis.source_mode == SourceMode.REAL else "LIVE"

    # Assemble Frozen ResultContract
    from datetime import datetime, timezone
    import hashlib

    input_hash = hashlib.sha256(str(analysis.capture_id).encode("utf-8")).hexdigest()
    now_utc = datetime.now(timezone.utc).isoformat()

    result_dict = {
        "schema_version": "1.0.0",
        "capture_id": analysis.capture_id,
        "source_mode": analysis.source_mode.value,
        "capability_available": True,
        "ladder_level": ladder_level.value,
        "top_hypothesis": {
            "modulation": top_hypo.modulation,
            "interleaver": top_hypo.interleaver,
            "fec": top_hypo.fec,
        },
        "alternate_hypotheses": [
            {
                "modulation": h.modulation,
                "interleaver": h.interleaver,
                "fec": h.fec,
                "prior_score": h.prior_score,
                "verification_score": h.verification_score,
                "total_score": h.final_rank_score,
                "status": str(h.status),
                "rejection_reason": h.rejection_reason,
            }
            for h in alternate_hypos[:5]
        ],
        "ml_prediction": classifier_output.ml_prediction,
        "ml_probability": classifier_output.ml_probabilities[classifier_output.ml_prediction],
        "calibrated_ml_probability": classifier_output.calibrated_probability,
        "rule_prediction": n5_result.rule_prediction,
        "rule_ml_agreement": n5_result.agreement,
        "rule_ml_penalty": n5_result.penalty,
        "cross_window_agreement": 1.0,
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

    result_contract = validate_result_dict(result_dict)
    return result_contract, stage_status
