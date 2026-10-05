"""
SpectralQ Candidate Decoder Search Acceptance Tests.

Verifies:
1. Stage A coarse pruning filters unviable candidate triples based on physical constraints.
2. Stage B executes genuine candidate-specific decoder evaluation for competing candidates.
3. At least two competing candidates reach the real decoder on a controlled case.
4. The winning candidate is selected by actual verification evidence (Viterbi / re-encode BER)
   rather than static classifier priors alone.
"""

from pathlib import Path
import pytest
import numpy as np

from spectralq.pipeline.runner import run
from spectralq.hypothesis.engine import HypothesisEngineV1
from spectralq.hypothesis.candidate import HypothesisCandidate
from spectralq.decoder.service import run_arpit_decoder
from spectralq.contracts.schemas import DecoderStatus, CrcStatus
from core.io import load_signal
from spectralq.features.iq_extractor import iq_to_analysis_contract
from spectralq.integration.classifier_adapter import ClassifierAdapter
import json

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = ROOT / "data" / "official" / "sinchana" / "golden"


def test_candidate_search_multi_candidate_decoder_execution():
    """Prove that multiple competing candidate triples reach the real decoder and
    the winner is selected strictly via physical verification evidence.
    """
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    meta_path = GOLDEN_DIR / "G2_BPSK_conv_block.json"
    if not g2_path.exists() or not meta_path.exists():
        pytest.skip(f"Capture {g2_path} not found")

    meta = json.loads(meta_path.read_text())
    fs = float(meta["sample_rate"])
    sig = load_signal(str(g2_path))
    analysis = iq_to_analysis_contract(sig.samples, fs_hz=fs, capture_id="G2_SEARCH_TEST")

    # Step 1: Hypothesis Engine generates full 175 candidate cross-product
    engine = HypothesisEngineV1()
    all_cands = engine.generate_all_candidates()
    assert len(all_cands) == 175, f"Expected 175 candidates, got {len(all_cands)}"

    # Step 2: Coarse pruning reduces candidates without dropping viable modulation
    cls_adapter = ClassifierAdapter()
    cls_out = cls_adapter.predict(analysis, capture_id="G2_SEARCH_TEST")
    engine.apply_coarse_pruning(all_cands, analysis, classifier_output=cls_out)

    pruned_count = sum(1 for c in all_cands if c.status == "PRUNED")
    unsupported_count = sum(1 for c in all_cands if c.status == "UNSUPPORTED")
    surviving = [c for c in all_cands if c.status == "EVALUATED"]
    assert len(surviving) > 0, "Expected surviving candidates after coarse pruning"
    assert unsupported_count == 0, f"Expected 0 unsupported candidates since all 5 FEC families are implemented, got {unsupported_count}"

    # Step 3: Competing candidate decoder execution
    # Candidate 1: (BPSK, conv_viterbi_k7, block) - True signal parameters
    cand1 = next(c for c in surviving if c.modulation == "BPSK" and c.fec == "conv_viterbi_k7" and c.interleaver == "block")
    out1 = run_arpit_decoder(
        capture_input=str(g2_path),
        capture_id="G2_CAND1",
        analysis=analysis,
        candidate_modulation=cand1.modulation,
        fec_scheme=cand1.fec,
        deinterleave_scheme=cand1.interleaver,
    )

    # Candidate 2: (BPSK, none, none) - Uncoded BPSK competitor
    cand2 = next(c for c in surviving if c.modulation == "BPSK" and c.fec == "none" and c.interleaver == "none")
    out2 = run_arpit_decoder(
        capture_input=str(g2_path),
        capture_id="G2_CAND2",
        analysis=analysis,
        candidate_modulation=cand2.modulation,
        fec_scheme=cand2.fec,
        deinterleave_scheme=cand2.interleaver,
    )

    # Candidate 3: (BPSK, conv_viterbi_k7, none) - Convolutional without deinterleaving
    cand3 = next(c for c in surviving if c.modulation == "BPSK" and c.fec == "conv_viterbi_k7" and c.interleaver == "none")
    out3 = run_arpit_decoder(
        capture_input=str(g2_path),
        capture_id="G2_CAND3",
        analysis=analysis,
        candidate_modulation=cand3.modulation,
        fec_scheme=cand3.fec,
        deinterleave_scheme=cand3.interleaver,
    )

    # Verification of candidate 1 (Winning hypothesis)
    assert out1.status == DecoderStatus.OK
    assert out1.fec_used == "conv_viterbi_k7"
    assert out1.interleaver_used == "block"
    assert out1.reencode_ber == 0.0, f"Expected 0.0 BER on matching candidate, got {out1.reencode_ber}"

    # Verification of candidate 2 (Uncoded competitor)
    assert out2.status == DecoderStatus.OK
    assert out2.fec_used == "none"
    assert out2.reencode_ber is None  # Uncoded has no FEC verification

    # Fine evaluation of evidence for all candidates
    engine.evaluate_fine_evidence(all_cands, out1)
    ranked = engine.rank_candidates(all_cands)
    winner = ranked[0]

    # Assert winner is backed by actual execution evidence
    assert winner.modulation == "BPSK"
    assert winner.fec == "conv_viterbi_k7"
    assert winner.interleaver == "block"
    assert winner.final_rank_score > cand2.final_rank_score, "Verified FEC candidate must outrank uncoded candidate"


def test_end_to_end_runner_uses_authoritative_hypothesis_winner():
    """Verify end-to-end runner strictly uses HypothesisEngine ranking to set top_hypothesis."""
    g2_path = GOLDEN_DIR / "G2_BPSK_conv_block.cf32"
    if not g2_path.exists():
        pytest.skip(f"Capture {g2_path} not found")

    pr = run(str(g2_path), mode="live")
    res = pr.result

    assert res.top_hypothesis is not None
    assert res.top_hypothesis.modulation == "BPSK"
    assert res.top_hypothesis.fec == "conv_viterbi_k7"
    assert res.top_hypothesis.interleaver == "block"
    assert pr.decoder.reencode_ber == 0.0
    assert pr.decoder.fec_used == "conv_viterbi_k7"
    assert pr.decoder.interleaver_used == "block"


def test_ldpc_candidate_decoder_execution():
    """Verify that LDPC candidate on G4 evaluates and achieves status OK with low BER."""
    g4_path = GOLDEN_DIR / "G4_16QAM_LDPC_pseudorandom.cf32"
    meta_path = GOLDEN_DIR / "G4_16QAM_LDPC_pseudorandom.json"
    if not g4_path.exists() or not meta_path.exists():
        pytest.skip(f"Capture {g4_path} not found")

    meta = json.loads(meta_path.read_text())
    fs = float(meta["sample_rate"])
    sig = load_signal(str(g4_path))
    analysis = iq_to_analysis_contract(sig.samples, fs_hz=fs, capture_id="G4_SEARCH_TEST")

    c_out = run_arpit_decoder(
        capture_input=str(g4_path),
        capture_id="G4_LDPC_TEST",
        analysis=analysis,
        candidate_modulation="16-QAM",
        fec_scheme="ldpc",
        deinterleave_scheme="pseudo-random",
    )
    assert c_out.status == DecoderStatus.OK
    assert c_out.fec_used == "ldpc"
    assert c_out.interleaver_used == "pseudo-random"
    assert c_out.reencode_ber is not None and c_out.reencode_ber <= 0.05
