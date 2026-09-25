"""
Hypothesis Definitions and Supported Capability Registry.
Hypothesis = Modulation x Interleaver x FEC.
"""

from typing import Dict, List, Set

SUPPORTED_MODULATIONS: List[str] = [
    "BPSK", "QPSK", "8-PSK", "16-QAM", "64-QAM", "2-FSK", "4-FSK"
]

SUPPORTED_INTERLEAVERS: List[str] = [
    "none", "block", "convolutional", "diagonal", "pseudo-random"
]

SUPPORTED_FECS: List[str] = [
    "none", "conv_viterbi_k7", "rs_255_223", "concatenated_rs_viterbi"
]

UNSUPPORTED_FECS: Set[str] = {
    "ldpc"  # Explicitly marked as unsupported; never faked or silently skipped
}

ALL_FECS: List[str] = SUPPORTED_FECS + list(UNSUPPORTED_FECS)

# Modulation minimum operational SNR benchmarks (dB)
MODULATION_MIN_SNR: Dict[str, float] = {
    "2-FSK": 0.0,
    "4-FSK": 2.0,
    "BPSK": 0.0,
    "QPSK": 3.0,
    "8-PSK": 8.0,
    "16-QAM": 12.0,
    "64-QAM": 18.0,
}
