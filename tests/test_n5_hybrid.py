"""
Tests for N5 Hybrid Modulation Identification (Rule Engine, ML Adapter, Agreement Scoring).
"""

import pytest
from spectralq.contracts.schemas import (
    AnalysisContract,
    Cumulants,
    ClusterMetrics,
    ProvenanceType,
)
from spectralq.n5_hybrid.rule_engine import RuleBasedClassifier
from spectralq.n5_hybrid.classifier_adapter import ClassifierAdapter
from spectralq.n5_hybrid.agreement import evaluate_n5_agreement


@pytest.fixture
def clean_bpsk_analysis():
    return AnalysisContract(
        capture_id="TEST_BPSK",
        provenance=ProvenanceType.SYNTHETIC,
        is_valid_burst=True,
        snr_m2m4_db=22.0,
        evm=0.04,
        phase_ambiguity_quality=0.95,
        envelope_variance=0.04,
        phase_entropy=0.69,
        cumulants=Cumulants(
            C20=0.99, C21=1.0, C40=-1.98, C42=-1.98, C60=0.0, C63=0.0, C80=0.0
        ),
        cluster_metrics=ClusterMetrics(
            cluster_count=2,
            silhouette_score=0.92,
            intra_cluster_dist=0.08,
            inter_cluster_dist=1.95,
            cluster_count_stability=0.98,
        ),
    )


@pytest.fixture
def clean_2fsk_analysis():
    return AnalysisContract(
        capture_id="TEST_2FSK",
        provenance=ProvenanceType.SYNTHETIC,
        is_valid_burst=True,
        snr_m2m4_db=18.0,
        evm=0.10,
        phase_ambiguity_quality=0.85,
        envelope_variance=0.48,  # High envelope variance characteristic of FSK
        phase_entropy=2.1,
        cumulants=Cumulants(
            C20=0.02, C21=1.0, C40=0.05, C42=-0.95, C60=0.0, C63=0.0, C80=0.0
        ),
        cluster_metrics=ClusterMetrics(
            cluster_count=2,
            silhouette_score=0.80,
            intra_cluster_dist=0.15,
            inter_cluster_dist=1.0,
            cluster_count_stability=0.92,
        ),
    )


def test_rule_classifier_bpsk(clean_bpsk_analysis):
    rule_engine = RuleBasedClassifier()
    pred, score, scores_dict = rule_engine.classify(clean_bpsk_analysis)
    assert pred == "BPSK"
    assert score > 0.40
    assert "BPSK" in scores_dict


def test_rule_classifier_2fsk(clean_2fsk_analysis):
    rule_engine = RuleBasedClassifier()
    pred, score, scores_dict = rule_engine.classify(clean_2fsk_analysis)
    assert pred == "2-FSK"
    assert score > 0.40


def test_classifier_adapter_prediction(clean_bpsk_analysis):
    adapter = ClassifierAdapter(seed=42)
    output = adapter.predict(clean_bpsk_analysis)
    assert output.predicted_class in ["BPSK", "QPSK", "8-PSK", "16-QAM", "64-QAM", "2-FSK", "4-FSK"]
    assert output.predicted_class == "BPSK"
    assert output.class_probabilities["BPSK"] > 0.50


def test_n5_agreement_consensus():
    agreed, score, details = evaluate_n5_agreement(
        rule_pred="BPSK",
        rule_score=0.80,
        ml_pred="BPSK",
        ml_prob=0.85,
        rule_scores_dict={"BPSK": 0.80, "QPSK": 0.10},
        ml_probs_dict={"BPSK": 0.85, "QPSK": 0.05},
    )
    assert agreed is True
    assert score >= 0.70
    assert details["conflict_type"] == "NONE"


def test_n5_agreement_conflict_penalty():
    agreed, score, details = evaluate_n5_agreement(
        rule_pred="BPSK",
        rule_score=0.80,
        ml_pred="16-QAM",
        ml_prob=0.75,
        rule_scores_dict={"BPSK": 0.80, "16-QAM": 0.05},
        ml_probs_dict={"16-QAM": 0.75, "BPSK": 0.05},
    )
    assert agreed is False
    assert score <= 0.40  # Hard conflict severely penalizes agreement score
    assert "HARD_CONFLICT" in details["conflict_type"]
