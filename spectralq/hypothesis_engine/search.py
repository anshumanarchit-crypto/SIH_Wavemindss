"""
Coarse-to-fine Hypothesis Search Engine.
Explores the Cartesian product of (Modulation x Interleaver x FEC),
applies physical feasibility constraints to prune candidates, evaluates verification
evidence, and ranks hypotheses with full audit reasons.
"""

from typing import Dict, List, Optional, Tuple
from spectralq.contracts.schemas import (
    AnalysisContract,
    ClassifierOutputContract,
    DecoderVerificationContract,
    CandidateStatus,
    HypothesisCandidate,
)
from spectralq.hypothesis_engine.hypotheses import (
    SUPPORTED_MODULATIONS,
    SUPPORTED_INTERLEAVERS,
    SUPPORTED_FECS,
    UNSUPPORTED_FECS,
    MODULATION_MIN_SNR,
)


class HypothesisEngine:
    """
    Evaluates and ranks transmission hypotheses (Modulation x Interleaver x FEC).
    """

    def __init__(self, snr_margin_db: float = 2.0):
        self.snr_margin_db = snr_margin_db

    def evaluate_hypotheses(
        self,
        analysis: AnalysisContract,
        rule_scores: Dict[str, float],
        classifier_output: ClassifierOutputContract,
        decoder_output: Optional[DecoderVerificationContract] = None,
    ) -> List[HypothesisCandidate]:
        """
        Executes coarse-to-fine hypothesis search and produces a complete candidate ledger.
        """
        candidates: List[HypothesisCandidate] = []
        snr = analysis.snr_m2m4_db
        ml_probs = classifier_output.class_probabilities

        # Top candidate hints from Rule and ML
        top_ml = classifier_output.predicted_class
        top_ml_prob = ml_probs.get(top_ml, 0.0)

        # 1. Coarse modulation feasibility check
        feasible_mods: Dict[str, Tuple[bool, Optional[str], float]] = {}
        for mod in SUPPORTED_MODULATIONS:
            min_snr = MODULATION_MIN_SNR.get(mod, 0.0)
            rule_p = rule_scores.get(mod, 0.0)
            ml_p = ml_probs.get(mod, 0.0)
            prior = float(0.4 * rule_p + 0.6 * ml_p)

            # Pruning condition 1: SNR deficiency
            if snr < (min_snr - self.snr_margin_db):
                reason = f"SNR {snr:.1f} dB is below operational threshold for {mod} ({min_snr:.1f} dB)"
                feasible_mods[mod] = (False, reason, prior)
            # Pruning condition 2: Extremely low joint probability
            elif prior < 0.01 and mod != top_ml:
                reason = f"Joint prior probability {prior:.3f} is below minimum evaluation threshold (0.01)"
                feasible_mods[mod] = (False, reason, prior)
            else:
                feasible_mods[mod] = (True, None, prior)

        # 2. Iterate across all Interleaver x FEC combinations
        for mod in SUPPORTED_MODULATIONS:
            is_mod_feasible, mod_rejection_reason, mod_prior = feasible_mods[mod]

            for fec in SUPPORTED_FECS + list(UNSUPPORTED_FECS):
                # Handle unsupported FEC explicitly
                if fec in UNSUPPORTED_FECS:
                    for interleaver in ["none", "block"]:
                        candidates.append(
                            HypothesisCandidate(
                                modulation=mod,
                                interleaver=interleaver,
                                fec=fec,
                                prior_score=mod_prior if is_mod_feasible else 0.0,
                                verification_score=0.0,
                                total_score=0.0,
                                status=CandidateStatus.UNSUPPORTED,
                                rejection_reason=f"FEC scheme '{fec.upper()}' is not supported in DSP suite (unsupported, never fabricated)",
                            )
                        )
                    continue

                for interleaver in SUPPORTED_INTERLEAVERS:
                    if not is_mod_feasible:
                        candidates.append(
                            HypothesisCandidate(
                                modulation=mod,
                                interleaver=interleaver,
                                fec=fec,
                                prior_score=mod_prior,
                                verification_score=0.0,
                                total_score=0.0,
                                status=CandidateStatus.PRUNED,
                                rejection_reason=mod_rejection_reason,
                            )
                        )
                        continue

                    # Evaluate surviving candidate with verification evidence
                    verif_score, verif_reason = self._compute_verification_score(
                        mod=mod,
                        interleaver=interleaver,
                        fec=fec,
                        decoder_output=decoder_output,
                    )

                    # Total score fusion for hypothesis ranking
                    # If decoder succeeded for this combination, it heavily boosts total score
                    total_score = float(min(1.0, 0.40 * mod_prior + 0.60 * verif_score))

                    candidates.append(
                        HypothesisCandidate(
                            modulation=mod,
                            interleaver=interleaver,
                            fec=fec,
                            prior_score=mod_prior,
                            verification_score=verif_score,
                            total_score=total_score,
                            status=CandidateStatus.EVALUATED,
                            rejection_reason=verif_reason,
                        )
                    )

        # Sort candidates: EVALUATED first (sorted by total_score descending), then PRUNED / UNSUPPORTED
        candidates.sort(
            key=lambda c: (
                1 if c.status == CandidateStatus.EVALUATED else 0,
                c.total_score,
                c.prior_score,
            ),
            reverse=True,
        )

        return candidates

    def _compute_verification_score(
        self,
        mod: str,
        interleaver: str,
        fec: str,
        decoder_output: Optional[DecoderVerificationContract],
    ) -> Tuple[float, Optional[str]]:
        """
        Evaluates physical verification evidence from Arpit's demod/decoder.
        """
        if decoder_output is None:
            return 0.10, "Decoder verification data unavailable"

        if decoder_output.status.value in ["UNAVAILABLE", "UNSUPPORTED_FEC"]:
            return 0.05, f"Decoder status: {decoder_output.status.value}"

        base_score = 0.10
        reason = None

        # Check sync detection
        if decoder_output.sync_detected:
            base_score += 0.35 * decoder_output.sync_confidence

        # Check CRC validation
        if decoder_output.crc_valid is True:
            base_score += 0.40
        elif decoder_output.crc_valid is False:
            base_score = max(0.05, base_score - 0.20)
            reason = "CRC validation failed"

        # Check re-encode BER residual
        if decoder_output.reencode_ber is not None:
            ber = decoder_output.reencode_ber
            if ber < 0.01:
                base_score += 0.25
            elif ber < 0.05:
                base_score += 0.15
            elif ber > 0.20:
                base_score = max(0.05, base_score - 0.15)
                reason = f"High re-encode BER ({ber:.3f})"

        # Check FEC match
        if decoder_output.fec_detected:
            if decoder_output.fec_detected.lower() == fec.lower():
                base_score += 0.10
            elif fec != "none":
                base_score = max(0.05, base_score - 0.10)

        # Check Interleaver match
        if decoder_output.interleaver_detected:
            if decoder_output.interleaver_detected.lower() == interleaver.lower():
                base_score += 0.10
            elif interleaver != "none":
                base_score = max(0.05, base_score - 0.05)

        return float(min(1.0, max(0.0, base_score))), reason
