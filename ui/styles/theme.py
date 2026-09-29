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
# Design Token Palettes (Neon Cyber Glassmorphism)
# -----------------------------------------------------------------------------
THEMES = {
    "dark": {
        "bg": "#070b14",
        "card_bg": "rgba(13, 20, 36, 0.78)",
        "card_border": "rgba(56, 189, 248, 0.18)",
        "text": "#f1f5f9",
        "text_muted": "#94a3b8",
        "primary": "#38bdf8",
        "accent": "#818cf8",
        "neon_cyan": "#00f2fe",
        "neon_blue": "#38bdf8",
        "neon_purple": "#c084fc",
        "neon_emerald": "#10b981",
        "neon_amber": "#f59e0b",
        "neon_rose": "#f43f5e",
        "pass_bg": "rgba(16, 185, 129, 0.14)",
        "pass_color": "#10b981",
        "pass_border": "rgba(16, 185, 129, 0.4)",
        "fail_bg": "rgba(244, 63, 94, 0.14)",
        "fail_color": "#f43f5e",
        "fail_border": "rgba(244, 63, 94, 0.4)",
        "warn_bg": "rgba(245, 158, 11, 0.14)",
        "warn_color": "#f59e0b",
        "warn_border": "rgba(245, 158, 11, 0.4)",
        "unavailable_bg": "rgba(30, 41, 59, 0.6)",
        "unavailable_color": "#94a3b8",
        "unavailable_border": "rgba(71, 85, 105, 0.4)",
        "ladder_bg": "rgba(56, 189, 248, 0.14)",
        "ladder_color": "#38bdf8",
        "ladder_border": "rgba(56, 189, 248, 0.4)",
        "replay_bg": "rgba(192, 132, 252, 0.14)",
        "replay_color": "#c084fc",
        "replay_border": "rgba(192, 132, 252, 0.4)",
        "plotly_template": "plotly_dark",
    },
    "light": {
        "bg": "#f8fafc",
        "card_bg": "rgba(255, 255, 255, 0.92)",
        "card_border": "rgba(203, 213, 225, 0.8)",
        "text": "#0f172a",
        "text_muted": "#64748b",
        "primary": "#0284c7",
        "accent": "#4f46e5",
        "neon_cyan": "#0284c7",
        "neon_blue": "#2563eb",
        "neon_purple": "#7c3aed",
        "neon_emerald": "#059669",
        "neon_amber": "#d97706",
        "neon_rose": "#e11d48",
        "pass_bg": "rgba(5, 150, 105, 0.12)",
        "pass_color": "#059669",
        "pass_border": "rgba(5, 150, 105, 0.35)",
        "fail_bg": "rgba(225, 29, 72, 0.12)",
        "fail_color": "#e11d48",
        "fail_border": "rgba(225, 29, 72, 0.35)",
        "warn_bg": "rgba(217, 119, 6, 0.12)",
        "warn_color": "#d97706",
        "warn_border": "rgba(217, 119, 6, 0.35)",
        "unavailable_bg": "#f1f5f9",
        "unavailable_color": "#64748b",
        "unavailable_border": "#cbd5e1",
        "ladder_bg": "rgba(2, 132, 199, 0.12)",
        "ladder_color": "#0284c7",
        "ladder_border": "rgba(2, 132, 199, 0.35)",
        "replay_bg": "rgba(124, 58, 237, 0.12)",
        "replay_color": "#7c3aed",
        "replay_border": "rgba(124, 58, 237, 0.35)",
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
    """Returns standard Plotly layout configuration honoring the current theme with neon styling."""
    tokens = get_theme_tokens()
    is_dark = tokens["plotly_template"] == "plotly_dark"
    return {
        "template": tokens["plotly_template"],
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(10, 17, 33, 0.65)" if is_dark else "rgba(241, 245, 249, 0.75)",
        "font": {"color": tokens["text"], "family": "Inter, -apple-system, sans-serif"},
        "margin": {"l": 45, "r": 20, "t": 45, "b": 40},
        "xaxis": {
            "gridcolor": "rgba(148, 163, 184, 0.12)" if is_dark else "rgba(100, 116, 139, 0.15)",
            "zerolinecolor": "rgba(56, 189, 248, 0.3)",
        },
        "yaxis": {
            "gridcolor": "rgba(148, 163, 184, 0.12)" if is_dark else "rgba(100, 116, 139, 0.15)",
            "zerolinecolor": "rgba(56, 189, 248, 0.3)",
        },
    }


def generate_theme_css(tokens: Dict[str, Any]) -> str:
    """Generates the full scoped CSS string with neon cyberpunk and glassmorphic styling."""
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

/* Base Root & Typography */
:root {{
    --bg-main: {tokens["bg"]};
    --card-bg: {tokens["card_bg"]};
    --card-border: {tokens["card_border"]};
    --neon-cyan: {tokens.get("neon_cyan", "#00f2fe")};
    --neon-blue: {tokens.get("neon_blue", "#38bdf8")};
    --neon-purple: {tokens.get("neon_purple", "#c084fc")};
    --neon-emerald: {tokens.get("neon_emerald", "#10b981")};
    --neon-amber: {tokens.get("neon_amber", "#f59e0b")};
    --neon-rose: {tokens.get("neon_rose", "#f43f5e")};
}}

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: {tokens["bg"]} !important;
    color: {tokens["text"]} !important;
}}

