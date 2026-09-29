"""
UI Summary Cards Component.
Renders the 8 canonical telemetry summary cards:
MODULATION, SYMBOL RATE / BAUD, CARRIER OFFSET, BANDWIDTH, SNR, FEC, INTERLEAVER, CONFIDENCE.
Every card explicitly presents: value, unit, source, status, and honest confidence.
Never shows unsupported values as zero, and never converts null to fake numbers.
"""

from typing import Optional
import streamlit as st
from ui.adapters.result_adapter import NormalizedResult
from ui.adapters.analysis_adapter import NormalizedAnalysis
from ui.adapters.decoder_adapter import NormalizedDecoder
from ui.components.icons import get_icon_svg


def render_summary_cards(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
    decoder: Optional[NormalizedDecoder],
):
    """Renders 8 summary cards across two responsive rows."""
    col1, col2, col3, col4 = st.columns(4)

    # 1. MODULATION
    with col1:
        if result:
            mod_val = "UNKNOWN" if result.is_unknown else result.top_hypothesis.modulation
            mod_sub = f"Source: N5 Consensus ({result.rule_prediction} / {result.ml_prediction})"
            badge_class = "badge-unknown" if result.is_unknown else "badge-pass"
            mod_badge = f'<span class="sq-badge {badge_class}">{"UNKNOWN" if result.is_unknown else "CONFIRMED"}</span>'
        else:
            mod_val = "N/A"
            mod_sub = "Awaiting analysis"
            mod_badge = '<span class="sq-badge badge-notrun">IDLE</span>'

        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title" style="display:flex; align-items:center; gap:6px;">
                    {get_icon_svg("modulation_hypotheses", size=13, color="#53D7FF")} Modulation Scheme
                </div>
                <div class="sq-card-value">{mod_val}</div>
                <div class="sq-card-sub">{mod_sub}</div>
                <div style="margin-top: 0.4rem;">{mod_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. SYMBOL RATE / BAUD
    with col2:
        if analysis and analysis.baud:
            baud_val = analysis.baud.display_value
            baud_sub = f"CI: [{analysis.baud.ci_lo:.0f}, {analysis.baud.ci_hi:.0f}] • {analysis.baud.method}"
            baud_badge = '<span class="sq-badge badge-pass">ESTIMATED</span>'
        else:
            baud_val = "N/A"
            baud_sub = "Not available"
            baud_badge = '<span class="sq-badge badge-unavail">UNAVAILABLE</span>'

        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title" style="display:flex; align-items:center; gap:6px;">
                    {get_icon_svg("activity", size=13, color="#53D7FF")} Symbol Rate (Baud)
                </div>
                <div class="sq-card-value">{baud_val}</div>
                <div class="sq-card-sub">{baud_sub}</div>
                <div style="margin-top: 0.4rem;">{baud_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3. CARRIER FREQUENCY OFFSET
    with col3:
        if analysis and analysis.cfo:
            cfo_val = analysis.cfo.display_value
            cfo_sub = f"CI: [{analysis.cfo.ci_lo:.1f}, {analysis.cfo.ci_hi:.1f}] Hz • {analysis.cfo.method}"
            cfo_badge = '<span class="sq-badge badge-pass">ESTIMATED</span>'
        else:
            cfo_val = "N/A"
            cfo_sub = "Not available"
            cfo_badge = '<span class="sq-badge badge-unavail">UNAVAILABLE</span>'

        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title" style="display:flex; align-items:center; gap:6px;">
                    {get_icon_svg("radio", size=13, color="#53D7FF")} Carrier Offset (CFO)
                </div>
                <div class="sq-card-value">{cfo_val}</div>
                <div class="sq-card-sub">{cfo_sub}</div>
                <div style="margin-top: 0.4rem;">{cfo_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. BANDWIDTH
    with col4:
        if analysis and analysis.bandwidth:
            bw_val = analysis.bandwidth.display_value
            bw_sub = f"CI: [{analysis.bandwidth.ci_lo / 1e3:.1f}, {analysis.bandwidth.ci_hi / 1e3:.1f}] kHz • {analysis.bandwidth.method}"
            bw_badge = '<span class="sq-badge badge-pass">ESTIMATED</span>'
        else:
            bw_val = "N/A"
            bw_sub = "Not available"
            bw_badge = '<span class="sq-badge badge-unavail">UNAVAILABLE</span>'

        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title" style="display:flex; align-items:center; gap:6px;">
                    {get_icon_svg("spectrum", size=13, color="#53D7FF")} Occupied Bandwidth
                </div>
                <div class="sq-card-value">{bw_val}</div>
                <div class="sq-card-sub">{bw_sub}</div>
                <div style="margin-top: 0.4rem;">{bw_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Second row
    col5, col6, col7, col8 = st.columns(4)

    # 5. SNR
    with col5:
        if analysis and analysis.snr:
            snr_val = analysis.snr.display_value
            snr_sub = f"Method: {analysis.snr.method} • CI: [{analysis.snr.ci_lo:.1f}, {analysis.snr.ci_hi:.1f}] dB"
            snr_badge = '<span class="sq-badge badge-pass">ESTIMATED</span>'
        else:
            snr_val = "N/A"
            snr_sub = "Not available"
            snr_badge = '<span class="sq-badge badge-unavail">UNAVAILABLE</span>'

        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title" style="display:flex; align-items:center; gap:6px;">
                    {get_icon_svg("waveform", size=13, color="#53D7FF")} Estimated SNR
                </div>
                <div class="sq-card-value">{snr_val}</div>
                <div class="sq-card-sub">{snr_sub}</div>
                <div style="margin-top: 0.4rem;">{snr_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 6. FEC
    with col6:
        if decoder:
            fec_val = decoder.fec_used
            fec_sub = f"Status: {decoder.status} • Reason: {decoder.failure_reason or 'None'}"
            if decoder.status == "OK":
                fec_badge = '<span class="sq-badge badge-pass">VERIFIED</span>'
            elif decoder.status == "UNSUPPORTED":
                fec_badge = '<span class="sq-badge badge-unavail">UNSUPPORTED</span>'
            else:
                fec_badge = '<span class="sq-badge badge-fail">FAILED</span>'
        elif result and result.top_hypothesis:
            fec_val = result.top_hypothesis.fec
            fec_sub = "Source: Hypothesis Engine"
            fec_badge = '<span class="sq-badge badge-pass">HYPOTHESIZED</span>'
        else:
            fec_val = "N/A"
            fec_sub = "Not available"
            fec_badge = '<span class="sq-badge badge-unavail">UNAVAILABLE</span>'

        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title" style="display:flex; align-items:center; gap:6px;">
                    {get_icon_svg("decoder_bitstream", size=13, color="#53D7FF")} Forward Error Correction
                </div>
                <div class="sq-card-value">{fec_val}</div>
                <div class="sq-card-sub">{fec_sub}</div>
                <div style="margin-top: 0.4rem;">{fec_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 7. INTERLEAVER
    with col7:
        if decoder:
            intl_val = decoder.interleaver_used
            intl_sub = f"BER: {decoder.ber_display}"
            intl_badge = f'<span class="sq-badge badge-ladder">{decoder.status}</span>'
        elif result and result.top_hypothesis:
            intl_val = result.top_hypothesis.interleaver
            intl_sub = "Source: Hypothesis Engine"
            intl_badge = '<span class="sq-badge badge-ladder">HYPOTHESIZED</span>'
        else:
            intl_val = "N/A"
            intl_sub = "Not available"
            intl_badge = '<span class="sq-badge badge-unavail">UNAVAILABLE</span>'

        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title" style="display:flex; align-items:center; gap:6px;">
                    {get_icon_svg("layers", size=13, color="#53D7FF")} Interleaver Scheme
                </div>
                <div class="sq-card-value">{intl_val}</div>
                <div class="sq-card-sub">{intl_sub}</div>
                <div style="margin-top: 0.4rem;">{intl_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 8. CONFIDENCE
    with col8:
        if result:
            if result.is_unknown:
                conf_val = "UNKNOWN"
                conf_sub = f"Version: {result.confidence_version} • ABSTAIN"
                conf_badge = '<span class="sq-badge badge-unknown">ABSTAIN</span>'
            else:
                conf_val = f"{result.final_confidence * 100:.1f}%"
                conf_sub = f"Version: {result.confidence_version}"
                if result.final_confidence >= 0.90:
                    conf_badge = '<span class="sq-badge badge-pass">CONFIRMED</span>'
                elif result.final_confidence >= 0.80:
                    conf_badge = '<span class="sq-badge badge-ladder">HIGH CONFIDENCE</span>'
                else:
                    conf_badge = '<span class="sq-badge badge-unavail">LOW CONFIDENCE</span>'
        else:
            conf_val = "N/A"
            conf_sub = "Not evaluated"
            conf_badge = '<span class="sq-badge badge-notrun">IDLE</span>'

        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title" style="display:flex; align-items:center; gap:6px;">
                    {get_icon_svg("evidence_decision", size=13, color="#53D7FF")} Decision Confidence
                </div>
                <div class="sq-card-value">{conf_val}</div>
                <div class="sq-card-sub">{conf_sub}</div>
                <div style="margin-top: 0.4rem;">{conf_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
