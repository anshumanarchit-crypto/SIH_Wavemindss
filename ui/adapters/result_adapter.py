"""
UI Result Adapter.
Converts backend ResultContract into normalized UI view models.
Strictly read-only; performs zero confidence or classification mathematics.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from spectralq.contracts.schemas import ResultContract, validate_result_dict


class ContractValidationError(Exception):
    """Raised when backend result fails contract schema validation."""
    pass


@dataclass
class NormalizedHypothesis:
    modulation: str
    interleaver: str
    fec: str
    prior_score: Optional[float] = None
    verification_score: Optional[float] = None
    total_score: Optional[float] = None
    status: str = "CONFIRMED"
    rejection_reason: Optional[str] = None


@dataclass
class NormalizedEvidence:
    evidence_id: str
    source: str
    check_name: str
    status: str  # "PASS", "FAIL", "NOT_RUN", "UNAVAILABLE", "CONFLICT"
    explanation: str
    value: Any = None
    numeric_value: Optional[float] = None
    normalized_value: Optional[float] = None
    threshold: Optional[float] = None
    failure_reason: Optional[str] = None
    hypothesis_id: Optional[str] = None


@dataclass
class NormalizedResult:
    schema_version: str
    capture_id: str
    source_mode: str
    is_replay: bool
    ladder_level: str
    top_hypothesis: NormalizedHypothesis
    alternate_hypotheses: List[NormalizedHypothesis]
    ml_prediction: str
    ml_probability: float
    calibrated_ml_probability: Optional[float]
    rule_prediction: str
    rule_ml_agreement: bool
    rule_ml_penalty: float
    cross_window_agreement: float
    evidence: List[NormalizedEvidence]
    failed_checks: List[str]
    unavailable_checks: List[str]
    final_confidence: float
    confidence_version: str
    is_unknown: bool
    unknown_reason: Optional[str]
    input_hash: str
    seed: int
    software_version: str
    generated_at: str
    capability_available: Optional[bool]
    raw_dict: Dict[str, Any] = field(default_factory=dict)

    @property
    def confidence_label(self) -> str:
        """Display label for confidence without altering backend value."""
        if self.is_unknown:
            return "UNKNOWN"
        if self.final_confidence >= 0.90:
            return "CONFIRMED"
        if self.final_confidence >= 0.80:
            return "HIGH CONFIDENCE"
        return "LOW CONFIDENCE"


def adapt_result(raw_data: Any) -> NormalizedResult:
    """
    Validates and adapts a backend result dict or ResultContract into NormalizedResult.
    Raises ContractValidationError if contract requirements are violated.
    """
    if isinstance(raw_data, ResultContract):
        contract = raw_data
        raw_dict = contract.model_dump()
    elif isinstance(raw_data, dict):
        try:
            contract = validate_result_dict(raw_data)
            raw_dict = raw_data
        except Exception as e:
            raise ContractValidationError(f"Invalid ResultContract schema: {e}") from e
    else:
        raise ContractValidationError(f"Expected dict or ResultContract, got {type(raw_data)}")

    # Extract top hypothesis
    top_hyp = NormalizedHypothesis(
        modulation=contract.top_hypothesis.modulation,
        interleaver=contract.top_hypothesis.interleaver,
        fec=contract.top_hypothesis.fec,
        status="CONFIRMED",
    )

    # Extract alternates
    alternates = [
        NormalizedHypothesis(
            modulation=alt.modulation,
            interleaver=alt.interleaver,
            fec=alt.fec,
            prior_score=alt.prior_score,
            verification_score=alt.verification_score,
            total_score=alt.total_score,
            status=alt.status,
            rejection_reason=alt.rejection_reason,
        )
        for alt in contract.alternate_hypotheses
    ]

    # Extract evidence items
    evidence_items = [
        NormalizedEvidence(
            evidence_id=ev.evidence_id,
            source=ev.source,
            check_name=ev.check_name,
            status=ev.status.value,
            explanation=ev.explanation,
            value=ev.value,
            numeric_value=ev.numeric_value,
            normalized_value=ev.normalized_value,
            threshold=ev.threshold,
            failure_reason=ev.failure_reason,
            hypothesis_id=ev.hypothesis_id,
        )
        for ev in contract.evidence
    ]

    is_replay = contract.source_mode.value.lower() == "replay"

    return NormalizedResult(
        schema_version=contract.schema_version,
        capture_id=contract.capture_id,
        source_mode=contract.source_mode.value.upper(),
        is_replay=is_replay,
        ladder_level=contract.ladder_level.value,
        top_hypothesis=top_hyp,
        alternate_hypotheses=alternates,
        ml_prediction=contract.ml_prediction,
        ml_probability=contract.ml_probability,
        calibrated_ml_probability=contract.calibrated_ml_probability,
        rule_prediction=contract.rule_prediction,
        rule_ml_agreement=contract.rule_ml_agreement,
        rule_ml_penalty=contract.rule_ml_penalty,
        cross_window_agreement=contract.cross_window_agreement,
        evidence=evidence_items,
        failed_checks=list(contract.failed_checks),
        unavailable_checks=list(contract.unavailable_checks),
        final_confidence=contract.final_confidence,
        confidence_version=contract.confidence_version,
        is_unknown=contract.unknown,
        unknown_reason=contract.unknown_reason,
        input_hash=contract.provenance.input_hash,
        seed=contract.provenance.seed,
        software_version=contract.provenance.software_version,
        generated_at=contract.provenance.generated_at,
        capability_available=contract.capability_available,
        raw_dict=raw_dict,
    )
