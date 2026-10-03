"""
SpectralQ Guided Demo Controller.
Phase 43: Evaluator Tour orchestrator across the 10 canonical workspaces.
Ensures zero fake data injection while guiding evaluators smoothly through:
1. Mission Control
2. Signal Observatory
3. Modulation
4. Hypothesis
5. Decoder
6. Evidence
7. UNKNOWN
8. Wideband
9. Simulation
10. Export
"""

from typing import List, Dict, Any
import streamlit as st
from ui.state.session_state import set_workspace


DEMO_STEPS: List[Dict[str, str]] = [
    {
        "title": "1. Mission Control",
        "workspace": "Mission Control",
        "badge": "EXECUTIVE TELEMETRY",
        "description": "Executive dashboard showing live signal ingest, top modulation hypothesis, Evidence Ladder level (L1–L5), and cryptographic provenance.",
        "evaluator_focus": "Notice that confidence combines real feature consistency, rule/ML consensus, and decoder verification — no arbitrary multipliers.",
    },
    {
        "title": "2. Signal Observatory",
        "workspace": "Signal Observatory",
        "badge": "RF OBSERVABILITY",
        "description": "Interactive RF physics dashboard: calibrated IQ constellation, power spectral density (PSD), waterfall, and eye diagrams.",
        "evaluator_focus": "Observe real IQ samples and baud/CFO/SNR parameter estimates with explicit confidence intervals and estimation methods.",
    },
    {
        "title": "3. Modulation & Feature Space",
        "workspace": "Modulation & Hypotheses",
        "badge": "AMC & CUMULANTS",
        "description": "Higher-Order Statistics (HOS C20–C80), constellation clustering metrics, and cross-window stability.",
        "evaluator_focus": "Inspect deterministic rule-based AMC alongside the trained Random Forest classifier with feature schema validation.",
    },
    {
        "title": "4. Hypothesis Search Space",
        "workspace": "Modulation & Hypotheses",
        "badge": "CANDIDATE RANKING",
        "description": "Cross-product search over Modulation x Interleaver x FEC code families.",
        "evaluator_focus": "Hypotheses are ranked on physical consistency, demodulation success, and FEC syndrome checks — not raw softmax probabilities.",
    },
    {
        "title": "5. Receiver & Decoder Bitstream",
        "workspace": "Decoder & Bitstream",
        "badge": "FEC & CRC INTEGRITY",
        "description": "Costas loop carrier recovery, Gardner timing recovery, deinterleaving, and forward error correction.",
        "evaluator_focus": "Inspect genuine Gallager LDPC syndrome checks (H*c = 0), Viterbi/RS telemetry, and strict CRC semantics (NOT_RUN vs PASS/FAIL).",
    },
    {
        "title": "6. Evidence & Decision Ladder",
        "workspace": "Evidence & Decision",
        "badge": "DEFENSIBILITY LADDER",
        "description": "Transparent multi-modal evidence ledger proving every claim made by the system.",
        "evaluator_focus": "Review the formal ladder justification: L1 (detected) through L5 (dual independent verification). Every entry has source and method.",
    },
    {
        "title": "7. Honest Abstention (UNKNOWN)",
        "workspace": "Evidence & Decision",
        "badge": "SAFE ABSTENTION",
        "description": "When SNR is degraded or pure noise is encountered, the system abstains rather than emitting high-confidence hallucinations.",
        "evaluator_focus": "Switch to G7 (near-threshold) or G10 (pure noise) in the sidebar to see explicit UNKNOWN flags and detailed reason telemetry.",
    },
    {
        "title": "8. Wideband Multi-Emission Scanner",
        "workspace": "Wideband Scanner",
        "badge": "SPECTRAL SEARCH",
        "description": "Autonomous wideband energy detector, spectral segmentation, and per-emission carrier isolation.",
        "evaluator_focus": "Inspect spectral channelization and individual emission parameter extraction across wideband bursts.",
    },
    {
        "title": "9. Signal Lab / Simulation",
        "workspace": "Signal Lab / Simulation",
        "badge": "CONTROLLED BENCHMARK",
        "description": "Interactive synthetic RF generator with compound channel impairments (CFO, timing jitter, IQ imbalance, AWGN).",
        "evaluator_focus": "Generate custom impaired bursts and run them blind through the live pipeline with strict truth isolation.",
    },
    {
        "title": "10. Evidence Export & Forensics Bundle",
        "workspace": "Provenance & Export",
        "badge": "AUDIT REPRODUCIBILITY",
        "description": "One-click export of the complete cryptographic evidence package (.zip) including SigMF metadata, contracts, and SHA-256 manifest.",
        "evaluator_focus": "Verify that all 9 contracts, plots, and raw hashes are verified before the ZIP archive is offered for download.",
    },
]


