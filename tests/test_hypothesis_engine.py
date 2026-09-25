"""
Tests for Hypothesis Engine (Modulation x Interleaver x FEC search, pruning, and unsupported LDPC handling).
"""

import pytest
from spectralq.contracts.schemas import (
    AnalysisContract,
    ClassifierOutputContract,
    DecoderVerificationContract,
    DecoderStatus,
    CandidateStatus,
    Cumulants,
    ClusterMetrics,
    ProvenanceType,
)
from spectralq.hypothesis_engine.search import HypothesisEngine


@pytest.fixture
def sample_analysis():
    return AnalysisContract(
        capture_id="HYP_TEST_001",
        provenance=ProvenanceType.SYNTHETIC,
        is_valid_burst=True,
        snr_m2m4_db=15.0,  # 15 dB is enough for QPSK, 8-PSK, but below 64-QAM (18 dB)
        evm=0.08,
        phase_ambiguity_quality=0.90,
        envelope_variance=0.05,
        phase_entropy=1.38,
        cumulants=Cumulants(
            C20=0.02, C21=1.0, C40=0.95, C42=-0.98, C60=0.0, C63=0.0, C80=0.0
        ),
        cluster_metrics=ClusterMetrics(
            cluster_count=4,
            silhouette_score=0.88,
            intra_cluster_dist=0.12,
            inter_cluster_dist=1.41,
            cluster_count_stability=0.95,
        ),
    )


def test_hypothesis_generation_and_ldpc_unsupported(sample_analysis):
    engine = HypothesisEngine()
    
    rule_scores = {"QPSK": 0.85, "BPSK": 0.05, "16-QAM": 0.05, "64-QAM": 0.01, "8-PSK": 0.02, "2-FSK": 0.01, "4-FSK": 0.01}
    classifier_output = ClassifierOutputContract(
        predicted_class="QPSK",
        class_probabilities=rule_scores,
        feature_vector={},
    )
    
    candidates = engine.evaluate_hypotheses(
        analysis=sample_analysis,
        rule_scores=rule_scores,
        classifier_output=classifier_output,
    )

    assert len(candidates) > 0

    # Verify LDPC is explicitly marked UNSUPPORTED and NEVER EVALUATED or faked
    ldpc_candidates = [c for c in candidates if c.fec == "ldpc"]
    assert len(ldpc_candidates) > 0
    for cand in ldpc_candidates:
        assert cand.status == CandidateStatus.UNSUPPORTED
        assert "not supported" in cand.rejection_reason.lower()
        assert cand.total_score == 0.0


def test_coarse_pruning_low_snr_modulations(sample_analysis):
    engine = HypothesisEngine()
    
    rule_scores = {"QPSK": 0.85, "64-QAM": 0.0, "BPSK": 0.05, "16-QAM": 0.05, "8-PSK": 0.02, "2-FSK": 0.01, "4-FSK": 0.01}
    classifier_output = ClassifierOutputContract(
        predicted_class="QPSK",
        class_probabilities=rule_scores,
        feature_vector={},
    )
    
    candidates = engine.evaluate_hypotheses(
        analysis=sample_analysis,
        rule_scores=rule_scores,
        classifier_output=classifier_output,
    )

    # 64-QAM should be PRUNED due to SNR = 15 dB < 18 dB floor
    qam64_candidates = [c for c in candidates if c.modulation == "64-QAM"]
    for c in qam64_candidates:
        if c.status != CandidateStatus.UNSUPPORTED:
            assert c.status == CandidateStatus.PRUNED
            assert "SNR" in c.rejection_reason or "probability" in c.rejection_reason
