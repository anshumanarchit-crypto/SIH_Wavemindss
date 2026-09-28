"""
SpectralQ UI Styling & Design Tokens Engine.
Provides engineering-grade telemetry styling with complete Light and Dark theme support.
Includes centralized design tokens, custom CSS badges, metric cards, navigation rail,
tooltips, and Plotly theme synchronization.
"""

from typing import Dict, Any
import streamlit as st


# -----------------------------------------------------------------------------
# Plain-English Telemetry Tooltip Dictionary
# -----------------------------------------------------------------------------
TOOLTIPS: Dict[str, str] = {
    "CFO": (
        "Carrier Frequency Offset (Hz): Frequency misalignment between transmitter and receiver "
        "caused by local oscillator mismatch or Doppler shift. Sinchana's blind estimator tracks this."
    ),
    "SNR": (
        "Signal-to-Noise Ratio (dB): Ratio of desired signal power to background thermal noise. "
        ">10 dB is clean; <3 dB is noisy; <0 dB triggers conservative abstention."
    ),
    "EVM": (
        "Error Vector Magnitude (% RMS): Deviation between measured constellation symbols and "
        "ideal constellation reference points. Lower indicates higher signal fidelity."
    ),
    "BAUD": (
        "Symbol Rate (Baud / sym/s): Rate at which discrete modulation symbols are transmitted. "
        "Estimated blindly via cyclic autocorrelation and spectral peak detection."
    ),
    "BANDWIDTH": (
        "Occupied Bandwidth (Hz): 3dB or 99% power spectral occupancy of the active transmission burst."
    ),
    "LADDER": (
        "Evidence Ladder (L1-L5): SpectralQ verification hierarchy:\n"
        "• L1: Signal Detection (burst & physical parameters)\n"
        "• L2: Modulation Identification (AMC consensus)\n"
        "• L3: Blind Symbol Demodulation (constellation lock)\n"
        "• L4: Coding & FEC Lock (viterbi / Reed-Solomon / Interleaver sync)\n"
        "• L5: Frame Synchronization & CRC Validation (full payload recovery)"
    ),
    "UNKNOWN": (
        "Abstention State: The system declines to guess when signal parameters are ambiguous, "
        "SNR is insufficient, or ML and rule-based AMC disagree. An honest UNKNOWN is superior "
        "to a catastrophic false-positive."
    ),
    "BER": (
        "Bit Error Rate (BER): Ratio of received bit errors to total received bits prior to or post-FEC."
    ),
    "CRC": (
        "Cyclic Redundancy Check: Polynomial integrity checksum verifying frame payload accuracy without corruption."
    ),
    "SIGMF": (
        "Signal Metadata Format: Standardized open RF metadata specification encapsulating sample rates, "
        "timestamps, frequencies, and author provenance."
    ),
}


# -----------------------------------------------------------------------------
# Design Token Palettes
# -----------------------------------------------------------------------------
THEMES = {
    "dark": {
        "bg": "#0e1117",
        "card_bg": "#161b22",
        "card_border": "#30363d",
        "text": "#f0f6fc",
        "text_muted": "#8b949e",
        "primary": "#58a6ff",
        "accent": "#1f6feb",
        "pass_bg": "rgba(63, 185, 80, 0.15)",
        "pass_color": "#3fb950",
        "pass_border": "#238636",
        "fail_bg": "rgba(248, 81, 73, 0.15)",
        "fail_color": "#f85149",
        "fail_border": "#da3633",
        "warn_bg": "rgba(210, 153, 34, 0.15)",
        "warn_color": "#d29922",
        "warn_border": "#9e6a03",
        "unavailable_bg": "#21262d",
        "unavailable_color": "#8b949e",
        "unavailable_border": "#484f58",
        "ladder_bg": "rgba(88, 166, 255, 0.15)",
        "ladder_color": "#58a6ff",
        "ladder_border": "#1f6feb",
        "replay_bg": "rgba(188, 140, 255, 0.15)",
        "replay_color": "#bc8cff",
        "replay_border": "#8957e5",
        "plotly_template": "plotly_dark",
    },
    "light": {
        "bg": "#f6f8fa",
        "card_bg": "#ffffff",
        "card_border": "#d0d7de",
        "text": "#24292f",
        "text_muted": "#57606a",
        "primary": "#0969da",
        "accent": "#0550ae",
        "pass_bg": "#dafbe1",
        "pass_color": "#1a7f37",
        "pass_border": "#2da44e",
        "fail_bg": "#ffebe9",
        "fail_color": "#cf222e",
        "fail_border": "#ff8182",
        "warn_bg": "#fff8c5",
        "warn_color": "#9a6700",
        "warn_border": "#d4a72c",
        "unavailable_bg": "#f6f8fa",
        "unavailable_color": "#57606a",
        "unavailable_border": "#afb8c1",
        "ladder_bg": "#ddf4ff",
        "ladder_color": "#0969da",
        "ladder_border": "#54aeff",
        "replay_bg": "#fbefff",
        "replay_color": "#8250df",
        "replay_border": "#c297ff",
        "plotly_template": "plotly_white",
    },
}


