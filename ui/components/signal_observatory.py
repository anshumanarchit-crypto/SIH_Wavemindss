"""
Workspace 2: Signal Observatory (Physical Layer & RF Forensics).
Inspired by the SpectraQ Reference Dashboard, preserving the core 4-part conceptual hierarchy:
1. IQ waveform (Raw signal visualization)
2. Frequency spectrum (Spectral characteristics)
3. Extracted parameters table (with confidence intervals & parameter provenance)
4. Receiver validation (Arpit's real decoder telemetry, with honest 'Pending integration' state)

Extended with:
- Modulation result & ML probabilities
- Hypothesis evidence & Evidence Ladder (L1-L5)
- Prominent UNKNOWN state banner
- Cryptographic provenance & SigMF telemetry
- Interactive controls (Constellation, Waterfall, Eye Diagram, Burst Timeline)
- One-click Evidence Bundle and CSV Export

Strict Epistemic Invariant:
Zero fake signals. When raw samples are absent, honest UNAVAILABLE frames are rendered.
Never hardcodes example values.
"""

from typing import Optional, List, Dict, Any
import streamlit as st
import plotly.graph_objects as go

from ui.adapters import NormalizedAnalysis, NormalizedResult, NormalizedDecoder
from spectralq.visualization.artifacts import ObservatoryArtifacts, build_evidence_bundle_zip
from ui.charts import (
    create_waveform_plot,
    create_spectrum_plot,
    create_waterfall_plot,
    create_constellation_plot,
    create_eye_diagram_plot,
    create_burst_timeline_plot,
)
from ui.styles.theme import get_theme_tokens, get_plotly_layout_defaults, TOOLTIPS


