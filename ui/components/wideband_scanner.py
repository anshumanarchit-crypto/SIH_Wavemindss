"""
Workspace: Wideband Spectrum Scanner & DDC Channelizer (Tier-1b).
Performs wideband energy detection, spectral occupancy mapping, and per-emission
digital down-conversion (DDC) channelization for Tier-1a single-signal analysis.
Operates on genuine capture data: 100% dynamic, multi-source ingestion.
"""

from pathlib import Path
from typing import Optional, Dict, Any, Tuple
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


def _get_preset_catalog() -> Dict[str, Dict[str, Any]]:
    """Builds a comprehensive catalog of all available golden and benchmark captures."""
    catalog: Dict[str, Dict[str, Any]] = {
        "G8: Wideband 4 Emissions (1 MHz Multi-Emitter)": {
            "path": "data/official/sinchana/golden/G8_Wideband_4_emissions.cf32",
            "fs_hz": 1_000_000.0,
            "desc": "Golden Wideband capture with 4 concurrent emitters across 1 MHz spectrum.",
        },
        "G1: QPSK Uncoded (100 kHz, 131k samples)": {
            "path": "data/official/sinchana/golden/G1_QPSK_uncoded.cf32",
            "fs_hz": 100_000.0,
            "desc": "Pure QPSK clean baseband capture without channel coding.",
        },
        "G2: BPSK Rate 1/2 Viterbi Conv (100 kHz)": {
            "path": "data/official/sinchana/golden/G2_BPSK_conv_block.cf32",
            "fs_hz": 100_000.0,
            "desc": "BPSK with rate 1/2 constraint length 7 convolutional coding.",
        },
        "G3: 8-PSK Reed-Solomon Diagonal (100 kHz)": {
            "path": "data/official/sinchana/golden/G3_8PSK_RS_diagonal.cf32",
            "fs_hz": 100_000.0,
            "desc": "8-PSK with RS(255,223) outer forward error correction.",
        },
        "G4: 16-QAM LDPC Pseudorandom (100 kHz)": {
            "path": "data/official/sinchana/golden/G4_16QAM_LDPC_pseudorandom.cf32",
            "fs_hz": 100_000.0,
            "desc": "16-QAM high-density constellation with LDPC parity structure.",
        },
        "G5: 2-FSK RS Conv Dual-Tone (100 kHz)": {
            "path": "data/official/sinchana/golden/G5_2FSK_RS_Conv_interleaved.cf32",
            "fs_hz": 100_000.0,
            "desc": "2-FSK satellite pass with dual continuous-phase tone clusters.",
        },
        "G6: BPSK Conv Interleaved Deep Fading (100 kHz)": {
            "path": "data/official/sinchana/golden/G6_BPSK_conv_interleaved.cf32",
            "fs_hz": 100_000.0,
            "desc": "BPSK with convolutional interleaver under Rayleigh multipath fading.",
        },
        "G7: QPSK Low SNR Near Threshold (100 kHz)": {
            "path": "data/official/sinchana/golden/G7_QPSK_conv_near_threshold.cf32",
            "fs_hz": 100_000.0,
            "desc": "QPSK near demodulation sensitivity floor (boundary condition).",
        },
        "G9: Headerless Raw Swapped IQ (100 kHz)": {
            "path": "data/official/sinchana/golden/G9_Headerless_Raw_swapped.cf32",
            "fs_hz": 100_000.0,
            "desc": "Hardware quadrature reversal test (Q/I swapped layout).",
        },
        "G10: Pure AWGN Noise Floor Test (100 kHz)": {
            "path": "data/official/sinchana/golden/G10_Noise_Only_AWGN.cf32",
            "fs_hz": 100_000.0,
            "desc": "Pure Gaussian noise capture — exercises Rule 12 UNKNOWN detector.",
        },
        "Synthetic: 2-FSK Satellite Pass 18 dB": {
            "path": "data/synthetic/2fsk_snr18db.wav",
            "fs_hz": 100_000.0,
            "desc": "Synthesized 2-FSK continuous-phase tone cluster in WAV format.",
        },
        "Synthetic: 16-QAM High Density 22 dB": {
            "path": "data/synthetic/16qam_snr22db.wav",
            "fs_hz": 100_000.0,
            "desc": "16-QAM high-SNR baseband with root-raised cosine pulse shaping.",
        },
        "Synthetic: BPSK Clean Carrier 20 dB": {
            "path": "data/synthetic/bpsk_snr20db_clean.wav",
            "fs_hz": 100_000.0,
            "desc": "Clean BPSK frame with CCSDS 32-bit synchronization preamble.",
        },
        "Synthetic: QPSK CFO Tracking 15 dB": {
            "path": "data/synthetic/qpsk_snr15db_cfo.wav",
            "fs_hz": 100_000.0,
            "desc": "QPSK burst with carrier offset requiring Costas loop acquisition.",
        },
    }

    # Dynamically discover any other captures in data/scratch/ or data/synthetic/
    root = Path("data")
    if root.exists():
        for sub in [root / "scratch", root / "synthetic"]:
            if sub.exists():
                for f in sub.glob("*"):
                    if f.is_file() and f.suffix.lower() in (".cf32", ".iq", ".wav") and not f.name.startswith("emission_"):
                        key_name = f"Capture: {f.name}"
                        if key_name not in catalog:
                            catalog[key_name] = {
                                "path": str(f),
                                "fs_hz": 100_000.0,
                                "desc": f"Local capture file ({f.suffix.upper()}).",
                            }
    return catalog


