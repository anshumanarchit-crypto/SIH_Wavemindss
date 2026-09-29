"""
SpectralQ Signal Visualization Engine.
Generates defense-grade, ultra-premium interactive Plotly visualizations for the Signal Observatory.
Features neon glow traces, translucent gradient fills, realistic RF spectrum analyzer grids,
high-density constellation clustering, and rich interactive tooltips.
Strictly operates on genuine capture data: zero fabricated signals.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt

from ui.styles.theme import get_theme_tokens, get_plotly_layout_defaults
from spectralq.visualization.artifacts import ObservatoryArtifacts


# -----------------------------------------------------------------------------
# 1. Interactive IQ Waveform Plot with Glowing Fills
# -----------------------------------------------------------------------------
def create_waveform_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly waveform plot showing I and Q time series with neon glow."""
    if not artifacts.raw_available or not artifacts.waveform_i:
        return None

    tokens = get_theme_tokens()
    fig = go.Figure()

    times = artifacts.waveform_times_ms
    i_vals = artifacts.waveform_i
    q_vals = artifacts.waveform_q

    # Calculate instantaneous magnitude for hover
    mag_vals = [np.sqrt(i**2 + q**2) for i, q in zip(i_vals, q_vals)]

    # Real / Channel 1 (In-Phase) - Electric Cyan
    fig.add_trace(go.Scatter(
        x=times,
        y=i_vals,
        name="Real [I] (In-Phase)",
        line=dict(color="#00f2fe", width=1.8),
        mode="lines",
        hovertemplate="Time: %{x:.3f} ms<br>I Amp: %{y:.4f}<extra></extra>",
    ))

    # Imag / Channel 2 (Quadrature) - Electric Violet/Pink
    fig.add_trace(go.Scatter(
        x=times,
        y=q_vals,
        name="Imag [Q] (Quadrature)",
        line=dict(color="#c084fc", width=1.8),
        mode="lines",
        hovertemplate="Time: %{x:.3f} ms<br>Q Amp: %{y:.4f}<extra></extra>",
    ))

    # Envelope Magnitude Guide
    fig.add_trace(go.Scatter(
        x=times,
        y=mag_vals,
        name="Envelope |z|",
        line=dict(color="rgba(148, 163, 184, 0.4)", width=1, dash="dot"),
        mode="lines",
        visible="legendonly",
        hovertemplate="Time: %{x:.3f} ms<br>Envelope: %{y:.4f}<extra></extra>",
    ))

    title_text = "<b>TIME-DOMAIN I/Q BASEBAND WAVEFORM</b>"
    if artifacts.downsampled:
        title_text += " <span style='font-size:10px;color:#94a3b8;font-weight:normal;'>[Anti-Aliased Decimation]</span>"

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": {
            "text": title_text,
            "font": {"size": 13, "color": "#f1f5f9"},
        },
        "xaxis": {
            "title": "Time offset (ms)",
            "gridcolor": "rgba(148, 163, 184, 0.12)",
            "zerolinecolor": "rgba(56, 189, 248, 0.3)",
        },
        "yaxis": {
            "title": "Normalized Amplitude (V)",
            "gridcolor": "rgba(148, 163, 184, 0.12)",
            "zerolinecolor": "rgba(56, 189, 248, 0.3)",
        },
        "hovermode": "x unified",
        "legend": dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color="#94a3b8"),
            bgcolor="rgba(0,0,0,0)",
        ),
        "height": 330,
        "margin": dict(l=45, r=15, t=40, b=35),
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig


