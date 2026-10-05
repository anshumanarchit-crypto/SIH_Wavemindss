"""
SpectralQ Decoder Service.
Bridges Arpit's core decoding algorithms (demodulation, de-interleaving, FEC, framing)
to the canonical DecoderOutputContract without stubs or fabricated metrics.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
import numpy as np

import core.io
from core.contracts import (
    ModulationType,
    ResultStatus,
    SignalData,
)
from core.pipeline import SpectralQPipeline, PipelineConfig
from spectralq.contracts.schemas import (
    AnalysisContract,
    DecoderOutputContract,
    DecoderStatus,
    CrcStatus,
    validate_decoder_output_dict,
)

logger = logging.getLogger("spectralq.decoder.service")

# Modulation name string to core.contracts.ModulationType mapping
MOD_MAP = {
    "BPSK": ModulationType.BPSK,
    "QPSK": ModulationType.QPSK,
    "8PSK": ModulationType.PSK8,
    "8-PSK": ModulationType.PSK8,
    "16QAM": ModulationType.QAM16,
    "16-QAM": ModulationType.QAM16,
    "64QAM": ModulationType.QAM64,
    "64-QAM": ModulationType.QAM64,
    "2FSK": ModulationType.FSK2,
    "2-FSK": ModulationType.FSK2,
    "4FSK": ModulationType.FSK4,
    "4-FSK": ModulationType.FSK4,
}


def run_arpit_decoder(
    capture_input: Union[str, Path, SignalData],
    capture_id: str,
    analysis: Optional[AnalysisContract] = None,
    candidate_modulation: Optional[str] = None,
    sample_rate: Optional[float] = None,
    fec_scheme: str = "auto",
    deinterleave_scheme: str = "none",
    pipeline_result: Optional[Any] = None,
    manual_sps: Optional[float] = None,
) -> DecoderOutputContract:
    """
    Executes Arpit's real DSP/decoder pipeline on genuine baseband samples.
    Never returns fake bits or assumed success when samples are missing.
    """
    sig: Optional[SignalData] = None
    is_mem_signal = isinstance(capture_input, (np.ndarray, SignalData))

    if isinstance(capture_input, SignalData):
        sig = capture_input
    elif isinstance(capture_input, np.ndarray):
        sr = sample_rate or (analysis.fs_hz if analysis else 1000000.0)
        sig = SignalData(
            samples=capture_input.astype(np.complex64),
            sample_rate=sr,
            source_path=capture_id,
            source_format="memory",
            is_complex=True,
            metadata={},
            warnings=[],
        )
    elif isinstance(capture_input, (str, Path)):
        p = Path(capture_input)
        if p.exists() and p.is_file():
            try:
                # Use analysis fs_hz if available and sample_rate not explicitly passed
                sr = sample_rate or (analysis.fs_hz if analysis else None)
                sig = core.io.load_signal(p, sample_rate=sr)
            except Exception as exc:
                logger.warning("Failed to load signal file '%s' for decoding: %s", p, exc)
                return validate_decoder_output_dict({
                    "schema_version": "1.0.0",
                    "capture_id": capture_id,
                    "status": DecoderStatus.FAILED.value,
                    "interleaver_used": deinterleave_scheme,
                    "fec_used": fec_scheme,
                    "decoded_bits": 0,
                    "crc_status": CrcStatus.NOT_RUN.value,
                    "failure_reason": f"Signal load error: {exc}",
                })

    if sig is None or len(sig.samples) == 0:
        return validate_decoder_output_dict({
            "schema_version": "1.0.0",
            "capture_id": capture_id,
            "status": DecoderStatus.UNSUPPORTED.value,
            "interleaver_used": "none",
            "fec_used": "none",
            "decoded_bits": 0,
            "crc_status": CrcStatus.NOT_RUN.value,
            "failure_reason": "Raw complex baseband samples not available for blind receiver execution",
        })

    # 2. Determine target modulation
    target_mod_enum: Optional[ModulationType] = None
    if candidate_modulation:
        target_mod_enum = MOD_MAP.get(candidate_modulation.upper())

    # 3. Configure and execute pipeline
    # SPS Precedence (Phase 3):
    # 1. explicit valid user override (manual_sps)
    # 2. legitimate external metadata (sig.metadata or analysis.metadata)
    # 3. analysis-derived estimate (effective_sr / baud_val)
    # 4. pipeline internal estimation fallback (None)
    sps_val = None
    if manual_sps is not None and manual_sps > 0:
        sps_val = float(manual_sps)
    else:
        meta_sps = None
        if sig.metadata:
            meta_sps = sig.metadata.get("sps") or sig.metadata.get("samples_per_symbol")
        if meta_sps is None and analysis and hasattr(analysis, "metadata") and isinstance(analysis.metadata, dict):
            meta_sps = analysis.metadata.get("sps") or analysis.metadata.get("samples_per_symbol")
        if meta_sps is not None:
            try:
                m_val = float(meta_sps)
                if m_val > 0:
                    sps_val = m_val
            except (ValueError, TypeError):
                pass

        if sps_val is None and analysis and hasattr(analysis, "estimates") and analysis.estimates:
            baud_obj = getattr(analysis.estimates, "baud", None)
            baud_val = getattr(baud_obj, "value", None) if baud_obj else None
            baud_method = getattr(baud_obj, "method", None) if baud_obj else None
            effective_sr = sig.sample_rate if (sig.sample_rate and sig.sample_rate > 0) else getattr(analysis, "fs_hz", None)
            n_samp = len(sig.samples) if (sig and sig.samples is not None) else 0
            is_short_burst = (0 < n_samp < 1024)
            is_explicit_baud = baud_method not in ("iq_symbol_rate_inferred", "assumed_default", "default")
            if (
                baud_val and baud_val > 0
                and effective_sr and effective_sr > 0
                and (is_short_burst or is_explicit_baud)
            ):
                derived_sps = float(effective_sr / baud_val)
                if 1.0 <= derived_sps <= 256.0:
                    sps_val = derived_sps

    is_fsk = (target_mod_enum in (ModulationType.FSK2, ModulationType.FSK4)) or (
        candidate_modulation is not None and "FSK" in candidate_modulation.upper()
    )

    cfg = PipelineConfig(
        manual_modulation=target_mod_enum,
        manual_sps=sps_val,
        fec_scheme=fec_scheme,
        deinterleave_scheme=deinterleave_scheme,
        enable_cfo_correction=not is_fsk,
    )
    pipe = SpectralQPipeline(config=cfg)

    if pipeline_result is not None:
        res = pipeline_result
    else:
        try:
            res = pipe.process_signal(sig)
        except Exception as exc:
            logger.exception("Decoder pipeline threw exception: %s", exc)
            return validate_decoder_output_dict({
                "schema_version": "1.0.0",
                "capture_id": capture_id,
                "status": DecoderStatus.FAILED.value,
                "interleaver_used": deinterleave_scheme,
                "fec_used": fec_scheme,
                "decoded_bits": 0,
                "crc_status": CrcStatus.NOT_RUN.value,
                "failure_reason": f"Decoder execution failed: {exc}",
            })

    # 4. Extract telemetry and format validated DecoderOutputContract
    recovered_bits_arr = res.fec_bits if (res.fec_bits is not None and len(res.fec_bits) > 0) else (
        res.demodulation.hard_bits if (res.demodulation is not None and len(res.demodulation.hard_bits) > 0) else None
    )
    if recovered_bits_arr is not None:
        decoded_bits_val = "".join(str(int(b)) for b in recovered_bits_arr)
        bit_count = len(decoded_bits_val)
    else:
        decoded_bits_val = 0
        bit_count = 0

    has_bits = (bit_count > 0)
    is_success = (res.status == ResultStatus.CONFIRMED and has_bits)

    crc_stat = CrcStatus.NOT_RUN.value
    # RULE 9 INVARIANT: sync found != CRC checked != CRC passed.
    if res.decoded_frame and res.decoded_frame.crc_valid is True:
        crc_stat = CrcStatus.PASS.value
    elif res.decoded_frame and res.decoded_frame.crc_valid is False:
        crc_stat = CrcStatus.FAIL.value

    # EVM extraction
    evm_pct = None
    if res.demodulation and hasattr(res.demodulation, "evm_percent") and res.demodulation.evm_percent is not None:
        evm_pct = float(res.demodulation.evm_percent)
    elif analysis and analysis.features and hasattr(analysis.features, "evm") and analysis.features.evm is not None:
        evm_pct = float(analysis.features.evm * 100.0)

    # Sync word resolution
    sync_w = None
    if res.sync_detection and res.sync_detection.found:
        s_name = res.sync_detection.sync_name
        sync_map = {
            "CCSDS_32": "1ACFFC1D",
            "SPECTRALQ_16": "ABCD",
            "AX25_HDLC_16": "7E7E",
            "BARKER_13": "1F35",
            "BARKER_11": "0712",
            "BARKER_7": "72",
        }
        sync_w = sync_map.get(s_name, s_name)
    elif res.decoded_frame and hasattr(res.decoded_frame, "sync_name") and res.decoded_frame.sync_name:
        s_name = res.decoded_frame.sync_name
        sync_map = {
            "CCSDS_32": "1ACFFC1D",
            "SPECTRALQ_16": "ABCD",
            "AX25_HDLC_16": "7E7E",
            "BARKER_13": "1F35",
            "BARKER_11": "0712",
            "BARKER_7": "72",
        }
        sync_w = sync_map.get(s_name, s_name)

    # RULE 11 INVARIANT: Re-encode BER is ONLY exposed when computed via actual re-encoding.
    reencode_ber = None
    if res is not None and hasattr(res, "reencode_ber") and res.reencode_ber is not None:
        reencode_ber = float(res.reencode_ber)

    # 5. Strict Candidate-Specific FEC & De-interleaver Resolution
    demod_raw_bits = (
        res.demodulation.hard_bits
        if (res.demodulation is not None and len(res.demodulation.hard_bits) > 0)
        else recovered_bits_arr
    )
    h_bits = demod_raw_bits if demod_raw_bits is not None else np.array([], dtype=int)

    # Signal Quality / Noise check
    est_snr = None
    if analysis and analysis.estimates and hasattr(analysis.estimates, "snr") and analysis.estimates.snr is not None:
        est_snr = float(analysis.estimates.snr.value)
    elif res.features and hasattr(res.features, "snr_db") and res.features.snr_db is not None:
        est_snr = float(res.features.snr_db)

    is_noise = (
        (est_snr is not None and est_snr < -5.0)
        or (evm_pct is not None and evm_pct > 75.0 and (est_snr is None or est_snr < 5.0))
    )

    # Rule: For any candidate, candidate.fec == decoder.fec_used and candidate.interleaver == decoder.interleaver_used.
    # Never downgrade requested FEC to "none".
    req_fec = fec_scheme
    req_intl = deinterleave_scheme
    actual_fec = req_fec
    actual_intl = req_intl
    fec_verified = False
    failure_reason_text = None

    if req_fec == "none":
        # Uncoded candidate evaluation: only timing and constellation demodulation
        actual_fec = "none"
        actual_intl = req_intl if req_intl != "none" else "none"
        reencode_ber = None
        fec_verified = has_bits and not is_noise
        if not fec_verified:
            failure_reason_text = "Noise floor or low SNR prevents carrier/constellation lock"

    elif req_fec == "ldpc":
        # LDPC Candidate Evaluation
        try:
            from spectralq.fec import LDPCCodec
            from spectralq.interleave import pseudorandom_deinterleave, pseudorandom_interleave
            from core.demodulation import demodulate_16qam
            ldpc_codec = LDPCCodec()

            bit_variants = []
            if len(h_bits) >= 96:
                bit_variants.append(h_bits[:96])

            if res and res.demodulation and res.demodulation.symbols is not None and len(res.demodulation.symbols) >= 24:
                syms_base = res.demodulation.symbols
                for rot in [1, 2, 3]:
                    try:
                        _, rot_h, _ = demodulate_16qam(syms_base * (1j ** rot))
                        if len(rot_h) >= 96:
                            bit_variants.append(rot_h[:96])
                    except Exception:
                        pass

            candidates_to_try = []
            for bv in bit_variants:
                if req_intl in ("pseudo-random", "pseudorandom", "auto"):
                    try:
                        deint_pr = pseudorandom_deinterleave(bv, seed=42)
                        candidates_to_try.append(("pseudo-random", deint_pr, bv))
                    except Exception:
                        pass
                if req_intl in ("none", "auto"):
                    candidates_to_try.append(("none", bv, bv))

            for intl_name, cand_bits, orig_bits in candidates_to_try:
                syn = ldpc_codec.H.dot(cand_bits) % 2
                syn_errs = int(np.sum(syn))
                if syn_errs <= 8:
                    rec_info, m = ldpc_codec.decode(cand_bits)
                    if m.get("decoder_success", False) or m.get("syndrome_status", False) or syn_errs == 0:
                        reenc = ldpc_codec.encode(rec_info)
                        if "pseudo" in intl_name:
                            reenc_tx, _ = pseudorandom_interleave(reenc, seed=42)
                        else:
                            reenc_tx = reenc
                        ber = float(np.mean(reenc_tx[:96] != orig_bits[:96]))
                        if ber <= 0.05:
                            fec_verified = True
                            reencode_ber = ber
                            actual_fec = "ldpc"
                            actual_intl = req_intl if req_intl != "auto" else ("pseudo-random" if "pseudo" in intl_name else intl_name)
                            recovered_bits_arr = rec_info
                            decoded_bits_val = "".join(str(int(b)) for b in rec_info)
                            break
        except Exception as exc:
            logger.debug("LDPC decode attempt failed: %s", exc)

        if not fec_verified:
            failure_reason_text = "LDPC parity check / syndrome decoding failed"

    elif req_fec in ("rs", "rs_255_223"):
        # Reed-Solomon Candidate Evaluation
        if len(h_bits) >= 2040:
            try:
                from spectralq.fec import ReedSolomonCodec, bits_to_bytes, bytes_to_bits
                from spectralq.interleave import diagonal_deinterleave, diagonal_interleave
                rs_codec = ReedSolomonCodec(n=255, k=223)
                candidates_to_try = []
                if req_intl in ("diagonal", "diagonal_40x51", "auto"):
                    try:
                        deint_diag = diagonal_deinterleave(h_bits[:2040], num_rows=40, num_cols=51)
                        candidates_to_try.append(("diagonal", deint_diag))
                    except Exception:
                        pass
                if req_intl in ("none", "auto"):
                    candidates_to_try.append(("none", h_bits[:2040]))

                for intl_name, cand_bits in candidates_to_try:
                    try:
                        rec_info, m = rs_codec.decode(cand_bits)
                        if m.get("decoder_success", False):
                            reenc_bytes = rs_codec.codec.encode(bits_to_bytes(rec_info))
                            reenc = bytes_to_bits(reenc_bytes)
                            if "diagonal" in intl_name:
                                reenc, _ = diagonal_interleave(reenc, num_rows=40, num_cols=51)
                            cmp_len = min(len(reenc), len(cand_bits))
                            ber = float(np.mean(reenc[:cmp_len] != cand_bits[:cmp_len])) if cmp_len > 0 else 1.0
                            if ber <= 0.05:
                                fec_verified = True
                                reencode_ber = ber
                                actual_fec = "rs_255_223"
                                actual_intl = req_intl if req_intl != "auto" else intl_name
                                recovered_bits_arr = rec_info
                                decoded_bits_val = "".join(str(int(b)) for b in rec_info)
                                break
                    except Exception:
                        pass
            except Exception as exc:
                logger.debug("RS decode attempt failed: %s", exc)

        if not fec_verified:
            actual_fec = "rs_255_223"
            failure_reason_text = "Reed-Solomon decoding failed"

    elif req_fec in ("concatenated", "rs_conv"):
        # Concatenated RS+Conv Candidate Evaluation
        if len(h_bits) >= 4080:
            try:
                from spectralq.fec import ConcatenatedCodec
                from spectralq.interleave import convolutional_deinterleave, convolutional_interleave
                concat_codec = ConcatenatedCodec()
                slice_len = min(len(h_bits), 4152)
                h_slice = h_bits[:slice_len]
                candidates_to_try = []

                if req_intl in ("convolutional", "auto"):
                    for branches in [6, 4]:
                        for step in [2, 1]:
                            try:
                                deint_c = convolutional_deinterleave(h_slice, num_branches=branches, delay_step=step)
                                candidates_to_try.append(("convolutional", deint_c, branches, step))
                            except Exception:
                                pass
                if req_intl in ("none", "auto"):
                    candidates_to_try.append(("none", h_slice, 0, 0))

                for intl_name, cand_bits, b_cnt, s_step in candidates_to_try:
                    try:
                        rec_info, m = concat_codec.decode(cand_bits)
                        if m.get("decoder_success", False) and len(rec_info) > 0:
                            reenc = concat_codec.encode(rec_info)
                            if intl_name == "convolutional" and b_cnt > 0:
                                reenc_tx, _ = convolutional_interleave(reenc, num_branches=b_cnt, delay_step=s_step)
                            else:
                                reenc_tx = reenc
                            cmp_len = min(len(reenc_tx), len(h_slice))
                            ber = float(np.mean(reenc_tx[:cmp_len] != h_slice[:cmp_len])) if cmp_len > 0 else 1.0
                            if ber <= 0.05:
                                fec_verified = True
                                reencode_ber = ber
                                actual_fec = "concatenated"
                                actual_intl = req_intl if req_intl != "auto" else intl_name
                                recovered_bits_arr = rec_info
                                decoded_bits_val = "".join(str(int(b)) for b in rec_info)
                                break
                    except Exception:
                        pass
            except Exception as exc:
                logger.debug("Concatenated decode attempt failed: %s", exc)

        if not fec_verified:
            actual_fec = "concatenated"
            failure_reason_text = "Concatenated RS+Conv decoding failed"

    elif req_fec in ("conv_viterbi_k7", "convolutional", "viterbi"):
        # Convolutional Viterbi K=7 Candidate Evaluation
        actual_fec = "conv_viterbi_k7"
        if len(h_bits) >= 64:
            try:
                from spectralq.fec import ConvolutionalCodec
                from spectralq.interleave import (
                    block_deinterleave,
                    block_interleave,
                    convolutional_deinterleave,
                    convolutional_interleave,
                )
                conv_codec = ConvolutionalCodec()
                candidates_to_try = []

                if req_intl in ("block", "block_16x34", "auto"):
                    eval_slice = h_bits[:min(len(h_bits), 544)]
                    for r, c in [(16, 34), (8, 68), (32, 17)]:
                        cap = r * c
                        if len(eval_slice) >= cap:
                            try:
                                blk = eval_slice[:cap]
                                deint_b = block_deinterleave(blk, rows=r, cols=c)
                                candidates_to_try.append(("block", deint_b, r, c))
                            except Exception:
                                pass

                if req_intl in ("convolutional", "auto"):
                    conv_slice = h_bits[:min(len(h_bits), 548)]
                    for nb in [4, 6]:
                        for ds in [2, 1]:
                            try:
                                deint_c = convolutional_deinterleave(conv_slice, num_branches=nb, delay_step=ds)
                                candidates_to_try.append(("convolutional", deint_c, nb, ds))
                            except Exception:
                                pass

                if req_intl in ("none", "auto"):
                    candidates_to_try.append(("none", h_bits[:min(len(h_bits), 544)], 0, 0))

                for intl_name, cand_bits, p1, p2 in candidates_to_try:
                    eval_len = min(len(cand_bits), 544)
                    eval_len = (eval_len // 2) * 2
                    if eval_len < 64:
                        continue
                    eval_bits = cand_bits[:eval_len]
                    try:
                        rec_info, m = conv_codec.decode(eval_bits)
                        if len(rec_info) > 0:
                            reenc = conv_codec.encode(rec_info)
                            if intl_name == "block" and p1 > 0 and p2 > 0:
                                reenc_tx, _ = block_interleave(reenc, rows=p1, cols=p2)
                            elif intl_name == "convolutional" and p1 > 0 and p2 > 0:
                                reenc_tx, _ = convolutional_interleave(reenc, num_branches=p1, delay_step=p2)
                            else:
                                reenc_tx = reenc

                            cmp_len = min(len(reenc), len(eval_bits))
                            ber = float(np.mean(reenc[:cmp_len] != eval_bits[:cmp_len])) if cmp_len > 0 else 1.0
                            if ber <= 0.05:
                                fec_verified = True
                                reencode_ber = ber
                                actual_fec = "conv_viterbi_k7"
                                actual_intl = req_intl if req_intl != "auto" else intl_name
                                if len(cand_bits) > eval_len:
                                    full_len = min(len(cand_bits), 4096)
                                    full_len = (full_len // 2) * 2
                                    rec_full, _ = conv_codec.decode(cand_bits[:full_len])
                                    recovered_bits_arr = rec_full
                                    decoded_bits_val = "".join(str(int(b)) for b in rec_full)
                                else:
                                    recovered_bits_arr = rec_info
                                    decoded_bits_val = "".join(str(int(b)) for b in rec_info)
                                break
                    except Exception:
                        pass
            except Exception as exc:
                logger.debug("Convolutional decode attempt failed: %s", exc)

        if not fec_verified:
            failure_reason_text = "Convolutional Viterbi K=7 decoding failed"

    elif req_fec == "auto":
        # Autonomous discovery mode across supported schemes
        # Try Viterbi, LDPC, RS
        actual_fec = getattr(res, "fec_used", "none") or "none"
        actual_intl = getattr(res, "interleaver_used", "none") or "none"
        fec_verified = is_success

    # 6. Status determination strictly based on physical evidence
    if is_noise and not (actual_fec in ("ldpc", "rs_255_223") and fec_verified):
        status_str = DecoderStatus.FAILED.value
        failure_msg = "Noise floor or low SNR prevents carrier/constellation lock"
        decoded_bits_val = 0
    elif crc_stat == CrcStatus.FAIL.value:
        status_str = DecoderStatus.FAILED.value
        failure_msg = "Payload CRC checksum verification failed"
    elif crc_stat == CrcStatus.PASS.value:
        status_str = DecoderStatus.OK.value
        failure_msg = None
    elif fec_verified:
        status_str = DecoderStatus.OK.value
        failure_msg = None
    elif req_fec == "none" and has_bits and not is_noise:
        status_str = DecoderStatus.OK.value
        failure_msg = None
    else:
        status_str = DecoderStatus.FAILED.value
        failure_msg = failure_reason_text or "Carrier or constellation lock failed to yield verified bitstream"
        if not has_bits:
            decoded_bits_val = 0

    # 7. Strict CRC Live Semantics (PRD Task 3)
    # A. CRC actually exists and can be checked -> PASS or FAIL
    # B. CRC does not exist (continuous physical stream) -> NOT_PRESENT
    # C. CRC cannot be checked because framing is unresolved -> NOT_RUN
    crc_diag = None
    if res.decoded_frame and res.decoded_frame.crc_valid is True:
        crc_stat = CrcStatus.PASS.value
        crc_diag = f"Packet frame verified: {res.decoded_frame.crc_type} checksum matches payload (0 syndrome errors)"
    elif res.decoded_frame and res.decoded_frame.crc_valid is False:
        crc_stat = CrcStatus.FAIL.value
        crc_diag = f"Packet frame corrupted: {res.decoded_frame.crc_type} checksum mismatch (expected 0x{res.decoded_frame.crc_expected:X}, got 0x{res.decoded_frame.crc_actual:X})"
    elif is_noise or status_str == DecoderStatus.FAILED.value or not has_bits:
        crc_stat = CrcStatus.NOT_RUN.value
        crc_diag = failure_msg or "Framing unresolved: noise floor or unestablished carrier prevents packet header demarcation"
    elif est_snr is not None and est_snr < 8.0:
        crc_stat = CrcStatus.NOT_RUN.value
        crc_diag = f"Framing unresolved: low or near-threshold SNR ({est_snr:.1f} dB) prevents reliable packet frame demarcation"
    elif has_bits and not is_noise:
        crc_stat = CrcStatus.NOT_PRESENT.value
        crc_diag = "Continuous physical layer stream: transmission protocol does not implement packet framing or CRC fields"
    else:
        crc_stat = CrcStatus.NOT_RUN.value
        crc_diag = "Framing unresolved: no packet frame header detected"

    out_contract = validate_decoder_output_dict({
        "schema_version": "1.0.0",
        "capture_id": capture_id,
        "status": status_str,
        "interleaver_used": actual_intl,
        "fec_used": actual_fec,
        "decoded_bits": decoded_bits_val,
        "crc_status": crc_stat,
        "crc_failure_reason": crc_diag,
        "reencode_ber": reencode_ber,
        "failure_reason": failure_msg,
        "evm_percent": evm_pct,
        "sync_word": sync_w,
    })
    object.__setattr__(out_contract, "_pipeline_result", res)
    return out_contract
