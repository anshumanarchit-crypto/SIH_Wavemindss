"""
Workspace 5: Evidence & Decision (Audit Trail & Confidence Engine).
Operational evidence command center providing:
- Evidence Verification Ladder (L1-L5 Progression Spine)
- Verification Check Aggregates & Penalty Breakdown
- Interactive Filterable Evidence Ledger Audit Trail
- Mathematical Confidence Aggregation Breakdown
"""

from typing import Optional, List, Dict, Any
import streamlit as st

from ui.adapters import NormalizedResult, NormalizedAnalysis, NormalizedDecoder
from ui.styles.theme import get_theme_tokens, TOOLTIPS
from ui.components.icons import get_icon_svg


LADDER_LEVELS = [
    ("L1", "Signal Detection", "Active burst detected, center frequency, bandwidth, and SNR estimated above floor."),
    ("L2", "Modulation Identification", "Statistical features and ML classifier agree on modulation candidate without severe penalty."),
    ("L3", "Blind Demodulation", "Carrier frequency offset corrected, symbol timing synchronized, constellation locked."),
    ("L4", "Coding & FEC Lock", "Interleaver structure resolved, convolutional and Reed-Solomon inner/outer FEC locked."),
    ("L5", "Frame & CRC Verified", "Preamble/sync word aligned, frame boundaries established, CRC polynomial passes with zero parity errors."),
]