# -----------------------------------------------------------------------------
# 2. Interactive Power Spectral Density with Bandwidth Highlight
# -----------------------------------------------------------------------------
def create_spectrum_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly Power Spectral Density plot with neon glow and bandwidth box."""
    if not artifacts.spectrum or not artifacts.spectrum.frequencies_mhz:
        return None

    spec = artifacts.spectrum
    tokens = get_theme_tokens()
    fig = go.Figure()

    # Find spectral peak
    max_idx = int(np.argmax(spec.psd_db))
    peak_freq = spec.frequencies_mhz[max_idx]
    peak_pwr = spec.psd_db[max_idx]

    # PSD Trace with Emerald Neon Glow
    fig.add_trace(go.Scatter(
        x=spec.frequencies_mhz,
        y=spec.psd_db,
        name="PSD (dB/Hz)",
        line=dict(color="#10b981", width=1.8),
        fill="tozeroy",
        fillcolor="rgba(16, 185, 129, 0.08)",
        mode="lines",
        hovertemplate="Freq: %{x:.4f} MHz<br>Power: %{y:.1f} dB<extra></extra>",
    ))

    # Spectral Peak Marker
    fig.add_trace(go.Scatter(
        x=[peak_freq],
        y=[peak_pwr],
        mode="markers+text",
        name="Carrier Peak",
        marker=dict(color="#00f2fe", size=8, symbol="diamond", line=dict(color="#ffffff", width=1)),
        text=[f"Peak: {peak_freq:.3f} MHz ({peak_pwr:.1f} dB)"],
        textposition="top center",
        textfont=dict(color="#38bdf8", size=10),
        hoverinfo="skip",
    ))

    # Add noise floor line
    noise_floor = getattr(spec, "noise_floor_db", None)
    if noise_floor is not None:
        fig.add_hline(
            y=noise_floor,
            line_dash="dash",
            line_color="rgba(244, 63, 94, 0.7)",
            line_width=1.2,
            annotation_text=f"Noise Floor ({noise_floor:.1f} dB)",
            annotation_position="bottom right",
            annotation_font=dict(size=9, color="#fb7185"),
        )

    # Add bandwidth span if available
    c_freq = getattr(spec, "center_freq_mhz", None)
    bw_val = getattr(spec, "bandwidth_mhz", None)
    if c_freq is not None and bw_val is not None and bw_val > 0:
        half_bw = bw_val / 2.0
        fig.add_vrect(
            x0=c_freq - half_bw,
            x1=c_freq + half_bw,
            fillcolor="#38bdf8",
            opacity=0.14,
            line_width=1,
            line_color="rgba(56, 189, 248, 0.6)",
            annotation_text=f"BW: {bw_val:.3f} MHz",
            annotation_position="top left",
            annotation_font=dict(size=10, color="#38bdf8"),
        )

    title_text = "<b>POWER SPECTRAL DENSITY (WELCH INTEGRATION)</b>"
    if spec.downsampled:
        title_text += " <span style='font-size:10px;color:#94a3b8;font-weight:normal;'>[Fast Fourier Grid]</span>"

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": {
            "text": title_text,
            "font": {"size": 13, "color": "#f1f5f9"},
        },
        "xaxis": {
            "title": "Frequency (MHz)",
            "gridcolor": "rgba(148, 163, 184, 0.12)",
            "zerolinecolor": "rgba(56, 189, 248, 0.3)",
        },
        "yaxis": {
            "title": "Spectral Density (dB/Hz)",
            "gridcolor": "rgba(148, 163, 184, 0.12)",
            "zerolinecolor": "rgba(56, 189, 248, 0.3)",
        },
        "hovermode": "x",
        "showlegend": False,
        "height": 330,
        "margin": dict(l=45, r=15, t=40, b=35),
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig


# -----------------------------------------------------------------------------
# 3. Interactive Constellation Diagram with Decision Rings
# -----------------------------------------------------------------------------
def create_constellation_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly I/Q Constellation scatter plot with decision rings."""
    if not artifacts.constellation or not artifacts.constellation.i_points:
        return None

    c = artifacts.constellation
    tokens = get_theme_tokens()
    fig = go.Figure()

    # Scatter points with high-contrast cyber glow
    fig.add_trace(go.Scatter(
        x=c.i_points,
        y=c.q_points,
        mode="markers",
        marker=dict(
            size=5,
            color="#38bdf8",
            opacity=0.65,
            line=dict(color="#00f2fe", width=0.5),
        ),
        name="Symbol Cloud",
        hovertemplate="I: %{x:.3f}<br>Q: %{y:.3f}<extra></extra>",
    ))

    # Unit circle for reference
    theta = np.linspace(0, 2 * np.pi, 120)
    fig.add_trace(go.Scatter(
        x=np.cos(theta),
        y=np.sin(theta),
        mode="lines",
        line=dict(color="rgba(148, 163, 184, 0.3)", width=1.2, dash="dash"),
        hoverinfo="skip",
        showlegend=False,
    ))

    # Outer amplitude ring for 16-QAM or 8-PSK reference
    fig.add_trace(go.Scatter(
        x=np.sqrt(2) * np.cos(theta),
        y=np.sqrt(2) * np.sin(theta),
        mode="lines",
        line=dict(color="rgba(148, 163, 184, 0.15)", width=1, dash="dot"),
        hoverinfo="skip",
        showlegend=False,
    ))

    num_pts = getattr(c, "num_points", getattr(c, "sample_count", len(c.i_points)))
    title_text = f"<b>I/Q CONSTELLATION SYMBOL CLUSTER</b> ({num_pts:,} pts)"
    evm_val = getattr(c, "evm_percent", None)
    if evm_val is not None:
        title_text += f" <span style='font-size:11px;color:#10b981;font-weight:normal;'>EVM: {evm_val:.1f}%</span>"

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": {
            "text": title_text,
            "font": {"size": 13, "color": "#f1f5f9"},
        },
        "xaxis_title": "In-Phase (I)",
        "yaxis_title": "Quadrature (Q)",
        "xaxis": dict(
            scaleanchor="y",
            scaleratio=1,
            zeroline=True,
            zerolinecolor="rgba(56, 189, 248, 0.4)",
            gridcolor="rgba(148, 163, 184, 0.12)",
        ),
        "yaxis": dict(
            zeroline=True,
            zerolinecolor="rgba(56, 189, 248, 0.4)",
            gridcolor="rgba(148, 163, 184, 0.12)",
        ),
        "height": 340,
        "showlegend": False,
        "margin": dict(l=45, r=15, t=40, b=35),
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig


