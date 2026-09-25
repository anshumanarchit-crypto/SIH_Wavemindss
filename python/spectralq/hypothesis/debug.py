"""
Human-Readable Debug Dump for Hypothesis Engine V1.
Provides formatted inspection of ranked hypotheses, evaluation breakdown,
evidence checks, and failure reasons for jury/viva review.
"""

from typing import List
from spectralq.hypothesis.candidate import HypothesisCandidate


def format_hypothesis_dump(
    candidates: List[HypothesisCandidate],
    top_n: int = 10,
    title: str = "SpectralQ Hypothesis Engine V1 Debug Dump",
) -> str:
    """
    Renders an ASCII table and detailed summary of ranked hypothesis candidates.
    """
    total = len(candidates)
    evaluated_count = sum(1 for c in candidates if c.status == "EVALUATED")
    pruned_count = sum(1 for c in candidates if c.status == "PRUNED")
    unsupported_count = sum(1 for c in candidates if c.status == "UNSUPPORTED")

    lines = []
    lines.append("=" * 84)
    lines.append(f" {title.upper()}")
    lines.append("=" * 84)
    lines.append(
        f" Total Candidates: {total} | Evaluated: {evaluated_count} | "
        f"Pruned: {pruned_count} | Unsupported: {unsupported_count}"
    )
    lines.append("-" * 84)
    lines.append(
        f"{'Rank':<5} {'Candidate (Mod x Intl x FEC)':<36} {'Status':<12} "
        f"{'Score':<7} {'Prior':<7} {'Verif':<7} {'Failed Checks'}"
    )
    lines.append("-" * 84)

    for idx, cand in enumerate(candidates[:top_n], start=1):
        tuple_str = f"{cand.modulation} x {cand.interleaver} x {cand.fec}"
        failed_str = ", ".join(cand.failed_checks) if cand.failed_checks else "None"
        lines.append(
            f"{idx:<5} {tuple_str:<36} {cand.status:<12} "
            f"{cand.final_rank_score:<7.4f} {cand.prior_score:<7.4f} "
            f"{cand.verification_score:<7.4f} {failed_str}"
        )

    lines.append("-" * 84)

    # Detailed inspection of top candidate
    if candidates:
        top = candidates[0]
        lines.append(f"\n[WINNING HYPOTHESIS: {top.modulation} x {top.interleaver} x {top.fec}]")
        lines.append(f"  Status             : {top.status}")
        lines.append(f"  Final Rank Score   : {top.final_rank_score:.4f} (Ranking only, NOT a confidence)")
        lines.append(f"  Prior Score (ML)   : {top.prior_score:.4f}")
        lines.append(f"  Verification Score : {top.verification_score:.4f}")
        lines.append(f"  Failed Checks      : {top.failed_checks or 'None'}")
        lines.append(f"  Unsupported Items  : {top.unsupported_components or 'None'}")
        lines.append("  Evidence Ledger Items:")
        for ev in top.evidence:
            lines.append(f"    - [{ev.status.value:<11}] {ev.check_name:<28} -> {ev.explanation}")

    lines.append("=" * 84)
    return "\n".join(lines)
