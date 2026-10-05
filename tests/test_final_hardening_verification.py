"""
Phase 41: Final Hardening Acceptance & Verification Test Suite.
Enforces the 18 mandatory acceptance criteria for evaluator-grade submission:

TEST 1: Candidate BPSK + Conv + Block reaches actual Viterbi.
TEST 2: Candidate BPSK + Conv + Block returns BER 0.
TEST 3: Candidate BPSK + Conv + Convolutional returns BER 0.
TEST 4: Candidate LDPC actually invokes LDPC decoder.
TEST 5: Requested FEC never silently becomes none.
TEST 6: Requested interleaver never silently becomes none.
TEST 7: Candidate winner equals authoritative HypothesisEngine winner.
TEST 8: Multiple modulation families reach real candidate decoder.
TEST 9: File-backed and memory-backed timing propagation are equivalent.
TEST 10: Candidate cache cannot contaminate another candidate.
TEST 11: Truth file never read at runtime.
TEST 12: Renaming golden input does not change prediction.
TEST 13: G7 remains UNKNOWN.
TEST 14: G9 remains UNKNOWN.
TEST 15: G10 remains UNKNOWN.
TEST 16: G8 produces emission candidates.
TEST 17: UNKNOWN confidence semantics are correct.
TEST 18: Candidate decoder behavior is deterministically reproducible.
"""

from pathlib import Path
import json
import tempfile
import shutil
import pytest
import numpy as np

from spectralq.pipeline.runner import run, run_samples
from spectralq.hypothesis.engine import HypothesisEngineV1
from spectralq.hypothesis.candidate import HypothesisCandidate
from spectralq.decoder.service import run_arpit_decoder
from spectralq.contracts.schemas import DecoderStatus, CrcStatus
from core.io import load_signal
from spectralq.features.iq_extractor import iq_to_analysis_contract
from spectralq.dsp.wideband_scanner import scan_wideband_spectrum

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = ROOT / "data" / "official" / "sinchana" / "golden"


def test_1_candidate_bpsk_conv_block_reaches_viterbi():
    """TEST 1: Candidate BPSK + Conv + Block reaches actual Viterbi."""
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    meta_path = GOLDEN_DIR / "G2_BPSK_conv_block.json"
    if not g2_path.exists():
        pytest.skip("G2 capture not found")
    meta = json.loads(meta_path.read_text())
    sig = load_signal(str(g2_path))
    analysis = iq_to_analysis_contract(sig.samples, fs_hz=float(meta["sample_rate"]), capture_id="G2_TEST1")
    out = run_arpit_decoder(
        capture_input=str(g2_path),
        capture_id="G2_TEST1",
        analysis=analysis,
        candidate_modulation="BPSK",
        fec_scheme="conv_viterbi_k7",
        deinterleave_scheme="block",
    )
    assert out.fec_used == "conv_viterbi_k7"
    assert out.interleaver_used == "block"
    assert out.status == DecoderStatus.OK


def test_2_candidate_bpsk_conv_block_returns_ber_zero():
    """TEST 2: Candidate BPSK + Conv + Block returns BER 0."""
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    meta_path = GOLDEN_DIR / "G2_BPSK_conv_block.json"
    if not g2_path.exists():
        pytest.skip("G2 capture not found")
    meta = json.loads(meta_path.read_text())
    sig = load_signal(str(g2_path))
    analysis = iq_to_analysis_contract(sig.samples, fs_hz=float(meta["sample_rate"]), capture_id="G2_TEST2")
    out = run_arpit_decoder(
        capture_input=str(g2_path),
        capture_id="G2_TEST2",
        analysis=analysis,
        candidate_modulation="BPSK",
        fec_scheme="conv_viterbi_k7",
        deinterleave_scheme="block",
    )
    assert out.reencode_ber == 0.0


