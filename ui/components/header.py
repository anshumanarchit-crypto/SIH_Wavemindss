"""
SpectralQ Command Header & Telemetry Ribbon.
Operational intelligence header displaying system identity, active workspace,
epistemic status chips, and canonical capture provenance.
"""

from typing import Optional
import streamlit as st
from ui.adapters.result_adapter import NormalizedResult
from ui.adapters.analysis_adapter import NormalizedAnalysis
from ui.components.icons import get_icon_svg, get_workspace_icon_svg
from ui.styles.theme import get_theme_tokens


def render_header(
    result: Optional[NormalizedResult] = None,
    analysis: Optional[NormalizedAnalysis] = None,
    source_filename: Optional[str] = None,
    is_replay: bool = False,
):
    """Renders the defense-grade operational header and telemetry identity ribbon."""
    tokens = get_theme_tokens()
    current_ws = st.session_state.get("active_workspace", "Mission Control")
    is_demo = st.session_state.get("guided_demo_active", False)

    # Workspace descriptions
    ws_descriptions = {
        "Mission Control": "Executive Intelligence Cockpit · Automated Multi-Stage Decision",
        "Signal Observatory": "Physical-Layer RF Observatory · Raw In-Phase / Quadrature Analytics",
        "Modulation & Hypotheses": "AMC Classification Workbench · ML Consensus & Cumulant Distance",
        "Decoder & Bitstream": "Multi-Stage Decoding Workbench · Frame Synchronization & Syndrome Integrity",
        "Evidence & Decision": "Epistemic Ledger & Audit Trail · Multi-Window Consensus Hierarchy",
        "Provenance & Export": "Forensic Chain of Custody · Standardized SigMF Metadata Export",
        "Signal Lab / Simulation": "Interactive RF Testbed · Channel Impairments & Ground-Truth Validation",
        "Synthetic Generator": "Benchmark Signal Synthesis · Scenario Permutation Engine",
        "Wideband Scanner": "Dynamic Spectrum Operations · Wideband Activity Mapping",
        "Run Trace": "Execution Pipeline Observability · Latency & Telemetry Trace",
    }
    ws_desc = ws_descriptions.get(current_ws, "Operational Intelligence Workspace")

    # Capture metadata derivation
    capture_id = result.capture_id if result else (analysis.capture_id if analysis else "NO CAPTURE LOADED")
    source_mode = result.source_mode if result else (analysis.source_mode if analysis else "IDLE")

    if is_replay or (result and result.is_replay):
        mode_badge = f'<span class="sq-badge badge-replay">{get_icon_svg("refresh", size=12)} REPLAY MODE</span>'
        mode_label = "REPLAY"
    elif source_mode == "REAL":
        mode_badge = f'<span class="sq-badge badge-ladder">{get_icon_svg("target", size=12)} LIVE SDR</span>'
        mode_label = "LIVE SDR"
    elif source_mode == "SYNTHETIC":
        mode_badge = f'<span class="sq-badge badge-pass">{get_icon_svg("zap", size=12)} SYNTHETIC</span>'
        mode_label = "SYNTHETIC"
    else:
        mode_badge = f'<span class="sq-badge badge-unavail">{source_mode}</span>'
        mode_label = source_mode

    ladder_str = result.ladder_level if result else "N/A"
    ladder_badge = (
        f'<span class="sq-badge badge-ladder">{get_icon_svg("layers", size=12)} LADDER {ladder_str}</span>'
        if result
        else '<span class="sq-badge badge-unavail">LADDER N/A</span>'
    )

    unknown_badge = (
        f'<span class="sq-badge badge-unknown">{get_icon_svg("shield_alert", size=12)} ABSTAINED</span>'
        if (result and result.is_unknown)
        else ""
    )

    demo_badge = (
        f'<span class="sq-badge" style="background:rgba(154,124,255,0.18);color:#9A7CFF;border:1px solid rgba(154,124,255,0.4);">'
        f'{get_icon_svg("target", size=12)} JUDGE DEMO MODE</span>'
        if is_demo
        else ""
    )

    timestamp = result.generated_at if result else (analysis.timestamp if analysis else "N/A")
    hash_abbr = (result.input_hash[:16] + "...") if (result and result.input_hash) else "N/A"
    display_filename = source_filename or capture_id

    # 1. Top Command Header
    ws_icon_svg = get_workspace_icon_svg(current_ws, size=24, color=tokens["primary"])

    st.markdown(
        f"""
        <div class="sq-header-wrap">
            <div style="display:flex; align-items:center; gap:0.9rem;">
                <div style="background:{tokens['card_bg']}; border:1px solid {tokens['card_border_strong']};
                    border-radius:10px; width:44px; height:44px; display:flex; align-items:center;
                    justify-content:center; box-shadow:{tokens['glow_primary']};">
                    {ws_icon_svg}
                </div>
                <div>
                    <div style="display:flex; align-items:center; gap:0.6rem;">
                        <span style="font-size:0.65rem; font-weight:800; color:{tokens['primary']};
                            letter-spacing:0.12em; text-transform:uppercase;">SPECTRALQ // NTRO SIH26147</span>
                    </div>
                    <div style="font-size:1.35rem; font-weight:800; color:{tokens['text']};
                        letter-spacing:-0.02em; margin-top:-2px;">
                        {current_ws}
                    </div>
                    <div style="font-size:0.75rem; color:{tokens['text_muted']}; margin-top:1px;">
                        {ws_desc}
                    </div>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap; justify-content:flex-end;">
                {demo_badge}
                {mode_badge}
                {ladder_badge}
                {unknown_badge}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Telemetry Ribbon (Capture Identity Ribbon)
    st.markdown(
        f"""
        <div class="sq-meta-ribbon">
            <div class="sq-ribbon-cell" style="flex:1.6;">
                <span class="sq-ribbon-label">Target Capture</span>
                <span class="sq-ribbon-val" style="color:{tokens['primary']};">{display_filename}</span>
            </div>
            <div class="sq-ribbon-cell" style="flex:0.8;">
                <span class="sq-ribbon-label">Ingest Mode</span>
                <span class="sq-ribbon-val">{mode_label}</span>
            </div>
            <div class="sq-ribbon-cell" style="flex:0.8;">
                <span class="sq-ribbon-label">Evidence Ladder</span>
                <span class="sq-ribbon-val" style="color:{tokens['violet']};">{ladder_str}</span>
            </div>
            <div class="sq-ribbon-cell" style="flex:1.4;">
                <span class="sq-ribbon-label">Input SHA-256</span>
                <span class="sq-ribbon-val" style="font-size:0.75rem;">{hash_abbr}</span>
            </div>
            <div class="sq-ribbon-cell" style="flex:1.2;">
                <span class="sq-ribbon-label">Generated Timestamp</span>
                <span class="sq-ribbon-val" style="font-size:0.75rem;">{timestamp}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
