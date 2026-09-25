"""
Hypothesis Registry & Capability Definitions for SpectralQ.
Fixed lists from Prompt 0:
- Modulations: BPSK, QPSK, 8-PSK, 16-QAM, 64-QAM, 2-FSK, 4-FSK
- Interleavers: none, block, convolutional, diagonal, pseudo-random
- FEC: none, conv_viterbi_k7, rs_255_223, concatenated, ldpc (unsupported)
"""

from typing import Dict, List, Set

MODULATIONS: List[str] = [
    "BPSK",
    "QPSK",
    "8-PSK",
    "16-QAM",
    "64-QAM",
    "2-FSK",
    "4-FSK",
]

INTERLEAVERS: List[str] = [
    "none",
    "block",
    "convolutional",
    "diagonal",
    "pseudo-random",
]

FEC_SCHEMES: List[str] = [
    "none",
    "conv_viterbi_k7",
    "rs_255_223",
    "concatenated",
    "ldpc",
]

SUPPORTED_MODULATIONS: Set[str] = set(MODULATIONS)
SUPPORTED_INTERLEAVERS: Set[str] = set(INTERLEAVERS)
SUPPORTED_FEC: Set[str] = {"none", "conv_viterbi_k7", "rs_255_223", "concatenated"}

# LDPC must NEVER be faked or silently dropped
UNSUPPORTED_FEC: Set[str] = {"ldpc"}

# Physical operational SNR floors (dB)
MODULATION_MIN_SNR: Dict[str, float] = {
    "2-FSK": 0.0,
    "4-FSK": 2.0,
    "BPSK": 0.0,
    "QPSK": 3.0,
    "8-PSK": 8.0,
    "16-QAM": 12.0,
    "64-QAM": 18.0,
}

# Minimum decoded bit length plausibility per FEC code family
FEC_MIN_PLAUSIBLE_BITS: Dict[str, int] = {
    "none": 1,
    "conv_viterbi_k7": 56,        # Constraint length K=7 requires trace-back flushing
    "rs_255_223": 2040,           # 255 bytes block length = 2040 bits
    "concatenated": 2040,         # Outer RS(255,223) requires at least 1 full RS block
    "ldpc": 512,                  # Standard sub-block
}
