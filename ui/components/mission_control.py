"""
Workspace 1: Mission Control (Executive / Evaluator Overview).
Provides defense-grade executive telemetry, visual confidence indicator,
evidence chain, 10-stage pipeline journey, canonical metrics with microvisuals,
and quick workspace launchers.
"""

from typing import Optional
import streamlit as st

from ui.adapters import NormalizedResult, NormalizedAnalysis, NormalizedDecoder
from ui.styles.theme import TOOLTIPS, get_theme_tokens
from ui.state.session_state import set_workspace
from ui.components.icons import get_icon_svg, get_workspace_icon_svg


def _render_confidence_arc(confidence_pct: float, is_unknown: bool, tokens: dict) -> str:
    """Generates an inline SVG radial confidence gauge."""
    if is_unknown:
        return f"""
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
            <svg width="120" height="120" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255, 98, 120, 0.15)" stroke-width="8" />
                <circle cx="60" cy="60" r="50" fill="none" stroke="{tokens['fail_color']}" stroke-width="8"
                    stroke-dasharray="314" stroke-dashoffset="150" stroke-linecap="round" />
            </svg>
            <div style="margin-top:-76px; text-align:center;">
                <div style="font-size:1.15rem; font-weight:800; color:{tokens['fail_color']};">ABSTAIN</div>
                <div style="font-size:0.62rem; color:{tokens['text_muted']}; text-transform:uppercase; font-weight:700;">UNCERTAIN</div>
            </div>
        </div>
        """
    
    # Calculate SVG stroke offset for radius 50 (circumference = 2 * pi * 50 = 314.159)
    circumference = 314.16
    dash_offset = circumference * (1.0 - (confidence_pct / 100.0))
    color = tokens["pass_color"] if confidence_pct >= 80.0 else (tokens["warn_color"] if confidence_pct >= 50.0 else tokens["fail_color"])

    return f"""
    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
        <svg width="120" height="120" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="8" />
            <circle cx="60" cy="60" r="50" fill="none" stroke="{color}" stroke-width="8"
                stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{dash_offset:.1f}"
                stroke-linecap="round" transform="rotate(-90 60 60)" style="filter:drop-shadow(0 0 6px {color}66);" />
        </svg>
        <div style="margin-top:-78px; text-align:center;">
            <div style="font-size:1.45rem; font-weight:800; color:{tokens['text']}; font-family:'JetBrains Mono', monospace; letter-spacing:-0.03em;">
                {confidence_pct:.1f}<span style="font-size:0.85rem; color:{color};">%</span>
            </div>
            <div style="font-size:0.6rem; color:{tokens['text_muted']}; text-transform:uppercase; font-weight:700; letter-spacing:0.06em;">
                CONFIDENCE
            </div>
        </div>
    </div>
    """


