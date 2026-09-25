"""
Independent Rule-Based Modulation Classifier.
Uses theoretical cumulant signatures, constellation cluster counts, envelope variance,
and phase entropy to classify modulation without trained ML weights.
"""

from typing import Dict, Tuple
import numpy as np
from spectralq.contracts.schemas import AnalysisContract


# Theoretical normalized cumulant benchmarks for unit-power constellations
THEORETICAL_CUMULANTS: Dict[str, Dict[str, float]] = {
    "BPSK": {"C20": 1.0, "C40": -2.0, "C42": -2.0, "cluster_count": 2.0},
    "QPSK": {"C20": 0.0, "C40": 1.0, "C42": -1.0, "cluster_count": 4.0},
    "8-PSK": {"C20": 0.0, "C40": 0.0, "C42": -1.0, "cluster_count": 8.0},
    "16-QAM": {"C20": 0.0, "C40": -0.680, "C42": -0.680, "cluster_count": 16.0},
    "64-QAM": {"C20": 0.0, "C40": -0.619, "C42": -0.619, "cluster_count": 64.0},
    "2-FSK": {"C20": 0.0, "C40": 0.0, "C42": -1.0, "cluster_count": 2.0},
    "4-FSK": {"C20": 0.0, "C40": 0.0, "C42": -1.0, "cluster_count": 4.0},
}


class RuleBasedClassifier:
    """
    Deterministically evaluates signal features against analytic boundaries.
    """

    def __init__(self, fsk_envelope_threshold: float = 0.35):
        self.fsk_envelope_threshold = fsk_envelope_threshold

    def classify(self, analysis: AnalysisContract) -> Tuple[str, float, Dict[str, float]]:
        """
        Classifies modulation using physics and statistical cumulant rules.
        Returns:
            (predicted_class, rule_confidence_score, candidate_scores_dict)
        """
        c20 = abs(analysis.cumulants.C20)
        c40 = analysis.cumulants.C40
        c42 = analysis.cumulants.C42
        env_var = analysis.envelope_variance
        clusters = float(analysis.cluster_metrics.cluster_count)
        snr = analysis.snr_m2m4_db

        scores: Dict[str, float] = {}

        # 1. Check FSK branch based on envelope variance and frequency characteristics
        if env_var > self.fsk_envelope_threshold:
            # High envelope variance indicates non-constant envelope or frequency modulation
            if clusters <= 3 or abs(clusters - 2.0) < abs(clusters - 4.0):
                scores["2-FSK"] = 0.85
                scores["4-FSK"] = 0.30
            else:
                scores["4-FSK"] = 0.85
                scores["2-FSK"] = 0.30

            # Suppress PSK/QAM scores when envelope variance indicates FSK
            for m in ["BPSK", "QPSK", "8-PSK", "16-QAM", "64-QAM"]:
                scores[m] = 0.04
        else:
            # 2. PSK / QAM branch using cumulant Euclidean distance in normalized feature space
            # Weightings: C20 (separates BPSK from all), C40 (separates QPSK from 8-PSK/QAM), C42 (QAM vs PSK), Clusters
            scores["2-FSK"] = 0.10
            scores["4-FSK"] = 0.10

            # BPSK distance
            d_bpsk = np.sqrt(
                4.0 * (c20 - 1.0) ** 2 +
                1.5 * (c40 - (-2.0)) ** 2 +
                1.5 * (c42 - (-2.0)) ** 2 +
                0.2 * (np.log2(max(1.0, clusters)) - np.log2(2.0)) ** 2
            )
            scores["BPSK"] = float(np.exp(-d_bpsk / 1.5))

            # QPSK distance
            d_qpsk = np.sqrt(
                3.0 * (c20 - 0.0) ** 2 +
                2.0 * (c40 - 1.0) ** 2 +
                1.5 * (c42 - (-1.0)) ** 2 +
                0.3 * (np.log2(max(1.0, clusters)) - np.log2(4.0)) ** 2
            )
            scores["QPSK"] = float(np.exp(-d_qpsk / 1.2))

            # 8-PSK distance
            d_8psk = np.sqrt(
                3.0 * (c20 - 0.0) ** 2 +
                2.0 * (c40 - 0.0) ** 2 +
                1.5 * (c42 - (-1.0)) ** 2 +
                0.4 * (np.log2(max(1.0, clusters)) - np.log2(8.0)) ** 2
            )
            scores["8-PSK"] = float(np.exp(-d_8psk / 1.2))

            # 16-QAM distance
            d_16qam = np.sqrt(
                3.0 * (c20 - 0.0) ** 2 +
                2.0 * (c40 - (-0.680)) ** 2 +
                2.0 * (c42 - (-0.680)) ** 2 +
                0.5 * (np.log2(max(1.0, clusters)) - np.log2(16.0)) ** 2
            )
            scores["16-QAM"] = float(np.exp(-d_16qam / 1.2))

            # 64-QAM distance (demands higher SNR)
            d_64qam = np.sqrt(
                3.0 * (c20 - 0.0) ** 2 +
                2.0 * (c40 - (-0.619)) ** 2 +
                2.0 * (c42 - (-0.619)) ** 2 +
                0.6 * (np.log2(max(1.0, clusters)) - np.log2(64.0)) ** 2
            )
            qam64_score = float(np.exp(-d_64qam / 1.2))
            if snr < 15.0:
                qam64_score *= max(0.1, snr / 15.0)
            scores["64-QAM"] = qam64_score

        # Normalize candidate scores to a probability-like sum
        total = sum(scores.values()) + 1e-9
        norm_scores = {k: float(v / total) for k, v in scores.items()}

        best_mod = max(norm_scores, key=norm_scores.get)
        best_score = norm_scores[best_mod]

        return best_mod, best_score, norm_scores
