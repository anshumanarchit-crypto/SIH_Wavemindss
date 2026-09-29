"""
Workspace: Wideband Spectrum Scanner & DDC Channelizer (Tier-1b).
Performs wideband energy detection, spectral occupancy mapping, and per-emission
digital down-conversion (DDC) channelization for Tier-1a single-signal analysis.
"""

from pathlib import Path
from typing import Optional
import numpy as np
import plotly.graph_objects as go
import streamlit as st

import core.io
from spectralq.dsp.wideband_scanner import (
    DetectedEmission,
    WidebandScanResult,
    channelize_emission,
    export_emission_for_pipeline,
    scan_wideband_spectrum,
)
from spectralq.pipeline.runner import run
from ui.adapters import adapt_analysis, adapt_decoder, adapt_result
from ui.state.session_state import set_active_case_artifacts, set_workspace
from ui.styles.theme import get_theme_tokens


def render_wideband_scanner() -> None:
    """Renders the Tier-1b Wideband Scanner workspace."""
    tokens = get_theme_tokens()

    st.markdown("## 📡 Wideband Spectrum Scanner (Tier-1b)")
    st.caption(
        "Wideband energy detection, spectral occupancy mapping, and Digital Down-Converter (DDC) "
        "channelization for isolated single-signal analysis."
    )

    # 1. Preset or Capture Selection
    st.markdown("### 🎛️ Ingest Wideband Capture")
    col1, col2 = st.columns([2, 1])

    with col1:
        preset_options = {
            "G8: Wideband 4 Emissions (1 MHz)": "data/official/sinchana/golden/G8_Wideband_4_emissions.cf32",
        }
        # Discover any other wideband captures
        wb_dir = Path("data") / "official" / "sinchana" / "golden"
        if wb_dir.exists():
            for p in wb_dir.glob("*wideband*.cf32"):
                preset_options[f"Official: {p.name}"] = str(p)

        selected_preset = st.selectbox(
            "Select Wideband Preset:",
            options=list(preset_options.keys()),
            help="Select golden wideband test captures with multiple concurrent emissions.",
        )
        capture_path = preset_options[selected_preset]

    with col2:
        user_fs = st.number_input(
            "Wideband Sample Rate (Hz):",
            min_value=100_000.0,
            max_value=100_000_000.0,
            value=1_000_000.0,
            step=100_000.0,
            format="%.0f",
            help="Hardware SDR sampling rate for wideband capture.",
        )

    # 2. Scanning parameters
    with st.expander("⚙️ Detection Threshold & Energy Detector Parameters", expanded=False):
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            margin_db = st.slider("Detection Threshold Margin (dB above noise):", 3.0, 30.0, 10.0, 1.0)
        with c_p2:
            n_fft_bins = st.selectbox("FFT Resolution (Bins):", [512, 1024, 2048, 4096], index=1)
        with c_p3:
            suppress_dc = st.checkbox("Suppress DC LO Leakage Spike", value=True)

    # 3. Execute Scan
    scan_state_key = f"wb_scan_{capture_path}_{user_fs}_{margin_db}"
    if st.button("🔍 Scan Spectrum & Map Occupancy", type="primary", use_container_width=True) or scan_state_key not in st.session_state:
        with st.spinner("Computing Welch PSD and clustering spectral energy..."):
            try:
                sig = core.io.load_signal(capture_path, sample_rate=user_fs)
                scan_res = scan_wideband_spectrum(
                    sig.samples,
                    fs_hz=user_fs,
                    n_fft=n_fft_bins,
                    threshold_margin_db=margin_db,
                    suppress_dc_spike=suppress_dc,
                )
                st.session_state[scan_state_key] = scan_res
                st.session_state["wb_current_samples"] = sig.samples
                st.session_state["wb_current_fs"] = user_fs
            except Exception as e:
                st.error(f"Failed to scan wideband signal: {e}")
                return

    scan_res: WidebandScanResult = st.session_state.get(scan_state_key)
    if not scan_res:
        return

    # 4. Summary Metrics
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Span", f"{scan_res.fs_hz / 1e6:.2f} MHz")
    with m2:
        st.metric("Noise Floor", f"{scan_res.noise_floor_db:.1f} dBFS")
    with m3:
        st.metric("Detection Gate", f"{scan_res.detection_threshold_db:.1f} dBFS")
    with m4:
        st.metric("Detected Emissions", f"{len(scan_res.emissions)}")

    # 5. Wideband Spectrum Plotly Chart
    st.markdown("### 📊 Wideband Spectrum Occupancy Map")
    fig = go.Figure()

    # PSD Curve
    fig.add_trace(
        go.Scatter(
            x=scan_res.freqs / 1e3,
            y=scan_res.psd_db,
            mode="lines",
            name="Power Spectral Density",
            line=dict(color=tokens["primary"], width=1.5),
            hovertemplate="Freq: %{x:.1f} kHz<br>Power: %{y:.1f} dBFS<extra></extra>",
        )
    )

    # Detection Threshold line
    fig.add_hline(
        y=scan_res.detection_threshold_db,
        line_dash="dash",
        line_color=tokens["error"],
        annotation_text="Detection Gate",
        annotation_position="bottom right",
    )

    # Shaded bounding boxes for detected emissions
    colors = ["#22c55e", "#06b6d4", "#eab308", "#a855f7", "#ec4899", "#f97316"]
    for i, em in enumerate(scan_res.emissions):
        color = colors[i % len(colors)]
        fig.add_vrect(
            x0=em.freq_start_hz / 1e3,
            x1=em.freq_stop_hz / 1e3,
            fillcolor=color,
            opacity=0.2,
            line_width=1,
            line_color=color,
            annotation_text=f"E#{em.emission_id} ({em.bandwidth_hz/1e3:.1f}k)",
            annotation_position="top left",
        )

    fig.update_layout(
        title="Wideband Power Spectral Density & Emission Clusters",
        xaxis_title="Baseband Frequency (kHz)",
        yaxis_title="Power Spectral Density (dBFS/Hz)",
        template=tokens["plotly_template"],
        margin=dict(l=40, r=40, t=50, b=40),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # 6. Detected Emissions Occupancy Table
    st.markdown("### 📋 Detected Emissions Occupancy Table")
    if not scan_res.emissions:
        st.info("No emissions detected above the threshold margin. Try reducing the detection margin slider above.")
        return

    for em in scan_res.emissions:
        with st.container():
            st.markdown(
                f"""
                <div class="sq-card" style="margin-bottom: 0.8rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span class="sq-badge badge-pass" style="font-size:0.95rem;">Emission #{em.emission_id}</span>
                            &nbsp; Center: <b>{em.center_freq_hz / 1e3:.1f} kHz</b> &nbsp;|&nbsp;
                            Span: <b>{em.bandwidth_hz / 1e3:.1f} kHz</b> &nbsp;|&nbsp;
                            Peak: <b>{em.peak_power_db:.1f} dBFS</b> &nbsp;|&nbsp;
                            SNR: <b>{em.snr_db:.1f} dB</b>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Channelize & Analyze action
            c_act1, c_act2 = st.columns([1, 3])
            with c_act1:
                btn_key = f"ddc_btn_{em.emission_id}"
                if st.button(
                    f"⚡ Channelize & Analyze #{em.emission_id}",
                    key=btn_key,
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner(f"DDC frequency translation & FIR decimation for Emission #{em.emission_id}..."):
                        all_samples = st.session_state.get("wb_current_samples")
                        wide_fs = st.session_state.get("wb_current_fs", 1e6)

                        # Run DDC channelization
                        narrow_iq, narrow_fs = channelize_emission(
                            iq_samples=all_samples,
                            fs_wide_hz=wide_fs,
                            center_freq_hz=em.center_freq_hz,
                            bandwidth_hz=em.bandwidth_hz,
                        )

                        # Export to scratch directory
                        scratch_dir = Path("data") / "scratch"
                        cap_file, _ = export_emission_for_pipeline(
                            narrowband_iq=narrow_iq,
                            fs_narrow_hz=narrow_fs,
                            emission_id=em.emission_id,
                            output_dir=scratch_dir,
                        )

                        # Execute SpectralQ pipeline
                        pipe_out = run(capture_path=str(cap_file), mode="live")

                        from spectralq.visualization.artifacts import prepare_observatory_artifacts
                        norm_res = adapt_result(pipe_out.result) if pipe_out.result else None
                        norm_ana = adapt_analysis(pipe_out.analysis) if pipe_out.analysis else None
                        norm_dec = adapt_decoder(pipe_out.decoder) if pipe_out.decoder else None

                        obs_artifacts = prepare_observatory_artifacts(
                            capture_path=str(cap_file),
                            analysis=norm_ana,
                            result=norm_res,
                            fs_hz=narrow_fs,
                            source_mode=f"DDC EMISSION #{em.emission_id}",
                        )

                        prov = {
                            "source": "Wideband DDC Channelizer",
                            "emission_id": em.emission_id,
                            "wideband_file": capture_path,
                            "center_freq_hz": em.center_freq_hz,
                            "bandwidth_hz": em.bandwidth_hz,
                            "narrowband_fs": narrow_fs,
                        }

                        # Store in session state and update active case artifacts
                        set_active_case_artifacts(
                            norm_res,
                            norm_ana,
                            norm_dec,
                            prov,
                            is_replay=False,
                            artifacts=obs_artifacts,
                        )
                        st.session_state["current_case_name"] = f"DDC Emission #{em.emission_id} ({em.center_freq_hz/1e3:.1f} kHz)"
                        st.session_state[f"analyzed_res_{em.emission_id}"] = norm_res
                        st.success(f"Emission #{em.emission_id} successfully channelized and analyzed!")
                        st.rerun()

            with c_act2:
                analyzed_res = st.session_state.get(f"analyzed_res_{em.emission_id}")
                if analyzed_res:
                    st.markdown(
                        f"""
                        <div style="padding:0.4rem 0.8rem; background:rgba(34,197,94,0.1); border-radius:6px; border:1px solid rgba(34,197,94,0.3);">
                            ✅ <b>Analyzed:</b> Modulation: <span class="sq-badge badge-pass">{analyzed_res.top_hypothesis.modulation}</span> &nbsp;|&nbsp;
                            Confidence: <b>{analyzed_res.final_confidence * 100:.1f}%</b> &nbsp;|&nbsp;
                            Ladder: <span class="sq-badge badge-ladder">{analyzed_res.ladder_level}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button(f"🔭 Inspect #{em.emission_id} in Observatory", key=f"obs_btn_{em.emission_id}"):
                        set_workspace("Signal Observatory")
                        st.rerun()
                else:
                    st.caption("Not yet channelized. Click 'Channelize & Analyze' to extract narrowband slice.")