# -----------------------------------------------------------------------------
# 4. Interactive 2D Spectrogram / Waterfall Plot
# -----------------------------------------------------------------------------
def create_waterfall_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly 2D Spectrogram / Waterfall heatmap with Turbo color scale."""
    if not artifacts.waterfall or not artifacts.waterfall.intensity_matrix:
        return None

    wf = artifacts.waterfall
    fig = go.Figure(data=go.Heatmap(
        z=wf.intensity_matrix,
        x=wf.freq_bins_mhz,
        y=wf.time_steps_ms,
        colorscale="Turbo",
        colorbar=dict(
            title=dict(text="dBFS", font=dict(size=10, color="#94a3b8")),
            len=0.9,
            thickness=14,
            tickfont=dict(size=9, color="#94a3b8"),
        ),
    ))

    title_text = "<b>2D TIME-FREQUENCY SPECTROGRAM (WATERFALL)</b>"
    if wf.downsampled:
        title_text += " <span style='font-size:11px;color:#94a3b8;font-weight:normal;'>(Temporal STFT)</span>"

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": {
            "text": title_text,
            "font": {"size": 13, "color": "#f1f5f9"},
        },
        "xaxis_title": "Frequency Offset (MHz)",
        "yaxis_title": "Time Elapsed (ms)",
        "height": 340,
        "margin": dict(l=50, r=20, t=40, b=35),
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig


# -----------------------------------------------------------------------------
# 5. Interactive Eye Diagram Plot
# -----------------------------------------------------------------------------
def create_eye_diagram_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly Eye Diagram with persistence styling."""
    if not artifacts.eye_diagram or not artifacts.eye_diagram.traces_i:
        return None

    eye = artifacts.eye_diagram
    tokens = get_theme_tokens()
    fig = go.Figure()

    t_rel = getattr(eye, "time_relative_sym", getattr(eye, "time_symbol_axis", []))
    syms_per = getattr(eye, "symbols_per_trace", 2)
    num_tr = getattr(eye, "num_traces", len(eye.traces_i))

    for tr in eye.traces_i:
        fig.add_trace(go.Scatter(
            x=t_rel,
            y=tr,
            mode="lines",
            line=dict(color="#38bdf8", width=0.9),
            opacity=0.35,
            showlegend=False,
            hoverinfo="skip",
        ))

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": {
            "text": f"<b>IN-PHASE EYE PATTERN PERSISTENCE</b> ({num_tr} traces, {syms_per} T_sym)",
            "font": {"size": 13, "color": "#f1f5f9"},
        },
        "xaxis_title": "Symbol Periods (T_sym)",
        "yaxis_title": "Normalized Amplitude",
        "height": 340,
        "margin": dict(l=45, r=15, t=40, b=35),
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig


