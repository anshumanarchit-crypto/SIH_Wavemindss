"""
Phase 5 Tests: ML Integration, Rule AMC, N5 Hybrid Consensus & Cross-Window Analysis.

Covers:
1. ClassifierAdapter: feature schema validation, deterministic ordering, raw ml_probability.
2. Real scikit-learn RandomForestClassifier integration without version deprecation crashes.
3. RuleBasedClassifier: genuine explainable AMC decision tree and human-readable decision path.
4. N5 Hybrid Consensus:
   - Agreement case (rule == ml): both predictions survive, agreement=True, penalty=0.0, status=PASS.
   - Disagreement case (rule != ml): both predictions survive, agreement=False, penalty=0.25, status=CONFLICT.
5. Cross-Window Analysis:
   - 4-window constructed scenario with 3 matching + 1 outlier.
   - agreement_ratio == 0.75, total_windows == 4.
   - Invariant: outlier window is NEVER dropped or hidden from the report.
"""

import pytest
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from spectralq.contracts.schemas import (
    AnalysisContract,
    ClassifierOutputContract,
    EvidenceStatus,
    validate_analysis_dict,
)
from spectralq.evidence.ledger import EvidenceLedger
from spectralq.integration import (
    ClassifierAdapter,
    RuleBasedClassifier,
    RuleClassificationResult,
    RuleThresholdConfig,
    evaluate_n5_consensus,
    evaluate_cross_window,
    CANONICAL_FEATURE_NAMES,
)


@pytest.fixture
def base_qpsk_features():
    """Features representing a clear QPSK constellation."""
    return {
        "C20": 0.01,
        "C21": 1.0,
        "C40": 0.98,
        "C42": -0.99,
        "C60": 0.0,
        "C63": 0.0,
        "C80": 0.0,
        "cluster_count": 4.0,
        "silhouette": 0.88,
        "intra_var": 0.08,
        "inter_dist": 1.41,
        "evm": 0.045,
        "phase_ambiguity_quality": 0.92,
        "snr": 18.0,
        "baud": 1.0e6,
    }


@pytest.fixture
def base_bpsk_features():
    """Features representing a 1D real BPSK constellation."""
    return {
        "C20": 0.95,
        "C21": 1.0,
        "C40": -1.95,
        "C42": -1.95,
        "C60": 0.0,
        "C63": 0.0,
        "C80": 0.0,
        "cluster_count": 2.0,
        "silhouette": 0.92,
        "intra_var": 0.05,
        "inter_dist": 2.0,
        "evm": 0.035,
        "phase_ambiguity_quality": 0.95,
        "snr": 18.0,
        "baud": 1.0e6,
    }


@pytest.fixture
def base_fsk_features():
    """Features representing a continuous phase 2-FSK tone."""
    return {
        "C20": 0.02,
        "C21": 1.0,
        "C40": 0.05,
        "C42": -0.98,
        "C60": 0.0,
        "C63": 0.0,
        "C80": 0.0,
        "cluster_count": 2.0,
        "silhouette": 0.22,  # Low constellation clustering in complex IQ domain
        "intra_var": 0.45,
        "inter_dist": 0.80,
        "evm": 0.25,
        "phase_ambiguity_quality": 0.50,
        "snr": 16.0,
        "baud": 5.0e4,
    }


# -----------------------------------------------------------------------------
# 1. ClassifierAdapter Feature Ordering & Validation
# -----------------------------------------------------------------------------
def test_classifier_adapter_feature_validation(base_qpsk_features):
    adapter = ClassifierAdapter(model_version="test-rf-1.0.0")

    # Full canonical features succeed
    vec = adapter.validate_features(base_qpsk_features)
    assert len(vec) == 15
    assert vec[0] == base_qpsk_features["C20"]

    # Missing feature raises ValueError with explicit missing field names
    incomplete_features = dict(base_qpsk_features)
    del incomplete_features["C40"]
    with pytest.raises(ValueError, match="Missing required features"):
        adapter.validate_features(incomplete_features)


def test_classifier_adapter_with_real_sklearn_rf(base_qpsk_features, base_bpsk_features):
    """Verifies that an actual fitted scikit-learn RandomForest works seamlessly."""
    X_train = np.array([
        [base_qpsk_features[f] for f in CANONICAL_FEATURE_NAMES],
        [base_bpsk_features[f] for f in CANONICAL_FEATURE_NAMES],
    ])
    y_train = np.array(["QPSK", "BPSK"])

    rf = RandomForestClassifier(n_estimators=10, random_state=42)
    rf.fit(X_train, y_train)

    adapter = ClassifierAdapter(model=rf, model_version="rf-live-fit-v1")
    output = adapter.predict(base_qpsk_features, capture_id="CAP_LIVE_RF")

    assert isinstance(output, ClassifierOutputContract)
    assert output.ml_prediction in ["QPSK", "BPSK"]
    assert 0.0 <= output.ml_probabilities[output.ml_prediction] <= 1.0
    # Must NOT contain calibrated probability until Phase 7
    assert output.calibrated_probability is None
    assert output.model_version == "rf-live-fit-v1"


# -----------------------------------------------------------------------------
# 2. RuleBasedClassifier: Explainable AMC Decision Tree
# -----------------------------------------------------------------------------
def test_rule_based_classifier_bpsk_path(base_bpsk_features):
    classifier = RuleBasedClassifier()
    res = classifier.classify(base_bpsk_features)

    assert res.predicted_class == "BPSK"
    assert len(res.decision_path) >= 1
    # Check that human-readable decision path documents the BPSK check
    assert "Step 1: Check BPSK" in res.decision_path[0]
    assert "Classified as BPSK" in res.decision_path[0]
    assert "tau_bpsk_c20" in res.thresholds_applied


def test_rule_based_classifier_qpsk_path(base_qpsk_features):
    classifier = RuleBasedClassifier()
    res = classifier.classify(base_qpsk_features)

    assert res.predicted_class == "QPSK"
    assert len(res.decision_path) >= 3
    # Step 1 passed through, step 2 passed through, step 3 triggered QPSK
    assert "Classified as QPSK" in res.decision_path[-1]
    assert "tau_qpsk_c40_min" in res.thresholds_applied


def test_rule_based_classifier_fsk_path(base_fsk_features):
    classifier = RuleBasedClassifier()
    res = classifier.classify(base_fsk_features)

    assert res.predicted_class == "2-FSK"
    assert any("Check FSK" in s for s in res.decision_path)
    assert "tau_fsk_silhouette" in res.thresholds_applied


# -----------------------------------------------------------------------------
# 3. N5 Hybrid Consensus: Agreement Case
# -----------------------------------------------------------------------------
def test_n5_consensus_agreement_case(base_qpsk_features):
    ledger = EvidenceLedger(run_id="RUN_N5_AGREE")

    rule_clf = RuleBasedClassifier()
    rule_res = rule_clf.classify(base_qpsk_features)
    assert rule_res.predicted_class == "QPSK"

    adapter = ClassifierAdapter(model_version="rf-mock-1.0.0")
    ml_out = adapter.predict(base_qpsk_features, capture_id="CAP_AGREE")
    assert ml_out.ml_prediction == "QPSK"

    n5_res = evaluate_n5_consensus(
        rule_result=rule_res,
        ml_output=ml_out,
        capture_id="CAP_AGREE",
        ledger=ledger,
        run_id="RUN_N5_AGREE",
    )

    # Invariants
    assert n5_res.agreement is True
    assert n5_res.rule_prediction == "QPSK"
    assert n5_res.ml_prediction == "QPSK"
    assert n5_res.penalty == 0.0

    # Both predictions survive unchanged
    d = n5_res.to_dict()
    assert d["rule_prediction"] == "QPSK"
    assert d["ml_prediction"] == "QPSK"

    # Evidence item in ledger has PASS status
    items = ledger.get_items()
    assert len(items) == 1
    assert items[0].check_name == "rule_ml_agreement"
    assert items[0].status == EvidenceStatus.PASS
    assert items[0].failure_reason is None
    assert "Consensus reached" in items[0].explanation


