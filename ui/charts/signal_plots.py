"""
SpectralQ Signal Visualization Engine.
Generates engineering-grade interactive Plotly visualizations for the Signal Observatory.
Consumes prepared artifacts from spectralq.visualization.
Never generates fake signals: operates strictly on genuine capture data.
Also preserves legacy matplotlib interfaces for backward compatibility.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt

from ui.styles.theme import get_theme_tokens, get_plotly_layout_defaults
from spectralq.visualization.artifacts import ObservatoryArtifacts


# -----------------------------------------------------------------------------
# Plotly Interactive Observational Charts
# -----------------------------------------------------------------------------

def create_waveform_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly waveform plot showing I and Q time series."""
    if not artifacts.raw_available or not artifacts.waveform_i:
        return None

    tokens = get_theme_tokens()
    fig = go.Figure()

    times = artifacts.waveform_times_ms
    # Real / Channel 1 (In-Phase) - Gold/Yellow
    fig.add_trace(go.Scatter(
        x=times,
        y=artifacts.waveform_i,
        name="Real (Channel 1) [I]",
        line=dict(color="#f1e05a" if tokens["plotly_template"] == "plotly_dark" else "#b08800", width=1.3),
        mode="lines",
    ))
    # Imag / Channel 2 (Quadrature) - Cyan/Blue
    fig.add_trace(go.Scatter(
        x=times,
        y=artifacts.waveform_q,
        name="Imag (Channel 2) [Q]",
        line=dict(color="#58a6ff" if tokens["plotly_template"] == "plotly_dark" else "#0969da", width=1.3),
        mode="lines",
    ))

    title_text = "IQ waveform <span style='font-size:12px;color:#8b949e;'>(Raw signal visualization)</span>"
    if artifacts.downsampled:
        title_text += " <span style='font-size:10px;color:#8b949e;'>[Decimated]</span>"

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": title_text,
        "xaxis_title": "Time (ms)",
        "yaxis_title": "Amplitude",
        "hovermode": "x unified",
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        "height": 330,
        "margin": dict(l=45, r=15, t=40, b=35),
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig



def create_spectrum_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly Power Spectral Density plot."""
    if not artifacts.spectrum or not artifacts.spectrum.frequencies_mhz:
        return None

    spec = artifacts.spectrum
    tokens = get_theme_tokens()
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=spec.frequencies_mhz,
        y=spec.psd_db,
        name="PSD (dB/Hz)",
        line=dict(color=tokens["pass_color"], width=1.4),
        mode="lines",
    ))

    # Add noise floor line
    noise_floor = getattr(spec, "noise_floor_db", None)
    if noise_floor is not None:
        fig.add_hline(
            y=noise_floor,
            line_dash="dot",
            line_color=tokens["text_muted"],
            annotation_text=f"Noise Floor ({noise_floor:.1f} dB)",
            annotation_position="bottom right",
        )

    # Add bandwidth span if available
    c_freq = getattr(spec, "center_freq_mhz", None)
    bw_val = getattr(spec, "bandwidth_mhz", None)
    if c_freq is not None and bw_val is not None and bw_val > 0:
        half_bw = bw_val / 2.0
        fig.add_vrect(
            x0=c_freq - half_bw,
            x1=c_freq + half_bw,
            fillcolor=tokens["primary"],
            opacity=0.12,
            line_width=0,
            annotation_text=f"BW: {bw_val:.3f} MHz",
            annotation_position="top left",
        )


    title_text = "Frequency spectrum <span style='font-size:12px;color:#8b949e;'>(Spectral characteristics)</span>"
    if spec.downsampled:
        title_text += " <span style='font-size:10px;color:#8b949e;'>[Decimated]</span>"

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": title_text,
        "xaxis_title": "Frequency (MHz)",
        "yaxis_title": "Power (dB)",
        "hovermode": "x",
        "height": 330,
        "margin": dict(l=45, r=15, t=40, b=35),
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig



def create_waterfall_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly 2D Spectrogram / Waterfall heatmap."""
    if not artifacts.waterfall or not artifacts.waterfall.intensity_matrix:
        return None

    wf = artifacts.waterfall
    fig = go.Figure(data=go.Heatmap(
        z=wf.intensity_matrix,
        x=wf.freq_bins_mhz,
        y=wf.time_steps_ms,
        colorscale="Viridis",
        colorbar=dict(title="dB", len=0.85),
    ))

    title_text = "Spectrogram / Waterfall Intensity"
    if wf.downsampled:
        title_text += " <span style='font-size:11px;color:#8b949e;'>(Decimated Grid)</span>"

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": title_text,
        "xaxis_title": "Frequency (MHz)",
        "yaxis_title": "Time (ms)",
        "height": 340,
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig


def create_constellation_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly I/Q Constellation scatter plot."""
    if not artifacts.constellation or not artifacts.constellation.i_points:
        return None

    c = artifacts.constellation
    tokens = get_theme_tokens()
    fig = go.Figure()

    # Scatter points
    fig.add_trace(go.Scatter(
        x=c.i_points,
        y=c.q_points,
        mode="markers",
        marker=dict(
            size=4,
            color=tokens["primary"],
            opacity=0.7,
        ),
        name="Symbols",
    ))

    # Unit circle for reference
    theta = np.linspace(0, 2 * np.pi, 100)
    fig.add_trace(go.Scatter(
        x=np.cos(theta),
        y=np.sin(theta),
        mode="lines",
        line=dict(color=tokens["card_border"], width=1, dash="dash"),
        hoverinfo="skip",
        showlegend=False,
    ))

    num_pts = getattr(c, "num_points", getattr(c, "sample_count", len(c.i_points)))
    title_text = f"I/Q Constellation Diagram ({num_pts} pts)"
    evm_val = getattr(c, "evm_percent", None)
    if evm_val is not None:
        title_text += f" <span style='font-size:11px;color:#8b949e;'>EVM: {evm_val:.1f}%</span>"


    layout = get_plotly_layout_defaults()
    layout.update({
        "title": title_text,
        "xaxis_title": "In-Phase (I)",
        "yaxis_title": "Quadrature (Q)",
        "xaxis": dict(scaleanchor="y", scaleratio=1, zeroline=True, zerolinecolor=tokens["card_border"]),
        "yaxis": dict(zeroline=True, zerolinecolor=tokens["card_border"]),
        "height": 340,
        "showlegend": False,
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig


def create_eye_diagram_plot(
    artifacts: ObservatoryArtifacts,
    layout_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[go.Figure]:
    """Generates an interactive Plotly Eye Diagram."""
    if not artifacts.eye_diagram or not artifacts.eye_diagram.traces_i:
        return None

    eye = artifacts.eye_diagram
    tokens = get_theme_tokens()
    fig = go.Figure()

    t_rel = getattr(eye, "time_relative_sym", getattr(eye, "time_symbol_axis", []))
    syms_per = getattr(eye, "symbols_per_trace", 2)
    num_tr = getattr(eye, "num_traces", len(eye.traces_i))
    # Draw individual traces
    for tr in eye.traces_i:
        fig.add_trace(go.Scatter(
            x=t_rel,
            y=tr,
            mode="lines",
            line=dict(color=tokens["primary"], width=0.8),
            opacity=0.35,
            showlegend=False,
            hoverinfo="skip",
        ))

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": f"In-Phase Eye Diagram ({num_tr} traces, {syms_per} symbols)",
        "xaxis_title": "Symbol Periods (T_sym)",
        "yaxis_title": "Amplitude",
        "height": 340,
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig


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
            line=dict(color=tokens["accent"], width=1.5),
            mode="lines",
        ))

    # Add burst duration shaded regions
    for idx, b in enumerate(bv.bursts):
        fig.add_vrect(
            x0=b.start_time_ms,
            x1=b.end_time_ms,
            fillcolor=tokens["pass_color"],
            opacity=0.2,
            line_width=1,
            line_color=tokens["pass_color"],
            annotation_text=f"B{idx+1} ({b.snr_db:.1f} dB)",
            annotation_position="top left",
        )

    layout = get_plotly_layout_defaults()
    layout.update({
        "title": f"Temporal Burst Power & Intervals (Detected: {bv.total_bursts})",
        "xaxis_title": "Time (ms)",
        "yaxis_title": "Power (dB)",
        "height": 300,
        "showlegend": False,
    })
    if layout_overrides:
        layout.update(layout_overrides)

    fig.update_layout(layout)
    return fig


# -----------------------------------------------------------------------------
# Legacy Matplotlib Helpers (Preserved for Backward Compatibility)
# -----------------------------------------------------------------------------

def plot_waveform(
    iq_samples: np.ndarray,
    fs_hz: float = 1e6,
    max_points: int = 2000,
) -> Tuple[plt.Figure, bool]:
    """Legacy matplotlib waveform plot."""
    fig, ax = plt.subplots(figsize=(8, 3.2), facecolor="#0e1117")
    ax.set_facecolor("#161b22")
    n = len(iq_samples)
    downsampled = n > max_points
    samples = iq_samples[::int(np.ceil(n / max_points))] if downsampled else iq_samples
    t_ms = np.arange(len(samples)) * (1.0 / fs_hz) * 1000.0 * (n / len(samples))
    ax.plot(t_ms, samples.real, label="I", color="#58a6ff", alpha=0.85)
    ax.plot(t_ms, samples.imag, label="Q", color="#d29922", alpha=0.85)
    ax.grid(True, color="#30363d", linestyle="--", alpha=0.5)
    ax.tick_params(colors="#c9d1d9")
    fig.tight_layout()
    return fig, downsampled


def plot_spectrum_psd(
    iq_samples: np.ndarray,
    fs_hz: float = 1e6,
    nfft: int = 1024,
) -> Tuple[plt.Figure, bool]:
    """Legacy matplotlib PSD plot."""
    fig, ax = plt.subplots(figsize=(8, 3.2), facecolor="#0e1117")
    ax.set_facecolor("#161b22")
    nfft = min(nfft, len(iq_samples))
    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, d=1.0 / fs_hz)) / 1e6
    psd = np.abs(np.fft.fftshift(np.fft.fft(iq_samples[:nfft]))) ** 2
    ax.plot(freqs, 10 * np.log10(np.maximum(psd, 1e-12)), color="#3fb950")
    ax.grid(True, color="#30363d", linestyle="--", alpha=0.5)
    ax.tick_params(colors="#c9d1d9")
    fig.tight_layout()
    return fig, False


def plot_constellation(
    iq_samples: np.ndarray,
    max_points: int = 1000,
) -> Tuple[plt.Figure, bool]:
    """Legacy matplotlib constellation plot."""
    fig, ax = plt.subplots(figsize=(4, 4), facecolor="#0e1117")
    ax.set_facecolor("#161b22")
    n = len(iq_samples)
    downsampled = n > max_points
    samples = iq_samples[::int(np.ceil(n / max_points))] if downsampled else iq_samples
    ax.scatter(samples.real, samples.imag, s=6, color="#58a6ff", alpha=0.6)
    ax.grid(True, color="#30363d", linestyle="--", alpha=0.5)
    ax.tick_params(colors="#c9d1d9")
    fig.tight_layout()
    return fig, downsampled


def plot_burst_timeline(
    bursts: List[Any],
    total_duration_ms: float = 100.0,
) -> plt.Figure:
    """Legacy matplotlib burst timeline plot."""
    fig, ax = plt.subplots(figsize=(8, 2.0), facecolor="#0e1117")
    ax.set_facecolor("#161b22")
    for idx, b in enumerate(bursts):
        start = getattr(b, "start_time_s", 0) * 1000.0
        dur = getattr(b, "duration_s", 0.01) * 1000.0
        ax.barh(0, dur, left=start, height=0.5, color="#58a6ff", alpha=0.8)
    ax.grid(True, color="#30363d", linestyle="--", alpha=0.5)
    ax.tick_params(colors="#c9d1d9")
    fig.tight_layout()
    return fig
