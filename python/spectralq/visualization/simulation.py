"""
SpectralQ Signal Lab Simulation Engine.
Generates genuine physical RF waveforms under controlled synthetic impairment conditions
for simulation validation and educational benchmark demonstration.

STRICT EPISTEMIC BOUNDARY:
Ground truth metadata generated herein is for SIMULATION VALIDATION DISPLAY ONLY.
It is NEVER passed into the blind decision pipeline, classifier, or confidence engine.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, Optional, Tuple
import numpy as np

from spectralq.demod import apply_rrc_filter


@dataclass
class SimulationTruth:
    modulation: str
    fec: str
    interleaver: str
    baud: float
    fs_hz: float
    snr_db: float
    cfo_hz: float
    phase_offset_rad: float
    fading: bool
    seed: int
    n_symbols: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modulation": self.modulation,
            "fec": self.fec,
            "interleaver": self.interleaver,
            "baud": self.baud,
            "fs_hz": self.fs_hz,
            "snr_db": self.snr_db,
            "cfo_hz": self.cfo_hz,
            "phase_offset_rad": self.phase_offset_rad,
            "fading": self.fading,
            "seed": self.seed,
            "n_symbols": self.n_symbols,
            "ground_truth_label": "GROUND TRUTH — SIMULATION VALIDATION ONLY",
        }

    @property
    def symbol_rate(self) -> float:
        return self.baud

    @property
    def sps(self) -> int:
        return max(2, int(round(self.fs_hz / self.baud)))


def generate_simulated_signal(
    mod: Optional[str] = None,
    fec: str = "conv_viterbi_k7",
    interleaver: str = "block",
    baud: float = 100_000.0,
    fs_hz: float = 1_000_000.0,
    snr_db: float = 18.0,
    cfo_hz: float = 120.0,
    phase_offset_rad: float = 0.2,
    fading: Any = False,
    seed: int = 42,
    n_symbols: int = 2000,
    modulation: Optional[str] = None,
    num_symbols: Optional[int] = None,
    sps: Optional[int] = None,
    phase_noise_deg: Optional[float] = None,
) -> Tuple[np.ndarray, "SimulationTruth"]:
    """
    Synthesizes a realistic complex IQ waveform with RRC pulse shaping, carrier offset,
    fading, and AWGN channel noise.

    Uses proper Root Raised Cosine (RRC) pulse shaping — NOT rectangular upsampling —
    to ensure modulation-specific cumulant features (C40, C42) are preserved and
    correctly estimated by the blind AMC pipeline.

    Returns (iq_samples, SimulationTruth).
    """
    if modulation is not None:
        mod = modulation
    if mod is None:
        mod = "QPSK"

    if num_symbols is not None:
        n_symbols = num_symbols

    if sps is not None:
        baud = fs_hz / sps

    if phase_noise_deg is not None:
        phase_offset_rad = float(np.radians(phase_noise_deg))

    is_fading = False
    if isinstance(fading, str):
        is_fading = fading.lower() not in ("none", "awgn only", "false")
    elif isinstance(fading, bool):
        is_fading = fading

    rng = np.random.default_rng(seed)
    actual_sps = max(4, int(round(fs_hz / baud)))

    # Clamp CFO to within the acquisition range of the M2M4 estimator:
    # |cfo| < baud/4 ensures the carrier rotation is within the estimator's pull-in range
    max_safe_cfo = baud / 4.0
    cfo_hz_applied = float(np.clip(cfo_hz, -max_safe_cfo, max_safe_cfo))

    # =========================================================================
    # 1. Base Constellation Symbols (modulation-specific alphabet)
    # =========================================================================
    mod_clean = mod.upper().replace("-", "")

    if mod_clean == "BPSK":
        # Binary PSK: 2 points on real axis — C42 ≈ -1.0 (theoretical)
        alphabet = np.array([-1.0, 1.0], dtype=np.complex128)
        sym_indices = rng.integers(0, 2, n_symbols)
        symbols = alphabet[sym_indices]

    elif mod_clean == "QPSK" or mod_clean == "4PSK":
        # QPSK: 4 points at ±45°, ±135° — C42 ≈ -1.0 (same as BPSK but SER differs)
        alphabet = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j], dtype=np.complex128) / np.sqrt(2.0)
        sym_indices = rng.integers(0, 4, n_symbols)
        symbols = alphabet[sym_indices]

    elif mod_clean == "8PSK":
        # 8-PSK: 8 equidistant phase points — C42 ≈ -0.7 (distinctive)
        alphabet = np.exp(1j * np.arange(8) * (2 * np.pi / 8)).astype(np.complex128)
        sym_indices = rng.integers(0, 8, n_symbols)
        symbols = alphabet[sym_indices]

    elif mod_clean == "16QAM":
        # 16-QAM: 4x4 rectangular grid — C42 ≈ -0.68, C40 ≈ -0.68 (distinct from PSK)
        coords = np.array([-3, -1, 1, 3], dtype=np.float64)
        grid_i = rng.choice(coords, n_symbols)
        grid_q = rng.choice(coords, n_symbols)
        symbols = ((grid_i + 1j * grid_q) / np.sqrt(10.0)).astype(np.complex128)

    elif mod_clean == "64QAM":
        # 64-QAM: 8x8 rectangular grid — C42 ≈ -0.62 (lower magnitude than 16-QAM)
        coords = np.array([-7, -5, -3, -1, 1, 3, 5, 7], dtype=np.float64)
        grid_i = rng.choice(coords, n_symbols)
        grid_q = rng.choice(coords, n_symbols)
        symbols = ((grid_i + 1j * grid_q) / np.sqrt(42.0)).astype(np.complex128)

    elif "FSK" in mod_clean:
        # FSK: continuous-phase FM — amplitude constant, phase varies
        m_tones = 4 if "4" in mod_clean else 2
        h_mod = 0.5  # Modulation index (0.5 = MSK, >0.5 = regular FSK)
        f_tones = (np.arange(m_tones) - (m_tones - 1) / 2.0) * (baud * h_mod)
        sym_indices = rng.integers(0, m_tones, n_symbols)
        freqs_seq = np.repeat(f_tones[sym_indices], actual_sps)
        phase = 2.0 * np.pi * np.cumsum(freqs_seq) / fs_hz
        iq_unshaped = np.exp(1j * phase).astype(np.complex128)
        symbols = None

    else:
        # Default to QPSK
        alphabet = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j], dtype=np.complex128) / np.sqrt(2.0)
        sym_indices = rng.integers(0, 4, n_symbols)
        symbols = alphabet[sym_indices]

    # =========================================================================
    # 2. RRC Pulse Shaping (critical for correct cumulant feature extraction)
    #
    # WHY RRC? Rectangular upsampling (np.repeat) produces infinite ISI and
    # a sinc-shaped spectrum that spreads energy across the full Nyquist band.
    # This destroys the modulation-specific statistical fingerprint (C40, C42)
    # that the blind classifier relies on. RRC filtering:
    #   (a) Concentrates energy in a bandwidth of baud*(1+beta) Hz
    #   (b) Achieves zero ISI at symbol-spaced sampling instants
    #   (c) Preserves the theoretical cumulant values for each modulation class
    # =========================================================================
    if symbols is not None:
        # Upsample by inserting zeros between symbols (Dirac comb in time domain)
        up = np.zeros(n_symbols * actual_sps, dtype=np.complex128)
        up[::actual_sps] = symbols

        # Apply Tx RRC shaping filter (beta=0.35 is standard for satellite comms)
        iq_shaped = apply_rrc_filter(up, sps=actual_sps, alpha=0.35, span=8)
    else:
        iq_shaped = iq_unshaped  # FSK already has continuous phase — no separate shaping needed

    # =========================================================================
    # 3. Phase Noise Injection
    # =========================================================================
    if phase_offset_rad > 0:
        total_len = len(iq_shaped)
        # Wiener-process phase noise model: cumulative sum of Gaussian increments
        pn_increments = rng.normal(0, phase_offset_rad / np.sqrt(actual_sps), total_len)
        pn_walk = np.cumsum(pn_increments)
        iq_shaped = iq_shaped * np.exp(1j * pn_walk)

    # =========================================================================
    # 4. Carrier Frequency Offset (CFO)
    # =========================================================================
    total_len = len(iq_shaped)
    t = np.arange(total_len) / fs_hz
    carrier_rotation = np.exp(1j * 2.0 * np.pi * cfo_hz_applied * t)
    iq_carrier = iq_shaped * carrier_rotation

    # =========================================================================
    # 5. Multipath Rayleigh Fading
    # =========================================================================
    if is_fading:
        fade_blocks = total_len // 200 + 1
        fade_raw = (rng.normal(0, 1, fade_blocks) + 1j * rng.normal(0, 1, fade_blocks))
        fade_env = np.abs(np.repeat(fade_raw, 200)[:total_len])
        fade_env = fade_env / (np.mean(fade_env) or 1.0)
        iq_carrier = iq_carrier * fade_env

    # =========================================================================
    # 6. AWGN Noise Addition (calibrated to actual signal power after shaping)
    # =========================================================================
    sig_power = float(np.mean(np.abs(iq_carrier) ** 2))
    if sig_power < 1e-12:
        sig_power = 1.0
    noise_power = sig_power / (10.0 ** (snr_db / 10.0))
    noise = np.sqrt(noise_power / 2.0) * (
        rng.normal(0, 1, total_len) + 1j * rng.normal(0, 1, total_len)
    )
    iq_noisy = (iq_carrier + noise).astype(np.complex64)

    truth = SimulationTruth(
        modulation=mod,
        fec=fec,
        interleaver=interleaver,
        baud=baud,
        fs_hz=fs_hz,
        snr_db=snr_db,
        cfo_hz=cfo_hz_applied,
        phase_offset_rad=phase_offset_rad,
        fading=is_fading,
        seed=seed,
        n_symbols=n_symbols,
    )

    return iq_noisy, truth
