"""
SpectralQ Guided Demo Controller.
Provides an interactive, step-by-step walkthrough for evaluators and judges.
Walks through real SDR captures, golden benchmark cases, abstention/UNKNOWN handling,
and synthetic impairment simulation.
"""

from typing import List, Dict, Any
import streamlit as st

from ui.loaders.case_discovery import DiscoveredCase
from ui.loaders.artifact_loader import load_case_artifacts, load_case_observatory
from ui.state.session_state import set_active_case_artifacts, set_workspace
from ui.styles.theme import get_theme_tokens


DEMO_SCENARIOS = [
    {
        "step_num": 1,
        "title": "Real Satellite Capture: Meteor-M2 LRPT",
        "case_match": "Meteor M2",
        "target_workspace": "Mission Control",
        "narrative": (
            "Demonstrates SpectralQ processing genuine, off-air satellite RF signals. "
            "The system detects QPSK transmission at 72k Baud, recovers synchronization, "
            "applies viterbi rate-1/2 decoding and Reed-Solomon(255,223) FEC, reaching Ladder L4/L5."
        ),
        "why_it_matters": "Proves end-to-end operational capability on real-world RF signals without synthetic artifacts.",
        "key_metrics": "Modulation: QPSK | Ladder: L4 | Confidence: >90% | Inner/Outer FEC: Active",
    },
    {
        "step_num": 2,
        "title": "Golden Benchmark: G1 (Clean Baseline QPSK)",
        "case_match": "G1:",
        "target_workspace": "Mission Control",
        "narrative": (
            "Establishes a clean baseline with high SNR AWGN channel. Both Harsh's ML classifier "
            "and Sinchana's rule-based AMC reach 100% agreement on QPSK modulation."
        ),
        "why_it_matters": "Demonstrates perfect consensus alignment and zero penalty application under standard channel conditions.",
        "key_metrics": "Consensus: AGREE | Rule Penalty: 0.00 | Confidence: High",
    },
    {
        "step_num": 3,
        "title": "Golden Benchmark: G2 (8-PSK with Severe CFO)",
        "case_match": "G2:",
        "target_workspace": "Signal Observatory",
        "narrative": (
            "Introduces carrier frequency offset (CFO). Sinchana's blind 4th-power estimator locks onto "
            "the carrier offset and recovers the phase constellation prior to AMC classification."
        ),
        "why_it_matters": "Highlights blind DSP carrier recovery robustness against severe Doppler / LO drift.",
        "key_metrics": "CFO Estimation: Locked | Modulation: 8-PSK | Constellation Stability: High",
    },
    {
        "step_num": 4,
        "title": "Golden Benchmark: G3 (16-QAM in Multipath)",
        "case_match": "G3:",
        "target_workspace": "Modulation & Hypotheses",
        "narrative": (
            "Higher-order 16-QAM modulation under multipath dispersion. Demonstrates Harsh's neural AMC "
            "differentiating multi-level constellations using higher-order cumulants and cyclic moments."
        ),
        "why_it_matters": "Demonstrates discriminative power on complex, multi-amplitude constellations.",
        "key_metrics": "Probability Spread: 16-QAM Dominant | Alternate Candidates Checked",
    },
    {
        "step_num": 5,
        "title": "Golden Benchmark: G4 (FSK with Matrix Interleaving)",
        "case_match": "G4:",
        "target_workspace": "Decoder & Bitstream",
        "narrative": (
            "Continuous-phase FSK transmission passing through Arpit's blind interleaver detection. "
            "The system detects periodicity in the demodulated bitstream and de-interleaves before frame sync."
        ),
        "why_it_matters": "Highlights blind FEC intelligence without requiring pre-shared configuration keys.",
        "key_metrics": "De-interleaver: Active | Sync Word: Detected | Bitstream Entropy: Normalized",
    },
    {
        "step_num": 6,
        "title": "Low-SNR & Abstention: G5 (Deliberate UNKNOWN State)",
        "case_match": "G5:",
        "target_workspace": "Evidence & Decision",
        "narrative": (
            "A low-SNR, ambiguous capture. When confidence drops below operational threshold or rule-ML AMC "
            "diverges, SpectralQ DELIBERATELY ABSTAINS and returns UNKNOWN. It never hallucinates a guess."
        ),
        "why_it_matters": "Crucial NTRO requirement: An honest UNKNOWN is infinitely superior to a catastrophic false-positive.",
        "key_metrics": "Decision: UNKNOWN | Abstained: True | Evidence Check Failures: Logged",
    },
    {
        "step_num": 7,
        "title": "Interactive Signal Lab (Custom Simulation & Validation)",
        "case_match": None,
        "target_workspace": "Signal Lab / Simulation",
        "narrative": (
            "Allows evaluators to synthesize arbitrary signals, tune SNR, CFO, and fading channels, "
            "and watch SpectralQ's blind extraction algorithms validate against known ground truth in real time."
        ),
        "why_it_matters": "Empowers judges to perform live stress-testing on any modulation or SNR condition.",
        "key_metrics": "Ground Truth vs Blind Estimate | Tolerances Checked",
    },
]


