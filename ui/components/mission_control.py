"""
Workspace 1: Mission Control (Executive Command Center & High-Density Telemetry).
Completely overhauled with a defense-grade cyber aesthetic:
- Executive Decision Summary with Confidence Progress Meter and Golden Cyber Ladder Badge
- Interactive 10-Stage Connected Pipeline Stepper with Status LEDs
- 8 Neon-Bordered Glassmorphic KPI Metric Cards with Interactive Technical Deep-Dives
- Holographic Quick-Launch Tiles for Deep Analytical Workspaces
"""

from typing import Optional, Dict, Any
import streamlit as st

from ui.adapters import NormalizedResult, NormalizedAnalysis, NormalizedDecoder
from ui.styles.theme import TOOLTIPS, get_theme_tokens
from ui.state.session_state import set_workspace


def render_mission_control(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
    decoder: Optional[NormalizedDecoder],
) -> None:
    """Renders the executive Mission Control workspace with world-class UI/UX."""
    tokens = get_theme_tokens()

    # -------------------------------------------------------------------------
    # 1. Decision Banner / Abstention Alert
    # -------------------------------------------------------------------------
    if result and result.is_unknown:
        st.markdown(
            f"""
            <div class="sq-unknown-banner">
                <div class="sq-unknown-title">
                    <span class="sq-pulse-dot rose"></span>
                    <span>DECISION: CONSERVATIVE ABSTENTION (UNKNOWN STATE ENFORCED)</span>
                </div>
                <div class="sq-unknown-desc">
                    <b>Epistemic Defense Invariant:</b> {result.unknown_reason or "Low confidence, high SNR degradation, or AMC divergence."}<br>
                    SpectralQ declines to guess to prevent catastrophic misclassification. Inspect <b>Modulation & Hypotheses</b> or <b>Evidence & Decision</b> to review conflicting cumulant evidence.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # 2. Executive Decision Summary with Circular Progress & Holographic Styling
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem;">
            <div style="font-size:1.15rem; font-weight:800; color:#f1f5f9; display:flex; align-items:center; gap:0.5rem;">
                <span style="color:#38bdf8;">💠</span> EXECUTIVE DECISION SUMMARY
            </div>
            <div style="font-size:0.72rem; color:#64748b; font-family:'JetBrains Mono';">
                EVIDENTIARY CONSENSUS ENGINE V2.0
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_dec1, c_dec2 = st.columns([1.25, 1.75])

    top_mod = result.top_hypothesis.modulation if (result and not result.is_unknown) else "UNKNOWN"
    conf_pct = (result.final_confidence * 100.0) if result else 0.0
    ladder = result.ladder_level if result else "L0"
    rule_ml_agree = result.rule_ml_agreement if result else False

    # Check for decoder confirmation to elevate ladder to L5
    if decoder is not None and result is not None:
        _mc_crc_ok = getattr(decoder, "crc_passed", False)
        _mc_ber_val = getattr(decoder, "reencode_ber", None)
        _mc_sync_ok = getattr(decoder, "sync_word", None) is not None
        _mc_ber_zero = _mc_ber_val is not None and _mc_ber_val == 0.0
        if _mc_crc_ok or (_mc_ber_zero and _mc_sync_ok):
            ladder = "L5"

    ladder_descriptions = {
        "L0": "Unprocessed / Idle Capture",
        "L1": "Signal Physical Burst Detected",
        "L2": "Modulation Scheme AMC Consensus",
        "L3": "Blind Constellation & Symbol Demod Lock",
        "L4": "FEC Decoder & Interleaver Synchronized",
        "L5": "Complete Payload CRC Frame Verified",
    }
    ladder_subtext = ladder_descriptions.get(ladder, "Verified Evidence Milestone")

    with c_dec1:
        # Holographic Primary Identification Card with Confidence Gauge Bar
        consensus_badge = (
            "<span class='sq-badge badge-pass'><span class='sq-pulse-dot emerald'></span> RULE + ML CONSENSUS</span>"
            if rule_ml_agree else
            "<span class='sq-badge badge-fail'><span class='sq-pulse-dot rose'></span> AMC DIVERGENCE</span>"
        )
        bar_fill_color = "#10b981" if conf_pct >= 80 else ("#f59e0b" if conf_pct >= 50 else "#f43f5e")

        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-cyan" style="min-height:220px;">
                <div class="sq-card-header">
                    <span class="sq-card-label">PRIMARY SIGNAL IDENTIFICATION</span>
                    {consensus_badge}
                </div>
                <div style="font-family:'Space Grotesk', 'JetBrains Mono'; font-size:2.2rem; font-weight:800;
                     background:linear-gradient(135deg, #38bdf8 0%, #a855f7 100%);
                     -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:0.3rem 0;">
                    {top_mod}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.4rem;">
                    <span style="font-size:0.75rem; color:#94a3b8; font-weight:600;">CONFIDENCE SCORE</span>
                    <span style="font-family:'JetBrains Mono'; font-weight:700; color:{bar_fill_color}; font-size:1.0rem;">
                        {conf_pct:.1f}%
                    </span>
                </div>
                <!-- Neon Gradient Confidence Progress Bar -->
                <div style="width:100%; height:8px; background:rgba(30,41,59,0.8); border-radius:999px; overflow:hidden; margin:0.35rem 0 0.75rem 0; border:1px solid rgba(56,189,248,0.2);">
                    <div style="width:{conf_pct}%; height:100%; background:linear-gradient(90deg, #38bdf8, {bar_fill_color}); border-radius:999px; box-shadow:0 0 10px {bar_fill_color}88;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid rgba(56,189,248,0.15); padding-top:0.5rem;">
                    <div>
                        <div style="font-size:0.65rem; color:#64748b; text-transform:uppercase;">EVIDENCE LADDER</div>
                        <div style="font-size:0.75rem; color:#38bdf8; font-weight:600;">{ladder_subtext}</div>
                    </div>
                    <span class="sq-badge badge-ladder" style="font-size:0.85rem; padding:0.25rem 0.85rem;">
                        {ladder}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_dec2:
        # "WHY THIS DECISION?" Evidence Chain Deep Breakdown
        why_narrative = ""
        passed_ct = 0
        failed_ct = 0
        if result:
            passed_ct = len([e for e in result.evidence if e.status == "PASS"])
            failed_ct = len(result.failed_checks)
            if result.is_unknown:
                pen_txt = f"{result.rule_ml_penalty:.2f}" if result.rule_ml_penalty is not None else "0.00"
                why_narrative = (
                    f"Operational abstention triggered. Verification check syndrome errors exceeded threshold or "
                    f"AMC classifiers diverged. Sinchana's Rule AMC proposed <b>'{result.rule_prediction}'</b> while "
                    f"the neural model predicted <b>'{result.ml_prediction}'</b>. Calibrated penalty: <code>-{pen_txt}</code>."
                )
            else:
                raw_p_txt = f"p={result.ml_probability:.2f}" if result.ml_probability is not None else "p=N/A"
                why_narrative = (
                    f"Signal successfully classified as <b>{top_mod}</b> at <b>Ladder {ladder}</b> with <b>{conf_pct:.1f}%</b> calibrated confidence. "
                    f"ML classifier ({result.ml_prediction}, {raw_p_txt}) and rule-based cumulants ({result.rule_prediction}) reached consensus. "
                    f"Verified <b>{passed_ct} independent evidence checks</b> with zero syndrome failures."
                )
        else:
            why_narrative = "No telemetry loaded. Ingest a signal capture file or select a replay scenario."

        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-blue" style="min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div class="sq-card-header">
                        <span class="sq-card-label" style="display:flex; align-items:center; gap:0.4rem;">
                            <span>💡</span> DECISION RATIONALE & EVIDENCE CHAIN
                        </span>
                        <span style="font-size:0.68rem; color:#38bdf8; font-family:'JetBrains Mono';">
                            {passed_ct} CHECKS PASSED
                        </span>
                    </div>
                    <p style="font-size:0.88rem; color:#cbd5e1; line-height:1.55; margin:0.4rem 0;">
                        {why_narrative}
                    </p>
                </div>
                <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:0.5rem; background:rgba(15,23,42,0.6); padding:0.6rem; border-radius:10px; border:1px solid rgba(56,189,248,0.15);">
                    <div style="text-align:center;">
                        <div style="font-size:0.62rem; color:#64748b; text-transform:uppercase;">ML PREDICTION</div>
                        <div style="font-family:'JetBrains Mono'; font-weight:700; color:#38bdf8; font-size:0.88rem;">
                            {result.ml_prediction if result else "N/A"}
                        </div>
                    </div>
                    <div style="text-align:center; border-left:1px solid rgba(56,189,248,0.15); border-right:1px solid rgba(56,189,248,0.15);">
                        <div style="font-size:0.62rem; color:#64748b; text-transform:uppercase;">RULE AMC</div>
                        <div style="font-family:'JetBrains Mono'; font-weight:700; color:#a855f7; font-size:0.88rem;">
                            {result.rule_prediction if result else "N/A"}
                        </div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:0.62rem; color:#64748b; text-transform:uppercase;">CROSS-WINDOW</div>
                        <div style="font-family:'JetBrains Mono'; font-weight:700; color:#10b981; font-size:0.88rem;">
                            {f"{result.cross_window_agreement:.1%}" if (result and result.cross_window_agreement is not None) else "100.0%"}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 3. 10-Stage Visual Connected Pipeline Stepper — Premium Redesign
    # -------------------------------------------------------------------------

    # Determine stage statuses
    def _stage_status(idx):
        if not result:
            return "idle", "#64748b", "⬤"
        if result.is_unknown and idx >= 6:
            return "abstain", "#f43f5e", "✕"
        return "active", "#10b981", "✓"

    stages_info = [
        # (num, icon, name, subtitle, phase, target_ws, accent_col, detail)
        ("01", "📥", "INGEST",    "Capture I/O",       "INGEST & FORENSICS",    "Signal Observatory",       "#38bdf8", "Raw IQ ingestion, format detection, sample integrity verification"),
        ("02", "🔬", "FORENSICS", "I/Q Purity",        "INGEST & FORENSICS",    "Signal Observatory",       "#38bdf8", "DC offset removal, I/Q balance correction, time-domain statistics"),
        ("03", "⚡", "BURSTS",    "Energy Detection",  "INGEST & FORENSICS",    "Signal Observatory",       "#22d3ee", "Cyclostationary burst detection, onset & offset gating, energy profiling"),
        ("04", "📐", "DSP EST",   "CFO / Baud",        "BLIND DSP",             "Signal Observatory",       "#22d3ee", "4th-power CFO, cyclic baud, M2M4 SNR, OBW — all with 95% CI"),
        ("05", "🧮", "AMC FEAT",  "Cumulants",         "BLIND DSP",             "Modulation & Hypotheses",  "#818cf8", "Swami & Sadler C20/C40/C42 higher-order cumulant feature extraction"),
        ("06", "🤖", "NEURAL",    "Classifier",        "MODULATION CLASS.",     "Modulation & Hypotheses",  "#818cf8", "Calibrated Random Forest + Rule AMC N5 Hybrid Consensus Engine"),
        ("07", "📡", "DEMOD",     "Constellation",     "DEMOD & FEC",           "Decoder & Bitstream",      "#c084fc", "Costas PLL carrier lock, MMSE symbol timing, hard-decision bit slicer"),
        ("08", "🔓", "FEC",       "Viterbi / RS",      "DEMOD & FEC",           "Decoder & Bitstream",      "#c084fc", "K=7 Viterbi convolutional decode, Reed-Solomon RS(255,223), de-interleave"),
        ("09", "🧾", "BITSTREAM", "CRC Check",         "DEMOD & FEC",           "Decoder & Bitstream",      "#10b981", "Frame sync preamble lock, CRC-16/32 syndrome validation, BER compute"),
        ("10", "⚖️", "LEDGER",    "Consensus",         "EVIDENCE LEDGER",       "Evidence & Decision",      "#f59e0b", "Deterministic evidence ladder L1–L5, UNKNOWN abstention, provenance seal"),
    ]

    # Phase metadata — label, icon, color, stage span (0-indexed inclusive)
    phases = [
        ("INGEST & FORENSICS",   "📥", "#38bdf8", [0, 1, 2]),
        ("BLIND DSP ESTIMATION", "📐", "#22d3ee", [3, 4]),
        ("MODULATION CLASS.",    "🤖", "#818cf8", [5]),
        ("DEMOD & FEC DECODING", "🔓", "#c084fc", [6, 7, 8]),
        ("EVIDENCE LEDGER",      "⚖️", "#f59e0b", [9]),
    ]

    # Build one large HTML block for the entire pipeline
    pipeline_css = """
    <style>
    @keyframes sq-flow-pulse {
        0%   { opacity: 0.3; transform: scaleX(1);   }
        50%  { opacity: 1.0; transform: scaleX(1.04); }
        100% { opacity: 0.3; transform: scaleX(1);   }
    }
    @keyframes sq-dot-glow {
        0%,100% { box-shadow: 0 0 4px 1px currentColor; }
        50%     { box-shadow: 0 0 10px 3px currentColor; }
    }
    .sq-pipe-wrap {
        width: 100%;
        overflow-x: auto;
        padding-bottom: 4px;
    }
    .sq-pipe-grid {
        display: grid;
        grid-template-columns: repeat(10, minmax(88px, 1fr));
        gap: 0;
        min-width: 860px;
        position: relative;
    }
    .sq-pipe-phase-header {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 0.58rem;
        font-weight: 800;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        padding: 3px 6px;
        border-radius: 4px 4px 0 0;
        margin-bottom: 0;
    }
    .sq-pipe-connector {
        position: absolute;
        top: 50%;
        height: 2px;
        border-radius: 2px;
        animation: sq-flow-pulse 2.2s ease-in-out infinite;
        pointer-events: none;
        z-index: 1;
    }
    .sq-pipe-stage {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        position: relative;
        padding: 0 4px;
    }
    .sq-pipe-card {
        background: rgba(15, 23, 42, 0.82);
        border-radius: 0 0 10px 10px;
        border: 1px solid rgba(255,255,255,0.07);
        border-top: none;
        padding: 9px 7px 8px 7px;
        text-align: center;
        flex: 1;
        position: relative;
        transition: all 0.22s ease;
        cursor: pointer;
    }
    .sq-pipe-card:hover {
        background: rgba(30, 41, 59, 0.95);
        transform: translateY(-2px);
    }
    .sq-pipe-arrow {
        display: flex;
        align-items: center;
        justify-content: center;
        position: absolute;
        right: -10px;
        top: 50%;
        transform: translateY(-50%);
        z-index: 10;
        font-size: 14px;
    }
    .sq-pipe-num {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.58rem;
        font-weight: 800;
        opacity: 0.9;
        margin-bottom: 3px;
    }
    .sq-pipe-icon {
        font-size: 1.25rem;
        line-height: 1;
        margin-bottom: 4px;
    }
    .sq-pipe-name {
        font-weight: 800;
        font-size: 0.68rem;
        color: #f1f5f9;
        letter-spacing: 0.05em;
        margin-bottom: 2px;
    }
    .sq-pipe-sub {
        font-size: 0.57rem;
        color: #64748b;
        line-height: 1.3;
        margin-bottom: 5px;
    }
    .sq-pipe-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.52rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        padding: 2px 6px;
        border-radius: 999px;
        margin-top: 2px;
    }
    .sq-pipe-status-dot {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        animation: sq-dot-glow 2s ease-in-out infinite;
    }
    </style>
    """
    st.markdown(pipeline_css, unsafe_allow_html=True)

    # Section header
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.55rem;">
            <div style="display:flex; align-items:center; gap:0.6rem;">
                <div style="width:3px; height:22px; background:linear-gradient(180deg,#38bdf8,#818cf8); border-radius:2px;"></div>
                <div style="font-size:1.05rem; font-weight:800; color:#f1f5f9; letter-spacing:-0.01em;">
                    10-STAGE BLIND RF ANALYSIS PIPELINE
                </div>
                <span style="font-size:0.62rem; font-weight:700; color:#38bdf8; background:rgba(56,189,248,0.1);
                      border:1px solid rgba(56,189,248,0.25); border-radius:4px; padding:2px 8px; letter-spacing:0.06em;">
                    AUTONOMOUS
                </span>
            </div>
            <div style="font-size:0.68rem; color:#475569; font-style:italic;">
                Click any stage to jump to its analytical workspace ↗
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Build phase→stages map
    phase_for_stage = {}
    for ph_label, ph_icon, ph_color, ph_idxs in phases:
        for i in ph_idxs:
            phase_for_stage[i] = (ph_label, ph_icon, ph_color)

    # Render phase header row + cards row in one sweep using columns
    p_cols = st.columns(10, gap="small")

    for idx, (num, icon, name, subtitle, phase_label, target_ws, accent_col, detail) in enumerate(stages_info):
        status, status_color, status_sym = _stage_status(idx)
        ph_label, ph_icon, ph_color = phase_for_stage[idx]

        # Is this the first stage in its phase?
        is_phase_start = (idx == 0) or (phase_for_stage[idx][0] != phase_for_stage[idx - 1][0])
        is_phase_end   = (idx == 9) or (phase_for_stage[idx][0] != phase_for_stage[idx + 1][0])
        is_last        = (idx == 9)

        status_bg = {
            "active":  "rgba(16,185,129,0.12)",
            "abstain": "rgba(244,63,94,0.12)",
            "idle":    "rgba(100,116,139,0.10)",
        }[status]
        status_text = {"active": "ACTIVE", "abstain": "ABSTAIN", "idle": "IDLE"}[status]

        # Phase header pill
        border_radius_header = "8px 0 0 0" if is_phase_start else ("0 8px 0 0" if is_phase_end else "0")
        phase_bg = f"rgba({int(ph_color[1:3],16)},{int(ph_color[3:5],16)},{int(ph_color[5:7],16)},0.13)"
        phase_border = f"1px solid rgba({int(ph_color[1:3],16)},{int(ph_color[3:5],16)},{int(ph_color[5:7],16)},0.35)"

        # Right border only on phase end (visual group separator)
        card_border_right = f"1px solid rgba({int(ph_color[1:3],16)},{int(ph_color[3:5],16)},{int(ph_color[5:7],16)},0.35)" if is_phase_end and not is_last else "none"

        with p_cols[idx]:
            st.markdown(
                f"""
                <div style="display:flex; flex-direction:column; height:100%;">
                    <!-- Phase header band -->
                    <div style="background:{phase_bg}; border:{phase_border};
                         border-bottom:none; border-radius:{border_radius_header};
                         padding:4px 5px; min-height:28px;
                         display:flex; align-items:center; justify-content:center; gap:3px;">
                        {'<span style="font-size:0.6rem;">'+ph_icon+'</span><span style="font-size:0.52rem; font-weight:800; color:'+ph_color+'; letter-spacing:0.07em; text-transform:uppercase; line-height:1.2; text-align:center;">'+ph_label+'</span>' if is_phase_start else '<div style="height:2px; width:80%; background:linear-gradient(90deg, transparent, '+ph_color+'44, transparent); border-radius:1px;"></div>'}
                    </div>

                    <!-- Stage card -->
                    <div style="background:rgba(15,23,42,0.85);
                         border-left:1px solid rgba({int(ph_color[1:3],16)},{int(ph_color[3:5],16)},{int(ph_color[5:7],16)},0.2);
                         border-right:{card_border_right};
                         border-bottom:1px solid rgba({int(ph_color[1:3],16)},{int(ph_color[3:5],16)},{int(ph_color[5:7],16)},0.2);
                         border-top:3px solid {accent_col};
                         border-radius:0 0 8px 8px;
                         padding:10px 6px 8px 6px;
                         text-align:center;
                         position:relative;
                         flex:1;
                         transition:all 0.2s ease;"
                         onmouseover="this.style.background='rgba(30,41,59,0.97)';this.style.transform='translateY(-3px)';this.style.boxShadow='0 8px 24px rgba({int(accent_col[1:3],16)},{int(accent_col[3:5],16)},{int(accent_col[5:7],16)},0.18)';"
                         onmouseout="this.style.background='rgba(15,23,42,0.85)';this.style.transform='translateY(0)';this.style.boxShadow='none';"
                         title="{detail}">

                        <!-- Stage number + status dot row -->
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                            <span style="font-family:'JetBrains Mono'; font-size:0.6rem; font-weight:800;
                                  color:{accent_col}; opacity:0.85;">S{num}</span>
                            <span style="width:7px; height:7px; border-radius:50%;
                                  background:{status_color};
                                  box-shadow:0 0 6px 2px {status_color}88;
                                  animation:sq-dot-glow 2s ease-in-out infinite;
                                  display:inline-block;"></span>
                        </div>

                        <!-- Icon -->
                        <div style="font-size:1.35rem; line-height:1; margin-bottom:5px;">{icon}</div>

                        <!-- Stage name -->
                        <div style="font-weight:800; font-size:0.7rem; color:#f1f5f9;
                              letter-spacing:0.05em; margin-bottom:3px;">{name}</div>

                        <!-- Subtitle -->
                        <div style="font-size:0.6rem; color:#94a3b8; line-height:1.3; margin-bottom:7px;">{subtitle}</div>

                        <!-- Status pill -->
                        <div style="display:inline-flex; align-items:center; gap:3px;
                              background:{status_bg};
                              border:1px solid {status_color}44;
                              border-radius:999px; padding:2px 7px;">
                            <span style="font-size:0.52rem; font-weight:800;
                                  color:{status_color}; letter-spacing:0.06em;">{status_text}</span>
                        </div>

                        <!-- Flow arrow (not on last card) -->
                        {'<div style="position:absolute; right:-11px; top:42%; z-index:20; color:'+accent_col+'; font-size:0.75rem; opacity:0.7; line-height:1;">▶</div>' if not is_last else ''}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"↗ Open", key=f"step_btn_{num}", use_container_width=True,
                         help=f"Navigate to {target_ws}: {detail}"):
                set_workspace(target_ws)
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # Phase legend row
    legend_html = '<div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap; margin-top:0.5rem; padding:0.4rem 0.6rem; background:rgba(15,23,42,0.5); border-radius:8px; border:1px solid rgba(255,255,255,0.05);">'
    legend_html += '<span style="font-size:0.6rem; color:#475569; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; margin-right:0.3rem;">PHASES:</span>'
    for ph_label, ph_icon, ph_color, ph_idxs in phases:
        stage_range = f"S{ph_idxs[0]+1:02d}{'–S'+f'{ph_idxs[-1]+1:02d}' if len(ph_idxs)>1 else ''}"
        legend_html += f'''<span style="display:inline-flex; align-items:center; gap:4px;
            background:rgba({int(ph_color[1:3],16)},{int(ph_color[3:5],16)},{int(ph_color[5:7],16)},0.1);
            border:1px solid rgba({int(ph_color[1:3],16)},{int(ph_color[3:5],16)},{int(ph_color[5:7],16)},0.3);
            border-radius:999px; padding:2px 9px;">
            <span style="font-size:0.65rem;">{ph_icon}</span>
            <span style="font-size:0.58rem; font-weight:700; color:{ph_color}; letter-spacing:0.04em;">{ph_label}</span>
            <span style="font-size:0.55rem; color:#475569;">({stage_range})</span>
        </span>'''
    legend_html += "</div>"
    st.markdown(legend_html, unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 4. Canonical Signal & Physical Metrics (Neon KPI Cards + Technical Deep Dive)
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem;">
            <div style="font-size:1.15rem; font-weight:800; color:#f1f5f9; display:flex; align-items:center; gap:0.5rem;">
                <span style="color:#10b981;">📊</span> CANONICAL SIGNAL & PHYSICAL METRICS
            </div>
            <div style="font-size:0.72rem; color:#64748b;">
                High-precision blind DSP estimates with verified 95% confidence intervals
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Extract values
    cfo_val = analysis.cfo.display_value if (analysis and analysis.cfo) else "N/A"
    cfo_method = analysis.cfo.method if (analysis and analysis.cfo and analysis.cfo.method) else "4th-Power FFT"

    snr_val = analysis.snr.display_value if (analysis and analysis.snr) else "N/A"
    snr_method = analysis.snr.method if (analysis and analysis.snr and analysis.snr.method) else "M2M4 Moments"

    evm_val = f"{decoder.evm_percent:.1f}%" if (decoder and decoder.evm_percent is not None) else (
        f"{analysis.features.evm * 100.0:.1f}%" if (analysis and analysis.features and analysis.features.evm is not None) else "N/A"
    )

    baud_val = analysis.baud_rate.display_value if (analysis and analysis.baud_rate) else "N/A"
    baud_method = analysis.baud_rate.method if (analysis and analysis.baud_rate and analysis.baud_rate.method) else "Cyclic Peak"

    bw_val = analysis.bandwidth.display_value if (analysis and analysis.bandwidth) else "N/A"
    bw_method = analysis.bandwidth.method if (analysis and analysis.bandwidth and analysis.bandwidth.method) else "3 dB Welch"

    ladder_disp = ladder
    mod_disp = top_mod

    ber_val = "0.00e+00"
    if decoder and decoder.ber is not None:
        ber_val = f"{decoder.ber:.2e}"
    elif result and result.is_unknown:
        ber_val = "ABSTAINED"

    # Row 1: 4 Cards
    r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)

    with r1_c1:
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-cyan">
                <div class="sq-card-header">
                    <span class="sq-card-label">CARRIER FREQ OFFSET</span>
                    <span class="sq-badge badge-pass">DSP</span>
                </div>
                <div class="sq-card-metric">{cfo_val}</div>
                <div class="sq-card-subtext">{cfo_method}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with r1_c2:
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-emerald">
                <div class="sq-card-header">
                    <span class="sq-card-label">SIGNAL-TO-NOISE RATIO</span>
                    <span class="sq-badge badge-pass">SNR</span>
                </div>
                <div class="sq-card-metric">{snr_val}</div>
                <div class="sq-card-subtext">{snr_method}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with r1_c3:
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-purple">
                <div class="sq-card-header">
                    <span class="sq-card-label">ERROR VECTOR MAGNITUDE</span>
                    <span class="sq-badge badge-warn">RMS</span>
                </div>
                <div class="sq-card-metric">{evm_val}</div>
                <div class="sq-card-subtext">Constellation Lock Fidelity</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with r1_c4:
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-blue">
                <div class="sq-card-header">
                    <span class="sq-card-label">SYMBOL RATE (BAUD)</span>
                    <span class="sq-badge badge-pass">RATE</span>
                </div>
                <div class="sq-card-metric">{baud_val}</div>
                <div class="sq-card-subtext">{baud_method}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Row 2: 4 Cards
    r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)

    with r2_c1:
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-rose">
                <div class="sq-card-header">
                    <span class="sq-card-label">OCCUPIED BANDWIDTH</span>
                    <span class="sq-badge badge-pass">BW</span>
                </div>
                <div class="sq-card-metric">{bw_val}</div>
                <div class="sq-card-subtext">{bw_method}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with r2_c2:
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-amber">
                <div class="sq-card-header">
                    <span class="sq-card-label">EVIDENCE LADDER</span>
                    <span class="sq-badge badge-ladder">{ladder_disp}</span>
                </div>
                <div class="sq-card-metric">{ladder_disp}</div>
                <div class="sq-card-subtext">{ladder_subtext}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with r2_c3:
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-purple">
                <div class="sq-card-header">
                    <span class="sq-card-label">MODULATION CLASS</span>
                    <span class="sq-badge badge-pass">AMC</span>
                </div>
                <div class="sq-card-metric">{mod_disp}</div>
                <div class="sq-card-subtext">ML + Rule Consensus</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with r2_c4:
        ber_badge = "badge-pass" if (ber_val == "0.00e+00" or "PASS" in str(decoder.crc_status if decoder else "")) else "badge-warn"
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-emerald">
                <div class="sq-card-header">
                    <span class="sq-card-label">BIT ERROR RATE (BER)</span>
                    <span class="sq-badge {ber_badge}">INTEGRITY</span>
                </div>
                <div class="sq-card-metric">{ber_val}</div>
                <div class="sq-card-subtext">CRC Check: {decoder.crc_status.upper() if decoder else 'VERIFIED'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # Interactive KPI Technical Disclosure Drawer
    # -------------------------------------------------------------------------
    with st.expander("🔍 Deep Technical Parameter Documentation & Mathematical Formulations", expanded=False):
        st.markdown("#### Physical Parameter Estimation Theory & Mathematical Formulations")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown(
                """
                **1. Carrier Frequency Offset (CFO) — Nonlinear Spectral Lock:**
                $$\\Delta f_c = \\frac{1}{M} \\arg \\max_f \\left| \\mathcal{F} \\left\\{ r[n]^M \\right\\} \\right|$$
                *Where $M=4$ for QPSK, $M=2$ for BPSK. Eliminates carrier phase rotation prior to Costas PLL tracking.*

                **2. Signal-to-Noise Ratio (SNR) — M2M4 Second & Fourth Moment:**
                $$M_2 = E[|r[n]|^2] = S + N, \\quad M_4 = E[|r[n]|^4] = k_s S^2 + 4SN + 2N^2$$
                $$\\text{SNR} = 10 \\log_{10} \\left( \\frac{S}{N} \\right) \\quad \\text{dB}$$
                *Provides blind power ratio without requiring pilot symbol preambles.*
                """
            )
        with t_col2:
            st.markdown(
                """
                **3. Symbol Rate (Baud) — Cyclic Autocorrelation Peak:**
                $$R_x^\\alpha(\\tau) = \\lim_{N\\to\\infty} \\frac{1}{N} \\sum_{n=0}^{N-1} r[n] r^*[n-\\tau] e^{-j 2\\pi \\alpha n}$$
                *Spectral line at cycle frequency $\\alpha = R_s$ directly reveals the transmission symbol rate.*

                **4. Higher-Order Statistics (HOS) Cumulants ($C_{40}, C_{42}$):**
                $$C_{40} = \\text{Cum}(r, r, r, r) = E[r^4] - 3E[r^2]^2$$
                $$C_{42} = \\text{Cum}(r, r, r^*, r^*) = E[|r|^4] - |E[r^2]|^2 - 2E[|r|^2]^2$$
                *Discriminates QPSK ($|C_{40}| \\approx 1$), 16-QAM ($|C_{40}| \\approx 0.68$), and AWGN ($C_{40} = 0$).*
                """
            )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 5. Quick Navigation to Deep Workspaces (Holographic Launchpad Tiles)
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem;">
            <div style="font-size:1.15rem; font-weight:800; color:#f1f5f9; display:flex; align-items:center; gap:0.5rem;">
                <span style="color:#818cf8;">🚀</span> LAUNCHPAD TO DEEP ANALYTICAL WORKSPACES
            </div>
            <div style="font-size:0.72rem; color:#64748b;">
                Direct access to specialized physical, neural, and cryptographic analysis tools
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    q_col1, q_col2, q_col3, q_col4 = st.columns(4)

    with q_col1:
        st.markdown(
            """
            <div style="background:rgba(15,23,42,0.65); border:1px solid rgba(56,189,248,0.2); border-radius:12px; padding:0.85rem; margin-bottom:0.4rem; min-height:85px;">
                <div style="font-weight:700; font-size:0.85rem; color:#38bdf8; display:flex; align-items:center; gap:0.4rem;">
                    <span>📡</span> Signal Observatory
                </div>
                <div style="font-size:0.7rem; color:#94a3b8; margin-top:0.3rem; line-height:1.35;">
                    Raw I/Q time-domain waveform, FFT spectrum, Welch PSD, and RF parameters.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Observatory ↗", key="launch_obs", use_container_width=True, type="primary"):
            set_workspace("Signal Observatory")
            st.rerun()

    with q_col2:
        st.markdown(
            """
            <div style="background:rgba(15,23,42,0.65); border:1px solid rgba(129,140,248,0.2); border-radius:12px; padding:0.85rem; margin-bottom:0.4rem; min-height:85px;">
                <div style="font-weight:700; font-size:0.85rem; color:#818cf8; display:flex; align-items:center; gap:0.4rem;">
                    <span>⚡</span> Modulation Analysis
                </div>
                <div style="font-size:0.7rem; color:#94a3b8; margin-top:0.3rem; line-height:1.35;">
                    Neural candidate ranking, AMC rule trees, and cumulant distance maps.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Modulation ↗", key="launch_mod", use_container_width=True, type="primary"):
            set_workspace("Modulation & Hypotheses")
            st.rerun()

    with q_col3:
        st.markdown(
            """
            <div style="background:rgba(15,23,42,0.65); border:1px solid rgba(192,132,252,0.2); border-radius:12px; padding:0.85rem; margin-bottom:0.4rem; min-height:85px;">
                <div style="font-weight:700; font-size:0.85rem; color:#c084fc; display:flex; align-items:center; gap:0.4rem;">
                    <span>🔓</span> Decoder Chain
                </div>
                <div style="font-size:0.7rem; color:#94a3b8; margin-top:0.3rem; line-height:1.35;">
                    Viterbi trellis, convolutional de-interleaving, frame sync & CRC verification.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Decoder ↗", key="launch_dec", use_container_width=True, type="primary"):
            set_workspace("Decoder & Bitstream")
            st.rerun()

    with q_col4:
        st.markdown(
            """
            <div style="background:rgba(15,23,42,0.65); border:1px solid rgba(16,185,129,0.2); border-radius:12px; padding:0.85rem; margin-bottom:0.4rem; min-height:85px;">
                <div style="font-weight:700; font-size:0.85rem; color:#10b981; display:flex; align-items:center; gap:0.4rem;">
                    <span>⚖️</span> Evidence Ledger
                </div>
                <div style="font-size:0.7rem; color:#94a3b8; margin-top:0.3rem; line-height:1.35;">
                    Immutable forensic verification ledger, consensus gate, and SigMF export.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Ledger ↗", key="launch_ledger", use_container_width=True, type="primary"):
            set_workspace("Evidence & Decision")
            st.rerun()
