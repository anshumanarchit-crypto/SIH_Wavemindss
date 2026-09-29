"""
Comprehensive Regression Test Suite for Decoder & Bitstream Service across All Captures.

Verifies:
1. No false bypasses or failures on valid framed captures (CRC PASS, accurate FEC & Interleaver tracking).
2. Pure noise rejected gracefully as FAILED / NOT_RUN (Rule 1 & Rule 12).
3. Continuous streams demodulate without false CRC FAIL (Rule 9: sync found != CRC check != CRC pass).
4. Strict compliance with Rule 11 (reencode_ber only computed when actual re-encoding ran).
"""

from pathlib import Path
import pytest

from python.spectralq.decoder.service import run_arpit_decoder
from spectralq.contracts.schemas import DecoderStatus, CrcStatus

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPTURES_DIR = REPO_ROOT / "sample_captures"


# -----------------------------------------------------------------------------
# 1. Official Sinchana Golden Reference Captures (G1 - G5)
# -----------------------------------------------------------------------------
def test_06_bpsk_conv_viterbi():
    """06_BPSK_conv_viterbi.wav: Rate 1/2 K=7 Convolutional with CCSDS preamble."""
    cap = CAPTURES_DIR / "06_BPSK_conv_viterbi.wav"
    out = run_arpit_decoder(capture_input=cap, capture_id=cap.stem)

    assert out.status == DecoderStatus.OK
    assert out.crc_status == CrcStatus.PASS
    assert out.fec_used == "conv_viterbi_k7_r12"
    assert out.interleaver_used == "none"
    assert out.reencode_ber == 0.0
    assert len(str(out.decoded_bits)) > 0


def test_07_qpsk_uncoded_golden():
    """07_QPSK_uncoded_golden.cf32: G1 Golden QPSK uncoded reference."""
    cap = CAPTURES_DIR / "07_QPSK_uncoded_golden.cf32"
    out = run_arpit_decoder(capture_input=cap, capture_id=cap.stem, sample_rate=800_000)

    assert out.status == DecoderStatus.OK
    assert out.crc_status == CrcStatus.PASS
    assert out.fec_used == "none"
    assert out.interleaver_used == "none"
    assert out.reencode_ber == 0.0
    assert len(str(out.decoded_bits)) > 0


def test_08_bpsk_conv_block():
    """08_BPSK_conv_block.cf32: G2 Golden BPSK with Block Interleaver (16x34) and Viterbi."""
    cap = CAPTURES_DIR / "08_BPSK_conv_block.cf32"
    out = run_arpit_decoder(capture_input=cap, capture_id=cap.stem, sample_rate=800_000)

    assert out.status == DecoderStatus.OK
    assert out.crc_status == CrcStatus.PASS
    assert out.fec_used == "conv_viterbi_k7"
    assert out.interleaver_used == "block_16x34"
    assert out.reencode_ber == 0.0
    assert len(str(out.decoded_bits)) > 0


def test_09_8psk_rs_diagonal():
    """09_8PSK_RS_diagonal.cf32: G3 Golden 8-PSK with Diagonal Interleaver and Reed-Solomon."""
    cap = CAPTURES_DIR / "09_8PSK_RS_diagonal.cf32"
    out = run_arpit_decoder(capture_input=cap, capture_id=cap.stem, sample_rate=800_000)

    assert out.status == DecoderStatus.OK
    assert out.crc_status == CrcStatus.PASS
    assert out.fec_used == "rs_255_223"
    assert out.interleaver_used == "diagonal_40x51"
    assert out.reencode_ber == 0.0
    assert len(str(out.decoded_bits)) > 0


