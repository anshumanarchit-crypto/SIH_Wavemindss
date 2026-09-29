"""
SpectralQ Tier-1b Wideband Spectrum Scanner & Digital Down-Converter (DDC).

Provides:
1. Wideband spectral scanning and energy detection via Welch PSD & threshold clustering.
2. Parameter estimation per candidate emission (center frequency, occupied bandwidth, SNR, power).
3. Digital Down-Converter (DDC) channelizer: complex frequency translation to DC,
   anti-aliasing FIR low-pass filtering, and decimation to an isolated narrowband slice.
4. Export interface ready for Tier-1a single-signal SpectralQ pipeline analysis.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import numpy as np
from scipy.signal import welch, firwin, lfilter


@dataclass
class DetectedEmission:
    emission_id: int
    center_freq_hz: float
    bandwidth_hz: float
    freq_start_hz: float
    freq_stop_hz: float
    peak_power_db: float
    snr_db: float
    status: str = "DETECTED"
    analyzed_modulation: Optional[str] = None
    analyzed_confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emission_id": self.emission_id,
            "center_freq_hz": round(self.center_freq_hz, 1),
            "center_freq_khz": round(self.center_freq_hz / 1000.0, 2),
            "bandwidth_hz": round(self.bandwidth_hz, 1),
            "bandwidth_khz": round(self.bandwidth_hz / 1000.0, 2),
            "freq_start_khz": round(self.freq_start_hz / 1000.0, 2),
            "freq_stop_khz": round(self.freq_stop_hz / 1000.0, 2),
            "peak_power_db": round(self.peak_power_db, 2),
            "snr_db": round(self.snr_db, 2),
            "status": self.status,
            "analyzed_modulation": self.analyzed_modulation,
            "analyzed_confidence": self.analyzed_confidence,
        }


@dataclass
class WidebandScanResult:
    fs_hz: float
    n_samples: int
    freqs: np.ndarray
    psd_db: np.ndarray
    noise_floor_db: float
    detection_threshold_db: float
    emissions: List[DetectedEmission] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fs_hz": self.fs_hz,
            "n_samples": self.n_samples,
            "noise_floor_db": round(self.noise_floor_db, 2),
            "detection_threshold_db": round(self.detection_threshold_db, 2),
            "num_emissions": len(self.emissions),
            "emissions": [e.to_dict() for e in self.emissions],
        }


def scan_wideband_spectrum(
    iq_samples: np.ndarray,
    fs_hz: float = 1.0e6,
    n_fft: int = 1024,
    threshold_margin_db: float = 8.0,
    min_bandwidth_bins: int = 2,
    suppress_dc_spike: bool = True,
) -> WidebandScanResult:
    """
    Performs energy detection and candidate emission clustering across the band.
    """
    iq = np.asarray(iq_samples, dtype=np.complex64)
    if len(iq) < 32:
        empty_f = np.linspace(-fs_hz / 2, fs_hz / 2, 64)
        return WidebandScanResult(
            fs_hz=fs_hz,
            n_samples=len(iq),
            freqs=empty_f,
            psd_db=np.full_like(empty_f, -100.0),
            noise_floor_db=-100.0,
            detection_threshold_db=-90.0,
            emissions=[],
        )

    nperseg = min(n_fft, len(iq))
    f, psd = welch(iq, fs=fs_hz, nperseg=nperseg, return_onesided=False)
    idx = np.argsort(f)
    freqs = f[idx]
    psd = psd[idx]

    psd_db = 10.0 * np.log10(np.maximum(psd, 1e-15))
    df = float(freqs[1] - freqs[0]) if len(freqs) > 1 else fs_hz / nperseg

    # Robust noise floor: median of bottom 40% of PSD
    sorted_psd = np.sort(psd_db)
    bottom_cut = max(1, int(len(sorted_psd) * 0.40))
    noise_floor_db = float(np.median(sorted_psd[:bottom_cut]))
    detection_threshold_db = noise_floor_db + threshold_margin_db

    # Binary mask of occupied spectral regions
    mask = psd_db >= detection_threshold_db

    # Connected component labeling along 1D frequency axis
    raw_blocks: List[Tuple[int, int]] = []
    in_block = False
    start_idx = 0

    for i in range(len(mask)):
        if mask[i] and not in_block:
            in_block = True
            start_idx = i
        elif not mask[i] and in_block:
            in_block = False
            stop_idx = i - 1
            if (stop_idx - start_idx + 1) >= min_bandwidth_bins:
                raw_blocks.append((start_idx, stop_idx))

    if in_block:
        stop_idx = len(mask) - 1
        if (stop_idx - start_idx + 1) >= min_bandwidth_bins:
            raw_blocks.append((start_idx, stop_idx))

    emissions: List[DetectedEmission] = []
    for start_idx, stop_idx in raw_blocks:
        peak_sub_idx = start_idx + int(np.argmax(psd_db[start_idx:stop_idx + 1]))
        f_start = float(freqs[start_idx])
        f_stop = float(freqs[stop_idx])
        f_center = (f_start + f_stop) / 2.0
        bw = max(df * min_bandwidth_bins, f_stop - f_start)
        peak_pwr = float(psd_db[peak_sub_idx])
        snr = max(0.0, peak_pwr - noise_floor_db)

        # SDR DC LO-leakage suppression: single-bin or 2-bin residual spike at exact 0 Hz
        if suppress_dc_spike and abs(f_center) <= 1.5 * df and (stop_idx - start_idx + 1) <= 3:
            continue

        emissions.append(
            DetectedEmission(
                emission_id=len(emissions) + 1,
                center_freq_hz=f_center,
                bandwidth_hz=bw,
                freq_start_hz=f_start,
                freq_stop_hz=f_stop,
                peak_power_db=peak_pwr,
                snr_db=snr,
            )
        )

    return WidebandScanResult(
        fs_hz=fs_hz,
        n_samples=len(iq),
        freqs=freqs,
        psd_db=psd_db,
        noise_floor_db=noise_floor_db,
        detection_threshold_db=detection_threshold_db,
        emissions=emissions,
    )


def channelize_emission(
    iq_samples: np.ndarray,
    fs_wide_hz: float,
    center_freq_hz: float,
    bandwidth_hz: float,
    guard_band_factor: float = 1.3,
    max_decimation: int = 16,
) -> Tuple[np.ndarray, float]:
    """
    Digital Down-Converter (DDC):
    1. Complex frequency mixing to translate center_freq_hz to 0 Hz (DC).
    2. Low-pass anti-aliasing FIR filter matching emission bandwidth.
    3. Integer decimation down to narrowband sample rate.
    """
    iq = np.asarray(iq_samples, dtype=np.complex64)
    n = np.arange(len(iq), dtype=np.float64)

    # 1. Complex mixing to baseband DC
    shifted = iq * np.exp(-1j * 2.0 * np.pi * (center_freq_hz / fs_wide_hz) * n).astype(np.complex64)

    # 2. Design anti-aliasing low-pass filter
    cutoff_hz = (bandwidth_hz / 2.0) * guard_band_factor
    cutoff_norm = float(np.clip(cutoff_hz / (fs_wide_hz / 2.0), 0.01, 0.45))
    num_taps = 65
    taps = firwin(num_taps, cutoff_norm, window="hamming").astype(np.float32)
    filtered = lfilter(taps, 1.0, shifted).astype(np.complex64)

    # 3. Calculate integer decimation factor
    # Nyquist constraint: fs_narrow >= 2 * cutoff_hz
    min_fs_narrow = max(bandwidth_hz * 2.2, 10000.0)
    desired_decimation = int(np.floor(fs_wide_hz / min_fs_narrow))
    decimation = max(1, min(max_decimation, desired_decimation))

    narrowband_iq = filtered[::decimation].copy()
    fs_narrow_hz = fs_wide_hz / decimation

    return narrowband_iq, fs_narrow_hz


def export_emission_for_pipeline(
    narrowband_iq: np.ndarray,
    fs_narrow_hz: float,
    emission_id: int,
    output_dir: Path,
) -> Tuple[Path, Path]:
    """
    Persists channelized narrowband IQ as .cf32 and companion metadata JSON,
    ready for direct ingestion by spectralq.pipeline.runner.run(..., mode='live').
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cap_file = output_dir / f"emission_{emission_id}_channelized.cf32"
    meta_file = cap_file.with_suffix(".json")

    # Write raw complex64 (I, Q float32 interleaved)
    raw_bytes = narrowband_iq.astype(np.complex64).tobytes()
    cap_file.write_bytes(raw_bytes)

    meta = {
        "schema_version": "1.0.0",
        "sample_rate": float(fs_narrow_hz),
        "fs_hz": float(fs_narrow_hz),
        "source": "Wideband DDC Channelizer",
        "emission_id": emission_id,
        "n_samples": len(narrowband_iq),
    }
    meta_file.write_text(json.dumps(meta, indent=2))

    return cap_file, meta_file
