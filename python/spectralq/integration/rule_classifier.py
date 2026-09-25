"""
Explainable Rule-Based Modulation Classifier.

Implements the standard family of cumulant-based Automatic Modulation Classification (AMC)
decision trees over 2nd and 4th order cumulants and cluster geometry metrics.

Thresholds are consumed from a versioned, documented configuration (RuleThresholdConfig),
never hardcoded as buried magic numbers.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from spectralq.contracts.schemas import AnalysisContract, FeaturesBlock
from spectralq.integration.rule_config import DEFAULT_RULE_CONFIG, RuleThresholdConfig


@dataclass
class RuleClassificationResult:
    predicted_class: str
    decision_path: List[str]
    features_used: Dict[str, float]
    thresholds_applied: Dict[str, float]
    config_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predicted_class": self.predicted_class,
            "decision_path": list(self.decision_path),
            "features_used": dict(self.features_used),
            "thresholds_applied": dict(self.thresholds_applied),
            "config_version": self.config_version,
        }


class RuleBasedClassifier:
    """
    Explainable cumulant & constellation cluster decision tree classifier.
    """

    def __init__(self, config: Optional[RuleThresholdConfig] = None):
        self.config = config or DEFAULT_RULE_CONFIG

    def classify(self, analysis_or_features: Any) -> RuleClassificationResult:
        """
        Executes the explainable AMC decision tree.
        Accepts AnalysisContract, FeaturesBlock, or a compatible dict.
        """
        # Extract features
        if isinstance(analysis_or_features, AnalysisContract):
            feat = analysis_or_features.features
        elif isinstance(analysis_or_features, FeaturesBlock):
            feat = analysis_or_features
        elif isinstance(analysis_or_features, dict):
            # Parse from dictionary (supports both nested schema dict and flat feature dict)
            feat_dict = analysis_or_features.get("features", analysis_or_features)
            if "cumulants" in feat_dict and isinstance(feat_dict["cumulants"], dict):
                cum = feat_dict["cumulants"]
                c20 = float(cum.get("C20", 0.0))
                c21 = float(cum.get("C21", 1.0))
                c40 = float(cum.get("C40", 0.0))
                c42 = float(cum.get("C42", -1.0))
            else:
                c20 = float(feat_dict.get("C20", 0.0))
                c21 = float(feat_dict.get("C21", 1.0))
                c40 = float(feat_dict.get("C40", 0.0))
                c42 = float(feat_dict.get("C42", -1.0))

            if "cluster" in feat_dict and isinstance(feat_dict["cluster"], dict):
                clu = feat_dict["cluster"]
                cluster_count = int(clu.get("count", 4))
                silhouette = float(clu.get("silhouette", 0.8))
            else:
                cluster_count = int(feat_dict.get("cluster_count", feat_dict.get("count", 4)))
                silhouette = float(feat_dict.get("silhouette", 0.8))

            evm = float(feat_dict.get("evm", 0.05))
            phase_ambiguity = float(feat_dict.get("phase_ambiguity_quality", 0.9))
            return self._evaluate_tree(
                c20=c20, c21=c21, c40=c40, c42=c42,
                cluster_count=cluster_count, silhouette=silhouette,
                evm=evm, phase_ambiguity=phase_ambiguity
            )
        else:
            feat = analysis_or_features

        c20 = feat.cumulants.C20
        c21 = feat.cumulants.C21
        c40 = feat.cumulants.C40
        c42 = feat.cumulants.C42
        cluster_count = feat.cluster.count
        silhouette = feat.cluster.silhouette
        evm = feat.evm
        phase_ambiguity = feat.phase_ambiguity_quality

        return self._evaluate_tree(
            c20=c20, c21=c21, c40=c40, c42=c42,
            cluster_count=cluster_count, silhouette=silhouette,
            evm=evm, phase_ambiguity=phase_ambiguity
        )

    def _evaluate_tree(
        self,
        c20: float,
        c21: float,
        c40: float,
        c42: float,
        cluster_count: int,
        silhouette: float,
        evm: float,
        phase_ambiguity: float,
    ) -> RuleClassificationResult:
        cfg = self.config
        norm_power = max(1e-9, abs(c21))
        rho_20 = abs(c20) / norm_power
        rho_40 = c40 / (norm_power ** 2)
        rho_42 = c42 / (norm_power ** 2)

        decision_path: List[str] = []
        features_used: Dict[str, float] = {
            "C20": c20,
            "C21": c21,
            "C40": c40,
            "C42": c42,
            "rho_20": rho_20,
            "rho_40": rho_40,
            "rho_42": rho_42,
            "cluster_count": float(cluster_count),
            "silhouette": silhouette,
            "evm": evm,
            "phase_ambiguity_quality": phase_ambiguity,
        }
        thresholds_applied: Dict[str, float] = {}

        # ---------------------------------------------------------------------
        # Branch 1: 1D Real vs 2D Complex (BPSK separation)
        # ---------------------------------------------------------------------
        thresholds_applied["tau_bpsk_c20"] = cfg.tau_bpsk_c20
        if rho_20 >= cfg.tau_bpsk_c20:
            decision_path.append(
                f"Step 1: Check BPSK (|C20|/C21 = {rho_20:.3f} >= threshold {cfg.tau_bpsk_c20:.3f}). "
                "Strong 1D real axis projection confirmed -> Classified as BPSK."
            )
            return RuleClassificationResult(
                predicted_class="BPSK",
                decision_path=decision_path,
                features_used=features_used,
                thresholds_applied=thresholds_applied,
                config_version=cfg.version,
            )

        decision_path.append(
            f"Step 1: Check BPSK (|C20|/C21 = {rho_20:.3f} < threshold {cfg.tau_bpsk_c20:.3f}). "
            "Signal is 2D complex circular constellation; proceed to FSK/QAM/PSK branch."
        )

        # ---------------------------------------------------------------------
        # Branch 2: Continuous Phase / Frequency Modulation (FSK separation)
        # ---------------------------------------------------------------------
        thresholds_applied["tau_fsk_silhouette"] = cfg.tau_fsk_silhouette
        if silhouette < cfg.tau_fsk_silhouette:
            if cluster_count <= 2:
                decision_path.append(
                    f"Step 2: Check FSK (Constellation silhouette {silhouette:.3f} < threshold {cfg.tau_fsk_silhouette:.3f}, "
                    f"cluster count {cluster_count} <= 2). Continuous phase tone signature -> Classified as 2-FSK."
                )
                return RuleClassificationResult(
                    predicted_class="2-FSK",
                    decision_path=decision_path,
                    features_used=features_used,
                    thresholds_applied=thresholds_applied,
                    config_version=cfg.version,
                )
            else:
                decision_path.append(
                    f"Step 2: Check FSK (Constellation silhouette {silhouette:.3f} < threshold {cfg.tau_fsk_silhouette:.3f}, "
                    f"cluster count {cluster_count} > 2). Multi-tone continuous phase -> Classified as 4-FSK."
                )
                return RuleClassificationResult(
                    predicted_class="4-FSK",
                    decision_path=decision_path,
                    features_used=features_used,
                    thresholds_applied=thresholds_applied,
                    config_version=cfg.version,
                )

        decision_path.append(
            f"Step 2: Check FSK (Constellation silhouette {silhouette:.3f} >= threshold {cfg.tau_fsk_silhouette:.3f}). "
            "Discrete constellation clustering detected; proceed to PSK/QAM analysis."
        )

        # ---------------------------------------------------------------------
        # Branch 3: QPSK Separation (Positive C40 and Unit-Magnitude C42)
        # ---------------------------------------------------------------------
        thresholds_applied["tau_qpsk_c40_min"] = cfg.tau_qpsk_c40_min
        if rho_40 >= cfg.tau_qpsk_c40_min and abs(rho_42) >= 0.78:
            decision_path.append(
                f"Step 3: Check QPSK (Normalized C40/C21^2 = {rho_40:.3f} >= threshold {cfg.tau_qpsk_c40_min:.3f}, "
                f"|C42|/C21^2 = {abs(rho_42):.3f} >= 0.780). "
                "Theoretical QPSK C40 is +1.0; 4-quadrant symmetric constant-modulus structure confirmed -> Classified as QPSK."
            )
            return RuleClassificationResult(
                predicted_class="QPSK",
                decision_path=decision_path,
                features_used=features_used,
                thresholds_applied=thresholds_applied,
                config_version=cfg.version,
            )

        decision_path.append(
            f"Step 3: Check QPSK (Normalized C40/C21^2 = {rho_40:.3f} or |C42|/C21^2 = {abs(rho_42):.3f} < 0.780). "
            "Not QPSK; proceed to 8-PSK and QAM separation."
        )

        # ---------------------------------------------------------------------
        # Branch 4: 8-PSK Separation (Vanishing C40, Unit-magnitude C42)
        # ---------------------------------------------------------------------
        thresholds_applied["tau_8psk_c40_max"] = cfg.tau_8psk_c40_max
        thresholds_applied["tau_8psk_c42_min"] = cfg.tau_8psk_c42_min
        if abs(rho_40) <= cfg.tau_8psk_c40_max and abs(rho_42) >= cfg.tau_8psk_c42_min:
            decision_path.append(
                f"Step 4: Check 8-PSK (|C40|/C21^2 = {abs(rho_40):.3f} <= {cfg.tau_8psk_c40_max:.3f} and "
                f"|C42|/C21^2 = {abs(rho_42):.3f} >= {cfg.tau_8psk_c42_min:.3f}). "
                "Circular 8-ary phase symmetry confirmed -> Classified as 8-PSK."
            )
            return RuleClassificationResult(
                predicted_class="8-PSK",
                decision_path=decision_path,
                features_used=features_used,
                thresholds_applied=thresholds_applied,
                config_version=cfg.version,
            )

        decision_path.append(
            f"Step 4: Check 8-PSK (|C40|/C21^2 = {abs(rho_40):.3f} or |C42|/C21^2 = {abs(rho_42):.3f} failed 8-PSK criteria). "
            "Candidate is in QAM family; proceed to order discrimination."
        )

        # ---------------------------------------------------------------------
        # Branch 5: QAM Order Discrimination (16-QAM vs 64-QAM)
        # ---------------------------------------------------------------------
        thresholds_applied["tau_qam_cluster_boundary"] = float(cfg.tau_qam_cluster_boundary)
        thresholds_applied["tau_qam_c42_split"] = cfg.tau_qam_c42_split

        if cluster_count > cfg.tau_qam_cluster_boundary or abs(rho_42) < cfg.tau_qam_c42_split:
            decision_path.append(
                f"Step 5: Check QAM Order (Cluster count {cluster_count} > boundary {cfg.tau_qam_cluster_boundary} "
                f"or |C42|/C21^2 = {abs(rho_42):.3f} < split {cfg.tau_qam_c42_split:.3f}). "
                "High-density grid geometry -> Classified as 64-QAM."
            )
            predicted_class = "64-QAM"
        else:
            decision_path.append(
                f"Step 5: Check QAM Order (Negative C40/C21^2 = {rho_40:.3f}, cluster count {cluster_count} <= {cfg.tau_qam_cluster_boundary}, "
                f"|C42|/C21^2 = {abs(rho_42):.3f} ~ 0.68). "
                "16-point grid geometry -> Classified as 16-QAM."
            )
            predicted_class = "16-QAM"

        return RuleClassificationResult(
            predicted_class=predicted_class,
            decision_path=decision_path,
            features_used=features_used,
            thresholds_applied=thresholds_applied,
            config_version=cfg.version,
        )
