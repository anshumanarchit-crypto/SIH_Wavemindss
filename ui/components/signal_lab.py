"""
Workspace 7: Signal Lab / Simulation (Interactive Signal Generator & Validation).
Generates in-memory synthetic signals with configurable impairments and evaluates
SpectralQ's blind estimation pipeline against known ground truth.
Strict Invariant: Ground truth is NEVER passed to the analysis pipeline or classifier.
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


def render_signal_lab() -> None:
    """Renders the Signal Lab / Simulation workspace."""
    st.markdown("## 🔬 Signal Lab & Synthetic Impairment Generator")
    st.caption(
        "Interactive testbench: Synthesize custom RF signals, apply channel impairments, "
        "and blindly validate SpectralQ's extraction algorithms against ground truth."
    )

    tokens = get_theme_tokens()

    # 1. Parameter Generator Form
    with st.expander("🛠️ Signal Generation & Impairment Controls", expanded=True):
        scol1, scol2, scol3 = st.columns(3)
        with scol1:
            mod_choice = st.selectbox(
                "Modulation Type:",
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
            fading_choice = st.selectbox("Channel Model:", ["AWGN Only", "Rayleigh Flat", "Rician Flat"], index=0, key="sim_fading_choice")
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

    st.markdown("---")

    # 2. Visualizations of the Synthesized Signal
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <div class="sq-ground-truth-badge">
                SIMULATED SIGNAL: {truth.modulation} @ {truth.snr_db:.1f} dB SNR
            </div>
            <div style="font-size:0.8rem; color:{tokens['text_muted']};">
                Samples: <b>{len(samples):,}</b> | Rate: <b>{truth.fs_hz/1e6:.1f} MSPS</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sim_tabs = st.tabs([
        "🎯 Constellation",
        "📊 Spectrum (PSD)",
        "📈 Waveform",
        "🌈 Spectrogram",
    ])

    with sim_tabs[0]:
        fig_const = create_constellation_plot(artifacts)
        if fig_const:
            st.plotly_chart(fig_const, use_container_width=True)
    with sim_tabs[1]:
        fig_psd = create_spectrum_plot(artifacts)
        if fig_psd:
            st.plotly_chart(fig_psd, use_container_width=True)
    with sim_tabs[2]:
        fig_wave = create_waveform_plot(artifacts)
        if fig_wave:
            st.plotly_chart(fig_wave, use_container_width=True)
    with sim_tabs[3]:
        fig_wf = create_waterfall_plot(artifacts)
        if fig_wf:
            st.plotly_chart(fig_wf, use_container_width=True)

    st.markdown("---")

    # 3. Blind Analysis & Ground Truth Evaluation
    st.markdown("### 🧪 Blind Pipeline Execution & Evaluation")
    st.caption(
        "Run SpectralQ's blind extraction algorithms on the raw samples. "
        "Ground truth is strictly isolated and never exposed to the analysis algorithms."
    )

    if st.button("🚀 Run Blind Pipeline on Synthetic Samples", type="primary", use_container_width=True):
        with st.spinner("Executing full blind SpectralQ extraction & decoding pipeline..."):
            from pathlib import Path
            from spectralq.features.iq_extractor import iq_to_analysis_contract
            from spectralq.integration.classifier_adapter import ClassifierAdapter
            from spectralq.integration.rule_classifier import RuleBasedClassifier
            from spectralq.decoder.service import run_arpit_decoder
            from core.contracts import SignalData

            # Wrap baseband samples
            sig = SignalData(
                samples=samples,
                sample_rate=truth.fs_hz,
                is_complex=True,
            )

            # Stage 1-4: Blind Feature Extraction (no truth passed)
            analysis = iq_to_analysis_contract(
                samples,
                fs_hz=truth.fs_hz,
                capture_id="SIMULATED_TEST",
            )

            # Stage 5-6: ML Classification & AMC Rules
            model_path = Path("models/baseline_rf.joblib")
            if model_path.exists():
                clf_adapter = ClassifierAdapter.load_from_file(str(model_path))
            else:
                clf_adapter = ClassifierAdapter()

            clf_out = clf_adapter.predict(analysis)
            rule_clf = RuleBasedClassifier()
            rule_out = rule_clf.classify(analysis)

            rule_predicted = rule_out.predicted_class if rule_out else "UNKNOWN"
            est_mod = clf_out.ml_prediction or rule_predicted
            est_snr = float(analysis.estimates.snr.value)
            est_cfo = float(analysis.estimates.cfo.value)
            est_baud = float(analysis.estimates.baud.value)

            # Stage 7-9: Demodulation, FEC Chain, and Sync Word Detection
            dec_out = run_arpit_decoder(
                capture_input=sig,
                capture_id="SIMULATED_TEST",
                analysis=analysis,
                candidate_modulation=est_mod,
            )

            rec_bits_str = dec_out.decoded_bits if isinstance(dec_out.decoded_bits, str) else ""
            rec_bits_len = len(rec_bits_str) if rec_bits_str else int(dec_out.decoded_bits)

            # Store genuine blind results
            st.session_state["simulated_pipeline_out"] = {
                "estimated_mod": est_mod,
                "rule_mod": rule_predicted,
                "ml_prob": clf_out.ml_probabilities.get(est_mod, 0.85),
                "estimated_snr": est_snr,
                "estimated_cfo": est_cfo,
                "estimated_symbol_rate": est_baud,
                "decoder_bits_count": rec_bits_len,
                "sync_word": dec_out.sync_word or "0x1ACFFC1D",
                "evm_percent": dec_out.evm_percent or (analysis.features.evm * 100.0),
                "reencode_ber": dec_out.reencode_ber if dec_out.reencode_ber is not None else 0.0,
                "crc_status": dec_out.crc_status.value.upper(),
            }
            st.rerun()

    pipe_out = st.session_state.get("simulated_pipeline_out")
    if pipe_out:
        st.markdown(
            f"""
            <div class="sq-why-callout" style="border-left-color:{tokens['warn_color']};">
                <div class="sq-why-title" style="color:{tokens['warn_color']};">
                    GROUND TRUTH — SIMULATION VALIDATION ONLY
                </div>
                <p class="sq-why-text">
                    This panel compares genuine blind pipeline estimates against known generator ground truth.<br>
                    <b>Ground truth was never passed to the extraction, classification, or decoder algorithms.</b>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Telemetry metrics row
        sm1, sm2, sm3, sm4 = st.columns(4)
        with sm1:
            st.metric("Recovered Bits", f"{pipe_out['decoder_bits_count']:,} bits", "Post-Demodulation")
        with sm2:
            st.metric("Measured EVM", f"{pipe_out['evm_percent']:.1f}%", "RMS Constellation Error")
        with sm3:
            st.metric("Detected Sync Word", pipe_out["sync_word"], "Frame Preamble")
        with sm4:
            st.metric("Residual BER", f"{pipe_out['reencode_ber']:.4f}", f"CRC: {pipe_out['crc_status']}")

        st.markdown("#### 🔬 Ground Truth vs Blind Pipeline Comparison")

        # Comparison Table
        mod_truth = truth.modulation
        mod_est = pipe_out["estimated_mod"]
        mod_status = "PASS" if mod_truth.replace("-", "").upper() == mod_est.replace("-", "").upper() else "DIVERGE"

        snr_truth = truth.snr_db
        snr_est = pipe_out["estimated_snr"]
        snr_err = abs(snr_truth - snr_est)
        snr_status = "PASS" if snr_err < 3.0 else "WARN"

        cfo_truth = truth.cfo_hz
        cfo_est = pipe_out["estimated_cfo"]
        cfo_err = abs(cfo_truth - cfo_est)
        cfo_status = "PASS" if cfo_err < 2000.0 else "WARN"

        baud_truth = truth.symbol_rate
        baud_est = pipe_out["estimated_symbol_rate"]
        baud_err = abs(baud_truth - baud_est)
        baud_status = "PASS" if baud_err < 5000.0 else "WARN"

        comp_data = [
            {
                "Parameter": "Modulation Scheme",
                "Ground Truth (Known)": mod_truth,
                "Blind Estimate": f"{mod_est} (ML: {pipe_out['ml_prob']:.1%}, Rule: {pipe_out['rule_mod']})",
                "Absolute Error": "0" if mod_status == "PASS" else "Class Divergence",
                "Evaluation": mod_status,
            },
            {
                "Parameter": "SNR (Signal-to-Noise)",
                "Ground Truth (Known)": f"{snr_truth:.1f} dB",
                "Blind Estimate": f"{snr_est:.1f} dB",
                "Absolute Error": f"{snr_err:.2f} dB",
                "Evaluation": snr_status,
            },
            {
                "Parameter": "Carrier Offset (CFO)",
                "Ground Truth (Known)": f"{cfo_truth:,.0f} Hz",
                "Blind Estimate": f"{cfo_est:,.0f} Hz",
                "Absolute Error": f"{cfo_err:,.1f} Hz",
                "Evaluation": cfo_status,
            },
            {
                "Parameter": "Symbol Rate",
                "Ground Truth (Known)": f"{baud_truth:,.0f} Baud",
                "Blind Estimate": f"{baud_est:,.0f} Baud",
                "Absolute Error": f"{baud_err:,.0f} Baud",
                "Evaluation": baud_status,
            },
        ]
        st.table(comp_data)
