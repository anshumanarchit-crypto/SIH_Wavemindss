"""
UI Header & Aerodynamic Cyber HUD Component.
Displays SpectralQ application title, current capture telemetry, execution mode,
evidence ladder level, input SHA-256 digest, and generation timestamp.
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
    """Renders the top application header and the aerodynamic cyber HUD bar."""
    st.markdown(
        """
        <div class="sq-header">
            <div>
                <h1 class="sq-title">
                    <span>📡</span> SPECTRALQ
                    <span style="font-size:0.75rem; background:rgba(56,189,248,0.15); color:#38bdf8;
                          border:1px solid rgba(56,189,248,0.4); padding:2px 8px; border-radius:999px;
                          letter-spacing:0.06em; font-weight:700; text-transform:uppercase; vertical-align:middle;">
                        DEFENSE V2.0
                    </span>
                </h1>
                <div class="sq-subtitle">
                    Evidence-First Blind RF Signal Intelligence &amp; Multi-Stage Demodulation System • NTRO PS-SIH26147
                </div>
            </div>
            <div style="text-align:right; display:flex; flex-direction:column; align-items:flex-end; gap:3px;">
                <div style="display:flex; align-items:center; gap:6px;">
                    <span class="sq-pulse-dot cyan"></span>
                    <span style="font-size:0.72rem; font-weight:700; color:#38bdf8; letter-spacing:0.08em; text-transform:uppercase;">
                        OPERATIONAL READINESS
                    </span>
                </div>
                <div style="font-size:0.65rem; color:#64748b; font-family:'JetBrains Mono';">
                    STRICT EPISTEMIC INTEGRITY • ZERO FABRICATED DATA
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Determine status & mode values
    capture_id = result.capture_id if result else (analysis.capture_id if analysis else "NO CAPTURE LOADED")
    source_mode = result.source_mode if result else (analysis.source_mode if analysis else "IDLE")

    if is_replay or (result and result.is_replay):
        mode_badge = '<span class="sq-badge badge-replay">● REPLAY TELEMETRY</span>'
    elif source_mode == "REAL":
        mode_badge = '<span class="sq-badge badge-ladder">● REAL RF PASS</span>'
    elif source_mode == "SYNTHETIC":
        mode_badge = '<span class="sq-badge badge-pass">● SYNTHETIC CAPTURE</span>'
    else:
        mode_badge = f'<span class="sq-badge badge-unavail">{source_mode}</span>'

    ladder_str = result.ladder_level if result else "L0"
    ladder_badge = f'<span class="sq-badge badge-ladder">LADDER {ladder_str}</span>' if result else '<span class="sq-badge badge-unavail">UNRATED</span>'

    unknown_badge = '<span class="sq-badge badge-unknown">⚠️ UNKNOWN STATE</span>' if (result and result.is_unknown) else ""

    timestamp = result.generated_at if result else (analysis.notes if (analysis and analysis.notes) else "N/A")
    raw_hash = result.input_hash if result else "N/A"
    hash_abbr = (raw_hash[:16] + "...") if len(raw_hash) > 16 else raw_hash

    # Aerodynamic Cyber HUD Box
    st.markdown(
        f"""
        <div class="sq-meta-hud">
            <div class="sq-meta-hud-item">
                <span class="sq-meta-hud-label">
                    <span>🎯</span> TARGET CAPTURE
                </span>
                <span class="sq-meta-hud-value" style="color:#38bdf8;">
                    {source_filename or capture_id}
                </span>
            </div>
            <div class="sq-meta-hud-item">
                <span class="sq-meta-hud-label">
                    <span>⚙️</span> EXECUTION PIPELINE
                </span>
                <span class="sq-meta-hud-value">
                    {mode_badge}
                </span>
            </div>
            <div class="sq-meta-hud-item">
                <span class="sq-meta-hud-label">
                    <span>🪜</span> EVIDENCE LEVEL
                </span>
                <span class="sq-meta-hud-value">
                    {ladder_badge}
                </span>
            </div>
            <div class="sq-meta-hud-item">
                <span class="sq-meta-hud-label">
                    <span>🔐</span> SHA-256 HASH
                </span>
                <span class="sq-meta-hud-value" style="font-size:0.78rem;" title="{raw_hash}">
                    <code>{hash_abbr}</code>
                </span>
            </div>
            <div class="sq-meta-hud-item">
                <span class="sq-meta-hud-label">
                    <span>⏱️</span> ACQUISITION UTC
                </span>
                <span class="sq-meta-hud-value" style="font-size:0.78rem;">
                    {timestamp}
                </span>
            </div>
            {f'<div class="sq-meta-hud-item"><span class="sq-meta-hud-label"><span>🛡️</span> SYSTEM STATE</span><span class="sq-meta-hud-value">{unknown_badge}</span></div>' if unknown_badge else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
