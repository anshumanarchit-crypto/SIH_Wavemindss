"""
SpectralQ Navigation & Sidebar Control Center.
Coordinates workspace selection, case discovery, live ingest,
and guided demo mode controls with a high-end cyber glassmorphic interface.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st

from ui.loaders.case_discovery import DiscoveredCase
from ui.loaders.artifact_loader import load_case_artifacts, load_case_observatory
from ui.adapters import adapt_result, adapt_analysis, adapt_decoder
from ui.state.session_state import set_active_case_artifacts, set_workspace, WORKSPACES, EXTENDED_WORKSPACES
from ui.styles.theme import get_theme_tokens


def render_sidebar(cases: List[DiscoveredCase]) -> None:
    """Renders the left sidebar control center with an ultra-premium layout."""
    tokens = get_theme_tokens()

    # -------------------------------------------------------------------------
    # 1. Brand Header with Cyber Pulse Badge
    # -------------------------------------------------------------------------
    st.sidebar.markdown(
        f"""
        <div style="padding: 0.5rem 0.2rem 1.0rem 0.2rem; border-bottom: 1px solid rgba(56, 189, 248, 0.2); margin-bottom: 1.0rem;">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.25rem;">
                <div style="font-family:'Space Grotesk', sans-serif; font-size:1.35rem; font-weight:800;
                     background:linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
                     -webkit-background-clip:text; -webkit-text-fill-color:transparent; letter-spacing:-0.02em;">
                    SPECTRALQ
                </div>
                <span class="sq-pulse-dot emerald" title="System Operational • Defense Grade"></span>
            </div>
            <div style="font-size:0.68rem; font-weight:700; color:#64748b; letter-spacing:0.08em; text-transform:uppercase;">
                SpectralQ Defense v2.0
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # 2. Workspace Navigation Rail (Now at Top with High-Tech Icons)
    # -------------------------------------------------------------------------
    st.sidebar.markdown(
        """
        <div style="font-size:0.72rem; font-weight:800; color:#38bdf8; letter-spacing:0.1em;
             text-transform:uppercase; margin-bottom:0.6rem; display:flex; align-items:center; gap:0.4rem;">
            <span>🧭</span> WORKSPACES
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_ws = st.session_state.get("active_workspace", "Mission Control")

    workspace_meta = {
        "Mission Control": {
            "icon": "💠",
            "tag": "EXECUTIVE",
            "desc": "Executive dashboard, ladder level & consensus overview",
        },
        "Signal Observatory": {
            "icon": "📡",
            "tag": "RF FORENSICS",
            "desc": "Raw I/Q waveforms, frequency spectrum & physical parameters",
        },
        "Modulation & Hypotheses": {
            "icon": "⚡",
            "tag": "AMC NEURAL",
            "desc": "Candidate probability distribution & cumulant distance matrix",
        },
        "Decoder & Bitstream": {
            "icon": "🔓",
            "tag": "FEC ENGINE",
            "desc": "Multi-stage Viterbi/Reed-Solomon decoding & CRC verification",
        },
        "Evidence & Decision": {
            "icon": "⚖️",
            "tag": "CONSENSUS",
            "desc": "Immutable evidence ledger & honest UNKNOWN abstention",
        },
        "Provenance & Export": {
            "icon": "📦",
            "tag": "SIGMF CRYPTO",
            "desc": "Cryptographic provenance chain & SigMF dataset export",
        },
        "Signal Lab / Simulation": {
            "icon": "🧪",
            "tag": "TESTBENCH",
            "desc": "Simulate RF channels with Rayleigh/Rician impairments",
        },
        "🧬 Synthetic Generator": {
            "icon": "🧬",
            "tag": "SYNTH RF",
            "desc": "Generate full benchmark suite across all pipeline permutations",
        },
    }

    # Render primary workspaces with clean styling
    for ws in WORKSPACES:
        meta = workspace_meta.get(ws, {"icon": "📌", "tag": "CORE", "desc": ws})
        is_active = (ws == current_ws)
        btn_type = "primary" if is_active else "secondary"
        
        # Display full name on button; Streamlit tooltip provides description
        if st.sidebar.button(
            f"{meta['icon']}  {ws}",
            key=f"nav_btn_{ws}",
            type=btn_type,
            use_container_width=True,
            help=f"{meta['tag']} • {meta['desc']}",
        ):
            if current_ws != ws:
                st.session_state["active_workspace"] = ws
                st.rerun()

    # Specialized Analytical Modules (Scanner & Trace)
    st.sidebar.markdown(
        """
        <div style="font-size:0.68rem; font-weight:800; color:#64748b; letter-spacing:0.08em;
             text-transform:uppercase; margin:0.6rem 0 0.35rem 0;">
            SPECIALIZED TOOLS
        </div>
        """,
        unsafe_allow_html=True,
    )
    c_s1, c_s2 = st.sidebar.columns(2)
    with c_s1:
        is_wb = (current_ws == "Wideband Scanner")
        if c_s1.button("🔍 Scanner", key="nav_btn_wb", type="primary" if is_wb else "secondary", use_container_width=True, help="Wideband Spectral Scanner"):
            st.session_state["active_workspace"] = "Wideband Scanner"
            st.rerun()
    with c_s2:
        is_trace = (current_ws == "Run Trace")
        if c_s2.button("⏱️ Trace", key="nav_btn_trace", type="primary" if is_trace else "secondary", use_container_width=True, help="Execution Diagnostics & Latency Trace"):
            st.session_state["active_workspace"] = "Run Trace"
            st.rerun()

    st.sidebar.markdown("---")

    # -------------------------------------------------------------------------
    # 3. Ingest Mode Portion (Upgraded Cyber Glass Card)
    # -------------------------------------------------------------------------
    st.sidebar.markdown(
        """
        <div style="font-size:0.72rem; font-weight:800; color:#38bdf8; letter-spacing:0.1em;
             text-transform:uppercase; margin-bottom:0.6rem; display:flex; align-items:center; gap:0.4rem;">
            <span>📥</span> SIGNAL INGESTION
        </div>
        """,
        unsafe_allow_html=True,
    )

    is_replay_current = st.session_state.get("is_replay", True)
    mode_options = ["Replay / Case Explorer", "Live SDR / File Ingest"]
    mode_idx = 0 if is_replay_current else 1

    mode = st.sidebar.radio(
        "Ingest Mode:",
        mode_options,
        index=mode_idx,
        label_visibility="collapsed",
        key="ingest_mode_selector",
    )

    case_map = {c.name: c for c in cases}
    case_names = list(case_map.keys())

    if mode == "Replay / Case Explorer":
        default_idx = 0
        for idx, name in enumerate(case_names):
            if "Meteor M2" in name or "G1:" in name:
                default_idx = idx
                break

        current_selected = st.session_state.get("current_case_name", case_names[default_idx] if case_names else "")
        if current_selected in case_names:
            default_idx = case_names.index(current_selected)

        selected_case_name = st.sidebar.selectbox(
            "Select Target Capture:",
            case_names,
            index=default_idx,
            key="case_selector_box",
            help="Select verified RF benchmark or real satellite pass",
        )
        selected_case = case_map[selected_case_name]

        # Cyber Glass Card for Case Details
        st.sidebar.markdown(
            f"""
            <div style="background:rgba(15, 23, 42, 0.65); border:1px solid rgba(56, 189, 248, 0.2);
                 border-left:3px solid #38bdf8; border-radius:10px; padding:0.65rem 0.85rem; margin:0.5rem 0;">
                <div style="font-size:0.65rem; color:#38bdf8; font-weight:700; text-transform:uppercase; letter-spacing:0.06em;">
                    {selected_case.category}
                </div>
                <div style="font-size:0.75rem; color:#cbd5e1; margin-top:2px; line-height:1.35;">
                    {selected_case.description}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        needs_load = (
            st.session_state.get("cached_result") is None
            or st.session_state.get("current_case_name") != selected_case.name
        )

        if st.sidebar.button("⚡ Load Telemetry Contracts", type="primary", use_container_width=True) or needs_load:
            with st.spinner("Synchronizing telemetry contracts..."):
                norm_res, norm_ana, norm_dec, prov = load_case_artifacts(selected_case)
                obs_artifacts = load_case_observatory(selected_case, norm_ana, norm_res)
                set_active_case_artifacts(
                    result=norm_res,
                    analysis=norm_ana,
                    decoder=norm_dec,
                    provenance=prov,
                    is_replay=True,
                    artifacts=obs_artifacts,
                )
                st.session_state["current_case_name"] = selected_case.name
                if selected_case.raw_path and selected_case.raw_path.exists():
                    st.session_state["active_capture_path"] = str(selected_case.raw_path)
                    st.session_state["active_capture_name"] = selected_case.name
                st.rerun()

    else:
        # Live File Ingest Mode
        st.sidebar.caption("Ingest raw .cf32, .iq, .wav, or verified JSON schema contract:")

        uploaded_file = st.sidebar.file_uploader(
            "Upload Signal File",
            type=["cf32", "iq", "wav", "json", "npy"],
            help="Supported: .cf32, .iq, .wav, .json, .npy",
            key="live_uploader",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            
            st.sidebar.markdown(
                f"""
                <div style="background:rgba(16, 185, 129, 0.1); border:1px solid rgba(16, 185, 129, 0.3);
                     border-radius:10px; padding:0.5rem 0.75rem; margin:0.4rem 0;">
                    <div style="font-size:0.75rem; color:#34d399; font-weight:700;">
                        ✓ {uploaded_file.name}
                    </div>
                    <div style="font-size:0.65rem; color:#94a3b8; font-family:'JetBrains Mono';">
                        {len(file_bytes)/1024:.1f} KB • SHA: {sha256_hash[:12]}...
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

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
                        st.sidebar.success("Contract verified against schema!")
                        st.rerun()
                    except Exception as exc:
                        st.sidebar.error(f"Contract Schema Error: {exc}")
            else:
                # Raw IQ, CF32, or WAV file
                is_wav = uploaded_file.name.lower().endswith(".wav")
                user_fs = None
                fs_source_label = "HEADER"

                if is_wav:
                    st.sidebar.caption("🎵 WAV Header will supply sample rate automatically.")
                    fs_source_label = "HEADER"
                else:
                    user_fs = st.sidebar.number_input(
                        "Sample Rate (Hz):",
                        min_value=1_000.0,
                        max_value=1_000_000_000.0,
                        value=100_000.0,
                        step=10_000.0,
                        format="%.0f",
                        help="Specify receiver sampling rate for headerless binary captures",
                    )
                    fs_source_label = "USER PROVIDED"

                if st.sidebar.button("🚀 Analyze Signal via Backend", type="primary", use_container_width=True):
                    with st.spinner("Executing blind SpectralQ analysis pipeline..."):
                        scratch_dir = Path("data") / "scratch"
                        scratch_dir.mkdir(parents=True, exist_ok=True)
                        tmp_cap = scratch_dir / uploaded_file.name
                        with open(tmp_cap, "wb") as f:
                            f.write(file_bytes)
                        if user_fs and not is_wav:
                            comp_meta = {"sample_rate": float(user_fs), "fs_hz": float(user_fs)}
                            with open(tmp_cap.with_suffix(".json"), "w") as f:
                                json.dump(comp_meta, f)

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
                                result=norm_res,
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
                            st.session_state["active_capture_path"] = str(tmp_cap)
                            st.session_state["active_capture_name"] = uploaded_file.name
                            st.sidebar.success("Signal analysis complete!")
                            st.rerun()
                        except Exception as exc:
                            st.sidebar.error("Analysis execution error.")
                            with st.sidebar.expander("🛠️ Error Diagnostics", expanded=True):
                                st.code(str(exc))

    st.sidebar.markdown("---")

    # -------------------------------------------------------------------------
    # 4. Toggling Component at the BOTTOM (Requirement 1 Fulfilled)
    # -------------------------------------------------------------------------
    st.sidebar.markdown(
        """
        <div style="font-size:0.68rem; font-weight:800; color:#64748b; letter-spacing:0.08em;
             text-transform:uppercase; margin-bottom:0.4rem;">
            SYSTEM PREFERENCES
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Guided Demo Mode Toggle
    is_demo = st.session_state.get("guided_demo_active", False)
    demo_toggle = st.sidebar.checkbox(
        "🎯 Guided Demo Mode (Judges)",
        value=is_demo,
        help="Interactive guided tour walking through real captures, golden cases, and abstention scenarios.",
    )
    if demo_toggle != is_demo:
        st.session_state["guided_demo_active"] = demo_toggle
        st.rerun()

    # Theme Display (Locked to Dark Theme)
    st.sidebar.caption("Theme: **DARK**")

    st.sidebar.markdown(
        """
        <div style="margin-top:1.0rem; text-align:center; font-size:0.62rem; color:#475569; letter-spacing:0.06em;">
            SPECTRALQ v2.0 • PROD BUILD
        </div>
        """,
        unsafe_allow_html=True,
    )