# -----------------------------------------------------------------------------
# 4. N5 Hybrid Consensus: Disagreement Case
# -----------------------------------------------------------------------------
def test_n5_consensus_disagreement_case(base_qpsk_features, base_bpsk_features):
    ledger = EvidenceLedger(run_id="RUN_N5_CONFLICT")

    # Rule predicts BPSK
    rule_clf = RuleBasedClassifier()
    rule_res = rule_clf.classify(base_bpsk_features)
    assert rule_res.predicted_class == "BPSK"

    # ML predicts QPSK
    adapter = ClassifierAdapter(model_version="rf-mock-1.0.0")
    ml_out = adapter.predict(base_qpsk_features, capture_id="CAP_DISAGREE")
    assert ml_out.ml_prediction == "QPSK"

    n5_res = evaluate_n5_consensus(
        rule_result=rule_res,
        ml_output=ml_out,
        capture_id="CAP_DISAGREE",
        ledger=ledger,
        run_id="RUN_N5_CONFLICT",
    )

    # Invariants
    assert n5_res.agreement is False
    # CRITICAL: Both predictions survive unchanged — neither overwrites the other
    assert n5_res.rule_prediction == "BPSK"
    assert n5_res.ml_prediction == "QPSK"
    assert n5_res.penalty == 0.25

    # Evidence item in ledger has CONFLICT status and explicit failure reason
    items = ledger.get_items()
    assert len(items) == 1
    assert items[0].check_name == "rule_ml_agreement"
    assert items[0].status == EvidenceStatus.CONFLICT
    assert items[0].failure_reason == "Classification disagreement: rule=BPSK vs ml=QPSK"
    assert "penalty of 0.25" in items[0].explanation

    # Verify Phase 4 non-positive score invariant: conflict must contribute 0.0 positive points
    score = ledger.calculate_evidence_score()
    assert score == 0.0


# -----------------------------------------------------------------------------
# 5. Cross-Window Stability & Outlier Preservation
# -----------------------------------------------------------------------------
def test_cross_window_four_windows_three_matching_one_outlier(
    base_qpsk_features, base_bpsk_features
):
    """
    Constructed 4-window scenario:
    - Window 0: QPSK (matches consensus)
    - Window 1: QPSK (matches consensus)
    - Window 2: BPSK (outlier)
    - Window 3: QPSK (matches consensus)

    Expectations:
    - total_windows == 4
    - consensus_prediction == 'QPSK'
    - agreement_ratio == 0.75 (3 / 4)
    - Invariant: Window 2 (the outlier) is preserved in the report.
    """
    windows_input = [
        dict(base_qpsk_features),
        dict(base_qpsk_features),
        dict(base_bpsk_features),  # Outlier
        dict(base_qpsk_features),
    ]

    adapter = ClassifierAdapter(model_version="rf-cw-1.0.0")
    rule_clf = RuleBasedClassifier()

    report = evaluate_cross_window(
        windows_input=windows_input,
        classifier_adapter=adapter,
        rule_classifier=rule_clf,
        capture_id="CAP_CROSS_WIN",
    )

    assert report.total_windows == 4
    assert report.consensus_prediction == "QPSK"
    assert pytest.approx(report.agreement_ratio, 1e-4) == 0.75
    assert len(report.windows) == 4

    # Check that Window 2 outlier is explicitly reported
    assert report.outlier_window_ids == [2]
    win2 = report.windows[2]
    assert win2.window_id == 2
    assert win2.ml_prediction == "BPSK"
    assert win2.window_consensus_match is False

    # Check serialization
    report_dict = report.to_dict()
    assert len(report_dict["windows"]) == 4
    assert report_dict["agreement_ratio"] == 0.75
