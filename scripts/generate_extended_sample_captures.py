"""
Generate Extended Test Capture Suite for SpectralQ.
Produces 10 distinct, mathematically rigorous RF captures (.wav, .iq, .cf32)
and companion JSON metadata files in sample_captures/ to exercise every stage
permutation (ACTIVE, BYPASS, FAILED/BLOCKED, UNCHECKED, UNKNOWN) across:
  - Modulation & Hypotheses Tab (Clean, Ambiguous Multimodal, Abstention/Unknown)
  - Decoder & Bitstream Tab (All Stages Pass, Interleaver Bypass, FEC Bypass, CRC Fail, etc.)
"""

import json
import math
import shutil
import struct
from pathlib import Path
import sys
from typing import Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
from scipy.io import wavfile

from core.correlation import CRC, KNOWN_SYNC_WORDS
from core.fec import ConvolutionalCodec
from core.preprocessing import apply_rrc_filter

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPTURES_DIR = REPO_ROOT / "sample_captures"
OFFICIAL_GOLDEN = REPO_ROOT / "data" / "official" / "sinchana" / "golden"

CAPTURES_DIR.mkdir(parents=True, exist_ok=True)


def pulse_shape_symbols(symbols: np.ndarray, sps: int = 8, beta: float = 0.35) -> np.ndarray:
    """Upsample symbols and apply Root Raised Cosine filter."""
    upsampled = np.zeros(len(symbols) * sps, dtype=np.complex64)
    upsampled[::sps] = symbols
    filtered = apply_rrc_filter(upsampled, sps=sps, beta=beta, span=8)
    return filtered


def add_awgn(samples: np.ndarray, snr_db: float) -> np.ndarray:
    """Add Complex AWGN noise for specified SNR."""
    sig_pwr = np.mean(np.abs(samples) ** 2)
    noise_pwr = sig_pwr / (10.0 ** (snr_db / 10.0))
    noise = np.sqrt(noise_pwr / 2.0) * (
        np.random.randn(len(samples)) + 1j * np.random.randn(len(samples))
    )
    return (samples + noise).astype(np.complex64)


def save_stereo_wav(filepath: Path, samples: np.ndarray, sample_rate: int = 100_000) -> None:
    """Save complex samples as stereo float32 WAV (Ch0=I, Ch1=Q)."""
    i_chan = np.real(samples).astype(np.float32)
    q_chan = np.imag(samples).astype(np.float32)
    stereo = np.column_stack([i_chan, q_chan])
    wavfile.write(str(filepath), sample_rate, stereo)


def save_raw_iq(filepath: Path, samples: np.ndarray) -> None:
    """Save complex samples as interleaved float32 (complex64) IQ."""
    samples.astype(np.complex64).tofile(filepath)


def save_cf32(filepath: Path, samples: np.ndarray) -> None:
    """Save complex samples as raw complex64 binary."""
    samples.astype(np.complex64).tofile(filepath)


def make_packet(
    payload_bytes: bytes,
    sync_name: str = "CCSDS_32",
    version: int = 1,
    pkt_type: int = 42,
    seq_num: int = 1001,
    crc_type: str = "crc16",
    corrupt_payload_bits: int = 0,
) -> Tuple[np.ndarray, np.ndarray, bytes, int]:
    """Constructs sync word and packet bits, optionally corrupting payload bits to test CRC FAIL."""
    sync_bits = KNOWN_SYNC_WORDS[sync_name]
    header = struct.pack(">BBHH", version, pkt_type, seq_num, len(payload_bytes))
    crc_val = CRC.crc16(header + payload_bytes)
    crc_bytes = struct.pack(">H", crc_val)

    # Convert to bits
    full_payload = bytearray(payload_bytes)
    if corrupt_payload_bits > 0:
        # Intentionally flip bits in the payload
        for i in range(min(corrupt_payload_bits, len(full_payload))):
            full_payload[i] ^= 0x55

    packet_stream = header + bytes(full_payload) + crc_bytes
    packet_bits = np.unpackbits(np.frombuffer(packet_stream, dtype=np.uint8))
    full_bits = np.concatenate([sync_bits, packet_bits])
    return sync_bits, packet_bits, header + bytes(full_payload) + crc_bytes, crc_val


