"""
Eye Diagram Extraction Layer.
Folds temporal RF samples across two symbol periods to render transmission eye patterns.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class EyeDiagramData:
    time_symbol_axis: List[float]
    traces_i: List[List[float]]
    traces_q: List[List[float]]
    sps: int
    num_traces: int
    downsampled: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_eye_diagram_data(
    iq_samples: Optional[np.ndarray],
    sps: int = 8,
    num_traces: int = 40,
) -> Optional[EyeDiagramData]:
    """
    Computes overlapping two-symbol eye diagram traces from genuine IQ samples.
    """
    if iq_samples is None or len(iq_samples) < (sps * 4):
        return None

    period = sps * 2
    n_available = len(iq_samples) // sps - 2
    if n_available <= 0:
        return None

    step = max(1, n_available // num_traces)
    traces_i = []
    traces_q = []

    for k in range(0, n_available, step):
        idx = k * sps
        seg = iq_samples[idx : idx + period]
        if len(seg) == period:
            traces_i.append(seg.real.tolist())
            traces_q.append(seg.imag.tolist())
        if len(traces_i) >= num_traces:
            break

    if not traces_i:
        return None

    # Normalized time axis in symbol periods [-1.0, 1.0]
    time_axis = np.linspace(-1.0, 1.0, period).tolist()

    return EyeDiagramData(
        time_symbol_axis=time_axis,
        traces_i=traces_i,
        traces_q=traces_q,
        sps=sps,
        num_traces=len(traces_i),
        downsampled=True,
    )
