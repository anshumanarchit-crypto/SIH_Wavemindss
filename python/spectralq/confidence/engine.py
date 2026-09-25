"""
N2 Computed Confidence Engine for SpectralQ.

Combines four independent probabilistic & physical evidentiary signals:
1. Calibrated ML Probability (or provisional raw ML probability until Phase 7)
2. Cross-Window Agreement (temporal stability across sub-windows)
3. Evidence Score strictly computed over verified checks: count(PASS) / (count(PASS) + count(FAIL))
4. Rule vs. ML Agreement / Penalty (learned consensus feature)

Invariants:
- NEVER uses a constant (e.g. 95.0% or 0.82).
- NEVER passes raw classifier probability straight through as final confidence.
- Weights are derived via Logistic Regression on held-out synthetic calibration instances,
  or explicitly flagged as manual_weights: True.
- If no evidence checks ran, evidence_score is 0.0 and no_verification_possible is set to True.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from spectralq.confidence.calibration import load_confidence_weights
from spectralq.contracts.schemas import EvidenceStatus
from spectralq.evidence.ledger import EvidenceLedger


CONFIDENCE_ENGINE_VERSION = "2.0.0-phase6-fitted"


@dataclass
class ConfidenceResult:
    prediction: str
    ml_probability: float
    calibrated_ml_probability: Optional[float]
    is_provisional_ml: bool
    cross_window_agreement: float
    evidence_score: float
    no_verification_possible: bool
    rule_prediction: str
    ml_prediction: str
    rule_ml_agreement: bool
    raw_hybrid_score: float
    final_confidence: float
    confidence_version: str
    weight_source: Literal["fitted", "manual"]
    weights_used: Dict[str, float]
    intercept: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction": self.prediction,
            "ml_probability": self.ml_probability,
            "calibrated_ml_probability": self.calibrated_ml_probability,
            "is_provisional_ml": self.is_provisional_ml,
            "cross_window_agreement": self.cross_window_agreement,
            "evidence_score": self.evidence_score,
            "no_verification_possible": self.no_verification_possible,
            "rule_prediction": self.rule_prediction,
            "ml_prediction": self.ml_prediction,
            "rule_ml_agreement": self.rule_ml_agreement,
            "raw_hybrid_score": self.raw_hybrid_score,
            "final_confidence": self.final_confidence,
            "confidence_version": self.confidence_version,
            "weight_source": self.weight_source,
            "weights_used": dict(self.weights_used),
            "intercept": self.intercept,
        }


class ConfidenceEngine:
    """
    Computes defensible multi-signal confidence for SpectralQ.
    """

    def __init__(
        self,
        weight_source: Literal["fitted", "manual"] = "fitted",
        custom_weights: Optional[Dict[str, float]] = None,
        custom_intercept: float = 0.0,
    ):
        self.weight_source = weight_source

        if weight_source == "fitted" and custom_weights is None:
            config = load_confidence_weights()
            self.weights = config["weights"]
            self.intercept = config["intercept"]
            self.version = f"fitted-{config.get('version', '1.0.0')}"
        elif weight_source == "manual" or custom_weights is not None:
            self.weight_source = "manual"
            self.weights = custom_weights or {
                "ml_probability": 0.35,
                "cross_window_agreement": 0.20,
                "evidence_score": 0.30,
                "rule_ml_agreement": 0.15,
            }
            self.intercept = custom_intercept
            self.version = "manual-weights-uncalibrated-v1.0"
        else:
            config = load_confidence_weights()
            self.weights = config["weights"]
            self.intercept = config["intercept"]
            self.version = CONFIDENCE_ENGINE_VERSION

    def compute_confidence(
        self,
        prediction: str,
        ml_probability: float,
        cross_window_agreement: float,
        rule_prediction: str,
        ml_prediction: str,
        rule_ml_agreement: bool,
        evidence_score: Optional[float] = None,
        ledger: Optional[EvidenceLedger] = None,
        calibrated_ml_probability: Optional[float] = None,
    ) -> ConfidenceResult:
        """
        Computes final confidence from the four input signals.
        """
        # 1. Determine ML probability (provisional until Phase 7)
        if calibrated_ml_probability is not None:
            eff_ml_prob = float(min(1.0, max(0.0, calibrated_ml_probability)))
            is_provisional = False
        else:
            eff_ml_prob = float(min(1.0, max(0.0, ml_probability)))
            is_provisional = True

        # 2. Determine evidence score and no_verification_possible flag
        if evidence_score is not None:
            eff_ev_score = float(min(1.0, max(0.0, evidence_score)))
            no_verification = False
        elif ledger is not None:
            eff_ev_score, no_verification = ledger.compute_evidence_ratio()
        else:
            eff_ev_score = 0.0
            no_verification = True

        # 3. Features for fusion
        x_ml = eff_ml_prob
        x_cw = float(min(1.0, max(0.0, cross_window_agreement)))
        x_ev = eff_ev_score
        x_agree = 1.0 if rule_ml_agreement else 0.0

        w_ml = self.weights.get("ml_probability", 3.0)
        w_cw = self.weights.get("cross_window_agreement", 2.0)
        w_ev = self.weights.get("evidence_score", 3.5)
        w_ag = self.weights.get("rule_ml_agreement", 1.8)

        # 4. Compute raw hybrid score
        if self.weight_source == "fitted":
            # Logistic regression log-odds: z = w^T x + b
            z = (w_ml * x_ml) + (w_cw * x_cw) + (w_ev * x_ev) + (w_ag * x_agree) + self.intercept
            # Sigmoid posterior probability
            raw_hybrid_score = 1.0 / (1.0 + math.exp(-z))
        else:
            # Normalized linear combination
            total_w = w_ml + w_cw + w_ev + w_ag
            if total_w > 0:
                raw_hybrid_score = ((w_ml * x_ml) + (w_cw * x_cw) + (w_ev * x_ev) + (w_ag * x_agree)) / total_w
            else:
                raw_hybrid_score = 0.0

        final_conf = float(min(1.0, max(0.0, raw_hybrid_score)))

        return ConfidenceResult(
            prediction=prediction,
            ml_probability=round(ml_probability, 4),
            calibrated_ml_probability=calibrated_ml_probability,
            is_provisional_ml=is_provisional,
            cross_window_agreement=round(x_cw, 4),
            evidence_score=round(x_ev, 4),
            no_verification_possible=no_verification,
            rule_prediction=rule_prediction,
            ml_prediction=ml_prediction,
            rule_ml_agreement=rule_ml_agreement,
            raw_hybrid_score=round(raw_hybrid_score, 4),
            final_confidence=round(final_conf, 4),
            confidence_version=self.version,
            weight_source=self.weight_source,
            weights_used=self.weights,
            intercept=self.intercept,
        )