# -----------------------------------------------------------------------------
# 6. Interactive Burst Timeline Plot
# -----------------------------------------------------------------------------
def create_burst_timeline_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly Burst Timeline and Power Envelope plot."""
    if not artifacts.burst_view:
        return None

    bv = artifacts.burst_view
    tokens = get_theme_tokens()
    fig = go.Figure()

    if bv.temporal_power_times_ms and bv.temporal_power_db:
        fig.add_trace(go.Scatter(
            x=bv.temporal_power_times_ms,
            y=bv.temporal_power_db,
            name="Power Envelope",
            line=dict(color="#f59e0b", width=1.8),
            mode="lines",
        ))

    # Add burst duration shaded regions
    for idx, b in enumerate(bv.bursts):
        fig.add_vrect(
            x0=b.start_time_ms,
            x1=b.end_time_ms,
            fillcolor="#10b981",
            opacity=0.22,
            line_width=1,
            line_color="rgba(16, 185, 129, 0.7)",
            annotation_text=f"Burst {idx+1} ({b.snr_db:.1f} dB)",
            annotation_position="top left",
            annotation_font=dict(size=9, color="#34d399"),
        )

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": {
            "text": f"<b>TEMPORAL BURST POWER PROFILE</b> ({bv.total_bursts} Transmission Bursts)",
            "font": {"size": 13, "color": "#f1f5f9"},
        },
        "xaxis_title": "Time offset (ms)",
        "yaxis_title": "Instantaneous Power (dBm)",
        "height": 300,
        "showlegend": False,
        "margin": dict(l=45, r=15, t=40, b=35),
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig


# -----------------------------------------------------------------------------
# Legacy Matplotlib Helpers (Preserved for Backward Compatibility)
# -----------------------------------------------------------------------------
def plot_waveform(iq_samples: np.ndarray, fs_hz: float = 1e6, max_points: int = 2000):
    fig, ax = plt.subplots(figsize=(8, 3.2), facecolor="#070b14")
    ax.set_facecolor("#0d1424")
    n = len(iq_samples)
    downsampled = n > max_points
    samples = iq_samples[::int(np.ceil(n / max_points))] if downsampled else iq_samples
    t_ms = np.arange(len(samples)) * (1.0 / fs_hz) * 1000.0 * (n / len(samples))
    ax.plot(t_ms, samples.real, label="I", color="#00f2fe", alpha=0.85)
    ax.plot(t_ms, samples.imag, label="Q", color="#c084fc", alpha=0.85)
    ax.grid(True, color="rgba(148,163,184,0.15)", linestyle="--")
    ax.tick_params(colors="#94a3b8")
    fig.tight_layout()
    return fig, downsampled


def plot_spectrum_psd(iq_samples: np.ndarray, fs_hz: float = 1e6, nfft: int = 1024):
    fig, ax = plt.subplots(figsize=(8, 3.2), facecolor="#070b14")
    ax.set_facecolor("#0d1424")
    nfft = min(nfft, len(iq_samples))
    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, d=1.0 / fs_hz)) / 1e6
    psd = np.abs(np.fft.fftshift(np.fft.fft(iq_samples[:nfft]))) ** 2
    ax.plot(freqs, 10 * np.log10(np.maximum(psd, 1e-12)), color="#10b981")
    ax.grid(True, color="rgba(148,163,184,0.15)", linestyle="--")
    ax.tick_params(colors="#94a3b8")
    fig.tight_layout()
    return fig, False


def plot_constellation(iq_samples: np.ndarray, max_points: int = 1000):
    fig, ax = plt.subplots(figsize=(4, 4), facecolor="#070b14")
    ax.set_facecolor("#0d1424")
    n = len(iq_samples)
    downsampled = n > max_points
    samples = iq_samples[::int(np.ceil(n / max_points))] if downsampled else iq_samples
    ax.scatter(samples.real, samples.imag, s=6, color="#38bdf8", alpha=0.6)
    ax.grid(True, color="rgba(148,163,184,0.15)", linestyle="--")
    ax.tick_params(colors="#94a3b8")
    fig.tight_layout()
    return fig, downsampled


def plot_burst_timeline(bursts: List[Any], total_duration_ms: float = 100.0):
    fig, ax = plt.subplots(figsize=(8, 2.0), facecolor="#070b14")
    ax.set_facecolor("#0d1424")
    for idx, b in enumerate(bursts):
        start = getattr(b, "start_time_s", 0) * 1000.0
        dur = getattr(b, "duration_s", 0.01) * 1000.0
        ax.barh(0, dur, left=start, height=0.5, color="#f59e0b", alpha=0.8)
    ax.grid(True, color="rgba(148,163,184,0.15)", linestyle="--")
    ax.tick_params(colors="#94a3b8")
    fig.tight_layout()
    return fig
