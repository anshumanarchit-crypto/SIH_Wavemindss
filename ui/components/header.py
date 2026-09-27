"""
UI Header Component.
Displays SpectralQ application title, current capture info, source mode, ladder level, and timestamp.
"""

from typing import Optional
import streamlit as st
from ui.adapters.result_adapter import NormalizedResult
from ui.adapters.analysis_adapter import NormalizedAnalysis


def render_header(
    result: Optional[NormalizedResult] = None,
    analysis: Optional[NormalizedAnalysis] = None,
    source_filename: Optional[str] = None,
    is_replay: bool = False,
):
    """Renders the top application header and metadata bar."""
    st.markdown(
        """
        <div class="sq-header">
            <h1 class="sq-title">SpectralQ</h1>
            <div class="sq-subtitle">Evidence-First Blind Signal Intelligence &amp; Analysis System (NTRO SIH26147)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Determine status & mode values
    capture_id = result.capture_id if result else (analysis.capture_id if analysis else "NO CAPTURE LOADED")
    source_mode = result.source_mode if result else (analysis.source_mode if analysis else "IDLE")
    if is_replay or (result and result.is_replay):
        mode_badge = '<span class="sq-badge badge-replay">REPLAY MODE</span>'
    elif source_mode == "REAL":
        mode_badge = '<span class="sq-badge badge-ladder">REAL CAPTURE</span>'
    elif source_mode == "SYNTHETIC":
        mode_badge = '<span class="sq-badge badge-pass">SYNTHETIC</span>'
    else:
        mode_badge = f'<span class="sq-badge badge-notrun">{source_mode}</span>'

    ladder_str = result.ladder_level if result else "N/A"
    ladder_badge = f'<span class="sq-badge badge-ladder">LADDER {ladder_str}</span>' if result else ""

    unknown_badge = '<span class="sq-badge badge-unknown">UNKNOWN STATE</span>' if (result and result.is_unknown) else ""

    timestamp = result.generated_at if result else "N/A"
    hash_abbr = (result.input_hash[:12] + "...") if result else "N/A"

    st.markdown(
        f"""
        <div class="sq-meta-bar">
            <div class="sq-meta-item">
                <span class="sq-meta-label">Capture / File</span>
                <span class="sq-meta-value">{source_filename or capture_id}</span>
            </div>
            <div class="sq-meta-item">
                <span class="sq-meta-label">Execution Mode</span>
                <span class="sq-meta-value">{mode_badge}</span>
            </div>
            <div class="sq-meta-item">
                <span class="sq-meta-label">Ladder Level</span>
                <span class="sq-meta-value">{ladder_badge or 'N/A'}</span>
            </div>
            <div class="sq-meta-item">
                <span class="sq-meta-label">Input SHA-256</span>
                <span class="sq-meta-value">{hash_abbr}</span>
            </div>
            <div class="sq-meta-item">
                <span class="sq-meta-label">Timestamp</span>
                <span class="sq-meta-value">{timestamp}</span>
            </div>
            {f'<div class="sq-meta-item"><span class="sq-meta-label">Status</span><span class="sq-meta-value">{unknown_badge}</span></div>' if unknown_badge else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
