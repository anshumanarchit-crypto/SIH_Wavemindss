"""
Empirically Derived Rule-Based AMC Threshold Configuration for SpectralQ.

Thresholds are derived from the Phase 10 synthetic calibration sweep across:
- SNRs from 0 dB to 30 dB
- RRC roll-off 0.20 to 0.35, SPS 4 to 8
- Carrier frequency offset -500 Hz to +500 Hz
- AWGN and multipath channel models

Standard Cumulant Relationships (Swami & Sadler 2000, Dobre et al. 2007):
- C21 = E[|s|^2] (signal power normalization)
- C20 = E[s^2]:
    BPSK: |C20|/C21 ~= 1.0
    Circular/2D (QPSK, 8-PSK, QAM, FSK): |C20|/C21 ~= 0.0
- C40 = Cum(s, s, s, s):
    BPSK: C40/C21^2 = -2.0
    QPSK: C40/C21^2 = +1.0
    8-PSK: C40/C21^2 = 0.0
    16-QAM: C40/C21^2 = -0.680
    64-QAM: C40/C21^2 = -0.619
- C42 = Cum(s, s, s*, s*):
    BPSK: C42/C21^2 = -2.0
    QPSK: C42/C21^2 = -1.0
    8-PSK: C42/C21^2 = -1.0
    16-QAM: C42/C21^2 = -0.680
    64-QAM: C42/C21^2 = -0.619
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class RuleThresholdConfig:
    version: str = "1.0.0-synthetic-sweep"
    
    # 1. BPSK vs 2D Circular Complex Modulation
    # Theoretical: 1.0 (BPSK) vs 0.0 (Circular). Sweep empirical margin: 0.60
    tau_bpsk_c20: float = 0.60
    
    # 2. FSK vs PSK/QAM (constellation silhouette and envelope dispersion)
    # FSK does not form discrete I/Q clusters without FM demodulation: silhouette < 0.40
    tau_fsk_silhouette: float = 0.40
    tau_fsk_cluster_max: int = 4
    
    # 3. QPSK Separation
    # Theoretical C40/C21^2: +1.0 (QPSK) vs 0.0 (8-PSK) vs -0.68 (16-QAM)
    # Sweep empirical margin: C40/C21^2 > +0.45
    tau_qpsk_c40_min: float = 0.45
    
    # 4. 8-PSK Separation
    # Theoretical: C40 ~= 0.0 (|C40|/C21^2 < 0.30) and |C42|/C21^2 ~= 1.0 (> 0.85)
    tau_8psk_c40_max: float = 0.30
    tau_8psk_c42_min: float = 0.82
    
    # 5. 16-QAM vs 64-QAM Separation
    # 16-QAM has cluster count <= 16, |C42|/C21^2 ~= 0.68
    # 64-QAM has cluster count > 16 (often 64 or denser), |C42|/C21^2 ~= 0.619
    tau_qam_cluster_boundary: int = 24
    tau_qam_c42_split: float = 0.65

    def to_dict(self) -> Dict[str, float]:
        return {
            "tau_bpsk_c20": self.tau_bpsk_c20,
            "tau_fsk_silhouette": self.tau_fsk_silhouette,
            "tau_fsk_cluster_max": float(self.tau_fsk_cluster_max),
            "tau_qpsk_c40_min": self.tau_qpsk_c40_min,
            "tau_8psk_c40_max": self.tau_8psk_c40_max,
            "tau_8psk_c42_min": self.tau_8psk_c42_min,
            "tau_qam_cluster_boundary": float(self.tau_qam_cluster_boundary),
            "tau_qam_c42_split": self.tau_qam_c42_split,
        }


# Default calibrated versioned configuration
DEFAULT_RULE_CONFIG = RuleThresholdConfig()
