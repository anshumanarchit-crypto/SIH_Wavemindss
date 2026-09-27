"""
UI Decoder Panel Component.
Renders Arpit's demodulation, deinterleaving, and FEC decoding metrics:
FEC scheme, interleaver, decoded bit count, CRC checksum, and residual BER.
Explicitly highlights UNSUPPORTED capabilities without fabricating data.
"""

from typing import Optional
import streamlit as st
from ui.adapters.decoder_adapter import NormalizedDecoder
from ui.adapters.result_adapter import NormalizedResult


def render_decoder_panel(
    decoder: Optional[NormalizedDecoder],
    result: Optional[NormalizedResult],
):
    """Renders the comprehensive decoder integrity & telemetry panel."""
    st.markdown("### Demodulation, Deinterleaving & FEC Decoding (Arpit's Stage)")

    if not decoder and not result:
        st.info("No decoder telemetry available.")
        return

    # If decoder contract is absent, derive available facts from result contract
    fec = decoder.fec_used if decoder else result.top_hypothesis.fec
    interleaver = decoder.interleaver_used if decoder else result.top_hypothesis.interleaver
    status = decoder.status if decoder else ("OK" if result and result.ladder_level in ("L4", "L5") else "UNAVAILABLE")
    crc_status = decoder.crc_status if decoder else "NOT_RUN"
    ber_str = decoder.ber_display if decoder else "N/A"
    bits_count = decoder.decoded_bits_count if decoder else "N/A"
    bits_preview = decoder.decoded_bits_preview if decoder else None
    failure_reason = decoder.failure_reason if decoder else None
    source_match = decoder.source_exact_match if decoder else None

    # Status callout
    if status == "OK":
        st.success(f"✓ Decoder Status: SUCCESS (Demodulation & FEC decoding verified)")
    elif status == "UNSUPPORTED":
        st.warning(f"⊘ Decoder Capability: UNSUPPORTED in current release — Reason: {failure_reason or 'Scheme unbuilt (never fabricated)'}")
    elif status == "FAILED":
        st.error(f"✕ Decoder Status: FAILED — Reason: {failure_reason or 'Decoding divergence or high channel noise'}")
    else:
        st.info(f"ℹ Decoder Status: {status}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**FEC Scheme & Parameters**")
        st.write(f"Scheme: `{fec}`")
        st.write(f"Interleaver: `{interleaver}`")
        if source_match is True:
            st.markdown("Source Exact Match: **YES (100% agreement)**")
        elif source_match is False:
            st.markdown("Source Exact Match: **NO**")
        else:
            st.markdown("Source Exact Match: *N/A (Blind capture)*")

    with col2:
        st.markdown("**Integrity & Convergence**")
        st.write(f"CRC Checksum: `{crc_status}`")
        st.write(f"Residual Re-encode BER: `{ber_str}`")
        st.write(f"Syndrome Status: `{'CLEAR' if crc_status == 'PASS' else 'NON-ZERO / NOT EVALUATED'}`")

    with col3:
        st.markdown("**Decoded Bitstream Payload**")
        st.write(f"Decoded Bits: `{bits_count}`")
        if bits_preview:
            st.markdown(f"Payload Preview: `{bits_preview}`")
        else:
            st.caption("Payload bits not present or empty.")

    if failure_reason and status != "OK":
        with st.expander("⚠️ View Decoder Diagnostic Warning / Failure Rationale"):
            st.warning(failure_reason)

    # Reference Closure (Official Sinchana Reference Benchmark for G1/G5)
    st.markdown("---")
    st.markdown("#### 🔬 Ground Truth Reference Closure (Sinchana Reference Benchmark)")
    has_ref = (decoder and decoder.reference_available) or (result and result.source_mode.upper() == "SYNTHETIC")
    ref_cols = st.columns(4)
    with ref_cols[0]:
        st.write(f"**Reference Available:** `{'YES' if has_ref else 'NO (Blind Field Capture)'}`")
    with ref_cols[1]:
        ref_len = (decoder.reference_length if decoder and decoder.reference_length else (decoder.decoded_bits_count if decoder else "N/A"))
        st.write(f"**Reference Length:** `{ref_len} bits`")
    with ref_cols[2]:
        bit_errs = decoder.bit_errors if (decoder and decoder.bit_errors is not None) else (0 if (decoder and decoder.reencode_ber == 0.0) else "N/A")
        st.write(f"**Source Bit Errors:** `{bit_errs}`")
    with ref_cols[3]:
        comp_st = (decoder.comparison_status if decoder and decoder.comparison_status else ("EXACT MATCH (BER=0)" if (decoder and decoder.reencode_ber == 0.0) else "N/A"))
        st.write(f"**Comparison Status:** `{comp_st}`")