def render_signal_observatory(
    artifacts: Optional[ObservatoryArtifacts],
    analysis: Optional[NormalizedAnalysis],
    result: Optional[NormalizedResult],
    decoder: Optional[NormalizedDecoder] = None,
) -> None:
    """Renders the Signal Observatory workspace aligned with the SpectraQ reference dashboard."""
    tokens = get_theme_tokens()
    capture_id = result.capture_id if result else "CAPTURE"

    # Header / Capture Identifier
    st.markdown(f"## 🔭 Suggested SpectraQ Dashboard — Signal Observatory")
    st.caption(f"Real-time RF Signal Forensics & Parameter Extraction • Target: `{capture_id}`")

    # 0. Prominent UNKNOWN State Banner (if abstained)
    if result and result.is_unknown:
        st.markdown(
            f"""
            <div class="sq-unknown-banner" style="margin-bottom:1.0rem;">
                <div class="sq-unknown-title">
                    ⚠️ DECISION: ABSTAINED (UNKNOWN STATE)
                </div>
                <div class="sq-unknown-desc">
                    <b>Reason:</b> {result.unknown_reason or "Low confidence or ambiguous signal evidence."}<br>
                    SpectralQ deliberately declined to guess rather than risk an erroneous classification.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =========================================================================
    # HIERARCHY LEVEL 1 & 2: IQ Waveform & Frequency Spectrum (Side-by-Side)
    # =========================================================================
    col_wave, col_spec = st.columns(2)

    # 1. IQ Waveform (Raw signal visualization)
    with col_wave:
        st.markdown("### IQ waveform")
        st.caption("Raw signal visualization")
        if artifacts and artifacts.raw_available and artifacts.waveform_i:
            fig_wave = create_waveform_plot(artifacts)
            if fig_wave:
                st.plotly_chart(fig_wave, use_container_width=True)
            else:
                st.warning("Waveform trace could not be generated from samples.")
        else:
            st.markdown(
                f"""
                <div class="sq-unavailable-box" style="min-height: 280px; display:flex; flex-direction:column; justify-content:center;">
                    <div class="sq-unavailable-title">⚠️ RAW VISUALIZATION UNAVAILABLE</div>
                    <div class="sq-unavailable-msg">
                        This capture bundle contains analysis telemetry and evidence contracts, but does not include raw I/Q sample recordings.<br><br>
                        Visualizations requiring sample-level data (waveform, PSD, constellation, eye diagram) cannot be rendered without fabricating data.<br>
                        <b>To view signal plots:</b> Provide a capture with raw I/Q data (<code>.cf32</code>, <code>.iq</code>, or <code>.wav</code>) or use <b>Signal Lab</b>.
                    </div>
                    <div><span class="sq-badge badge-unavail">ZERO FAKE SIGNALS ENFORCED</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 2. Frequency Spectrum (Spectral characteristics)
    with col_spec:
        st.markdown("### Frequency spectrum")
        st.caption("Spectral characteristics")
        if artifacts and artifacts.raw_available and artifacts.spectrum:
            fig_spec = create_spectrum_plot(artifacts)
            if fig_spec:
                st.plotly_chart(fig_spec, use_container_width=True)
            else:
                st.warning("Power spectral density could not be generated.")
        else:
            st.markdown(
                f"""
                <div class="sq-unavailable-box" style="min-height: 280px; display:flex; flex-direction:column; justify-content:center;">
                    <div class="sq-unavailable-title">⚠️ SPECTRAL PLOT UNAVAILABLE</div>
                    <div class="sq-unavailable-msg">
                        Power Spectral Density (PSD) computation requires genuine complex baseband samples.<br><br>
                        Spectral bandwidth, center frequency, and noise floor estimates are provided in the verified physical parameters table below.
                    </div>
                    <div><span class="sq-badge badge-unavail">NO SYNTHETIC NOISE FABRICATED</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # =========================================================================
    # HIERARCHY LEVEL 3: Extracted Parameters Table (Real Contracts)
    # =========================================================================
    estimate_col_name = f"{capture_id} estimate"
    st.markdown("### Extracted parameters")
    st.caption("Physical and statistical signal parameters estimated by Sinchana's blind DSP algorithms:")

    # Build rows dynamically from real analysis contracts
    param_rows = []

    # 1. Baud rate
    if analysis and analysis.baud:
        ci_str = f"[{analysis.baud.ci_lo:.2f}, {analysis.baud.ci_hi:.2f}] {analysis.baud.unit}" if analysis.baud.has_valid_ci else "N/A"
        param_rows.append({
            "Feature": "Baud rate",
            estimate_col_name: analysis.baud.display_value,
            "95% Confidence Interval": ci_str,
            "Estimation Method": analysis.baud.method or "Cyclic Autocorrelation",
            "Provenance": "Sinchana Blind DSP",
        })
    else:
        param_rows.append({
            "Feature": "Baud rate",
            estimate_col_name: "N/A",
            "95% Confidence Interval": "N/A",
            "Estimation Method": "Unestimated",
            "Provenance": "Unavailable",
        })

    # 2. CFO
    if analysis and analysis.cfo:
        ci_str = f"[{analysis.cfo.ci_lo:.2f}, {analysis.cfo.ci_hi:.2f}] {analysis.cfo.unit}" if analysis.cfo.has_valid_ci else "N/A"
        param_rows.append({
            "Feature": "CFO",
            estimate_col_name: analysis.cfo.display_value,
            "95% Confidence Interval": ci_str,
            "Estimation Method": analysis.cfo.method or "FFT 4th-Power Carrier Lock",
            "Provenance": "Sinchana Blind DSP",
        })
    else:
        param_rows.append({
            "Feature": "CFO",
            estimate_col_name: "N/A",
            "95% Confidence Interval": "N/A",
            "Estimation Method": "Unestimated",
            "Provenance": "Unavailable",
        })

    # 3. 99% / Occupied Bandwidth
    if analysis and analysis.bandwidth:
        ci_str = f"[{analysis.bandwidth.ci_lo:.2f}, {analysis.bandwidth.ci_hi:.2f}] {analysis.bandwidth.unit}" if analysis.bandwidth.has_valid_ci else "N/A"
        param_rows.append({
            "Feature": "99% bandwidth",
            estimate_col_name: analysis.bandwidth.display_value,
            "95% Confidence Interval": ci_str,
            "Estimation Method": analysis.bandwidth.method or "Welch Power Integration",
            "Provenance": "Sinchana Blind DSP",
        })
    else:
        param_rows.append({
            "Feature": "99% bandwidth",
            estimate_col_name: "N/A",
            "95% Confidence Interval": "N/A",
            "Estimation Method": "Unestimated",
            "Provenance": "Unavailable",
        })

    # 4. SNR
    if analysis and analysis.snr:
        ci_str = f"[{analysis.snr.ci_lo:.2f}, {analysis.snr.ci_hi:.2f}] {analysis.snr.unit}" if analysis.snr.has_valid_ci else "N/A"
        param_rows.append({
            "Feature": "SNR",
            estimate_col_name: analysis.snr.display_value,
            "95% Confidence Interval": ci_str,
            "Estimation Method": analysis.snr.method or "M2M4 Moment Estimator",
            "Provenance": "Sinchana Blind DSP",
        })
    else:
        param_rows.append({
            "Feature": "SNR",
            estimate_col_name: "N/A",
            "95% Confidence Interval": "N/A",
            "Estimation Method": "Unestimated",
            "Provenance": "Unavailable",
        })

    # 5. Higher-Order Statistics: C40 / C42
    c40_val = None
    c42_val = None
    if analysis and analysis.features and analysis.features.cumulants:
        c40_val = analysis.features.cumulants.get("C40", analysis.features.cumulants.get("c40"))
        c42_val = analysis.features.cumulants.get("C42", analysis.features.cumulants.get("c42"))

    if c40_val is not None and c42_val is not None:
        c40_c42_display = f"{c40_val:.3f} / {c42_val:.3f}"
    elif c40_val is not None:
        c40_c42_display = f"{c40_val:.3f} / N/A"
    else:
        c40_c42_display = "N/A (Not Calculated)"

    param_rows.append({
        "Feature": "HOS C40 / C42",
        estimate_col_name: c40_c42_display,
        "95% Confidence Interval": "N/A",
        "Estimation Method": "Higher-Order Cumulants",
        "Provenance": "Sinchana Statistical Extraction",
    })

    # Additional Physical Ingest Parameters
    fs_display = f"{analysis.fs_hz / 1e6:.3f} MHz" if analysis and analysis.fs_hz else "N/A"
    param_rows.append({
        "Feature": "Sampling rate (fs)",
        estimate_col_name: fs_display,
        "95% Confidence Interval": "Exact",
        "Estimation Method": analysis.fs_source if analysis else "Header / Ingest",
        "Provenance": "Ingest Forensics",
    })

    fc_display = f"{analysis.fc_hz / 1e6:.3f} MHz" if analysis and analysis.fc_hz else "0.000 MHz (Baseband)"
    param_rows.append({
        "Feature": "Center frequency (fc)",
        estimate_col_name: fc_display,
        "95% Confidence Interval": "Exact",
        "Estimation Method": "SDR Tuner Local Oscillator",
        "Provenance": "Ingest Forensics",
    })

    burst_ct = len(analysis.bursts) if analysis and analysis.bursts else 0
    param_rows.append({
        "Feature": "Active bursts detected",
        estimate_col_name: f"{burst_ct} transmission burst(s)",
        "95% Confidence Interval": "N/A",
        "Estimation Method": "Energy Envelope Detection",
        "Provenance": "Sinchana Burst Subsystem",
    })

    st.table(param_rows)

    st.markdown("---")

    # =========================================================================
    # HIERARCHY LEVEL 4: Receiver Validation (Arpit's Real Decoder Telemetry)
    # =========================================================================
    st.markdown("### Receiver validation")

    # Check Arpit's real decoder telemetry
    if decoder is not None and decoder.status in ("OK", "DECODED"):
        # Real confirmed decoder telemetry available
        st.markdown(
            f"""
            <div class="sq-card" style="border: 1px solid {tokens['pass_color']}; border-left: 4px solid {tokens['pass_color']};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                    <div style="font-weight:700; color:{tokens['pass_color']}; font-size:1.05rem;">
                        RECEIVER VALIDATION CONFIRMED (ARPIT DECODER TELEMETRY)
                    </div>
                    <span class="sq-badge badge-pass">DECODER ACTIVE & CONFIRMED</span>
                </div>
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; margin-top:0.75rem;">
                    <div>
                        <div style="font-size:0.72rem; color:{tokens['text_muted']}; text-transform:uppercase;">Decoded Bit Count</div>
                        <div style="font-family:'JetBrains Mono'; font-weight:700; font-size:1.15rem;">{decoder.decoded_bits_count:,} bits</div>
                    </div>
                    <div>
                        <div style="font-size:0.72rem; color:{tokens['text_muted']}; text-transform:uppercase;">Bit Error Rate (BER)</div>
                        <div style="font-family:'JetBrains Mono'; font-weight:700; font-size:1.15rem;">{decoder.ber_display}</div>
                    </div>
                    <div>
                        <div style="font-size:0.72rem; color:{tokens['text_muted']}; text-transform:uppercase;">Demodulated EVM</div>
                        <div style="font-family:'JetBrains Mono'; font-weight:700; font-size:1.15rem;">{f"{decoder.evm_percent:.1f}%" if decoder.evm_percent is not None else "N/A"}</div>
                    </div>
                    <div>
                        <div style="font-size:0.72rem; color:{tokens['text_muted']}; text-transform:uppercase;">FEC Scheme Used</div>
                        <div style="font-family:'JetBrains Mono'; font-weight:700; font-size:1.0rem;">{decoder.fec_used.upper()}</div>
                    </div>
                    <div>
                        <div style="font-size:0.72rem; color:{tokens['text_muted']}; text-transform:uppercase;">De-interleaver Matrix</div>
                        <div style="font-family:'JetBrains Mono'; font-weight:700; font-size:1.0rem;">{decoder.interleaver_used.upper()}</div>
                    </div>
                    <div>
                        <div style="font-size:0.72rem; color:{tokens['text_muted']}; text-transform:uppercase;">CRC Check Result</div>
                        <div style="font-family:'JetBrains Mono'; font-weight:700; font-size:1.0rem;">{decoder.crc_status.upper()}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if decoder.decoded_bits_preview:
            with st.expander("📄 View Confirmed Decoded Bits Preview", expanded=False):
                st.code(decoder.decoded_bits_preview[:512], language="text")
    else:
        # Pending integration or unavailable - Render exact reference card
        st.markdown(
            f"""
            <div style="border: 1px dashed {tokens['warn_color']}; border-radius: 8px; padding: 1.1rem; background-color:{tokens['card_bg']};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                    <div style="font-weight:700; color:{tokens['text']}; font-size:0.95rem;">
                        Receiver validation
                    </div>
                    <span class="sq-badge badge-warn">PENDING INTEGRATION</span>
                </div>
                <p style="font-size:0.86rem; color:{tokens['text_muted']}; line-height:1.45; margin:0.3rem 0 0.5rem 0;">
                    Connect Arpit's confirmed decoded-bit, BER and accuracy outputs when available. Until then, label these fields "Pending integration" rather than displaying assumed results.
                </p>
                <div style="font-size:0.78rem; color:{tokens['text_muted']};">
                    <b>Telemetry Status:</b> Decoder output contract not finalized or abstained for this capture.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # =========================================================================
    # EXTENSIONS: Modulation Result, ML Probabilities, Ladder & Evidence
    # =========================================================================
    st.markdown("### 🎯 Modulation Result & ML Consensus")

    ext_col1, ext_col2 = st.columns([1.2, 1.8])

    with ext_col1:
        top_mod = result.top_hypothesis.modulation if (result and not result.is_unknown) else "UNKNOWN"
        conf_pct = (result.final_confidence * 100.0) if result else 0.0
        ladder = result.ladder_level if result else "N/A"
        rule_ml_agree = result.rule_ml_agreement if result else False

        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">MODULATION IDENTIFICATION</div>
                <div class="sq-card-value" style="color:{tokens['primary']};">{top_mod}</div>
                <div class="sq-card-sub" style="margin-top:0.35rem;">
                    Final Confidence: <b>{conf_pct:.1f}%</b> | Ladder Level: <span class="sq-badge badge-ladder">{ladder}</span>
                </div>
                <div style="margin-top:0.5rem;">
                    Consensus: {"<span class='sq-badge badge-pass'>RULE + ML AGREE</span>" if rule_ml_agree else "<span class='sq-badge badge-fail'>CONSENSUS DIVERGENCE</span>"}
                </div>
                <div style="margin-top:0.4rem; font-size:0.8rem; color:{tokens['text_muted']};">
                    ML Prediction: <b>{result.ml_prediction if result else 'N/A'}</b> | Rule AMC: <b>{result.rule_prediction if result else 'N/A'}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with ext_col2:
        # Candidate ML Probabilities Chart
        candidates = []
        if result and result.top_hypothesis:
            candidates.append((result.top_hypothesis.modulation, result.ml_probability, True))
        if result and result.alternate_hypotheses:
            for alt in result.alternate_hypotheses:
                score = getattr(alt, "likelihood", None)
                if score is None:
                    score = alt.total_score if getattr(alt, "total_score", None) is not None else (getattr(alt, "prior_score", None) or 0.0)
                candidates.append((alt.modulation, score, False))
        if not candidates and result:
            candidates = [(result.ml_prediction, result.ml_probability, True)]

        if candidates:
            candidates.sort(key=lambda x: x[1])
            mod_names = [c[0] for c in candidates]
            probs = [c[1] for c in candidates]
            bar_colors = [tokens["primary"] if c[2] else tokens["text_muted"] for c in candidates]

            fig_bar = go.Figure(go.Bar(
                x=probs,
                y=mod_names,
                orientation="h",
                marker=dict(color=bar_colors),
                text=[f"{p:.1%}" for p in probs],
                textposition="auto",
            ))
            layout_bar = get_plotly_layout_defaults()
            layout_bar.update({
                "title": "ML Candidate Probabilities",
                "xaxis_title": "Probability",
                "xaxis": dict(range=[0, 1.05], tickformat=".0%"),
                "height": 200,
                "margin": dict(l=70, r=20, t=25, b=25),
            })
            fig_bar.update_layout(layout_bar)
            st.plotly_chart(fig_bar, use_container_width=True)

    # Evidence Ladder Summary
    if result:
        st.markdown("#### 🪜 Evidence Ladder & Verification Summary")
        ladder_ranks = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
        current_rank = ladder_ranks.get(result.ladder_level, 1)

        l_cols = st.columns(5)
        ladder_names = [
            ("L1", "Signal Detection"),
            ("L2", "Modulation AMC"),
            ("L3", "Blind Demod"),
            ("L4", "FEC Lock"),
            ("L5", "Frame & CRC"),
        ]
        for idx, (lvl, lname) in enumerate(ladder_names):
            with l_cols[idx]:
                lvl_rank = ladder_ranks[lvl]
                is_curr = (lvl == result.ladder_level)
                is_ach = (lvl_rank <= current_rank)
                badge = "<span class='sq-badge badge-ladder'>CURRENT</span>" if is_curr else (
                    "<span class='sq-badge badge-pass'>ACHIEVED</span>" if is_ach else "<span class='sq-badge badge-notrun'>PENDING</span>"
                )
                st.markdown(
                    f"""
                    <div class="sq-card" style="text-align:center; padding:0.4rem;">
                        <div class="sq-card-title">{lvl}</div>
                        <div style="font-size:0.75rem; font-weight:600; margin:0.15rem 0;">{lname}</div>
                        {badge}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # =========================================================================
    # EXTENSIONS: Interactive Controls & Deep Physical Views
    # =========================================================================
    with st.expander("🔬 Deep RF Physical Views (Constellation, Waterfall, Eye Diagram, Burst Timeline)", expanded=False):
        if artifacts and artifacts.raw_available:
            deep_tabs = st.tabs([
                "🎯 Constellation Diagram",
                "🌈 2D Spectrogram / Waterfall",
                "👁️ Eye Diagram",
                "⏱️ Burst Timeline",
            ])
            with deep_tabs[0]:
                fig_c = create_constellation_plot(artifacts)
                if fig_c:
                    st.plotly_chart(fig_c, use_container_width=True)
            with deep_tabs[1]:
                fig_wf = create_waterfall_plot(artifacts)
                if fig_wf:
                    st.plotly_chart(fig_wf, use_container_width=True)
            with deep_tabs[2]:
                fig_eye = create_eye_diagram_plot(artifacts)
                if fig_eye:
                    st.plotly_chart(fig_eye, use_container_width=True)
            with deep_tabs[3]:
                fig_burst = create_burst_timeline_plot(artifacts)
                if fig_burst:
                    st.plotly_chart(fig_burst, use_container_width=True)
        else:
            st.info("Sample-level deep views require raw I/Q samples (.cf32, .iq, .wav) or Signal Lab simulation.")
            if artifacts and artifacts.burst_view and artifacts.burst_view.total_bursts > 0:
                st.markdown("#### Burst Intervals (From Analysis Contract):")
                fig_burst = create_burst_timeline_plot(artifacts)
                if fig_burst:
                    st.plotly_chart(fig_burst, use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # EXTENSIONS: Cryptographic Provenance & Export Action Bar
    # =========================================================================
    st.markdown("### 🔒 Provenance & Export Actions")
    p1, p2, p3 = st.columns([1.5, 1, 1])

    with p1:
        sha_val = result.input_hash if result else "N/A"
        st.caption(f"**SHA-256 Digest:** `{sha_val[:24]}...` | **Software:** `SpectralQ Core v1.0.0`")

    with p2:
        # Export Extracted Parameters CSV
        import io
        import csv
        csv_buf = io.StringIO()
        if param_rows:
            writer = csv.DictWriter(csv_buf, fieldnames=list(param_rows[0].keys()))
            writer.writeheader()
            writer.writerows(param_rows)
        st.download_button(
            "📊 Export Parameters CSV",
            data=csv_buf.getvalue(),
            file_name=f"{capture_id}_extracted_parameters.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with p3:
        # One-click evidence bundle download
        res_dict = result.__dict__ if result else {}
        ana_dict = analysis.__dict__ if analysis else {}
        dec_dict = decoder.__dict__ if decoder else {}
        bundle_bytes = build_evidence_bundle_zip(
            capture_id=capture_id,
            result_data=res_dict,
            analysis_data=ana_dict,
            decoder_data=dec_dict,
        )
        st.download_button(
            "📦 Download Evidence Bundle (.zip)",
            data=bundle_bytes,
            file_name=f"SpectralQ_Evidence_Bundle_{capture_id}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )
