"""
Phase 6 Tests: N2 Computed Confidence Engine & Relative Ordinal Behavior.

Covers:
1. Relative behavior of four canonical cases (Cases A, B, C, D):
   - A: strong ML + strong window agreement + strong evidence + rule agrees -> top quartile (> 0.75)
   - B: strong ML + poor window agreement + weak evidence + rule disagrees -> substantially lower than A
   - C: moderate ML + excellent verification + agreement -> moderate/high
   - D: strong ML + rule disagreement -> measurably reduced vs otherwise identical Case A
2. Output always strictly bounded in [0.0, 1.0].
3. Deterministic output given identical inputs.
4. Evidence score with no verified checks sets evidence_score = 0.0 and no_verification_possible = True.
5. Invariant: Raw classifier probability is NEVER passed straight through as final confidence.
6. Codebase audit: Grep verifies NO hardcoded 95.0% or 0.95 final confidence anywhere.
"""

import re
from pathlib import Path
import pytest

from spectralq.confidence import (
    ConfidenceEngine,
    ConfidenceResult,
    generate_held_out_calibration_dataset,
    fit_and_save_confidence_weights,
)
from spectralq.evidence.ledger import EvidenceLedger
from spectralq.contracts.schemas import EvidenceStatus


@pytest.fixture
def confidence_engine():
    return ConfidenceEngine(weight_source="fitted")


# -----------------------------------------------------------------------------
# 1. Canonical Cases A, B, C, D: Relative Ordinal Validation
# -----------------------------------------------------------------------------
def test_case_a_strong_everything(confidence_engine):
    """
    Case A: strong ML (0.95) + strong window (1.0) + strong evidence (1.0) + rule agrees (True)
    -> Final confidence in top quartile (> 0.75).
    """
    res = confidence_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.95,
        cross_window_agreement=1.0,
        rule_prediction="QPSK",
        ml_prediction="QPSK",
        rule_ml_agreement=True,
        evidence_score=1.0,
    )
    assert 0.0 <= res.final_confidence <= 1.0
    assert res.final_confidence > 0.75, f"Case A should be in top quartile (> 0.75), got {res.final_confidence}"
    assert res.no_verification_possible is False


def test_case_b_substantially_lower_than_case_a(confidence_engine):
    """
    Case B: strong ML (0.95) + poor window (0.25) + weak evidence (0.20) + rule disagrees (False)
    -> Final confidence substantially lower than Case A (margin > 0.20).
    """
    res_a = confidence_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.95,
        cross_window_agreement=1.0,
        rule_prediction="QPSK",
        ml_prediction="QPSK",
        rule_ml_agreement=True,
        evidence_score=1.0,
    )
    res_b = confidence_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.95,
        cross_window_agreement=0.25,
        rule_prediction="16-QAM",
        ml_prediction="QPSK",
        rule_ml_agreement=False,
        evidence_score=0.20,
    )

    assert 0.0 <= res_b.final_confidence <= 1.0
    assert res_b.final_confidence < res_a.final_confidence - 0.20, (
        f"Case B ({res_b.final_confidence}) must be substantially lower than Case A ({res_a.final_confidence})"
    )


def test_case_c_moderate_ml_excellent_verification(confidence_engine):
    """
    Case C: moderate ML (0.65) + excellent verification (1.0) + rule agreement (True)
    -> Moderate to high confidence (0.60 to 0.95).
    """
    res = confidence_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.65,
        cross_window_agreement=0.90,
        rule_prediction="QPSK",
        ml_prediction="QPSK",
        rule_ml_agreement=True,
        evidence_score=1.0,
    )
    assert 0.60 <= res.final_confidence <= 0.95, f"Case C expected moderate/high, got {res.final_confidence}"


def test_case_d_rule_ml_disagreement_measurably_reduces_confidence(confidence_engine):
    """
    Case D: strong ML (0.95) + strong disagreement (rule != ml)
    -> Final confidence measurably reduced vs. otherwise-identical Case A.
    """
    res_a = confidence_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.95,
        cross_window_agreement=1.0,
        rule_prediction="QPSK",
        ml_prediction="QPSK",
        rule_ml_agreement=True,
        evidence_score=1.0,
    )
    res_d = confidence_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.95,
        cross_window_agreement=1.0,
        rule_prediction="BPSK",
        ml_prediction="QPSK",
        rule_ml_agreement=False,
        evidence_score=1.0,
    )

    assert 0.0 <= res_d.final_confidence <= 1.0
    assert res_d.final_confidence < res_a.final_confidence - 0.05, (
        f"Case D with disagreement ({res_d.final_confidence}) must be measurably lower than Case A ({res_a.final_confidence})"
    )


