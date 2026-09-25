"""
Cross-Window Stability & Agreement Analyzer for SpectralQ.

Runs classification independently over multiple temporal sub-windows of the same capture.
Outputs:
- Per-window ML prediction
- Per-window ML probability
- Per-window Rule prediction
- Agreement ratio in [0.0, 1.0]
- Total count of windows analyzed

Invariants:
- Unstable or outlier windows are NEVER hidden or dropped from the report.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from spectralq.contracts.schemas import AnalysisContract, ClassifierOutputContract, FeaturesBlock
from spectralq.integration.classifier_adapter import (
    ClassifierAdapter,
    extract_features_from_analysis,
)
from spectralq.integration.rule_classifier import RuleBasedClassifier, RuleClassificationResult


@dataclass
class WindowClassification:
    window_id: int
    ml_prediction: str
    ml_probability: float
    rule_prediction: str
    window_consensus_match: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "ml_prediction": self.ml_prediction,
            "ml_probability": self.ml_probability,
            "rule_prediction": self.rule_prediction,
            "window_consensus_match": self.window_consensus_match,
        }


@dataclass
class CrossWindowReport:
    total_windows: int
    consensus_prediction: str
    agreement_ratio: float
    windows: List[WindowClassification]
    outlier_window_ids: List[int]
    is_stable: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_windows": self.total_windows,
            "consensus_prediction": self.consensus_prediction,
            "agreement_ratio": self.agreement_ratio,
            "windows": [w.to_dict() for w in self.windows],
            "outlier_window_ids": list(self.outlier_window_ids),
            "is_stable": self.is_stable,
        }


def evaluate_cross_window(
    windows_input: List[Union[Dict[str, float], FeaturesBlock, AnalysisContract]],
    classifier_adapter: ClassifierAdapter,
    rule_classifier: Optional[RuleBasedClassifier] = None,
    capture_id: str = "CAPTURE",
    stability_threshold: float = 0.75,
) -> CrossWindowReport:
    """
    Evaluates classification independently across multiple temporal windows.
    Preserves all windows in the final report without dropping outliers.
    """
    if not windows_input:
        return CrossWindowReport(
            total_windows=0,
            consensus_prediction="UNKNOWN",
            agreement_ratio=0.0,
            windows=[],
            outlier_window_ids=[],
            is_stable=False,
        )

    rule_clf = rule_classifier or RuleBasedClassifier()
    raw_results = []

    for idx, win_item in enumerate(windows_input):
        # Extract features dictionary
        if isinstance(win_item, AnalysisContract):
            feat_dict = extract_features_from_analysis(win_item)
            rule_input = win_item.features
        elif isinstance(win_item, FeaturesBlock):
            # Convert to dict for classifier
            feat_dict = {
                "C20": float(win_item.cumulants.C20),
                "C21": float(win_item.cumulants.C21),
                "C40": float(win_item.cumulants.C40),
                "C42": float(win_item.cumulants.C42),
                "C60": float(win_item.cumulants.C60),
                "C63": float(win_item.cumulants.C63),
                "C80": float(win_item.cumulants.C80),
                "cluster_count": float(win_item.cluster.count),
                "silhouette": float(win_item.cluster.silhouette),
                "intra_var": float(win_item.cluster.intra_var),
                "inter_dist": float(win_item.cluster.inter_dist),
                "evm": float(win_item.evm),
                "phase_ambiguity_quality": float(win_item.phase_ambiguity_quality),
                "snr": 15.0,
                "baud": 1.0e6,
            }
            rule_input = win_item
        else:
            feat_dict = win_item
            rule_input = win_item

        # Run ML
        ml_contract: ClassifierOutputContract = classifier_adapter.predict(
            analysis_or_features=feat_dict,
            capture_id=capture_id,
            window_id=idx,
        )
        ml_pred = ml_contract.ml_prediction
        ml_prob = ml_contract.ml_probabilities.get(ml_pred, 0.0)

        # Run Rule
        rule_res: RuleClassificationResult = rule_clf.classify(rule_input)
        rule_pred = rule_res.predicted_class

        raw_results.append({
            "window_id": idx,
            "ml_pred": ml_pred,
            "ml_prob": ml_prob,
            "rule_pred": rule_pred,
        })

    # Determine consensus (most frequent ML prediction across all windows)
    all_ml_preds = [r["ml_pred"] for r in raw_results]
    counter = Counter(all_ml_preds)
    consensus_pred, consensus_count = counter.most_common(1)[0]

    total_windows = len(raw_results)
    agreement_ratio = float(consensus_count / total_windows)

    # Build per-window records
    windows: List[WindowClassification] = []
    outlier_ids: List[int] = []

    for r in raw_results:
        matches = (r["ml_pred"] == consensus_pred)
        if not matches:
            outlier_ids.append(r["window_id"])

        windows.append(WindowClassification(
            window_id=r["window_id"],
            ml_prediction=r["ml_pred"],
            ml_probability=r["ml_prob"],
            rule_prediction=r["rule_pred"],
            window_consensus_match=matches,
        ))

    return CrossWindowReport(
        total_windows=total_windows,
        consensus_prediction=consensus_pred,
        agreement_ratio=agreement_ratio,
        windows=windows,
        outlier_window_ids=outlier_ids,
        is_stable=(agreement_ratio >= stability_threshold),
    )
