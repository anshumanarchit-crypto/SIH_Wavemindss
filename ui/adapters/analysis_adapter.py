"""
UI Analysis Adapter.
Converts backend AnalysisContract into normalized UI view models.
Strictly read-only; performs zero DSP or parameter estimation calculations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from spectralq.contracts.schemas import AnalysisContract, validate_analysis_dict


class AnalysisValidationError(Exception):
    """Raised when backend analysis data fails schema validation."""
    pass


@dataclass
class NormalizedEstimate:
    name: str
    value: float
    unit: str
    ci_lo: float
    ci_hi: float
    method: str
    has_valid_ci: bool

    @property
    def display_value(self) -> str:
        if self.unit == "Hz":
            if abs(self.value) >= 1e6:
                return f"{self.value / 1e6:.3f} MHz"
            elif abs(self.value) >= 1e3:
                return f"{self.value / 1e3:.2f} kHz"
            else:
                return f"{self.value:.1f} Hz"
        elif self.unit == "Baud":
            if self.value >= 1e6:
                return f"{self.value / 1e6:.3f} MBaud"
            elif self.value >= 1e3:
                return f"{self.value / 1e3:.2f} kBaud"
            else:
                return f"{self.value:.0f} Baud"
        elif self.unit == "dB":
            return f"{self.value:.2f} dB"
        return f"{self.value:.4f} {self.unit}"


@dataclass
class NormalizedBurst:
    index: int
    start_ms: float
    end_ms: float
    duration_ms: float
    power_db: float


@dataclass
class NormalizedFeatures:
    cumulants: Dict[str, float]
    cluster_count: int
    silhouette: float
    intra_var: float
    inter_dist: float
    evm: float
    phase_ambiguity_quality: Optional[float]
    cyclic: Optional[Dict[str, Any]]


@dataclass
class NormalizedAnalysis:
    schema_version: str
    capture_id: str
    source_mode: str
    fs_hz: float
    fs_source: str
    bursts: List[NormalizedBurst]
    baud: NormalizedEstimate
    cfo: NormalizedEstimate
    bandwidth: NormalizedEstimate
    snr: NormalizedEstimate
    features: NormalizedFeatures
    sub_windows: Optional[List[Dict[str, Any]]]
    notes: Optional[str]
    capability_available: Optional[bool]
    raw_dict: Dict[str, Any] = field(default_factory=dict)


def adapt_analysis(raw_data: Any) -> NormalizedAnalysis:
    """
    Validates and adapts a backend analysis dict or AnalysisContract into NormalizedAnalysis.
    Raises AnalysisValidationError if contract requirements are violated.
    """
    if isinstance(raw_data, AnalysisContract):
        contract = raw_data
        raw_dict = contract.model_dump()
    elif isinstance(raw_data, dict):
        try:
            contract = validate_analysis_dict(raw_data)
            raw_dict = raw_data
        except Exception as e:
            raise AnalysisValidationError(f"Invalid AnalysisContract schema: {e}") from e
    else:
        raise AnalysisValidationError(f"Expected dict or AnalysisContract, got {type(raw_data)}")

    # Parse bursts
    bursts = [
        NormalizedBurst(
            index=i,
            start_ms=b.start_ms,
            end_ms=b.end_ms,
            duration_ms=b.end_ms - b.start_ms,
            power_db=b.power,
        )
        for i, b in enumerate(contract.bursts)
    ]

    # Parse estimates
    est = contract.estimates
    baud_est = NormalizedEstimate(
        name="Symbol Rate / Baud",
        value=est.baud.value,
        unit="Baud",
        ci_lo=est.baud.ci_lo,
        ci_hi=est.baud.ci_hi,
        method=est.baud.method,
        has_valid_ci=est.baud.ci_lo <= est.baud.ci_hi,
    )
    cfo_est = NormalizedEstimate(
        name="Carrier Frequency Offset",
        value=est.cfo.value,
        unit="Hz",
        ci_lo=est.cfo.ci_lo,
        ci_hi=est.cfo.ci_hi,
        method=est.cfo.method,
        has_valid_ci=est.cfo.ci_lo <= est.cfo.ci_hi,
    )
    bw_est = NormalizedEstimate(
        name="Bandwidth (Occupied)",
        value=est.bandwidth.value,
        unit="Hz",
        ci_lo=est.bandwidth.ci_lo,
        ci_hi=est.bandwidth.ci_hi,
        method=est.bandwidth.method,
        has_valid_ci=est.bandwidth.ci_lo <= est.bandwidth.ci_hi,
    )
    snr_est = NormalizedEstimate(
        name="Signal-to-Noise Ratio (SNR)",
        value=est.snr.value,
        unit="dB",
        ci_lo=est.snr.ci_lo,
        ci_hi=est.snr.ci_hi,
        method=est.snr.method,
        has_valid_ci=est.snr.ci_lo <= est.snr.ci_hi,
    )

    # Features
    cum_dict = {
        "C20": contract.features.cumulants.C20,
        "C21": contract.features.cumulants.C21,
        "C40": contract.features.cumulants.C40,
        "C42": contract.features.cumulants.C42,
        "C60": contract.features.cumulants.C60,
        "C63": contract.features.cumulants.C63,
        "C80": contract.features.cumulants.C80,
    }
    feats = NormalizedFeatures(
        cumulants=cum_dict,
        cluster_count=contract.features.cluster.count,
        silhouette=contract.features.cluster.silhouette,
        intra_var=contract.features.cluster.intra_var,
        inter_dist=contract.features.cluster.inter_dist,
        evm=contract.features.evm,
        phase_ambiguity_quality=contract.features.phase_ambiguity_quality,
        cyclic=contract.features.cyclic,
    )

    return NormalizedAnalysis(
        schema_version=contract.schema_version,
        capture_id=contract.capture_id,
        source_mode=contract.source_mode.value.upper(),
        fs_hz=contract.fs_hz,
        fs_source=contract.fs_source.value,
        bursts=bursts,
        baud=baud_est,
        cfo=cfo_est,
        bandwidth=bw_est,
        snr=snr_est,
        features=feats,
        sub_windows=contract.sub_windows,
        notes=contract.notes,
        capability_available=contract.capability_available,
        raw_dict=raw_dict,
    )
