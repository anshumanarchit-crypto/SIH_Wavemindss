"""
Tests for Phase 7: Re-encode BER Integrity Contract Enforcement.
Verifies that:
1. When FEC decoding succeeds cleanly without bit errors, re-encoded bits match
   received hard bits exactly, yielding reencode_ber == 0.0.
2. When FEC decoding corrects received bit errors, re-encoding the decoded payload
   produces the corrected codeword, and comparing against received noisy hard bits
   yields a strictly positive reencode_ber > 0.0 reflecting the exact error count.
3. When transmission is uncoded, or FEC was bypassed, reencode_ber is strictly None
   (never fabricated as 0.0 or derived from EVM / CRC).
"""

from pathlib import Path
import numpy as np
import pytest

from spectralq.fec import (
    LDPCCodec,
    ReedSolomonCodec,
    bits_to_bytes,
    bytes_to_bits,
)
from spectralq.contracts.schemas import DecoderStatus, CrcStatus
from spectralq.decoder.service import run_arpit_decoder


def test_ldpc_reencode_ber_perfect():
    """LDPC decoding with no errors produces reencode_ber == 0.0."""
    codec = LDPCCodec()
    info_bits = np.random.RandomState(42).randint(0, 2, codec.k_info)
    codeword = codec.encode(info_bits)

    decoded, metrics = codec.decode(codeword)
    assert metrics["decoder_success"] is True

    reencoded = codec.encode(decoded)
    ber = float(np.mean(reencoded != codeword))
    assert ber == 0.0


def test_ldpc_reencode_ber_corrected_error():
    """LDPC decoding with a corrected bit error produces reencode_ber > 0.0."""
    codec = LDPCCodec()
    info_bits = np.random.RandomState(42).randint(0, 2, codec.k_info)
    codeword = codec.encode(info_bits)

    # Inject 1 bit error into codeword
    noisy_codeword = codeword.copy()
    error_idx = 7
    noisy_codeword[error_idx] = 1 - noisy_codeword[error_idx]

    decoded, metrics = codec.decode(noisy_codeword)
    assert metrics["decoder_success"] is True
    assert np.array_equal(decoded, info_bits)

    # Re-encode and compute BER against noisy input
    reencoded = codec.encode(decoded)
    ber = float(np.mean(reencoded != noisy_codeword))
    expected_ber = 1.0 / len(codeword)
    assert abs(ber - expected_ber) < 1e-6
    assert ber > 0.0


def test_rs_reencode_ber_perfect():
    """Reed-Solomon RS(255,223) decoding with no errors produces reencode_ber == 0.0."""
    codec = ReedSolomonCodec(n=255, k=223)
    info_bytes = b"A" * 223
    info_bits = bytes_to_bits(info_bytes)
    codeword_bytes = codec.codec.encode(info_bytes)
    codeword_bits = bytes_to_bits(codeword_bytes)

    decoded_bits, metrics = codec.decode(codeword_bits)
    assert metrics["decoder_success"] is True

    reencoded_bytes = codec.codec.encode(bits_to_bytes(decoded_bits))
    reencoded_bits = bytes_to_bits(reencoded_bytes)
    ber = float(np.mean(reencoded_bits != codeword_bits))
    assert ber == 0.0


def test_rs_reencode_ber_corrected_error():
    """Reed-Solomon decoding with corrected byte errors produces reencode_ber > 0.0."""
    codec = ReedSolomonCodec(n=255, k=223)
    info_bytes = b"A" * 223
    codeword_bytes = codec.codec.encode(info_bytes)
    codeword_bits = bytes_to_bits(codeword_bytes)

    # Corrupt 2 bits in the first byte
    noisy_bits = codeword_bits.copy()
    noisy_bits[0] = 1 - noisy_bits[0]
    noisy_bits[1] = 1 - noisy_bits[1]

    decoded_bits, metrics = codec.decode(noisy_bits)
    assert metrics["decoder_success"] is True

    reencoded_bytes = codec.codec.encode(bits_to_bytes(decoded_bits))
    reencoded_bits = bytes_to_bits(reencoded_bytes)
    ber = float(np.mean(reencoded_bits != noisy_bits))
    expected_ber = 2.0 / len(codeword_bits)
    assert abs(ber - expected_ber) < 1e-6
    assert ber > 0.0


def test_uncoded_stream_reencode_ber_is_none():
    """Uncoded captures must report reencode_ber as None, never 0.0."""
    g1_path = Path("data/official/sinchana/golden/G1_QPSK_uncoded.cf32")
    if not g1_path.exists():
        pytest.skip("G1 golden capture not found")

    out = run_arpit_decoder(g1_path, "G1_QPSK", sample_rate=800_000)
    assert out.status == DecoderStatus.OK
    assert out.fec_used == "none"
    assert out.reencode_ber is None