def render_guided_demo_banner(cases: List[DiscoveredCase]) -> None:
    """Renders the top banner for Guided Demo Mode with step controls."""
    if not st.session_state.get("guided_demo_active", False):
        return

    tokens = get_theme_tokens()
    step_idx = st.session_state.get("guided_demo_step", 0)
    total_steps = len(DEMO_SCENARIOS)

    # Wrap around or clamp
    step_idx = max(0, min(step_idx, total_steps - 1))
    scen = DEMO_SCENARIOS[step_idx]

    st.markdown(
        f"""
        <div style="background-color:{tokens['ladder_bg']}; border: 2px solid {tokens['primary']}; border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.0rem;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="font-weight:700; color:{tokens['primary']}; font-size:1.05rem;">
                    🎯 GUIDED EVALUATION TOUR — Step {scen['step_num']} of {total_steps}: {scen['title']}
                </div>
                <div>
                    <span class="sq-badge badge-ladder">JUDGES MODE ACTIVE</span>
                </div>
            </div>
            <div style="margin-top:0.4rem; font-size:0.86rem; color:{tokens['text']}; line-height:1.4;">
                {scen['narrative']}
            </div>
            <div style="margin-top:0.35rem; font-size:0.82rem; color:{tokens['text_muted']};">
                💡 <b>Why This Matters:</b> {scen['why_it_matters']}<br>
                🔍 <b>Key Highlights:</b> <code>{scen['key_metrics']}</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Controller buttons
    c_btn1, c_btn2, c_btn3, c_btn4 = st.columns([1, 1, 1, 3])
    with c_btn1:
        if st.button("◀️ Previous Step", disabled=(step_idx == 0), use_container_width=True):
            st.session_state["guided_demo_step"] = step_idx - 1
            _navigate_scenario(cases, DEMO_SCENARIOS[step_idx - 1])
            st.rerun()

    with c_btn2:
        if st.button("Next Step ▶️", disabled=(step_idx == total_steps - 1), type="primary", use_container_width=True):
            st.session_state["guided_demo_step"] = step_idx + 1
            _navigate_scenario(cases, DEMO_SCENARIOS[step_idx + 1])
            st.rerun()

    with c_btn3:
        if st.button("❌ Exit Tour", use_container_width=True):
            st.session_state["guided_demo_active"] = False
            st.rerun()


def _navigate_scenario(cases: List[DiscoveredCase], scenario: Dict[str, Any]) -> None:
    """Switches workspace and loads matching case for scenario."""
    target_ws = scenario["target_workspace"]
    set_workspace(target_ws)

    case_match = scenario["case_match"]
    if case_match:
        # Find matching case
        for c in cases:
            if case_match.lower() in c.name.lower() or case_match.lower() in c.case_id.lower():
                norm_res, norm_ana, norm_dec, prov = load_case_artifacts(c)
                obs_artifacts = load_case_observatory(c, norm_ana, norm_res)
                set_active_case_artifacts(
                    result=norm_res,
                    analysis=norm_ana,
                    decoder=norm_dec,
                    provenance=prov,
                    is_replay=True,
                    artifacts=obs_artifacts,
                )
                st.session_state["current_case_name"] = c.name
                break
