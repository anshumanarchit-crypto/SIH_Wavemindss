"""
Deterministic Evidence Ladder (L1 - L5) Calculator.
Evaluates the highest confirmed verification level based strictly on genuine,
non-stub upstream data presence and verification consistency.
"""

from typing import Optional, Tuple
from spectralq.contracts.schemas import (
    AnalysisContract,
    DecoderVerificationContract,
    LadderLevel,
    DecoderStatus,
)


def compute_ladder_level(
    analysis: AnalysisContract,
    decoder_output: Optional[DecoderVerificationContract],
    n5_agreement: bool,
    cross_window_agreement_score: float,
) -> Tuple[LadderLevel, str]:
    """
    Computes the deterministic ladder level:
      - L1: Signal detected (valid burst detected).
      - L2: Characterised (blind estimation, cumulants, SNR, baud rate valid).
      - L3: Demodulated, internally consistent (timing/constellation resolved, EVM bounded).
      - L4: Structure verified (sync detected AND (CRC valid or re-encode BER <= 0.05)).
      - L5: Independently cross-checked (L4 verified + cross-window score >= 0.80 + N5 agreement).
      
    Returns:
        (ladder_level, explanation)
    """
    # Check L1: Signal Ingest & Burst Detection
    if not analysis.is_valid_burst:
        return LadderLevel.L1, "Burst detection failed or signal energy insufficient"

    # Check L2: Blind Estimation & Feature Extraction
    has_valid_snr = analysis.snr_m2m4_db is not None
    has_valid_cumulants = (
        analysis.cumulants.C20 is not None and
        analysis.cumulants.C42 is not None
    )
    has_valid_clusters = analysis.cluster_metrics.cluster_count >= 1

    if not (has_valid_snr and has_valid_cumulants and has_valid_clusters):
        return LadderLevel.L1, "Signal detected (L1) but blind characterisation / features incomplete"

    # Check L3: Demodulation & Constellation Consistency
    # Demodulation is internally consistent if EVM is finite and not blown up, and cluster stability is reasonable
    is_demod_consistent = (
        analysis.evm < 0.65 and
        analysis.phase_ambiguity_quality > 0.20 and
        analysis.cluster_metrics.cluster_count_stability > 0.40
    )

    if not is_demod_consistent or decoder_output is None:
        return LadderLevel.L2, "Signal characterised (L2), but demodulation/carrier recovery not fully resolved"

    # Check if decoder output is genuine or stub/unavailable
    if decoder_output.status in [DecoderStatus.UNAVAILABLE, DecoderStatus.UNSUPPORTED_FEC, DecoderStatus.DECODE_FAILED]:
        return LadderLevel.L3, f"Demodulated consistently (L3), but frame verification status is {decoder_output.status.value}"

    # Check L4: Structure Verified (Sync detected AND (CRC valid or low re-encode BER))
    sync_ok = decoder_output.sync_detected and decoder_output.sync_confidence >= 0.50
    crc_ok = (decoder_output.crc_valid is True)
    reencode_ok = (decoder_output.reencode_ber is not None and decoder_output.reencode_ber <= 0.05)

    is_structure_verified = sync_ok and (crc_ok or reencode_ok)

    if not is_structure_verified:
        return LadderLevel.L3, "Demodulated (L3), but frame sync / CRC / re-encode check not verified"

    # Check L5: Independently Cross-Checked
    # Requires L4 + high cross-window consistency (>= 0.80) + N5 Rule/ML agreement
    is_cross_checked = (
        is_structure_verified and
        n5_agreement and
        cross_window_agreement_score >= 0.80
    )

    if is_cross_checked:
        return LadderLevel.L5, "Independently cross-checked (L5): Verified frame structure, N5 agreement, and high sub-window stability"

    return LadderLevel.L4, "Structure verified (L4): Frame sync and CRC/re-encode validated"