# -----------------------------------------------------------------------------
# 2. Invariants: [0, 1] Bounds & Determinism
# -----------------------------------------------------------------------------
def test_confidence_always_bounded_and_deterministic(confidence_engine):
    for ml in [0.0, 0.2, 0.5, 0.8, 1.0]:
        for cw in [0.0, 0.5, 1.0]:
            for ev in [0.0, 0.5, 1.0]:
                for agree in [True, False]:
                    res1 = confidence_engine.compute_confidence(
                        prediction="QPSK",
                        ml_probability=ml,
                        cross_window_agreement=cw,
                        rule_prediction="QPSK" if agree else "BPSK",
                        ml_prediction="QPSK",
                        rule_ml_agreement=agree,
                        evidence_score=ev,
                    )
                    res2 = confidence_engine.compute_confidence(
                        prediction="QPSK",
                        ml_probability=ml,
                        cross_window_agreement=cw,
                        rule_prediction="QPSK" if agree else "BPSK",
                        ml_prediction="QPSK",
                        rule_ml_agreement=agree,
                        evidence_score=ev,
                    )
                    assert 0.0 <= res1.final_confidence <= 1.0
                    assert res1.final_confidence == res2.final_confidence


# -----------------------------------------------------------------------------
# 3. Evidence Score: Strict Handling When No Verification Was Possible
# -----------------------------------------------------------------------------
def test_no_verification_possible_handling(confidence_engine):
    ledger = EvidenceLedger(run_id="RUN_EMPTY_VERIF")
    # Add only NOT_RUN and UNAVAILABLE checks (no evaluable physical evidence)
    ledger.record(
        evidence_id="EV_UNSUPP",
        source="Decoder",
        check_name="ldpc",
        status=EvidenceStatus.UNAVAILABLE,
        explanation="LDPC unsupported",
    )
    ledger.record(
        evidence_id="EV_NOTRUN",
        source="Decoder",
        check_name="crc",
        status=EvidenceStatus.NOT_RUN,
        explanation="CRC not run",
    )

    ev_score, no_verif = ledger.compute_evidence_ratio()
    assert ev_score == 0.0
    assert no_verif is True

    res = confidence_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.80,
        cross_window_agreement=0.90,
        rule_prediction="QPSK",
        ml_prediction="QPSK",
        rule_ml_agreement=True,
        ledger=ledger,
    )
    assert res.evidence_score == 0.0
    assert res.no_verification_possible is True
    # Confidence must reflect lack of physical verification (not defaulted to 0.5)
    assert res.final_confidence < 0.90


def test_never_passes_raw_classifier_prob_straight_through(confidence_engine):
    """Verifies that final_confidence is never an unadjusted passthrough of ml_probability."""
    res = confidence_engine.compute_confidence(
        prediction="QPSK",
        ml_probability=0.8888,
        cross_window_agreement=0.40,
        rule_prediction="BPSK",
        ml_prediction="QPSK",
        rule_ml_agreement=False,
        evidence_score=0.10,
    )
    assert res.final_confidence != 0.8888
    assert res.final_confidence < 0.8888


# -----------------------------------------------------------------------------
# 4. Codebase Audit: No Hardcoded 95.0% or 0.95 in Final Confidence Assignment
# -----------------------------------------------------------------------------
def test_no_hardcoded_95_final_confidence():
    """
    Audits python/spectralq/ to ensure no hardcoded 95.0, 0.95, or 95% is assigned
    as a final confidence score anywhere in the codebase.
    """
    root = Path(__file__).parent.parent / "python" / "spectralq"
    assert root.exists()

    pattern = re.compile(r"(final_confidence|confidence)\s*=\s*(0\.95|95(\.0)?\b)")

    violations = []
    for py_file in root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for line_num, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                violations.append(f"{py_file.name}:{line_num}: {line.strip()}")

    assert not violations, f"Found hardcoded 95 confidence assignments: {violations}"
