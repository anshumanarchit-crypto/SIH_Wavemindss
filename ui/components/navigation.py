"""
SpectralQ Navigation & Sidebar Control Center.
Coordinates workspace selection, case discovery, live ingest, theme toggling,
and guided demo mode controls.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st

from ui.loaders.case_discovery import DiscoveredCase
from ui.loaders.artifact_loader import load_case_artifacts, load_case_observatory
from ui.adapters import adapt_result, adapt_analysis, adapt_decoder
from ui.state.session_state import set_active_case_artifacts, set_workspace, WORKSPACES
from ui.styles.theme import get_current_theme_name


def render_sidebar(cases: List[DiscoveredCase]) -> None:
    """Renders the left sidebar control center."""
    st.sidebar.markdown("## 📡 SpectralQ Control")
    st.sidebar.caption("PS: SIH26147 (NTRO) • Production Interface")

    # 1. Theme Toggle
    current_theme = get_current_theme_name()
    col_t1, col_t2 = st.sidebar.columns([1, 1])
    with col_t1:
        st.caption(f"Theme: **{current_theme.upper()}**")
    with col_t2:
        new_theme = "light" if current_theme == "dark" else "dark"
        if st.button(f"☀️/🌙 Toggle", key="theme_toggle_btn", use_container_width=True):
            st.session_state["theme"] = new_theme
            st.rerun()

    st.sidebar.markdown("---")

    # 2. Guided Demo Mode Toggle
    is_demo = st.session_state.get("guided_demo_active", False)
    demo_toggle = st.sidebar.checkbox(
        "🎯 Guided Demo Mode (Judges)",
        value=is_demo,
        help="Interactive guided tour walking through real captures, golden cases, and abstention scenarios.",
    )
    if demo_toggle != is_demo:
        st.session_state["guided_demo_active"] = demo_toggle
        st.rerun()

    # 3. Workspace Navigation Rail
    st.sidebar.markdown("### 🗂️ Workspaces")
    current_ws = st.session_state.get("active_workspace", "Mission Control")

    workspace_icons = {
        "Mission Control": "🚀",
        "Signal Observatory": "🔭",
        "Modulation & Hypotheses": "🎯",
        "Decoder & Bitstream": "🔓",
        "Evidence & Decision": "⚖️",
        "Provenance & Export": "📦",
        "Signal Lab / Simulation": "🔬",
    }

    for ws in WORKSPACES:
        icon = workspace_icons.get(ws, "📌")
        btn_type = "primary" if ws == current_ws else "secondary"
        if st.sidebar.button(
            f"{icon} {ws}",
            key=f"nav_btn_{ws}",
            type=btn_type,
            use_container_width=True,
        ):
            if current_ws != ws:
                st.session_state["active_workspace"] = ws
                st.rerun()

    st.sidebar.markdown("---")

    # 4. Ingest / Replay Case Selection
    mode = st.sidebar.radio(
        "Ingest Mode:",
        ["Replay / Case Explorer", "Live SDR / File Ingest"],
        index=0 if st.session_state.get("is_replay", True) else 1,
    )

    case_map = {c.name: c for c in cases}
    case_names = list(case_map.keys())

    if mode == "Replay / Case Explorer":
        st.sidebar.markdown("### 📡 Target Capture")
        default_idx = 0
        for idx, name in enumerate(case_names):
            if "Meteor M2" in name or "G1:" in name:
                default_idx = idx
                break

        current_selected = st.session_state.get("current_case_name", case_names[default_idx] if case_names else "")
        if current_selected in case_names:
            default_idx = case_names.index(current_selected)

        selected_case_name = st.sidebar.selectbox(
            "Select Capture Case:",
            case_names,
            index=default_idx,
            key="case_selector_box",
        )
        selected_case = case_map[selected_case_name]

        st.sidebar.info(f"**Category:** {selected_case.category}\n\n{selected_case.description}")

        needs_load = (
            st.session_state.get("cached_result") is None
            or st.session_state.get("current_case_name") != selected_case.name
        )

        if st.sidebar.button("🔄 Load Case Telemetry", type="primary", use_container_width=True) or needs_load:
            with st.spinner("Loading case artifacts & telemetry contracts..."):
                norm_res, norm_ana, norm_dec, prov = load_case_artifacts(selected_case)
                obs_artifacts = load_case_observatory(selected_case, norm_ana)
                set_active_case_artifacts(
                    result=norm_res,
                    analysis=norm_ana,
                    decoder=norm_dec,
                    provenance=prov,
                    is_replay=True,
                    artifacts=obs_artifacts,
                )
                st.session_state["current_case_name"] = selected_case.name
                st.rerun()

    else:
        # Live File Ingest Mode
        st.sidebar.markdown("### 📥 Live Signal Ingest")
        st.sidebar.caption("Upload raw .cf32, .iq, .wav, or verified JSON contract.")

        uploaded_file = st.sidebar.file_uploader(
            "Upload Signal File",
            type=["cf32", "iq", "wav", "json", "npy"],
            help="Upload raw I/Q samples, WAV audio, or verified JSON contract",
            key="live_uploader",
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            st.sidebar.success(f"Loaded: `{uploaded_file.name}` ({len(file_bytes)/1024:.1f} KB)")
            st.sidebar.caption(f"SHA-256: `{sha256_hash[:16]}...`")

            if uploaded_file.name.endswith(".json"):
                if st.sidebar.button("⚡ Parse & Verify Contract", type="primary", use_container_width=True):
                    try:
                        data = json.loads(file_bytes.decode("utf-8"))
                        res_obj = None
                        ana_obj = None
                        dec_obj = None
                        prov_info = {
                            "uploaded_file": uploaded_file.name,
                            "sha256": sha256_hash,
                            "size_bytes": len(file_bytes),
                        }
                        if "top_hypothesis" in data:
                            res_obj = adapt_result(data)
                        elif "bursts" in data and "estimates" in data:
                            ana_obj = adapt_analysis(data)
                        elif "fec_used" in data or "decoder_status" in data:
                            dec_obj = adapt_decoder(data)

                        from spectralq.visualization.artifacts import prepare_observatory_artifacts
                        obs_artifacts = prepare_observatory_artifacts(
                            analysis=ana_obj,
                            source_mode="LIVE UPLOAD",
                        )
                        set_active_case_artifacts(res_obj, ana_obj, dec_obj, prov_info, is_replay=False, artifacts=obs_artifacts)
                        st.session_state["current_case_name"] = uploaded_file.name
                        st.sidebar.success("Contract parsed and verified against schema!")
                        st.rerun()
                    except Exception as exc:
                        st.sidebar.error(f"Contract Schema Error: {exc}")
            else:
                # Raw IQ, CF32, or WAV file
                st.sidebar.markdown("**Signal Ingest & Sampling Rate:**")
                is_wav = uploaded_file.name.lower().endswith(".wav")
                user_fs = None
                fs_source_label = "HEADER"

                if is_wav:
                    st.sidebar.info("🎵 WAV file: Sampling rate will be read directly from WAV RIFF header.")
                    fs_source_label = "HEADER"
                else:
                    st.sidebar.caption("Headerless raw IQ/CF32 requires sampling rate specification:")
                    user_fs = st.sidebar.number_input(
                        "Sampling Rate (Hz):",
                        min_value=1_000.0,
                        max_value=1_000_000_000.0,
                        value=100_000.0,
                        step=10_000.0,
                        format="%.0f",
                        help="Raw binary files carry no intrinsic sampling rate header. Provide the hardware SDR sample rate.",
                    )
                    fs_source_label = "USER PROVIDED"

                if st.sidebar.button("🚀 Analyze Signal via Backend", type="primary", use_container_width=True):
                    with st.spinner("Invoking SpectralQ backend pipeline runner..."):
                        scratch_dir = Path("data") / "scratch"
                        scratch_dir.mkdir(parents=True, exist_ok=True)
                        tmp_cap = scratch_dir / uploaded_file.name
                        with open(tmp_cap, "wb") as f:
                            f.write(file_bytes)

                        from spectralq.pipeline.runner import run
                        from spectralq.visualization.artifacts import prepare_observatory_artifacts
                        try:
                            pipe_out = run(capture_path=str(tmp_cap), mode="live")
                            norm_res = adapt_result(pipe_out.result) if pipe_out.result else None
                            norm_ana = adapt_analysis(pipe_out.analysis) if pipe_out.analysis else None
                            norm_dec = adapt_decoder(pipe_out.decoder) if pipe_out.decoder else None

                            obs_artifacts = prepare_observatory_artifacts(
                                capture_path=str(tmp_cap),
                                analysis=norm_ana,
                                fs_hz=norm_ana.fs_hz if norm_ana else (user_fs or 100_000.0),
                                source_mode="LIVE SDR CAPTURE",
                            )
                            prov = {
                                "uploaded_file": uploaded_file.name,
                                "sha256": sha256_hash,
                                "size_bytes": len(file_bytes),
                                "fs_source": fs_source_label,
                            }
                            set_active_case_artifacts(
                                norm_res,
                                norm_ana,
                                norm_dec,
                                prov,
                                is_replay=False,
                                artifacts=obs_artifacts,
                            )
                            st.session_state["current_case_name"] = uploaded_file.name
                            st.sidebar.success("Analysis complete!")
                            st.rerun()
                        except Exception as exc:
                            st.sidebar.error("Analysis failed. Backend execution error.")
                            with st.sidebar.expander("🛠️ Diagnostics", expanded=True):
                                st.write(f"**Error:** `{type(exc).__name__}`")
                                st.code(str(exc))
