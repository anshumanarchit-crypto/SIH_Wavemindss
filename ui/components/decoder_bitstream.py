"""
Workspace 4: Decoder & Bitstream (Blind Demodulation & Bitstream Intelligence).
Visualizes the multi-stage decoding pipeline (Demod -> De-interleaver -> viterbi -> RS -> Frame Sync)
and provides deep Bitstream Explorer tabs (Bits, Hex, Bytes, Frame Structure, Payload, Statistics).
"""

import math
from typing import Optional, List
import streamlit as st

from ui.adapters import NormalizedDecoder, NormalizedResult
from ui.styles.theme import get_theme_tokens, TOOLTIPS


def _calculate_entropy(data_bytes: bytes) -> float:
    """Calculates Shannon entropy in bits/byte."""
    if not data_bytes:
        return 0.0
    freqs = {}
    for b in data_bytes:
        freqs[b] = freqs.get(b, 0) + 1
    n = len(data_bytes)
    ent = 0.0
    for count in freqs.values():
        p = count / n
        ent -= p * math.log2(p)
    return ent


def _format_hex_dump(data_bytes: bytes, max_rows: int = 32) -> str:
    """Formats bytes into a standard 16-byte hex dump with address and ASCII sidebar."""
    lines = []
    total_len = min(len(data_bytes), max_rows * 16)
    for offset in range(0, total_len, 16):
        chunk = data_bytes[offset : offset + 16]
        hex_parts = [f"{b:02x}" for b in chunk]
        # Pad to 16 bytes if last line
        while len(hex_parts) < 16:
            hex_parts.append("  ")
        hex_str = " ".join(hex_parts[:8]) + "  " + " ".join(hex_parts[8:])
        ascii_chars = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        lines.append(f"{offset:08x}  {hex_str}  |{ascii_chars}|")
    if len(data_bytes) > total_len:
        lines.append(f"... ({len(data_bytes) - total_len} additional bytes omitted from view) ...")
    return "\n".join(lines)


