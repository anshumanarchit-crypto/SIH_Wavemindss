"""
SpectralQ Navigation & Sidebar Command Console.
Coordinates workspace selection, case discovery, live ingest, and system settings.
Designed to meet the Defense RF Intelligence Command Center specification.
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
from ui.styles.theme import get_current_theme_name, get_theme_tokens
from ui.components.icons import get_icon_svg, get_workspace_icon_svg


def render_sidebar(cases: List[DiscoveredCase]) -> None:
    """Renders the defense-grade sidebar command rail."""
    tokens = get_theme_tokens()
    current_ws = st.session_state.get("active_workspace", "Mission Control")

    # 1. Brand Block at Top
    logo_svg = get_icon_svg("logo_mark", size=24, color=tokens["primary"])
    st.sidebar.markdown(
        f"""
        <div style="padding: 0.25rem 0 0.85rem 0; border-bottom: 1px solid {tokens['card_border']}; margin-bottom: 0.85rem;">
            <div style="display:flex; align-items:center; gap:0.65rem;">
                <div style="background:{tokens['card_bg']}; border:1px solid {tokens['card_border_strong']};
                    border-radius:8px; width:36px; height:36px; display:flex; align-items:center;
                    justify-content:center; box-shadow:{tokens['glow_primary']};">
                    {logo_svg}
                </div>
                <div>
                    <div style="font-size:1.15rem; font-weight:800; letter-spacing:0.04em; color:{tokens['text']}; line-height:1.1;">
                        SPECTRAL<span style="color:{tokens['primary']};">Q</span>
                    </div>
                    <div style="font-size:0.62rem; font-weight:700; color:{tokens['primary']}; letter-spacing:0.12em; text-transform:uppercase; margin-top:2px;">
                        RF INTELLIGENCE // NTRO
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Guided Demo Mode (Judge Presentation Mode)
    is_demo = st.session_state.get("guided_demo_active", False)
    demo_toggle = st.sidebar.checkbox(
        "🎯 Judge Demo Mode",
        value=is_demo,
        help="Interactive presentation walkthrough for evaluators: guided cases, golden verification, and abstention telemetry.",
    )
    if demo_toggle != is_demo:
        st.session_state["guided_demo_active"] = demo_toggle
        st.rerun()

    # 3. Workspace Navigation Rail
    st.sidebar.markdown(
        f"""
        <div style="font-size:0.65rem; font-weight:800; color:{tokens['text_muted']};
            text-transform:uppercase; letter-spacing:0.1em; margin: 0.85rem 0 0.4rem 0;">
            Primary Workspaces
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Core 7 Workspaces
    for ws in WORKSPACES:
        is_active = ws == current_ws
        btn_type = "primary" if is_active else "secondary"
        icon_svg = get_workspace_icon_svg(ws, size=16, color=tokens["bg"] if is_active else tokens["primary"])

        if st.sidebar.button(
            f"{ws}",
            key=f"nav_btn_{ws}",
            type=btn_type,
            use_container_width=True,
        ):
            if current_ws != ws:
                st.session_state["active_workspace"] = ws
                st.rerun()

    # Specialized Operations / Utility Section
    st.sidebar.markdown(
        f"""
        <div style="font-size:0.65rem; font-weight:800; color:{tokens['text_muted']};
            text-transform:uppercase; letter-spacing:0.1em; margin: 0.85rem 0 0.4rem 0;">
            Operations &amp; Utilities
        </div>
        """,
        unsafe_allow_html=True,
    )

    u_col1, u_col2 = st.sidebar.columns(2)
    with u_col1:
        if st.button(
            "🧬 Generator",
            key="nav_btn_synth",
            type="primary" if current_ws in ("Synthetic Generator", "🧬 Synthetic Generator") else "secondary",
            use_container_width=True,
        ):
            st.session_state["active_workspace"] = "Synthetic Generator"
            st.rerun()
    with u_col2:
        if st.button(
            "📡 Scanner",
            key="nav_btn_wb",
            type="primary" if current_ws == "Wideband Scanner" else "secondary",
            use_container_width=True,
        ):
            st.session_state["active_workspace"] = "Wideband Scanner"
            st.rerun()

    if st.sidebar.button(
        "⏱️ Execution Trace",
        key="nav_btn_trace",
        type="primary" if current_ws == "Run Trace" else "secondary",
        use_container_width=True,
    ):
        st.session_state["active_workspace"] = "Run Trace"
        st.rerun()

    st.sidebar.markdown("---")

    # 4. Ingest Control Center (Capture Control)
    st.sidebar.markdown(
        f"""
        <div style="font-size:0.68rem; font-weight:800; color:{tokens['text_muted']};
            text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.4rem;">
            Capture Control Center
        </div>
        """,
        unsafe_allow_html=True,
    )

    mode = st.sidebar.radio(
        "Ingest Mode:",
        ["Replay / Case Explorer", "Live SDR / File Ingest"],
        index=0 if st.session_state.get("is_replay", True) else 1,
        label_visibility="collapsed",
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
            "Target RF Capture:",
            case_names,
            index=default_idx,
            key="case_selector_box",
        )
        selected_case = case_map[selected_case_name]

        st.sidebar.markdown(
            f"""
            <div style="background:{tokens['card_bg']}; border:1px solid {tokens['card_border']};
                border-radius:8px; padding:0.6rem 0.75rem; margin:0.4rem 0 0.6rem 0; font-size:0.75rem;">
                <div style="font-weight:700; color:{tokens['primary']}; text-transform:uppercase; font-size:0.65rem;">
                    {selected_case.category}
                </div>
                <div style="color:{tokens['text_secondary']}; margin-top:0.2rem; line-height:1.35;">
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
            with st.spinner("Loading telemetry contracts & observatory artifacts..."):
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
                st.rerun()

    else:
        # Live File Ingest Mode
        st.sidebar.caption("Accepts raw .cf32, .iq, .wav, or verified schema contract JSON:")

        uploaded_file = st.sidebar.file_uploader(
            "Upload Signal File",
            type=["cf32", "iq", "wav", "json", "npy"],
            help="Upload raw I/Q samples, WAV audio, or verified JSON contract",
            key="live_uploader",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            st.sidebar.markdown(
                f"""
                <div style="background:{tokens['card_bg']}; border:1px solid {tokens['border_success'] if 'border_success' in tokens else tokens['card_border']};
                    border-radius:8px; padding:0.6rem 0.75rem; margin:0.4rem 0;">
                    <div style="font-weight:700; color:{tokens['pass_color']}; font-size:0.75rem;">
                        ✓ File Ingested: {uploaded_file.name}
                    </div>
                    <div style="font-family:'JetBrains Mono', monospace; font-size:0.65rem; color:{tokens['text_muted']}; margin-top:2px;">
                        Size: {len(file_bytes)/1024:.1f} KB | SHA: {sha256_hash[:12]}...
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
                        st.sidebar.success("Contract parsed and verified against schema!")
                        st.rerun()
                    except Exception as exc:
                        st.sidebar.error(f"Contract Schema Error: {exc}")
            else:
                # Raw IQ, CF32, or WAV file
                is_wav = uploaded_file.name.lower().endswith(".wav")
                user_fs = None
                fs_source_label = "HEADER"

                if is_wav:
                    st.sidebar.caption("🎵 Rate will be read from WAV header.")
                    fs_source_label = "HEADER"
                else:
                    st.sidebar.caption("Headerless raw IQ/CF32 sample rate:")
                    user_fs = st.sidebar.number_input(
                        "Sampling Rate (Hz):",
                        min_value=1_000.0,
                        max_value=1_000_000_000.0,
                        value=100_000.0,
                        step=10_000.0,
                        format="%.0f",
                    )
                    fs_source_label = "USER PROVIDED"

                if st.sidebar.button("🚀 Analyze Signal via Backend", type="primary", use_container_width=True):
                    with st.spinner("Executing blind SpectralQ backend pipeline..."):
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
                            st.sidebar.success("Analysis complete!")
                            st.rerun()
                        except Exception as exc:
                            st.sidebar.error(f"Analysis failed: {exc}")

    st.sidebar.markdown("---")

    # 5. Theme / System Settings at the VERY BOTTOM (Dock Console)
    current_theme = get_current_theme_name()
    new_theme = "light" if current_theme == "dark" else "dark"
    theme_icon = get_icon_svg("sun" if current_theme == "dark" else "moon", size=14, color=tokens["text_muted"])

    st.sidebar.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
            <span style="font-size:0.65rem; color:{tokens['text_muted']}; text-transform:uppercase; font-weight:700;">
                System Theme
            </span>
            <span style="font-size:0.68rem; font-weight:700; color:{tokens['primary']}; font-family:'JetBrains Mono', monospace;">
                {current_theme.upper()}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.sidebar.button(
        f"Switch to {new_theme.capitalize()} Mode",
        key="theme_toggle_dock_btn",
        use_container_width=True,
    ):
        st.session_state["theme"] = new_theme
        st.rerun()

    st.sidebar.caption("SpectralQ v2.0 · NTRO Defense Telemetry Specification")