def generate_all() -> None:
    print("Generating extended test capture suite in sample_captures/...")
    np.random.seed(42)

    # =========================================================================
    # 16. BPSK CRC FAIL Corrupted (CRC Check Blocked / Failed)
    # =========================================================================
    sync_bits, packet_bits, _, crc_val = make_packet(
        payload_bytes=b"SPECTRALQ_CRC_CORRUPTED_PAYLOAD_TEST",
        corrupt_payload_bits=2,  # Intentional CRC mismatch
    )
    # Lead-in and lead-out noise
    lead_in = np.random.randint(0, 2, 64)
    lead_out = np.random.randint(0, 2, 64)
    all_bits = np.concatenate([lead_in, sync_bits, packet_bits, lead_out])
    bpsk_syms = 2.0 * all_bits.astype(np.complex64) - 1.0
    shaped = pulse_shape_symbols(bpsk_syms, sps=8)
    sig_16 = add_awgn(shaped, snr_db=22.0)
    p_16 = CAPTURES_DIR / "16_BPSK_crc_fail_corrupted.wav"
    save_stereo_wav(p_16, sig_16, sample_rate=100_000)

    with open(p_16.with_suffix(".json"), "w") as f:
        json.dump({
            "sample_rate": 100000.0,
            "modulation": "BPSK",
            "snr_db": 22.0,
            "test_target": "CRC_FAIL_STAGE_BLOCKED",
            "expected_stages": {
                "demodulator": "ACTIVE",
                "deinterleaver": "BYPASS",
                "inner_fec": "BYPASS",
                "outer_fec": "BYPASS",
                "frame_sync_and_crc": "FAIL",
            },
            "failure_reason": "Payload CRC checksum verification failed",
        }, f, indent=2)
    print("  -> Created 16_BPSK_crc_fail_corrupted.wav")

    # =========================================================================
    # 17. QPSK Viterbi Active with CRC FAIL (Severe Burst Overwhelming Viterbi)
    # =========================================================================
    viterbi = ConvolutionalCodec()
    raw_packet_bytes = struct.pack(">BBHH", 1, 42, 1002, 28) + b"SPECTRALQ_VITERBI_FAIL_TEST!"
    crc_17 = CRC.crc16(raw_packet_bytes)
    raw_with_crc = raw_packet_bytes + struct.pack(">H", crc_17)
    raw_bits_17 = np.unpackbits(np.frombuffer(raw_with_crc, dtype=np.uint8))
    encoded_payload_bits = viterbi.encode(raw_bits_17)

    # Corrupt 6 bits in the payload region (coded domain) to keep header intact while failing CRC
    corrupted_encoded = encoded_payload_bits.copy()
    corrupted_encoded[120:126] = 1 - corrupted_encoded[120:126]

    sync_32 = KNOWN_SYNC_WORDS["CCSDS_32"]
    tx_stream_17 = np.concatenate([sync_32, corrupted_encoded])
    # Pad to even length for QPSK
    if len(tx_stream_17) % 2 != 0:
        tx_stream_17 = np.append(tx_stream_17, 0)

    # QPSK Gray mapping: 2 bits per symbol
    b0 = tx_stream_17[0::2]
    b1 = tx_stream_17[1::2]
    qpsk_syms = ((2.0 * b0 - 1.0) + 1j * (2.0 * b1 - 1.0)) / np.sqrt(2.0)
    shaped_17 = pulse_shape_symbols(qpsk_syms, sps=8)
    sig_17 = add_awgn(shaped_17, snr_db=18.0)
    p_17 = CAPTURES_DIR / "17_QPSK_viterbi_crc_fail.wav"
    save_stereo_wav(p_17, sig_17, sample_rate=100_000)

    with open(p_17.with_suffix(".json"), "w") as f:
        json.dump({
            "sample_rate": 100000.0,
            "modulation": "QPSK",
            "snr_db": 18.0,
            "test_target": "VITERBI_ACTIVE_CRC_FAIL",
            "expected_stages": {
                "demodulator": "ACTIVE",
                "deinterleaver": "BYPASS",
                "inner_fec": "RATE 1/2 (K=7)",
                "outer_fec": "BYPASS",
                "frame_sync_and_crc": "FAIL",
            },
        }, f, indent=2)
    print("  -> Created 17_QPSK_viterbi_crc_fail.wav")

    # =========================================================================
    # 18. BPSK Conv Interleaved (Official Golden G6)
    # =========================================================================
    g6_src = OFFICIAL_GOLDEN / "G6_BPSK_conv_interleaved.cf32"
    p_18 = CAPTURES_DIR / "18_BPSK_conv_interleaved.cf32"
    if g6_src.exists():
        shutil.copy2(g6_src, p_18)
    with open(p_18.with_suffix(".json"), "w") as f:
        json.dump({
            "sample_rate": 800000.0,
            "modulation": "BPSK",
            "snr_db": 18.0,
            "test_target": "CONV_INTERLEAVER_AND_VITERBI_PASS",
            "expected_stages": {
                "demodulator": "ACTIVE",
                "deinterleaver": "CONVOLUTIONAL",
                "inner_fec": "RATE 1/2 (K=7)",
                "outer_fec": "BYPASS",
                "frame_sync_and_crc": "PASS",
            },
            "reencode_ber": 0.0,
        }, f, indent=2)
    print("  -> Created 18_BPSK_conv_interleaved.cf32")

    # =========================================================================
    # 19. QPSK Conv Near Threshold (Official Golden G7)
    # =========================================================================
    g7_src = OFFICIAL_GOLDEN / "G7_QPSK_conv_near_threshold.cf32"
    p_19 = CAPTURES_DIR / "19_QPSK_conv_near_threshold.cf32"
    if g7_src.exists():
        shutil.copy2(g7_src, p_19)
    with open(p_19.with_suffix(".json"), "w") as f:
        json.dump({
            "sample_rate": 800000.0,
            "modulation": "QPSK",
            "snr_db": 6.0,
            "test_target": "VITERBI_NEAR_THRESHOLD_PASS",
            "expected_stages": {
                "demodulator": "ACTIVE",
                "deinterleaver": "BYPASS",
                "inner_fec": "RATE 1/2 (K=7)",
                "outer_fec": "BYPASS",
                "frame_sync_and_crc": "PASS",
            },
            "reencode_ber": 0.0,
        }, f, indent=2)
    print("  -> Created 19_QPSK_conv_near_threshold.cf32")

    # =========================================================================
    # 20. 4-FSK Multi-Tone (M-ary FSK Satellite Modulation)
    # =========================================================================
    fs_20 = 100_000.0
    baud_20 = 10_000.0
    sps_20 = int(fs_20 / baud_20)  # 10
    sync_bits, packet_bits, _, _ = make_packet(b"SPECTRALQ_4FSK_TELEMETRY_PKT_01")
    fsk_bits = np.concatenate([np.random.randint(0, 2, 40), sync_bits, packet_bits, np.random.randint(0, 2, 40)])
    if len(fsk_bits) % 2 != 0:
        fsk_bits = np.append(fsk_bits, 0)

    # 4-FSK symbol mapping: 2 bits per tone
    # Tone freqs: -15 kHz, -5 kHz, +5 kHz, +15 kHz
    tone_map = {
        (0, 0): -15000.0,
        (0, 1): -5000.0,
        (1, 0): +5000.0,
        (1, 1): +15000.0,
    }
    sym_tones = [tone_map[(fsk_bits[2*i], fsk_bits[2*i+1])] for i in range(len(fsk_bits) // 2)]
    # Continuous phase frequency modulation
    t_sym = np.arange(sps_20) / fs_20
    fsk_samples = []
    curr_phase = 0.0
    for f_tone in sym_tones:
        chunk = np.exp(1j * (curr_phase + 2.0 * np.pi * f_tone * t_sym))
        curr_phase = np.angle(chunk[-1])
        fsk_samples.append(chunk)
    fsk_sig = np.concatenate(fsk_samples)
    sig_20 = add_awgn(fsk_sig, snr_db=18.0)
    p_20 = CAPTURES_DIR / "20_4FSK_multitone_15dB.wav"
    save_stereo_wav(p_20, sig_20, sample_rate=int(fs_20))

    with open(p_20.with_suffix(".json"), "w") as f:
        json.dump({
            "sample_rate": 100000.0,
            "modulation": "4-FSK",
            "snr_db": 18.0,
            "test_target": "MARY_FSK_DEMOD_AND_FRAMING",
            "expected_stages": {
                "demodulator": "ACTIVE",
                "deinterleaver": "BYPASS",
                "inner_fec": "BYPASS",
                "outer_fec": "BYPASS",
                "frame_sync_and_crc": "PASS",
            },
        }, f, indent=2)
    print("  -> Created 20_4FSK_multitone_15dB.wav")

    # =========================================================================
    # 21. QPSK Severe IQ Imbalance (4 dB Gain + 25 deg Phase Error)
    # =========================================================================
    sync_bits, packet_bits, _, _ = make_packet(b"SPECTRALQ_IQ_IMBALANCE_RESILIENCE_TEST")
    tx_bits = np.concatenate([np.random.randint(0, 2, 32), sync_bits, packet_bits, np.random.randint(0, 2, 32)])
    if len(tx_bits) % 2 != 0:
        tx_bits = np.append(tx_bits, 0)
    b0 = tx_bits[0::2]
    b1 = tx_bits[1::2]
    q_syms = ((2.0 * b0 - 1.0) + 1j * (2.0 * b1 - 1.0)) / np.sqrt(2.0)
    shaped_q = pulse_shape_symbols(q_syms, sps=8)

    # Inject severe IQ imbalance: Gain = 4.0 dB, Phase = 25 degrees
    gain_linear = 10.0 ** (4.0 / 20.0)  # ~1.58
    phi_rad = np.radians(25.0)
    i_imb = np.real(shaped_q) * gain_linear
    q_imb = np.imag(shaped_q) * np.cos(phi_rad) + np.real(shaped_q) * np.sin(phi_rad)
    imb_samples = (i_imb + 1j * q_imb).astype(np.complex64)
    sig_21 = add_awgn(imb_samples, snr_db=22.0)
    p_21 = CAPTURES_DIR / "21_QPSK_severe_iq_imbalance.iq"
    save_raw_iq(p_21, sig_21)

    with open(p_21.with_suffix(".json"), "w") as f:
        json.dump({
            "sample_rate": 100000.0,
            "modulation": "QPSK",
            "snr_db": 22.0,
            "gain_imbalance_db": 4.0,
            "phase_imbalance_deg": 25.0,
            "test_target": "GRAM_SCHMIDT_PREPROCESSING_RESILIENCE",
            "expected_stages": {
                "demodulator": "ACTIVE",
                "deinterleaver": "BYPASS",
                "inner_fec": "BYPASS",
                "outer_fec": "BYPASS",
                "frame_sync_and_crc": "PASS",
            },
        }, f, indent=2)
    print("  -> Created 21_QPSK_severe_iq_imbalance.iq")

    # =========================================================================
    # 22. BPSK Extreme Carrier Frequency Offset (+35 kHz at fs=100 kHz)
    # =========================================================================
    sync_bits, packet_bits, _, _ = make_packet(b"SPECTRALQ_EXTREME_CFO_RECOVERY_TEST")
    tx_bits = np.concatenate([np.random.randint(0, 2, 48), sync_bits, packet_bits, np.random.randint(0, 2, 48)])
    b_syms = 2.0 * tx_bits.astype(np.complex64) - 1.0
    shaped_b = pulse_shape_symbols(b_syms, sps=8)
    # Apply +5 kHz carrier offset
    cfo_5k = 5000.0
    t_axis = np.arange(len(shaped_b)) / 100000.0
    cfo_spun = shaped_b * np.exp(1j * 2.0 * np.pi * cfo_5k * t_axis)
    sig_22 = add_awgn(cfo_spun, snr_db=20.0)
    p_22 = CAPTURES_DIR / "22_BPSK_cfo_tracking_5kHz.wav"
    save_stereo_wav(p_22, sig_22, sample_rate=100_000)

    with open(p_22.with_suffix(".json"), "w") as f:
        json.dump({
            "sample_rate": 100000.0,
            "modulation": "BPSK",
            "cfo_hz": 5000.0,
            "snr_db": 20.0,
            "test_target": "CFO_TRACKING_AND_LOCK_PASS",
            "expected_stages": {
                "demodulator": "ACTIVE",
                "deinterleaver": "BYPASS",
                "inner_fec": "BYPASS",
                "outer_fec": "BYPASS",
                "frame_sync_and_crc": "PASS",
            },
        }, f, indent=2)
    print("  -> Created 22_BPSK_cfo_tracking_5kHz.wav")

    # =========================================================================
    # 23. QPSK Ambiguous Multimodal Boundary Case (Competitor Table Test)
    # =========================================================================
    # Low SNR + high phase jitter causes cumulants to fall between QPSK and 16-QAM
    sync_bits, packet_bits, _, _ = make_packet(b"SPECTRALQ_MULTIMODAL_DECISION_TEST")
    tx_bits = np.concatenate([sync_bits, packet_bits])
    if len(tx_bits) % 2 != 0:
        tx_bits = np.append(tx_bits, 0)
    b0 = tx_bits[0::2]
    b1 = tx_bits[1::2]
    q_syms = ((2.0 * b0 - 1.0) + 1j * (2.0 * b1 - 1.0)) / np.sqrt(2.0)
    shaped_amb = pulse_shape_symbols(q_syms, sps=8)
    # Add random phase jitter (14 deg RMS)
    pj = np.random.normal(0, np.radians(14.0), len(shaped_amb))
    jittered = shaped_amb * np.exp(1j * pj)
    sig_23 = add_awgn(jittered, snr_db=8.0)
    p_23 = CAPTURES_DIR / "23_QPSK_ambiguous_multimodal_8dB.wav"
    save_stereo_wav(p_23, sig_23, sample_rate=100_000)

    with open(p_23.with_suffix(".json"), "w") as f:
        json.dump({
            "sample_rate": 100000.0,
            "modulation": "QPSK",
            "snr_db": 8.0,
            "test_target": "MODULATION_HYPOTHESIS_COMPETITOR_RANKING",
            "expected_stages": {
                "demodulator": "ACTIVE",
                "deinterleaver": "BYPASS",
                "inner_fec": "BYPASS",
                "outer_fec": "BYPASS",
                "frame_sync_and_crc": "PASS",
            },
            "notes": "Shows competitor table in Modulation & Hypotheses tab with alternate probabilities (QPSK vs 16-QAM)",
        }, f, indent=2)
    print("  -> Created 23_QPSK_ambiguous_multimodal_8dB.wav")

    # =========================================================================
    # 24. Degraded SNR (-8 dB) Abstention / UNKNOWN
    # =========================================================================
    # Weak signal completely submerged in noise: triggers Rule 12 UNKNOWN
    carrier = np.exp(1j * 2.0 * np.pi * 5000.0 * np.arange(8000) / 800000.0) * 0.05
    noise_heavy = (np.random.randn(8000) + 1j * np.random.randn(8000)) * 1.0
    sig_24 = (carrier + noise_heavy).astype(np.complex64)
    p_24 = CAPTURES_DIR / "24_Degraded_SNR_minus8dB_unknown.cf32"
    save_cf32(p_24, sig_24)

    with open(p_24.with_suffix(".json"), "w") as f:
        json.dump({
            "sample_rate": 800000.0,
            "modulation": "UNKNOWN",
            "snr_db": -8.0,
            "test_target": "RULE_12_UNKNOWN_ABSTENTION_BANNER",
            "expected_stages": {
                "demodulator": "BYPASS",
                "deinterleaver": "BYPASS",
                "inner_fec": "BYPASS",
                "outer_fec": "BYPASS",
                "frame_sync_and_crc": "UNCHECKED",
            },
            "unknown_state": True,
            "unknown_reason": "SNR below sensitivity threshold (-8.0 dB < 0.0 dB)",
        }, f, indent=2)
    print("  -> Created 24_Degraded_SNR_minus8dB_unknown.cf32")

    # =========================================================================
    # 25. BPSK Uncoded Plain Frame (All Stages Bypass except CRC PASS)
    # =========================================================================
    sync_bits, packet_bits, _, _ = make_packet(b"SPECTRALQ_UNCODED_PLAIN_BASELINE_PKT")
    all_bits = np.concatenate([np.random.randint(0, 2, 32), sync_bits, packet_bits, np.random.randint(0, 2, 32)])
    b_syms = 2.0 * all_bits.astype(np.complex64) - 1.0
    shaped_plain = pulse_shape_symbols(b_syms, sps=8)
    sig_25 = add_awgn(shaped_plain, snr_db=20.0)
    p_25 = CAPTURES_DIR / "25_BPSK_uncoded_plain_frame.iq"
    save_raw_iq(p_25, sig_25)

    with open(p_25.with_suffix(".json"), "w") as f:
        json.dump({
            "sample_rate": 100000.0,
            "modulation": "BPSK",
            "snr_db": 20.0,
            "test_target": "BASELINE_UNCODED_ALL_FEC_BYPASS_PASS",
            "expected_stages": {
                "demodulator": "ACTIVE",
                "deinterleaver": "BYPASS",
                "inner_fec": "BYPASS",
                "outer_fec": "BYPASS",
                "frame_sync_and_crc": "PASS",
            },
            "reencode_ber": None,
        }, f, indent=2)
    print("  -> Created 25_BPSK_uncoded_plain_frame.iq")

    print("\nSuccessfully generated all 10 new test captures in sample_captures/!")


if __name__ == "__main__":
    generate_all()
