"""
SpectralQ Hypothesis Engine V1.

Implements in strict order:
1. Candidate generation: 175 combinations (7 modulations x 5 interleavers x 5 FECs).
   LDPC is explicitly tagged as UNSUPPORTED (never silently dropped or faked).
2. Coarse pruning using classifier hints, SNR operational floors, and code-family length plausibility.
3. Fine evaluation per surviving candidate with four explicit evidence states:
   PASS, FAIL, NOT_RUN, UNAVAILABLE.
4. Evidence collection persisting evidence list, failed checks, and unsupported components.
5. Deterministic ranking by final rank score (strictly for ranking, NOT confidence).
"""

from typing import Any, Dict, List, Optional, Tuple
from spectralq.contracts.schemas import (
    AnalysisContract,
    ClassifierOutputContract,
    DecoderOutputContract,
    DecoderStatus,
    CrcStatus,
    EvidenceStatus,
    EvidenceItem,
)
from spectralq.hypothesis.registry import (
    MODULATIONS,
    INTERLEAVERS,
    FEC_SCHEMES,
    SUPPORTED_FEC,
    UNSUPPORTED_FEC,
    MODULATION_MIN_SNR,
    FEC_MIN_PLAUSIBLE_BITS,
)
from spectralq.hypothesis.candidate import HypothesisCandidate