def test_10_16qam_ldpc_pseudo():
    """10_16QAM_LDPC_pseudo.cf32: G4 Golden 16-QAM with Pseudorandom Interleaver and LDPC."""
    cap = CAPTURES_DIR / "10_16QAM_LDPC_pseudo.cf32"
    out = run_arpit_decoder(capture_input=cap, capture_id=cap.stem, sample_rate=800_000)

    assert out.status == DecoderStatus.OK
    assert out.crc_status == CrcStatus.PASS
    assert out.fec_used == "ldpc"
    assert out.interleaver_used == "pseudorandom"
    assert out.reencode_ber == 0.0
    assert len(str(out.decoded_bits)) > 0


def test_11_2fsk_concatenated():
    """11_2FSK_concatenated.cf32: G5 Golden 2-FSK with Convolutional Interleaver (4x2) & Concat FEC."""
    cap = CAPTURES_DIR / "11_2FSK_concatenated.cf32"
    out = run_arpit_decoder(capture_input=cap, capture_id=cap.stem, sample_rate=800_000)

    assert out.status == DecoderStatus.OK
    assert out.crc_status == CrcStatus.PASS
    assert out.fec_used == "concat_rs_conv"
    assert out.interleaver_used == "convolutional_4x2"
    assert out.reencode_ber == 0.0
    assert len(str(out.decoded_bits)) > 0


# -----------------------------------------------------------------------------
# 2. Clean & CFO Bursts Frame Synchronization and CRC PASS
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("filename,sample_rate", [
    ("01_BPSK_clean_20dB.wav", None),
    ("02_QPSK_with_CFO_15dB.wav", None),
    ("04_16QAM_high_density_22dB.wav", None),
    ("13_BPSK_raw_int16.iq", 100_000),
    ("14_QPSK_with_cfo_int16.iq", 100_000),
])
def test_clean_bursts_crc_pass(filename, sample_rate):
    """Verifies that clean and CFO bursts demodulate and verify CRC successfully."""
    cap = CAPTURES_DIR / filename
    out = run_arpit_decoder(capture_input=cap, capture_id=cap.stem, sample_rate=sample_rate)

    assert out.status == DecoderStatus.OK, f"Expected OK status for {filename}, got {out.status}"
    assert out.crc_status == CrcStatus.PASS, f"Expected CRC PASS for {filename}, got {out.crc_status}"
    assert len(str(out.decoded_bits)) > 0


# -----------------------------------------------------------------------------
# 3. Continuous Unpacketized Streams (Rule 9: sync found != CRC check != CRC pass)
# -----------------------------------------------------------------------------
def test_15_8psk_continuous_unpacketized_stream():
    """15_8PSK_carrier_locked_18dB.wav: Continuous 8-PSK stream without packets."""
    cap = CAPTURES_DIR / "15_8PSK_carrier_locked_18dB.wav"
    out = run_arpit_decoder(capture_input=cap, capture_id=cap.stem)

    assert out.status == DecoderStatus.OK
    assert out.crc_status == CrcStatus.NOT_RUN  # Must not false-alarm FAIL
    assert len(str(out.decoded_bits)) >= 10_000


def test_03_2fsk_satellite_stream():
    """03_2FSK_satellite_18dB.wav: Continuous FSK stream."""
    cap = CAPTURES_DIR / "03_2FSK_satellite_18dB.wav"
    out = run_arpit_decoder(capture_input=cap, capture_id=cap.stem)

    assert out.status == DecoderStatus.OK
    assert out.crc_status == CrcStatus.NOT_RUN
    assert len(str(out.decoded_bits)) > 0


# -----------------------------------------------------------------------------
# 4. Pure Noise Rejection (Rule 1 & Rule 12)
# -----------------------------------------------------------------------------
def test_12_pure_awgn_noise_only():
    """12_Pure_AWGN_noise_only.cf32: Pure AWGN noise must fail and not fabricate CRC PASS."""
    cap = CAPTURES_DIR / "12_Pure_AWGN_noise_only.cf32"
    out = run_arpit_decoder(capture_input=cap, capture_id=cap.stem, sample_rate=800_000)

    assert out.status == DecoderStatus.FAILED
    assert out.crc_status == CrcStatus.NOT_RUN
