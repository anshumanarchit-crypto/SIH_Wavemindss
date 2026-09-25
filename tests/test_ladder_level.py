"""
Tests for deterministic Ladder Level (L1 - L5) computation.
"""

import pytest
from spectralq.contracts.schemas import (
    AnalysisContract,
    DecoderVerificationContract,
    DecoderStatus,
    LadderLevel,
    Cumulants,
    ClusterMetrics,
    ProvenanceType,
)
from spectralq.evidence_ledger.ladder import compute_ladder_level


@pytest.fixture
def base_analysis():
    return AnalysisContract(
        capture_id="LADDER_TEST",
        provenance=ProvenanceType.SYNTHETIC,
        is_valid_burst=True,
        snr_m2m4_db=20.0,
        evm=0.05,
        phase_ambiguity_quality=0.90,
        envelope_variance=0.05,
        phase_entropy=1.2,
        cumulants=Cumulants(
            C20=1.0, C21=1.0, C40=-2.0, C42=-2.0, C60=0.0, C63=0.0, C80=0.0
        ),
        cluster_metrics=ClusterMetrics(
            cluster_count=2,
            silhouette_score=0.90,
            intra_cluster_dist=0.1,
            inter_cluster_dist=1.9,
            cluster_count_stability=0.95,
        ),
    )


def test_ladder_l1_no_burst(base_analysis):
    base_analysis.is_valid_burst = False
    ladder, _ = compute_ladder_level(base_analysis, decoder_output=None, n5_agreement=False, cross_window_agreement_score=0.0)
    assert ladder == LadderLevel.L1


def test_ladder_l2_no_decoder(base_analysis):
    # Burst and features valid, but decoder output is None
    ladder, _ = compute_ladder_level(base_analysis, decoder_output=None, n5_agreement=True, cross_window_agreement_score=0.9)
    assert ladder == LadderLevel.L2


def test_ladder_l3_decoder_unavailable(base_analysis):
    decoder = DecoderVerificationContract(
        sync_detected=False,
        sync_confidence=0.0,
        crc_valid=None,
        reencode_ber=None,
        status=DecoderStatus.UNAVAILABLE,
    )
    ladder, _ = compute_ladder_level(base_analysis, decoder_output=decoder, n5_agreement=True, cross_window_agreement_score=0.9)
    assert ladder == LadderLevel.L3


def test_ladder_l4_structure_verified(base_analysis):
    decoder = DecoderVerificationContract(
        sync_detected=True,
        sync_confidence=0.92,
        crc_valid=True,
        reencode_ber=0.001,
        status=DecoderStatus.SUCCESS,
    )
    # L4 when cross-window or N5 agreement is low/false
    ladder, _ = compute_ladder_level(base_analysis, decoder_output=decoder, n5_agreement=False, cross_window_agreement_score=0.5)
    assert ladder == LadderLevel.L4


def test_ladder_l5_independently_cross_checked(base_analysis):
    decoder = DecoderVerificationContract(
        sync_detected=True,
        sync_confidence=0.95,
        crc_valid=True,
        reencode_ber=0.001,
        status=DecoderStatus.SUCCESS,
    )
    # L5 when verified + N5 agreement + high cross window score (>= 0.80)
    ladder, _ = compute_ladder_level(base_analysis, decoder_output=decoder, n5_agreement=True, cross_window_agreement_score=0.95)
    assert ladder == LadderLevel.L5
