"""
Workspace 7: Signal Lab / Simulation (Interactive Signal Generator & Validation).
Generates in-memory synthetic signals with configurable impairments and evaluates
SpectralQ's blind estimation pipeline against known ground truth.
Strict Epistemic Invariant: Ground truth is NEVER passed to the analysis pipeline or classifier.
"""

from typing import Optional, Dict, Any
import numpy as np
import streamlit as st

from spectralq.visualization.simulation import generate_simulated_signal, SimulationTruth
from spectralq.visualization.artifacts import prepare_observatory_artifacts, ObservatoryArtifacts
from ui.charts import (
    create_waveform_plot,
    create_spectrum_plot,
    create_waterfall_plot,
    create_constellation_plot,
)
from ui.styles.theme import get_theme_tokens
from ui.components.icons import get_icon_svg


def render_signal_lab() -> None:
    """Renders the defense-grade Signal Lab & Simulation workbench."""
    tokens = get_theme_tokens()

    # Workspace Header
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem; border-bottom:1px solid {tokens['card_border']}; padding-bottom:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.6rem;">
                {get_icon_svg("signal_lab", size=20, color=tokens['primary'])}
                <span style="font-size:1.15rem; font-weight:800; letter-spacing:0.04em; color:{tokens['text']};">
                    RF EXPERIMENT &amp; SIMULATION TESTBENCH
                </span>
            </div>
            <div>
                <span class="sq-badge badge-warn">
                    {get_icon_svg('zap', size=11)} IN-MEMORY SYNTHESIS
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Parameter Generator Form
    with st.expander("🛠️ Signal Synthesis & Impairment Parameters", expanded=True):
        scol1, scol2, scol3 = st.columns(3)
        with scol1:
            mod_choice = st.selectbox(
                "Modulation Scheme:",
                ["QPSK", "BPSK", "8-PSK", "16-QAM", "2-FSK", "4-FSK"],
                index=0,
                key="sim_mod_choice",
            )
            num_syms = st.select_slider(
                "Symbol Count:",
                options=[512, 1024, 2048, 4096],
                value=2048,
                key="sim_num_syms",
            )
        with scol2:
            snr_input = st.slider("Signal-to-Noise Ratio (dB):", -5.0, 30.0, 15.0, 1.0, key="sim_snr_slider")
            cfo_input = st.slider("Carrier Frequency Offset (Hz):", -25000.0, 25000.0, 2500.0, 500.0, key="sim_cfo_slider")
        with scol3:
            sps_input = st.selectbox("Samples Per Symbol (SPS):", [4, 8, 16], index=1, key="sim_sps_choice")
            fading_choice = st.selectbox("Propagation Channel Model:", ["AWGN Only", "Rayleigh Flat", "Rician Flat"], index=0, key="sim_fading_choice")
            phase_noise = st.slider("Phase Noise (deg RMS):", 0.0, 15.0, 1.0, 0.5, key="sim_pn_slider")

        fading_type = "none"
        if "Rayleigh" in fading_choice:
            fading_type = "rayleigh"
        elif "Rician" in fading_choice:
            fading_type = "rician"

        if st.button("⚡ Synthesize Signal in Memory", type="primary", use_container_width=True):
            with st.spinner("Generating baseband signal with RF impairments..."):
                samples, truth = generate_simulated_signal(
                    modulation=mod_choice,
                    num_symbols=num_syms,
                    sps=sps_input,
                    fs_hz=1.0e6,
                    snr_db=snr_input,
                    cfo_hz=cfo_input,
                    phase_noise_deg=phase_noise,
                    fading=fading_type,
                )
                obs_artifacts = prepare_observatory_artifacts(
                    iq_samples=samples,
                    fs_hz=truth.fs_hz,
                    source_mode="SIMULATED",
                    sps=truth.sps,
                )
                st.session_state["simulated_samples"] = samples
                st.session_state["simulated_truth"] = truth
                st.session_state["simulated_artifacts"] = obs_artifacts
                st.session_state["simulated_pipeline_out"] = None
                st.success(f"Synthesized {len(samples):,} complex samples ({truth.modulation})!")

    # Check if a signal is currently generated in memory
    samples = st.session_state.get("simulated_samples")
    truth: Optional[SimulationTruth] = st.session_state.get("simulated_truth")
    artifacts: Optional[ObservatoryArtifacts] = st.session_state.get("simulated_artifacts")

    if samples is None or truth is None or artifacts is None:
        st.info("No active synthetic signal in memory. Adjust controls above and click 'Synthesize Signal'.")
        return

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Visualizations of the Synthesized Signal
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                {get_icon_svg("waveform", size=16, color=tokens['primary'])}
                <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                    Synthesized Baseband Diagnostics
                </span>
            </div>
            <span class="sq-badge badge-warn">SIMULATION GROUND TRUTH · KNOWN PARAMETERS</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        fig_w = create_waveform_plot(artifacts)
        if fig_w:
            st.plotly_chart(fig_w, use_container_width=True)
    with col2:
        fig_s = create_spectrum_plot(artifacts)
        if fig_s:
            st.plotly_chart(fig_s, use_container_width=True)

    c_col1, c_col2 = st.columns([1, 1])
    with c_col1:
        fig_c = create_constellation_plot(artifacts)
        if fig_c:
            st.plotly_chart(fig_c, use_container_width=True)
    with c_col2:
        fig_wf = create_waterfall_plot(artifacts)
        if fig_wf:
            st.plotly_chart(fig_wf, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Blind Pipeline Execution & Ground-Truth Verification
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.6rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                {get_icon_svg("target", size=16, color=tokens['primary'])}
                <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                    Blind Validation Against Ground Truth
                </span>
            </div>
            <span style="font-size:0.7rem; color:{tokens['text_muted']};">Epistemic Isolation Enforced</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🚀 Run Blind Pipeline on Simulated Signal", type="primary", use_container_width=True):
        with st.spinner("Running SpectralQ blind extraction & classification pipeline..."):
            from spectralq.pipeline.runner import run
            from spectralq.features.iq_extractor import iq_to_analysis_contract
            from ui.adapters import adapt_result, adapt_analysis, adapt_decoder

            sim_analysis = iq_to_analysis_contract(
                iq_samples=samples,
                fs_hz=truth.fs_hz,
                capture_id="SIMULATED_TESTBENCH",
            )
            pipe_out = run(capture_path="SIMULATED_TESTBENCH", mode="live", analysis_override=sim_analysis)
            st.session_state["simulated_pipeline_out"] = pipe_out

    pipe_out = st.session_state.get("simulated_pipeline_out")
    if pipe_out and pipe_out.result and pipe_out.analysis:
        norm_res = adapt_result(pipe_out.result)
        norm_ana = adapt_analysis(pipe_out.analysis)

        v_col1, v_col2 = st.columns(2)
        with v_col1:
            st.markdown(
                f"""
                <div class="sq-card">
                    <div class="sq-card-title">SIMULATION GROUND TRUTH (KNOWN)</div>
                    <div style="font-size:0.85rem; line-height:1.7;">
                        <b>True Modulation:</b> <span class="sq-badge badge-pass">{truth.modulation}</span><br>
                        <b>True SNR:</b> <code>{truth.snr_db:.1f} dB</code><br>
                        <b>True CFO:</b> <code>{truth.cfo_hz:+.1f} Hz</code><br>
                        <b>True Baud:</b> <code>{truth.baud_rate:,.0f} Baud</code><br>
                        <b>Channel Model:</b> <code>{truth.fading.upper()}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with v_col2:
            est_mod = norm_res.top_hypothesis.modulation if not norm_res.is_unknown else "UNKNOWN"
            est_snr = norm_ana.snr.display_value if norm_ana.snr else "N/A"
            est_cfo = norm_ana.cfo.display_value if norm_ana.cfo else "N/A"
            est_baud = norm_ana.baud_rate.display_value if norm_ana.baud_rate else "N/A"
            mod_match = est_mod == truth.modulation
            match_badge = "<span class='sq-badge badge-pass'>✓ EXACT MATCH</span>" if mod_match else "<span class='sq-badge badge-fail'>✗ MISMATCH</span>"

            st.markdown(
                f"""
                <div class="sq-card">
                    <div class="sq-card-title">BLIND PIPELINE ESTIMATE (DERIVED)</div>
                    <div style="font-size:0.85rem; line-height:1.7;">
                        <b>Predicted Class:</b> <code>{est_mod}</code> {match_badge}<br>
                        <b>Estimated SNR:</b> <code>{est_snr}</code><br>
                        <b>Estimated CFO:</b> <code>{est_cfo}</code><br>
                        <b>Estimated Baud:</b> <code>{est_baud}</code><br>
                        <b>Decision Ladder:</b> <span class="sq-badge badge-ladder">{norm_res.ladder_level}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
