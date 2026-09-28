"""
Spectrum and Power Spectral Density (PSD) Extraction Layer.
Computes calibrated frequency-domain data from actual RF samples for visualization.
Performs honest decimation and preserves physical frequency axes.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class SpectrumData:
    frequencies_mhz: List[float]
    psd_db: List[float]
    peak_freq_mhz: float
    peak_power_db: float
    rbw_khz: float
    downsampled: bool
    source_sample_count: int
    noise_floor_db: Optional[float] = None
    center_freq_mhz: Optional[float] = None
    bandwidth_mhz: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)



def compute_spectrum_data(
    iq_samples: Optional[np.ndarray],
    fs_hz: float = 1.0e6,
    nfft: int = 1024,
    max_points: int = 1024,
) -> Optional[SpectrumData]:
    """
    Computes averaged Power Spectral Density (PSD) from genuine IQ samples.
    Returns SpectrumData or None if samples are absent or insufficient.
    """
    if iq_samples is None or len(iq_samples) < 16:
        return None

    n_samples = len(iq_samples)
    actual_nfft = min(nfft, int(2 ** np.floor(np.log2(n_samples))))
    if actual_nfft < 16:
        actual_nfft = 16

    hop = actual_nfft // 2
    window = np.hanning(actual_nfft)
    window_norm = np.sum(window ** 2)

    segments = []
    for i in range(0, n_samples - actual_nfft + 1, hop):
        seg = iq_samples[i : i + actual_nfft] * window
        fft_res = np.fft.fftshift(np.fft.fft(seg))
        pwr = (np.abs(fft_res) ** 2) / (window_norm * fs_hz)
        segments.append(pwr)
        if len(segments) >= 64:  # Cap segments for fast interactive performance
            break

    if not segments:
        return None

    mean_pwr = np.mean(segments, axis=0)
    psd_db = 10.0 * np.log10(np.maximum(mean_pwr, 1e-18))
    freqs_mhz = (np.fft.fftshift(np.fft.fftfreq(actual_nfft, d=1.0 / fs_hz)) / 1.0e6).tolist()
    psd_list = psd_db.tolist()

    downsampled = False
    if len(freqs_mhz) > max_points:
        step = int(np.ceil(len(freqs_mhz) / max_points))
        freqs_mhz = freqs_mhz[::step]
        psd_list = psd_list[::step]
        downsampled = True

    peak_idx = int(np.argmax(psd_list))
    peak_freq = freqs_mhz[peak_idx]
    peak_pwr = psd_list[peak_idx]
    rbw = (fs_hz / actual_nfft) / 1000.0

    return SpectrumData(
        frequencies_mhz=freqs_mhz,
        psd_db=psd_list,
        peak_freq_mhz=float(peak_freq),
        peak_power_db=float(peak_pwr),
        rbw_khz=float(rbw),
        downsampled=downsampled,
        source_sample_count=n_samples,
    )
