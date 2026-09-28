"""
Constellation Extraction Layer.
Computes in-phase and quadrature coordinates from genuine RF samples for scatter visualization.
Never fabricates ideal geometric grids; strictly renders observed signal points.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class ConstellationData:
    i_points: List[float]
    q_points: List[float]
    sample_count: int
    rms_magnitude: float
    downsampled: bool
    evm_percent: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def num_points(self) -> int:
        return self.sample_count



def compute_constellation_data(
    iq_samples: Optional[np.ndarray],
    max_points: int = 2000,
    normalize: bool = True,
) -> Optional[ConstellationData]:
    """
    Extracts normalized I and Q points from genuine IQ samples.
    Returns ConstellationData or None if samples are insufficient.
    """
    if iq_samples is None or len(iq_samples) < 8:
        return None

    n_samples = len(iq_samples)
    downsampled = False

    if n_samples > max_points:
        rng = np.random.default_rng(42)
        indices = rng.choice(n_samples, size=max_points, replace=False)
        pts = iq_samples[indices]
        downsampled = True
    else:
        pts = iq_samples

    rms = float(np.sqrt(np.mean(np.abs(pts) ** 2)) or 1.0)
    if normalize and rms > 1e-12:
        pts = pts / rms

    return ConstellationData(
        i_points=pts.real.tolist(),
        q_points=pts.imag.tolist(),
        sample_count=len(pts),
        rms_magnitude=rms,
        downsampled=downsampled,
    )