def render_decoder_bitstream(
    decoder: Optional[NormalizedDecoder],
    result: Optional[NormalizedResult],
) -> None:
    """Renders the Decoder & Bitstream workspace."""
    st.markdown("## 🔓 Decoder & Bitstream Intelligence")
    st.caption("Stage 7-9: Blind Demodulation, FEC Chain (Arpit), and Bitstream Forensics.")

    tokens = get_theme_tokens()

    # 1. Visual Decoder Chain Diagram
    st.markdown("### ⛓️ Pipeline Decoding & Integrity Architecture")

    # Evaluate active stages from decoder data
    demod_active = decoder is not None and decoder.raw_bits is not None
    interleaver_active = decoder is not None and decoder.interleaver_used
    viterbi_active = decoder is not None and decoder.viterbi_used
    rs_active = decoder is not None and decoder.reed_solomon_used
    crc_passed = decoder is not None and decoder.crc_passed

    chain_cols = st.columns(5)
    with chain_cols[0]:
        badge = "badge-pass" if demod_active else "badge-unavail"
        st.markdown(
            f"""
            <div class="sq-card" style="text-align:center;">
                <div class="sq-card-title">STAGE 1</div>
                <div style="font-weight:700; margin:0.3rem 0;">DEMODULATOR</div>
                <span class="sq-badge {badge}">{"ACTIVE" if demod_active else "BYPASS"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with chain_cols[1]:
        badge = "badge-pass" if interleaver_active else "badge-notrun"
        label = decoder.interleaver_type if (decoder and interleaver_active) else "BYPASS"
        st.markdown(
            f"""
            <div class="sq-card" style="text-align:center;">
                <div class="sq-card-title">STAGE 2</div>
                <div style="font-weight:700; margin:0.3rem 0;">DE-INTERLEAVER</div>
                <span class="sq-badge {badge}">{label.upper()}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with chain_cols[2]:
        badge = "badge-pass" if viterbi_active else "badge-notrun"
        st.markdown(
            f"""
            <div class="sq-card" style="text-align:center;">
                <div class="sq-card-title">STAGE 3</div>
                <div style="font-weight:700; margin:0.3rem 0;">INNER FEC (VITERBI)</div>
                <span class="sq-badge {badge}">{"RATE 1/2 (K=7)" if viterbi_active else "BYPASS"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with chain_cols[3]:
        badge = "badge-pass" if rs_active else "badge-notrun"
        st.markdown(
            f"""
            <div class="sq-card" style="text-align:center;">
                <div class="sq-card-title">STAGE 4</div>
                <div style="font-weight:700; margin:0.3rem 0;">OUTER FEC (RS)</div>
                <span class="sq-badge {badge}">{"RS(255,223)" if rs_active else "BYPASS"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with chain_cols[4]:
        badge = "badge-pass" if crc_passed else ("badge-fail" if (decoder and decoder.crc_checked) else "badge-notrun")
        crc_text = "PASS" if crc_passed else ("FAIL" if (decoder and decoder.crc_checked) else "UNCHECKED")
        st.markdown(
            f"""
            <div class="sq-card" style="text-align:center;">
                <div class="sq-card-title">STAGE 5</div>
                <div style="font-weight:700; margin:0.3rem 0;">FRAME SYNC & CRC</div>
                <span class="sq-badge {badge}">{crc_text}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 2. Decoder Summary Telemetry
    st.markdown("### 📊 Decoding Telemetry & Error Metrics")
    d1, d2, d3, d4 = st.columns(4)

    with d1:
        if decoder and decoder.ber is not None:
            st.metric("Bit Error Rate (BER)", f"{decoder.ber:.3e}", "Post-Demodulation")
        else:
            st.metric("Bit Error Rate (BER)", "UNAVAILABLE", "Not computed without ground truth")
    with d2:
        evm_txt = f"{decoder.evm_percent:.1f}%" if (decoder and decoder.evm_percent is not None) else "N/A"
        st.metric("Constellation EVM", evm_txt, "RMS Error")
    with d3:
        sync_txt = decoder.sync_word or "None Detected" if decoder else "N/A"
        st.metric("Detected Sync Word", sync_txt, "Frame Preamble")
    with d4:
        bits_count = len(decoder.raw_bits) if (decoder and decoder.raw_bits) else 0
        st.metric("Recovered Bit Count", f"{bits_count:,} bits", "Bitstream Length")

    st.markdown("---")

    # 3. Bitstream Explorer Tabs
    st.markdown("### 🔍 Bitstream Explorer")
    st.caption("Interactive telemetry inspection across binary, hex, byte distribution, frame, and payload layers.")

    raw_bits_str = decoder.raw_bits if (decoder and decoder.raw_bits) else ""
    bitstream_bytes = b""
    if raw_bits_str:
        # Convert bits string to bytes
        clean_bits = "".join(b for b in raw_bits_str if b in ("0", "1"))
        byte_chunks = [clean_bits[i:i+8] for i in range(0, len(clean_bits) - len(clean_bits) % 8, 8)]
        bitstream_bytes = bytes([int(b, 2) for b in byte_chunks])

    b_tabs = st.tabs([
        "0️⃣1️⃣ Bits (Raw)",
        "💻 Hex Dump",
        "🧮 Bytes & Entropy",
        "📐 Frame Structure",
        "📄 Payload Preview",
        "📈 Statistics",
    ])

    # TAB 1: Bits
    with b_tabs[0]:
        st.markdown("#### Raw Binary Bitstream")
        if raw_bits_str:
            st.caption(f"Showing first 1,024 of {len(raw_bits_str):,} bits.")
            st.code(raw_bits_str[:1024], language="text")
            st.download_button(
                "⬇️ Download Raw Bits (.txt)",
                data=raw_bits_str,
                file_name=f"recovered_bits_{decoder.capture_id if decoder else 'capture'}.txt",
                mime="text/plain",
            )
        else:
            st.info("No demodulated bitstream available for this capture.")

    # TAB 2: Hex
    with b_tabs[1]:
        st.markdown("#### Hexadecimal Memory Dump (16-Byte Rows)")
        if bitstream_bytes:
            hex_view = _format_hex_dump(bitstream_bytes, max_rows=32)
            st.code(hex_view, language="text")
        else:
            st.info("No byte data available to dump.")

    # TAB 3: Bytes & Entropy
    with b_tabs[2]:
        st.markdown("#### Shannon Entropy & Byte Distribution")
        if bitstream_bytes:
            entropy = _calculate_entropy(bitstream_bytes)
            ecol1, ecol2 = st.columns([1, 2])
            with ecol1:
                st.metric("Calculated Entropy", f"{entropy:.3f} bits/byte", "Theoretical Max: 8.0")
                if entropy > 7.5:
                    st.caption("High entropy indicates compressed, encrypted, or scrambled data.")
                else:
                    st.caption("Moderate/low entropy indicates structured packet framing or redundancy.")
            with ecol2:
                st.caption(f"Analyzed {len(bitstream_bytes):,} bytes from bitstream.")
        else:
            st.info("No byte data available for entropy calculation.")

    # TAB 4: Frame Structure
    with b_tabs[3]:
        st.markdown("#### Frame Layout & Synchronization")
        if decoder and (decoder.sync_word or decoder.crc_checked):
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                st.markdown(
                    f"""
                    - **Sync Word Preamble:** `0x{decoder.sync_word or 'UNKNOWN'}`
                    - **Frame Synchronized:** `{'YES' if decoder.sync_word else 'NO'}`
                    - **CRC Polynomial:** `CRC-16 / CRC-32 (Standard Telemetry)`
                    - **CRC Check Result:** `{'PASS' if decoder.crc_passed else 'FAIL / UNCHECKED'}`
                    """
                )
            with fcol2:
                st.markdown(
                    f"""
                    - **viterbi Traceback Depth:** `35`
                    - **Reed-Solomon Parity Bytes:** `32`
                    - **Interleaver Matrix:** `{decoder.interleaver_type.upper()}`
                    """
                )
        else:
            st.info("No synchronized frame headers detected in this capture.")

    # TAB 5: Payload Preview
    with b_tabs[4]:
        st.markdown("#### Recovered Payload Preview")
        if bitstream_bytes:
            # Printable preview
            printable = "".join(chr(b) if 32 <= b <= 126 or b in (10, 13) else "." for b in bitstream_bytes[:2048])
            st.text_area("Decoded Payload Excerpt", printable, height=180)
        else:
            st.info("No recovered payload available.")

    # TAB 6: Statistics
    with b_tabs[5]:
        st.markdown("#### Bit Distribution & Transition Density")
        if raw_bits_str:
            ones = raw_bits_str.count("1")
            zeros = raw_bits_str.count("0")
            total = ones + zeros
            ratio_one = (ones / total) * 100.0 if total > 0 else 0.0

            scol1, scol2, scol3 = st.columns(3)
            with scol1:
                st.metric("Bit Balance (1s)", f"{ratio_one:.2f}%", f"{ones:,} ones")
            with scol2:
                st.metric("Bit Balance (0s)", f"{100.0 - ratio_one:.2f}%", f"{zeros:,} zeros")
            with scol3:
                st.metric("Total Counted Bits", f"{total:,}")
        else:
            st.info("No bit statistics available.")
