"""
SpectralQ N2 Computed Confidence & Abstention Engine Module.
"""

from spectralq.confidence.engine import (
    ConfidenceEngine,
    ConfidenceResult,
    CONFIDENCE_ENGINE_VERSION,
)
from spectralq.confidence.calibration import (
    generate_held_out_calibration_dataset,
    fit_and_save_confidence_weights,
    load_confidence_weights,
)
from spectralq.confidence.threshold_sweep import (
    sweep_abstention_thresholds,
    load_abstention_config,
)
from spectralq.confidence.abstention import (
    AbstentionSystem,
    AbstentionDecision,
    DEFAULT_ABSTENTION_THRESHOLD,
)

__all__ = [
    "ConfidenceEngine",
    "ConfidenceResult",
    "CONFIDENCE_ENGINE_VERSION",
    "generate_held_out_calibration_dataset",
    "fit_and_save_confidence_weights",
    "load_confidence_weights",
    "sweep_abstention_thresholds",
    "load_abstention_config",
    "AbstentionSystem",
    "AbstentionDecision",
    "DEFAULT_ABSTENTION_THRESHOLD",
]
