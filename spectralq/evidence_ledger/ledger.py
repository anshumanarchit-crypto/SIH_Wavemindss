"""
Evidence Ledger and Audit Trail Accumulator.
Captures and chronologically logs all intermediate evidentiary items, metric weights,
and domain interpretations for total pipeline transparency.
"""

from datetime import datetime, timezone
from typing import Any, List
from spectralq.contracts.schemas import EvidenceLedgerEntry


class EvidenceLedger:
    """
    Maintains a defensible audit trail of every piece of evidence contributing to the decision.
    """

    def __init__(self):
        self._entries: List[EvidenceLedgerEntry] = []

    def record(
        self,
        stage: str,
        source: str,
        metric_name: str,
        metric_value: Any,
        interpretation: str,
        weight: float = 1.0,
    ) -> None:
        """
        Appends an evidence item to the ledger.
        """
        entry = EvidenceLedgerEntry(
            stage=stage,
            source=source,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            metric_name=metric_name,
            metric_value=metric_value,
            interpretation=interpretation,
            weight=float(weight),
        )
        self._entries.append(entry)

    def get_entries(self) -> List[EvidenceLedgerEntry]:
        """
        Returns all recorded ledger entries.
        """
        return list(self._entries)

    def clear(self) -> None:
        """
        Clears ledger.
        """
        self._entries.clear()
