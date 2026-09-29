"""
SpectralQ UI Styling & Design Tokens Engine.
Provides engineering-grade telemetry styling with complete Light and Dark theme support.
Complies strictly with the SpectralQ Master Color System and Defense Command Center specification.
"""

from typing import Dict, Any
import streamlit as st
from ui.styles.design_system import DESIGN_TOKENS, get_design_tokens


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
        "• L4: Coding & FEC Lock (conv / Reed-Solomon / Interleaver sync)\n"
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
# Design Token Palettes (Flagship Dark Command Center & High-Contrast Light)
# -----------------------------------------------------------------------------
THEMES = {
    "dark": {
        "bg": "#070A0F",
        "card_bg": "#101720",
        "card_border": "rgba(255, 255, 255, 0.08)",
        "card_border_strong": "rgba(255, 255, 255, 0.14)",
        "text": "#F4F7FB",
        "text_secondary": "#A8B2C2",
        "text_muted": "#707C90",
        "primary": "#53D7FF",           # Primary RF Cyan
        "accent": "#5B8CFF",            # Secondary Electric Blue
        "violet": "#9A7CFF",
        "magenta": "#F06BFF",
        "pass_bg": "rgba(53, 227, 154, 0.12)",
        "pass_color": "#35E39A",
        "pass_border": "rgba(53, 227, 154, 0.35)",
        "fail_bg": "rgba(255, 98, 120, 0.14)",
        "fail_color": "#FF6278",
        "fail_border": "rgba(255, 98, 120, 0.35)",
        "warn_bg": "rgba(255, 184, 77, 0.12)",
        "warn_color": "#FFB84D",
        "warn_border": "rgba(255, 184, 77, 0.35)",
        "unavailable_bg": "#151D27",
        "unavailable_color": "#707C90",
        "unavailable_border": "rgba(255, 255, 255, 0.08)",
        "ladder_bg": "rgba(154, 124, 255, 0.14)",
        "ladder_color": "#9A7CFF",
        "ladder_border": "rgba(154, 124, 255, 0.35)",
        "replay_bg": "rgba(240, 107, 255, 0.14)",
        "replay_color": "#F06BFF",
        "replay_border": "rgba(240, 107, 255, 0.35)",
        "glow_primary": "0 0 16px rgba(83, 215, 255, 0.22)",
        "glow_pass": "0 0 16px rgba(53, 227, 154, 0.22)",
        "plotly_template": "plotly_dark",
    },
    "light": {
        "bg": "#F4F7FB",
        "card_bg": "#FFFFFF",
        "card_border": "#D8E0EA",
        "card_border_strong": "#B8C4D4",
        "text": "#152033",
        "text_secondary": "#5C6B7F",
        "text_muted": "#8A99AD",
        "primary": "#0969DA",
        "accent": "#0550AE",
        "violet": "#8250DF",
        "magenta": "#BF3989",
        "pass_bg": "#DAFBE1",
        "pass_color": "#1A7F37",
        "pass_border": "#2DA44E",
        "fail_bg": "#FFEBE9",
        "fail_color": "#CF222E",
        "fail_border": "#FF8182",
        "warn_bg": "#FFF8C5",
        "warn_color": "#9A6700",
        "warn_border": "#D4A72C",
        "unavailable_bg": "#F6F8FA",
        "unavailable_color": "#57606A",
        "unavailable_border": "#AFB8C1",
        "ladder_bg": "#DDF4FF",
        "ladder_color": "#0969DA",
        "ladder_border": "#54AEFF",
        "replay_bg": "#FBEFFF",
        "replay_color": "#8250DF",
        "replay_border": "#C297FF",
        "glow_primary": "0 2px 10px rgba(9, 105, 218, 0.15)",
        "glow_pass": "0 2px 10px rgba(26, 127, 55, 0.15)",
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
    is_dark = tokens["plotly_template"] == "plotly_dark"
    return {
        "template": tokens["plotly_template"],
        "paper_bgcolor": tokens["bg"] if is_dark else tokens["bg"],
        "plot_bgcolor": tokens["card_bg"],
        "font": {"color": tokens["text"], "family": "Inter, -apple-system, sans-serif"},
        "margin": {"l": 45, "r": 20, "t": 45, "b": 40},
        "xaxis": {
            "gridcolor": "rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.08)",
            "zerolinecolor": "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.15)",
            "tickfont": {"size": 10, "family": "JetBrains Mono, monospace"},
        },
        "yaxis": {
            "gridcolor": "rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.08)",
            "zerolinecolor": "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.15)",
            "tickfont": {"size": 10, "family": "JetBrains Mono, monospace"},
        },
    }


def generate_theme_css(tokens: Dict[str, Any]) -> str:
    """Generates the full scoped CSS string using theme tokens."""
    is_dark = tokens["plotly_template"] == "plotly_dark"
    
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

/* Global Root & Typography */
html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background-color: {tokens["bg"]} !important;
    color: {tokens["text"]} !important;
}}

