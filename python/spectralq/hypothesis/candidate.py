"""
Hypothesis Candidate Data Structure.
Persists modulation, interleaver, fec, status, evidence list, failed checks,
unsupported components, and final rank score.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from spectralq.contracts.schemas import EvidenceItem, EvidenceStatus


class HypothesisCandidate(BaseModel):
    """
    Represents a specific hypothesis tuple (Modulation x Interleaver x FEC)
    with physical verification evidence, failure diagnostics, and deterministic rank score.
    """
    model_config = ConfigDict(extra="forbid")

    modulation: str = Field(..., description="Hypothesized modulation scheme")
    interleaver: str = Field(..., description="Hypothesized interleaver scheme")
    fec: str = Field(..., description="Hypothesized FEC scheme")
    status: str = Field(..., description="Candidate status: EVALUATED, PRUNED, or UNSUPPORTED")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="All individual evidence check records")
    failed_checks: List[str] = Field(default_factory=list, description="Names of checks that evaluated to FAIL")
    unsupported_components: List[str] = Field(default_factory=list, description="List of unsupported component identifiers")
    prior_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Upstream plausibility / classifier prior")
    verification_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Physical verification score from decoder")
    final_rank_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Deterministic rank score (ranking only, NOT a confidence)")
    rejection_reason: Optional[str] = Field(default=None, description="Explicit reason if pruned or unsupported")

    def add_evidence(
        self,
        evidence_id: str,
        source: str,
        check_name: str,
        status: EvidenceStatus,
        value: Any,
        explanation: str,
    ) -> None:
        """Appends an evidence check item and tracks failure if status == FAIL."""
        item = EvidenceItem(
            evidence_id=evidence_id,
            source=source,
            check_name=check_name,
            status=status,
            value=value,
            explanation=explanation,
        )
        self.evidence.append(item)
        if status == EvidenceStatus.FAIL and check_name not in self.failed_checks:
            self.failed_checks.append(check_name)