def test_3_candidate_bpsk_conv_convolutional_returns_ber_zero():
    """TEST 3: Candidate BPSK + Conv + Convolutional returns BER 0 on G6."""
    g6_path = GOLDEN_DIR / "G6_BPSK_conv_interleaved.cf32"
    meta_path = GOLDEN_DIR / "G6_BPSK_conv_interleaved.json"
    if not g6_path.exists():
        pytest.skip("G6 capture not found")
    meta = json.loads(meta_path.read_text())
    sig = load_signal(str(g6_path))
    analysis = iq_to_analysis_contract(sig.samples, fs_hz=float(meta["sample_rate"]), capture_id="G6_TEST3")
    out = run_arpit_decoder(
        capture_input=str(g6_path),
        capture_id="G6_TEST3",
        analysis=analysis,
        candidate_modulation="BPSK",
        fec_scheme="conv_viterbi_k7",
        deinterleave_scheme="convolutional",
    )
    assert out.status == DecoderStatus.OK
    assert out.fec_used == "conv_viterbi_k7"
    assert out.interleaver_used == "convolutional"
    assert out.reencode_ber == 0.0


def test_4_candidate_ldpc_actually_invokes_ldpc():
    """TEST 4: Candidate LDPC actually invokes LDPC decoder."""
    g4_path = GOLDEN_DIR / "G4_16QAM_LDPC_pseudorandom.cf32"
    meta_path = GOLDEN_DIR / "G4_16QAM_LDPC_pseudorandom.json"
    if not g4_path.exists():
        pytest.skip("G4 capture not found")
    meta = json.loads(meta_path.read_text())
    sig = load_signal(str(g4_path))
    analysis = iq_to_analysis_contract(sig.samples, fs_hz=float(meta["sample_rate"]), capture_id="G4_TEST4")
    out = run_arpit_decoder(
        capture_input=str(g4_path),
        capture_id="G4_TEST4",
        analysis=analysis,
        candidate_modulation="16-QAM",
        fec_scheme="ldpc",
        deinterleave_scheme="pseudo-random",
    )
    assert out.fec_used == "ldpc"
    assert out.interleaver_used == "pseudo-random"
    assert out.status == DecoderStatus.OK
    assert out.reencode_ber is not None and out.reencode_ber <= 0.05


def test_5_requested_fec_never_silently_becomes_none():
    """TEST 5: Requested FEC never silently becomes none."""
    noise_iq = (np.random.randn(2048) + 1j * np.random.randn(2048)).astype(np.complex64)
    analysis = iq_to_analysis_contract(noise_iq, fs_hz=100000.0, capture_id="NOISE_TEST5")
    for fec in ["conv_viterbi_k7", "ldpc", "rs_255_223", "concatenated"]:
        out = run_arpit_decoder(
            capture_input=noise_iq,
            capture_id="NOISE_TEST5",
            analysis=analysis,
            candidate_modulation="QPSK",
            fec_scheme=fec,
            deinterleave_scheme="block",
        )
        assert out.fec_used == fec, f"Requested FEC '{fec}' became '{out.fec_used}'"
        assert out.fec_used != "none"
        assert out.status == DecoderStatus.FAILED


def test_6_requested_interleaver_never_silently_becomes_none():
    """TEST 6: Requested interleaver never silently becomes none."""
    noise_iq = (np.random.randn(2048) + 1j * np.random.randn(2048)).astype(np.complex64)
    analysis = iq_to_analysis_contract(noise_iq, fs_hz=100000.0, capture_id="NOISE_TEST6")
    for intl in ["block", "convolutional", "pseudo-random", "diagonal"]:
        out = run_arpit_decoder(
            capture_input=noise_iq,
            capture_id="NOISE_TEST6",
            analysis=analysis,
            candidate_modulation="BPSK",
            fec_scheme="conv_viterbi_k7",
            deinterleave_scheme=intl,
        )
        assert out.interleaver_used == intl, f"Requested interleaver '{intl}' became '{out.interleaver_used}'"


def test_7_candidate_winner_equals_authoritative_engine_winner():
    """TEST 7: Candidate winner equals authoritative HypothesisEngine winner."""
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    if not g2_path.exists():
        pytest.skip("G2 capture not found")
    pr = run(str(g2_path), mode="live")
    assert pr.result.top_hypothesis.modulation == "BPSK"
    assert pr.result.top_hypothesis.fec == "conv_viterbi_k7"
    assert pr.result.top_hypothesis.interleaver == "block"
    assert pr.decoder.fec_used == pr.result.top_hypothesis.fec
    assert pr.decoder.interleaver_used == pr.result.top_hypothesis.interleaver


