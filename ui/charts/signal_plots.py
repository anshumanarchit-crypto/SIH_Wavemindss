"""
Signal Visualization Helpers.
Strictly for UI presentation; does not alter analysis data or execute decoders.
Downsamples for visualization when needed and displays 'Visualization downsampled' badges.
"""

from typing import Any, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np

# Styling constants
PLOT_BG_COLOR = "#0e1117"
PLOT_CARD_BG = "#161b22"
PLOT_TEXT_COLOR = "#c9d1d9"
PLOT_GRID_COLOR = "#30363d"
ACCENT_BLUE = "#58a6ff"
ACCENT_GREEN = "#3fb950"
ACCENT_ORANGE = "#d29922"
ACCENT_PURPLE = "#bc8cff"


def _apply_theme(ax: plt.Axes, title: str, xlabel: str, ylabel: str) -> None:
    """Applies clean engineering dark theme to a matplotlib axes."""
    ax.set_facecolor(PLOT_CARD_BG)
    ax.tick_params(colors=PLOT_TEXT_COLOR, labelsize=9)
    ax.set_title(title, color=PLOT_TEXT_COLOR, fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, color=PLOT_TEXT_COLOR, fontsize=10)
    ax.set_ylabel(ylabel, color=PLOT_TEXT_COLOR, fontsize=10)
    ax.grid(True, color=PLOT_GRID_COLOR, linestyle="--", linewidth=0.5, alpha=0.7)
    for spine in ax.spines.values():
        spine.set_color(PLOT_GRID_COLOR)


def plot_waveform(
    iq_samples: np.ndarray,
    fs_hz: float = 1e6,
    max_points: int = 2000,
) -> Tuple[plt.Figure, bool]:
    """Plots in-phase (I) and quadrature (Q) time-domain waveform."""
    fig, ax = plt.subplots(figsize=(8, 3.2), facecolor=PLOT_BG_COLOR)
    downsampled = False
    n = len(iq_samples)

    if n > max_points:
        step = int(np.ceil(n / max_points))
        samples = iq_samples[::step]
        downsampled = True
    else:
        samples = iq_samples

    t_ms = np.arange(len(samples)) * (1.0 / fs_hz) * 1000.0 * (n / len(samples))
    ax.plot(t_ms, samples.real, label="I (In-phase)", color=ACCENT_BLUE, alpha=0.85, linewidth=1.0)
    ax.plot(t_ms, samples.imag, label="Q (Quadrature)", color=ACCENT_ORANGE, alpha=0.85, linewidth=1.0)

    title = "Time-Domain IQ Waveform" + (" (Visualization downsampled)" if downsampled else "")
    _apply_theme(ax, title, "Time (ms)", "Amplitude")
    ax.legend(facecolor=PLOT_CARD_BG, edgecolor=PLOT_GRID_COLOR, labelcolor=PLOT_TEXT_COLOR, loc="upper right")
    fig.tight_layout()
    return fig, downsampled


def plot_spectrum_psd(
    iq_samples: np.ndarray,
    fs_hz: float = 1e6,
    nfft: int = 1024,
) -> Tuple[plt.Figure, bool]:
    """Plots power spectral density (PSD)."""
    fig, ax = plt.subplots(figsize=(8, 3.2), facecolor=PLOT_BG_COLOR)
    downsampled = False

    # Compute FFT
    if len(iq_samples) < nfft:
        nfft = max(64, int(2 ** np.floor(np.log2(len(iq_samples)))))

    # Average PSD over segments
    hop = nfft // 2
    segments = []
    window = np.hanning(nfft)
    for i in range(0, len(iq_samples) - nfft + 1, hop):
        seg = iq_samples[i : i + nfft] * window
        segments.append(np.abs(np.fft.fftshift(np.fft.fft(seg))) ** 2)
        if len(segments) >= 64:
            downsampled = True
            break

    if segments:
        psd = np.mean(segments, axis=0)
        psd_db = 10 * np.log10(np.maximum(psd, 1e-12))
        freqs_mhz = np.fft.fftshift(np.fft.fftfreq(nfft, d=1.0 / fs_hz)) / 1e6
        ax.plot(freqs_mhz, psd_db, color=ACCENT_GREEN, linewidth=1.2)
        title = "Power Spectral Density (PSD)" + (" (Visualization downsampled)" if downsampled else "")
        _apply_theme(ax, title, "Frequency (MHz)", "Power (dB/Hz)")
    else:
        ax.text(0.5, 0.5, "Insufficient samples for PSD", color=PLOT_TEXT_COLOR, ha="center")
        _apply_theme(ax, "Power Spectral Density", "Frequency", "Power")

    fig.tight_layout()
    return fig, downsampled


def plot_constellation(
    iq_samples: np.ndarray,
    max_points: int = 3000,
) -> Tuple[plt.Figure, bool]:
    """Plots 2D complex constellation scatter."""
    fig, ax = plt.subplots(figsize=(4.5, 4.5), facecolor=PLOT_BG_COLOR)
    downsampled = False
    n = len(iq_samples)

    if n > max_points:
        indices = np.random.RandomState(42).choice(n, size=max_points, replace=False)
        pts = iq_samples[indices]
        downsampled = True
    else:
        pts = iq_samples

    ax.scatter(pts.real, pts.imag, s=6, color=ACCENT_BLUE, alpha=0.5, edgecolors="none")
    ax.axhline(0, color=PLOT_GRID_COLOR, linestyle="--", linewidth=0.8)
    ax.axvline(0, color=PLOT_GRID_COLOR, linestyle="--", linewidth=0.8)

    title = "IQ Constellation" + (" (Downsampled)" if downsampled else "")
    _apply_theme(ax, title, "In-phase (I)", "Quadrature (Q)")
    fig.tight_layout()
    return fig, downsampled


def plot_burst_timeline(bursts: List[Any]) -> plt.Figure:
    """Visualizes detected bursts on a timeline."""
    fig, ax = plt.subplots(figsize=(8, 2.4), facecolor=PLOT_BG_COLOR)
    if not bursts:
        ax.text(0.5, 0.5, "No Bursts Detected (Continuous or Noise-only)", color=PLOT_TEXT_COLOR, ha="center", va="center")
        _apply_theme(ax, "Burst Activity Timeline", "Time (ms)", "Power (dBm)")
        fig.tight_layout()
        return fig

    for b in bursts:
        # Support both NormalizedBurst and dict
        s = getattr(b, "start_ms", b.get("start_ms", 0.0))
        e = getattr(b, "end_ms", b.get("end_ms", 1.0))
        p = getattr(b, "power_db", getattr(b, "power", b.get("power", -10.0)))
        idx = getattr(b, "index", 0)

        dur = e - s
        ax.barh(0, dur, left=s, height=0.5, color=ACCENT_PURPLE, alpha=0.75, edgecolor=ACCENT_BLUE)
        ax.text(s + dur / 2, 0, f"B{idx}\n{p:.1f} dBm", color="#ffffff", ha="center", va="center", fontsize=8, fontweight="bold")

    ax.set_yticks([])
    _apply_theme(ax, "Detected Burst Timeline", "Time (ms)", "")
    fig.tight_layout()
    return fig