code, pre, .mono, [data-testid="stMarkdownContainer"] code {{
    font-family: 'JetBrains Mono', monospace !important;
}}

/* Sidebar Command Rail */
[data-testid="stSidebar"] {{
    background-color: {'#0B1017' if is_dark else '#EBF0F6'} !important;
    border-right: 1px solid {tokens["card_border"]} !important;
}}

[data-testid="stSidebar"] hr {{
    margin: 1rem 0 !important;
    border-color: {tokens["card_border"]} !important;
}}

/* Button Overhaul — No Red Buttons */
.stButton > button {{
    background-color: {tokens["card_bg"]} !important;
    border: 1px solid {tokens["card_border_strong"]} !important;
    color: {tokens["text"]} !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 0.45rem 0.9rem !important;
    transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
}}

.stButton > button:hover {{
    border-color: {tokens["primary"]} !important;
    color: {tokens["primary"]} !important;
    transform: translateY(-1px) !important;
    box-shadow: {tokens["glow_primary"]} !important;
}}

/* Primary Buttons: High-Fidelity Cyan Accent Gradient */
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {tokens["accent"]} 0%, {tokens["primary"]} 100%) !important;
    border: none !important;
    color: {'#070A0F' if is_dark else '#FFFFFF'} !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    box-shadow: {tokens["glow_primary"]} !important;
}}

.stButton > button[kind="primary"]:hover {{
    filter: brightness(1.08) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 0 20px rgba(83, 215, 255, 0.4) !important;
}}

/* Streamlit Tabs */
.stTabs [data-baseweb="tab-list"] {{
    background-color: transparent !important;
    border-bottom: 1px solid {tokens["card_border"]} !important;
    gap: 0.5rem !important;
}}

.stTabs [data-baseweb="tab"] {{
    background-color: transparent !important;
    border: none !important;
    border-radius: 6px 6px 0 0 !important;
    color: {tokens["text_muted"]} !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 0.6rem 1rem !important;
    transition: all 0.15s ease !important;
}}

.stTabs [aria-selected="true"] {{
    background-color: {tokens["card_bg"]} !important;
    color: {tokens["primary"]} !important;
    border-bottom: 2px solid {tokens["primary"]} !important;
}}

/* Expander Overhaul */
.streamlit-expanderHeader {{
    background-color: {tokens["card_bg"]} !important;
    border: 1px solid {tokens["card_border"]} !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    color: {tokens["text"]} !important;
}}

/* Metric Cards */
.sq-card {{
    background-color: {tokens["card_bg"]};
    border: 1px solid {tokens["card_border"]};
    border-radius: 10px;
    padding: 1.0rem 1.15rem;
    margin-bottom: 0.75rem;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
}}

.sq-card:hover {{
    border-color: {tokens["card_border_strong"]};
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.18);
}}

.sq-card-hero {{
    background: linear-gradient(135deg, {tokens["card_bg"]} 0%, {'#151D27' if is_dark else '#F9FAFC'} 100%);
    border: 1px solid {tokens["border_accent"] if "border_accent" in tokens else tokens["card_border_strong"]};
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
}}