code, pre, .mono, [data-testid="stMarkdownContainer"] code {{
    font-family: 'JetBrains Mono', monospace !important;
}}

/* Top Header Cyber Aesthetic */
.sq-header {{
    border-bottom: 1px solid rgba(56, 189, 248, 0.2);
    padding: 0.75rem 0 1.0rem 0;
    margin-bottom: 1.25rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(90deg, rgba(56, 189, 248, 0.05) 0%, rgba(129, 140, 248, 0.03) 50%, transparent 100%);
    border-radius: 12px;
    padding-left: 1rem;
    padding-right: 1rem;
}}

.sq-title {{
    font-family: 'Space Grotesk', 'Inter', sans-serif;
    font-size: 1.95rem;
    font-weight: 800;
    background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.03em;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}}

.sq-subtitle {{
    font-size: 0.84rem;
    color: {tokens["text_muted"]};
    margin-top: 0.25rem;
    letter-spacing: 0.04em;
    font-weight: 500;
}}

/* Aerodynamic Cyber HUD Telemetry Bar */
.sq-meta-hud {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.75rem;
    background: rgba(15, 23, 42, 0.75);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(56, 189, 248, 0.22);
    border-radius: 14px;
    padding: 0.85rem 1.2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.45), 0 0 15px -3px rgba(56, 189, 248, 0.1);
    position: relative;
    overflow: hidden;
}}

.sq-meta-hud::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc, #10b981);
}}

.sq-meta-hud-item {{
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}}

.sq-meta-hud-label {{
    color: #64748b;
    font-size: 0.68rem;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.08em;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}}

.sq-meta-hud-value {{
    color: #f1f5f9;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.88rem;
    font-weight: 600;
    word-break: break-all;
}}

/* Neon Glowing Cards with Gradient Borders */
.sq-neon-card {{
    background: rgba(13, 20, 36, 0.82);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(56, 189, 248, 0.16);
    border-radius: 14px;
    padding: 1.15rem 1.25rem;
    margin-bottom: 0.9rem;
    position: relative;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
}}

.sq-neon-card:hover {{
    transform: translateY(-3px);
    border-color: rgba(56, 189, 248, 0.42);
    box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5), 0 0 20px 0 rgba(56, 189, 248, 0.16);
}}

.sq-neon-card-cyan {{ border-top: 3px solid #00f2fe; }}
.sq-neon-card-blue {{ border-top: 3px solid #38bdf8; }}
.sq-neon-card-purple {{ border-top: 3px solid #c084fc; }}
.sq-neon-card-emerald {{ border-top: 3px solid #10b981; }}
.sq-neon-card-amber {{ border-top: 3px solid #f59e0b; }}
.sq-neon-card-rose {{ border-top: 3px solid #f43f5e; }}

.sq-card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}}

.sq-card-label {{
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
}}

.sq-card-metric {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.55rem;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -0.02em;
    margin: 0.2rem 0;
}}

.sq-card-subtext {{
    font-size: 0.74rem;
    color: #64748b;
    line-height: 1.4;
}}

/* Status Badges with Glowing Halo */
.sq-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    transition: all 0.2s ease;
}}

.badge-pass {{
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.4);
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.15);
}}

.badge-fail {{
    background: rgba(244, 63, 94, 0.15);
    color: #fb7185;
    border: 1px solid rgba(244, 63, 94, 0.45);
    box-shadow: 0 0 10px rgba(244, 63, 94, 0.2);
}}

.badge-warn {{
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.4);
    box-shadow: 0 0 10px rgba(245, 158, 11, 0.15);
}}

.badge-ladder {{
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.2) 0%, rgba(129, 140, 248, 0.2) 100%);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.5);
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
    font-weight: 800;
}}

.badge-replay {{
    background: rgba(192, 132, 252, 0.15);
    color: #d8b4fe;
    border: 1px solid rgba(192, 132, 252, 0.4);
    box-shadow: 0 0 10px rgba(192, 132, 252, 0.2);
}}

.badge-unknown {{
    background: rgba(244, 63, 94, 0.2);
    color: #f43f5e;
    border: 2px solid #f43f5e;
    box-shadow: 0 0 15px rgba(244, 63, 94, 0.4);
    font-weight: 800;
}}

.badge-unavail {{
    background: rgba(51, 65, 85, 0.5);
    color: #94a3b8;
    border: 1px solid rgba(71, 85, 105, 0.4);
}}

/* Pulsing Live Dot */
.sq-pulse-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    position: relative;
}}