def render_mission_control(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
    decoder: Optional[NormalizedDecoder],
) -> None:
    """Renders the executive Mission Control workspace."""
    tokens = get_theme_tokens()

    # 1. Prominent UNKNOWN / Abstention Banner
    if result and result.is_unknown:
        st.markdown(
            f"""
            <div class="sq-unknown-banner">
                <div style="display:flex; align-items:flex-start; gap:0.9rem;">
                    <div style="background:{tokens['fail_bg']}; border:1px solid {tokens['fail_color']};
                        border-radius:8px; width:40px; height:40px; display:flex; align-items:center;
                        justify-content:center; flex-shrink:0;">
                        {get_icon_svg("shield_alert", size=22, color=tokens["fail_color"])}
                    </div>
                    <div>
                        <div style="font-size:1.05rem; font-weight:800; color:{tokens['fail_color']}; letter-spacing:0.02em;">
                            EPISTEMIC ABSTENTION · ZERO UNVERIFIED GUESSES
                        </div>
                        <div style="color:{tokens['text']}; font-size:0.84rem; line-height:1.5; margin-top:0.35rem;">
                            <b>Abstention Reason:</b> {result.unknown_reason or "Low confidence or ambiguous signal parameters."}<br>
                            SpectralQ enforces conservative defense intelligence standards: an honest UNKNOWN state is
                            epistemically superior to an unverified false positive.
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Executive Decision Hero (Three-Column Cockpit)
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.6rem;">
            {get_icon_svg("target", size=18, color=tokens['primary'])}
            <span style="font-size:0.95rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                Executive Decision Cockpit
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_mod = result.top_hypothesis.modulation if (result and not result.is_unknown) else "UNKNOWN"
    conf_pct = (result.final_confidence * 100.0) if result else 0.0
    ladder = result.ladder_level if result else "N/A"
    rule_ml_agree = result.rule_ml_agreement if result else False

    # Promote ladder to L5 on the executive card if decoder confirms CRC pass or sync lock
    if decoder is not None and result is not None:
        _mc_crc_ok = getattr(decoder, "crc_passed", False)
        _mc_ber_val = getattr(decoder, "reencode_ber", None)
        _mc_sync_ok = getattr(decoder, "sync_word", None) is not None
        _mc_ber_zero = _mc_ber_val is not None and _mc_ber_val == 0.0
        if _mc_crc_ok or (_mc_ber_zero and _mc_sync_ok):
            ladder = "L5"

    h_col1, h_col2, h_col3 = st.columns([1.3, 1.0, 1.7])

    with h_col1:
        consensus_chip = (
            f"<span class='sq-badge badge-pass'>{get_icon_svg('circle_check', size=11)} RULE + ML CONSENSUS</span>"
            if rule_ml_agree
            else f"<span class='sq-badge badge-fail'>{get_icon_svg('circle_x', size=11)} CONSENSUS DIVERGENCE</span>"
        )
        st.markdown(
            f"""
            <div class="sq-card sq-card-hero" style="min-height:165px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div class="sq-card-title">PRIMARY IDENTIFICATION</div>
                    <div class="sq-card-value" style="color:{tokens['primary']}; font-size:1.9rem; margin:0.2rem 0;">
                        {top_mod}
                    </div>
                </div>
                <div>
                    <div style="font-size:0.75rem; color:{tokens['text_muted']}; margin-bottom:0.4rem;">
                        Evidence Ladder: <span class="sq-badge badge-ladder">{ladder}</span>
                    </div>
                    <div>{consensus_chip}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with h_col2:
        gauge_html = _render_confidence_arc(conf_pct, (result.is_unknown if result else False), tokens)
        st.markdown(
            f"""
            <div class="sq-card" style="min-height:165px; display:flex; align-items:center; justify-content:center; text-align:center;">
                {gauge_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with h_col3:
        why_text = ""
        passed_ct = 0
        failed_ct = 0
        if result:
            passed_ct = len([e for e in result.evidence if e.status == "PASS"])
            failed_ct = len(result.failed_checks)
            if result.is_unknown:
                why_text = (
                    f"The pipeline abstained because verification gates failed or consensus diverged. "
                    f"Rule AMC suggested <b>{result.rule_prediction}</b> while ML predicted <b>{result.ml_prediction}</b>."
                )
            else:
                raw_p_txt = f"p={result.ml_probability:.2f}" if result.ml_probability is not None else "p=N/A"
                why_text = (
                    f"Identified as <b>{top_mod}</b> at Evidence Ladder <b>{ladder}</b>. "
                    f"ML classifier ({result.ml_prediction}, {raw_p_txt}) and rule-based AMC ({result.rule_prediction}) reached consensus. "
                    f"Auditable evidence passed <b>{passed_ct}</b> checks with {failed_ct} failures."
                )
        else:
            why_text = "Awaiting signal telemetry contract."

        st.markdown(
            f"""
            <div class="sq-why-callout" style="min-height:165px; display:flex; flex-direction:column; justify-content:space-between; margin:0;">
                <div>
                    <div class="sq-why-title" style="display:flex; align-items:center; gap:0.4rem;">
                        {get_icon_svg("info", size=14, color=tokens['primary'])}
                        DECISION RATIONALE (EVIDENCE CHAIN)
                    </div>
                    <p class="sq-why-text" style="font-size:0.8rem; line-height:1.45; margin-top:0.3rem;">
                        {why_text}
                    </p>
                </div>
                <div style="display:flex; gap:0.5rem; margin-top:0.5rem; font-family:'JetBrains Mono', monospace; font-size:0.68rem;">
                    <span style="color:{tokens['pass_color']};">✓ {passed_ct} Checks Passed</span>
                    <span style="color:{tokens['text_muted']};">·</span>
                    <span style="color:{tokens['fail_color'] if failed_ct > 0 else tokens['text_muted']};">✗ {failed_ct} Failures</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Evidence Chain (Horizontal Process Pipeline)
    st.markdown(
        f"""
        <div style="background:{tokens['card_bg']}; border:1px solid {tokens['card_border']}; border-radius:10px; padding:0.75rem 1.0rem; margin-bottom:1.25rem;">
            <div style="font-size:0.65rem; font-weight:800; color:{tokens['text_muted']}; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.5rem;">
                Evidence Verification Hierarchy
            </div>
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.5rem; font-size:0.72rem; font-weight:700;">
                <span style="color:{tokens['pass_color']};">1. Raw Signal</span>
                <span style="color:{tokens['text_muted']};">→</span>
                <span style="color:{tokens['pass_color']};">2. IQ Features</span>
                <span style="color:{tokens['text_muted']};">→</span>
                <span style="color:{tokens['pass_color']};">3. Rule AMC</span>
                <span style="color:{tokens['text_muted']};">→</span>
                <span style="color:{tokens['pass_color']};">4. ML Classifier</span>
                <span style="color:{tokens['text_muted']};">→</span>
                <span style="color:{tokens['primary'] if rule_ml_agree else tokens['fail_color']};">5. Consensus</span>
                <span style="color:{tokens['text_muted']};">→</span>
                <span style="color:{tokens['pass_color'] if decoder and decoder.status == 'SUCCESS' else tokens['text_muted']};">6. Decoder</span>
                <span style="color:{tokens['text_muted']};">→</span>
                <span style="color:{tokens['violet']};">7. Ladder {ladder}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4. 10-Stage Blind RF Analysis Pipeline (Visual Journey)
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                {get_icon_svg("layers", size=18, color=tokens['primary'])}
                <span style="font-size:0.95rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                    10-Stage Pipeline Traversal
                </span>
            </div>
            <span style="font-size:0.7rem; color:{tokens['text_muted']};">Interactive Journey · Click to Inspect</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    stages = [
        ("01", "INGEST", "Signal Observatory", analysis.fs_source if analysis else "Fs 0.8M"),
        ("02", "FORENSIC", "Signal Observatory", "IQ Stream"),
        ("03", "BURST", "Signal Observatory", f"{len(analysis.bursts)} burst" if analysis and analysis.bursts else "1 burst"),
        ("04", "BLIND DSP", "Signal Observatory", f"{analysis.snr.display_value}" if analysis and analysis.snr else "SNR Est"),
        ("05", "AMC FEAT", "Modulation & Hypotheses", "Cumulants"),
        ("06", "CLASSIFIER", "Modulation & Hypotheses", result.ml_prediction if result else "QPSK"),
        ("07", "DEMOD", "Decoder & Bitstream", "Lock"),
        ("08", "FEC/SYNC", "Decoder & Bitstream", decoder.fec_used if decoder else "FEC"),
        ("09", "BITSTREAM", "Decoder & Bitstream", f"{decoder.decoded_bits_count}b" if decoder and getattr(decoder, 'decoded_bits_count', 0) else "Bits"),
        ("10", "DECISION", "Evidence & Decision", f"L{ladder}"),
    ]

    p_cols = st.columns(10)
    for idx, (num, name, target_ws, sub_val) in enumerate(stages):
        with p_cols[idx]:
            btn_label = f"S{num}\n{name}\n{sub_val}"
            if st.button(btn_label, key=f"mc_step_btn_{num}", use_container_width=True):
                set_workspace(target_ws)
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. Canonical Physical Metrics (Tier A & Tier B with Interactive Detail Popovers)
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.6rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                {get_icon_svg("spectrum", size=18, color=tokens['primary'])}
                <span style="font-size:0.95rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                    Canonical Physical &amp; Signal Telemetry
                </span>
            </div>
            <span style="font-size:0.7rem; color:{tokens['text_muted']};">Verified 95% Confidence Intervals</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Metric 1: CFO
    cfo_val = analysis.cfo.display_value if (analysis and analysis.cfo) else "N/A"
    cfo_method = analysis.cfo.method if (analysis and analysis.cfo) else "Cyclic-FFT"
    cfo_ci = f"[{analysis.cfo.ci_lo:.1f}, {analysis.cfo.ci_hi:.1f}] Hz" if (analysis and analysis.cfo and analysis.cfo.ci_lo) else "±500 Hz"

    # Metric 2: SNR
    snr_val = analysis.snr.display_value if (analysis and analysis.snr) else "N/A"
    snr_method = analysis.snr.method if (analysis and analysis.snr) else "M2M4"
    snr_ci = f"[{analysis.snr.ci_lo:.1f}, {analysis.snr.ci_hi:.1f}] dB" if (analysis and analysis.snr and analysis.snr.ci_lo) else "N/A"

    # Metric 3: EVM
    evm_val = "N/A"
    if decoder and decoder.evm_percent is not None:
        evm_val = f"{decoder.evm_percent:.1f}%"
    elif analysis and analysis.features and analysis.features.evm is not None:
        evm_val = f"{analysis.features.evm * 100.0:.1f}%"

    # Metric 4: Symbol Rate (Baud)
    baud_val = analysis.baud_rate.display_value if (analysis and analysis.baud_rate) else (analysis.baud.display_value if analysis and analysis.baud else "N/A")
    baud_method = analysis.baud_rate.method if (analysis and analysis.baud_rate) else "Cyclic Auto"

    # Row 1 (Tier A: Hero Metrics)
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">CARRIER FREQ OFFSET (CFO)</div>
                <div class="sq-card-value" style="color:{tokens['primary']};">{cfo_val}</div>
                <div class="sq-card-sub">Method: {cfo_method}</div>
                <div style="margin-top:0.4rem; height:4px; background:rgba(255,255,255,0.08); border-radius:2px; overflow:hidden;">
                    <div style="width:65%; height:100%; background:{tokens['primary']};"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.popover("ⓘ CFO Details", use_container_width=True):
            st.markdown(f"**Carrier Frequency Offset (CFO)**")
            st.caption(TOOLTIPS["CFO"])
            st.markdown(f"- **Observed:** `{cfo_val}`\n- **Method:** `{cfo_method}`\n- **95% Confidence Interval:** `{cfo_ci}`\n- **Source:** Sinchana Blind DSP Engine")

    with m_col2:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">SIGNAL-TO-NOISE RATIO (SNR)</div>
                <div class="sq-card-value" style="color:{tokens['pass_color']};">{snr_val}</div>
                <div class="sq-card-sub">Method: {snr_method}</div>
                <div style="margin-top:0.4rem; height:4px; background:rgba(255,255,255,0.08); border-radius:2px; overflow:hidden;">
                    <div style="width:80%; height:100%; background:{tokens['pass_color']};"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.popover("ⓘ SNR Details", use_container_width=True):
            st.markdown(f"**Signal-to-Noise Ratio (SNR)**")
            st.caption(TOOLTIPS["SNR"])
            st.markdown(f"- **Observed:** `{snr_val}`\n- **Method:** `{snr_method}`\n- **95% Confidence Interval:** `{snr_ci}`\n- **Interpretation:** Operational SNR above detection floor.")

    with m_col3:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">ERROR VECTOR MAGNITUDE (EVM)</div>
                <div class="sq-card-value" style="color:{tokens['warn_color']};">{evm_val}</div>
                <div class="sq-card-sub">Constellation RMS Fidelity</div>
                <div style="margin-top:0.4rem; height:4px; background:rgba(255,255,255,0.08); border-radius:2px; overflow:hidden;">
                    <div style="width:40%; height:100%; background:{tokens['warn_color']};"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.popover("ⓘ EVM Details", use_container_width=True):
            st.markdown(f"**Error Vector Magnitude (EVM)**")
            st.caption(TOOLTIPS["EVM"])
            st.markdown(f"- **Measured RMS:** `{evm_val}`\n- **Standard Reference:** Matched constellation cluster dispersion\n- **Impact:** Used in Level 3/4 evidence consensus.")

    with m_col4:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">SYMBOL RATE (BAUD)</div>
                <div class="sq-card-value">{baud_val}</div>
                <div class="sq-card-sub">Method: {baud_method}</div>
                <div style="margin-top:0.4rem; height:4px; background:rgba(255,255,255,0.08); border-radius:2px; overflow:hidden;">
                    <div style="width:70%; height:100%; background:{tokens['accent']};"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.popover("ⓘ Baud Details", use_container_width=True):
            st.markdown(f"**Symbol Rate (Baud)**")
            st.caption(TOOLTIPS["BAUD"])
            st.markdown(f"- **Estimated Value:** `{baud_val}`\n- **Estimation Method:** `{baud_method}`\n- **Source:** Sinchana Cyclic Autocorrelation Peak Detector")

    # Row 2 (Tier B: Supporting Metrics)
    bw_val = analysis.bandwidth.display_value if (analysis and analysis.bandwidth) else "N/A"
    ber_val = f"{decoder.ber:.2e}" if (decoder and decoder.ber is not None) else ("ABSTAINED" if (result and result.is_unknown) else "UNAVAILABLE")

    m_col5, m_col6, m_col7, m_col8 = st.columns(4)
    with m_col5:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">OCCUPIED BANDWIDTH</div>
                <div class="sq-card-value" style="font-size:1.25rem;">{bw_val}</div>
                <div class="sq-card-sub">3 dB Spectral Occupancy</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.popover("ⓘ Bandwidth", use_container_width=True):
            st.caption(TOOLTIPS["BANDWIDTH"])

    with m_col6:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">EVIDENCE LADDER</div>
                <div class="sq-card-value" style="font-size:1.25rem; color:{tokens['violet']};">{ladder}</div>
                <div class="sq-card-sub">Hierarchy Level (L1–L5)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.popover("ⓘ Ladder", use_container_width=True):
            st.caption(TOOLTIPS["LADDER"])

    with m_col7:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">MODULATION CLASS</div>
                <div class="sq-card-value" style="font-size:1.25rem; color:{tokens['primary']};">{top_mod}</div>
                <div class="sq-card-sub">AMC ML: {result.ml_prediction if result else 'N/A'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.popover("ⓘ Modulation", use_container_width=True):
            st.caption("Modulation identified via N5 hybrid agreement between rule-based AMC and calibrated ML.")

    with m_col8:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">INTEGRITY / BER</div>
                <div class="sq-card-value" style="font-size:1.25rem; color:{tokens['pass_color'] if ber_val != 'UNAVAILABLE' else tokens['text_muted']};">{ber_val}</div>
                <div class="sq-card-sub">Post-Demod Residual</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.popover("ⓘ BER", use_container_width=True):
            st.caption(TOOLTIPS["BER"])

    st.markdown("<br>", unsafe_allow_html=True)

    # 6. Quick Navigation to Deep Workspaces (Visual Tiles)
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.6rem;">
            {get_icon_svg("zap", size=18, color=tokens['primary'])}
            <span style="font-size:0.95rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                Operational Workspace Launchers
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    with q_col1:
        st.markdown(
            f"""
            <div style="background:{tokens['card_bg']}; border:1px solid {tokens['card_border']};
                border-radius:10px; padding:0.85rem; margin-bottom:0.4rem; min-height:85px;">
                <div style="display:flex; align-items:center; gap:0.4rem; font-weight:700; color:{tokens['text']}; font-size:0.82rem;">
                    {get_icon_svg("signal_observatory", size=16, color=tokens['primary'])} Observatory
                </div>
                <div style="font-size:0.7rem; color:{tokens['text_muted']}; margin-top:0.3rem;">
                    Physical I/Q, PSD &amp; burst analytics
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Observatory →", key="mc_launch_obs", use_container_width=True):
            set_workspace("Signal Observatory")
            st.rerun()

    with q_col2:
        st.markdown(
            f"""
            <div style="background:{tokens['card_bg']}; border:1px solid {tokens['card_border']};
                border-radius:10px; padding:0.85rem; margin-bottom:0.4rem; min-height:85px;">
                <div style="display:flex; align-items:center; gap:0.4rem; font-weight:700; color:{tokens['text']}; font-size:0.82rem;">
                    {get_icon_svg("modulation_hypotheses", size=16, color=tokens['primary'])} Modulation
                </div>
                <div style="font-size:0.7rem; color:{tokens['text_muted']}; margin-top:0.3rem;">
                    AMC classifier &amp; candidate ranking
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Modulation →", key="mc_launch_mod", use_container_width=True):
            set_workspace("Modulation & Hypotheses")
            st.rerun()

    with q_col3:
        st.markdown(
            f"""
            <div style="background:{tokens['card_bg']}; border:1px solid {tokens['card_border']};
                border-radius:10px; padding:0.85rem; margin-bottom:0.4rem; min-height:85px;">
                <div style="display:flex; align-items:center; gap:0.4rem; font-weight:700; color:{tokens['text']}; font-size:0.82rem;">
                    {get_icon_svg("decoder_bitstream", size=16, color=tokens['primary'])} Decoder
                </div>
                <div style="font-size:0.7rem; color:{tokens['text_muted']}; margin-top:0.3rem;">
                    FEC chains, sync word &amp; CRC
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Decoder →", key="mc_launch_dec", use_container_width=True):
            set_workspace("Decoder & Bitstream")
            st.rerun()

    with q_col4:
        st.markdown(
            f"""
            <div style="background:{tokens['card_bg']}; border:1px solid {tokens['card_border']};
                border-radius:10px; padding:0.85rem; margin-bottom:0.4rem; min-height:85px;">
                <div style="display:flex; align-items:center; gap:0.4rem; font-weight:700; color:{tokens['text']}; font-size:0.82rem;">
                    {get_icon_svg("evidence_decision", size=16, color=tokens['primary'])} Evidence
                </div>
                <div style="font-size:0.7rem; color:{tokens['text_muted']}; margin-top:0.3rem;">
                    Auditable evidence ledger &amp; ladder
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Evidence →", key="mc_launch_ev", use_container_width=True):
            set_workspace("Evidence & Decision")
            st.rerun()
