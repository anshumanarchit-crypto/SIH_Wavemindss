"""
UNKNOWN Abstention System for SpectralQ.

Core Rules:
1. If final_confidence is below a validated operational threshold, return UNKNOWN
   with a preserved, transparent unknown_reason.
2. NEVER return a low-confidence best guess labeled as if it were a real answer.
3. G10 Noise-Only Guard: Pure noise captures MUST return UNKNOWN every time.
   Even if the raw classifier produces a strong guess on noise, the evidence guard
   strictly overrides it to UNKNOWN and logs the override explicitly in the EvidenceLedger.
4. G7 Low-SNR Physical Floor Guard: Integrates with MODULATION_MIN_SNR from registry.py.
   If SNR is below the modulation's physical threshold, abstains to UNKNOWN.
5. All intermediate stage outputs (raw_ml_probability, calibrated_ml_probability,
   raw_hybrid_score, final_confidence) are strictly preserved for inspection.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from spectralq.confidence.engine import ConfidenceResult
from spectralq.confidence.threshold_sweep import load_abstention_config
from spectralq.contracts.schemas import (
    AnalysisContract,
    EvidenceItem,
    EvidenceStatus,
    CrcStatus,
    DecoderStatus,
)
from spectralq.evidence.ledger import EvidenceLedger
from spectralq.hypothesis.registry import MODULATION_MIN_SNR


DEFAULT_ABSTENTION_THRESHOLD = 0.80


@dataclass
class AbstentionDecision:
    is_unknown: bool
    unknown_reason: Optional[str]
    output_label: str
    final_confidence: float
    threshold: float
    guard_triggered: Optional[str]
    raw_ml_probability: float
    calibrated_ml_probability: Optional[float]
    raw_hybrid_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_unknown": self.is_unknown,
            "unknown_reason": self.unknown_reason,
            "output_label": self.output_label,
            "final_confidence": self.final_confidence,
            "threshold": self.threshold,
            "guard_triggered": self.guard_triggered,
            "raw_ml_probability": self.raw_ml_probability,
            "calibrated_ml_probability": self.calibrated_ml_probability,
            "raw_hybrid_score": self.raw_hybrid_score,
        }


class AbstentionSystem:
    """
    Evaluates multi-tiered abstention guards to prevent false-acceptances.
    """

    def __init__(self, threshold: Optional[float] = None):
        if threshold is not None:
            self.threshold = threshold
        else:
            config = load_abstention_config()
            self.threshold = float(config.get("selected_threshold", DEFAULT_ABSTENTION_THRESHOLD))

    def evaluate(
        self,
        analysis: AnalysisContract,
        confidence_result: ConfidenceResult,
        ledger: Optional[EvidenceLedger] = None,
        capture_id: str = "CAPTURE",
        decoder_output: Optional[Any] = None,
        hypothesis_gap: Optional[float] = None,
        top_candidate: Optional[Any] = None,
    ) -> AbstentionDecision:
        """
        Executes abstention evaluation against noise, low SNR physical floors,
        unverified demodulation quality, and empirical confidence thresholds.
        """
        top_pred = getattr(top_candidate, "modulation", None) or confidence_result.prediction
        snr = float(analysis.estimates.snr.value)
        final_conf = confidence_result.final_confidence
        raw_ml_p = confidence_result.ml_probability
        cal_ml_p = confidence_result.calibrated_ml_probability
        raw_hybrid = confidence_result.raw_hybrid_score

        # ---------------------------------------------------------------------
        # Tier 1: G10 Noise-Only Guard
        # ---------------------------------------------------------------------
        # If signal power is negligible, SNR is at or below noise floor,
        # or bursts are absent, input is pure noise.
        # However, if actual receiver physical verification succeeded (e.g. valid LDPC/FEC with zero syndrome errors),
        # it is provably a valid communication transmission operating near or below 0 dB.
        decoder_verified = (
            decoder_output is not None
            and getattr(decoder_output, "status", None) == DecoderStatus.OK
            and getattr(decoder_output, "reencode_ber", None) is not None
            and getattr(decoder_output, "reencode_ber", 1.0) <= 0.05
        )
        is_noise = (not decoder_verified) and (
            (snr <= 0.0) or (len(analysis.bursts) == 0) or (analysis.features.cluster.silhouette < 0.15 and snr < 3.0)
        )

        if is_noise:
            reason = (
                f"Noise-only capture detected: estimated SNR ({snr:.1f} dB) is at or below "
                f"physical detection floor (0.0 dB); classifier prediction '{top_pred}' "
                f"(raw_p={raw_ml_p:.4f}) overridden to UNKNOWN"
            )
            if ledger is not None:
                ledger.record(
                    evidence_id=f"EV_NOISE_OVERRIDE_{capture_id}",
                    source="Abstention_Guard",
                    check_name="noise_floor_override",
                    status=EvidenceStatus.FAIL,
                    value=snr,
                    numeric_value=snr,
                    threshold=0.0,
                    explanation=reason,
                    failure_reason="Noise floor violation",
                    provenance={
                        "raw_ml_prediction": top_pred,
                        "raw_ml_probability": raw_ml_p,
                        "guard": "noise_floor_override",
                    },
                )
            return AbstentionDecision(
                is_unknown=True,
                unknown_reason=reason,
                output_label="UNKNOWN",
                final_confidence=0.0,
                threshold=self.threshold,
                guard_triggered="noise_floor_override",
                raw_ml_probability=raw_ml_p,
                calibrated_ml_probability=cal_ml_p,
                raw_hybrid_score=raw_hybrid,
            )

        # ---------------------------------------------------------------------
        # Tier 2: Physical Modulation SNR Floor Guard (Integrated with Registry)
        # ---------------------------------------------------------------------
        min_snr = MODULATION_MIN_SNR.get(top_pred, 0.0)
        if snr < min_snr:
            reason = (
                f"Physical SNR floor violation: estimated SNR ({snr:.1f} dB) is below "
                f"minimum physical operational floor for {top_pred} ({min_snr:.1f} dB); "
                f"abstaining to UNKNOWN to prevent near-threshold false acceptance"
            )
            if ledger is not None:
                ledger.record(
                    evidence_id=f"EV_SNR_GUARD_{capture_id}",
                    source="Abstention_Guard",
                    check_name="snr_floor_guard",
                    status=EvidenceStatus.FAIL,
                    value=snr,
                    numeric_value=snr,
                    threshold=min_snr,
                    explanation=reason,
                    failure_reason=f"SNR ({snr:.1f} dB) < operational limit ({min_snr:.1f} dB)",
                    provenance={"target_modulation": top_pred, "guard": "snr_floor_guard"},
                )
            return AbstentionDecision(
                is_unknown=True,
                unknown_reason=reason,
                output_label="UNKNOWN",
                final_confidence=final_conf,
                threshold=self.threshold,
                guard_triggered="snr_floor_guard",
                raw_ml_probability=raw_ml_p,
                calibrated_ml_probability=cal_ml_p,
                raw_hybrid_score=raw_hybrid,
            )

        # ---------------------------------------------------------------------
        # Tier 2.5: Demodulation Quality & Unverified Stream Guard (General G9/Adversarial Policy)
        # ---------------------------------------------------------------------
        if decoder_output is not None:
            evm = getattr(decoder_output, "evm_percent", None)
            crc_stat = getattr(decoder_output, "crc_status", None)
            sync_w = getattr(decoder_output, "sync_word", None)
            reenc_ber = getattr(decoder_output, "reencode_ber", None)

            crc_pass = (crc_stat == CrcStatus.PASS) or (str(crc_stat).lower() == "pass")
            is_unpacketized = (not crc_pass) and (sync_w is None) and (reenc_ber is None or reenc_ber > 0.05)

            if evm is not None and evm > 40.0 and is_unpacketized:
                reason = (
                    f"Demodulation quality failure: recovered constellation EVM ({evm:.1f}%) "
                    f"exceeds physical tolerance threshold (40.0%) on an unpacketized headerless "
                    f"stream without CRC or FEC confirmation; abstaining to UNKNOWN"
                )
                if ledger is not None:
                    ledger.record(
                        evidence_id=f"EV_DEMOD_GUARD_{capture_id}",
                        source="Abstention_Guard",
                        check_name="demod_quality_guard",
                        status=EvidenceStatus.FAIL,
                        numeric_value=evm,
                        threshold=40.0,
                        explanation=reason,
                        failure_reason=f"EVM ({evm:.1f}%) > threshold (40.0%) with unverified stream",
                        provenance={"guard": "demod_quality_guard", "evm_percent": evm},
                    )
                return AbstentionDecision(
                    is_unknown=True,
                    unknown_reason=reason,
                    output_label="UNKNOWN",
                    final_confidence=float(min(final_conf, 0.40)),
                    threshold=self.threshold,
                    guard_triggered="demod_quality_guard",
                    raw_ml_probability=raw_ml_p,
                    calibrated_ml_probability=cal_ml_p,
                    raw_hybrid_score=raw_hybrid,
                )

        # ---------------------------------------------------------------------
        # Tier 3: Empirical Confidence Threshold Abstention Guard
        # ---------------------------------------------------------------------
        if final_conf < self.threshold:
            reason = (
                f"Low confidence abstention: final_confidence ({final_conf:.4f}) is below "
                f"validated operational threshold ({self.threshold:.4f}); "
                f"never returning low-confidence guess as factual answer"
            )
            if ledger is not None:
                ledger.record(
                    evidence_id=f"EV_CONF_GUARD_{capture_id}",
                    source="Abstention_Guard",
                    check_name="confidence_threshold_guard",
                    status=EvidenceStatus.FAIL,
                    value=final_conf,
                    numeric_value=final_conf,
                    threshold=self.threshold,
                    explanation=reason,
                    failure_reason=f"Confidence {final_conf:.4f} < threshold {self.threshold:.4f}",
                    provenance={"guard": "confidence_threshold_guard"},
                )
            return AbstentionDecision(
                is_unknown=True,
                unknown_reason=reason,
                output_label="UNKNOWN",
                final_confidence=final_conf,
                threshold=self.threshold,
                guard_triggered="confidence_threshold_guard",
                raw_ml_probability=raw_ml_p,
                calibrated_ml_probability=cal_ml_p,
                raw_hybrid_score=raw_hybrid,
            )

        # ---------------------------------------------------------------------
        # Clean Confident Pass
        # ---------------------------------------------------------------------
        if ledger is not None:
            ledger.record(
                evidence_id=f"EV_CONF_PASS_{capture_id}",
                source="Abstention_Guard",
                check_name="confidence_threshold_guard",
                status=EvidenceStatus.PASS,
                value=final_conf,
                numeric_value=final_conf,
                threshold=self.threshold,
                explanation=(
                    f"Confidence check passed: final_confidence ({final_conf:.4f}) >= "
                    f"operational threshold ({self.threshold:.4f})"
                ),
                provenance={"guard": "confidence_threshold_guard"},
            )

        return AbstentionDecision(
            is_unknown=False,
            unknown_reason=None,
            output_label=top_pred,
            final_confidence=final_conf,
            threshold=self.threshold,
            guard_triggered=None,
            raw_ml_probability=raw_ml_p,
            calibrated_ml_probability=cal_ml_p,
            raw_hybrid_score=raw_hybrid,
        )
