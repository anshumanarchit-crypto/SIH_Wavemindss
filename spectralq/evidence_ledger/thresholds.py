"""
Decision Thresholding and UNKNOWN Fallback Logic.
Enforces strict gatekeeping: returns UNKNOWN when evidence is insufficient or conflicting.
"""

from typing import Optional, Tuple
from spectralq.contracts.schemas import LadderLevel


DEFAULT_CONFIDENCE_THRESHOLD = 0.60
MIN_SNR_FLOOR_DB = 1.0


def evaluate_decision_label(
    top_modulation: Optional[str],
    fused_confidence: float,
    ladder_level: LadderLevel,
    n5_agreement: bool,
    n5_agreement_score: float,
    cross_window_score: float,
    snr_db: float,
    is_valid_burst: bool,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> Tuple[str, Optional[str]]:
    """
    Evaluates whether evidence warrants asserting a specific modulation label,
    or falls back to UNKNOWN with an explicit, defensible reason.

    Returns:
        (decision_label, unknown_reason)
    """
    # 1. No valid burst detected
    if not is_valid_burst:
        return "UNKNOWN", "NO_VALID_BURST: Upstream ingest detected no valid signal energy"

    # 2. Insufficient SNR floor
    if snr_db < MIN_SNR_FLOOR_DB:
        return "UNKNOWN", f"SNR_BELOW_OPERATIONAL_FLOOR: Estimated SNR ({snr_db:.1f} dB) below minimum reliability threshold ({MIN_SNR_FLOOR_DB:.1f} dB)"

    # 3. Severe cross-window feature instability
    if cross_window_score < 0.35:
        return "UNKNOWN", f"CROSS_WINDOW_INSTABILITY: High feature drift across sub-windows (score {cross_window_score:.2f} < 0.35)"

    # 4. Severe N5 Conflict with low overall verification
    if not n5_agreement and n5_agreement_score < 0.20 and fused_confidence < (threshold + 0.10):
        return "UNKNOWN", f"N5_CONFLICT_UNRESOLVED: Rule and ML paths strongly disagree without decisive physical verification"

    # 5. Ladder Level below characterisation
    if ladder_level == LadderLevel.L1:
        return "UNKNOWN", "INSUFFICIENT_LADDER_LEVEL: Signal detected (L1) but feature extraction/blind estimation was incomplete"

    # 6. Final Fused Confidence Threshold Gate
    if fused_confidence < threshold or top_modulation is None:
        return "UNKNOWN", f"CONFIDENCE_BELOW_THRESHOLD: Fused confidence ({fused_confidence:.3f}) is below operational gate ({threshold:.2f})"

    # All criteria satisfied: Assert top modulation label
    return top_modulation, None
