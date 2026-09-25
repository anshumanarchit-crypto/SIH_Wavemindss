"""
N5 Hybrid Modulation Identification & Consensus Fusion.

Combines independent opinions:
1. Statistical / physical Cumulant Decision Tree (Rule-based)
2. Machine Learning Classifier (RandomForest)

Invariants:
- agreement = (rule_prediction == ml_prediction)
- Both predictions are ALWAYS preserved in the output — never overwrite one with the other.
- Disagreement is recorded as an explicit evidence item with status CONFLICT.
- Documented penalty effect: Disagreement imposes an explicit penalty (0.25)
  tracked for consumption by Phase 6's confidence engine.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from spectralq.contracts.schemas import (
    ClassifierOutputContract,
    EvidenceItem,
    EvidenceStatus,
)
from spectralq.evidence.ledger import EvidenceLedger
from spectralq.integration.rule_classifier import RuleClassificationResult


# Documented confidence penalty weight applied when Rule and ML disagree
DISAGREEMENT_PENALTY_WEIGHT = 0.25


@dataclass
class N5FusionResult:
    rule_prediction: str
    ml_prediction: str
    ml_probability: float
    agreement: bool
    penalty: float
    evidence_item: EvidenceItem
    decision_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_prediction": self.rule_prediction,
            "ml_prediction": self.ml_prediction,
            "ml_probability": self.ml_probability,
            "agreement": self.agreement,
            "penalty": self.penalty,
            "evidence_item": self.evidence_item.model_dump(mode="json"),
            "decision_summary": self.decision_summary,
        }


def evaluate_n5_consensus(
    rule_result: RuleClassificationResult,
    ml_output: ClassifierOutputContract,
    capture_id: str = "CAPTURE",
    ledger: Optional[EvidenceLedger] = None,
    run_id: Optional[str] = None,
) -> N5FusionResult:
    """
    Evaluates agreement between Rule-based AMC and ML Classifier.
    Appends an explicit consensus evidence item to the ledger.
    """
    rule_pred = rule_result.predicted_class
    ml_pred = ml_output.ml_prediction
    top_ml_prob = ml_output.ml_probabilities.get(ml_pred, 0.0)

    agreement = (rule_pred == ml_pred)
    penalty = 0.0 if agreement else DISAGREEMENT_PENALTY_WEIGHT

    if agreement:
        status = EvidenceStatus.PASS
        explanation = (
            f"Consensus reached: Rule engine and ML classifier both identified {rule_pred} "
            f"(ML probability: {top_ml_prob:.4f}, agreement=True)"
        )
        failure_reason = None
        decision_summary = f"AGREEMENT: {rule_pred}"
    else:
        status = EvidenceStatus.CONFLICT
        explanation = (
            f"Consensus conflict: Rule engine identified {rule_pred} while ML classifier "
            f"predicted {ml_pred} (ML probability: {top_ml_prob:.4f}). "
            f"Documented confidence penalty of {DISAGREEMENT_PENALTY_WEIGHT:.2f} recorded."
        )
        failure_reason = f"Classification disagreement: rule={rule_pred} vs ml={ml_pred}"
        decision_summary = f"CONFLICT: Rule={rule_pred}, ML={ml_pred}"

    evidence_item = EvidenceItem(
        evidence_id=f"EV_N5_{capture_id}",
        hypothesis_id=f"HYP_{ml_pred}",
        source="N5_Hybrid_Consensus",
        check_name="rule_ml_agreement",
        status=status,
        value=agreement,
        numeric_value=1.0 if agreement else 0.0,
        normalized_value=1.0 if agreement else 0.0,
        threshold=1.0,
        provenance={
            "rule_prediction": rule_pred,
            "ml_prediction": ml_pred,
            "rule_config_version": rule_result.config_version,
            "ml_model_version": ml_output.model_version,
            "penalty_applied": penalty,
            "rule_decision_path": rule_result.decision_path,
        },
        run_id=run_id,
        explanation=explanation,
        failure_reason=failure_reason,
    )

    if ledger is not None:
        ledger.record(
            evidence_id=evidence_item.evidence_id,
            hypothesis_id=evidence_item.hypothesis_id,
            source=evidence_item.source,
            check_name=evidence_item.check_name,
            status=evidence_item.status,
            value=evidence_item.value,
            numeric_value=evidence_item.numeric_value,
            normalized_value=evidence_item.normalized_value,
            threshold=evidence_item.threshold,
            provenance=evidence_item.provenance,
            explanation=evidence_item.explanation,
            failure_reason=evidence_item.failure_reason,
        )

    return N5FusionResult(
        rule_prediction=rule_pred,
        ml_prediction=ml_pred,
        ml_probability=top_ml_prob,
        agreement=agreement,
        penalty=penalty,
        evidence_item=evidence_item,
        decision_summary=decision_summary,
    )