.sq-pulse-dot.emerald {{
    background-color: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: sq-pulse-anim 2s infinite;
}}

.sq-pulse-dot.cyan {{
    background-color: #00f2fe;
    box-shadow: 0 0 8px #00f2fe;
    animation: sq-pulse-anim 2s infinite;
}}

.sq-pulse-dot.rose {{
    background-color: #f43f5e;
    box-shadow: 0 0 8px #f43f5e;
    animation: sq-pulse-anim 1.5s infinite;
}}

@keyframes sq-pulse-anim {{
    0% {{ transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }}
    70% {{ transform: scale(1); opacity: 1; box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }}
    100% {{ transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
}}

/* Streamlit Button Overrides - Remove Crude Red Boxes */
button[kind="primary"] {{
    background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(56, 189, 248, 0.4) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 4px 14px rgba(2, 132, 199, 0.3) !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

button[kind="primary"]:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(2, 132, 199, 0.45), 0 0 12px rgba(56, 189, 248, 0.3) !important;
    border-color: #38bdf8 !important;
}}

button[kind="secondary"] {{
    background: rgba(15, 23, 42, 0.75) !important;
    color: #cbd5e1 !important;
    border: 1px solid rgba(56, 189, 248, 0.18) !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

button[kind="secondary"]:hover {{
    background: rgba(30, 41, 59, 0.9) !important;
    color: #38bdf8 !important;
    border-color: rgba(56, 189, 248, 0.45) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
}}

/* Sidebar Custom Styling */
section[data-testid="stSidebar"] {{
    background-color: rgba(10, 15, 29, 0.98) !important;
    border-right: 1px solid rgba(56, 189, 248, 0.15) !important;
    box-shadow: 4px 0 25px rgba(0, 0, 0, 0.45) !important;
}}

section[data-testid="stSidebar"] .stButton > button {{
    border-radius: 10px !important;
    padding: 0.55rem 0.85rem !important;
    text-align: left !important;
}}

/* Custom Scrollbars */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}

::-webkit-scrollbar-track {{
    background: rgba(15, 23, 42, 0.6);
}}

::-webkit-scrollbar-thumb {{
    background: rgba(56, 189, 248, 0.25);
    border-radius: 4px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: rgba(56, 189, 248, 0.5);
}}

/* Prominent UNKNOWN Banner */
.sq-unknown-banner {{
    background: linear-gradient(135deg, rgba(244, 63, 94, 0.18) 0%, rgba(15, 23, 42, 0.95) 100%);
    border: 2px solid #f43f5e;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 0 25px rgba(244, 63, 94, 0.25);
}}

.sq-unknown-title {{
    font-size: 1.15rem;
    font-weight: 800;
    color: #f43f5e;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}}

.sq-unknown-desc {{
    color: #cbd5e1;
    font-size: 0.9rem;
    line-height: 1.5;
}}

/* Unavailable Box */
.sq-unavailable-box {{
    background: rgba(15, 23, 42, 0.7);
    border: 1px dashed rgba(148, 163, 184, 0.3);
    border-radius: 12px;
    padding: 1.75rem;
    text-align: center;
    margin: 1.0rem 0;
}}

.sq-unavailable-title {{
    font-size: 1.05rem;
    font-weight: 700;
    color: #fbbf24;
    margin-bottom: 0.5rem;
}}

.sq-unavailable-msg {{
    font-size: 0.85rem;
    color: #94a3b8;
    max-width: 600px;
    margin: 0 auto 0.75rem auto;
    line-height: 1.5;
}}

/* "Why This Decision?" Callout */
.sq-why-callout {{
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(129, 140, 248, 0.04) 100%);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-left: 4px solid #38bdf8;
    padding: 1.0rem 1.25rem;
    border-radius: 0 12px 12px 0;
    margin: 0.75rem 0 1.0rem 0;
}}

.sq-why-title {{
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #38bdf8;
    margin-bottom: 0.35rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}}

.sq-why-text {{
    font-size: 0.88rem;
    color: #cbd5e1;
    line-height: 1.5;
    margin: 0;
}}
</style>
"""


def apply_theme():
    """Injects custom CSS theme into the active Streamlit app."""
    tokens = get_theme_tokens()
    st.markdown(generate_theme_css(tokens), unsafe_allow_html=True)

