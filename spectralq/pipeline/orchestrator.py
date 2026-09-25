"""
SpectralQ Pipeline Orchestrator.
Coordinates the end-to-end evidence-first decision flow:
  AnalysisContract (DSP Features)
    -> Rule Classifier & ML Classifier (Stage 5)
    -> N5 Agreement Check
    -> Hypothesis Engine (Modulation x Interleaver x FEC)
    -> Decoder Verification Evidence (Arpit)
    -> Deterministic Ladder Level (L1 - L5)
    -> Confidence Fusion & Calibration (N2)
    -> Decision Label / UNKNOWN Fallback
    -> ResultContract (result.json)
"""

from typing import Any, Dict, Optional
import time

from spectralq.contracts.schemas import (
    AnalysisContract,
    ClassifierOutputContract,
    DecoderVerificationContract,
    ResultContract,
    LadderLevel,
)
from spectralq.n5_hybrid.rule_engine import RuleBasedClassifier
from spectralq.n5_hybrid.classifier_adapter import ClassifierAdapter
from spectralq.n5_hybrid.agreement import evaluate_n5_agreement
from spectralq.hypothesis_engine.search import HypothesisEngine
from spectralq.evidence_ledger.ladder import compute_ladder_level
from spectralq.evidence_ledger.confidence_fusion import (
    ConfidenceFusionEngine,
    evaluate_cross_window_agreement,
)
from spectralq.evidence_ledger.calibration import ConfidenceCalibrator
from spectralq.evidence_ledger.thresholds import evaluate_decision_label
from spectralq.evidence_ledger.ledger import EvidenceLedger


