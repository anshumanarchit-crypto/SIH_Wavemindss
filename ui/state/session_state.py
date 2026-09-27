"""
UI State Management.
Safely coordinates st.session_state keys without holding massive arrays in memory.
Tracks current capture, loaded artifacts, analysis mode, and selected stages.
"""

from typing import Any, Dict, Optional
import streamlit as st
from ui.adapters.result_adapter import NormalizedResult
from ui.adapters.analysis_adapter import NormalizedAnalysis
from ui.adapters.decoder_adapter import NormalizedDecoder


def init_session_state():
    """Initializes standard session state keys if not already present."""
    defaults = {
        "current_capture_id": "METEOR_M2_LRPT",
        "current_case_name": "Real: Meteor M2 Lrpt",
        "analysis_mode": "replay",  # "replay" or "live"
        "selected_stage": "result",
        "selected_burst": 0,
        "selected_hypothesis": None,
        "is_replay": True,
        "cached_result": None,
        "cached_analysis": None,
        "cached_decoder": None,
        "provenance_info": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def set_active_case_artifacts(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
    decoder: Optional[NormalizedDecoder],
    provenance: Dict[str, str],
    is_replay: bool = True,
):
    """Sets the active case artifacts into session state."""
    st.session_state["cached_result"] = result
    st.session_state["cached_analysis"] = analysis
    st.session_state["cached_decoder"] = decoder
    st.session_state["provenance_info"] = provenance
    st.session_state["is_replay"] = is_replay
    if result:
        st.session_state["current_capture_id"] = result.capture_id
