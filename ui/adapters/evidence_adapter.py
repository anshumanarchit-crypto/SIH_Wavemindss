"""
UI Evidence Adapter.
Categorizes and formats Evidence Ledger items for clear human/judge presentation.
Preserves the exact evidence chain and NEVER fabricates passes or numeric values.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from ui.adapters.result_adapter import NormalizedEvidence, NormalizedResult


@dataclass
class EvidenceSummary:
    total_checks: int
    passed_count: int
    failed_count: int
    unavailable_count: int
    not_run_count: int
    conflict_count: int
    categories: Dict[str, List[NormalizedEvidence]]
    contradictions: List[str]
    warnings: List[str]


def categorize_evidence_item(item: NormalizedEvidence) -> str:
    """Categorizes an evidence item based on source and check_name."""
    src = item.source.lower()
    chk = item.check_name.lower()

    if "ingest" in src or "burst" in chk:
        return "1. Ingest & Burst Forensics"
    elif "estimation" in src or "parameter" in chk or "snr" in chk or "baud" in chk:
        return "2. Blind DSP Estimation"
    elif "classifier" in src or "ml" in chk or "feature" in src:
        return "3. Modulation Features & Classifier"
    elif "rule" in src or "consensus" in src or "n5" in src or "agreement" in chk:
        return "4. AMC & Consensus Validation"
    elif "decoder" in src or "crc" in chk or "ber" in chk:
        return "5. Demodulation & Decoder Integrity"
    elif "ladder" in src or "ladder" in chk:
        return "6. Evidence Ladder Qualification"
    else:
        return "7. Other Verification Checks"


def summarize_evidence(result: NormalizedResult) -> EvidenceSummary:
    """
    Produces an organized, honest summary of evidence items.
    Does not compute confidence or modify backend checks.
    """
    categories: Dict[str, List[NormalizedEvidence]] = {}
    passed = 0
    failed = 0
    unavailable = 0
    not_run = 0
    conflict = 0
    contradictions = []
    warnings = []

    for ev in result.evidence:
        st = ev.status.upper()
        if st == "PASS":
            passed += 1
        elif st == "FAIL":
            failed += 1
            contradictions.append(f"{ev.check_name}: {ev.explanation} (FAIL)")
        elif st == "UNAVAILABLE":
            unavailable += 1
            warnings.append(f"{ev.check_name}: Data unavailable upstream ({ev.explanation})")
        elif st == "NOT_RUN":
            not_run += 1
        elif st == "CONFLICT":
            conflict += 1
            contradictions.append(f"Conflict in {ev.check_name}: {ev.explanation}")

        cat = categorize_evidence_item(ev)
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(ev)

    # Add rule/ml disagreement as a contradiction if present
    if not result.rule_ml_agreement and not result.is_unknown:
        contradictions.append(
            f"Rule AMC ({result.rule_prediction}) and ML Classifier ({result.ml_prediction}) disagree; "
            f"penalty of {result.rule_ml_penalty:.2f} applied."
        )

    return EvidenceSummary(
        total_checks=len(result.evidence),
        passed_count=passed,
        failed_count=failed,
        unavailable_count=unavailable,
        not_run_count=not_run,
        conflict_count=conflict,
        categories=categories,
        contradictions=contradictions,
        warnings=warnings,
    )
