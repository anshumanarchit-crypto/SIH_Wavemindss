"""
Deterministic Ladder Level Computation.
Computes the evidence ladder tier (L1 to L5) as a pure function of upstream data availability.

Ladder Level Definitions:
  L1 = a burst/signal was detected, nothing more
  L2 = characterised: baud/CFO/modulation family estimated with intervals
  L3 = demodulated to bits, internally consistent (no decoder failure)
  L4 = structure verified: sync word AND/OR CRC pass, or a recognized frame
  L5 = independently cross-checked (e.g. a second decoder/tool agrees)
"""

from typing import Optional, Tuple
from spectralq.contracts.schemas import (
    AnalysisContract,
    DecoderOutputContract,
    DecoderStatus,
    CrcStatus,
    LadderLevel,
)


def compute_ladder_level(
    analysis: Optional[AnalysisContract],
    decoder_output: Optional[DecoderOutputContract] = None,
    second_tool_agreed: bool = False,
) -> Tuple[LadderLevel, str]:
    """
    Pure deterministic evaluation of the highest confirmed evidence ladder level.
    Never relies on manual flags; evaluates presence and validity of stage outputs.
    """
    # -------------------------------------------------------------------------
    # Tier 0 -> L1 Check: Signal Burst Ingest
    # -------------------------------------------------------------------------
    if analysis is None or not analysis.bursts or len(analysis.bursts) == 0:
        return LadderLevel.L1, "Signal burst detection absent or empty (L1 floor)"

    # Check if estimates are populated with valid confidence intervals
    est = analysis.estimates
    has_valid_intervals = (
        est.baud.ci_lo <= est.baud.ci_hi and
        est.cfo.ci_lo <= est.cfo.ci_hi and
        est.bandwidth.ci_lo <= est.bandwidth.ci_hi and
        est.snr.ci_lo <= est.snr.ci_hi
    )

    if not has_valid_intervals:
        return LadderLevel.L1, "Signal burst detected (L1), but parameter confidence intervals incomplete or invalid"

    # -------------------------------------------------------------------------
    # Tier L2 Check: Characterised with Intervals
    # -------------------------------------------------------------------------
    # At this point, baud/CFO/bandwidth/SNR are estimated with valid intervals.
    # If decoder output is absent, unavailable, or failed, signal is characterised at L2.
    if decoder_output is None:
        return (
            LadderLevel.L2,
            "Signal characterised with parameter intervals (L2); demodulation not executed",
        )

    if decoder_output.status == DecoderStatus.UNSUPPORTED:
        return (
            LadderLevel.L2,
            f"Signal characterised (L2); evaluated FEC scheme is unsupported ({decoder_output.failure_reason})",
        )

    # Check bitstream extraction
    has_bits = False
    if isinstance(decoder_output.decoded_bits, str):
        has_bits = len(decoder_output.decoded_bits) > 0
    elif isinstance(decoder_output.decoded_bits, list):
        has_bits = len(decoder_output.decoded_bits) > 0
    elif isinstance(decoder_output.decoded_bits, int):
        has_bits = decoder_output.decoded_bits > 0

    if decoder_output.status == DecoderStatus.FAILED or not has_bits:
        return (
            LadderLevel.L2,
            f"Signal characterised (L2); demodulation failed to extract bits ({decoder_output.failure_reason or '0 bits'})",
        )

    # -------------------------------------------------------------------------
    # Tier L3 Check: Demodulated to bits, Internally Consistent
    # -------------------------------------------------------------------------
    # Internal consistency requires EVM < 0.65 and phase ambiguity quality > 0.20 (if evaluated)
    paq = analysis.features.phase_ambiguity_quality
    is_internally_consistent = (
        analysis.features.evm < 0.65 and
        (paq is None or paq > 0.20)
    )

    if not is_internally_consistent:
        return (
            LadderLevel.L2,
            "Signal characterised (L2), but demodulation constellation exhibits high EVM or unresolved phase ambiguity",
        )

    # Check if structure is verified (CRC pass or low re-encode BER)
    crc_passed = (decoder_output.crc_status == CrcStatus.PASS)
    reencode_passed = (
        decoder_output.reencode_ber is not None and
        decoder_output.reencode_ber <= 0.05
    )

    is_structure_verified = crc_passed or reencode_passed

    if not is_structure_verified:
        return (
            LadderLevel.L3,
            "Demodulated to bits with internal constellation consistency (L3); frame structure / CRC not verified",
        )

    # -------------------------------------------------------------------------
    # Tier L4 Check: Structure Verified
    # -------------------------------------------------------------------------
    if not second_tool_agreed:
        verif_method = "CRC checksum pass" if crc_passed else f"re-encode BER ({decoder_output.reencode_ber:.4f})"
        return (
            LadderLevel.L4,
            f"Frame structure verified via {verif_method} (L4)",
        )

    # -------------------------------------------------------------------------
    # Tier L5 Check: Independently Cross-Checked
    # -------------------------------------------------------------------------
    return (
        LadderLevel.L5,
        "Independently cross-checked: Verified frame structure confirmed by second independent tool/decoder (L5)",
    )
