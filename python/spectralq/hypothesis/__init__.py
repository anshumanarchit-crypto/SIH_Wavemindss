"""
SpectralQ Hypothesis Engine Package (Phase 3).
"""

from spectralq.hypothesis.registry import (
    MODULATIONS,
    INTERLEAVERS,
    FEC_SCHEMES,
    SUPPORTED_FEC,
    UNSUPPORTED_FEC,
    MODULATION_MIN_SNR,
    FEC_MIN_PLAUSIBLE_BITS,
)
from spectralq.hypothesis.candidate import HypothesisCandidate
from spectralq.hypothesis.engine import HypothesisEngineV1
from spectralq.hypothesis.debug import format_hypothesis_dump

__all__ = [
    "MODULATIONS",
    "INTERLEAVERS",
    "FEC_SCHEMES",
    "SUPPORTED_FEC",
    "UNSUPPORTED_FEC",
    "MODULATION_MIN_SNR",
    "FEC_MIN_PLAUSIBLE_BITS",
    "HypothesisCandidate",
    "HypothesisEngineV1",
    "format_hypothesis_dump",
]