def render_evidence_decision(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
    decoder: Optional[NormalizedDecoder],
) -> None:
    """Renders the defense-grade Evidence & Decision workspace."""
    tokens = get_theme_tokens()

    # Workspace Header
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem; border-bottom:1px solid {tokens['card_border']}; padding-bottom:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.6rem;">
                {get_icon_svg("evidence_decision", size=20, color=tokens['primary'])}
                <span style="font-size:1.15rem; font-weight:800; letter-spacing:0.04em; color:{tokens['text']};">
                    EVIDENCE LEDGER &amp; DECISION VERIFICATION
                </span>
            </div>
            <div>
                <span class="sq-badge badge-ladder">
                    {get_icon_svg('layers', size=11)} LADDER {result.ladder_level if result else 'N/A'}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not result:
        st.info("No signal telemetry contract loaded. Please select a capture case.")
        return

    # 1. Prominent UNKNOWN Diagnosis (if Abstained)
    if result.is_unknown:
        st.markdown(
            f"""
            <div class="sq-unknown-banner">
                <div style="display:flex; align-items:flex-start; gap:0.75rem;">
                    {get_icon_svg("shield_alert", size=20, color=tokens['fail_color'])}
                    <div>
                        <div style="font-size:0.95rem; font-weight:800; color:{tokens['fail_color']};">
                            PIPELINE ABSTENTION / UNKNOWN STATE AUDIT
                        </div>
                        <div style="color:{tokens['text']}; font-size:0.82rem; margin-top:0.3rem; line-height:1.45;">
                            <b>Primary Reason:</b> {result.unknown_reason or "Low confidence or ambiguous signal parameters."}<br>
                            <b>Epistemic Guarantee:</b> Rather than forcing an ungrounded or speculative classification, 
                            the decision engine enforced abstention because evidence was insufficient to guarantee operational reliability.<br>
                            <b>Failed Verification Checks:</b> {', '.join(result.failed_checks) if result.failed_checks else 'None explicit; low SNR or consensus divergence'}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Evidence Ladder Progression Spine (L1 - L5)
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.6rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                {get_icon_svg("layers", size=16, color=tokens['primary'])}
                <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                    Hierarchical Verification Ladder
                </span>
            </div>
            <span style="font-size:0.7rem; color:{tokens['text_muted']};">Progressive Evidence Grounding Hierarchy</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_ladder = result.ladder_level
    if decoder is not None:
        _crc_ok = getattr(decoder, "crc_passed", False)
        _ber_val = getattr(decoder, "reencode_ber", None)
        _sync_ok = getattr(decoder, "sync_word", None) is not None
        _ber_zero = _ber_val is not None and _ber_val == 0.0
        if _crc_ok or (_ber_zero and _sync_ok):
            current_ladder = "L5"

    ladder_cols = st.columns(5)
    ranks = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
    curr_rank = ranks.get(current_ladder, 1)

    for idx, (lvl, name, desc) in enumerate(LADDER_LEVELS):
        lvl_rank = ranks[lvl]
        is_current = (lvl == current_ladder)
        is_achieved = (lvl_rank <= curr_rank)

        with ladder_cols[idx]:
            border_color = tokens["primary"] if is_current else (tokens["pass_color"] if is_achieved else tokens["card_border"])
            badge_html = f"<span class='sq-badge badge-ladder'>CURRENT</span>" if is_current else (
                f"<span class='sq-badge badge-pass'>ACHIEVED</span>" if is_achieved else f"<span class='sq-badge badge-notrun'>PENDING</span>"
            )

            st.markdown(
                f"""
                <div class="sq-card" style="border: 1px solid {border_color}; min-height: 140px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div class="sq-card-title">{lvl}: {name}</div>
                        <div style="font-size:0.72rem; color:{tokens['text_muted']}; line-height:1.3; margin-top:0.3rem;">{desc}</div>
                    </div>
                    <div style="margin-top:0.4rem;">{badge_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Evidence Check Summary Metrics
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.6rem;">
            {get_icon_svg("spectrum", size=16, color=tokens['primary'])}
            <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                Verification Check Aggregates
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_evidence = result.evidence
    passed = [e for e in all_evidence if e.status == "PASS"]
    failed = [e for e in all_evidence if e.status == "FAIL"]
    unavail = [e for e in all_evidence if e.status == "UNAVAILABLE"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">Total Evidence Checks</div>
                <div class="sq-card-value">{len(all_evidence)}</div>
                <div class="sq-card-sub">Comprehensive Audit Suite</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        pass_pct = (len(passed) / len(all_evidence) * 100.0) if all_evidence else 0.0
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">Passed Checks</div>
                <div class="sq-card-value" style="color:{tokens['pass_color']};">{len(passed)}</div>
                <div class="sq-card-sub">{pass_pct:.1f}% Verification Rate</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        failed_col = tokens["fail_color"] if failed else tokens["text_muted"]
        failed_pen_str = f"-{result.rule_ml_penalty:.2f} penalty" if (failed and result.rule_ml_penalty is not None) else "Zero penalties applied"
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">Failed Checks</div>
                <div class="sq-card-value" style="color:{failed_col};">{len(failed)}</div>
                <div class="sq-card-sub">{failed_pen_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">Unavailable Checks</div>
                <div class="sq-card-value" style="color:{tokens['text_muted']};">{len(unavail)}</div>
                <div class="sq-card-sub">Safely Skipped / Bypassed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Interactive Evidence Ledger Table
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.6rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                {get_icon_svg("file", size=16, color=tokens['primary'])}
                <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                    Evidence Ledger Audit Trail
                </span>
            </div>
            <span style="font-size:0.7rem; color:{tokens['text_muted']};">Granular Check Verification Registry</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        search_query = st.text_input("Search Check or Explanation:", placeholder="e.g. snr, consensus, crc", key="ev_search_input")

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
    with st.expander("💡 Mathematical Confidence Aggregation Breakdown", expanded=False):
        st.markdown("#### Confidence Aggregation Formula")
        st.latex(r"C_{\text{final}} = P_{\text{ML}} \cdot (1 - \text{Penalty}_{\text{Consensus}}) \cdot \prod_{i} (1 - P_{\text{check}, i})")
        raw_prob_txt = f"{result.ml_probability:.4f}" if result.ml_probability is not None else "N/A"
        pen_txt = f"FAIL (-{result.rule_ml_penalty:.2f} penalty)" if (result.rule_ml_penalty is not None and not result.rule_ml_agreement) else ("PASS (0.00 penalty)" if result.rule_ml_agreement else "FAIL")
        cal_prob_txt = f"{result.calibrated_ml_probability:.4f}" if result.calibrated_ml_probability is not None else (f"{result.ml_probability:.4f} (Uncalibrated)" if result.ml_probability is not None else "N/A")
        cwa_txt = f"{result.cross_window_agreement:.2f}" if result.cross_window_agreement is not None else "N/A"
        fin_conf_txt = f"{result.final_confidence:.4f}" if result.final_confidence is not None else "N/A"

        st.markdown(
            f"""
            - **Raw ML Model Probability:** `{raw_prob_txt}`
            - **Consensus Agreement:** `{pen_txt}`
            - **Calibrated ML Probability:** `{cal_prob_txt}`
            - **Cross-Window Consistency:** `{cwa_txt}`
            - **Final Aggregated Confidence:** `{fin_conf_txt}`
            - **Confidence Engine Version:** `{result.confidence_version or 'v1.0'}`
            """
        )
