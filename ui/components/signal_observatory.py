"""
Workspace 2: Signal Observatory (Physical Layer & RF Forensics).
Provides interactive Plotly visualizations for genuine capture I/Q samples.
Strictly adheres to Critical Fix A: Zero fake signals.
Displays 'RAW VISUALIZATION UNAVAILABLE' with physical parameters when samples are absent.
"""

from typing import Optional
import streamlit as st
import plotly.graph_objects as go

from ui.adapters import NormalizedAnalysis, NormalizedResult
from spectralq.visualization.artifacts import ObservatoryArtifacts
from ui.charts import (
    create_waveform_plot,
    create_spectrum_plot,
    create_waterfall_plot,
    create_constellation_plot,
    create_eye_diagram_plot,
    create_burst_timeline_plot,
)
from ui.styles.theme import get_theme_tokens


def render_signal_observatory(
    artifacts: Optional[ObservatoryArtifacts],
    analysis: Optional[NormalizedAnalysis],
    result: Optional[NormalizedResult],
) -> None:
    """Renders the Physical Signal Observatory workspace."""
    st.markdown("## 🔭 Signal Observatory & RF Forensics")
    st.caption("Interactive physical layer analysis rendered strictly from genuine capture data.")

    tokens = get_theme_tokens()

    # -------------------------------------------------------------------------
    # Case A: Raw Samples NOT Available -> Explicit Honest State
    # -------------------------------------------------------------------------
    if not artifacts or not artifacts.raw_available:
        st.markdown(
            f"""
            <div class="sq-unavailable-box">
                <div class="sq-unavailable-title">⚠️ RAW VISUALIZATION UNAVAILABLE</div>
                <div class="sq-unavailable-msg">
                    This capture bundle contains analysis telemetry and evidence contracts, but does not include raw I/Q sample recordings.<br><br>
                    Visualizations requiring sample-level data (waveform, PSD, constellation, eye diagram) cannot be rendered without fabricating data.<br>
                    <b>To view signal plots:</b> Upload or select a capture with raw I/Q data (<code>.cf32</code>, <code>.iq</code>, or <code>.wav</code>), or switch to <b>Signal Lab / Simulation</b>.
                </div>
                <span class="sq-badge badge-unavail">ZERO FAKE SIGNALS POLICY ENFORCED</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 📋 Estimated Physical Parameters (From Ingest & DSP Telemetry)")
        st.caption("The following verified physical parameters govern this capture:")

        pcol1, pcol2, pcol3, pcol4 = st.columns(4)
        with pcol1:
            fs_text = f"{analysis.fs_hz / 1e6:.3f} MHz" if analysis and analysis.fs_hz else "20.000 MHz (Nominal)"
            st.metric("Sampling Rate (fs)", fs_text)
        with pcol2:
            fc_text = f"{analysis.fc_hz / 1e6:.3f} MHz" if analysis and analysis.fc_hz else "0.000 MHz (Baseband)"
            st.metric("Center Frequency (fc)", fc_text)
        with pcol3:
            snr_text = analysis.snr.display_value if analysis and analysis.snr else "N/A"
            st.metric("Estimated SNR", snr_text)
        with pcol4:
            cfo_text = analysis.cfo.display_value if analysis and analysis.cfo else "N/A"
            st.metric("Estimated CFO", cfo_text)

        pcol5, pcol6, pcol7, pcol8 = st.columns(4)
        with pcol5:
            bw_text = analysis.bandwidth.display_value if analysis and analysis.bandwidth else "N/A"
            st.metric("Estimated Bandwidth", bw_text)
        with pcol6:
            baud_text = analysis.baud_rate.display_value if analysis and analysis.baud_rate else "N/A"
            st.metric("Estimated Symbol Rate", baud_text)
        with pcol7:
            burst_ct = len(analysis.bursts) if analysis and analysis.bursts else 0
            st.metric("Detected Bursts", f"{burst_ct} active")
        with pcol8:
            source_txt = result.source_mode.upper() if result else "OFFLINE"
            st.metric("Source Mode", source_txt)

        # If burst intervals exist in telemetry, we CAN show the burst timeline honestly
        if artifacts and artifacts.burst_view and artifacts.burst_view.total_bursts > 0:
            st.markdown("---")
            st.markdown("### ⏱️ Temporal Burst Intervals (From Analysis Telemetry)")
            fig_burst = create_burst_timeline_plot(artifacts)
            if fig_burst:
                st.plotly_chart(fig_burst, use_container_width=True)

        return

    # -------------------------------------------------------------------------
    # Case B: Raw Samples ARE Available -> Render Interactive Plotly Charts
    # -------------------------------------------------------------------------
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <div>
                <span class="sq-badge badge-pass">ACTUAL RAW SAMPLES LOADED</span>
                <span class="sq-badge badge-replay">{artifacts.source_provenance}</span>
                {"<span class='sq-badge badge-unavail'>VISUALIZATION DECIMATED</span>" if artifacts.downsampled else ""}
            </div>
            <div style="font-size:0.8rem; color:{tokens['text_muted']};">
                Samples: <b>{artifacts.metadata.get('sample_count', 'N/A')}</b> | Interactive Plotly Charts
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    obs_tabs = st.tabs([
        "📈 Time-Domain Waveform",
        "📊 Power Spectral Density (PSD)",
        "🌈 Spectrogram / Waterfall",
        "🎯 Constellation Diagram",
        "👁️ Eye Diagram",
        "⏱️ Burst Timeline & Power",
    ])

    # TAB 1: Waveform
    with obs_tabs[0]:
        st.markdown("#### In-Phase (I) and Quadrature (Q) Time Series")
        fig_wave = create_waveform_plot(artifacts)
        if fig_wave:
            st.plotly_chart(fig_wave, use_container_width=True)
        else:
            st.warning("Waveform trace could not be generated from samples.")

    # TAB 2: PSD
    with obs_tabs[1]:
        st.markdown("#### Power Spectral Density & Occupied Bandwidth")
        fig_psd = create_spectrum_plot(artifacts)
        if fig_psd:
            st.plotly_chart(fig_psd, use_container_width=True)
        else:
            st.warning("PSD could not be generated.")

    # TAB 3: Waterfall
    with obs_tabs[2]:
        st.markdown("#### Time-Frequency Spectrogram Heatmap")
        fig_wf = create_waterfall_plot(artifacts)
        if fig_wf:
            st.plotly_chart(fig_wf, use_container_width=True)
        else:
            st.warning("Spectrogram grid could not be generated.")

    # TAB 4: Constellation
    with obs_tabs[3]:
        st.markdown("#### I/Q Symbol Constellation")
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            fig_const = create_constellation_plot(artifacts)
            if fig_const:
                st.plotly_chart(fig_const, use_container_width=True)
            else:
                st.warning("Constellation points could not be generated.")
        with col_c2:
            st.markdown("##### Constellation Metrics")
            if artifacts.constellation:
                evm_str = f"{artifacts.constellation.evm_percent:.2f}%" if artifacts.constellation.evm_percent else "N/A"
                st.metric("Measured EVM (RMS)", evm_str)
                st.metric("Plotted Symbols", f"{artifacts.constellation.num_points} pts")
                st.caption("Unit circle shown as dashed line for reference. Center points are zero-mean normalized.")

    # TAB 5: Eye Diagram
    with obs_tabs[4]:
        st.markdown("#### Symbol Eye Diagram (In-Phase)")
        fig_eye = create_eye_diagram_plot(artifacts)
        if fig_eye:
            st.plotly_chart(fig_eye, use_container_width=True)
        else:
            st.warning("Eye diagram traces could not be generated.")

    # TAB 6: Burst Timeline
    with obs_tabs[5]:
        st.markdown("#### Temporal Power Envelope & Active Bursts")
        fig_burst = create_burst_timeline_plot(artifacts)
        if fig_burst:
            st.plotly_chart(fig_burst, use_container_width=True)
        else:
            st.info("No active burst boundaries detected.")
