"""
UI Bitstream Intelligence View Component.
Displays physical frame boundaries: preamble / header, payload, and CRC trailer.
Only displays boundaries if provided by backend; NEVER infers them in the GUI.
"""

from typing import Optional
import streamlit as st
from ui.adapters.decoder_adapter import NormalizedDecoder


def render_bitstream_panel(decoder: Optional[NormalizedDecoder]):
    """Renders bitstream structure and frame alignment if available."""
    st.markdown("### Bitstream Intelligence & Physical Frame Alignment")

    if not decoder or decoder.decoded_bits_count == 0:
        st.info("No decoded bitstream available for frame analysis.")
        return

    st.write(f"**Total Decoded Length:** `{decoder.decoded_bits_count} bits`")
    st.write(f"**CRC Integrity Check:** `{decoder.crc_status}`")

    # Visual frame schematic
    st.markdown("#### Physical Frame Organization")
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        st.markdown(
            """
            <div style="background-color: #21262d; border: 1px dashed #58a6ff; border-radius: 4px; padding: 0.8rem; text-align: center;">
                <div style="font-size: 0.75rem; color: #8b949e; font-weight: 700;">PREAMBLE / SYNC</div>
                <div style="font-family: monospace; font-size: 0.85rem; color: #58a6ff; margin-top: 0.2rem;">DETECTED</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 4px; padding: 0.8rem; text-align: center;">
                <div style="font-size: 0.75rem; color: #8b949e; font-weight: 700;">PAYLOAD DATA STREAM</div>
                <div style="font-family: monospace; font-size: 0.85rem; color: #f0f6fc; margin-top: 0.2rem;">{decoder.decoded_bits_count} bits</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        crc_color = "#3fb950" if decoder.crc_status == "PASS" else ("#f85149" if decoder.crc_status == "FAIL" else "#8b949e")
        st.markdown(
            f"""
            <div style="background-color: #21262d; border: 1px dashed {crc_color}; border-radius: 4px; padding: 0.8rem; text-align: center;">
                <div style="font-size: 0.75rem; color: #8b949e; font-weight: 700;">CRC CHECKSUM</div>
                <div style="font-family: monospace; font-size: 0.85rem; color: {crc_color}; margin-top: 0.2rem;">{decoder.crc_status}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if decoder.decoded_bits_preview:
        st.markdown("**Decoded Bitstream Window (First 64 Bits):**")
        st.code(decoder.decoded_bits_preview, language="text")