.sq-card-title {{
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {tokens["text_muted"]};
    margin-bottom: 0.35rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.sq-card-value {{
    font-size: 1.45rem;
    font-weight: 800;
    color: {tokens["text"]};
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -0.02em;
    line-height: 1.2;
}}

.sq-card-sub {{
    font-size: 0.72rem;
    color: {tokens["text_muted"]};
    margin-top: 0.35rem;
    line-height: 1.35;
}}

/* Status Badges & Pills */
.sq-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-size: 0.68rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}

.badge-pass {{ background-color: {tokens["pass_bg"]}; color: {tokens["pass_color"]}; border: 1px solid {tokens["pass_border"]}; }}
.badge-fail {{ background-color: {tokens["fail_bg"]}; color: {tokens["fail_color"]}; border: 1px solid {tokens["fail_border"]}; }}
.badge-warn {{ background-color: {tokens["warn_bg"]}; color: {tokens["warn_color"]}; border: 1px solid {tokens["warn_border"]}; }}
.badge-unavail {{ background-color: {tokens["unavailable_bg"]}; color: {tokens["unavailable_color"]}; border: 1px solid {tokens["unavailable_border"]}; }}
.badge-ladder {{ background-color: {tokens["ladder_bg"]}; color: {tokens["ladder_color"]}; border: 1px solid {tokens["ladder_border"]}; }}
.badge-replay {{ background-color: {tokens["replay_bg"]}; color: {tokens["replay_color"]}; border: 1px solid {tokens["replay_border"]}; }}
.badge-unknown {{ background-color: {tokens["fail_bg"]}; color: {tokens["fail_color"]}; border: 1px solid {tokens["fail_border"]}; font-weight: 800; }}

/* Command Header & Telemetry Ribbon */
.sq-header-wrap {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0 1.0rem 0;
    border-bottom: 1px solid {tokens["card_border"]};
    margin-bottom: 1.0rem;
}}

.sq-meta-ribbon {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    background-color: {tokens["card_bg"]};
    border: 1px solid {tokens["card_border"]};
    border-radius: 8px;
    padding: 0.6rem 1.0rem;
    margin-bottom: 1.25rem;
    align-items: center;
}}

.sq-ribbon-cell {{
    display: flex;
    flex-direction: column;
    padding-right: 0.75rem;
    border-right: 1px solid {tokens["card_border"]};
}}

.sq-ribbon-cell:last-child {{
    border-right: none;
    padding-right: 0;
}}

.sq-ribbon-label {{
    color: {tokens["text_muted"]};
    font-size: 0.62rem;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.08em;
    margin-bottom: 0.15rem;
}}

.sq-ribbon-val {{
    color: {tokens["text"]};
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    font-weight: 700;
}}

/* Abstention / UNKNOWN Banner */
.sq-unknown-banner {{
    background: linear-gradient(135deg, rgba(255, 98, 120, 0.12) 0%, {tokens["card_bg"]} 100%);
    border: 1px solid {tokens["fail_color"]};
    border-left: 4px solid {tokens["fail_color"]};
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
}}

/* Raw Visualization Unavailable Box */
.sq-unavailable-box {{
    background-color: {tokens["card_bg"]};
    border: 1px dashed {tokens["card_border_strong"]};
    border-radius: 10px;
    padding: 2.25rem 1.5rem;
    text-align: center;
    margin: 1.0rem 0;
}}

/* Why This Decision Callout */
.sq-why-callout {{
    background-color: {tokens["card_bg"]};
    border: 1px solid {tokens["card_border"]};
    border-left: 4px solid {tokens["primary"]};
    padding: 1.0rem 1.25rem;
    border-radius: 0 10px 10px 0;
    margin: 0.5rem 0 1.0rem 0;
}}
</style>
"""


def apply_theme():
    """Injects custom CSS theme into the active Streamlit app."""
    tokens = get_theme_tokens()
    st.markdown(generate_theme_css(tokens), unsafe_allow_html=True)