class HypothesisEngineV1:
    """
    Hypothesis search and physical verification engine.
    """

    def __init__(self, snr_pruning_margin_db: float = 3.0):
        self.snr_pruning_margin_db = snr_pruning_margin_db

    def generate_all_candidates(self) -> List[HypothesisCandidate]:
        """
        Step 1: Candidate Generation (Full Cross-Product: 7 x 5 x 5 = 175).
        Tags unsupported components (LDPC) immediately.
        """
        candidates: List[HypothesisCandidate] = []

        for mod in MODULATIONS:
            for intl in INTERLEAVERS:
                for fec in FEC_SCHEMES:
                    unsupported: List[str] = []
                    status = "EVALUATED"
                    rejection_reason = None

                    if fec in UNSUPPORTED_FEC:
                        status = "UNSUPPORTED"
                        unsupported.append(f"fec:{fec}")
                        rejection_reason = f"FEC scheme '{fec.upper()}' is unsupported in upstream DSP suite (never fabricated)"

                    cand = HypothesisCandidate(
                        modulation=mod,
                        interleaver=intl,
                        fec=fec,
                        status=status,
                        unsupported_components=unsupported,
                        rejection_reason=rejection_reason,
                    )

                    # If unsupported, record UNAVAILABLE evidence check
                    if status == "UNSUPPORTED":
                        cand.add_evidence(
                            evidence_id=f"EV_CAP_{mod}_{intl}_{fec}",
                            source="hypothesis_registry",
                            check_name="fec_support",
                            status=EvidenceStatus.UNAVAILABLE,
                            value=fec,
                            explanation=f"FEC scheme '{fec}' has no physical decoder implementation available",
                        )

                    candidates.append(cand)

        return candidates

    def apply_coarse_pruning(
        self,
        candidates: List[HypothesisCandidate],
        analysis: AnalysisContract,
        classifier_output: Optional[ClassifierOutputContract] = None,
        decoder_output: Optional[DecoderOutputContract] = None,
    ) -> None:
        """
        Step 2: Coarse Pruning using measurement plausibility and classifier hints.
        Deprioritizes candidates; never hard-deletes without fallback.
        """
        snr = analysis.estimates.snr.value
        probs = classifier_output.ml_probabilities if classifier_output else {}

        # Extract decoded bitstream length if available
        bit_len = 0
        if decoder_output:
            if isinstance(decoder_output.decoded_bits, str):
                bit_len = len(decoder_output.decoded_bits)
            elif isinstance(decoder_output.decoded_bits, list):
                bit_len = len(decoder_output.decoded_bits)
            elif isinstance(decoder_output.decoded_bits, int):
                bit_len = decoder_output.decoded_bits

        for cand in candidates:
            # Do not re-prune already unsupported candidates
            if cand.status == "UNSUPPORTED":
                continue

            # 2a. SNR Plausibility Check
            min_snr = MODULATION_MIN_SNR.get(cand.modulation, 0.0)
            if snr < (min_snr - self.snr_pruning_margin_db):
                is_top_ml = bool(classifier_output and cand.modulation == classifier_output.ml_prediction)
                cand.add_evidence(
                    evidence_id=f"EV_SNR_{cand.modulation}",
                    source="measurement_plausibility",
                    check_name="snr_floor",
                    status=EvidenceStatus.FAIL,
                    value=snr,
                    explanation=f"SNR ({snr:.1f} dB) is below physical operational floor for {cand.modulation} ({min_snr:.1f} dB)",
                )
                if not is_top_ml:
                    cand.status = "PRUNED"
                    cand.rejection_reason = (
                        f"SNR ({snr:.1f} dB) is below physical operational floor "
                        f"for {cand.modulation} ({min_snr:.1f} dB)"
                    )
                    continue

            # 2b. Code Family / Bitstream Length Incompatibility
            min_bits = FEC_MIN_PLAUSIBLE_BITS.get(cand.fec, 1)
            if bit_len > 0 and bit_len < min_bits and cand.fec not in ["none", "ldpc"]:
                cand.status = "PRUNED"
                cand.rejection_reason = (
                    f"Decoded payload length ({bit_len} bits) is insufficient for "
                    f"{cand.fec} minimum block structure ({min_bits} bits)"
                )
                cand.add_evidence(
                    evidence_id=f"EV_LEN_{cand.fec}",
                    source="code_family_plausibility",
                    check_name="block_length_compatibility",
                    status=EvidenceStatus.FAIL,
                    value=bit_len,
                    explanation=cand.rejection_reason,
                )
                continue

            # 2c. Classifier Exclusion Check (Deprioritization)
            # Only prune if classifier probability is negligible (< 0.005) AND not top class
            mod_prob = probs.get(cand.modulation, 0.5)
            cand.prior_score = float(mod_prob)
            if classifier_output and mod_prob < 0.005 and cand.modulation != classifier_output.ml_prediction:
                cand.status = "PRUNED"
                cand.rejection_reason = (
                    f"Classifier confidence for {cand.modulation} is negligible ({mod_prob:.4f})"
                )
                cand.add_evidence(
                    evidence_id=f"EV_ML_{cand.modulation}",
                    source="classifier_hint",
                    check_name="ml_probability_floor",
                    status=EvidenceStatus.FAIL,
                    value=mod_prob,
                    explanation=cand.rejection_reason,
                )

    def evaluate_fine_evidence(
        self,
        candidates: List[HypothesisCandidate],
        decoder_output: Optional[DecoderOutputContract] = None,
    ) -> None:
        """
        Step 3 & 4: Fine Evaluation & Evidence Collection per Candidate.
        Evaluates physical sync/pattern match, CRC/checksum, and re-encode BER.
        All 4 states (PASS, FAIL, NOT_RUN, UNAVAILABLE) are explicitly assigned.
        """
        for cand in candidates:
            # Skip unsupported and pruned candidates from physical decoder matching
            if cand.status in ["UNSUPPORTED", "PRUNED"]:
                continue

            if decoder_output is None:
                # Decoder not run at all
                cand.add_evidence(
                    evidence_id=f"EV_DEC_{cand.modulation}_{cand.interleaver}_{cand.fec}",
                    source="decoder_pipeline",
                    check_name="physical_verification",
                    status=EvidenceStatus.UNAVAILABLE,
                    value=None,
                    explanation="Decoder output unavailable for evaluation",
                )
                cand.verification_score = 0.10
                continue

            # Check if this candidate corresponds to what the decoder actually configured/detected
            is_matching_fec = (decoder_output.fec_used.lower() == cand.fec.lower())
            is_matching_intl = (decoder_output.interleaver_used.lower() == cand.interleaver.lower())

            if is_matching_fec and is_matching_intl:
                verif_score = 0.20

                # 1. Sync / Pattern Match Check
                # If decoder status is OK, sync was found
                if decoder_output.status == DecoderStatus.OK:
                    cand.add_evidence(
                        evidence_id=f"EV_SYNC_{cand.modulation}",
                        source="demodulator",
                        check_name="sync_pattern_match",
                        status=EvidenceStatus.PASS,
                        value=True,
                        explanation="Preamble / frame synchronization pattern matched",
                    )
                    verif_score += 0.30
                else:
                    cand.add_evidence(
                        evidence_id=f"EV_SYNC_{cand.modulation}",
                        source="demodulator",
                        check_name="sync_pattern_match",
                        status=EvidenceStatus.FAIL,
                        value=False,
                        explanation=f"Demodulation/sync failed: {decoder_output.failure_reason or 'No sync'}",
                    )

                # 2. CRC / Checksum Integrity Check
                if decoder_output.crc_status == CrcStatus.PASS:
                    cand.add_evidence(
                        evidence_id=f"EV_CRC_{cand.modulation}",
                        source="decoder",
                        check_name="crc_checksum",
                        status=EvidenceStatus.PASS,
                        value="pass",
                        explanation="Frame CRC verification passed with 0 syndrome errors",
                    )
                    verif_score += 0.35
                elif decoder_output.crc_status == CrcStatus.FAIL:
                    cand.add_evidence(
                        evidence_id=f"EV_CRC_{cand.modulation}",
                        source="decoder",
                        check_name="crc_checksum",
                        status=EvidenceStatus.FAIL,
                        value="fail",
                        explanation="CRC checksum verification failed (nonzero residual)",
                    )
                    verif_score = max(0.05, verif_score - 0.20)
                else:
                    cand.add_evidence(
                        evidence_id=f"EV_CRC_{cand.modulation}",
                        source="decoder",
                        check_name="crc_checksum",
                        status=EvidenceStatus.NOT_RUN,
                        value="not_run",
                        explanation="CRC check was not executed for this mode",
                    )

                # 3. Re-encode Comparison / BER Residual
                if decoder_output.reencode_ber is not None:
                    ber = decoder_output.reencode_ber
                    if ber <= 0.02:
                        cand.add_evidence(
                            evidence_id=f"EV_BER_{cand.modulation}",
                            source="reencoder",
                            check_name="reencode_ber_residual",
                            status=EvidenceStatus.PASS,
                            value=ber,
                            explanation=f"Re-encoded bitstream matched with low residual BER ({ber:.4f})",
                        )
                        verif_score += 0.15
                    else:
                        cand.add_evidence(
                            evidence_id=f"EV_BER_{cand.modulation}",
                            source="reencoder",
                            check_name="reencode_ber_residual",
                            status=EvidenceStatus.FAIL,
                            value=ber,
                            explanation=f"High re-encode BER ({ber:.4f}) exceeds threshold (0.02)",
                        )
                        verif_score = max(0.05, verif_score - 0.15)
                else:
                    cand.add_evidence(
                        evidence_id=f"EV_BER_{cand.modulation}",
                        source="reencoder",
                        check_name="reencode_ber_residual",
                        status=EvidenceStatus.UNAVAILABLE,
                        value=None,
                        explanation="Re-encode verification residual not computed",
                    )

                cand.verification_score = float(min(1.0, max(0.0, verif_score)))
            else:
                # Candidate does not match the active decoder run: physical checks were NOT_RUN for it
                cand.add_evidence(
                    evidence_id=f"EV_DEC_{cand.modulation}_{cand.interleaver}_{cand.fec}",
                    source="decoder",
                    check_name="physical_verification",
                    status=EvidenceStatus.NOT_RUN,
                    value=None,
                    explanation=f"Physical decoder ran {decoder_output.fec_used}/{decoder_output.interleaver_used}; not run for this candidate",
                )
                cand.verification_score = 0.10

    def rank_candidates(self, candidates: List[HypothesisCandidate]) -> List[HypothesisCandidate]:
        """
        Step 5: Deterministic Ranking.
        Calculates final_rank_score for ranking (NOT a confidence percentage)
        and sorts with complete determinism.
        """
        for cand in candidates:
            if cand.status == "UNSUPPORTED":
                cand.final_rank_score = 0.0
            elif cand.status == "PRUNED":
                cand.final_rank_score = 0.0
            else:
                # Calculate rank score combining prior and physical verification
                score = 0.40 * cand.prior_score + 0.60 * cand.verification_score
                # Severe penalty if any physical decoder check evaluated to FAIL
                physical_fails = [c for c in cand.failed_checks if c in ("sync_pattern_match", "crc_checksum", "reencode_ber_residual")]
                if physical_fails:
                    score *= 0.20
                cand.final_rank_score = float(min(1.0, max(0.0, score)))

        # Deterministic sorting:
        # 1. EVALUATED (2) > PRUNED (1) > UNSUPPORTED (0)
        # 2. final_rank_score descending
        # 3. prior_score descending
        # 4. Lexicographical tie-break: modulation, interleaver, fec
        def sort_key(c: HypothesisCandidate):
            status_order = 2 if c.status == "EVALUATED" else (1 if c.status == "PRUNED" else 0)
            intl_idx = INTERLEAVERS.index(c.interleaver) if c.interleaver in INTERLEAVERS else 99
            fec_idx = FEC_SCHEMES.index(c.fec) if c.fec in FEC_SCHEMES else 99
            return (
                status_order,
                round(c.final_rank_score, 6),
                round(c.prior_score, 6),
                -MODULATIONS.index(c.modulation),  # prefer earlier in registry
                -intl_idx,  # prefer 'none' (index 0) over complex interleaver when tied
                -fec_idx,   # prefer 'none' (index 0) over complex FEC when tied
            )

        candidates.sort(key=sort_key, reverse=True)
        return candidates

    def evaluate_candidate_with_decoder(
        self,
        cand: HypothesisCandidate,
        decoder_output: DecoderOutputContract,
    ) -> None:
        """
        Step 3 & 4 (Per-Candidate Fine Evaluation):
        Evaluates physical sync/pattern match, CRC/checksum, and re-encode BER
        for a specific candidate against its own decoder execution.
        """
        if cand.status in ["UNSUPPORTED", "PRUNED"]:
            return

        verif_score = 0.20

        # 1. Sync / Pattern Match Check
        if decoder_output.status == DecoderStatus.OK:
            cand.add_evidence(
                evidence_id=f"EV_SYNC_{cand.modulation}_{cand.interleaver}_{cand.fec}",
                source="demodulator",
                check_name="sync_pattern_match",
                status=EvidenceStatus.PASS,
                value=True,
                explanation=f"Demodulation & symbol lock succeeded for {cand.modulation}",
            )
            verif_score += 0.30

            # FEC matching check
            fec_match = (decoder_output.fec_used.lower() == cand.fec.lower()) or (cand.fec == "none" and decoder_output.fec_used.lower() in ("none", "auto"))
            if fec_match and cand.fec != "none":
                verif_score += 0.20
            elif cand.fec != "none":
                verif_score = max(0.05, verif_score - 0.15)

            # Interleaver matching check
            intl_match = (decoder_output.interleaver_used.lower() == cand.interleaver.lower()) or (cand.interleaver == "none" and decoder_output.interleaver_used.lower() in ("none", ""))
            if intl_match and cand.interleaver != "none":
                verif_score += 0.10
            elif cand.interleaver != "none":
                verif_score = max(0.05, verif_score - 0.10)
        else:
            cand.add_evidence(
                evidence_id=f"EV_SYNC_{cand.modulation}_{cand.interleaver}_{cand.fec}",
                source="demodulator",
                check_name="sync_pattern_match",
                status=EvidenceStatus.FAIL,
                value=False,
                explanation=f"Demodulation/sync failed: {decoder_output.failure_reason or 'No sync'}",
            )

        # 2. CRC / Checksum Integrity Check
        if decoder_output.crc_status == CrcStatus.PASS:
            cand.add_evidence(
                evidence_id=f"EV_CRC_{cand.modulation}_{cand.interleaver}_{cand.fec}",
                source="decoder",
                check_name="crc_checksum",
                status=EvidenceStatus.PASS,
                value="pass",
                explanation="Frame CRC verification passed with 0 syndrome errors",
            )
            verif_score += 0.35
        elif decoder_output.crc_status == CrcStatus.FAIL:
            cand.add_evidence(
                evidence_id=f"EV_CRC_{cand.modulation}_{cand.interleaver}_{cand.fec}",
                source="decoder",
                check_name="crc_checksum",
                status=EvidenceStatus.FAIL,
                value="fail",
                explanation="CRC checksum verification failed (nonzero residual)",
            )
            verif_score = max(0.05, verif_score - 0.20)
        else:
            cand.add_evidence(
                evidence_id=f"EV_CRC_{cand.modulation}_{cand.interleaver}_{cand.fec}",
                source="decoder",
                check_name="crc_checksum",
                status=EvidenceStatus.NOT_RUN,
                value="not_run",
                explanation="CRC check was not executed for this mode",
            )

        # 3. Re-encode Comparison / BER Residual
        if decoder_output.reencode_ber is not None:
            ber = decoder_output.reencode_ber
            if ber <= 0.05:
                cand.add_evidence(
                    evidence_id=f"EV_BER_{cand.modulation}_{cand.interleaver}_{cand.fec}",
                    source="reencoder",
                    check_name="reencode_ber_residual",
                    status=EvidenceStatus.PASS,
                    value=ber,
                    explanation=f"Re-encoded bitstream matched with low residual BER ({ber:.4f})",
                )
                verif_score += 0.25
            else:
                cand.add_evidence(
                    evidence_id=f"EV_BER_{cand.modulation}_{cand.interleaver}_{cand.fec}",
                    source="reencoder",
                    check_name="reencode_ber_residual",
                    status=EvidenceStatus.FAIL,
                    value=ber,
                    explanation=f"High re-encode BER ({ber:.4f}) exceeds threshold (0.05)",
                )
                verif_score = max(0.05, verif_score - 0.15)
        else:
            status_val = EvidenceStatus.UNAVAILABLE if cand.fec == "none" else EvidenceStatus.NOT_RUN
            cand.add_evidence(
                evidence_id=f"EV_BER_{cand.modulation}_{cand.interleaver}_{cand.fec}",
                source="reencoder",
                check_name="reencode_ber_residual",
                status=status_val,
                value=None,
                explanation="Re-encode verification residual not computed (uncoded or unsupported)",
            )

        cand.verification_score = float(min(1.0, max(0.0, verif_score)))

    def build_hypothesis_trace(
        self,
        candidates: List[HypothesisCandidate],
        top_candidate: HypothesisCandidate,
    ) -> Dict[str, Any]:
        """
        Builds complete diagnostic hypothesis trace matching Phase 5 specifications.
        """
        evaluated_count = sum(1 for c in candidates if c.status == "EVALUATED" and c.verification_score > 0.10)
        pruned_count = sum(1 for c in candidates if c.status == "PRUNED")
        unsupported_count = sum(1 for c in candidates if c.status == "UNSUPPORTED")

        return {
            "candidates_generated": len(candidates),
            "candidates_evaluated": max(1, evaluated_count),
            "candidates_pruned": pruned_count,
            "candidates_unsupported": unsupported_count,
            "top_hypothesis": {
                "modulation": top_candidate.modulation,
                "interleaver": top_candidate.interleaver,
                "fec": top_candidate.fec,
                "final_rank_score": round(top_candidate.final_rank_score, 4),
                "prior_score": round(top_candidate.prior_score, 4),
                "verification_score": round(top_candidate.verification_score, 4),
            },
            "alternatives": [
                {
                    "modulation": c.modulation,
                    "interleaver": c.interleaver,
                    "fec": c.fec,
                    "prior_score": round(c.prior_score, 4),
                    "verification_score": round(c.verification_score, 4),
                    "total_score": round(c.final_rank_score, 4),
                    "status": c.status,
                    "rejection_reason": c.rejection_reason,
                }
                for c in candidates[1:6]
            ],
            "rejection_reasons": [
                {"candidate": f"{c.modulation}_{c.interleaver}_{c.fec}", "reason": c.rejection_reason}
                for c in candidates if c.status == "PRUNED" and c.rejection_reason
            ][:10],
        }

    def run(
        self,
        analysis: AnalysisContract,
        classifier_output: Optional[ClassifierOutputContract] = None,
        decoder_output: Optional[DecoderOutputContract] = None,
    ) -> List[HypothesisCandidate]:
        """
        End-to-end execution of Phase 3 Hypothesis Engine V1.
        """
        # Step 1: Generate full cross-product
        candidates = self.generate_all_candidates()

        # Step 2: Coarse pruning
        self.apply_coarse_pruning(
            candidates=candidates,
            analysis=analysis,
            classifier_output=classifier_output,
            decoder_output=decoder_output,
        )

        # Step 3 & 4: Fine evaluation & evidence collection
        self.evaluate_fine_evidence(
            candidates=candidates,
            decoder_output=decoder_output,
        )

        # Step 5: Deterministic ranking
        ranked = self.rank_candidates(candidates)
        return ranked
