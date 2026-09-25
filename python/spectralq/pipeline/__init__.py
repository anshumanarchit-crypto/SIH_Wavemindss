"""
SpectralQ Pipeline Plumbing Module.
"""

from spectralq.pipeline.octave_bridge import (
    OctaveBridge,
    OctaveBridgeError,
    OctaveNotFoundError,
    OctaveTimeoutError,
    OctaveExecutionError,
    OctaveParseError,
)
from spectralq.pipeline.runner import (
    run,
    PipelineResult,
    compute_file_hash,
    get_stub_classifier_output,
    get_stub_decoder_output,
)

__all__ = [
    "OctaveBridge",
    "OctaveBridgeError",
    "OctaveNotFoundError",
    "OctaveTimeoutError",
    "OctaveExecutionError",
    "OctaveParseError",
    "run",
    "PipelineResult",
    "compute_file_hash",
    "get_stub_classifier_output",
    "get_stub_decoder_output",
]
