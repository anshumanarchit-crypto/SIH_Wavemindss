"""
Workspace 5: Evidence & Decision (Audit Trail & Confidence Engine).
Visualizes the L1-L5 Evidence Ladder, aggregated check counts, the complete interactive
evidence ledger table with multi-criteria filtering, and the 'Explain Decision' drawer.
"""

from typing import Optional, List, Dict, Any
import streamlit as st

from ui.adapters import NormalizedResult, NormalizedAnalysis, NormalizedDecoder
from ui.styles.theme import get_theme_tokens, TOOLTIPS


LADDER_LEVELS = [
    ("L1", "Signal Detection", "Active burst detected, center frequency, bandwidth, and SNR estimated above floor."),
    ("L2", "Modulation Identification", "Statistical features and ML classifier agree on modulation candidate without severe penalty."),
    ("L3", "Blind Demodulation", "Carrier frequency offset corrected, symbol timing synchronized, constellation locked."),
    ("L4", "Coding & FEC Lock", "Interleaver structure resolved, convolutional/viterbi and Reed-Solomon inner/outer FEC locked."),
    ("L5", "Frame & CRC Verified", "Preamble/sync word aligned, frame boundaries established, CRC polynomial passes with zero parity errors."),
]


def render_evidence_decision(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
    decoder: Optional[NormalizedDecoder],
) -> None:
    """Renders the Evidence & Decision workspace."""
    st.markdown("## ⚖️ Evidence & Decision Engine")
    st.caption("Stage 10: Hierarchical Verification Ladder, Evidence Ledger (Archit), and Confidence Provenance.")

    if not result:
        st.info("No result telemetry loaded. Please select or load a capture.")
        return

    tokens = get_theme_tokens()

    # 1. Prominent UNKNOWN Diagnosis (if Abstained)
    if result.is_unknown:
        st.markdown(
            f"""
            <div class="sq-unknown-banner">
                <div class="sq-unknown-title">
                    🛑 PIPELINE ABSTENTION / UNKNOWN STATE DIAGNOSIS
                </div>
                <div class="sq-unknown-desc">
                    <b>Primary Reason:</b> {result.unknown_reason or "Low confidence or ambiguous signal parameters."}<br><br>
                    <b>Why did SpectralQ abstain?</b> Rather than forcing an ungrounded or speculative classification, 
                    the decision engine triggered abstention because evidence was insufficient to guarantee operational reliability.<br>
                    <b>Failed Checks:</b> {', '.join(result.failed_checks) if result.failed_checks else 'None explicit; low SNR or consensus penalty'}<br>
                    <b>Resolution:</b> Collect higher SNR samples or wider capture bandwidth to resolve ambiguity.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Evidence Ladder Visualization (L1 - L5)
    st.markdown("### 🪜 Hierarchical Evidence Ladder")
    st.caption(TOOLTIPS["LADDER"])

    current_ladder = result.ladder_level
    ladder_cols = st.columns(5)

    # Ladder rank map
    ranks = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
    curr_rank = ranks.get(current_ladder, 1)

    for idx, (lvl, name, desc) in enumerate(LADDER_LEVELS):
        lvl_rank = ranks[lvl]
        is_current = (lvl == current_ladder)
        is_achieved = (lvl_rank <= curr_rank)

        with ladder_cols[idx]:
            border_color = tokens["primary"] if is_current else (tokens["pass_color"] if is_achieved else tokens["card_border"])
            bg_color = tokens["ladder_bg"] if is_current else (tokens["card_bg"])
            badge_html = f"<span class='sq-badge badge-pass'>ACHIEVED</span>" if is_achieved else "<span class='sq-badge badge-notrun'>PENDING</span>"
            if is_current:
                badge_html = f"<span class='sq-badge badge-ladder'>CURRENT LEVEL</span>"

            st.markdown(
                f"""
                <div class="sq-card" style="border: 2px solid {border_color}; background-color:{bg_color}; min-height: 140px;">
                    <div class="sq-card-title">{lvl}: {name}</div>
                    <div style="margin: 0.35rem 0;">{badge_html}</div>
                    <div style="font-size:0.75rem; color:{tokens['text_muted']}; line-height:1.3;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # 3. Evidence Check Summary Metrics
    st.markdown("### 📊 Verification Check Aggregates")
    all_evidence = result.evidence
    passed = [e for e in all_evidence if e.status == "PASS"]
    failed = [e for e in all_evidence if e.status == "FAIL"]
    unavail = [e for e in all_evidence if e.status == "UNAVAILABLE"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Evidence Checks", len(all_evidence), "Comprehensive Audit")
    with c2:
        st.metric("Passed Checks", len(passed), f"{(len(passed)/len(all_evidence)*100.0) if all_evidence else 0:.1f}%")
    with c3:
        st.metric("Failed Checks", len(failed), f"-{result.rule_ml_penalty:.2f} penalty" if failed else "Zero Penalties")
    with c4:
        st.metric("Unavailable Checks", len(unavail), f"{len(unavail)} checks skipped")

    st.markdown("---")

    # 4. Interactive Evidence Ledger Table
    st.markdown("### 📜 Evidence Ledger Audit Trail")
    st.caption("Inspect individual telemetry checks across physical DSP, ML AMC, and blind FEC decoding layers.")

    f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
    with f_col1:
        status_filter = st.selectbox(
            "Filter by Status:",
            ["ALL", "PASS", "FAIL", "UNAVAILABLE"],
            index=0,
            key="ev_status_filter",
        )
    with f_col2:
        all_sources = sorted(list(set(e.source for e in all_evidence))) if all_evidence else []
        source_filter = st.selectbox(
            "Filter by Source:",
            ["ALL"] + all_sources,
            index=0,
            key="ev_source_filter",
        )
    with f_col3:
        search_query = st.text_input("Search Check or Explanation:", placeholder="e.g. snr, viterbi, consensus", key="ev_search_input")

    # Filter checks
    filtered_evidence = all_evidence
    if status_filter != "ALL":
        filtered_evidence = [e for e in filtered_evidence if e.status == status_filter]
    if source_filter != "ALL":
        filtered_evidence = [e for e in filtered_evidence if e.source == source_filter]
    if search_query:
        q = search_query.lower()
        filtered_evidence = [e for e in filtered_evidence if q in e.check_name.lower() or q in e.explanation.lower()]

    table_data = []
    for e in filtered_evidence:
        table_data.append({
            "ID": e.evidence_id,
            "Source": e.source,
            "Check Name": e.check_name,
            "Status": e.status,
            "Explanation": e.explanation,
        })

    st.dataframe(table_data, use_container_width=True, height=280)

    # 5. "Explain Decision" Interactive Drawer
    with st.expander("💡 Deep Dive: Mathematical Confidence Aggregation Breakdown", expanded=False):
        st.markdown("#### Confidence Aggregation Formula")
        st.latex(r"C_{\text{final}} = P_{\text{ML}} \cdot (1 - \text{Penalty}_{\text{Consensus}}) \cdot \prod_{i} (1 - P_{\text{check}, i})")
        st.markdown(
            f"""
            - **Raw ML Model Probability:** `{result.ml_probability:.4f}`
            - **Consensus Agreement:** `{'PASS (0.00 penalty)' if result.rule_ml_agreement else f'FAIL (-{result.rule_ml_penalty:.2f} penalty)'}`
            - **Calibrated ML Probability:** `{result.calibrated_ml_probability:.4f}`
            - **Cross-Window Consistency:** `{result.cross_window_agreement:.2f}`
            - **Final Aggregated Confidence:** `{result.final_confidence:.4f}`
            - **Confidence Engine Version:** `{result.confidence_version}`
            """
        )
