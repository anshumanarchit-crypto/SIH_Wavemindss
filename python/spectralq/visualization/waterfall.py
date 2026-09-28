"""
Waterfall & Spectrogram Extraction Layer.
Computes 2D Time-Frequency intensity matrix from actual RF samples for visualization.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class WaterfallData:
    times_ms: List[float]
    frequencies_mhz: List[float]
    power_matrix_db: List[List[float]]
    min_power_db: float
    max_power_db: float
    downsampled: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def intensity_matrix(self) -> List[List[float]]:
        return self.power_matrix_db

    @property
    def freq_bins_mhz(self) -> List[float]:
        return self.frequencies_mhz

    @property
    def time_steps_ms(self) -> List[float]:
        return self.times_ms



def compute_waterfall_data(
    iq_samples: Optional[np.ndarray],
    fs_hz: float = 1.0e6,
    nfft: int = 256,
    n_time_bins: int = 40,
) -> Optional[WaterfallData]:
    """
    Computes 2D Spectrogram (Waterfall) from genuine IQ samples.
    Returns WaterfallData or None if samples are insufficient.
    """
    if iq_samples is None or len(iq_samples) < 64:
        return None

    n_samples = len(iq_samples)
    actual_nfft = min(nfft, int(2 ** np.floor(np.log2(n_samples // 4))))
    if actual_nfft < 16:
        actual_nfft = 16

    slice_len = n_samples // n_time_bins
    if slice_len < actual_nfft:
        n_time_bins = max(4, n_samples // actual_nfft)
        slice_len = actual_nfft

    window = np.hanning(actual_nfft)
    freqs_mhz = (np.fft.fftshift(np.fft.fftfreq(actual_nfft, d=1.0 / fs_hz)) / 1.0e6).tolist()
    times_ms = []
    matrix_db = []

    for t_idx in range(n_time_bins):
        start = t_idx * slice_len
        end = start + actual_nfft
        if end > n_samples:
            break
        chunk = iq_samples[start:end] * window
        pwr = np.abs(np.fft.fftshift(np.fft.fft(chunk))) ** 2
        pwr_db = (10.0 * np.log10(np.maximum(pwr, 1e-18))).tolist()
        matrix_db.append(pwr_db)
        times_ms.append(float((start / fs_hz) * 1000.0))

    if not matrix_db:
        return None

    flat = [val for row in matrix_db for val in row]
    return WaterfallData(
        times_ms=times_ms,
        frequencies_mhz=freqs_mhz,
        power_matrix_db=matrix_db,
        min_power_db=float(min(flat)),
        max_power_db=float(max(flat)),
        downsampled=n_samples > (actual_nfft * n_time_bins),
    )
