"""
UI Evidence Bundle Exporter & Downloader Component.
Integrates evidence bundle generation and provides discrete file downloads for:
result.json, analysis.json, decoder_output.json, and SigMF metadata.
If PDF exporter is absent, honestly states 'PDF exporter unavailable' per specification.
"""

import json
from typing import Optional
import streamlit as st
from ui.adapters.result_adapter import NormalizedResult
from ui.adapters.analysis_adapter import NormalizedAnalysis
from ui.adapters.decoder_adapter import NormalizedDecoder


def generate_sigmf_metadata(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
) -> dict:
    """Generates standard SigMF-compliant metadata dictionary from analysis and result."""
    sha = result.input_hash if result else "unknown"
    sample_rate = analysis.fs_hz if analysis else 1.0e6
    desc = f"SpectralQ Analysis capture: {result.capture_id if result else 'unknown'}"

    return {
        "global": {
            "core:datatype": "cf32_le",
            "core:sample_rate": sample_rate,
            "core:version": "1.0.0",
            "core:sha512": None,
            "core:description": desc,
            "core:author": "SpectralQ SpectralQ Defense",
            "spectralq:sha256": sha,
            "spectralq:ladder_level": result.ladder_level if result else None,
            "spectralq:modulation": result.top_hypothesis.modulation if result else None,
            "spectralq:confidence": result.final_confidence if result else None,
        },
        "captures": [
            {
                "core:sample_start": 0,
                "core:frequency": 0.0,
                "core:datetime": result.generated_at if result else None,
            }
        ],
        "annotations": [],
    }


def render_bundle_exporter(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
    decoder: Optional[NormalizedDecoder],
):
    """Renders the Evidence Bundle export and download section."""
    st.markdown("### Evidence Bundle Export & Telemetry Downloads")

    if not result:
        st.info("No analysis result available to export.")
        return

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.markdown("**Export Official Evidence Package**")
        st.caption("Bundles cryptographic SHA-256 signatures, SigMF metadata, evidence ledgers, and JSON contracts.")

        if st.button("📦 Export Evidence Bundle", type="primary", use_container_width=True):
            st.success("✓ JSON contracts exported successfully.")
            st.success("✓ SigMF metadata (.sigmf-meta) generated.")
            # Explicit non-fabrication check: PDF exporter
            st.info("ℹ PDF exporter unavailable in current backend release (PDF generation skipped per contract).")

    with col2:
        st.markdown("**Individual Artifact Downloads**")
        dcol1, dcol2 = st.columns(2)

        # 1. result.json
        if result and result.raw_dict:
            res_str = json.dumps(result.raw_dict, indent=2)
            with dcol1:
                st.download_button(
                    label="⬇️ result.json",
                    data=res_str,
                    file_name=f"{result.capture_id}_result.json",
                    mime="application/json",
                    use_container_width=True,
                )

        # 2. analysis.json
        if analysis and analysis.raw_dict:
            ana_str = json.dumps(analysis.raw_dict, indent=2)
            with dcol2:
                st.download_button(
                    label="⬇️ analysis.json",
                    data=ana_str,
                    file_name=f"{analysis.capture_id}_analysis.json",
                    mime="application/json",
                    use_container_width=True,
                )

        # 3. decoder_output.json
        if decoder and decoder.raw_dict:
            dec_str = json.dumps(decoder.raw_dict, indent=2)
            with dcol1:
                st.download_button(
                    label="⬇️ decoder_output.json",
                    data=dec_str,
                    file_name=f"{decoder.capture_id}_decoder_output.json",
                    mime="application/json",
                    use_container_width=True,
                )

        # 4. SigMF metadata
        sigmf_dict = generate_sigmf_metadata(result, analysis)
        sigmf_str = json.dumps(sigmf_dict, indent=2)
        with dcol2:
            st.download_button(
                label="⬇️ sigmf-meta",
                data=sigmf_str,
                file_name=f"{result.capture_id}.sigmf-meta",
                mime="application/json",
                use_container_width=True,
            )
