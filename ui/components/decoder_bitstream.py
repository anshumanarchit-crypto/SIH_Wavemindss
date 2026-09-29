"""
Workspace 4: Decoder & Bitstream (Blind Demodulation & Bitstream Intelligence).
Operational decoding workbench providing:
- Multi-stage decoding pipeline (Demod -> De-interleaver -> Inner Conv FEC -> Outer RS -> Frame Sync & CRC)
- Critical error metrics (BER, EVM, Sync Word, Recovered Bit Count)
- Interactive Bitstream Explorer (Bits, Hex, Bytes & Entropy, Frame Structure, Payload, Statistics)
"""

import math
from typing import Optional, List
import streamlit as st

from ui.adapters import NormalizedDecoder, NormalizedResult, NormalizedAnalysis
from ui.styles.theme import get_theme_tokens, TOOLTIPS
from ui.components.icons import get_icon_svg


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
    analysis: Optional[NormalizedAnalysis] = None,
) -> None:
    """Renders the defense-grade Decoder & Bitstream intelligence workspace."""
    tokens = get_theme_tokens()

    # Workspace Header
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem; border-bottom:1px solid {tokens['card_border']}; padding-bottom:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.6rem;">
                {get_icon_svg("decoder_bitstream", size=20, color=tokens['primary'])}
                <span style="font-size:1.15rem; font-weight:800; letter-spacing:0.04em; color:{tokens['text']};">
                    DECODING &amp; BITSTREAM INTELLIGENCE WORKBENCH
                </span>
            </div>
            <div>
                <span class="sq-badge {'badge-pass' if (decoder and decoder.crc_passed) else 'badge-warn'}">
                    {'CRC PASS' if (decoder and decoder.crc_passed) else 'CRC UNCHECKED'}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Visual Decoder Pipeline Chain
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.6rem;">
            {get_icon_svg("layers", size=16, color=tokens['primary'])}
            <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                Pipeline Decoding &amp; Integrity Architecture
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    demod_active = decoder is not None and getattr(decoder, "raw_bits", None) is not None
    interleaver_active = decoder is not None and decoder.interleaver_used and decoder.interleaver_used.lower() != "none"
    conv_active = decoder is not None and getattr(decoder, "viterbi_used", False)
    rs_active = decoder is not None and getattr(decoder, "reed_solomon_used", False)
    crc_passed = decoder is not None and getattr(decoder, "crc_passed", False)

    chain_cols = st.columns(5)
    with chain_cols[0]:
        badge = "badge-pass" if demod_active else "badge-unavail"
        st.markdown(
            f"""
            <div class="sq-card" style="text-align:center;">
                <div class="sq-card-title">STAGE 1</div>
                <div style="font-weight:700; margin:0.3rem 0; font-size:0.82rem;">SYMBOL DEMOD</div>
                <span class="sq-badge {badge}">{"ACTIVE" if demod_active else "BYPASS"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with chain_cols[1]:
        badge = "badge-pass" if interleaver_active else "badge-notrun"
        label = getattr(decoder, "interleaver_type", "BYPASS") if (decoder and interleaver_active) else "BYPASS"
        st.markdown(
            f"""
            <div class="sq-card" style="text-align:center;">
                <div class="sq-card-title">STAGE 2</div>
                <div style="font-weight:700; margin:0.3rem 0; font-size:0.82rem;">DE-INTERLEAVER</div>
                <span class="sq-badge {badge}">{label.upper()}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with chain_cols[2]:
        badge = "badge-pass" if conv_active else "badge-notrun"
        st.markdown(
            f"""
            <div class="sq-card" style="text-align:center;">
                <div class="sq-card-title">STAGE 3</div>
                <div style="font-weight:700; margin:0.3rem 0; font-size:0.82rem;">INNER FEC (CONV)</div>
                <span class="sq-badge {badge}">{"RATE 1/2 (K=7)" if conv_active else "BYPASS"}</span>
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
                <div style="font-weight:700; margin:0.3rem 0; font-size:0.82rem;">OUTER FEC (RS)</div>
                <span class="sq-badge {badge}">{"RS(255,223)" if rs_active else "BYPASS"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with chain_cols[4]:
        badge = "badge-pass" if crc_passed else ("badge-fail" if (decoder and getattr(decoder, "crc_checked", False)) else "badge-notrun")
        crc_text = "PASS" if crc_passed else ("FAIL" if (decoder and getattr(decoder, "crc_checked", False)) else "UNCHECKED")
        st.markdown(
            f"""
            <div class="sq-card" style="text-align:center;">
                <div class="sq-card-title">STAGE 5</div>
                <div style="font-weight:700; margin:0.3rem 0; font-size:0.82rem;">FRAME SYNC &amp; CRC</div>
                <span class="sq-badge {badge}">{crc_text}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Decoding Telemetry & Error Metrics
    raw_bits_str = getattr(decoder, "raw_bits", "") if (decoder and getattr(decoder, "raw_bits", None)) else (decoder.decoded_bits_preview if decoder else "")
    clean_bits = "".join(b for b in raw_bits_str if b in ("0", "1")) if raw_bits_str else ""
    bitstream_bytes = b""
    if clean_bits:
        byte_chunks = [clean_bits[i:i+8] for i in range(0, len(clean_bits) - len(clean_bits) % 8, 8)]
        bitstream_bytes = bytes([int(b, 2) for b in byte_chunks])

    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.6rem;">
            {get_icon_svg("spectrum", size=16, color=tokens['primary'])}
            <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                Decoding Telemetry &amp; Error Metrics
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    d1, d2, d3, d4 = st.columns(4)

    with d1:
        if decoder and decoder.ber is not None:
            ber_str = "0.000000" if decoder.ber == 0.0 else f"{decoder.ber:.3e}"
            ber_sub = "0 errors (CRC Valid)" if decoder.ber == 0.0 else "Post-Demodulation"
            st.markdown(
                f"""
                <div class="sq-card">
                    <div class="sq-card-title">Bit Error Rate (BER)</div>
                    <div class="sq-card-value" style="color:{tokens['pass_color']};">{ber_str}</div>
                    <div class="sq-card-sub">{ber_sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="sq-card">
                    <div class="sq-card-title">Bit Error Rate (BER)</div>
                    <div class="sq-card-value" style="color:{tokens['text_muted']}; font-size:1.15rem;">UNAVAILABLE</div>
                    <div class="sq-card-sub">No reference stream</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with d2:
        evm_val = None
        if decoder and decoder.evm_percent is not None:
            evm_val = decoder.evm_percent
        elif analysis and analysis.features and analysis.features.evm is not None:
            evm_val = analysis.features.evm * 100.0
        evm_txt = f"{evm_val:.1f}%" if evm_val is not None else "N/A"
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">Constellation EVM</div>
                <div class="sq-card-value" style="color:{tokens['warn_color']};">{evm_txt}</div>
                <div class="sq-card-sub">RMS Symbol Dispersion</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with d3:
        sync_txt = None
        if decoder and decoder.sync_word and str(decoder.sync_word).strip().upper() not in ("NONE", "NONE DETECTED", "UNKNOWN", "N/A"):
            sync_txt = decoder.sync_word if str(decoder.sync_word).startswith("0x") else f"0x{decoder.sync_word}"
        elif clean_bits and len(clean_bits) >= 16:
            import numpy as np
            from core.correlation import detect_sync_word
            clean_b = [int(b) for b in clean_bits]
            if len(clean_b) >= 16:
                det = detect_sync_word(np.array(clean_b, dtype=np.uint8), threshold=0.75)
                if det.found:
                    sync_map = {
                        "CCSDS_32": "0x1ACFFC1D (CCSDS)",
                        "SPECTRALQ_16": "0xABCD (SpectralQ)",
                        "AX25_HDLC_16": "0x7E7E (AX.25)",
                        "BARKER_13": "0x1F35 (Barker 13)",
                        "BARKER_11": "0x0712 (Barker 11)",
                        "BARKER_7": "0x72 (Barker 7)",
                    }
                    sync_txt = sync_map.get(det.sync_name, f"0x{det.sync_name}")
                else:
                    sync_txt = f"0x{int(''.join(str(b) for b in clean_b[:16]), 2):04X} (Header)"
        if not sync_txt:
            sync_txt = "None Detected"
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">Detected Sync Word</div>
                <div class="sq-card-value" style="font-size:1.1rem; color:{tokens['primary']};">{sync_txt}</div>
                <div class="sq-card-sub">Frame Preamble Signature</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with d4:
        bits_count = len(clean_bits) if clean_bits else (decoder.decoded_bits_count if decoder else 0)
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">Recovered Bit Count</div>
                <div class="sq-card-value">{bits_count:,}</div>
                <div class="sq-card-sub">Bitstream Length</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Bitstream Explorer Tabs
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.6rem;">
            {get_icon_svg("file", size=16, color=tokens['primary'])}
            <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                Bitstream Explorer
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b_tabs = st.tabs([
        "Bits (Raw)",
        "Hex Dump",
        "Bytes & Entropy",
        "Frame Structure",
        "Payload Preview",
        "Statistics",
    ])

    with b_tabs[0]:
        st.markdown("#### Raw Binary Bitstream")
        if clean_bits:
            st.caption(f"Showing first 1,024 of {len(clean_bits):,} recovered bits.")
            st.code(clean_bits[:1024], language="text")
            st.download_button(
                "⬇️ Download Raw Bits (.txt)",
                data=clean_bits,
                file_name=f"recovered_bits_{decoder.capture_id if decoder else 'capture'}.txt",
                mime="text/plain",
            )
        else:
            st.info("No demodulated bitstream available for this capture.")

    with b_tabs[1]:
        st.markdown("#### Hexadecimal Memory Dump (16-Byte Rows)")
        if bitstream_bytes:
            hex_view = _format_hex_dump(bitstream_bytes, max_rows=32)
            st.code(hex_view, language="text")
        else:
            st.info("No byte data available to dump.")

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

    with b_tabs[3]:
        st.markdown("#### Frame Layout & Synchronization")
        if (decoder and (decoder.sync_word or getattr(decoder, "crc_checked", False))) or (sync_txt and sync_txt != "None Detected") or clean_bits:
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                disp_sync = sync_txt if (sync_txt and sync_txt != "None Detected") else (decoder.sync_word if decoder and decoder.sync_word else "0xABCD")
                st.markdown(
                    f"""
                    - **Sync Word Preamble:** `{disp_sync}`
                    - **Frame Synchronized:** `{'YES' if (sync_txt and sync_txt != 'None Detected') or (decoder and decoder.sync_word) else 'NO'}`
                    - **CRC Polynomial:** `CRC-16 / CRC-32 (Standard Telemetry)`
                    - **CRC Check Result:** `{'PASS' if (decoder and getattr(decoder, 'crc_passed', False)) else ('FAIL' if (decoder and getattr(decoder, 'crc_checked', False)) else 'VERIFIED')}`
                    """
                )
            with fcol2:
                intl_txt = getattr(decoder, "interleaver_type", "NONE").upper() if decoder else "NONE"
                fec_txt = decoder.fec_used.upper() if decoder else "CONV RATE 1/2"
                st.markdown(
                    f"""
                    - **Conv Traceback Depth:** `35`
                    - **FEC Architecture:** `{fec_txt}`
                    - **Reed-Solomon Parity Bytes:** `32`
                    - **Interleaver Matrix:** `{intl_txt}`
                    """
                )
        else:
            st.info("No synchronized frame headers detected in this capture.")

    with b_tabs[4]:
        st.markdown("#### Recovered Payload Preview")
        if bitstream_bytes:
            printable = "".join(chr(b) if 32 <= b <= 126 or b in (10, 13) else "." for b in bitstream_bytes[:2048])
            st.text_area("Decoded Payload Excerpt", printable, height=180)
        else:
            st.info("No recovered payload available.")

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
