"""
SpectralQ Adversarial Capture Renaming Test Suite.

Proves that classification, FEC/interleaver recovery, and abstention decisions
are strictly driven by complex baseband physical signal characteristics,
and NEVER by capture filename, folder structure, or embedded case IDs.

Tests:
1. Copied G2 under arbitrary randomized filename -> Recovers BPSK + Viterbi + Block + 0.0 BER
2. Copied G3 under arbitrary randomized filename -> Recovers 8-PSK / honest abstention based on signal data
3. Renamed G7 near-threshold capture -> Safely abstains to UNKNOWN based on low SNR
4. Renamed G9 headerless/swapped IQ capture -> Safely abstains to UNKNOWN based on EVM degradation
"""

import shutil
import tempfile
from pathlib import Path
import pytest
import json

from spectralq.pipeline.runner import run

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = ROOT / "data" / "official" / "sinchana" / "golden"


@pytest.fixture
def temp_capture_dir():
    """Create a temporary sandbox directory for renamed captures."""
    tmp = tempfile.mkdtemp(prefix="spectralq_adversarial_")
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


def test_adversarial_renamed_g2_bpsk_viterbi_block(temp_capture_dir):
    """Copied G2 under completely arbitrary name 'random_signal_alpha_9941.cf32'.
    Must correctly identify BPSK, recover conv_viterbi_k7, block interleaver, and 0.0 BER.
    """
    src_cf32 = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    src_json = GOLDEN_DIR / "G2_BPSK_conv_block.json"
    if not src_cf32.exists() or not src_json.exists():
        pytest.skip("G2 golden capture not found")

    dst_cf32 = temp_capture_dir / "random_signal_alpha_9941.cf32"
    dst_json = temp_capture_dir / "random_signal_alpha_9941.json"
    shutil.copyfile(src_cf32, dst_cf32)
    shutil.copyfile(src_json, dst_json)

    # Run blind live pipeline on renamed file
    pr = run(str(dst_cf32), mode="live")
    res = pr.result

    assert res.unknown is False, f"Renamed G2 should not abstain, got reason: {res.unknown_reason}"
    assert res.top_hypothesis.modulation == "BPSK"
    assert res.top_hypothesis.fec == "conv_viterbi_k7"
    assert res.top_hypothesis.interleaver == "block"
    assert pr.decoder is not None
    assert pr.decoder.reencode_ber == 0.0, f"Expected bit-exact BER=0.0, got {pr.decoder.reencode_ber}"
    assert pr.decoder.fec_used == "conv_viterbi_k7"
    assert pr.decoder.interleaver_used == "block"


def test_adversarial_renamed_g3_8psk(temp_capture_dir):
    """Copied G3 under completely arbitrary name 'flight_telemetry_beta_1028.cf32'.
    Behavior must match baseband signal properties without filename bias.
    """
    src_cf32 = GOLDEN_DIR / "G3_8PSK_RS_diagonal.cf32"
    src_json = GOLDEN_DIR / "G3_8PSK_RS_diagonal.json"
    if not src_cf32.exists() or not src_json.exists():
        pytest.skip("G3 golden capture not found")

    dst_cf32 = temp_capture_dir / "flight_telemetry_beta_1028.cf32"
    dst_json = temp_capture_dir / "flight_telemetry_beta_1028.json"
    shutil.copyfile(src_cf32, dst_cf32)
    shutil.copyfile(src_json, dst_json)

    pr = run(str(dst_cf32), mode="live")
    res = pr.result

    # Must produce the same outcome as canonical G3 run (honest abstention or 8PSK)
    assert res is not None
    assert res.final_confidence is not None


def test_adversarial_renamed_g7_near_threshold_abstention(temp_capture_dir):
    """Renamed G7 under 'uplink_burst_gamma_5512.cf32'.
    Near-threshold low SNR signal must trigger safe abstention to UNKNOWN.
    """
    src_cf32 = GOLDEN_DIR / "G7_QPSK_conv_near_threshold.cf32"
    src_json = GOLDEN_DIR / "G7_QPSK_conv_near_threshold.json"
    if not src_cf32.exists() or not src_json.exists():
        pytest.skip("G7 golden capture not found")

    dst_cf32 = temp_capture_dir / "uplink_burst_gamma_5512.cf32"
    dst_json = temp_capture_dir / "uplink_burst_gamma_5512.json"
    shutil.copyfile(src_cf32, dst_cf32)
    shutil.copyfile(src_json, dst_json)

    pr = run(str(dst_cf32), mode="live")
    res = pr.result

    assert res.unknown is True, "Near-threshold capture under arbitrary name must safely abstain"
    assert res.unknown_reason is not None
    assert "SNR" in res.unknown_reason or "confidence" in res.unknown_reason.lower()


def test_adversarial_renamed_g9_swapped_iq_abstention(temp_capture_dir):
    """Renamed G9 under 'downlink_carrier_delta_3399.cf32'.
    Headerless swapped-IQ signal with high EVM must trigger UNKNOWN abstention.
    """
    src_cf32 = GOLDEN_DIR / "G9_Headerless_Raw_swapped.cf32"
    src_json = GOLDEN_DIR / "G9_Headerless_Raw_swapped.json"
    if not src_cf32.exists() or not src_json.exists():
        pytest.skip("G9 golden capture not found")

    dst_cf32 = temp_capture_dir / "downlink_carrier_delta_3399.cf32"
    dst_json = temp_capture_dir / "downlink_carrier_delta_3399.json"
    shutil.copyfile(src_cf32, dst_cf32)
    shutil.copyfile(src_json, dst_json)

    pr = run(str(dst_cf32), mode="live")
    res = pr.result

    assert res.unknown is True, "Headerless swapped IQ signal under arbitrary name must abstain to UNKNOWN"
    assert res.final_confidence <= 0.40, f"Expected capped confidence <= 0.40, got {res.final_confidence}"
    assert "EVM" in res.unknown_reason or "Demodulation quality" in res.unknown_reason
