"""
Burst Timeline & Energy Profile Extraction Layer.
Extracts burst boundaries, durations, powers, and envelopes from AnalysisContract or actual IQ samples.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class BurstRecordItem:
    index: int
    start_ms: float
    end_ms: float
    duration_ms: float
    power_db: float
    bandwidth_display: str

    @property
    def start_time_ms(self) -> float:
        return self.start_ms

    @property
    def end_time_ms(self) -> float:
        return self.end_ms

    @property
    def snr_db(self) -> float:
        return self.power_db


@dataclass
class BurstViewData:
    burst_count: int
    bursts: List[BurstRecordItem]
    timeline_duration_ms: float
    envelope_times_ms: List[float]
    envelope_power_db: List[float]
    downsampled: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "burst_count": self.burst_count,
            "bursts": [asdict(b) for b in self.bursts],
            "timeline_duration_ms": self.timeline_duration_ms,
            "envelope_times_ms": self.envelope_times_ms,
            "envelope_power_db": self.envelope_power_db,
            "downsampled": self.downsampled,
        }

    @property
    def total_bursts(self) -> int:
        return self.burst_count

    @property
    def temporal_power_times_ms(self) -> List[float]:
        return self.envelope_times_ms

    @property
    def temporal_power_db(self) -> List[float]:
        return self.envelope_power_db



def compute_burst_view_data(
    bursts_input: Optional[List[Any]] = None,
    iq_samples: Optional[np.ndarray] = None,
    fs_hz: float = 1.0e6,
    bandwidth_str: str = "N/A",
) -> BurstViewData:
    """
    Constructs BurstViewData from pre-computed Analysis bursts and/or raw IQ envelope.
    """
    records: List[BurstRecordItem] = []
    max_time_ms = 100.0

    if bursts_input:
        for i, b in enumerate(bursts_input):
            s = float(getattr(b, "start_ms", b.get("start_ms", 0.0) if isinstance(b, dict) else 0.0))
            e = float(getattr(b, "end_ms", b.get("end_ms", 0.0) if isinstance(b, dict) else 0.0))
            p = float(getattr(b, "power_db", getattr(b, "power", b.get("power", -10.0) if isinstance(b, dict) else -10.0)))
            dur = max(0.0, e - s)
            records.append(BurstRecordItem(
                index=i,
                start_ms=s,
                end_ms=e,
                duration_ms=dur,
                power_db=p,
                bandwidth_display=bandwidth_str,
            ))
            if e > max_time_ms:
                max_time_ms = e

    env_times = []
    env_pwr = []
    downsampled = False

    if iq_samples is not None and len(iq_samples) > 0:
        n = len(iq_samples)
        total_ms = (n / fs_hz) * 1000.0
        max_time_ms = max(max_time_ms, total_ms)
        # Decimate envelope to 100 points
        step = max(1, n // 100)
        mag_sq = np.abs(iq_samples) ** 2
        for k in range(0, n - step + 1, step):
            block_pwr = np.mean(mag_sq[k : k + step])
            pwr_db = float(10.0 * np.log10(max(block_pwr, 1e-12)))
            t_ms = float((k / fs_hz) * 1000.0)
            env_times.append(t_ms)
            env_pwr.append(pwr_db)
        downsampled = n > 100

    return BurstViewData(
        burst_count=len(records),
        bursts=records,
        timeline_duration_ms=float(max_time_ms),
        envelope_times_ms=env_times,
        envelope_power_db=env_pwr,
        downsampled=downsampled,
    )
