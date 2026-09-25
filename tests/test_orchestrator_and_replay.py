"""
Integration tests for SpectralQ Orchestrator, Replay Controller, and Octave Bridge.
"""

import json
import pytest
from pathlib import Path

from spectralq.contracts.schemas import (
    AnalysisContract,
    DecoderVerificationContract,
    DecoderStatus,
    LadderLevel,
    ProvenanceType,
    Cumulants,
    ClusterMetrics,
    SubWindowMetrics,
)
from spectralq.pipeline.orchestrator import SpectralQOrchestrator
from spectralq.pipeline.replay import ReplayController
from spectralq.pipeline.octave_bridge import OctaveBridge


@pytest.fixture
def high_quality_qpsk_analysis():
    return AnalysisContract(
        capture_id="INTEG_QPSK_001",
        provenance=ProvenanceType.SYNTHETIC,
        is_valid_burst=True,
        center_freq_hz=868.0e6,
        bandwidth_hz=200e3,
        baud_rate=100e3,
        snr_m2m4_db=24.0,
        evm=0.03,
        phase_ambiguity_quality=0.96,
        envelope_variance=0.05,
        phase_entropy=1.38,
        cumulants=Cumulants(
            C20=0.01, C21=1.0, C40=0.98, C42=-0.99, C60=0.0, C63=0.0, C80=0.0
        ),
        cluster_metrics=ClusterMetrics(
            cluster_count=4,
            silhouette_score=0.92,
            intra_cluster_dist=0.08,
            inter_cluster_dist=1.41,
            cluster_count_stability=0.98,
        ),
        sub_windows=[
            SubWindowMetrics(window_idx=0, estimated_snr_db=24.1, estimated_c42=-0.99, estimated_c20=0.01, cluster_count=4),
            SubWindowMetrics(window_idx=1, estimated_snr_db=23.9, estimated_c42=-0.98, estimated_c20=0.01, cluster_count=4),
        ],
    )


def test_orchestrator_end_to_end(high_quality_qpsk_analysis):
    orchestrator = SpectralQOrchestrator(seed=42)

    decoder_output = DecoderVerificationContract(
        sync_detected=True,
        sync_confidence=0.95,
        crc_valid=True,
        reencode_ber=0.001,
        interleaver_detected="block",
        fec_detected="conv_viterbi_k7",
        status=DecoderStatus.SUCCESS,
        decoded_bits_count=1024,
    )

    result = orchestrator.process(
        analysis=high_quality_qpsk_analysis,
        decoder_output=decoder_output,
    )

    # 1. Verify schema validity and fields
    assert result.capture_id == "INTEG_QPSK_001"
    assert result.decision_label == "QPSK"
    assert result.ladder_level == LadderLevel.L5
    assert result.final_confidence > 0.80
    assert result.is_calibrated is True
    assert result.unknown_reason is None

    # 2. Verify N5 Hybrid details
    assert result.rule_prediction == "QPSK"
    assert result.ml_prediction == "QPSK"
    assert result.n5_agreement is True
    assert result.n5_agreement_score >= 0.80

    # 3. Verify Hypothesis Engine Candidate Ranking
    assert len(result.candidates) > 0
    top = result.top_hypothesis
    assert top is not None
    assert top.modulation == "QPSK"

    # 4. Verify Evidence Ledger Audit Trail
    assert len(result.evidence_ledger) >= 8
    stage_names = [e.stage for e in result.evidence_ledger]
    assert "Ingest_and_Forensics" in stage_names
    assert "N5_Rule_Path" in stage_names
    assert "N5_ML_Path" in stage_names
    assert "N5_Agreement" in stage_names
    assert "Ladder_Level_Evaluation" in stage_names
    assert "Confidence_Fusion" in stage_names


def test_replay_controller_provenance_and_seed(tmp_path, high_quality_qpsk_analysis):
    # Save fixture
    json_path = tmp_path / "replay_test.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(high_quality_qpsk_analysis.model_dump(mode="json"), f)

    replay = ReplayController(seed=1234)
    analysis = replay.load_replay_analysis(str(json_path))

    # Verify provenance tag forced to replayed
    assert analysis.provenance == ProvenanceType.REPLAYED

    orchestrator = SpectralQOrchestrator(seed=1234)
    result = orchestrator.process(analysis=analysis)
    assert result.provenance == ProvenanceType.REPLAYED
    assert result.diagnostics["seed"] == 1234


def test_octave_bridge_unavailability_handling():
    # Pass non-existent directory to test strict unavailability reporting
    bridge = OctaveBridge(script_dir="non_existent_octave_path")
    status = bridge.get_status()
    assert "capability_available" in status

    # Forensics execution should return capability_unavailable: True without failing/crashing
    res = bridge.execute_forensics("dummy.cf32")
    assert res["capability_unavailable"] is True
    assert "error" in res
