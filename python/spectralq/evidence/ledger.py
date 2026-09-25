"""
Evidence Ledger Abstraction for SpectralQ.

Tracks itemized evidentiary records across all pipeline stages:
- Sinchana's analysis output (bursts, SNR, bandwidth, baud, CFO)
- ML classifier (probabilities, top class)
- Rule-based classifier (cumulants, cluster count)
- Cross-window agreement (temporal stability)
- Sync/pattern matching (preamble correlator)
- CRC/checksum (syndrome verification)
- Re-encode/BER comparison (residual error)
- Phase-ambiguity resolver (constellation rotation invariance)
- Decoder result (payload extraction)
- Hypothesis engine ranking (top hypothesis and alternate ranks)

Invariants:
- Statuses supported: PASS, FAIL, NOT_RUN, UNAVAILABLE, CONFLICT.
- Unsupported or NOT_RUN evidence must NEVER silently become a positive score.
"""

from typing import Any, Dict, List, Optional
from spectralq.contracts.schemas import EvidenceItem, EvidenceStatus


class EvidenceLedger:
    """
    Chronological and queryable audit ledger storing individual evidence items.
    """

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self._items: List[EvidenceItem] = []

    def record(
        self,
        evidence_id: str,
        source: str,
        check_name: str,
        status: EvidenceStatus,
        explanation: str,
        hypothesis_id: Optional[str] = None,
        value: Any = None,
        numeric_value: Optional[float] = None,
        normalized_value: Optional[float] = None,
        threshold: Optional[float] = None,
        provenance: Optional[Dict[str, Any]] = None,
        failure_reason: Optional[str] = None,
    ) -> EvidenceItem:
        """
        Appends an evidence item to the ledger.
        """
        # If failure occurred, ensure failure_reason is documented
        if status in [EvidenceStatus.FAIL, EvidenceStatus.CONFLICT] and not failure_reason:
            failure_reason = explanation

        item = EvidenceItem(
            evidence_id=evidence_id,
            hypothesis_id=hypothesis_id,
            source=source,
            check_name=check_name,
            status=status,
            value=value,
            numeric_value=numeric_value,
            normalized_value=normalized_value,
            threshold=threshold,
            provenance=provenance,
            run_id=self.run_id,
            explanation=explanation,
            failure_reason=failure_reason,
        )
        self._items.append(item)
        return item

    def get_items(self) -> List[EvidenceItem]:
        """Returns all evidence items."""
        return list(self._items)

    def get_failed_checks(self) -> List[str]:
        """Returns list of check names that evaluated to FAIL."""
        return [item.check_name for item in self._items if item.status == EvidenceStatus.FAIL]

    def get_unavailable_checks(self) -> List[str]:
        """Returns list of check names that were UNAVAILABLE."""
        return [item.check_name for item in self._items if item.status == EvidenceStatus.UNAVAILABLE]

    def get_conflicts(self) -> List[EvidenceItem]:
        """Returns all evidence items with CONFLICT status."""
        return [item for item in self._items if item.status == EvidenceStatus.CONFLICT]

    def calculate_evidence_score(self) -> float:
        """
        Computes a physical evidence verification aggregate score in [0.0, 1.0].
        
        CRITICAL ARCHITECTURAL INVARIANT:
        Unsupported, UNAVAILABLE, NOT_RUN, or FAIL items must NEVER contribute positively
        to the score. Only genuine PASS evidence can produce a positive contribution.
        """
        if not self._items:
            return 0.0

        pass_points = 0.0
        total_evaluable_checks = 0

        for item in self._items:
            # NOT_RUN and UNAVAILABLE contribute exactly 0.0 positive points
            if item.status in [EvidenceStatus.NOT_RUN, EvidenceStatus.UNAVAILABLE]:
                continue

            total_evaluable_checks += 1

            if item.status == EvidenceStatus.PASS:
                # Add normalized value if present, else 1.0 point
                pts = item.normalized_value if item.normalized_value is not None else 1.0
                pass_points += max(0.0, pts)
            elif item.status in [EvidenceStatus.FAIL, EvidenceStatus.CONFLICT]:
                # Failure or conflict contributes 0 positive score
                pass_points += 0.0

        if total_evaluable_checks == 0:
            return 0.0

        return float(min(1.0, max(0.0, pass_points / float(total_evaluable_checks))))

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Serializes all ledger items to a list of dicts."""
        return [item.model_dump(mode="json") for item in self._items]

    @classmethod
    def from_dict_list(cls, data: List[Dict[str, Any]], run_id: Optional[str] = None) -> "EvidenceLedger":
        """Deserializes a list of dicts into an EvidenceLedger instance."""
        ledger = cls(run_id=run_id)
        for d in data:
            item = EvidenceItem.model_validate(d)
            ledger._items.append(item)
        return ledger
