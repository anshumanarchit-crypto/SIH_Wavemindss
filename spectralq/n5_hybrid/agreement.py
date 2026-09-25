"""
N5 Hybrid Modulation ID Agreement Engine.
Computes explicit agreement/disagreement between the independent Rule-based engine
and the trained ML Classifier. Disagreement strictly penalizes confidence.
"""

from typing import Any, Dict, Tuple


def evaluate_n5_agreement(
    rule_pred: str,
    rule_score: float,
    ml_pred: str,
    ml_prob: float,
    rule_scores_dict: Dict[str, float] = None,
    ml_probs_dict: Dict[str, float] = None
) -> Tuple[bool, float, Dict[str, Any]]:
    """
    Evaluates N5 consensus between Rule Engine and ML Classifier.
    
    Returns:
        agreed (bool): True if both paths choose the exact same modulation.
        agreement_score (float): Bounded in [0.0, 1.0].
        details (dict): Structured audit trail of the comparison.
    """
    rule_scores_dict = rule_scores_dict or {}
    ml_probs_dict = ml_probs_dict or {}

    agreed = (rule_pred == ml_pred)

    if agreed:
        # Both paths agree on the modulation
        # Score combines rule confidence and ML probability
        combined_strength = (rule_score + ml_prob) / 2.0
        # Check cross-class margin: margin between top class and second class in both
        rule_sorted = sorted(rule_scores_dict.values(), reverse=True)
        ml_sorted = sorted(ml_probs_dict.values(), reverse=True)
        
        rule_margin = (rule_sorted[0] - rule_sorted[1]) if len(rule_sorted) > 1 else rule_score
        ml_margin = (ml_sorted[0] - ml_sorted[1]) if len(ml_sorted) > 1 else ml_prob

        # Agreement score is high when both are confident
        agreement_score = float(min(1.0, 0.5 + 0.3 * combined_strength + 0.2 * min(rule_margin, ml_margin)))
        conflict_type = "NONE"
    else:
        # Disagreement detected!
        # Both predictions are preserved.
        # Check if the rule prediction was ranked high by ML or vice versa (soft disagreement vs hard conflict)
        ml_prob_for_rule_choice = ml_probs_dict.get(rule_pred, 0.0)
        rule_score_for_ml_choice = rule_scores_dict.get(ml_pred, 0.0)

        cross_support = (ml_prob_for_rule_choice + rule_score_for_ml_choice) / 2.0
        
        # Hard conflict has very low agreement score (<= 0.35)
        # Even soft disagreement cannot exceed 0.45
        agreement_score = float(max(0.05, min(0.40, 0.15 + 0.25 * cross_support)))
        conflict_type = f"HARD_CONFLICT: Rule={rule_pred}({rule_score:.2f}) vs ML={ml_pred}({ml_prob:.2f})"

    details = {
        "agreed": agreed,
        "agreement_score": agreement_score,
        "conflict_type": conflict_type,
        "rule_prediction": rule_pred,
        "rule_score": rule_score,
        "ml_prediction": ml_pred,
        "ml_prob": ml_prob,
    }

    return agreed, agreement_score, details
