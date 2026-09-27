"""
SpectralQ UI Styling & Theme Engine.
Provides engineering-grade, high-density telemetry styling for the Streamlit dashboard.
"""

import streamlit as st


SPECTRALQ_CSS = """
<style>
/* SpectralQ Global Engineering Theme */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

code, pre, .mono {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Header Banner */
.sq-header {
    border-bottom: 2px solid #30363d;
    padding-bottom: 0.75rem;
    margin-bottom: 1.25rem;
}

.sq-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #58a6ff;
    letter-spacing: -0.02em;
    margin: 0;
}

.sq-subtitle {
    font-size: 0.85rem;
    color: #8b949e;
    margin-top: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Metadata Bar */
.sq-meta-bar {
    display: flex;
    gap: 1.5rem;
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 0.6rem 1rem;
    margin-bottom: 1.25rem;
    font-size: 0.82rem;
}

.sq-meta-item {
    display: flex;
    flex-direction: column;
}

.sq-meta-label {
    color: #8b949e;
    font-size: 0.7rem;
    text-transform: uppercase;
    font-weight: 600;
}

.sq-meta-value {
    color: #f0f6fc;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
}

/* Metric Cards */
.sq-card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.75rem;
    position: relative;
}

.sq-card-title {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #8b949e;
    margin-bottom: 0.25rem;
    font-weight: 600;
}

.sq-card-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: #f0f6fc;
    font-family: 'JetBrains Mono', monospace;
}

.sq-card-sub {
    font-size: 0.75rem;
    color: #8b949e;
    margin-top: 0.2rem;
}

/* Status Badges */
.sq-badge {
    display: inline-block;
    padding: 0.18rem 0.5rem;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.badge-pass { background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #238636; }
.badge-fail { background-color: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #da3633; }
.badge-unavail { background-color: rgba(210, 153, 34, 0.15); color: #d29922; border: 1px solid #9e6a03; }
.badge-notrun { background-color: rgba(139, 148, 158, 0.15); color: #8b949e; border: 1px solid #484f58; }
.badge-ladder { background-color: rgba(88, 166, 255, 0.15); color: #58a6ff; border: 1px solid #1f6feb; }
.badge-replay { background-color: rgba(188, 140, 255, 0.15); color: #bc8cff; border: 1px solid #8957e5; }
.badge-unknown { background-color: rgba(248, 81, 73, 0.25); color: #ff7b72; border: 1px solid #f85149; }

/* UNKNOWN Banner */
.sq-unknown-banner {
    background-color: rgba(248, 81, 73, 0.08);
    border: 2px solid #f85149;
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1.5rem;
}

.sq-unknown-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #ff7b72;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.sq-unknown-desc {
    color: #c9d1d9;
    font-size: 0.9rem;
    line-height: 1.45;
}

/* Pipeline Stage Stepper */
.sq-stepper {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1.25rem;
}

.sq-step {
    flex: 1;
    min-width: 110px;
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 5px;
    padding: 0.5rem 0.6rem;
    text-align: center;
}

.sq-step.active {
    border-color: #58a6ff;
    background-color: rgba(88, 166, 255, 0.05);
}

.sq-step-name {
    font-size: 0.72rem;
    color: #8b949e;
    font-weight: 600;
    text-transform: uppercase;
}

.sq-step-status {
    font-size: 0.85rem;
    font-weight: 700;
    margin-top: 0.2rem;
}
</style>
"""


def apply_theme():
    """Injects custom CSS theme into the active Streamlit app."""
    st.markdown(SPECTRALQ_CSS, unsafe_allow_html=True)