def get_current_theme_name() -> str:
    """Returns the current active theme name ('dark' or 'light')."""
    return st.session_state.get("theme", "dark")


def get_theme_tokens() -> Dict[str, Any]:
    """Returns the dictionary of color and style tokens for the active theme."""
    t_name = get_current_theme_name()
    return THEMES.get(t_name, THEMES["dark"])


def get_plotly_layout_defaults() -> Dict[str, Any]:
    """Returns standard Plotly layout configuration honoring the current theme."""
    tokens = get_theme_tokens()
    return {
        "template": tokens["plotly_template"],
        "paper_bgcolor": tokens["card_bg"],
        "plot_bgcolor": tokens["card_bg"],
        "font": {"color": tokens["text"], "family": "Inter, sans-serif"},
        "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
    }


def generate_theme_css(tokens: Dict[str, Any]) -> str:
    """Generates the full scoped CSS string using theme tokens."""
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

/* Typography Defaults */
html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}

code, pre, .mono {{
    font-family: 'JetBrains Mono', monospace !important;
}}

/* Top Header */
.sq-header {{
    border-bottom: 2px solid {tokens["card_border"]};
    padding-bottom: 0.6rem;
    margin-bottom: 1.0rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.sq-title {{
    font-size: 1.55rem;
    font-weight: 700;
    color: {tokens["primary"]};
    letter-spacing: -0.02em;
    margin: 0;
}}

.sq-subtitle {{
    font-size: 0.82rem;
    color: {tokens["text_muted"]};
    margin-top: 0.15rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

/* Telemetry Metadata Bar */
.sq-meta-bar {{
    display: flex;
    flex-wrap: wrap;
    gap: 1.25rem;
    background-color: {tokens["card_bg"]};
    border: 1px solid {tokens["card_border"]};
    border-radius: 6px;
    padding: 0.5rem 0.85rem;
    margin-bottom: 1.0rem;
    font-size: 0.82rem;
}}

.sq-meta-item {{
    display: flex;
    flex-direction: column;
}}

.sq-meta-label {{
    color: {tokens["text_muted"]};
    font-size: 0.68rem;
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.04em;
}}

.sq-meta-value {{
    color: {tokens["text"]};
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
}}

/* High-Density Metric Cards */
.sq-card {{
    background-color: {tokens["card_bg"]};
    border: 1px solid {tokens["card_border"]};
    border-radius: 6px;
    padding: 0.75rem 0.9rem;
    margin-bottom: 0.65rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}

.sq-card-title {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {tokens["text_muted"]};
    margin-bottom: 0.2rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.sq-card-value {{
    font-size: 1.3rem;
    font-weight: 700;
    color: {tokens["text"]};
    font-family: 'JetBrains Mono', monospace;
}}

.sq-card-sub {{
    font-size: 0.72rem;
    color: {tokens["text_muted"]};
    margin-top: 0.2rem;
}}

/* Tooltips */
.sq-info-icon {{
    display: inline-block;
    cursor: help;
    font-size: 0.75rem;
    color: {tokens["primary"]};
    margin-left: 0.3rem;
    opacity: 0.8;
}}
.sq-info-icon:hover {{
    opacity: 1.0;
}}

/* Status Badges */
.sq-badge {{
    display: inline-block;
    padding: 0.16rem 0.48rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}}

.badge-pass {{ background-color: {tokens["pass_bg"]}; color: {tokens["pass_color"]}; border: 1px solid {tokens["pass_border"]}; }}
.badge-fail {{ background-color: {tokens["fail_bg"]}; color: {tokens["fail_color"]}; border: 1px solid {tokens["fail_border"]}; }}
.badge-warn {{ background-color: {tokens["warn_bg"]}; color: {tokens["warn_color"]}; border: 1px solid {tokens["warn_border"]}; }}
.badge-unavail {{ background-color: {tokens["unavailable_bg"]}; color: {tokens["unavailable_color"]}; border: 1px solid {tokens["unavailable_border"]}; }}
.badge-ladder {{ background-color: {tokens["ladder_bg"]}; color: {tokens["ladder_color"]}; border: 1px solid {tokens["ladder_border"]}; }}
.badge-replay {{ background-color: {tokens["replay_bg"]}; color: {tokens["replay_color"]}; border: 1px solid {tokens["replay_border"]}; }}
.badge-unknown {{ background-color: {tokens["fail_bg"]}; color: {tokens["fail_color"]}; border: 2px solid {tokens["fail_color"]}; font-weight: 800; }}

/* Prominent UNKNOWN Banner */
.sq-unknown-banner {{
    background-color: {tokens["fail_bg"]};
    border: 2px solid {tokens["fail_color"]};
    border-radius: 8px;
    padding: 1.1rem;
    margin-bottom: 1.25rem;
}}

.sq-unknown-title {{
    font-size: 1.15rem;
    font-weight: 700;
    color: {tokens["fail_color"]};
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}

.sq-unknown-desc {{
    color: {tokens["text"]};
    font-size: 0.88rem;
    line-height: 1.4;
}}

/* Prominent Raw Visualization Unavailable Banner */
.sq-unavailable-box {{
    background-color: {tokens["card_bg"]};
    border: 2px dashed {tokens["card_border"]};
    border-radius: 8px;
    padding: 1.5rem;
    text-align: center;
    margin: 1.0rem 0;
}}

.sq-unavailable-title {{
    font-size: 1.1rem;
    font-weight: 700;
    color: {tokens["warn_color"]};
    margin-bottom: 0.5rem;
}}

.sq-unavailable-msg {{
    font-size: 0.86rem;
    color: {tokens["text_muted"]};
    max-width: 650px;
    margin: 0 auto 0.75rem auto;
    line-height: 1.45;
}}

/* Simulation Ground Truth Watermark */
.sq-ground-truth-badge {{
    background-color: {tokens["warn_bg"]};
    border: 1px solid {tokens["warn_border"]};
    color: {tokens["warn_color"]};
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.35rem 0.75rem;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 0.75rem;
}}

/* "Why This Decision?" Drawer Callout */
.sq-why-callout {{
    background-color: {tokens["ladder_bg"]};
    border-left: 4px solid {tokens["primary"]};
    padding: 0.85rem 1.0rem;
    border-radius: 0 6px 6px 0;
    margin: 0.75rem 0 1.0rem 0;
}}

.sq-why-title {{
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {tokens["primary"]};
    margin-bottom: 0.25rem;
}}

.sq-why-text {{
    font-size: 0.86rem;
    color: {tokens["text"]};
    line-height: 1.4;
    margin: 0;
}}

/* Pipeline Stepper Bar */
.sq-stepper {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(105px, 1fr));
    gap: 0.4rem;
    margin-bottom: 1.0rem;
}}

.sq-step {{
    background-color: {tokens["card_bg"]};
    border: 1px solid {tokens["card_border"]};
    border-radius: 5px;
    padding: 0.45rem 0.5rem;
    text-align: center;
    transition: all 0.15s ease-in-out;
}}

.sq-step.active {{
    border-color: {tokens["primary"]};
    background-color: {tokens["ladder_bg"]};
}}

.sq-step-num {{
    font-size: 0.65rem;
    color: {tokens["text_muted"]};
    font-weight: 700;
}}

.sq-step-name {{
    font-size: 0.7rem;
    color: {tokens["text"]};
    font-weight: 600;
    margin: 0.15rem 0;
    text-transform: uppercase;
}}
</style>
"""


def apply_theme():
    """Injects custom CSS theme into the active Streamlit app."""
    tokens = get_theme_tokens()
    st.markdown(generate_theme_css(tokens), unsafe_allow_html=True)
