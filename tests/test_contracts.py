"""
Unit tests for SpectralQ Pydantic schemas and contracts.
"""

import pytest
from pydantic import ValidationError

from spectralq.contracts.schemas import (
    AnalysisContract,
    Cumulants,
    ClusterMetrics,
    ProvenanceType,
    LadderLevel,
    ResultContract,
    DecoderVerificationContract,
    DecoderStatus,
)


def test_valid_analysis_contract():
    analysis = AnalysisContract(
        capture_id="TEST_001",
        provenance=ProvenanceType.SYNTHETIC,
        is_valid_burst=True,
        center_freq_hz=433.92e6,
        bandwidth_hz=100e3,
        baud_rate=50e3,
        snr_m2m4_db=20.0,
        evm=0.05,
        phase_ambiguity_quality=0.9,
        envelope_variance=0.05,
        phase_entropy=1.2,
        cumulants=Cumulants(
            C20=1.0, C21=1.0, C40=-2.0, C42=-2.0, C60=0.0, C63=0.0, C80=0.0
        ),
        cluster_metrics=ClusterMetrics(
            cluster_count=2,
            silhouette_score=0.9,
            intra_cluster_dist=0.1,
            inter_cluster_dist=1.9,
            cluster_count_stability=0.95,
        ),
    )
    assert analysis.capture_id == "TEST_001"
    assert analysis.provenance == ProvenanceType.SYNTHETIC
    assert analysis.cumulants.C20 == 1.0


def test_analysis_contract_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        AnalysisContract(
            capture_id="TEST_EXTRA",
            provenance=ProvenanceType.SYNTHETIC,
            is_valid_burst=True,
            snr_m2m4_db=20.0,
            evm=0.05,
            phase_ambiguity_quality=0.9,
            envelope_variance=0.05,
            phase_entropy=1.2,
            cumulants=Cumulants(
                C20=1.0, C21=1.0, C40=-2.0, C42=-2.0, C60=0.0, C63=0.0, C80=0.0
            ),
            cluster_metrics=ClusterMetrics(
                cluster_count=2,
                silhouette_score=0.9,
                intra_cluster_dist=0.1,
                inter_cluster_dist=1.9,
                cluster_count_stability=0.95,
            ),
            unauthorized_field="forbidden",  # Extra field
        )


def test_decoder_verification_contract():
    decoder = DecoderVerificationContract(
        sync_detected=True,
        sync_confidence=0.88,
        crc_valid=True,
        reencode_ber=0.002,
        interleaver_detected="block",
        fec_detected="conv_viterbi_k7",
        status=DecoderStatus.SUCCESS,
        decoded_bits_count=1024,
    )
    assert decoder.sync_detected is True
    assert decoder.crc_valid is True
    assert decoder.status == DecoderStatus.SUCCESS
