"""
SpectralQ Visualization Preparation Layer.
Provides decimated, honest, calibrated visual artifacts for the presentation layer.
Strictly decoupled from UI rendering and signal classification mathematics.
"""

from spectralq.visualization.extractor import load_capture_samples, compute_file_sha256
from spectralq.visualization.spectrum import SpectrumData, compute_spectrum_data
from spectralq.visualization.waterfall import WaterfallData, compute_waterfall_data
from spectralq.visualization.constellation import ConstellationData, compute_constellation_data
from spectralq.visualization.eye_diagram import EyeDiagramData, compute_eye_diagram_data
from spectralq.visualization.burst_view import BurstViewData, BurstRecordItem, compute_burst_view_data
from spectralq.visualization.artifacts import (
    ObservatoryArtifacts,
    prepare_observatory_artifacts,
    build_evidence_bundle_zip,
)

__all__ = [
    "load_capture_samples",
    "compute_file_sha256",
    "SpectrumData",
    "compute_spectrum_data",
    "WaterfallData",
    "compute_waterfall_data",
    "ConstellationData",
    "compute_constellation_data",
    "EyeDiagramData",
    "compute_eye_diagram_data",
    "BurstViewData",
    "BurstRecordItem",
    "compute_burst_view_data",
    "ObservatoryArtifacts",
    "prepare_observatory_artifacts",
    "build_evidence_bundle_zip",
]