class SpectralQOrchestrator:
    """
    Primary integration and decision engine for SpectralQ.
    """

    def __init__(
        self,
        classifier_model_path: Optional[str] = None,
        confidence_threshold: float = 0.60,
        seed: int = 42,
    ):
        self.seed = seed
        self.confidence_threshold = confidence_threshold
        self.rule_engine = RuleBasedClassifier()
        self.classifier_adapter = ClassifierAdapter(model_path=classifier_model_path, seed=seed)
        self.hypothesis_engine = HypothesisEngine()
        self.fusion_engine = ConfidenceFusionEngine()
        self.calibrator = ConfidenceCalibrator()

    def process(
        self,
        analysis: AnalysisContract,
        decoder_output: Optional[DecoderVerificationContract] = None,
        custom_classifier_output: Optional[ClassifierOutputContract] = None,
    ) -> ResultContract:
        """
        Processes upstream signal analysis and produces a defensible ResultContract.
        """
        start_time = time.perf_counter()
        ledger = EvidenceLedger()

        # 1. Record Ingest Evidence
        ledger.record(
            stage="Ingest_and_Forensics",
            source="Sinchana (Stage 1-4)",
            metric_name="burst_detected",
            metric_value=analysis.is_valid_burst,
            interpretation="Signal burst detection confirmation",
            weight=1.0,
        )
        ledger.record(
            stage="Feature_Extraction",
            source="Sinchana (Stage 4)",
            metric_name="snr_m2m4_db",
            metric_value=analysis.snr_m2m4_db,
            interpretation=f"Estimated signal-to-noise ratio: {analysis.snr_m2m4_db:.2f} dB",
            weight=1.0,
        )
        ledger.record(
            stage="Feature_Extraction",
            source="Sinchana (Stage 4)",
            metric_name="cumulants",
            metric_value={
                "C20": analysis.cumulants.C20,
                "C40": analysis.cumulants.C40,
                "C42": analysis.cumulants.C42,
            },
            interpretation="Higher-order cumulant statistical signatures",
            weight=1.2,
        )

        # 2. Execute Independent Rule-Based Classifier
        rule_pred, rule_score, rule_scores_dict = self.rule_engine.classify(analysis)
        ledger.record(
            stage="N5_Rule_Path",
            source="Archit (Rule Engine)",
            metric_name="rule_prediction",
            metric_value={"predicted": rule_pred, "score": rule_score},
            interpretation=f"Analytic cumulant & cluster rules favor {rule_pred} (score {rule_score:.3f})",
            weight=1.0,
        )

        # 3. Execute ML Classifier (Harsh / Baseline Adapter)
        if custom_classifier_output is not None:
            classifier_out = custom_classifier_output
        else:
            classifier_out = self.classifier_adapter.predict(analysis)

        ml_pred = classifier_out.predicted_class
        ml_prob = classifier_out.class_probabilities.get(ml_pred, 0.0)
        ml_calibrated_prob = self.calibrator.calibrate(ml_prob)

        ledger.record(
            stage="N5_ML_Path",
            source="Harsh (Stage 5 Classifier)",
            metric_name="ml_prediction",
            metric_value={"predicted": ml_pred, "raw_prob": ml_prob, "calibrated_prob": ml_calibrated_prob},
            interpretation=f"RandomForest classifier predicts {ml_pred} (calibrated prob {ml_calibrated_prob:.3f})",
            weight=1.0,
        )

        # 4. Evaluate N5 Agreement
        n5_agreed, n5_score, n5_details = evaluate_n5_agreement(
            rule_pred=rule_pred,
            rule_score=rule_score,
            ml_pred=ml_pred,
            ml_prob=ml_calibrated_prob,
            rule_scores_dict=rule_scores_dict,
            ml_probs_dict=classifier_out.class_probabilities,
        )
        ledger.record(
            stage="N5_Agreement",
            source="Archit (N5 Consensus)",
            metric_name="n5_agreement",
            metric_value=n5_details,
            interpretation=(
                f"Consensus reached on {rule_pred}"
                if n5_agreed
                else f"Conflict detected: Rule({rule_pred}) vs ML({ml_pred}). Final confidence penalized."
            ),
            weight=1.5,
        )

        # 5. Evaluate Cross-Window Consistency
        cross_window_score = evaluate_cross_window_agreement(analysis.sub_windows)
        ledger.record(
            stage="Cross_Window_Evaluation",
            source="Archit (Sub-Window Tracker)",
            metric_name="cross_window_agreement_score",
            metric_value=cross_window_score,
            interpretation=f"Feature temporal stability score: {cross_window_score:.3f}",
            weight=1.0,
        )

        # 6. Execute Hypothesis Engine
        candidates = self.hypothesis_engine.evaluate_hypotheses(
            analysis=analysis,
            rule_scores=rule_scores_dict,
            classifier_output=classifier_out,
            decoder_output=decoder_output,
        )
        top_cand = candidates[0] if candidates else None

        # 7. Record Verification Evidence
        verif_evidence_score = top_cand.verification_score if top_cand else 0.10
        if decoder_output:
            ledger.record(
                stage="Decoder_Verification",
                source="Arpit (Stage 6/9 Demod & FEC)",
                metric_name="verification_status",
                metric_value={
                    "sync_detected": decoder_output.sync_detected,
                    "sync_confidence": decoder_output.sync_confidence,
                    "crc_valid": decoder_output.crc_valid,
                    "reencode_ber": decoder_output.reencode_ber,
                    "status": decoder_output.status.value,
                },
                interpretation=f"Physical frame verification status: {decoder_output.status.value}",
                weight=1.5,
            )

        # 8. Compute Deterministic Ladder Level (L1 - L5)
        ladder_level, ladder_explanation = compute_ladder_level(
            analysis=analysis,
            decoder_output=decoder_output,
            n5_agreement=n5_agreed,
            cross_window_agreement_score=cross_window_score,
        )
        ledger.record(
            stage="Ladder_Level_Evaluation",
            source="Archit (Evidence Ladder)",
            metric_name="ladder_level",
            metric_value=ladder_level.value,
            interpretation=ladder_explanation,
            weight=1.5,
        )

        # 9. Compute N2 Calibrated Confidence Fusion
        fused_confidence, fusion_breakdown = self.fusion_engine.compute_confidence(
            ml_calibrated_prob=ml_calibrated_prob,
            n5_agreement_score=n5_score,
            cross_window_agreement_score=cross_window_score,
            verification_evidence_score=verif_evidence_score,
            evm=analysis.evm,
            snr_db=analysis.snr_m2m4_db,
        )
        ledger.record(
            stage="Confidence_Fusion",
            source="Archit (N2 Logistic Model)",
            metric_name="fused_confidence_breakdown",
            metric_value=fusion_breakdown,
            interpretation=f"Multi-evidence fused confidence computed as {fused_confidence:.4f}",
            weight=2.0,
        )

        # 10. Evaluate Final Decision Label vs UNKNOWN
        top_mod = top_cand.modulation if top_cand else None
        decision_label, unknown_reason = evaluate_decision_label(
            top_modulation=top_mod,
            fused_confidence=fused_confidence,
            ladder_level=ladder_level,
            n5_agreement=n5_agreed,
            n5_agreement_score=n5_score,
            cross_window_score=cross_window_score,
            snr_db=analysis.snr_m2m4_db,
            is_valid_burst=analysis.is_valid_burst,
            threshold=self.confidence_threshold,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # 11. Compile Result Contract
        return ResultContract(
            capture_id=analysis.capture_id,
            provenance=analysis.provenance,
            ladder_level=ladder_level,
            decision_label=decision_label,
            final_confidence=round(fused_confidence, 4),
            is_calibrated=True,
            unknown_reason=unknown_reason,
            rule_prediction=rule_pred,
            rule_score=round(rule_score, 4),
            ml_prediction=ml_pred,
            ml_calibrated_prob=round(ml_calibrated_prob, 4),
            n5_agreement=n5_agreed,
            n5_agreement_score=round(n5_score, 4),
            cross_window_agreement_score=round(cross_window_score, 4),
            verification_evidence_score=round(verif_evidence_score, 4),
            top_hypothesis=top_cand,
            candidates=candidates,
            evidence_ledger=ledger.get_entries(),
            diagnostics={
                "processing_time_ms": round(elapsed_ms, 2),
                "fusion_logit": fusion_breakdown["logit_z"],
                "seed": self.seed,
            },
        )
