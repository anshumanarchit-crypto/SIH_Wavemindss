"""
Workspace 1: Mission Control (Executive / Evaluator Overview).
Provides high-density executive telemetry, decision rationale, 8 canonical metrics,
and the interactive 10-stage pipeline stepper.
"""

from typing import Optional
import streamlit as st

from ui.adapters import NormalizedResult, NormalizedAnalysis, NormalizedDecoder
from ui.styles.theme import TOOLTIPS, get_theme_tokens
from ui.state.session_state import set_workspace


def render_mission_control(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
    decoder: Optional[NormalizedDecoder],
) -> None:
    """Renders the executive Mission Control workspace."""
    tokens = get_theme_tokens()

    # 1. Decision Banner / Abstention Alert
    if result and result.is_unknown:
        st.markdown(
            f"""
            <div class="sq-unknown-banner">
                <div class="sq-unknown-title">
                    ⚠️ DECISION: ABSTAINED (UNKNOWN STATE)
                </div>
                <div class="sq-unknown-desc">
                    <b>Reason:</b> {result.unknown_reason or "Low confidence or ambiguous signal evidence."}<br>
                    SpectralQ deliberately declined to guess rather than risk an erroneous classification.
                    Inspect <b>Modulation & Hypotheses</b> and <b>Evidence & Decision</b> to see the conflicting metrics.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Executive Decision Highlight Card & "WHY THIS DECISION?"
    st.markdown("### 🎯 Executive Decision Summary")
    c_dec1, c_dec2 = st.columns([1.2, 1.8])

    with c_dec1:
        top_mod = result.top_hypothesis.modulation if (result and not result.is_unknown) else "UNKNOWN"
        conf_pct = (result.final_confidence * 100.0) if result else 0.0
        ladder = result.ladder_level if result else "N/A"
        rule_ml_agree = result.rule_ml_agreement if result else False

        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">PRIMARY IDENTIFICATION</div>
                <div class="sq-card-value" style="color:{tokens['primary']};">{top_mod}</div>
                <div class="sq-card-sub" style="margin-top:0.4rem;">
                    Confidence: <b>{conf_pct:.1f}%</b> | Ladder: <span class="sq-badge badge-ladder">{ladder}</span>
                </div>
                <div style="margin-top:0.5rem;">
                    Consensus: {"<span class='sq-badge badge-pass'>RULE + ML AGREE</span>" if rule_ml_agree else "<span class='sq-badge badge-fail'>CONSENSUS DIVERGENCE</span>"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_dec2:
        # "WHY THIS DECISION?" Rationale Drawer
        why_text = ""
        if result:
            if result.is_unknown:
                pen_txt = f"{result.rule_ml_penalty:.2f}" if result.rule_ml_penalty is not None else "0.00"
                why_text = (
                    f"The pipeline abstained because critical verification checks failed or confidence dropped below "
                    f"the operational threshold. Rule AMC suggested '{result.rule_prediction}' while ML predicted "
                    f"'{result.ml_prediction}'. Penalty applied: {pen_txt}."
                )
            else:
                passed_ct = len([e for e in result.evidence if e.status == "PASS"])
                failed_ct = len(result.failed_checks)
                raw_p_txt = f"p={result.ml_probability:.2f}" if result.ml_probability is not None else "p=N/A"
                why_text = (
                    f"Identified as <b>{top_mod}</b> at Evidence Ladder <b>{ladder}</b> with {conf_pct:.1f}% confidence. "
                    f"ML classifier ({result.ml_prediction}, {raw_p_txt}) and rule-based AMC "
                    f"({result.rule_prediction}) reached consensus. Passed <b>{passed_ct}</b> verification checks "
                    f"with {failed_ct} failures."
                )
        else:
            why_text = "No telemetry loaded. Please select or ingest a capture file."

        st.markdown(
            f"""
            <div class="sq-why-callout">
                <div class="sq-why-title">💡 WHY THIS DECISION? (Evidence Chain)</div>
                <p class="sq-why-text">{why_text}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 3. 10-Stage Pipeline Traversal Stepper
    st.markdown("### 🔄 10-Stage Blind RF Analysis Pipeline")
    st.caption("Click any stage to jump directly to its dedicated analytical workspace.")

    stages = [
        ("01", "INGEST", "Signal Observatory"),
        ("02", "FORENSICS", "Signal Observatory"),
        ("03", "BURST", "Signal Observatory"),
        ("04", "BLIND DSP", "Signal Observatory"),
        ("05", "AMC FEAT", "Modulation & Hypotheses"),
        ("06", "CLASSIFIER", "Modulation & Hypotheses"),
        ("07", "DEMOD", "Decoder & Bitstream"),
        ("08", "FEC/SYNC", "Decoder & Bitstream"),
        ("09", "BITSTREAM", "Decoder & Bitstream"),
        ("10", "EVIDENCE", "Evidence & Decision"),
    ]

    p_cols = st.columns(10)
    for idx, (num, name, target_ws) in enumerate(stages):
        with p_cols[idx]:
            # Determine status
            status_badge = "PASS"
            if result and result.is_unknown and idx >= 6:
                status_badge = "ABSTAIN"
            elif not result:
                status_badge = "IDLE"

            btn_label = f"S{num}\n{name}"
            if st.button(btn_label, key=f"step_btn_{num}", use_container_width=True):
                set_workspace(target_ws)
                st.rerun()

    st.markdown("---")

    # 4. 8 Canonical Metric Summary Cards (with Tooltips)
    st.markdown("### 📊 Canonical Signal & Physical Metrics")

    # Metric 1: CFO
    cfo_val = "N/A"
    cfo_sub = "Not Estimated"
    if analysis and analysis.cfo:
        cfo_val = analysis.cfo.display_value
        cfo_sub = f"Method: {analysis.cfo.method or 'FFT-Cyclic'}"

    # Metric 2: SNR
    snr_val = "N/A"
    snr_sub = "Not Estimated"
    if analysis and analysis.snr:
        snr_val = analysis.snr.display_value
        snr_sub = f"Method: {analysis.snr.method or 'M2M4'}"

    # Metric 3: EVM
    evm_val = "N/A"
    evm_sub = "Constellation Lock"
    if decoder and decoder.evm_percent is not None:
        evm_val = f"{decoder.evm_percent:.1f}%"
        evm_sub = "Measured RMS"
    elif analysis and analysis.features and analysis.features.evm is not None:
        evm_val = f"{analysis.features.evm * 100.0:.1f}%"
        evm_sub = "Spectral Estimation"

    # Metric 4: Symbol Rate (Baud)
    baud_val = "N/A"
    baud_sub = "Blind Rate"
    if analysis and analysis.baud_rate:
        baud_val = analysis.baud_rate.display_value
        baud_sub = "Cyclic Peak"

    # Row 1
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">
                    CARRIER FREQ OFFSET (CFO)
                    <span class="sq-info-icon" title="{TOOLTIPS['CFO']}">ⓘ</span>
                </div>
                <div class="sq-card-value">{cfo_val}</div>
                <div class="sq-card-sub">{cfo_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col2:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">
                    SIGNAL-TO-NOISE RATIO (SNR)
                    <span class="sq-info-icon" title="{TOOLTIPS['SNR']}">ⓘ</span>
                </div>
                <div class="sq-card-value">{snr_val}</div>
                <div class="sq-card-sub">{snr_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col3:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">
                    ERROR VECTOR MAGNITUDE (EVM)
                    <span class="sq-info-icon" title="{TOOLTIPS['EVM']}">ⓘ</span>
                </div>
                <div class="sq-card-value">{evm_val}</div>
                <div class="sq-card-sub">{evm_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col4:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">
                    SYMBOL RATE (BAUD)
                    <span class="sq-info-icon" title="{TOOLTIPS['BAUD']}">ⓘ</span>
                </div>
                <div class="sq-card-value">{baud_val}</div>
                <div class="sq-card-sub">{baud_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Metric 5: Bandwidth
    bw_val = "N/A"
    bw_sub = "Occupied Spectrum"
    if analysis and analysis.bandwidth:
        bw_val = analysis.bandwidth.display_value
        bw_sub = "3 dB Bandwidth"

    # Metric 6: Ladder Level
    ladder_val = result.ladder_level if result else "N/A"
    ladder_sub = f"Ladder Level (L1-L5)"

    # Metric 7: Modulation
    mod_val = result.top_hypothesis.modulation if (result and not result.is_unknown) else "UNKNOWN"
    mod_sub = f"ML: {result.ml_prediction if result else 'N/A'}"

    # Metric 8: Decision / BER
    ber_val = "UNAVAILABLE"
    ber_sub = "BER Post-Demod"
    if decoder and decoder.ber is not None:
        ber_val = f"{decoder.ber:.2e}"
        ber_sub = "Post-Demod BER"
    elif result and result.is_unknown:
        ber_val = "ABSTAINED"
        ber_sub = "Confidence < Gate"

    # Row 2
    m_col5, m_col6, m_col7, m_col8 = st.columns(4)
    with m_col5:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">
                    OCCUPIED BANDWIDTH
                    <span class="sq-info-icon" title="{TOOLTIPS['BANDWIDTH']}">ⓘ</span>
                </div>
                <div class="sq-card-value">{bw_val}</div>
                <div class="sq-card-sub">{bw_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col6:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">
                    EVIDENCE LADDER
                    <span class="sq-info-icon" title="{TOOLTIPS['LADDER']}">ⓘ</span>
                </div>
                <div class="sq-card-value"><span class="sq-badge badge-ladder">{ladder_val}</span></div>
                <div class="sq-card-sub">{ladder_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col7:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">
                    MODULATION CLASS
                    <span class="sq-info-icon" title="Modulation scheme identified by AMC and classifier.">ⓘ</span>
                </div>
                <div class="sq-card-value">{mod_val}</div>
                <div class="sq-card-sub">{mod_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col8:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">
                    INTEGRITY / BER
                    <span class="sq-info-icon" title="{TOOLTIPS['BER']}">ⓘ</span>
                </div>
                <div class="sq-card-value">{ber_val}</div>
                <div class="sq-card-sub">{ber_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 5. Quick Navigation Action Bar
    st.markdown("### ⚡ Quick Navigation to Deep Workspaces")
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    with q_col1:
        if st.button("🔭 Open Signal Observatory", use_container_width=True):
            set_workspace("Signal Observatory")
            st.rerun()
    with q_col2:
        if st.button("🎯 Open Modulation Analysis", use_container_width=True):
            set_workspace("Modulation & Hypotheses")
            st.rerun()
    with q_col3:
        if st.button("🔓 Open Decoder Chain", use_container_width=True):
            set_workspace("Decoder & Bitstream")
            st.rerun()
    with q_col4:
        if st.button("⚖️ Open Evidence Ledger", use_container_width=True):
            set_workspace("Evidence & Decision")
            st.rerun()