def render_wideband_scanner() -> None:
    """Renders the Tier-1b Wideband Scanner workspace."""
    tokens = get_theme_tokens()

    st.markdown("## 📡 Wideband Spectrum Scanner (Tier-1b)")
    st.caption(
        "Wideband energy detection, spectral occupancy mapping, and Digital Down-Converter (DDC) "
        "channelization for isolated single-signal analysis."
    )

    # -------------------------------------------------------------------------
    # 1. Multi-Source Ingestion Header
    # -------------------------------------------------------------------------
    st.markdown("### 🎛️ Select Spectrum Capture Source")

    preset_catalog = _get_preset_catalog()

    # Check for actively ingested session capture
    active_path = st.session_state.get("active_capture_path")
    active_name = st.session_state.get("active_capture_name", st.session_state.get("current_case_name", "Active Signal"))
    has_active_signal = active_path is not None and Path(active_path).exists()

    source_mode_options = []
    if has_active_signal:
        source_mode_options.append("📥 Active Ingested Signal")
    source_mode_options.extend(["🎯 Golden & Benchmark Presets", "📁 Direct File Upload"])

    src_col1, src_col2 = st.columns([1.2, 2.8])

    with src_col1:
        selected_source_mode = st.radio(
            "Source Selection Mode:",
            options=source_mode_options,
            index=0,
            key="wb_source_mode_radio",
        )

    target_path: Optional[str] = None
    target_samples: Optional[np.ndarray] = None
    default_fs: float = 1_000_000.0
    source_label: str = ""

    with src_col2:
        if selected_source_mode == "📥 Active Ingested Signal":
            target_path = active_path
            source_label = f"Active: {active_name}"
            # Check if active is G8 or .wav
            if active_path.lower().endswith(".wav"):
                try:
                    from scipy.io import wavfile
                    wav_fs, _ = wavfile.read(active_path)
                    default_fs = float(wav_fs)
                except Exception:
                    default_fs = 100_000.0
            elif "wideband" in active_path.lower():
                default_fs = 1_000_000.0
            else:
                default_fs = 100_000.0

            st.markdown(
                f"""
                <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3);
                     border-left:4px solid #10b981; border-radius:8px; padding:0.75rem 1rem; margin-top:0.25rem;">
                    <div style="color:#10b981; font-weight:700; font-size:0.85rem;">✓ ACTIVE SESSION SIGNAL CONNECTED</div>
                    <div style="color:#f1f5f9; font-family:monospace; font-size:0.95rem; margin-top:2px;">{active_name}</div>
                    <div style="color:#94a3b8; font-size:0.75rem; margin-top:4px;">Path: <code>{active_path}</code></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        elif selected_source_mode == "🎯 Golden & Benchmark Presets":
            preset_names = list(preset_catalog.keys())
            selected_preset_name = st.selectbox(
                "Select Benchmark Capture:",
                options=preset_names,
                index=0,
                key="wb_preset_select",
                help="Select golden test captures covering wideband multi-emission and single-carrier benchmarks.",
            )
            preset_meta = preset_catalog[selected_preset_name]
            target_path = preset_meta["path"]
            default_fs = preset_meta["fs_hz"]
            source_label = selected_preset_name
            st.caption(f"ℹ️ {preset_meta['desc']}")

        else:
            # Direct File Upload Mode
            uploaded_file = st.file_uploader(
                "Upload Raw Spectrum Capture (.cf32, .iq, .wav, .npy):",
                type=["cf32", "iq", "wav", "npy"],
                key="wb_direct_uploader",
                help="Upload any wideband or narrowband SDR recording.",
            )
            if uploaded_file is not None:
                scratch_dir = Path("data") / "scratch"
                scratch_dir.mkdir(parents=True, exist_ok=True)
                direct_path = scratch_dir / f"wb_upload_{uploaded_file.name}"
                with open(direct_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                target_path = str(direct_path)
                source_label = f"Uploaded: {uploaded_file.name}"
                if uploaded_file.name.lower().endswith(".wav"):
                    try:
                        from scipy.io import wavfile
                        wav_fs, _ = wavfile.read(str(direct_path))
                        default_fs = float(wav_fs)
                    except Exception:
                        default_fs = 100_000.0
                else:
                    default_fs = 1_000_000.0
                st.success(f"✓ Loaded {uploaded_file.name} ({len(uploaded_file.getvalue())/1024:.1f} KB)")
            else:
                st.info("Please upload a .cf32, .iq, or .wav file to scan.")

    # -------------------------------------------------------------------------
    # 2. Scanning Parameters Bar
    # -------------------------------------------------------------------------
    st.markdown("---")
    c_p1, c_p2, c_p3, c_p4 = st.columns([1.5, 1.2, 1.2, 1.1])

    with c_p1:
        user_fs = st.number_input(
            "Sampling Rate (Hz):",
            min_value=1_000.0,
            max_value=100_000_000.0,
            value=float(default_fs),
            step=10_000.0,
            format="%.0f",
            key=f"wb_fs_input_{selected_source_mode}",
            help="SDR baseband hardware sampling rate.",
        )
    with c_p2:
        margin_db = st.slider("Detection Threshold (dB):", 2.0, 30.0, 10.0, 0.5, key="wb_margin_slider", help="Margin above estimated noise floor.")
    with c_p3:
        n_fft_bins = st.selectbox("FFT Resolution:", [512, 1024, 2048, 4096], index=1, key="wb_fft_select")
    with c_p4:
        suppress_dc = st.checkbox("Suppress DC Spike", value=True, key="wb_dc_check")

    if not target_path or not Path(target_path).exists():
        st.warning("Please select or upload a valid signal capture above to begin spectral analysis.")
        return

    # -------------------------------------------------------------------------
    # 3. Dynamic Execution & Scan Computation
    # -------------------------------------------------------------------------
    scan_state_key = f"wb_scan_{target_path}_{user_fs}_{margin_db}_{n_fft_bins}_{suppress_dc}"

    btn_col1, btn_col2 = st.columns([1.5, 3.5])
    with btn_col1:
        trigger_scan = st.button("🔍 Scan Spectrum & Map Occupancy", type="primary", use_container_width=True, key="wb_scan_exec_btn")

    if trigger_scan or scan_state_key not in st.session_state:
        with st.spinner(f"Computing Welch PSD and clustering spectral emissions for {Path(target_path).name}..."):
            try:
                sig = core.io.load_signal(target_path, sample_rate=user_fs)
                if sig.samples is None or len(sig.samples) == 0:
                    st.error(f"Could not load samples from '{target_path}'. Check file format.")
                    return

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
                st.session_state["wb_current_path"] = target_path
                st.session_state["wb_current_label"] = source_label
                st.session_state["wb_last_scan_key"] = scan_state_key
            except Exception as exc:
                st.error(f"Failed to scan wideband signal: {exc}")
                with st.expander("🛠️ Diagnostics"):
                    import traceback
                    st.code(traceback.format_exc())
                return

    scan_res: Optional[WidebandScanResult] = st.session_state.get(scan_state_key)
    if not scan_res:
        return

    curr_samples = st.session_state.get("wb_current_samples")

    # -------------------------------------------------------------------------
    # 4. Summary KPI Metrics Row (100% Dynamic from scan_res)
    # -------------------------------------------------------------------------
    st.markdown("---")

    span_str = f"{scan_res.fs_hz / 1e6:.2f} MHz" if scan_res.fs_hz >= 1e6 else f"{scan_res.fs_hz / 1e3:.1f} kHz"
    n_emissions = len(scan_res.emissions)
    em_color = "#10b981" if n_emissions > 0 else "#f59e0b"

    st.markdown(
        f"""
        <div style="display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 160px; background: rgba(10,14,26,0.6); backdrop-filter: blur(8px); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); border-left: 4px solid #38bdf8; padding: 1rem;">
                <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">📈 TOTAL SPAN</div>
                <div style="color: #f8fafc; font-size: 1.45rem; font-family: monospace; font-weight: 700;">{span_str}</div>
                <div style="color: #64748b; font-size: 0.65rem; margin-top: 2px;">Nyquist Bandwidth</div>
            </div>
            <div style="flex: 1; min-width: 160px; background: rgba(10,14,26,0.6); backdrop-filter: blur(8px); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); border-left: 4px solid #818cf8; padding: 1rem;">
                <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">🌊 NOISE FLOOR</div>
                <div style="color: #818cf8; font-size: 1.45rem; font-family: monospace; font-weight: 700;">{scan_res.noise_floor_db:.1f} <span style="font-size:0.85rem;">dBFS</span></div>
                <div style="color: #64748b; font-size: 0.65rem; margin-top: 2px;">Welch PSD Median</div>
            </div>
            <div style="flex: 1; min-width: 160px; background: rgba(10,14,26,0.6); backdrop-filter: blur(8px); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); border-left: 4px solid #ef4444; padding: 1rem;">
                <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">🚪 DETECTION GATE</div>
                <div style="color: #ef4444; font-size: 1.45rem; font-family: monospace; font-weight: 700;">{scan_res.detection_threshold_db:.1f} <span style="font-size:0.85rem;">dBFS</span></div>
                <div style="color: #64748b; font-size: 0.65rem; margin-top: 2px;">+{margin_db:.1f} dB above noise floor</div>
            </div>
            <div style="flex: 1; min-width: 160px; background: rgba(10,14,26,0.6); backdrop-filter: blur(8px); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); border-left: 4px solid {em_color}; padding: 1rem;">
                <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">🎯 DETECTED EMISSIONS</div>
                <div style="color: {em_color}; font-size: 1.45rem; font-family: monospace; font-weight: 700;">{n_emissions}</div>
                <div style="color: #64748b; font-size: 0.65rem; margin-top: 2px;">{'Active Emitters Clustered' if n_emissions > 0 else 'Noise Floor Only (Rule 12)'}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # 5. Wideband Spectrum Plotly Chart
    # -------------------------------------------------------------------------
    st.markdown(f"### 📊 Wideband Spectrum Occupancy Map — `{Path(target_path).name}`")

    fig = go.Figure()

    # Noise Floor shading below
    fig.add_trace(
        go.Scatter(
            x=scan_res.freqs / 1e3,
            y=np.full_like(scan_res.freqs, scan_res.noise_floor_db),
            mode="lines",
            line=dict(width=0),
            fill="tozeroy",
            fillcolor="rgba(16,185,129,0.04)",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # PSD Curve
    fig.add_trace(
        go.Scatter(
            x=scan_res.freqs / 1e3,
            y=scan_res.psd_db,
            mode="lines",
            name="Power Spectral Density",
            line=dict(color="#00f2fe", width=1.6),
            fill="tozeroy",
            fillcolor="rgba(0,242,254,0.08)",
            hovertemplate="Freq: %{x:.1f} kHz<br>Power: %{y:.1f} dBFS<extra></extra>",
        )
    )

    # Detection Threshold line
    fig.add_hline(
        y=scan_res.detection_threshold_db,
        line_dash="dash",
        line_color="#ef4444",
        line_width=1.5,
        annotation_text=f"Detection Gate ({scan_res.detection_threshold_db:.1f} dBFS)",
        annotation_position="bottom right",
        annotation_font_color="#ef4444",
        annotation_font_size=10,
    )

    # Shaded bounding boxes for detected emissions
    colors = ["#22c55e", "#06b6d4", "#eab308", "#a855f7", "#ec4899", "#f97316"]
    max_psd = float(np.max(scan_res.psd_db))

    for i, em in enumerate(scan_res.emissions):
        color = colors[i % len(colors)]
        fig.add_vrect(
            x0=em.freq_start_hz / 1e3,
            x1=em.freq_stop_hz / 1e3,
            fillcolor=color,
            opacity=0.14,
            line_width=0,
            annotation_text=f"E#{em.emission_id} ({em.bandwidth_hz/1e3:.1f}k)",
            annotation_position="top left",
            annotation_font=dict(color=color, size=10),
            annotation_bgcolor="rgba(0,0,0,0.75)",
            annotation_bordercolor=color,
            annotation_borderwidth=1,
        )

        fig.add_trace(
            go.Scatter(
                x=[em.freq_start_hz / 1e3, em.freq_stop_hz / 1e3],
                y=[max_psd * 0.98, max_psd * 0.98],
                mode="lines",
                line=dict(color=color, width=2.0),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        title=dict(
            text=f"Power Spectral Density & Cluster Bounding Boxes ({len(scan_res.emissions)} Emitter{'s' if len(scan_res.emissions)!=1 else ''} Resolved)",
            font=dict(color="#94a3b8", size=13),
        ),
        xaxis_title="Baseband Frequency (kHz)",
        yaxis_title="Power Spectral Density (dBFS/Hz)",
        xaxis=dict(
            title_font=dict(color="#64748b"),
            tickfont=dict(color="#64748b"),
            gridcolor="rgba(56,189,248,0.08)",
            zerolinecolor="rgba(56,189,248,0.25)",
        ),
        yaxis=dict(
            title_font=dict(color="#64748b"),
            tickfont=dict(color="#64748b"),
            gridcolor="rgba(56,189,248,0.08)",
            zerolinecolor="rgba(56,189,248,0.25)",
        ),
        paper_bgcolor="rgba(10,14,26,1)",
        plot_bgcolor="rgba(10,14,26,1)",
        legend=dict(
            bgcolor="rgba(10,14,26,0.8)",
            bordercolor="rgba(56,189,248,0.2)",
            borderwidth=1,
            font=dict(color="#94a3b8"),
        ),
        margin=dict(l=40, r=40, t=50, b=40),
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------------
    # 6. Detected Emissions Occupancy Table & Channelize Actions
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="margin-bottom: 1.2rem; display: flex; align-items: center; gap: 0.75rem;">
            <div style="width: 4px; height: 24px; background: linear-gradient(to bottom, #38bdf8, #818cf8); border-radius: 2px;"></div>
            <div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.01em;">Detected Emissions Occupancy Table</div>
                <div style="font-size: 0.85rem; color: #94a3b8;">Channelize and blindly analyze isolated signals from the spectrum capture</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not scan_res.emissions:
        st.info(
            "ℹ️ No signals detected above the current detection threshold. "
            "If analyzing a low-power emission, try reducing the Detection Threshold slider above."
        )
        return

    row_colors = ["#22c55e", "#06b6d4", "#eab308", "#a855f7", "#ec4899", "#f97316"]

    for i, em in enumerate(scan_res.emissions):
        row_color = row_colors[i % len(row_colors)]
        with st.container():
            st.markdown(
                f"""
                <div style="margin-bottom: 0.8rem; padding: 1rem; background: rgba(10,14,26,0.6); backdrop-filter: blur(8px); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); border-left: 3px solid {row_color}; display: flex; flex-direction: column; gap: 0.75rem;">
                    <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;">
                        <div style="background: {row_color}20; color: {row_color}; border: 1px solid {row_color}40; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            Emission #{em.emission_id}
                        </div>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.85rem;">
                                <span style="color: #94a3b8; margin-right: 0.25rem;">Center:</span>
                                <span style="color: #f8fafc; font-weight: 600; font-family: monospace;">{em.center_freq_hz / 1e3:+.1f} kHz</span>
                            </div>
                            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.85rem;">
                                <span style="color: #94a3b8; margin-right: 0.25rem;">Span:</span>
                                <span style="color: #f8fafc; font-weight: 600; font-family: monospace;">{em.bandwidth_hz / 1e3:.1f} kHz</span>
                            </div>
                            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.85rem;">
                                <span style="color: #94a3b8; margin-right: 0.25rem;">Peak Power:</span>
                                <span style="color: #f8fafc; font-weight: 600; font-family: monospace;">{em.peak_power_db:.1f} dBFS</span>
                            </div>
                            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.85rem;">
                                <span style="color: #94a3b8; margin-right: 0.25rem;">SNR:</span>
                                <span style="color: #10b981; font-weight: 700; font-family: monospace;">{em.snr_db:.1f} dB</span>
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Channelize & Analyze action
            c_act1, c_act2 = st.columns([1.2, 2.8])
            with c_act1:
                btn_key = f"ddc_btn_{Path(target_path).stem}_{em.emission_id}"
                if st.button(
                    f"⚡ Channelize & Analyze #{em.emission_id}",
                    key=btn_key,
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner(f"DDC frequency translation & FIR decimation for Emission #{em.emission_id}..."):
                        all_samples = curr_samples
                        if all_samples is None:
                            sig_load = core.io.load_signal(target_path, sample_rate=user_fs)
                            all_samples = sig_load.samples

                        # Run DDC channelization
                        narrow_iq, narrow_fs = channelize_emission(
                            iq_samples=all_samples,
                            fs_wide_hz=user_fs,
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

                        # Execute SpectralQ pipeline on genuine in-memory samples
                        from spectralq.features.iq_extractor import iq_to_analysis_contract
                        from spectralq.decoder.service import run_arpit_decoder
                        from spectralq.contracts.schemas import DecoderOutputContract, DecoderStatus, CrcStatus
                        from core.contracts import SignalData as _SignalData

                        _cap_id = f"DDC_EM{em.emission_id}_{int(em.center_freq_hz/1e3)}kHz"

                        # Stage A: IQ feature extraction on narrow-band samples
                        _analysis_contract = iq_to_analysis_contract(
                            narrow_iq,
                            fs_hz=narrow_fs,
                            capture_id=_cap_id,
                        )

                        # Stage B: Real DSP decoder on in-memory samples
                        _sig_obj = _SignalData(
                            samples=narrow_iq,
                            sample_rate=narrow_fs,
                            is_complex=True,
                        )
                        _dec_raw = run_arpit_decoder(
                            capture_input=_sig_obj,
                            capture_id=_cap_id,
                            analysis=_analysis_contract,
                            candidate_modulation=None,
                        )

                        # Build genuine decoder contract
                        _dec_contract = DecoderOutputContract(
                            schema_version="1.0.0",
                            capture_id=_cap_id,
                            status=_dec_raw.status,
                            interleaver_used=_dec_raw.interleaver_used or "none",
                            fec_used=_dec_raw.fec_used or "none",
                            decoded_bits=_dec_raw.decoded_bits or 0,
                            crc_status=_dec_raw.crc_status,
                            reencode_ber=_dec_raw.reencode_ber,
                            sync_word=_dec_raw.sync_word,
                            evm_percent=_dec_raw.evm_percent,
                            failure_reason=_dec_raw.failure_reason,
                        )

                        # Stage C: Full pipeline with LIVE overrides
                        pipe_out = run(
                            capture_path=str(cap_file),
                            mode="live",
                            analysis_override=_analysis_contract,
                            decoder_override=_dec_contract,
                        )

                        from spectralq.visualization.artifacts import prepare_observatory_artifacts
                        norm_res = adapt_result(pipe_out.result) if pipe_out.result else None
                        norm_ana = adapt_analysis(pipe_out.analysis) if pipe_out.analysis else None
                        norm_dec = adapt_decoder(pipe_out.decoder) if pipe_out.decoder else None

                        obs_artifacts = prepare_observatory_artifacts(
                            iq_samples=narrow_iq,
                            analysis=norm_ana,
                            result=norm_res,
                            fs_hz=narrow_fs,
                            source_mode=f"DDC EMISSION #{em.emission_id}",
                        )

                        prov = {
                            "source": "Wideband DDC Channelizer",
                            "emission_id": em.emission_id,
                            "wideband_file": target_path,
                            "center_freq_hz": em.center_freq_hz,
                            "bandwidth_hz": em.bandwidth_hz,
                            "narrowband_fs": narrow_fs,
                            "capture_id": _cap_id,
                            "stage_status": pipe_out.stage_status,
                            "input_hash": pipe_out.result.provenance.input_hash if pipe_out.result and pipe_out.result.provenance else "N/A",
                            "is_replay": False,
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
                        st.session_state["active_capture_path"] = str(cap_file)
                        st.session_state["active_capture_name"] = f"Emission #{em.emission_id}"
                        st.success(f"Emission #{em.emission_id} successfully channelized and analyzed!")
                        st.rerun()

            with c_act2:
                analyzed_res = st.session_state.get(f"analyzed_res_{em.emission_id}")
                if analyzed_res:
                    st.markdown(
                        f"""
                        <div style="padding:0.4rem 0.8rem; background:rgba(34,197,94,0.1); border-radius:6px; border:1px solid rgba(34,197,94,0.3); display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.5rem;">
                            <div>
                                ✅ <b>Analyzed:</b> <span class="sq-badge badge-pass">{analyzed_res.top_hypothesis.modulation}</span> &nbsp;|&nbsp;
                                Confidence: <b>{analyzed_res.final_confidence * 100:.1f}%</b> &nbsp;|&nbsp;
                                Ladder: <span class="sq-badge badge-ladder">{analyzed_res.ladder_level}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button(f"🔭 Inspect Emission #{em.emission_id} in Signal Observatory", key=f"obs_btn_{em.emission_id}", type="primary"):
                        set_workspace("Signal Observatory")
                        st.rerun()
                else:
                    st.caption("Not yet channelized. Click 'Channelize & Analyze' to extract narrowband DDC slice.")
