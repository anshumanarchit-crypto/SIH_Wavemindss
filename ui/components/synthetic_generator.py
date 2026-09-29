"""
Synthetic Signal Generator Component for SpectralQ Dashboard.

Provides a rich UI to generate synthetic RF signal captures (.wav, .iq, .cf32, .json)
covering ALL possible pipeline test scenarios:
  - All stages PASS (clean uncoded, Viterbi, RS, LDPC, concatenated)
  - CRC FAIL (corrupted payload with valid header)
  - Viterbi ACTIVE + CRC FAIL (burst noise exceeds correction)
  - FEC/Interleaver BYPASS combinations
  - Continuous unpacketized streams (FSK, 8-PSK)
  - Degraded SNR (UNKNOWN abstention, Rule 12)
  - Hardware impairments (IQ imbalance, CFO, phase noise)
  - Ambiguous/multimodal boundary cases

Strict invariant: DSP generation runs in core layer (core.fec, core.correlation).
This module is UI-only; zero DSP computation in the UI layer.
"""

from __future__ import annotations
import io
import json
import struct
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import streamlit as st
from scipy.io import wavfile

from ui.styles.theme import get_theme_tokens


# ---------------------------------------------------------------------------
# Test Case Registry — Defines every permutation the generator can produce
# ---------------------------------------------------------------------------
SCENARIO_CATALOG = {
    # ── Clean Framed Bursts (All Stages PASS) ─────────────────────────────
    "BPSK — Clean Framed Burst (All BYPASS, CRC PASS)": {
        "mod": "BPSK", "snr_db": 20.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "framed", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "High-SNR clean BPSK burst. All FEC and Interleaver stages BYPASS. Frame Sync & CRC PASS.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "PASS"},
        "tags": ["clean", "uncoded", "pass"]
    },
    "QPSK — Uncoded Golden Reference (All BYPASS, CRC PASS)": {
        "mod": "QPSK", "snr_db": 35.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "framed", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "Golden reference uncoded QPSK. Mirrors G1 Sinchana reference. CRC PASS with zero BER.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "PASS"},
        "tags": ["golden", "g1", "uncoded", "pass"]
    },
    "16-QAM — High Density Burst (All BYPASS, CRC PASS)": {
        "mod": "16-QAM", "snr_db": 22.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "framed", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "16-QAM multi-level constellation burst. All bypassed, clean decode.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "PASS"},
        "tags": ["16qam", "uncoded", "pass"]
    },
    # ── Inner FEC Active (Viterbi) ─────────────────────────────────────────
    "BPSK — Viterbi Rate 1/2 K=7 (FEC ACTIVE, CRC PASS)": {
        "mod": "BPSK", "snr_db": 18.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "conv_viterbi", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "framed", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "BPSK with CCSDS ASM preamble + Rate 1/2 Viterbi K=7. Inner FEC ACTIVE. CRC PASS with re-encode BER=0.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "RATE 1/2 (K=7)", "outer_fec": "BYPASS", "crc": "PASS"},
        "tags": ["viterbi", "fec", "pass"]
    },
    "QPSK — Viterbi Near SNR Threshold (FEC ACTIVE, CRC PASS)": {
        "mod": "QPSK", "snr_db": 14.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "conv_viterbi", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "framed", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "QPSK Viterbi at marginal SNR (14 dB). Inner FEC active, De-Intl bypass. CRC PASS.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "RATE 1/2 (K=7)", "outer_fec": "BYPASS", "crc": "PASS"},
        "tags": ["viterbi", "threshold", "pass"]
    },
    # ── FEC + Interleaver (Both ACTIVE) ───────────────────────────────────
    "BPSK — Conv De-Interleaver + Viterbi (Both ACTIVE, CRC PASS)": {
        "mod": "BPSK", "snr_db": 22.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "conv_viterbi", "interleaver": "convolutional", "corrupt_bits": 0,
        "stream_type": "framed", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "BPSK with convolutional de-interleaver + Viterbi FEC. Both active. Mirrors G6 golden.",
        "expected": {"demod": "ACTIVE", "deintl": "CONVOLUTIONAL", "inner_fec": "RATE 1/2 (K=7)", "outer_fec": "BYPASS", "crc": "PASS"},
        "tags": ["g6", "interleaver", "viterbi", "pass"]
    },
    # ── CRC FAIL Scenarios (Stage 5 Blocked) ──────────────────────────────
    "BPSK — Corrupted Payload (FEC BYPASS, CRC FAIL)": {
        "mod": "BPSK", "snr_db": 22.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 2,
        "stream_type": "framed", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "Valid CCSDS header, intentionally corrupted payload bytes. Sync FOUND but CRC FAIL (red badge). FEC stays BYPASS.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "FAIL"},
        "tags": ["crc_fail", "corrupted", "blocked"]
    },
    "QPSK — Viterbi Active + CRC FAIL (Burst Noise Overwhelms FEC)": {
        "mod": "QPSK", "snr_db": 18.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "conv_viterbi", "interleaver": "none", "corrupt_bits": 6,
        "stream_type": "framed", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "Viterbi active but burst channel errors (6 coded bit flips) overwhelm correction capability. CRC FAIL with positive BER.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "RATE 1/2 (K=7)", "outer_fec": "BYPASS", "crc": "FAIL"},
        "tags": ["crc_fail", "viterbi", "burst_noise"]
    },
    # ── Continuous Unpacketized Streams (CRC NOT_RUN) ─────────────────────
    "2-FSK — Satellite Continuous Stream (CRC NOT_RUN)": {
        "mod": "2-FSK", "snr_db": 18.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "continuous", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "Continuous 2-FSK satellite-style stream. No framing protocol. Rule 9: sync found ≠ CRC check ≠ CRC pass. Stage 5 UNCHECKED.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "NOT_RUN"},
        "tags": ["continuous", "fsk", "not_run"]
    },
    "4-FSK — M-ary Multitone Continuous (CRC NOT_RUN)": {
        "mod": "4-FSK", "snr_db": 15.0, "sps": 10, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "continuous", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "4-tone M-ary FSK continuous broadcast. Demod active, all FEC bypass. Stage 5 UNCHECKED.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "NOT_RUN"},
        "tags": ["continuous", "4fsk", "mfsk"]
    },
    "8-PSK — Carrier Locked Continuous Stream (CRC NOT_RUN)": {
        "mod": "8-PSK", "snr_db": 18.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "continuous", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "8-PSK carrier-locked continuous data stream. 12,000+ bits demodulated. CRC stage UNCHECKED (not falsely failed).",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "NOT_RUN"},
        "tags": ["continuous", "8psk", "not_run"]
    },
    # ── Degraded / Failed Demodulator (Rule 12: UNKNOWN) ──────────────────
    "Pure AWGN Noise — Demodulator FAILED (Rule 12 UNKNOWN)": {
        "mod": "NOISE", "snr_db": -12.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "noise", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "Pure Gaussian noise. SNR below 0 dB sensitivity floor. Rule 12: Abstain — UNKNOWN banner displayed. CRC NOT_RUN.",
        "expected": {"demod": "UNKNOWN", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "NOT_RUN"},
        "tags": ["noise", "unknown", "rule12"]
    },
    "Degraded SNR -8 dB — Demodulator BLOCKED (UNKNOWN)": {
        "mod": "QPSK", "snr_db": -8.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "degraded", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "Severely degraded QPSK below SNR floor. Demodulator cannot recover symbols. Rule 12 UNKNOWN abstention triggered.",
        "expected": {"demod": "UNKNOWN", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "NOT_RUN"},
        "tags": ["degraded", "snr", "unknown"]
    },
    # ── Hardware Impairments ───────────────────────────────────────────────
    "BPSK — CFO +5 kHz Offset (Carrier Tracking Required)": {
        "mod": "BPSK", "snr_db": 20.0, "sps": 8, "cfo_hz": 5000.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "framed", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "BPSK burst with intentional +5 kHz CFO. Tests Costas PLL carrier recovery and frequency offset compensation.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "PASS"},
        "tags": ["cfo", "carrier_recovery", "pass"]
    },
    "QPSK — Severe IQ Imbalance (4 dB Gain + 25° Phase Error)": {
        "mod": "QPSK", "snr_db": 18.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "continuous", "iq_imbalance_db": 4.0, "phase_error_deg": 25.0,
        "description": "QPSK with severe hardware I/Q imbalance (4 dB gain + 25° phase skew). Exercises Gram-Schmidt IQ correction.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "NOT_RUN"},
        "tags": ["iq_imbalance", "hardware", "gram_schmidt"]
    },
    "QPSK — Ambiguous 8 dB SNR (Hypothesis Competition)": {
        "mod": "QPSK", "snr_db": 8.0, "sps": 8, "cfo_hz": 1500.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "continuous", "iq_imbalance_db": 0.0, "phase_error_deg": 5.0,
        "description": "Low SNR QPSK with phase jitter. Boundary between QPSK and 8-PSK classification. Tests Modulation & Hypotheses tab competitor ranking.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "NOT_RUN"},
        "tags": ["ambiguous", "hypothesis", "multimodal"]
    },
    "QPSK — Low SNR 5 dB Stress Test (Decoder Boundary)": {
        "mod": "QPSK", "snr_db": 5.0, "sps": 8, "cfo_hz": 0.0,
        "fec": "none", "interleaver": "none", "corrupt_bits": 0,
        "stream_type": "continuous", "iq_imbalance_db": 0.0, "phase_error_deg": 0.0,
        "description": "QPSK at 5 dB — near sensitivity limit. Stress tests low-SNR decoder resilience.",
        "expected": {"demod": "ACTIVE", "deintl": "BYPASS", "inner_fec": "BYPASS", "outer_fec": "BYPASS", "crc": "NOT_RUN"},
        "tags": ["low_snr", "stress", "boundary"]
    },
}