def start_guided_demo():
    """Activates guided demo starting at Step 0."""
    st.session_state["guided_demo_active"] = True
    st.session_state["guided_demo_step"] = 0
    set_workspace(DEMO_STEPS[0]["workspace"])


def stop_guided_demo():
    """Deactivates guided demo."""
    st.session_state["guided_demo_active"] = False


def next_demo_step():
    """Advances to next demo step."""
    step = st.session_state.get("guided_demo_step", 0)
    if step < len(DEMO_STEPS) - 1:
        step += 1
        st.session_state["guided_demo_step"] = step
        set_workspace(DEMO_STEPS[step]["workspace"])


def prev_demo_step():
    """Returns to previous demo step."""
    step = st.session_state.get("guided_demo_step", 0)
    if step > 0:
        step -= 1
        st.session_state["guided_demo_step"] = step
        set_workspace(DEMO_STEPS[step]["workspace"])


def render_guided_demo_banner():
    """Renders the top interactive tour navigation banner if demo is active."""
    if not st.session_state.get("guided_demo_active", False):
        return

    step_idx = st.session_state.get("guided_demo_step", 0)
    step = DEMO_STEPS[step_idx]

    b_col1, b_col2, b_col3, b_col4 = st.columns([4, 1.2, 1.2, 1.0])
    with b_col1:
        st.markdown(
            f"""
            <div style="background: rgba(30, 41, 59, 0.95); border: 1px solid #38bdf8; border-radius: 8px; padding: 0.6rem 1rem; margin-bottom: 0.8rem;">
                <div style="display:flex; align-items:center; gap:0.6rem;">
                    <span style="background:#38bdf8; color:#0f172a; font-weight:800; font-size:0.75rem; padding:2px 8px; border-radius:4px;">
                        TOUR STEP {step_idx + 1}/10
                    </span>
                    <span style="font-weight:700; color:#f8fafc; font-size:0.95rem;">{step['title']}</span>
                    <span style="font-size:0.72rem; color:#94a3b8; border:1px solid #475569; padding:1px 6px; border-radius:3px;">{step['badge']}</span>
                </div>
                <div style="font-size:0.82rem; color:#cbd5e1; margin-top:0.3rem;">
                    {step['description']}
                </div>
                <div style="font-size:0.78rem; color:#38bdf8; font-style:italic; margin-top:0.2rem;">
                    🔍 <strong>Evaluator Focus:</strong> {step['evaluator_focus']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with b_col2:
        if step_idx > 0:
            if st.button("⬅️ Previous", key="demo_prev", use_container_width=True):
                prev_demo_step()
                st.rerun()

    with b_col3:
        if step_idx < len(DEMO_STEPS) - 1:
            if st.button("Next ➡️", key="demo_next", type="primary", use_container_width=True):
                next_demo_step()
                st.rerun()

    with b_col4:
        if st.button("Exit Tour ✕", key="demo_exit", use_container_width=True):
            stop_guided_demo()
            st.rerun()