def test_8_multiple_modulation_families_reach_real_decoder():
    """TEST 8: Multiple modulation families reach real candidate decoder."""
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    if not g2_path.exists():
        pytest.skip("G2 capture not found")
    pr = run(str(g2_path), mode="live")
    assert pr.result.provenance.candidates_decoder_evaluated >= 2
    assert pr.result.provenance.candidates_generated == 175


def test_9_file_and_memory_timing_propagation_equivalent():
    """TEST 9: File-backed and memory-backed timing propagation are equivalent."""
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    meta_path = GOLDEN_DIR / "G2_BPSK_conv_block.json"
    if not g2_path.exists():
        pytest.skip("G2 capture not found")
    meta = json.loads(meta_path.read_text())
    fs = float(meta["sample_rate"])
    sig = load_signal(str(g2_path))
    analysis_file = iq_to_analysis_contract(sig.samples, fs_hz=fs, capture_id="G2_FILE")
    analysis_mem = iq_to_analysis_contract(sig.samples, fs_hz=fs, capture_id="G2_MEM")
    out_file = run_arpit_decoder(
        capture_input=str(g2_path),
        capture_id="G2_FILE",
        analysis=analysis_file,
        candidate_modulation="BPSK",
        fec_scheme="conv_viterbi_k7",
        deinterleave_scheme="block",
    )
    out_mem = run_arpit_decoder(
        capture_input=sig.samples,
        capture_id="G2_MEM",
        analysis=analysis_mem,
        sample_rate=fs,
        candidate_modulation="BPSK",
        fec_scheme="conv_viterbi_k7",
        deinterleave_scheme="block",
    )
    assert out_file.status == out_mem.status == DecoderStatus.OK
    assert out_file.reencode_ber == out_mem.reencode_ber == 0.0
    assert out_file.decoded_bits == out_mem.decoded_bits


def test_10_candidate_cache_cannot_contaminate_another_candidate():
    """TEST 10: Candidate cache cannot contaminate another candidate."""
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    meta_path = GOLDEN_DIR / "G2_BPSK_conv_block.json"
    if not g2_path.exists():
        pytest.skip("G2 capture not found")
    meta = json.loads(meta_path.read_text())
    sig = load_signal(str(g2_path))
    analysis = iq_to_analysis_contract(sig.samples, fs_hz=float(meta["sample_rate"]), capture_id="G2_CACHE_TEST")

    # Candidate A: BPSK + conv + block (should succeed with BER 0.0)
    out_a1 = run_arpit_decoder(
        capture_input=sig.samples,
        capture_id="G2_A1",
        analysis=analysis,
        sample_rate=float(meta["sample_rate"]),
        candidate_modulation="BPSK",
        fec_scheme="conv_viterbi_k7",
        deinterleave_scheme="block",
    )
    # Candidate B: BPSK + none + none (uncoded)
    out_b = run_arpit_decoder(
        capture_input=sig.samples,
        capture_id="G2_B",
        analysis=analysis,
        sample_rate=float(meta["sample_rate"]),
        candidate_modulation="BPSK",
        fec_scheme="none",
        deinterleave_scheme="none",
    )
    # Candidate A again: must be identical to A1
    out_a2 = run_arpit_decoder(
        capture_input=sig.samples,
        capture_id="G2_A2",
        analysis=analysis,
        sample_rate=float(meta["sample_rate"]),
        candidate_modulation="BPSK",
        fec_scheme="conv_viterbi_k7",
        deinterleave_scheme="block",
    )

    assert out_a1.fec_used == "conv_viterbi_k7"
    assert out_a1.reencode_ber == 0.0
    assert out_b.fec_used == "none"
    assert out_b.reencode_ber is None
    assert out_a2.fec_used == "conv_viterbi_k7"
    assert out_a2.reencode_ber == 0.0
    assert out_a1.decoded_bits == out_a2.decoded_bits


def test_11_truth_file_never_read_at_runtime(monkeypatch):
    """TEST 11: Truth file never read at runtime."""
    import builtins
    orig_open = builtins.open

    def guarded_open(file, *args, **kwargs):
        s = str(file)
        if "truth.json" in s.lower():
            raise AssertionError(f"Truth file read attempted: {file}")
        return orig_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    if g2_path.exists():
        pr = run(str(g2_path), mode="live")
        assert pr.result.top_hypothesis.modulation == "BPSK"