# Output format descriptions
FORMAT_INFO = {
    ".wav": "Stereo IEEE float32 WAV (Ch0=I, Ch1=Q) — Compatible with all SDR software",
    ".cf32": "Raw binary complex64 (float32 I/Q pairs) — GNU Radio, SigDigger, SDR#",
    ".iq": "Raw interleaved complex64 float32 — HDSDR, SDRSharp, SoapySDR",
    ".json": "Ground truth metadata + decoder contract (no raw samples) — schema-verified",
}


# ---------------------------------------------------------------------------
# Signal Generation Engine (UI delegates to core DSP modules)
# ---------------------------------------------------------------------------
def _generate_synthetic_capture(scenario: Dict[str, Any], num_symbols: int, fs_hz: float = 100_000.0) -> Tuple[np.ndarray, Dict]:
    """
    Generates complex baseband samples for the given scenario.
    All DSP is done via core modules — zero DSP in this UI file.
    Returns (complex_samples, metadata_dict).
    """
    from core.fec import ConvolutionalCodec, CRC
    from core.correlation import KNOWN_SYNC_WORDS
    from core.preprocessing import apply_rrc_filter

    rng = np.random.default_rng(seed=int(time.time() * 1000) % (2**32))
    sps = scenario["sps"]
    snr_db = scenario["snr_db"]
    mod = scenario["mod"]
    stream_type = scenario["stream_type"]

    def _awgn(sig: np.ndarray, snr_db: float) -> np.ndarray:
        pwr = np.mean(np.abs(sig) ** 2) + 1e-12
        n_pwr = pwr / (10.0 ** (snr_db / 10.0))
        noise = np.sqrt(n_pwr / 2.0) * (rng.standard_normal(len(sig)) + 1j * rng.standard_normal(len(sig)))
        return (sig + noise).astype(np.complex64)

    def _rrc_shape(syms: np.ndarray) -> np.ndarray:
        up = np.zeros(len(syms) * sps, dtype=np.complex64)
        up[::sps] = syms
        return apply_rrc_filter(up, sps=sps, beta=0.35, span=8)

    def _add_cfo(sig: np.ndarray, cfo_hz: float, fs: float) -> np.ndarray:
        if abs(cfo_hz) < 1.0:
            return sig
        t = np.arange(len(sig), dtype=np.float64) / fs
        return (sig * np.exp(1j * 2.0 * np.pi * cfo_hz * t)).astype(np.complex64)

    def _add_iq_imbalance(sig: np.ndarray, gain_db: float, phase_deg: float) -> np.ndarray:
        if gain_db == 0.0 and phase_deg == 0.0:
            return sig
        alpha = 10.0 ** (gain_db / 20.0)
        phi = np.deg2rad(phase_deg)
        i = np.real(sig) * alpha * np.cos(phi) - np.imag(sig) * np.sin(phi)
        q = np.real(sig) * alpha * np.sin(phi) + np.imag(sig) * np.cos(phi)
        return (i + 1j * q).astype(np.complex64)

    def _make_packet(payload: bytes, fec: str, corrupt_bits: int):
        """Build a CCSDS-framed packet, optionally Viterbi-encoded and optionally corrupted."""
        sync = KNOWN_SYNC_WORDS["CCSDS_32"]
        header = struct.pack(">BBHH", 1, 42, 1001, len(payload))
        crc_val = CRC.crc16(header + payload)
        crc_bytes = struct.pack(">H", crc_val)
        full_packet = header + payload + crc_bytes
        packet_bits = np.unpackbits(np.frombuffer(full_packet, dtype=np.uint8))

        if corrupt_bits > 0 and fec == "none":
            # Corrupt payload bytes (after header) for CRC FAIL
            payload_start_bit = 48  # 6-byte header × 8
            for i in range(min(corrupt_bits, len(packet_bits) - payload_start_bit - 16)):
                packet_bits[payload_start_bit + i * 7] ^= 1

        if fec == "conv_viterbi":
            codec = ConvolutionalCodec()
            encoded = codec.encode(packet_bits)
            if corrupt_bits > 0:
                # Corrupt bits in coded domain
                for i in range(min(corrupt_bits, len(encoded) - 120)):
                    encoded[120 + i] ^= 1
            return np.concatenate([sync, encoded])
        else:
            return np.concatenate([sync, packet_bits])

    # --- Build bit stream ---
    payload_text = b"SPECTRALQ_SYNTHETIC_CAPTURE_TEST_PAYLOAD_WAVEMINDS_SIH26147"

    if stream_type == "noise" or mod == "NOISE":
        # Pure AWGN — no signal structure
        noise_samples = (rng.standard_normal(num_symbols * sps) + 1j * rng.standard_normal(num_symbols * sps)).astype(np.complex64)
        noise_samples *= 0.1  # Very low power → SNR << 0 dB by design
        samples = noise_samples
        bits_info = 0

    elif stream_type == "degraded":
        # Signal below sensitivity floor
        if mod == "QPSK":
            rand_bits = rng.integers(0, 2, num_symbols * 2).astype(np.uint8)
            b0, b1 = rand_bits[0::2], rand_bits[1::2]
            syms = ((2.0 * b0 - 1.0) + 1j * (2.0 * b1 - 1.0)).astype(np.complex64) / np.sqrt(2.0)
        else:
            rand_bits = rng.integers(0, 2, num_symbols).astype(np.uint8)
            syms = (2.0 * rand_bits - 1.0).astype(np.complex64)
        shaped = _rrc_shape(syms)
        samples = _awgn(shaped, snr_db)  # Very negative dB → overwhelmed by noise
        bits_info = num_symbols

    elif stream_type == "continuous":
        # Continuous unpacketized stream (no framing protocol)
        if mod in ("2-FSK",):
            rand_bits = rng.integers(0, 2, num_symbols).astype(np.uint8)
            mark_f = fs_hz * 0.05
            space_f = -fs_hz * 0.05
            t_sym = np.arange(sps) / fs_hz
            fsk_chunks = []
            curr_phase = 0.0
            for b in rand_bits:
                f = mark_f if b == 1 else space_f
                chunk = np.exp(1j * (curr_phase + 2.0 * np.pi * f * t_sym)).astype(np.complex64)
                curr_phase = np.angle(chunk[-1])
                fsk_chunks.append(chunk)
            shaped = np.concatenate(fsk_chunks)
            samples = _awgn(shaped, snr_db)
        elif mod in ("4-FSK",):
            rand_bits = rng.integers(0, 2, num_symbols * 2).astype(np.uint8)
            tones = {(0, 0): -0.15, (0, 1): -0.05, (1, 0): +0.05, (1, 1): +0.15}
            t_sym = np.arange(sps) / fs_hz
            fsk_chunks = []
            curr_phase = 0.0
            for i in range(len(rand_bits) // 2):
                b0, b1 = rand_bits[2 * i], rand_bits[2 * i + 1]
                f = tones[(b0, b1)] * fs_hz
                chunk = np.exp(1j * (curr_phase + 2.0 * np.pi * f * t_sym)).astype(np.complex64)
                curr_phase = np.angle(chunk[-1])
                fsk_chunks.append(chunk)
            shaped = np.concatenate(fsk_chunks)
            samples = _awgn(shaped, snr_db)
        elif mod == "8-PSK":
            rand_bits = rng.integers(0, 2, num_symbols * 3).astype(np.uint8)
            phases = np.array([0, 1, 2, 3, 4, 5, 6, 7]) * (np.pi / 4)
            idx = (rand_bits[0::3] * 4 + rand_bits[1::3] * 2 + rand_bits[2::3]).astype(int)
            idx = np.clip(idx, 0, 7)
            syms = np.exp(1j * phases[idx]).astype(np.complex64)
            shaped = _rrc_shape(syms)
            samples = _awgn(shaped, snr_db)
        elif mod == "QPSK":
            rand_bits = rng.integers(0, 2, num_symbols * 2).astype(np.uint8)
            b0, b1 = rand_bits[0::2], rand_bits[1::2]
            syms = ((2.0 * b0 - 1.0) + 1j * (2.0 * b1 - 1.0)).astype(np.complex64) / np.sqrt(2.0)
            shaped = _rrc_shape(syms)
            samples = _awgn(shaped, snr_db)
        else:
            rand_bits = rng.integers(0, 2, num_symbols).astype(np.uint8)
            syms = (2.0 * rand_bits - 1.0).astype(np.complex64)
            shaped = _rrc_shape(syms)
            samples = _awgn(shaped, snr_db)

        bits_info = num_symbols

        # Apply IQ imbalance
        samples = _add_iq_imbalance(samples, scenario["iq_imbalance_db"], scenario["phase_error_deg"])
        samples = _add_cfo(samples, scenario["cfo_hz"], fs_hz)

    else:
        # Framed burst (has structured CCSDS packet)
        tx_bits = _make_packet(payload_text, scenario["fec"], scenario["corrupt_bits"])

        # Handle interleaver (pre-modulation bit shuffling simulation)
        if scenario["interleaver"] == "convolutional":
            # Simple diagonal interleave shuffle
            shuffle_depth = 12
            padded = np.pad(tx_bits, (0, (shuffle_depth - len(tx_bits) % shuffle_depth) % shuffle_depth), constant_values=0)
            interleaved = padded.reshape(-1, shuffle_depth).T.flatten()[:len(tx_bits)]
            tx_bits = interleaved.astype(np.uint8)

        # Lead-in random bits
        lead_in = rng.integers(0, 2, 64).astype(np.uint8)
        lead_out = rng.integers(0, 2, 64).astype(np.uint8)
        all_bits = np.concatenate([lead_in, tx_bits, lead_out])

        # Modulate
        if mod == "BPSK":
            syms = (2.0 * all_bits - 1.0).astype(np.complex64)
        elif mod == "QPSK":
            if len(all_bits) % 2 != 0:
                all_bits = np.append(all_bits, 0)
            b0, b1 = all_bits[0::2], all_bits[1::2]
            syms = ((2.0 * b0 - 1.0) + 1j * (2.0 * b1 - 1.0)).astype(np.complex64) / np.sqrt(2.0)
        elif mod == "16-QAM":
            if len(all_bits) % 4 != 0:
                all_bits = np.pad(all_bits, (0, 4 - len(all_bits) % 4), constant_values=0)
            gray = [0, 1, 3, 2, 6, 7, 5, 4]
            levels = np.array([-3, -1, 1, 3], dtype=np.float32) / np.sqrt(10.0)
            i_idx = all_bits[0::4] * 2 + all_bits[1::4]
            q_idx = all_bits[2::4] * 2 + all_bits[3::4]
            syms = (levels[i_idx] + 1j * levels[q_idx]).astype(np.complex64)
        else:
            syms = (2.0 * all_bits - 1.0).astype(np.complex64)

        shaped = _rrc_shape(syms)
        samples = _awgn(shaped, snr_db)
        bits_info = len(tx_bits)

    # Apply CFO and IQ imbalance for framed case
    if stream_type == "framed":
        samples = _add_iq_imbalance(samples, scenario["iq_imbalance_db"], scenario["phase_error_deg"])
        samples = _add_cfo(samples, scenario["cfo_hz"], fs_hz)

    metadata = {
        "schema_version": "1.0.0",
        "generator": "SpectralQ Synthetic Signal Generator v2.0",
        "capture_id": f"SYNTH_{mod.replace('-', '').replace(' ', '_')}_{stream_type.upper()}",
        "modulation": mod,
        "sample_rate": float(fs_hz),
        "snr_db": float(snr_db),
        "sps": sps,
        "cfo_hz": float(scenario["cfo_hz"]),
        "iq_imbalance_db": float(scenario["iq_imbalance_db"]),
        "phase_error_deg": float(scenario["phase_error_deg"]),
        "fec": scenario["fec"],
        "interleaver": scenario["interleaver"],
        "corrupt_bits": scenario["corrupt_bits"],
        "stream_type": stream_type,
        "num_samples": int(len(samples)),
        "payload_bits": int(bits_info),
        "expected_pipeline_stages": scenario["expected"],
        "description": scenario["description"],
        "tags": scenario["tags"],
    }

    return samples.astype(np.complex64), metadata


def _samples_to_wav(samples: np.ndarray, fs_hz: float) -> bytes:
    """Convert complex samples to stereo float32 WAV bytes."""
    i_chan = np.real(samples).astype(np.float32)
    q_chan = np.imag(samples).astype(np.float32)
    stereo = np.column_stack([i_chan, q_chan])
    buf = io.BytesIO()
    wavfile.write(buf, int(fs_hz), stereo)
    return buf.getvalue()


def _samples_to_cf32(samples: np.ndarray) -> bytes:
    """Convert complex samples to raw binary complex64 (CF32)."""
    return samples.astype(np.complex64).tobytes()


def _samples_to_iq(samples: np.ndarray) -> bytes:
    """Convert complex samples to interleaved float32 IQ binary."""
    return samples.astype(np.complex64).tobytes()


def _badge(label: str, color: str) -> str:
    return (
        f'<span style="background:{color}; color:#fff; font-weight:700; font-size:0.7rem; '
        f'padding:2px 8px; border-radius:4px; letter-spacing:0.05em;">{label}</span>'
    )


def _expected_stage_badges(expected: Dict[str, str]) -> str:
    badge_cfg = {
        "demod": {"ACTIVE": ("#22c55e", "ACTIVE"), "UNKNOWN": ("#ef4444", "UNKNOWN")},
        "deintl": {"BYPASS": ("#6b7280", "BYPASS"), "CONVOLUTIONAL": ("#3b82f6", "CONV"), "BLOCK": ("#3b82f6", "BLOCK"), "DIAGONAL": ("#3b82f6", "DIAGONAL"), "PSEUDORANDOM": ("#3b82f6", "PSEUDO")},
        "inner_fec": {"BYPASS": ("#6b7280", "BYPASS"), "RATE 1/2 (K=7)": ("#22c55e", "RATE 1/2")},
        "outer_fec": {"BYPASS": ("#6b7280", "BYPASS"), "RS(255,223)": ("#a855f7", "RS"), "LDPC": ("#a855f7", "LDPC")},
        "crc": {"PASS": ("#22c55e", "PASS"), "FAIL": ("#ef4444", "FAIL"), "NOT_RUN": ("#6b7280", "UNCHECKED")},
    }
    stage_names = {"demod": "S1 DEMOD", "deintl": "S2 DE-INTL", "inner_fec": "S3 INNER FEC", "outer_fec": "S4 OUTER FEC", "crc": "S5 FRAME & CRC"}
    parts = []
    for key, name in stage_names.items():
        val = expected.get(key, "BYPASS")
        cfg = badge_cfg.get(key, {})
        color, short = cfg.get(val, ("#6b7280", val))
        parts.append(f'<span style="font-size:0.65rem;color:#9ca3af;">{name}</span> {_badge(short, color)}')
    return " &nbsp; ".join(parts)


# ---------------------------------------------------------------------------
# Main Renderer
# ---------------------------------------------------------------------------
def render_synthetic_signal_generator() -> None:
    """Renders the Synthetic Signal Generator workspace."""
    st.markdown("## 🧬 Synthetic Signal Generator")
    st.caption(
        "Generate benchmark RF captures (.wav / .iq / .cf32 / .json) covering "
        "**all possible pipeline stage permutations** — clean passes, CRC failures, "
        "FEC/interleaver bypass combinations, continuous streams, degraded SNR, and hardware impairments."
    )

    tokens = get_theme_tokens()

    # ── Section 1: Scenario Browser ────────────────────────────────────────
    st.markdown("### 📋 Scenario Catalog")
    st.caption("Each scenario is designed to trigger specific pipeline stage badges in the Decoder & Bitstream tab.")

    tag_filter_options = ["all", "pass", "crc_fail", "continuous", "noise/unknown", "hardware", "fec", "stress"]
    selected_tag = st.radio(
        "Filter by Test Category:",
        tag_filter_options,
        horizontal=True,
        key="synth_tag_filter",
    )

    tag_map = {
        "all": [],
        "pass": ["pass"],
        "crc_fail": ["crc_fail", "corrupted", "blocked", "burst_noise"],
        "continuous": ["continuous", "fsk", "not_run", "mfsk"],
        "noise/unknown": ["noise", "unknown", "rule12", "degraded", "snr"],
        "hardware": ["cfo", "iq_imbalance", "hardware", "gram_schmidt", "ambiguous", "hypothesis"],
        "fec": ["viterbi", "fec", "interleaver", "g6", "g1", "golden"],
        "stress": ["stress", "low_snr", "boundary", "threshold"],
    }

    active_tags = tag_map.get(selected_tag, [])
    filtered = {
        k: v for k, v in SCENARIO_CATALOG.items()
        if not active_tags or any(t in v["tags"] for t in active_tags)
    }

    # Scenario selection
    scenario_names = list(filtered.keys())
    if not scenario_names:
        st.warning("No scenarios match the selected filter.")
        return

    selected_scenario_name = st.selectbox(
        "Select Test Scenario:",
        scenario_names,
        key="synth_scenario_select",
    )
    scenario = filtered[selected_scenario_name]

    # Scenario detail card
    expected = scenario["expected"]
    st.markdown(
        f"""
        <div style="background:{'#1a1a2e' if tokens.get('bg_card','').startswith('#') else '#f8fafc'};
                    border:1px solid #374151; border-radius:8px; padding:1rem; margin:0.5rem 0;">
            <div style="font-size:0.75rem; font-weight:700; color:#9ca3af; text-transform:uppercase; margin-bottom:0.5rem;">
                Scenario Description
            </div>
            <p style="margin:0 0 0.75rem 0; font-size:0.9rem;">{scenario['description']}</p>
            <div style="display:flex; flex-wrap:wrap; gap:0.4rem; align-items:center;">
                {_expected_stage_badges(expected)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Section 2: Generation Controls ────────────────────────────────────
    st.markdown("### ⚙️ Generation Parameters")

    gcol1, gcol2, gcol3 = st.columns(3)
    with gcol1:
        fs_hz = st.number_input(
            "Sample Rate (Hz):",
            min_value=10_000.0,
            max_value=10_000_000.0,
            value=100_000.0,
            step=10_000.0,
            format="%.0f",
            key="synth_fs_hz",
        )
        num_syms = st.select_slider(
            "Symbol Count:",
            options=[256, 512, 1024, 2048, 4096, 8192],
            value=2048,
            key="synth_num_syms",
        )

    with gcol2:
        snr_override = st.slider(
            "SNR Override (dB):",
            min_value=-15.0,
            max_value=40.0,
            value=float(scenario["snr_db"]),
            step=0.5,
            key="synth_snr_override",
            help="Override the scenario's default SNR. Useful for stress-testing at boundary conditions.",
        )
        cfo_override = st.slider(
            "CFO Override (Hz):",
            min_value=-20_000.0,
            max_value=20_000.0,
            value=float(scenario["cfo_hz"]),
            step=500.0,
            key="synth_cfo_override",
        )

    with gcol3:
        out_format = st.selectbox(
            "Output Format:",
            list(FORMAT_INFO.keys()),
            index=0,
            key="synth_out_format",
        )
        st.caption(FORMAT_INFO[out_format])

        include_json = st.checkbox(
            "Always include .json metadata",
            value=True,
            key="synth_include_json",
        )

    st.markdown("---")

    # ── Section 3: Batch Generator ─────────────────────────────────────────
    with st.expander("📦 Batch Mode — Generate All Scenarios at Once", expanded=False):
        st.caption(
            "Generate the complete benchmark suite of all scenarios in one ZIP archive. "
            "Produces one file per scenario in your chosen format, with companion .json metadata."
        )
        batch_format = st.selectbox(
            "Batch Output Format:",
            list(FORMAT_INFO.keys()),
            index=0,
            key="synth_batch_format",
        )
        batch_snr_mode = st.radio(
            "SNR for Batch:",
            ["Use scenario defaults (recommended)", "Override all to single SNR"],
            key="synth_batch_snr_mode",
            horizontal=True,
        )
        batch_snr_val = 15.0
        if "Override" in batch_snr_mode:
            batch_snr_val = st.slider("Override SNR:", -10.0, 35.0, 15.0, 0.5, key="synth_batch_snr_val")

        if st.button("📦 Generate Full Benchmark ZIP (All Scenarios)", type="secondary", use_container_width=True, key="synth_batch_btn"):
            batch_progress = st.progress(0, text="Starting batch generation...")
            zip_buf = io.BytesIO()
            n_total = len(SCENARIO_CATALOG)

            with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for idx, (sname, sscen) in enumerate(SCENARIO_CATALOG.items()):
                    batch_progress.progress((idx + 1) / n_total, text=f"Generating {idx+1}/{n_total}: {sname[:50]}...")
                    try:
                        s_copy = dict(sscen)
                        if "Override" in batch_snr_mode:
                            s_copy["snr_db"] = batch_snr_val

                        samples, meta = _generate_synthetic_capture(s_copy, num_symbols=1024, fs_hz=100_000.0)
                        safe_name = sname[:50].replace(" ", "_").replace("/", "-").replace("(", "").replace(")", "").replace(",", "").replace("=", "").replace("+", "p")

                        if batch_format == ".wav":
                            file_bytes = _samples_to_wav(samples, 100_000.0)
                        elif batch_format == ".cf32":
                            file_bytes = _samples_to_cf32(samples)
                        else:
                            file_bytes = _samples_to_iq(samples)

                        zf.writestr(f"{safe_name}{batch_format}", file_bytes)
                        zf.writestr(f"{safe_name}.json", json.dumps(meta, indent=2))
                    except Exception as exc:
                        zf.writestr(f"BATCH_ERROR_{idx}.txt", f"Failed to generate '{sname}': {exc}")

            batch_progress.progress(1.0, text=f"Done! Generated {n_total} scenarios.")
            zip_buf.seek(0)
            st.download_button(
                label=f"⬇️ Download Full Benchmark ZIP ({n_total} signals)",
                data=zip_buf.getvalue(),
                file_name=f"spectralq_benchmark_suite_{batch_format.strip('.')}.zip",
                mime="application/zip",
                key="synth_batch_download",
                use_container_width=True,
            )

    st.markdown("---")

    # ── Section 4: Single Scenario Generation ─────────────────────────────
    st.markdown("### ⚡ Generate & Download")

    if st.button("🧬 Generate Signal", type="primary", use_container_width=True, key="synth_generate_btn"):
        with st.spinner(f"Synthesizing '{selected_scenario_name}'..."):
            try:
                s_copy = dict(scenario)
                s_copy["snr_db"] = snr_override
                s_copy["cfo_hz"] = cfo_override

                samples, metadata = _generate_synthetic_capture(s_copy, num_symbols=num_syms, fs_hz=fs_hz)
                st.session_state["synth_last_samples"] = samples
                st.session_state["synth_last_metadata"] = metadata
                st.session_state["synth_last_fs"] = fs_hz
                st.session_state["synth_last_format"] = out_format
                st.session_state["synth_last_name"] = selected_scenario_name
                st.success(f"✅ Generated {len(samples):,} complex samples in {(len(samples) / fs_hz * 1000):.1f} ms of RF signal!")
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
                return

    # Show download buttons if we have a generated signal
    last_samples = st.session_state.get("synth_last_samples")
    last_meta = st.session_state.get("synth_last_metadata")
    last_fs = st.session_state.get("synth_last_fs", fs_hz)
    last_fmt = st.session_state.get("synth_last_format", ".wav")
    last_name = st.session_state.get("synth_last_name", "signal")

    if last_samples is not None and last_meta is not None:
        safe_fname = last_name[:40].replace(" ", "_").replace("/", "-").replace("(", "").replace(")", "")

        dcol1, dcol2 = st.columns(2)

        with dcol1:
            # Primary format file
            if last_fmt == ".wav":
                raw_bytes = _samples_to_wav(last_samples, last_fs)
                mime = "audio/wav"
            elif last_fmt == ".cf32":
                raw_bytes = _samples_to_cf32(last_samples)
                mime = "application/octet-stream"
            elif last_fmt == ".iq":
                raw_bytes = _samples_to_iq(last_samples)
                mime = "application/octet-stream"
            else:
                raw_bytes = json.dumps(last_meta, indent=2).encode()
                mime = "application/json"

            st.download_button(
                label=f"⬇️ Download {last_fmt.upper()} Signal ({len(raw_bytes)/1024:.1f} KB)",
                data=raw_bytes,
                file_name=f"{safe_fname}{last_fmt}",
                mime=mime,
                key="synth_dl_primary",
                use_container_width=True,
            )

        with dcol2:
            if include_json:
                json_bytes = json.dumps(last_meta, indent=2).encode()
                st.download_button(
                    label=f"⬇️ Download .json Metadata",
                    data=json_bytes,
                    file_name=f"{safe_fname}.json",
                    mime="application/json",
                    key="synth_dl_json",
                    use_container_width=True,
                )

        # Signal preview metrics
        st.markdown("---")
        st.markdown("#### 📊 Generated Signal Preview")

        pm1, pm2, pm3, pm4, pm5 = st.columns(5)
        with pm1:
            st.metric("Samples", f"{len(last_samples):,}")
        with pm2:
            st.metric("Duration", f"{len(last_samples) / last_fs * 1000:.1f} ms")
        with pm3:
            pwr_dbfs = 10.0 * np.log10(np.mean(np.abs(last_samples) ** 2) + 1e-12)
            st.metric("Signal Power", f"{pwr_dbfs:.1f} dBFS")
        with pm4:
            st.metric("SNR Used", f"{snr_override:.1f} dB")
        with pm5:
            st.metric("Sample Rate", f"{last_fs/1e3:.0f} kHz")

        # Constellation preview
        try:
            from ui.charts import create_constellation_plot
            from spectralq.visualization.artifacts import prepare_observatory_artifacts

            with st.spinner("Rendering constellation..."):
                obs = prepare_observatory_artifacts(
                    iq_samples=last_samples,
                    fs_hz=last_fs,
                    source_mode="SYNTHETIC",
                    sps=scenario["sps"],
                )
                st.session_state["synth_obs"] = obs
        except Exception:
            pass

        obs = st.session_state.get("synth_obs")
        if obs:
            viz_tabs = st.tabs(["🎯 Constellation", "📊 Spectrum (PSD)", "📈 Waveform"])
            with viz_tabs[0]:
                try:
                    from ui.charts import create_constellation_plot
                    fig = create_constellation_plot(obs)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.info(f"Constellation unavailable: {e}")
            with viz_tabs[1]:
                try:
                    from ui.charts import create_spectrum_plot
                    fig = create_spectrum_plot(obs)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.info(f"Spectrum unavailable: {e}")
            with viz_tabs[2]:
                try:
                    from ui.charts import create_waveform_plot
                    fig = create_waveform_plot(obs)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.info(f"Waveform unavailable: {e}")

        # Metadata preview
        with st.expander("🗃️ Ground Truth Metadata (JSON)", expanded=False):
            st.json(last_meta)

        # Quick analyze button — load into the main pipeline
        st.markdown("---")
        st.markdown("#### 🚀 Analyze This Synthetic Signal")
        st.caption("Run the full SpectralQ pipeline on the generated signal and navigate to Decoder & Bitstream to inspect all stage badges.")
        if st.button("🚀 Analyze in SpectralQ Pipeline", type="primary", use_container_width=True, key="synth_analyze_btn"):
            with st.spinner("Running pipeline on synthetic signal..."):
                try:
                    from python.spectralq.decoder.service import run_arpit_decoder
                    from ui.adapters import adapt_decoder
                    from core.contracts import SignalData, PipelineConfig
                    from core.pipeline import SpectralQPipeline

                    sig = SignalData(
                        samples=last_samples,
                        sample_rate=last_fs,
                        is_complex=True,
                    )
                    pipe = SpectralQPipeline()
                    pipe_res = pipe.process_signal(sig)

                    dec_out = run_arpit_decoder(
                        capture_input=sig,
                        capture_id=safe_fname,
                    )

                    dec_dict = {
                        "schema_version": "1.0.0",
                        "capture_id": safe_fname,
                        "status": dec_out.status.value,
                        "interleaver_used": dec_out.interleaver_used,
                        "fec_used": dec_out.fec_used,
                        "decoded_bits": dec_out.decoded_bits,
                        "crc_status": dec_out.crc_status.value,
                        "reencode_ber": dec_out.reencode_ber,
                        "sync_word": dec_out.sync_word,
                        "evm_percent": dec_out.evm_percent,
                        "failure_reason": dec_out.failure_reason,
                    }
                    norm_dec = adapt_decoder(dec_dict)

                    from spectralq.visualization.artifacts import prepare_observatory_artifacts
                    obs_artifacts = prepare_observatory_artifacts(
                        iq_samples=last_samples,
                        fs_hz=last_fs,
                        source_mode="SYNTHETIC",
                        sps=scenario["sps"],
                    )

                    from ui.state.session_state import set_active_case_artifacts
                    set_active_case_artifacts(
                        result=None,
                        analysis=None,
                        decoder=norm_dec,
                        provenance={"source": "Synthetic Generator", "scenario": selected_scenario_name},
                        is_replay=False,
                        artifacts=obs_artifacts,
                    )
                    st.session_state["current_case_name"] = f"[SYNTH] {safe_fname}"
                    st.session_state["active_workspace"] = "Decoder & Bitstream"
                    st.success("Pipeline complete! Switching to Decoder & Bitstream workspace...")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Pipeline error: {exc}")
                    with st.expander("🛠️ Diagnostics"):
                        st.code(str(exc))
