"""
SpectralQ Calibration & Diagnostic Reliability Module.
"""

from spectralq.calibration.dataset import (
    SignalInstanceRecord,
    generate_synthetic_signal_instance,
    generate_synthetic_sweep,
    split_by_signal_instance,
)
from spectralq.calibration.metrics import (
    ReliabilityBin,
    CalibrationReport,
    compute_reliability_bins,
    LOW_COUNT_THRESHOLD,
)
from spectralq.calibration.calibrator import (
    ModelCalibrator,
    run_calibration_pipeline,
)
from spectralq.calibration.plotter import (
    plot_reliability_diagram,
)

__all__ = [
    "SignalInstanceRecord",
    "generate_synthetic_signal_instance",
    "generate_synthetic_sweep",
    "split_by_signal_instance",
    "ReliabilityBin",
    "CalibrationReport",
    "compute_reliability_bins",
    "LOW_COUNT_THRESHOLD",
    "ModelCalibrator",
    "run_calibration_pipeline",
    "plot_reliability_diagram",
]