def test_12_renaming_golden_input_does_not_change_prediction():
    """TEST 12: Renaming golden input does not change prediction."""
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    g2_json = GOLDEN_DIR / "G2_BPSK_conv_block.json"
    if not g2_path.exists() or not g2_json.exists():
        pytest.skip("G2 capture not found")
    with tempfile.TemporaryDirectory() as td:
        adversarial_path = Path(td) / "adversarial_random_sig_xyz.cf32"
        adversarial_json = Path(td) / "adversarial_random_sig_xyz.json"
        shutil.copy2(g2_path, adversarial_path)
        shutil.copy2(g2_json, adversarial_json)
        pr_orig = run(str(g2_path), mode="live")
        pr_adv = run(str(adversarial_path), mode="live")
        assert pr_orig.result.top_hypothesis.modulation == pr_adv.result.top_hypothesis.modulation
        assert pr_orig.result.top_hypothesis.fec == pr_adv.result.top_hypothesis.fec
        assert pr_orig.result.top_hypothesis.interleaver == pr_adv.result.top_hypothesis.interleaver


def test_13_g7_remains_unknown():
    """TEST 13: G7 remains UNKNOWN."""
    g7_path = GOLDEN_DIR / "G7_QPSK_conv_near_threshold.cf32"
    if not g7_path.exists():
        pytest.skip("G7 capture not found")
    pr = run(str(g7_path), mode="live")
    assert pr.result.unknown is True
    assert pr.result.unknown_reason is not None


def test_14_g9_remains_unknown():
    """TEST 14: G9 remains UNKNOWN."""
    g9_path = GOLDEN_DIR / "G9_Headerless_Raw_swapped.cf32"
    if not g9_path.exists():
        pytest.skip("G9 capture not found")
    pr = run(str(g9_path), mode="live")
    assert pr.result.unknown is True
    assert pr.result.unknown_reason is not None


def test_15_g10_remains_unknown():
    """TEST 15: G10 remains UNKNOWN."""
    g10_path = GOLDEN_DIR / "G10_Noise_Only_AWGN.cf32"
    if not g10_path.exists():
        pytest.skip("G10 capture not found")
    pr = run(str(g10_path), mode="live")
    assert pr.result.unknown is True
    assert pr.result.unknown_reason is not None


def test_16_g8_produces_emission_candidates():
    """TEST 16: G8 produces emission candidates."""
    g8_path = GOLDEN_DIR / "G8_Wideband_4_emissions.cf32"
    if not g8_path.exists():
        pytest.skip("G8 capture not found")
    pr = run(str(g8_path), mode="live")
    assert pr.result.result_type == "MULTI_EMISSION"
    assert pr.result.emissions is not None
    assert len(pr.result.emissions) >= 2


def test_17_unknown_confidence_semantics_are_correct():
    """TEST 17: UNKNOWN confidence semantics are correct."""
    g10_path = GOLDEN_DIR / "G10_Noise_Only_AWGN.cf32"
    if not g10_path.exists():
        pytest.skip("G10 capture not found")
    pr = run(str(g10_path), mode="live")
    assert pr.result.unknown is True
    assert 0.0 <= pr.result.final_confidence <= 1.0


def test_18_candidate_decoder_reproducibility():
    """TEST 18: Candidate decoder behavior is deterministically reproducible."""
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    if not g2_path.exists():
        pytest.skip("G2 capture not found")
    pr1 = run(str(g2_path), mode="live", seed=42)
    pr2 = run(str(g2_path), mode="live", seed=42)
    assert pr1.result.top_hypothesis.modulation == pr2.result.top_hypothesis.modulation == "BPSK"
    assert pr1.result.top_hypothesis.fec == pr2.result.top_hypothesis.fec == "conv_viterbi_k7"
    assert pr1.result.top_hypothesis.interleaver == pr2.result.top_hypothesis.interleaver == "block"
    assert pr1.decoder.reencode_ber == pr2.decoder.reencode_ber == 0.0
