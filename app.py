"""
SpectralQ Streamlit Main Application.
Production GUI & User-Facing Intelligence Interface for SIH26147 (NTRO).
Owner: Himanshu (Streamlit GUI, visualization, evidence-bundle presentation).

Strict Architectural Invariant:
Strictly consumes backend contracts and genuine RF captures.
Zero DSP, zero classifier training, zero confidence mathematics,
and zero decoder logic resides in the GUI layer.
"""

from pathlib import Path
from typing import Optional
import streamlit as st

# Setup wide page config
st.set_page_config(
    page_title="SpectralQ — Blind RF Signal Analysis System",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.styles import apply_theme, get_theme_tokens
from ui.state import init_session_state, set_active_case_artifacts, set_workspace, WORKSPACES
from ui.loaders import discover_available_cases, load_case_artifacts, load_case_observatory, DiscoveredCase
from ui.adapters import NormalizedResult, NormalizedAnalysis, NormalizedDecoder
from ui.components import (
    render_header,
    render_sidebar,
    render_mission_control,
    render_signal_observatory,
    render_modulation_hypotheses,
    render_decoder_bitstream,
    render_evidence_decision,
    render_provenance_export,
    render_signal_lab,
    render_guided_demo_banner,
    render_wideband_scanner,
    render_run_trace,
    render_synthetic_signal_generator,
)
from spectralq.visualization.artifacts import ObservatoryArtifacts


# -----------------------------------------------------------------------------
# 1. State & Theme Initialization
# -----------------------------------------------------------------------------
init_session_state()
apply_theme()


# -----------------------------------------------------------------------------
# 2. Case Discovery & Pre-loading
# -----------------------------------------------------------------------------
@st.cache_data
def get_discovered_cases_cached():
    return discover_available_cases()


cases = get_discovered_cases_cached()

# Ensure default case is loaded if state is fresh
if st.session_state.get("cached_result") is None and cases:
    default_case = cases[0]
    for c in cases:
        if "Meteor M2" in c.name or "meteor" in c.case_id.lower():
            default_case = c
            break

    norm_res, norm_ana, norm_dec, prov = load_case_artifacts(default_case)
    obs_artifacts = load_case_observatory(default_case, norm_ana, norm_res)
    set_active_case_artifacts(
        result=norm_res,
        analysis=norm_ana,
        decoder=norm_dec,
        provenance=prov,
        is_replay=True,
        artifacts=obs_artifacts,
    )
    st.session_state["current_case_name"] = default_case.name


# -----------------------------------------------------------------------------
# 3. Sidebar Control Center
# -----------------------------------------------------------------------------
render_sidebar(cases)


# -----------------------------------------------------------------------------
# 4. Main Body: Top Header & Guided Demo Controller
# -----------------------------------------------------------------------------
res: Optional[NormalizedResult] = st.session_state.get("cached_result")
ana: Optional[NormalizedAnalysis] = st.session_state.get("cached_analysis")
dec: Optional[NormalizedDecoder] = st.session_state.get("cached_decoder")
artifacts: Optional[ObservatoryArtifacts] = st.session_state.get("observatory_artifacts")
prov: dict = st.session_state.get("provenance_info", {})
is_replay: bool = st.session_state.get("is_replay", True)
current_ws: str = st.session_state.get("active_workspace", "Mission Control")

# Guided demo top banner (if active)
render_guided_demo_banner(cases)

# Standard executive header
render_header(
    result=res,
    analysis=ana,
    source_filename=st.session_state.get("current_case_name"),
    is_replay=is_replay,
)


# -----------------------------------------------------------------------------
# 5. Workspace Routing
# -----------------------------------------------------------------------------
if current_ws == "Mission Control":
    render_mission_control(result=res, analysis=ana, decoder=dec)

elif current_ws == "Signal Observatory":
    render_signal_observatory(artifacts=artifacts, analysis=ana, result=res, decoder=dec)


elif current_ws == "Modulation & Hypotheses":
    render_modulation_hypotheses(result=res, analysis=ana)

elif current_ws == "Decoder & Bitstream":
    render_decoder_bitstream(decoder=dec, result=res, analysis=ana)

elif current_ws == "Evidence & Decision":
    render_evidence_decision(result=res, analysis=ana, decoder=dec)

elif current_ws == "Provenance & Export":
    render_provenance_export(
        result=res,
        analysis=ana,
        decoder=dec,
        artifacts=artifacts,
        provenance=prov,
    )

elif current_ws == "Wideband Scanner":
    render_wideband_scanner()

elif current_ws == "Signal Lab / Simulation":
    render_signal_lab()

elif current_ws == "🧬 Synthetic Generator":
    render_synthetic_signal_generator()

elif current_ws == "Run Trace":
    render_run_trace(result=res, analysis=ana, decoder=dec, provenance=prov)

else:
    st.error(f"Unknown workspace: {current_ws}")
    if st.button("Return to Mission Control"):
        set_workspace("Mission Control")
        st.rerun()
